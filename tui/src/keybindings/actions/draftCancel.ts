// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T030 — `draft-cancel` action handler (User Story 3).
//
// FR-005 / FR-007 — the resolver already short-circuits `draft-cancel` while
// `useKoreanIME().isComposing === true` (mutates_buffer guard in resolver.ts
// T014).  This handler is the citizen-safety backstop per tasks.md T030:
//
//   > clears InputBar buffer on empty-IME state; no-op when composing
//   > (resolver already gates, but handler-level assertion catches
//   > regressions).  FR-005.
//
// The handler is pure — it reads a snapshot of buffer + composition state
// through injectable getters so the same function drives unit tests and
// the Ink runtime (T031 `InputBar.tsx` refactor).
//
// Handler outcome is announced to screen readers (FR-030) only on an
// actual clear — empty-draft or mid-composition paths are benign and
// emit neither an audit event nor an announcement (data-model.md §
// "Empty-buffer escape = no action fires and no audit record").

import { type AccessibilityAnnouncer } from '../types'

// ---------------------------------------------------------------------------
// Dependencies
// ---------------------------------------------------------------------------

export type DraftCancelDeps = Readonly<{
  /** Current committed input buffer text. */
  readDraft: () => string
  /** True while `useKoreanIME` has an in-flight partial syllable. */
  isComposing: () => boolean
  /** Clear both committed + composition state (InputBar wires `ime.clear`). */
  clearDraft: () => void
  /** Announce the clear — only fires on the cleared outcome per FR-030. */
  announcer: AccessibilityAnnouncer
}>

// ---------------------------------------------------------------------------
// Outcomes
// ---------------------------------------------------------------------------

export type DraftCancelOutcome =
  | Readonly<{ kind: 'cleared' }>
  | Readonly<{ kind: 'ignored-empty' }>
  | Readonly<{ kind: 'ignored-composing' }>

// ---------------------------------------------------------------------------
// Announcement text (Korean-first, bilingual)
// ---------------------------------------------------------------------------

const CLEARED_MESSAGE = '입력 초안을 비웠습니다. / Input draft cleared.'

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

export function cancelDraft(deps: DraftCancelDeps): DraftCancelOutcome {
  // FR-005 / FR-007 backstop — if the resolver was bypassed, still no-op.
  if (deps.isComposing()) {
    return Object.freeze({ kind: 'ignored-composing' })
  }
  const draft = deps.readDraft()
  if (draft.length === 0) {
    // Spec 288 data-model § 7 "ignored" path: no audit, no announce.
    return Object.freeze({ kind: 'ignored-empty' })
  }
  deps.clearDraft()
  deps.announcer.announce(CLEARED_MESSAGE, { priority: 'polite' })
  return Object.freeze({ kind: 'cleared' })
}
