// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T022 — parser grammar + canonicalisation.

import { describe, expect, test } from 'bun:test'
import { parseChord, tryParseChord } from '../../src/keybindings/parser'

describe('parser — chord grammar', () => {
  test('plain key', () => {
    expect(String(parseChord('escape'))).toBe('escape')
    expect(String(parseChord('enter'))).toBe('enter')
    expect(String(parseChord('up'))).toBe('up')
    expect(String(parseChord('a'))).toBe('a')
  })

  test('single-modifier lowercases and preserves', () => {
    expect(String(parseChord('ctrl+c'))).toBe('ctrl+c')
    expect(String(parseChord('CTRL+R'))).toBe('ctrl+r')
    expect(String(parseChord('shift+tab'))).toBe('shift+tab')
    // `meta+m` normalises to `alt+m` — see `meta → alt` canonicalisation
    // in `parseChord`. Addresses Codex P2 on PR #1591: the matcher always
    // emits `alt+<key>` for Ink's collapsed meta flag, so accepting `meta`
    // as a distinct chord modifier would silently break user overrides.
    expect(String(parseChord('meta+m'))).toBe('alt+m')
  })

  test('meta normalises to alt at parse time (Codex P2 PR #1591)', () => {
    // Both spellings produce the same ChordString so user overrides keyed
    // on `meta+...` match runtime events emitted as `alt+...`.
    expect(String(parseChord('meta+m'))).toBe(String(parseChord('alt+m')))
    expect(String(parseChord('meta+k'))).toBe(String(parseChord('alt+k')))
    // Idempotent collapse when both alt and meta are spelled in the same
    // chord — no duplicate-modifier error.
    expect(String(parseChord('alt+meta+m'))).toBe('alt+m')
    expect(String(parseChord('meta+alt+m'))).toBe('alt+m')
  })

  test('canonical modifier order (ctrl → shift → alt; meta → alt)', () => {
    // Input order is random; output MUST be the canonical order. `meta`
    // collapses into `alt` silently per Codex P2 fix.
    expect(String(parseChord('shift+ctrl+p'))).toBe('ctrl+shift+p')
    expect(String(parseChord('meta+alt+shift+ctrl+x'))).toBe(
      'ctrl+shift+alt+x',
    )
    expect(String(parseChord('alt+ctrl+t'))).toBe('ctrl+alt+t')
  })

  test('function keys', () => {
    expect(String(parseChord('f1'))).toBe('f1')
    expect(String(parseChord('ctrl+f12'))).toBe('ctrl+f12')
  })

  test('digits', () => {
    expect(String(parseChord('ctrl+0'))).toBe('ctrl+0')
    expect(String(parseChord('9'))).toBe('9')
  })

  test('rejects empty input', () => {
    expect(() => parseChord('')).toThrow()
    expect(tryParseChord('')).toBeNull()
  })

  test('rejects duplicate modifier', () => {
    expect(() => parseChord('ctrl+ctrl+c')).toThrow(/duplicate/)
    expect(tryParseChord('shift+shift+tab')).toBeNull()
  })

  test('rejects unknown modifier', () => {
    expect(() => parseChord('super+x')).toThrow()
    expect(tryParseChord('hyper+x')).toBeNull()
  })

  test('rejects malformed key', () => {
    expect(tryParseChord('ctrl+capslock')).toBeNull()
    expect(tryParseChord('ctrl+')).toBeNull()
  })

  test('tryParseChord returns null instead of throwing', () => {
    expect(tryParseChord('ctrl+shift+p')).not.toBeNull()
    expect(tryParseChord('ctrl+ctrl+p')).toBeNull()
  })
})
