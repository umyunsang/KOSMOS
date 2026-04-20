// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Codex P1 on PR #1591 — reserved-chord collision defense.
//
// Primary defense lives in `loadUserBindings.ts` (rejects overrides whose
// effective chord collides with a reserved chord's default, emitting a
// `reserved-chord-collision` warning). Registry-level backstop lives in
// `buildRegistry()` and throws `RegistryInvariantError(I4)` when a crafted
// `loaderResult` bypasses the loader and tries to place a non-reserved
// entry on a reserved chord's slot (Spec 025 V6 two-layer pattern).
//
// These tests cover:
//   1. End-to-end: loader + buildRegistry preserves reserved chords for
//      every override variant the Codex finding called out.
//   2. Backstop: crafted `loaderResult` with a collision throws I4.

import { describe, expect, it } from 'bun:test'
import { buildRegistry } from '../../src/keybindings/registry'
import { loadUserBindings } from '../../src/keybindings/loadUserBindings'
import {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
} from '../../src/keybindings/defaultBindings'
import { parseChord } from '../../src/keybindings/chord'
import { RegistryInvariantError } from '../../src/keybindings/validate'
import {
  type KeybindingEntry,
  type TierOneAction,
} from '../../src/keybindings/types'

function loadOverrides(json: string): ReturnType<typeof loadUserBindings> {
  return loadUserBindings({
    path: '<test:registry-collision>',
    readFile: () => json,
    onWarning: () => {
      /* warnings captured via result.warnings */
    },
  })
}

// ---------------------------------------------------------------------------
// End-to-end: ctrl+c remap attempt (Codex P1 exact repro)
// ---------------------------------------------------------------------------

describe('Reserved-chord collision (Codex P1 on PR #1591)', () => {
  it('remap of history-search onto ctrl+c preserves agent-interrupt', () => {
    const result = loadOverrides('{"ctrl+c": "history-search"}')
    const registry = buildRegistry({ loaderResult: result })

    const entry = registry.lookupByChord(parseChord('ctrl+c'), 'Global')
    expect(entry?.action).toBe('agent-interrupt')
    expect(entry?.reserved).toBe(true)

    // history-search stays on its default chord (ctrl+r).
    const historySearch = registry.entries.get('history-search')
    expect(historySearch?.effective_chord).toBe(parseChord('ctrl+r'))
  })

  it('remap of history-search onto ctrl+d preserves session-exit', () => {
    const result = loadOverrides('{"ctrl+d": "history-search"}')
    const registry = buildRegistry({ loaderResult: result })

    const entry = registry.lookupByChord(parseChord('ctrl+d'), 'Global')
    expect(entry?.action).toBe('session-exit')
    expect(entry?.reserved).toBe(true)

    const historySearch = registry.entries.get('history-search')
    expect(historySearch?.effective_chord).toBe(parseChord('ctrl+r'))
  })

  it('null disable on ctrl+c still resolves to agent-interrupt (FR-028)', () => {
    // Regression guard: FR-028 was already covered by loader tests. The
    // extra defense should keep the effective behaviour identical.
    const result = loadOverrides('{"ctrl+c": null}')
    const registry = buildRegistry({ loaderResult: result })

    const entry = registry.lookupByChord(parseChord('ctrl+c'), 'Global')
    expect(entry?.action).toBe('agent-interrupt')
    expect(result.disabled_chords.length).toBe(0)
  })

  it('null disable on ctrl+d still resolves to session-exit (FR-028)', () => {
    const result = loadOverrides('{"ctrl+d": null}')
    const registry = buildRegistry({ loaderResult: result })

    const entry = registry.lookupByChord(parseChord('ctrl+d'), 'Global')
    expect(entry?.action).toBe('session-exit')
  })

  it('context fallback still resolves reserved chords from any surface', () => {
    // The registry's context → Global fallback path MUST survive the
    // collision defense — otherwise we break FR-016 (reserved chords
    // reachable from every context).
    const result = loadOverrides('{"ctrl+c": "history-search"}')
    const registry = buildRegistry({ loaderResult: result })

    for (const context of ['Chat', 'HistorySearch', 'Confirmation'] as const) {
      const entry = registry.lookupByChord(parseChord('ctrl+c'), context)
      expect(entry?.action).toBe('agent-interrupt')
    }
  })
})

// ---------------------------------------------------------------------------
// Backstop: crafted loaderResult bypassing the loader
// ---------------------------------------------------------------------------

describe('Registry I4 backstop (Spec 025 V6 two-layer pattern)', () => {
  function craftedCollidingLoaderResult(): ReturnType<typeof loadUserBindings> {
    // Build a loaderResult whose `bindings` map places a non-reserved entry
    // (history-search) onto the reserved ctrl+c chord. This is what a future
    // bug in the loader OR a direct caller with crafted input would look
    // like — the backstop MUST throw rather than silently shadow ctrl+c.
    const defaults = defaultBindingsByAction()
    const bindings = new Map<TierOneAction, KeybindingEntry>()
    for (const [action, def] of defaults) {
      if (action === 'history-search') {
        bindings.set(
          action,
          Object.freeze({ ...def, effective_chord: parseChord('ctrl+c') }),
        )
      } else {
        bindings.set(action, def)
      }
    }
    return Object.freeze({
      bindings,
      warnings: Object.freeze([]),
      disabled_chords: Object.freeze([]),
      effective_chord_to_action: new Map(),
    })
  }

  it('throws RegistryInvariantError(I4) on crafted ctrl+c collision', () => {
    const crafted = craftedCollidingLoaderResult()
    expect(() => buildRegistry({ loaderResult: crafted })).toThrow(
      RegistryInvariantError,
    )

    try {
      buildRegistry({ loaderResult: crafted })
    } catch (err) {
      expect(err).toBeInstanceOf(RegistryInvariantError)
      const e = err as RegistryInvariantError
      expect(e.invariant).toBe('I4')
      expect(e.entry.action).toBe('history-search')
      expect(e.message).toContain('agent-interrupt')
    }
  })

  it('default (no override) produces a valid registry with reserved chords intact', () => {
    // Baseline sanity: the reorder-reserved-first change in buildRegistry
    // MUST NOT alter the resolution of the default-bindings registry.
    const defaults = defaultBindingsByAction()
    const loaderResult = Object.freeze({
      bindings: defaults,
      warnings: Object.freeze([]),
      disabled_chords: Object.freeze([]),
      effective_chord_to_action: new Map(),
    })
    const registry = buildRegistry({ loaderResult })

    for (const entry of DEFAULT_BINDINGS) {
      if (entry.effective_chord === null) continue
      const resolved = registry.lookupByChord(
        entry.effective_chord,
        entry.context,
      )
      expect(resolved?.action).toBe(entry.action)
    }
  })
})
