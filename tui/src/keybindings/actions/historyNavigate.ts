// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T036 — `history-prev` / `history-next` action handlers
// (User Story 5).
//
// Closes #1582 / #1583.  FR-017 / FR-018 / FR-019.
//
// The navigator keeps a cursor into the citizen's query history and moves
// it in response to `prev` / `next` calls.  The cursor is session-lifetime
// in-memory state — it does not leak across the process boundary.
//
// Behaviour matrix (from data-model.md § History cursor):
//
//   state                         │ prev                  │ next
//   ──────────────────────────────┼───────────────────────┼────────────
//   buffer non-empty              │ pass-through          │ pass-through
//   buffer empty, cursor at none  │ load newest           │ at-present
//   buffer empty, cursor mid-list │ load older            │ load newer
//   buffer empty, cursor oldest   │ at-bound              │ load newer
//   buffer empty, cursor newest   │ load older            │ returned-to-
//                                  │                       │ present
//
// Consent scoping (FR-019):
//   - Without memdir USER consent OR when the memdir USER tier is unavailable
//     entirely (graceful degradation per Spec 288 assumptions / scope
//     boundaries), only `current-session` entries are traversable.  `prev`
//     pressed at the current-session boundary returns `at-scope-boundary` +
//     an assertive announcement explaining why.
//   - With consent AND memdir available, the first step that moves from a
//     current-session entry to a prior-session entry emits an assertive
//     crossing notice so the citizen knows they are now reading older data.

import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../types'

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------

export type HistoryNavigationEntry = Readonly<{
  query_text: string
  timestamp: string
  session_id: string
  consent_scope: 'current-session' | 'cross-session'
}>

export type HistoryConsentState = Readonly<{
  memdir_user_granted: boolean
}>

export type HistoryNavigatorDeps = Readonly<{
  /** Current committed draft text — determines pass-through vs load. */
  readDraft: () => string
  /** Write `value` into the draft (InputBar-level setter). */
  setDraft: (value: string) => void
  /**
   * Entire history accessible to the layer (current + cross-session where
   * present).  The navigator applies the consent filter internally.
   */
  getHistory: () => ReadonlyArray<HistoryNavigationEntry>
  /** memdir USER consent decision. */
  consentState: HistoryConsentState
  /**
   * True when the memdir USER tier is physically available (Epic D #1299
   * landed) — when false, cross-session entries are treated as out-of-scope
   * regardless of the consent flag per graceful-degradation rule.
   */
  memdirAvailable: boolean
  /** Used to classify entries at runtime when sorting/filtering. */
  currentSessionId: string
  announcer: AccessibilityAnnouncer
}>

// ---------------------------------------------------------------------------
// Outcomes
// ---------------------------------------------------------------------------

export type HistoryPrevOutcome =
  | Readonly<{ kind: 'loaded'; entry: HistoryNavigationEntry }>
  | Readonly<{ kind: 'crossed-scope'; entry: HistoryNavigationEntry }>
  | Readonly<{ kind: 'at-bound' }>
  | Readonly<{ kind: 'at-scope-boundary' }>
  | Readonly<{ kind: 'empty' }>
  | Readonly<{ kind: 'pass-through' }>

export type HistoryNextOutcome =
  | Readonly<{ kind: 'loaded'; entry: HistoryNavigationEntry }>
  | Readonly<{ kind: 'returned-to-present' }>
  | Readonly<{ kind: 'at-present' }>
  | Readonly<{ kind: 'pass-through' }>

// ---------------------------------------------------------------------------
// Controller
// ---------------------------------------------------------------------------

export interface HistoryNavigator {
  prev(): HistoryPrevOutcome
  next(): HistoryNextOutcome
  reset(): void
  /** Current cursor — null when the draft is at the present. */
  readonly cursor: number | null
}

// ---------------------------------------------------------------------------
// Announcement text
// ---------------------------------------------------------------------------

const LOAD_PREV_MSG = '이전 질문을 불러왔습니다. / Previous query loaded.'
const LOAD_NEXT_MSG = '다음 질문을 불러왔습니다. / Next query loaded.'
const RETURN_PRESENT_MSG =
  '입력창이 현재로 돌아왔습니다. / Draft returned to present.'
const CROSSED_SCOPE_MSG =
  '이전 세션의 질문을 불러왔습니다. / Now reading a prior-session entry.'
const SCOPE_BOUNDARY_DECLINED_MSG =
  '이전 세션 이력은 메모리 동의가 필요합니다. / Prior-session history requires memdir consent.'
const SCOPE_BOUNDARY_MEMDIR_ABSENT_MSG =
  '이전 세션 이력을 사용할 수 없습니다. / Prior-session history is unavailable.'

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

