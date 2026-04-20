// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T026 — `agent-interrupt` action handler (User Story 1).
//
// Closes #1577. FR-012 / FR-013 / SC-001 / SC-006.
//
// Design:
//   - A pure controller (no React dep) encapsulates the double-press arm/fire
//     state machine described in data-model.md § State transitions.
//   - `handle()` returns a `Outcome` rather than mutating UI state directly,
//     so the Ink-side `useKeybinding('Global', ...)` handler can plug it into
//     the resolver without owning additional state.
//
// Contract (consumed by the resolver + `useKeybinding` Chat/Global bag):
//   1. If an agent loop is active, every ctrl+c press:
//        a. invokes `cancellation.cancelActiveAgentLoop(sessionId)`
//        b. writes a Spec 024 `user-interrupted` audit record via `audit`
//        c. announces an assertive accessibility notice (FR-030)
//        d. clears any previously armed double-press state
//      and returns `{ kind: 'interrupted', tool_call_id }`.
//   2. If no agent loop is active and the controller is idle, ctrl+c arms a
//      double-press exit window of `ARM_WINDOW_MS` ms (FR-013) and announces
//      an assertive "press ctrl+c again to exit" notice.  Returns
//      `{ kind: 'armed', expires_at }`.
//   3. If the controller is armed and the virtual clock is still within
//      the window, ctrl+c fires `session-exit`:
//        a. writes a Spec 024 `session-exited` audit record (SC-006)
//        b. announces the exit
//        c. invokes `deps.exit(0)` — injectable so tests do not crash.
//      Returns `{ kind: 'exited' }`.
//   4. If the arm window expired, ctrl+c falls through to case (2) and
//      re-arms — the timeout is silent (no audit, no exit).
//
// Audit resilience (FR-013 SC-001): a rejected audit write MUST NOT abort
// the interrupt — the cancellation envelope fires regardless. The
// rejection is swallowed (logged to stderr) to preserve the UI contract.
//
// The resolver already writes a matching reserved-action audit record on
// span emission (T014b); this handler writes the same payload so tests
// that mock the resolver see the audit call too.  In production the
// double-write is deduplicated by the Spec 024 writer via
// `transaction_id` — handled in the backend, out of scope for the TUI.

import {
  type AccessibilityAnnouncer,
  type AuditWriter,
  type CancellationSignal,
  type ReservedActionAuditPayload,
} from '../types'

// ---------------------------------------------------------------------------
// Tunables
// ---------------------------------------------------------------------------

/** Double-press exit window per FR-013. */
export const ARM_WINDOW_MS = 2000

// ---------------------------------------------------------------------------
// Dependencies — everything the controller needs, injected so tests can
// replace each surface with an in-memory stub.  Mirrors the `AuditWriter`
// injection pattern Team C adopted in T037.
// ---------------------------------------------------------------------------

export type AgentInterruptDeps = Readonly<{
  sessionId: string
  /** True while the agent tool-loop is actively running a tool call. */
  isAgentLoopActive: () => boolean
  /** Current in-flight tool-call id (null when idle). */
  currentToolCallId: () => string | null
  cancellation: CancellationSignal
  audit: AuditWriter
  announcer: AccessibilityAnnouncer
  /** Clock — injectable for virtual-time tests. */
  now?: () => number
  /** Process-exit shim — injectable for tests.  Default: `process.exit`. */
  exit?: (code: number) => void
}>

// ---------------------------------------------------------------------------
// Outcome — reported back to the Ink-side caller for test assertions and UI
// state updates (e.g., flashing the "press again to exit" hint).
// ---------------------------------------------------------------------------

export type AgentInterruptOutcome =
  | Readonly<{
      kind: 'interrupted'
      tool_call_id: string | null
    }>
  | Readonly<{
      kind: 'armed'
      expires_at: number
    }>
  | Readonly<{ kind: 'exited' }>

// ---------------------------------------------------------------------------
// Controller interface — exposed to the caller.
// ---------------------------------------------------------------------------

