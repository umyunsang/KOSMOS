// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T012 — immutable registry assembler.
//
// `buildRegistry` merges `DEFAULT_BINDINGS` with the user-override loader
// output via `validateEntries` and produces a frozen `KeybindingRegistry`
// whose `lookupByChord` respects context scoping (FR-001 / FR-003).
//
// The registry is constructed exactly once at TUI boot (see
// `KeybindingProviderSetup.tsx`, T017) and is never mutated afterwards.

import { DEFAULT_BINDINGS } from './defaultBindings'
import { loadUserBindings, type LoaderResult } from './loadUserBindings'
import { validateEntries } from './validate'
import {
  type ChordString,
  type KeybindingContext,
  type KeybindingEntry,
  type KeybindingRegistry,
  type TierOneAction,
} from './types'

export type BuildRegistryOptions = {
  /** Override loader result. Defaults to `loadUserBindings()` with default path. */
  loaderResult?: LoaderResult
}

export function buildRegistry(
  options: BuildRegistryOptions = {},
): KeybindingRegistry {
  const result = options.loaderResult ?? loadUserBindings()

  // Merge: defaults provide identity; loader-merged entries (bindings map)
  // override effective_chord where the citizen remapped or disabled.
  const merged: KeybindingEntry[] = []
  for (const def of DEFAULT_BINDINGS) {
    const override = result.bindings.get(def.action)
    merged.push(Object.freeze(override ?? def))
  }

  validateEntries(merged)

  const byAction = new Map<TierOneAction, KeybindingEntry>()
  for (const e of merged) byAction.set(e.action, e)

  // Build the (chord, context) → entry lookup. Disabled entries
  // (effective_chord === null) are excluded. Reserved actions live in
  // context `Global` so they reach the resolver from every surface.
  const byChord = new Map<string, KeybindingEntry>()
  for (const e of merged) {
    if (e.effective_chord === null) continue
    byChord.set(chordKey(e.effective_chord, e.context), e)
  }

  const frozenEntries: ReadonlyMap<TierOneAction, KeybindingEntry> =
    Object.freeze(byAction)

  return Object.freeze<KeybindingRegistry>({
    entries: frozenEntries,
    lookupByChord(chord: ChordString, context: KeybindingContext) {
      const direct = byChord.get(chordKey(chord, context))
      if (direct !== undefined) return direct
      if (context !== 'Global') {
        // Fall through to Global so reserved chords always resolve (FR-016).
        const global = byChord.get(chordKey(chord, 'Global'))
        if (global !== undefined) return global
      }
      return null
    },
    describe(action: TierOneAction): string {
      return byAction.get(action)?.description ?? ''
    },
  })
}

function chordKey(chord: ChordString, context: KeybindingContext): string {
  return `${context}:${chord}`
}
