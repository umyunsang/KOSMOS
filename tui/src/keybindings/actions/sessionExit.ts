// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T028 — `session-exit` (ctrl+d) action handler (User Story 2).
//
// Closes #1578. FR-014 / FR-015 / FR-016 / SC-006.
//
// Contract:
//   - FR-014: keystroke is IGNORED while the input buffer contains text
//     (citizen-safety rule — prevents accidental exit mid-typing).
//   - FR-015: when the buffer is empty and an agent loop is active, the
//     handler requests citizen confirmation before exiting; on decline,
//     the exit is aborted and the cancellation is announced.
//   - FR-015: when the buffer is empty and no loop is active (OR the
//     citizen confirmed the exit), the handler drains the audit queue
//     BEFORE invoking `process.exit(0)`. The drain MUST complete before
//     exit fires so no in-flight audit record is lost (SC-006).
//   - FR-015: on audit-flush failure, the handler still exits — a
//     half-shut session would trap the citizen (parallels the resolver's
//     FR-013 robustness rule).
//   - FR-016: detection lives upstream in `match.ts` (raw-byte `\x04`);
//     this module runs only after the resolver has dispatched the
//     `session-exit` action.
//   - FR-030: every successful exit emits an accessibility announcement
//     within 1 s of dispatch. The buffer-non-empty no-op path is silent
//     (mirrors the resolver's benign-block rule).
//
// The handler is exposed as a pure builder. The TUI root wires in the
// real IPC-backed audit writer + raw `process.exit`; tests inject
// in-memory doubles so no actual exit fires. The builder holds no
// internal state — each invocation is independent.

import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../types'

// ---------------------------------------------------------------------------
// Public result surface
// ---------------------------------------------------------------------------

export type SessionExitBlockedReason = 'buffer-non-empty' | 'exit-cancelled'

export type SessionExitResult =
  | Readonly<{ kind: 'exited' }>
  | Readonly<{ kind: 'blocked'; reason: SessionExitBlockedReason }>

// ---------------------------------------------------------------------------
// Injected dependencies
// ---------------------------------------------------------------------------

export type SessionExitDeps = Readonly<{
  /** Returns `true` when the InputBar buffer is empty (FR-014 guard). */
  isBufferEmpty: () => boolean
  /** Returns `true` when an agent loop is currently executing (FR-015). */
  isLoopActive: () => boolean
  /**
   * Drains the audit queue to durable storage. MUST resolve only after
   * every pending record has been flushed; rejection is caught by the
   * handler so the exit path still fires.
   */
  flushAudit: () => Promise<void>
  /** Screen-reader announcer (FR-030). */
  announcer: AccessibilityAnnouncer
  /**
   * Citizen-visible confirmation dialog. Called only when a loop is
   * active. Resolve to `true` to proceed with exit, `false` to cancel.
   */
  confirmExit: () => Promise<boolean>
  /**
   * Actual process-exit call. Injected so tests can substitute a fake.
   * Production wiring passes `process.exit`.
   */
  processExit: (code?: number) => never
}>

// ---------------------------------------------------------------------------
// Announcements — citizen-readable ko + en
// ---------------------------------------------------------------------------

const EXIT_SUCCESS_MESSAGE =
  '세션을 안전하게 종료합니다. 감사 기록을 저장 중입니다.'
const EXIT_CANCELLED_MESSAGE =
  '세션 종료가 취소되었습니다. 에이전트 루프가 계속 진행됩니다.'

function announce(
  announcer: AccessibilityAnnouncer,
  message: string,
  priority: AnnouncementPriority,
): void {
  announcer.announce(message, { priority })
}

// ---------------------------------------------------------------------------
// Builder — returns a per-dispatch async handler
// ---------------------------------------------------------------------------

export function buildSessionExitHandler(
  deps: SessionExitDeps,
): () => Promise<SessionExitResult> {
  return async function sessionExitHandler(): Promise<SessionExitResult> {
    // FR-014 — buffer-empty guard. Silent no-op; the citizen is
    // mid-typing and a screen-reader interruption would be jarring.
    if (!deps.isBufferEmpty()) {
      return Object.freeze({
        kind: 'blocked',
        reason: 'buffer-non-empty',
      })
    }

    // FR-015 — active-loop confirmation prompt.
    if (deps.isLoopActive()) {
      const confirmed = await deps.confirmExit()
      if (!confirmed) {
        announce(deps.announcer, EXIT_CANCELLED_MESSAGE, 'assertive')
        return Object.freeze({
          kind: 'blocked',
          reason: 'exit-cancelled',
        })
      }
    }

    // FR-030 — announce the exit BEFORE the flush so the screen reader
    // has already spoken before the process dies. Polite priority —
    // the citizen initiated the exit deliberately.
    announce(deps.announcer, EXIT_SUCCESS_MESSAGE, 'polite')

    // FR-015 / SC-006 — drain the audit queue BEFORE exit. Flush errors
    // are swallowed so the citizen never gets trapped in a half-shut
    // session; the error is surfaced via stderr for observability.
    try {
      await deps.flushAudit()
    } catch (err) {
      process.stderr.write(
        `[session-exit] audit flush failed: ${(err as Error).message}\n`,
      )
    }

    // FR-015 — actually exit. The return-type `never` keeps downstream
    // code from relying on the post-exit path.
    deps.processExit(0)
    // Unreachable in production; reachable only when tests inject a
    // non-terminating `processExit`. The return satisfies TypeScript.
    return Object.freeze({ kind: 'exited' })
  }
}
