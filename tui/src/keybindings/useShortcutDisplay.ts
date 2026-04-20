// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/useShortcutDisplay.ts (CC 2.1.88, research-use)
// Spec 288 · T019 — React hook returning the effective chord for an action.
//
// Renders help-surface text like "이전 질문 불러오기 (↑)" and lets the
// HistorySearchOverlay / PermissionGauntletModal show the live chord the
// citizen would press next.

import { useKeybindingSurfaces } from './KeybindingContext'
import { type ChordString, type TierOneAction } from './types'

export function useShortcutDisplay(action: TierOneAction): ChordString | null {
  const { registry } = useKeybindingSurfaces()
  const entry = registry.entries.get(action)
  if (entry === undefined) return null
  return entry.effective_chord
}
