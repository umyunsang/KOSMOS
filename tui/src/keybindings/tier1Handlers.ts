// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 288 Codex P1 follow-up.
//
// Wires the real Tier-1 action controllers (agent-interrupt, session-exit,
// permission-mode-cycle, history-prev, history-next, history-search) into the
// `ActionHandlers` shape consumed by `<KeybindingProviderSetup>`'s
// `handlerOverrides` prop.  Without this bridge the provider falls back to its
// announce-only stubs (Codex P1 on tui.tsx:513), so dispatched chords never
// invoke their intended controller — reserved shortcuts such as ctrl+d and
// history navigation become silent at runtime.
//
// Wiring strategy:
//   - Real deps are used wherever the surrounding TUI state already exists
//     (session id, permission mode, IME-backed buffer probe, consent state).
//   - Backend-bound deps that require an IPC protocol KOSMOS has not yet
//     implemented (Spec 027 cancellation envelope, Spec 024 audit writer) are
//     supplied as fail-loud stubs — stderr traces identify the missing piece
//     so the follow-up integration (tracked under Spec 288.1) has a
//     reproducible signal.
//
// `buildTier1Handlers` itself is pure: it closes over the provided deps and
// returns frozen `ActionHandlers` bags keyed by Keybinding context.  The
// returned object is passed straight into `handlerOverrides`, where the
// provider registers each handler bag against the matching context via
// `registerHandlers(context, bag)`.

import {
  createAgentInterruptController,
  type AgentInterruptDeps,
} from './actions/agentInterrupt'
import {
  buildSessionExitHandler,
  type SessionExitDeps,
} from './actions/sessionExit'
import {
  buildPermissionModeCycleHandler,
  type PermissionModeCycleDeps,
} from './actions/permissionModeCycle'
import {
  createHistoryNavigator,
  type HistoryNavigationEntry,
  type HistoryNavigatorDeps,
} from './actions/historyNavigate'
import {
  openHistorySearchOverlay,
  type HistoryEntry,
  type OverlayOpenRequest,
} from './actions/historySearch'
import type { PermissionMode } from '../permissions/types'
import type {
  AccessibilityAnnouncer,
  AuditWriter,
  CancellationSignal,
} from './types'
import type { ActionHandlers } from './useKeybinding'

// ---------------------------------------------------------------------------
// Public dep surface — what `tui.tsx` threads into the factory.
// ---------------------------------------------------------------------------

export type Tier1HandlerDeps = Readonly<{
  /** Current session id (backend session_id when handshaked, else the
   *  onboarding-local UUID from `sessionIdRef`). */
  sessionId: string

  /** Accessibility announcer — same instance the provider holds. */
  announcer: AccessibilityAnnouncer

  // -------------------------------------------------------------------------
  // Agent loop probes
  // -------------------------------------------------------------------------

  /**
   * `true` while the agent tool-loop is actively streaming or running a tool
   * call.  Drives `agent-interrupt` (kill vs arm-exit) and `session-exit`
   * (prompt for confirmation).
   */
  isAgentLoopActive: () => boolean

  /** In-flight tool-call id, or `null` when idle. */
  currentToolCallId: () => string | null

  // -------------------------------------------------------------------------
  // Input buffer probe
  // -------------------------------------------------------------------------

  /** `true` when the InputBar buffer is empty (FR-014 guard for ctrl+d). */
  isBufferEmpty: () => boolean

  // -------------------------------------------------------------------------
  // Permission v2 accessors (Spec 033)
  // -------------------------------------------------------------------------

  getPermissionMode: () => PermissionMode
  setPermissionMode: (mode: PermissionMode) => void
  hasPendingIrreversibleAction: () => boolean

  // -------------------------------------------------------------------------
  // Draft accessors (Chat-context history navigation)
  // -------------------------------------------------------------------------

  readDraft: () => string
  setDraft: (value: string) => void

  // -------------------------------------------------------------------------
  // History sources
  // -------------------------------------------------------------------------

  /** All history entries (current + cross-session) visible to this surface. */
  getHistory: () => ReadonlyArray<HistoryNavigationEntry>
  /** memdir USER consent verdict (true when consent record exists + fresh). */
  memdirUserGranted: boolean
  /** True when the memdir USER tier is reachable on disk. */
  memdirUserAvailable: boolean

  // -------------------------------------------------------------------------
  // History-search overlay wiring (Spec 288 Codex P1 follow-up)
  // -------------------------------------------------------------------------

  /**
   * Snapshot of the current InputBar draft at dispatch time — captured so the
   * overlay can restore it byte-for-byte on `escape` (FR-022).  Read once per
   * `history-search` dispatch rather than closed over because `buildTier1Handlers`
   * is memoised and must not bake a stale draft into its handler bag.
   */
  getCurrentDraft: () => string

  /**
   * App-level setter that mounts / unmounts `<HistorySearchOverlay>`.  The
   * handler hands it the open-request envelope returned by
   * `openHistorySearchOverlay(...)`; passing `null` closes the overlay.  The
   * return value of the pure action is purely declarative — without this
   * setter the overlay stays unmounted and ctrl+r is effectively a no-op
   * (Codex P1 finding at line 295 of the pre-fix handler).
   */
  setOverlayRequest: (request: OverlayOpenRequest | null) => void

  // -------------------------------------------------------------------------
  // Backend-bound deps (usually supplied as stubs during the Spec 288.1 gap)
  // -------------------------------------------------------------------------

  /**
   * Spec 027 cancellation envelope.  Production wiring sends a cancellation
   * frame over stdio; the default stub only logs to stderr.
   */
  cancellation?: CancellationSignal
  /**
   * Spec 024 audit writer.  Production wiring emits a `ToolCallAuditRecord`
   * via the IPC bridge; the default stub logs to stderr and resolves.
   */
  audit?: AuditWriter
  /**
   * Drains the audit queue before `session-exit` fires.  Default stub
   * resolves immediately (no backing queue exists yet).
   */
  flushAudit?: () => Promise<void>
  /**
   * Citizen confirmation prompt shown before exiting mid-loop.  Default stub
   * resolves `true` (direct exit) because the confirmation modal has not been
   * mounted yet — safer than blocking forever on a non-existent UI.
   */
  confirmExit?: () => Promise<boolean>
  /** Process-exit shim — tests inject a non-terminating replacement. */
  processExit?: (code?: number) => never

  /**
   * Spec 288 Codex P1 — IPC bridge close hook.  Invoked before `exit(0)` on
   * the agent-interrupt FIRE branch (double-press ctrl+c) so the backend
   * receives SIGTERM + ≤ 3 s grace (FR-009) instead of being orphaned by a
   * bare `process.exit`.  The legacy `useInput` ctrl+c handler in `tui.tsx`
   * used to own `bridge.close()`; dropping that dual path means the Tier-1
   * `agent-interrupt` handler must own the lifecycle guarantee.  Optional so
   * tests and the onboarding-pre-bridge mount can omit it; rejection is
   * caught by the controller so a stuck bridge cannot trap the citizen in a
   * half-shut session.  Not yet threaded into `session-exit` (ctrl+d) — that
   * path's bridge lifecycle will be tracked by the Spec 288.1 follow-up.
   */
  closeBridge?: () => Promise<void>
}>

