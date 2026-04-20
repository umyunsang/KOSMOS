// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Regression — `MODE_CYCLE_DEFAULT_CHORD` must be a chord string
// the matcher can actually emit. Guards against the Codex P2 finding on
// PR #1591 where the Windows fallback was `meta+m` but `buildChordEvent()`
// canonicalises Ink's collapsed meta flag to the `alt` token, leaving the
// default binding unreachable on Windows fallback terminals.

import { describe, expect, test } from 'bun:test'
import {
  DEFAULT_BINDINGS,
  MODE_CYCLE_DEFAULT_CHORD,
  defaultBindingsByAction,
} from '../../src/keybindings/defaultBindings'
import { buildChordEvent, type InkKeyLike } from '../../src/keybindings/match'
import { parseChord } from '../../src/keybindings/chord'

function blankKey(over: Partial<InkKeyLike> = {}): InkKeyLike {
  return { ctrl: false, shift: false, meta: false, ...over }
}

describe('defaultBindings — MODE_CYCLE_DEFAULT_CHORD', () => {
  test('is one of the two documented fallback chord literals', () => {
    // The Windows fallback path (no VT support for shift+tab) must pick a
    // chord the matcher can produce. `buildChordEvent()` emits the `alt`
    // token for Ink's collapsed meta flag — so `meta+m` would be
    // unreachable. Codex P2 on PR #1591.
    expect(['shift+tab', 'alt+m']).toContain(MODE_CYCLE_DEFAULT_CHORD)
  })

  test('round-trips through buildChordEvent (shift+tab path)', () => {
    // The non-fallback path: shift+tab arrives from Ink with shift=true +
    // tab=true. The emitted ChordEvent.chord must equal the registered
    // default when SUPPORTS_TERMINAL_VT_MODE is true.
    const ev = buildChordEvent('', blankKey({ shift: true, tab: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('shift+tab')
  })

  test('round-trips through buildChordEvent (alt+m Windows fallback path)', () => {
    // The fallback path: citizen presses Alt+M (or Meta+M on macOS-style
    // hosts). Ink collapses both into `key.meta=true`; the matcher must
    // emit `alt+m` which is exactly what the fallback chord literal
    // registers. Pre-fix this was `meta+m` and the match would fail.
    const ev = buildChordEvent('m', blankKey({ meta: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('alt+m')
    // Parity check: the parsed chord of the fallback literal equals the
    // event's chord string. `parseChord` canonicalises modifier order so
    // this also protects against a future reshuffle.
    expect(String(parseChord('alt+m'))).toBe('alt+m')
  })

  test('permission-mode-cycle default binding is reachable via the matcher', () => {
    // End-to-end invariant: the binding the registry seeds for
    // permission-mode-cycle must be hittable by whichever chord the active
    // platform branch produced. We pick the matching Ink key shape for the
    // current `MODE_CYCLE_DEFAULT_CHORD` value.
    const entry = defaultBindingsByAction().get('permission-mode-cycle')
    expect(entry).not.toBeUndefined()
    expect(String(entry!.default_chord)).toBe(MODE_CYCLE_DEFAULT_CHORD)

    const ev =
      MODE_CYCLE_DEFAULT_CHORD === 'shift+tab'
        ? buildChordEvent('', blankKey({ shift: true, tab: true }))
        : buildChordEvent('m', blankKey({ meta: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe(String(entry!.default_chord))
  })

  test('DEFAULT_BINDINGS includes the permission-mode-cycle seed', () => {
    const actions = DEFAULT_BINDINGS.map((e) => e.action)
    expect(actions).toContain('permission-mode-cycle')
  })
})
