// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Regression — user overrides keyed on `meta+<key>` must match
// the `alt+<key>` ChordEvent the matcher emits for Ink's collapsed meta
// flag. Guards against Codex P2 on PR #1591 where the parser accepted
// `meta` as a distinct modifier while the matcher always emitted `alt`,
// silently breaking customisation for all meta-keyed remaps.
//
// Fix: `parseChord()` normalises `meta` → `alt` at parse time so
// loader-accepted strings and matcher-emitted events agree on a single
// canonical form (the KOSMOS invariant).

import { describe, expect, test } from 'bun:test'
import { loadUserBindings } from '../../src/keybindings/loadUserBindings'
import { buildChordEvent, type InkKeyLike } from '../../src/keybindings/match'
import { parseChord } from '../../src/keybindings/chord'

function blankKey(over: Partial<InkKeyLike> = {}): InkKeyLike {
  return { ctrl: false, shift: false, meta: false, ...over }
}

describe('meta → alt normalisation — loader + matcher agreement', () => {
  test('user override `{"meta+k": "history-search"}` matches an Ink meta=true, input=k event', () => {
    // 1. Citizen writes `meta+k` in their override file.
    const result = loadUserBindings({
      path: '<test:meta-k-remap>',
      readFile: () => '{"meta+k": "history-search"}',
      onWarning: () => {
        /* swallow — no warnings expected for a valid chord + action */
      },
    })
    // The override is accepted (no warnings — `meta+k` is valid syntax).
    expect(result.warnings.length).toBe(0)

    // 2. The effective chord stored on the entry is the canonical form
    //    `alt+k`, because `parseChord()` normalised `meta` at parse time.
    const entry = result.bindings.get('history-search')
    expect(entry).not.toBeUndefined()
    expect(entry!.effective_chord).not.toBeNull()
    expect(String(entry!.effective_chord)).toBe('alt+k')

    // 3. The default `ctrl+r` chord no longer points to history-search.
    expect(
      result.effective_chord_to_action.has(parseChord('ctrl+r')),
    ).toBe(false)

    // 4. The matcher synthesises `alt+k` from an Ink meta=true event.
    const ev = buildChordEvent('k', blankKey({ meta: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('alt+k')

    // 5. End-to-end parity: the event's chord is registered in the
    //    loader's effective map — so the resolver will dispatch the
    //    remapped action instead of silently dropping the keystroke.
    expect(result.effective_chord_to_action.get(ev!.chord)).toBe(
      'history-search',
    )
  })

  test('`meta+k` and `alt+k` overrides are semantically identical', () => {
    // Both spellings parse to the same ChordString and the matcher emits
    // the same chord for the same keystroke — so the choice of spelling
    // in the override file is purely stylistic.
    const metaOverride = loadUserBindings({
      path: '<test:meta-override>',
      readFile: () => '{"meta+k": "history-search"}',
      onWarning: () => {},
    })
    const altOverride = loadUserBindings({
      path: '<test:alt-override>',
      readFile: () => '{"alt+k": "history-search"}',
      onWarning: () => {},
    })

    const metaEntry = metaOverride.bindings.get('history-search')
    const altEntry = altOverride.bindings.get('history-search')

    expect(metaEntry?.effective_chord).toBe(altEntry?.effective_chord!)
    expect(String(metaEntry?.effective_chord)).toBe('alt+k')
  })

  test('`meta+<non-letter>` overrides (digits, named keys) also normalise', () => {
    // Regression guard: the normalisation applies uniformly — not just to
    // letters. Citizens might remap `meta+3` or `meta+pageup`.
    const result = loadUserBindings({
      path: '<test:meta-digit>',
      readFile: () => '{"meta+3": "history-prev"}',
      onWarning: () => {},
    })
    const entry = result.bindings.get('history-prev')
    expect(String(entry?.effective_chord)).toBe('alt+3')

    const ev = buildChordEvent('3', blankKey({ meta: true }))
    expect(String(ev!.chord)).toBe('alt+3')
    expect(result.effective_chord_to_action.get(ev!.chord)).toBe(
      'history-prev',
    )
  })

  test('`meta+ctrl+shift+k` collapses meta into alt while preserving other modifiers', () => {
    // Multi-modifier chord with meta — the other modifiers must round-trip
    // intact; only meta is rewritten.
    const result = loadUserBindings({
      path: '<test:complex>',
      readFile: () => '{"meta+ctrl+shift+k": "history-search"}',
      onWarning: () => {},
    })
    const entry = result.bindings.get('history-search')
    expect(String(entry?.effective_chord)).toBe('ctrl+shift+alt+k')
  })
})