// ---------------------------------------------------------------------------
// Default fail-loud stubs for Spec 288.1 gaps
// ---------------------------------------------------------------------------

const CANCEL_STUB_MESSAGE =
  '[cancellation] agent-interrupt fired; Spec 027 cancellation envelope not yet implemented on bridge\n'

const AUDIT_STUB_MESSAGE =
  '[audit] reserved-action write requested; Spec 024 audit writer not yet implemented on bridge\n'

const FLUSH_STUB_MESSAGE =
  '[audit] flushAudit requested; Spec 024 audit writer not yet implemented on bridge\n'

function defaultCancellation(): CancellationSignal {
  // FIXME: Spec 288.1 — wire to bridge.cancelActiveAgentLoop() once the
  // Spec 027 cancellation frame ships.
  return {
    cancelActiveAgentLoop: async (): Promise<void> => {
      process.stderr.write(CANCEL_STUB_MESSAGE)
    },
  }
}

function defaultAudit(): AuditWriter {
  // FIXME: Spec 288.1 — wire to bridge.writeReservedAction() once the
  // Spec 024 ToolCallAuditRecord frame ships.
  return {
    writeReservedAction: async (): Promise<void> => {
      process.stderr.write(AUDIT_STUB_MESSAGE)
    },
  }
}

function defaultFlushAudit(): () => Promise<void> {
  // FIXME: Spec 288.1 — drain the audit queue once the Spec 024 writer exists.
  return async (): Promise<void> => {
    process.stderr.write(FLUSH_STUB_MESSAGE)
  }
}

function defaultConfirmExit(): () => Promise<boolean> {
  // FIXME: Spec 288.1 — mount the exit-confirmation modal and hand that
  // resolver's verdict back here.  Direct exit is preferred over a blocking
  // prompt we cannot satisfy yet.
  return async (): Promise<boolean> => true
}

function defaultProcessExit(): (code?: number) => never {
  // eslint-disable-next-line @typescript-eslint/unbound-method -- bound by reference
  return ((code?: number): never => process.exit(code ?? 0)) as (
    code?: number,
  ) => never
}

// ---------------------------------------------------------------------------
// History adapter for the pure `openHistorySearchOverlay` handler.
// `HistoryEntry` and `HistoryNavigationEntry` share the same shape at the
// type level — the adapter is a no-op pass-through.
// ---------------------------------------------------------------------------

