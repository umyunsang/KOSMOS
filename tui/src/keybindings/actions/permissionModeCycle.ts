// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T034 — `permission-mode-cycle` (shift+tab / alt+m fallback) handler.
//
// Closes #1583 (US4). FR-008 / FR-009 / FR-010 / FR-011 / SC-005.
//
// Contract:
//   - FR-008: shift+tab cycles the Tier 1 Permission Modes in the order
//     plan → default → acceptEdits → bypassPermissions → plan (wrap).
//     The Tier 1 cycle intentionally extends Spec 033's low-risk
//     3-mode cycle (`default → plan → acceptEdits → default`) to expose
//     bypassPermissions to citizens directly. The handler gates the
//     bypassPermissions step behind the irreversible-action flag so the
//     Tier 1 surface never bypasses Spec 033's safety spectrum.
//   - FR-009: cycling into bypassPermissions is blocked whenever the
//     session carries an outstanding irreversible-action flag. On block,
//     the mode HOLDS at the previous step and a citizen-readable notice
//     is announced. The resolver's `blocked/permission-mode-blocked`
//     result carries the FR-034 blocked-reason span attribute; this
//     handler's own return carries the same discriminant.
//   - FR-010: the mode-indicator update pathway fires within 200 ms of
//     dispatch. The handler invokes `setMode` synchronously before the
//     span emit, so the status bar re-renders on the next React tick.
//   - FR-011: Spec 033's ModeCycle is the sole authority on permitted
//     transitions. The handler is a thin adapter — it does NOT hard-
//     code transition validity; it delegates the irreversible-action
//     check to the injected probe (which reads Spec 033 state) and
//     computes next-mode via a deterministic Tier 1 ordering.
//   - FR-030: successful dispatches announce the new mode within 1 s
//     (polite priority); blocks announce the reason (assertive priority
//     so the screen reader interrupts).
//   - OTel: on success the handler invokes Spec 033's
//     `emitModeChangedOtel` which produces a
//     `permission.mode.changed` span carrying `kosmos.permission.to_mode`
//     etc. This satisfies the spec's FR-010 span-attribute requirement
//     without adding a new JS telemetry dependency (SC-008).
//
// Test surface: the handler is exposed as a pure builder (no module-
// level state). `computeTier1NextMode` is exported separately so the
// cycle ordering is independently unit-testable.

import { emitModeChangedOtel } from '../../permissions/otelEmit'
import type { PermissionMode } from '../../permissions/types'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../types'

// ---------------------------------------------------------------------------
// Cycle ordering — FR-008
// ---------------------------------------------------------------------------

/**
 * Tier 1 cycle sequence — `plan → default → acceptEdits →
 * bypassPermissions → plan`. Modes outside the cycle (`dontAsk`) return
 * to the front of the cycle (`plan`), matching Spec 033's S1 escape-
 * hatch spirit.
 */
const TIER_1_CYCLE: readonly PermissionMode[] = [
  'plan',
  'default',
  'acceptEdits',
  'bypassPermissions',
] as const

export function computeTier1NextMode(current: PermissionMode): PermissionMode {
  const idx = TIER_1_CYCLE.indexOf(current)
  if (idx === -1) {
    // Off-cycle (dontAsk) — return to the front of the Tier 1 cycle.
    return TIER_1_CYCLE[0]!
  }
  const nextIdx = (idx + 1) % TIER_1_CYCLE.length
  return TIER_1_CYCLE[nextIdx]!
}

// ---------------------------------------------------------------------------
// Result surface
// ---------------------------------------------------------------------------

export type PermissionModeCycleResult =
  | Readonly<{ kind: 'cycled'; fromMode: PermissionMode; toMode: PermissionMode }>
  | Readonly<{
      kind: 'blocked'
      reason: 'permission-mode-blocked'
      attemptedMode: PermissionMode
    }>

// ---------------------------------------------------------------------------
// Dependencies
// ---------------------------------------------------------------------------

export type ModeChangedSpanArgs = Readonly<{
  fromMode: PermissionMode
  toMode: PermissionMode
  trigger: 'shift_tab'
  confirmed: boolean
  sessionId: string
}>

export type PermissionModeCycleDeps = Readonly<{
  /** Current Permission Mode — typically lifted from the session store. */
  getMode: () => PermissionMode
  /** Session-store setter — invoked synchronously for the 200 ms SLO. */
  setMode: (mode: PermissionMode) => void
  /**
   * Returns `true` when the session has an outstanding irreversible
   * action (Spec 033 ConsentRecord with `is_irreversible=true` awaiting
   * execution, OR a pending 정부24 submission flag). Controlled by the
   * Spec 033 permission-pipeline state — the handler does NOT consult
   * the raw state directly per FR-011.
   */
  hasPendingIrreversibleAction: () => boolean
  /** Session id threaded into the OTel span envelope. */
  getSessionId: () => string
  /** Screen-reader announcer (FR-030). */
  announcer: AccessibilityAnnouncer
  /**
   * OTel span emitter — defaults to Spec 033's `emitModeChangedOtel`.
   * Tests substitute a spy to assert attribute contents without
   * cluttering stderr.
   */
  emitSpan?: (args: ModeChangedSpanArgs) => void
}>

// ---------------------------------------------------------------------------
// Announcement helpers
// ---------------------------------------------------------------------------

function announce(
  announcer: AccessibilityAnnouncer,
  message: string,
  priority: AnnouncementPriority,
): void {
  announcer.announce(message, { priority })
}

function formatSuccess(toMode: PermissionMode): string {
  return `권한 모드를 ${toMode}(으)로 변경했습니다.`
}

const BYPASS_BLOCK_MESSAGE =
  '되돌릴 수 없는 작업이 진행 중이라 bypassPermissions로 전환할 수 없습니다. 작업 완료 후 다시 시도하세요.'

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildPermissionModeCycleHandler(
  deps: PermissionModeCycleDeps,
): () => Promise<PermissionModeCycleResult> {
  const emit = deps.emitSpan ?? emitModeChangedOtel

  return async function permissionModeCycleHandler(): Promise<PermissionModeCycleResult> {
    const fromMode = deps.getMode()
    const toMode = computeTier1NextMode(fromMode)

    // FR-009 / SC-005 — block the bypassPermissions transition when an
    // irreversible action is pending. The handler holds at the previous
    // step; the status bar does NOT update.
    if (
      toMode === 'bypassPermissions' &&
      deps.hasPendingIrreversibleAction()
    ) {
      announce(deps.announcer, BYPASS_BLOCK_MESSAGE, 'assertive')
      return Object.freeze({
        kind: 'blocked',
        reason: 'permission-mode-blocked',
        attemptedMode: toMode,
      })
    }

    // FR-010 — setMode synchronously so the status bar re-renders on
    // the next React tick (well under the 200 ms SLO).
    deps.setMode(toMode)

    // FR-030 — announce the new mode. Polite priority — successful
    // cycles are non-urgent.
    announce(deps.announcer, formatSuccess(toMode), 'polite')

    // FR-010 / SC-008 — emit the permission.mode.changed span through
    // the existing Spec 033 stderr-JSONL bridge. No new JS OTel dep.
    try {
      emit({
        fromMode,
        toMode,
        trigger: 'shift_tab',
        confirmed: true,
        sessionId: deps.getSessionId(),
      })
    } catch {
      // Telemetry MUST NEVER crash the handler — swallow.
    }

    return Object.freeze({ kind: 'cycled', fromMode, toMode })
  }
}
