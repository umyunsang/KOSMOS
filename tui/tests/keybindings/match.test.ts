// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T023 — chord-to-event matcher + raw-byte FR-016.

import { describe, expect, test } from 'bun:test'
import { buildChordEvent, type InkKeyLike } from '../../src/keybindings/match'

function blankKey(over: Partial<InkKeyLike> = {}): InkKeyLike {
  return { ctrl: false, shift: false, meta: false, ...over }
}

describe('match — ChordEvent synthesis', () => {
  test('ctrl+c raw byte fires even without Key modifier flags (FR-016)', () => {
    const ev = buildChordEvent('\x03', blankKey(), () => 1000)
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('ctrl+c')
    expect(ev!.ctrl).toBe(true)
    expect(ev!.timestamp).toBe(1000)
  })

  test('ctrl+d raw byte fires even without Key modifier flags (FR-016)', () => {
    const ev = buildChordEvent('\x04', blankKey())
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('ctrl+d')
    expect(ev!.ctrl).toBe(true)
  })

  test('shift+tab synthesises the canonical chord string', () => {
    const ev = buildChordEvent('', blankKey({ shift: true, tab: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('shift+tab')
  })

  test('meta+m Windows fallback', () => {
    const ev = buildChordEvent('m', blankKey({ meta: true }))
    expect(ev).not.toBeNull()
    // Ink collapses alt/meta; KOSMOS canonicalises to "alt" token first.
    expect(String(ev!.chord)).toBe('alt+m')
  })

  test('escape key ignores Ink key.meta quirk', () => {
    // Ink sets meta=true on escape; match.ts must strip it so "escape"
    // matches rather than "alt+escape".
    const ev = buildChordEvent('', blankKey({ escape: true, meta: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('escape')
    expect(ev!.meta).toBe(false)
  })

  test('up arrow', () => {
    const ev = buildChordEvent('', blankKey({ upArrow: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('up')
  })

  test('down arrow', () => {
    const ev = buildChordEvent('', blankKey({ downArrow: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('down')
  })

  test('ctrl+r', () => {
    const ev = buildChordEvent('r', blankKey({ ctrl: true }))
    expect(ev).not.toBeNull()
    expect(String(ev!.chord)).toBe('ctrl+r')
  })

  test('returns null for uninterpretable input', () => {
    const ev = buildChordEvent('', blankKey())
    expect(ev).toBeNull()
  })
})