function toHistorySearchEntries(
  nav: ReadonlyArray<HistoryNavigationEntry>,
): ReadonlyArray<HistoryEntry> {
  return nav
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

export type Tier1HandlerOverrides = Readonly<{
  Global: ActionHandlers
  Chat: ActionHandlers
}>

export function buildTier1Handlers(
  deps: Tier1HandlerDeps,
): Tier1HandlerOverrides {
  // ------------------------------------------------------------------------
  // Assemble controller deps
  // ------------------------------------------------------------------------

  const cancellation = deps.cancellation ?? defaultCancellation()
  const audit = deps.audit ?? defaultAudit()
  const flushAudit = deps.flushAudit ?? defaultFlushAudit()
  const confirmExit = deps.confirmExit ?? defaultConfirmExit()
  const processExit = deps.processExit ?? defaultProcessExit()

  // agent-interrupt — FR-012 / FR-013
  const agentInterruptDeps: AgentInterruptDeps = {
    sessionId: deps.sessionId,
    isAgentLoopActive: deps.isAgentLoopActive,
    currentToolCallId: deps.currentToolCallId,
    cancellation,
    audit,
    announcer: deps.announcer,
    // Spec 288 Codex P1 — tear the IPC bridge down before `exit(0)` on the
    // double-press FIRE branch.  See `AgentInterruptDeps.beforeExit` for the
    // contract; omission (tests, onboarding-pre-bridge mount) falls back to a
    // bare `process.exit` so the old behaviour is preserved when no bridge
    // is live.
    ...(deps.closeBridge !== undefined
      ? { beforeExit: deps.closeBridge }
      : {}),
    // Forward the test-injected `processExit` shim to the controller so the
    // FIRE branch does not terminate the test runner when dispatched inside
    // `ink-testing-library`.  Production callers leave `processExit`
    // undefined, in which case the controller defaults to `process.exit`
    // (matches the legacy behaviour).
    ...(deps.processExit !== undefined
      ? { exit: (code: number) => deps.processExit!(code) }
      : {}),
  }
  const agentInterrupt = createAgentInterruptController(agentInterruptDeps)

  // session-exit — FR-014 / FR-015 / SC-006
  const sessionExitDeps: SessionExitDeps = {
    isBufferEmpty: deps.isBufferEmpty,
    isLoopActive: deps.isAgentLoopActive,
    flushAudit,
    announcer: deps.announcer,
    confirmExit,
    processExit,
  }
  const sessionExit = buildSessionExitHandler(sessionExitDeps)

  // permission-mode-cycle — FR-008 / FR-009 / FR-010 / FR-011
  const permissionCycleDeps: PermissionModeCycleDeps = {
    getMode: deps.getPermissionMode,
    setMode: deps.setPermissionMode,
    hasPendingIrreversibleAction: deps.hasPendingIrreversibleAction,
    getSessionId: () => deps.sessionId,
    announcer: deps.announcer,
  }
  const permissionCycle = buildPermissionModeCycleHandler(permissionCycleDeps)

  // history-prev / history-next — FR-017 / FR-018 / FR-019
  const historyNavDeps: HistoryNavigatorDeps = {
    readDraft: deps.readDraft,
    setDraft: deps.setDraft,
    getHistory: deps.getHistory,
    consentState: { memdir_user_granted: deps.memdirUserGranted },
    memdirAvailable: deps.memdirUserAvailable,
    currentSessionId: deps.sessionId,
    announcer: deps.announcer,
  }
  const historyNav = createHistoryNavigator(historyNavDeps)

  // ------------------------------------------------------------------------
  // Build handler bags
  // ------------------------------------------------------------------------

  const globalHandlers: ActionHandlers = {
    'agent-interrupt': () => {
      void agentInterrupt.handle()
    },
    'session-exit': () => {
      void sessionExit()
    },
    'permission-mode-cycle': () => {
      void permissionCycle()
    },
    'history-search': () => {
      // Capture the draft at dispatch time — `getCurrentDraft()` reads live
      // IME buffer state so `escape` can restore it byte-for-byte (FR-022).
      // `readDraft` remains the history-navigation accessor; the two read
      // from the same source today but we keep the surfaces separate so a
      // future overlay-scoped draft (e.g. virtual composition freeze) can
      // diverge without touching history-prev / history-next.
      const request = openHistorySearchOverlay({
        all_entries: toHistorySearchEntries(deps.getHistory()),
        saved_draft: deps.getCurrentDraft(),
        consent: { memdir_user_granted: deps.memdirUserGranted },
        announcer: deps.announcer,
      })
      // Hand the envelope to the app-level state so <HistorySearchOverlay>
      // actually mounts.  Previously we dropped the return value — the
      // action announced itself (FR-030) but the citizen saw nothing
      // (Codex P1 at line 295 of the pre-fix file).
      deps.setOverlayRequest(request)
    },
  }

  const chatHandlers: ActionHandlers = {
    'history-prev': () => {
      historyNav.prev()
    },
    'history-next': () => {
      historyNav.next()
    },
  }

  return Object.freeze({
    Global: globalHandlers,
    Chat: chatHandlers,
  })
}
