// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T024 — registry invariants.

import { describe, expect, test } from 'bun:test'
import { parseChord } from '../../src/keybindings/parser'
import { validateEntries, RegistryInvariantError } from '../../src/keybindings/validate'
import { DEFAULT_BINDINGS } from '../../src/keybindings/defaultBindings'
import { type KeybindingEntry } from '../../src/keybindings/types'

describe('validate — registry invariants', () => {
  test('DEFAULT_BINDINGS passes all invariants', () => {
    expect(() => validateEntries(DEFAULT_BINDINGS)).not.toThrow()
  })

  test('I1 — reserved action marked remappable throws', () => {
    const bad: KeybindingEntry = Object.freeze({
      action: 'agent-interrupt',
      default_chord: parseChord('ctrl+c'),
      effective_chord: parseChord('ctrl+c'),
      context: 'Global',
      description: 'bad I1',
      remappable: true,
      reserved: true,
      mutates_buffer: false,
    })
    try {
      validateEntries([bad])
      expect.unreachable()
    } catch (e) {
      expect(e).toBeInstanceOf(RegistryInvariantError)
      expect((e as RegistryInvariantError).invariant).toBe('I1')
    }
  })

  test('I2 — reserved action with diverged effective_chord throws (FR-028)', () => {
    const bad: KeybindingEntry = Object.freeze({
      action: 'session-exit',
      default_chord: parseChord('ctrl+d'),
      effective_chord: parseChord('ctrl+q'),
      context: 'Global',
      description: 'bad I2',
      remappable: false,
      reserved: true,
      mutates_buffer: false,
    })
    try {
      validateEntries([bad])
      expect.unreachable()
    } catch (e) {
      expect((e as RegistryInvariantError).invariant).toBe('I2')
    }
  })

  test('I3 — default_chord that does not round-trip throws', () => {
    // Forge an entry whose default_chord is invalid under the grammar.
    const bad: KeybindingEntry = Object.freeze({
      action: 'draft-cancel',
      // cast through unknown — we're deliberately bypassing the brand
      default_chord: 'FOOBAR' as unknown as ReturnType<typeof parseChord>,
      effective_chord: null,
      context: 'Chat',
      description: 'bad I3',
      remappable: true,
      reserved: false,
      mutates_buffer: true,
    })
    try {
      validateEntries([bad])
      expect.unreachable()
    } catch (e) {
      expect((e as RegistryInvariantError).invariant).toBe('I3')
    }
  })
})