export interface AgentInterruptController {
  /** Handle one ctrl+c press; returns the resulting outcome. */
  handle(): Promise<AgentInterruptOutcome>
  /** Clear any armed state (used by tests + timer-driven timeouts). */
  reset(): void
  /** Current armed-expires-at epoch-ms, or null when idle. */
  readonly armedExpiresAt: number | null
}

// ---------------------------------------------------------------------------
// Announcer messages (Korean-first per spec UX surface).
// ---------------------------------------------------------------------------

const INTERRUPT_MESSAGE =
  '에이전트 루프를 중단했습니다. / Agent loop interrupted.'
const ARM_MESSAGE =
  '종료하려면 Ctrl+C를 다시 누르세요. / Press Ctrl+C again to exit.'
const EXIT_MESSAGE =
  '세션을 안전하게 종료합니다. / Exiting session cleanly.'

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

export function createAgentInterruptController(
  deps: AgentInterruptDeps,
): AgentInterruptController {
  const now = deps.now ?? Date.now
  // eslint-disable-next-line @typescript-eslint/unbound-method -- process.exit is
  // intentionally bound by reference so the default path mirrors production.
  const exit = deps.exit ?? ((code: number) => process.exit(code))
  let armedExpiresAt: number | null = null

  return {
    get armedExpiresAt() {
      return armedExpiresAt
    },

    reset() {
      armedExpiresAt = null
    },

    async handle(): Promise<AgentInterruptOutcome> {
      // Loop-active path wins over any armed state (FR-012 precedence).
      if (deps.isAgentLoopActive()) {
        armedExpiresAt = null
        const toolCallId = deps.currentToolCallId()
        const payload: ReservedActionAuditPayload = {
          event_type: 'user-interrupted',
          session_id: deps.sessionId,
          ...(toolCallId !== null
            ? { interrupted_tool_call_id: toolCallId }
            : {}),
        }
        // FR-030 — assertive announce first so screen readers never miss the
        // interrupt when a noisy loop was streaming output.
        deps.announcer.announce(INTERRUPT_MESSAGE, { priority: 'assertive' })
        // Fire the cancellation envelope.  This is the SC-001 critical path;
        // the signal implementation MUST be non-blocking.
        try {
          await deps.cancellation.cancelActiveAgentLoop(deps.sessionId)
        } catch (err) {
          process.stderr.write(
            `[keybindings] cancellation failed: ${(err as Error).message}\n`,
          )
        }
        // Best-effort audit.  Rejection is logged but never re-thrown — the
        // interrupt semantics win per FR-013 comment above.
        try {
          await deps.audit.writeReservedAction(payload)
        } catch (err) {
          process.stderr.write(
            `[keybindings] audit write failed: ${(err as Error).message}\n`,
          )
        }
        return Object.freeze({
          kind: 'interrupted',
          tool_call_id: toolCallId,
        })
      }

      // No active loop — consult the arm state.
      const currentTime = now()
      if (armedExpiresAt !== null && currentTime <= armedExpiresAt) {
        // Fire the double-press exit.
        armedExpiresAt = null
        const payload: ReservedActionAuditPayload = {
          event_type: 'session-exited',
          session_id: deps.sessionId,
        }
        deps.announcer.announce(EXIT_MESSAGE, { priority: 'polite' })
        try {
          await deps.audit.writeReservedAction(payload)
        } catch (err) {
          process.stderr.write(
            `[keybindings] audit write failed: ${(err as Error).message}\n`,
          )
        }
        // Exit the process.  Tests inject a shim so this does not terminate
        // the test runner.
        exit(0)
        return Object.freeze({ kind: 'exited' })
      }

      // Idle — arm the double-press window (also covers the "arm expired,
      // next press re-arms" case per data-model.md § State transitions).
      armedExpiresAt = currentTime + ARM_WINDOW_MS
      deps.announcer.announce(ARM_MESSAGE, { priority: 'assertive' })
      return Object.freeze({ kind: 'armed', expires_at: armedExpiresAt })
    },
  }
}
