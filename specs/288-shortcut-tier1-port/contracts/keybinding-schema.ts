/**
 * Contract: Keybinding Registry Type Surface (Spec 288)
 *
 * This file is the authoritative type contract for the Tier 1 keybinding port.
 * Any deviation between the runtime registry and these types is a spec violation.
 *
 * Shape parity target (SC-009): ≥ 80% identical to:
 *   .references/claude-code-sourcemap/restored-src/src/keybindings/schema.ts
 *   .references/claude-code-sourcemap/restored-src/src/keybindings/types.ts
 *
 * Zero new runtime dependencies (SC-008, AGENTS.md hard rule).
 */

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

export const KEYBINDING_CONTEXT_DESCRIPTIONS: Record<KeybindingContext, string> = {
  Global: '전역 — 상위 컨텍스트에 의해 클레임되지 않은 경우 항상 활성',
  Chat: 'InputBar 포커스 상태',
  HistorySearch: 'ctrl+r 이력 검색 오버레이 열림 상태',
  Confirmation: 'PermissionGauntletModal 또는 ConsentPrompt 열림 상태',
}

// -----------------------------------------------------------------------------
// Tier 1 action enum — exactly seven actions (mode-cycle includes Windows fallback)
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
// Chord grammar — port of CC parser.ts
// -----------------------------------------------------------------------------

export type Modifier = 'ctrl' | 'shift' | 'alt' | 'meta'

export const MODIFIER_ORDER: readonly Modifier[] = ['ctrl', 'shift', 'alt', 'meta'] as const

export type ChordString = string & { readonly __brand: unique symbol }

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

// Invariants checked at registry-build time:
//   reserved === true  ⟹  remappable === false
//   effective_chord === null ⟹ reserved === false (FR-028)

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
  | Readonly<{ kind: 'dispatched'; action: TierOneAction; context: KeybindingContext }>
  | Readonly<{ kind: 'blocked'; action: TierOneAction; reason: BlockedReason }>
  | Readonly<{ kind: 'no-match' }>
  | Readonly<{ kind: 'double-press-armed'; action: TierOneAction; expires_at: number }>
  | Readonly<{ kind: 'double-press-fired'; action: TierOneAction }>

// -----------------------------------------------------------------------------
// Registry surface — exposed to consumers via useKeybinding hook
// -----------------------------------------------------------------------------

export interface KeybindingRegistry {
  readonly entries: ReadonlyMap<TierOneAction, KeybindingEntry>
  lookupByChord(chord: ChordString, context: KeybindingContext): KeybindingEntry | null
  describe(action: TierOneAction): string
}

// -----------------------------------------------------------------------------
// User override loader contract
// -----------------------------------------------------------------------------

export type UserOverrideEntry = { chord: ChordString; action: TierOneAction | null }

export interface UserOverrideLoader {
  load(path: string): ReadonlyArray<UserOverrideEntry>
  // Contract: MUST NOT throw on missing/invalid file (FR-023, FR-024).
  //          Parse errors logged; defaults applied.
}

// -----------------------------------------------------------------------------
// Accessibility announcer contract (KWCAG 2.1 § 4.1.3)
// -----------------------------------------------------------------------------

export interface AccessibilityAnnouncer {
  announce(message: string, options?: { priority?: 'polite' | 'assertive' }): void
  // Contract: message MUST reach the screen-reader channel within 1 s (FR-030).
}

// -----------------------------------------------------------------------------
// Audit + cancellation integration contracts (consumed, not implemented here)
// -----------------------------------------------------------------------------

export type ReservedActionAuditPayload = Readonly<{
  event_type: 'user-interrupted' | 'session-exited'
  session_id: string
  interrupted_tool_call_id?: string
}>

export interface AuditWriter {
  // Port of Spec 024 ToolCallAuditRecord writer — contract only.
  writeReservedAction(payload: ReservedActionAuditPayload): Promise<void>
}

export interface CancellationSignal {
  // Port of Spec 027 mailbox-based cancellation envelope.
  cancelActiveAgentLoop(session_id: string): Promise<void>
}