export function createHistoryNavigator(
  deps: HistoryNavigatorDeps,
): HistoryNavigator {
  // Cursor points at the index into `scopedEntries()` of the currently
  // displayed entry.  null ⇒ draft is at the present (no entry loaded).
  let cursor: number | null = null

  // History mode is entered as soon as a prev/next press loads an entry
  // from an empty buffer.  Subsequent prev/next presses stay in history
  // mode — the draft is considered "loaded history" rather than "user
  // typed text" so FR-017 pass-through does NOT apply until the citizen
  // either submits, presses `draft-cancel`, or manually returns to the
  // present via repeated `next` (triggers the `returned-to-present`
  // branch which also clears history-mode).
  let inHistoryMode = false

  function scopedEntries(): ReadonlyArray<HistoryNavigationEntry> {
    return deps.getHistory()
  }

  function crossScopeAllowed(): boolean {
    return deps.memdirAvailable && deps.consentState.memdir_user_granted
  }

  function reachableEntries(): ReadonlyArray<HistoryNavigationEntry> {
    const raw = scopedEntries()
    if (crossScopeAllowed()) return raw
    return raw.filter((e) => e.consent_scope === 'current-session')
  }

  function announce(
    message: string,
    priority: AnnouncementPriority = 'polite',
  ): void {
    deps.announcer.announce(message, { priority })
  }

  function loadEntryAt(index: number): HistoryNavigationEntry {
    const scoped = reachableEntries()
    const entry = scoped[index]
    if (entry === undefined) {
      throw new Error(
        `history cursor out of range: ${index} (len=${scoped.length})`,
      )
    }
    deps.setDraft(entry.query_text)
    return entry
  }

  return {
    get cursor() {
      return cursor
    },

    reset() {
      cursor = null
      inHistoryMode = false
    },

    prev(): HistoryPrevOutcome {
      // FR-017 — pass through when the buffer is non-empty AND we are not
      // already navigating history.  (User-typed text must never be
      // overwritten by a prev press; history-loaded text, however, is
      // navigable further back.)
      if (!inHistoryMode && deps.readDraft().length > 0) {
        return Object.freeze({ kind: 'pass-through' })
      }

      const scoped = reachableEntries()
      if (scoped.length === 0) {
        // Distinguish "no scoped history at all" from "blocked by scope".
        // If the raw history has cross-session entries but we filtered them
        // out, surface that as an at-scope-boundary so the citizen sees why.
        const raw = scopedEntries()
        if (raw.length > 0 && raw.some((e) => e.consent_scope === 'cross-session')) {
          const msg = deps.memdirAvailable
            ? SCOPE_BOUNDARY_DECLINED_MSG
            : SCOPE_BOUNDARY_MEMDIR_ABSENT_MSG
          announce(msg, 'assertive')
          return Object.freeze({ kind: 'at-scope-boundary' })
        }
        return Object.freeze({ kind: 'empty' })
      }

      // From the present we load the newest scoped entry.
      if (cursor === null) {
        const nextIdx = scoped.length - 1
        const entry = loadEntryAt(nextIdx)
        cursor = nextIdx
        inHistoryMode = true
        announce(LOAD_PREV_MSG, 'polite')
        return Object.freeze({ kind: 'loaded', entry })
      }

      if (cursor === 0) {
        // Already at oldest scoped entry — either we hold (no more scoped
        // history) or we would cross the scope boundary.
        const raw = scopedEntries()
        const olderCrossSession = raw.some(
          (e) =>
            e.consent_scope === 'cross-session' &&
            !reachableEntries().includes(e),
        )
        if (olderCrossSession) {
          const msg = deps.memdirAvailable
            ? SCOPE_BOUNDARY_DECLINED_MSG
            : SCOPE_BOUNDARY_MEMDIR_ABSENT_MSG
          announce(msg, 'assertive')
          return Object.freeze({ kind: 'at-scope-boundary' })
        }
        return Object.freeze({ kind: 'at-bound' })
      }

      // Normal step backward.
      const nextIdx = cursor - 1
      const prevEntry = scoped[cursor]
      const newEntry = loadEntryAt(nextIdx)
      cursor = nextIdx

      // FR-019 scope-crossing notice — fires only when the current step
      // transitions from a current-session entry into a cross-session one.
      const crossing =
        prevEntry !== undefined &&
        prevEntry.consent_scope === 'current-session' &&
        newEntry.consent_scope === 'cross-session'
      if (crossing) {
        announce(CROSSED_SCOPE_MSG, 'assertive')
        return Object.freeze({ kind: 'crossed-scope', entry: newEntry })
      }
      announce(LOAD_PREV_MSG, 'polite')
      return Object.freeze({ kind: 'loaded', entry: newEntry })
    },

    next(): HistoryNextOutcome {
      // FR-018 — pass through when the buffer carries user-typed text.
      // Once we are navigating history, `next` is the return path.
      if (!inHistoryMode && deps.readDraft().length > 0) {
        return Object.freeze({ kind: 'pass-through' })
      }
      if (cursor === null) {
        return Object.freeze({ kind: 'at-present' })
      }
      const scoped = reachableEntries()
      const nextIdx = cursor + 1
      if (nextIdx >= scoped.length) {
        // Return to present — clear the draft, drop history mode.
        deps.setDraft('')
        cursor = null
        inHistoryMode = false
        announce(RETURN_PRESENT_MSG, 'polite')
        return Object.freeze({ kind: 'returned-to-present' })
      }
      const entry = loadEntryAt(nextIdx)
      cursor = nextIdx
      announce(LOAD_NEXT_MSG, 'polite')
      return Object.freeze({ kind: 'loaded', entry })
    },
  }
}
