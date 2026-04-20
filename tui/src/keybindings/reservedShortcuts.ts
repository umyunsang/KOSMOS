// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/reservedShortcuts.ts (CC 2.1.88, research-use)
// Spec 288 · T008 — KOSMOS reserved-action predicates.
//
// KOSMOS reserves exactly two actions per FR-027 / D6:
//   - `agent-interrupt` (ctrl+c)
//   - `session-exit`    (ctrl+d)
//
// These cannot be remapped or disabled by the citizen's override file. This
// module exposes the reserved predicates consumed by `loadUserBindings.ts`
// (T010) and `validate.ts` (T011). CC's larger reserved-shortcut taxonomy
// (TERMINAL_RESERVED, MACOS_RESERVED) is not ported — KOSMOS only owns the
// two hardcoded interrupts; terminal-OS collisions are a runtime concern
// surfaced through the announcer rather than a registry-build concern.

import { DEFAULT_BINDINGS } from './defaultBindings'
import { type ChordString, type TierOneAction } from './types'

export const RESERVED_ACTIONS: ReadonlySet<TierOneAction> = new Set([
  'agent-interrupt',
  'session-exit',
])

/** FR-027 — `true` when the action MUST NOT appear as a remap target. */
export function isReservedAction(action: TierOneAction): boolean {
  return RESERVED_ACTIONS.has(action)
}

/**
 * FR-028 — `true` when the chord corresponds to a reserved default binding.
 * The registry forbids `null`-unbinding these chords; attempts are silently
 * ignored and the default effective_chord is preserved.
 */
export function isReservedChord(chord: ChordString): boolean {
  for (const entry of DEFAULT_BINDINGS) {
    if (entry.default_chord === chord && entry.reserved) return true
  }
  return false
}
