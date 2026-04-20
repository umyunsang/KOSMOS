// SPDX-License-Identifier: Apache-2.0
// Source: specs/288-shortcut-tier1-port/contracts/keybinding-schema.ts (Spec 288)
//
// Verbatim copy of the contract type surface. This file is the source of
// truth for every consumer in tui/src/keybindings/ and tui/src/components/
// history/. Any deviation between this file and the contract is a Spec 288
// violation. Re-exported from ./index.ts.
//
// The runtime registry/resolver/announcer ports (T012/T013/T014/T015) live
// in sibling files; this module contributes only the types they implement.

// -----------------------------------------------------------------------------
// Context enum — narrowed subset of CC's 18 contexts
// -----------------------------------------------------------------------------

export const KEYBINDING_CONTEXTS = [
  'Global',
  'Chat',
  'HistorySearch',
  'Confirmation',
] as const
export type KeybindingContext = (typeof KEYBINDING_CONTEXTS)[number]

export const KEYBINDING_CONTEXT_DESCRIPTIONS: Record<
  KeybindingContext,
  string
> = {
  Global: '전역 — 상위 컨텍스트에 의해 클레임되지 않은 경우 항상 활성',
  Chat: 'InputBar 포커스 상태',
  HistorySearch: 'ctrl+r 이력 검색 오버레이 열림 상태',
  Confirmation: 'PermissionGauntletModal 또는 ConsentPrompt 열림 상태',
}

// -----------------------------------------------------------------------------
// Tier 1 action enum — exactly seven actions
// -----------------------------------------------------------------------------

export const TIER_ONE_ACTIONS = [
  'agent-interrupt',
  'session-exit',
  'draft-cancel',
  'history-search',
  'history-prev',
  'history-next',
  'permission-mode-cycle',
] as const
export type TierOneAction = (typeof TIER_ONE_ACTIONS)[number]

// -----------------------------------------------------------------------------
// Chord grammar — mirrors CC parser.ts
// -----------------------------------------------------------------------------

export type Modifier = 'ctrl' | 'shift' | 'alt' | 'meta'
export const MODIFIER_ORDER: readonly Modifier[] = [
  'ctrl',
  'shift',
  'alt',
  'meta',
] as const

// Branded string. Construct via parser.ts (Lead-owned, T004); this module
// only narrows from `string` for type-flow. The `__brand` is unique-symbol
// so unsafe casts are caught at compile time.
declare const CHORD_BRAND: unique symbol
export type ChordString = string & { readonly [CHORD_BRAND]: 'ChordString' }

// -----------------------------------------------------------------------------
// KeybindingEntry — one row in the registry
// -----------------------------------------------------------------------------

export type KeybindingEntry = Readonly<{
  action: TierOneAction
  default_chord: ChordString
  effective_chord: ChordString | null
  context: KeybindingContext
  description: string
  remappable: boolean
  reserved: boolean
  mutates_buffer: boolean
}>

// -----------------------------------------------------------------------------
// Runtime event + resolution
// -----------------------------------------------------------------------------

export type ChordEvent = Readonly<{
  raw: string
  chord: ChordString
  ctrl: boolean
  shift: boolean
  alt: boolean
  meta: boolean
  timestamp: number
}>

export type BlockedReason =
  | 'ime-composing'
  | 'buffer-non-empty'
  | 'permission-mode-blocked'
  | 'consent-out-of-scope'

export type ResolutionResult =
  | Readonly<{
      kind: 'dispatched'
      action: TierOneAction
      context: KeybindingContext
    }>
  | Readonly<{ kind: 'blocked'; action: TierOneAction; reason: BlockedReason }>
  | Readonly<{ kind: 'no-match' }>
  | Readonly<{
      kind: 'double-press-armed'
      action: TierOneAction
      expires_at: number
    }>
  | Readonly<{ kind: 'double-press-fired'; action: TierOneAction }>

// -----------------------------------------------------------------------------
// Registry surface — consumed by useKeybinding hook (T018)
// -----------------------------------------------------------------------------

export interface KeybindingRegistry {
  readonly entries: ReadonlyMap<TierOneAction, KeybindingEntry>
  lookupByChord(
    chord: ChordString,
    context: KeybindingContext,
  ): KeybindingEntry | null
  describe(action: TierOneAction): string
}

// -----------------------------------------------------------------------------
// User override loader contract
// -----------------------------------------------------------------------------

export type UserOverrideEntry = {
  chord: ChordString
  action: TierOneAction | null
}

export interface UserOverrideLoader {
  load(path: string): ReadonlyArray<UserOverrideEntry>
  // Contract: MUST NOT throw on missing/invalid file (FR-023, FR-024).
  //          Parse errors logged; defaults applied.
}

// -----------------------------------------------------------------------------
// Accessibility announcer contract (KWCAG 2.1 § 4.1.3)
// -----------------------------------------------------------------------------

export type AnnouncementPriority = 'polite' | 'assertive'

export interface AccessibilityAnnouncer {
  announce(
    message: string,
    options?: { priority?: AnnouncementPriority },
  ): void
  // Contract: message MUST reach the screen-reader channel within 1 s (FR-030).
}

// -----------------------------------------------------------------------------
// Audit + cancellation integration contracts
// -----------------------------------------------------------------------------

export type ReservedActionAuditPayload = Readonly<{
  event_type: 'user-interrupted' | 'session-exited'
  session_id: string
  interrupted_tool_call_id?: string
}>

export interface AuditWriter {
  writeReservedAction(payload: ReservedActionAuditPayload): Promise<void>
}

export interface CancellationSignal {
  cancelActiveAgentLoop(session_id: string): Promise<void>
}
