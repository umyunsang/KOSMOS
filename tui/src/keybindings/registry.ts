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
import { RegistryInvariantError, validateEntries } from './validate'
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
  //
  // Defense-in-depth against reserved-chord collisions (Codex P1 on PR
  // #1591, Spec 025 V6 two-layer pattern): reserved entries populate the
  // map FIRST. If a later non-reserved entry's effective_chord would land
  // on a slot already held by a reserved entry, we throw I4 rather than
  // silently overwrite — loader-layer rejection is the primary guard
  // (`reserved-chord-collision` warning), so reaching this path implies a
  // bypass (e.g. direct `buildRegistry({ loaderResult })` injection with
  // crafted bindings) and must surface loudly. The loader-produced
  // `merged` map is a `ReadonlyMap<TierOneAction, KeybindingEntry>` that
  // the loader guarantees never emits reserved-chord collisions, so this
  // backstop is only exercised by adversarial `loaderResult` overrides.
  const byChord = new Map<string, KeybindingEntry>()
  const reservedFirst: KeybindingEntry[] = []
  const nonReserved: KeybindingEntry[] = []
  for (const e of merged) {
    if (e.reserved) reservedFirst.push(e)
    else nonReserved.push(e)
  }
  for (const e of reservedFirst) {
    if (e.effective_chord === null) continue
    byChord.set(chordKey(e.effective_chord, e.context), e)
  }
  for (const e of nonReserved) {
    if (e.effective_chord === null) continue
    const key = chordKey(e.effective_chord, e.context)
    const direct = byChord.get(key)
    if (direct?.reserved === true) {
      throw new RegistryInvariantError(
        'I4',
        e,
        `non-reserved action ${e.action} cannot remap onto reserved chord ${e.effective_chord} (held by ${direct.action})`,
      )
    }
    // Also refuse to shadow a reserved Global slot when the non-reserved
    // entry uses a non-Global context. The resolver's `lookupByChord`
    // fallback resolves context → Global, so a non-reserved `Chat:ctrl+c`
    // entry would win in Chat context and starve the Global reserved
    // agent-interrupt — same safety violation, different scope.
    if (e.context !== 'Global') {
      const globalKey = chordKey(e.effective_chord, 'Global')
      const globalHolder = byChord.get(globalKey)
      if (globalHolder?.reserved === true) {
        throw new RegistryInvariantError(
          'I4',
          e,
          `non-reserved action ${e.action} in ${e.context} cannot shadow reserved Global chord ${e.effective_chord} (held by ${globalHolder.action})`,
        )
      }
    }
    byChord.set(key, e)
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
