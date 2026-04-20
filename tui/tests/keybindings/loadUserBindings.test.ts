// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T039 — user-override loader regression suite (User Story 7).
//
// Closes #1586. Asserts FR-023..FR-028 round-trip + SC-004 (override of
// `ctrl+r` produces zero overlays in 10 consecutive presses).
//
// Strategy: drive `loadUserBindings()` with an injected `readFile` that
// returns the bytes of each fixture under tests/keybindings/fixtures/
// override-files/. We never touch `~/.kosmos/keybindings.json` — the
// loader's path argument is parameterised for exactly this reason.

import { describe, expect, it } from 'bun:test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import {
  loadUserBindings,
  type LoaderWarning,
} from '../../src/keybindings/loadUserBindings'
import {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
} from '../../src/keybindings/defaultBindings'
import { parseChord } from '../../src/keybindings/chord'

const FIXTURES = join(import.meta.dir, 'fixtures', 'override-files')

function readFixture(name: string): string {
  return readFileSync(join(FIXTURES, name), 'utf-8')
}

function loadFromFixture(
  name: string,
): ReturnType<typeof loadUserBindings> & {
  warnings_by_kind: Record<string, LoaderWarning[]>
} {
  const result = loadUserBindings({
    path: `<test:${name}>`,
    readFile: () => readFixture(name),
    onWarning: () => {
      /* swallow — captured via .warnings */
    },
  })
  const byKind: Record<string, LoaderWarning[]> = {}
  for (const w of result.warnings) {
    const bucket = byKind[w.kind] ?? []
    bucket.push(w)
    byKind[w.kind] = bucket
  }
  return Object.assign({}, result, { warnings_by_kind: byKind })
}

// ---------------------------------------------------------------------------
// FR-023 — missing file degrades silently to defaults
// ---------------------------------------------------------------------------

describe('FR-023 missing override file', () => {
  it('returns defaults when readFile signals ENOENT (returns null)', () => {
    const result = loadUserBindings({
      path: '/nonexistent/path/keybindings.json',
      readFile: () => null,
      onWarning: () => {},
    })
    expect(result.warnings.length).toBe(0)
    expect(result.bindings.size).toBe(DEFAULT_BINDINGS.length)
    for (const e of DEFAULT_BINDINGS) {
      expect(result.bindings.get(e.action)?.effective_chord).toBe(
        e.default_chord,
      )
    }
  })
})

// ---------------------------------------------------------------------------
// FR-024 — corrupted file degrades silently
// ---------------------------------------------------------------------------

describe('FR-024 corrupted override file', () => {
  it('logs a parse-error warning and falls back to defaults on malformed JSON', () => {
    const result = loadUserBindings({
      path: '<test:corrupt>',
      readFile: () => '{ this is not valid json',
      onWarning: () => {},
    })
    expect(result.warnings.some((w) => w.kind === 'parse-error')).toBe(true)
    expect(result.bindings.size).toBe(DEFAULT_BINDINGS.length)
  })

  it('logs a shape-invalid warning when the root is an array', () => {
    const result = loadFromFixture('invalid-shape.json')
    expect(result.warnings_by_kind['shape-invalid']?.length ?? 0).toBe(1)
    // Defaults preserved.
    for (const e of DEFAULT_BINDINGS) {
      expect(result.bindings.get(e.action)?.effective_chord).toBe(
        e.default_chord,
      )
    }
  })
})

// ---------------------------------------------------------------------------
// FR-025 — `<chord>: null` disables the binding
// ---------------------------------------------------------------------------

describe('FR-025 disable binding via null', () => {
  it('disables history-search when ctrl+r is mapped to null', () => {
    const result = loadFromFixture('disable-ctrl-r.json')
    const entry = result.bindings.get('history-search')
    expect(entry?.effective_chord).toBeNull()
    expect(result.disabled_chords).toContain(parseChord('ctrl+r'))
  })

  it('SC-004: 10 consecutive ctrl+r lookups against the disabled registry yield zero matches', () => {
    const result = loadFromFixture('disable-ctrl-r.json')
    const ctrlR = parseChord('ctrl+r')
    let opens = 0
    for (let i = 0; i < 10; i += 1) {
      // Simulate the resolver's chord-to-action lookup; a disabled binding
      // means the chord is absent from `effective_chord_to_action`.
      if (result.effective_chord_to_action.has(ctrlR)) opens += 1
    }
    expect(opens).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// FR-026 — remap action to a new chord
// ---------------------------------------------------------------------------

describe('FR-026 remap binding to new chord', () => {
  it('moves history-search from ctrl+r to ctrl+f', () => {
    const result = loadFromFixture('remap-ctrl-r-to-ctrl-f.json')
    const entry = result.bindings.get('history-search')
    expect(entry?.effective_chord).toBe(parseChord('ctrl+f'))
    expect(result.effective_chord_to_action.get(parseChord('ctrl+f'))).toBe(
      'history-search',
    )
    // Old chord no longer points to the action.
    expect(result.effective_chord_to_action.has(parseChord('ctrl+r'))).toBe(
      false,
    )
  })

  it('preserves other defaults untouched when one binding is remapped', () => {
    const result = loadFromFixture('remap-ctrl-r-to-ctrl-f.json')
    const defaults = defaultBindingsByAction()
    for (const [action, def] of defaults) {
      if (action === 'history-search') continue
      const got = result.bindings.get(action)
      expect(got?.effective_chord).toBe(def.effective_chord)
    }
  })
})

// ---------------------------------------------------------------------------
// FR-027 — reserved-action remap is rejected with a warning
// ---------------------------------------------------------------------------

describe('FR-027 reserved-action remap rejection', () => {
  it('rejects a remap of agent-interrupt to ctrl+x with a logged warning', () => {
    const result = loadFromFixture('attempt-reserved-remap.json')
    const reserved =
      result.warnings_by_kind['reserved-action-remap'] ?? []
    expect(reserved.length).toBe(1)
    expect(reserved[0]?.message).toContain('agent-interrupt')
    // Default ctrl+c → agent-interrupt remains.
    const ctrlC = parseChord('ctrl+c')
    expect(result.effective_chord_to_action.get(ctrlC)).toBe(
      'agent-interrupt',
    )
    // ctrl+x is NOT bound to agent-interrupt.
    const ctrlX = parseChord('ctrl+x')
    expect(result.effective_chord_to_action.get(ctrlX)).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// FR-028 — only non-reserved bindings are disableable
// ---------------------------------------------------------------------------

describe('FR-028 reserved bindings are not disableable', () => {
  it('ignores a `null` override on ctrl+c (reserved agent-interrupt)', () => {
    const result = loadUserBindings({
      path: '<test:disable-reserved>',
      readFile: () => '{"ctrl+c": null}',
      onWarning: () => {},
    })
    const entry = result.bindings.get('agent-interrupt')
    expect(entry?.effective_chord).toBe(parseChord('ctrl+c'))
    expect(
      result.effective_chord_to_action.get(parseChord('ctrl+c')),
    ).toBe('agent-interrupt')
    expect(result.disabled_chords.length).toBe(0)
  })

  it('also refuses to disable session-exit (reserved ctrl+d)', () => {
    const result = loadUserBindings({
      path: '<test:disable-ctrl-d>',
      readFile: () => '{"ctrl+d": null}',
      onWarning: () => {},
    })
    expect(
      result.effective_chord_to_action.get(parseChord('ctrl+d')),
    ).toBe('session-exit')
  })
})

// ---------------------------------------------------------------------------
// Codex P1 on PR #1591 — reserved-chord collision rejection
// ---------------------------------------------------------------------------
//
// FR-027 rejects remaps whose VALUE is a reserved action. This layer adds a
// companion guard that rejects overrides whose KEY (chord) collides with a
// reserved chord's default — otherwise `{"ctrl+c": "history-search"}` would
// silently shadow agent-interrupt. The new warning kind is
// `reserved-chord-collision`; it fires regardless of whether the value is
// a remap target or `null`.

describe('Codex P1 reserved-chord collision rejection', () => {
  it('rejects remapping history-search onto ctrl+c (reserved agent-interrupt)', () => {
    const result = loadUserBindings({
      path: '<test:collide-ctrl-c-remap>',
      readFile: () => '{"ctrl+c": "history-search"}',
      onWarning: () => {},
    })
    const kinds = result.warnings.map((w) => w.kind)
    expect(kinds).toContain('reserved-chord-collision')

    // history-search keeps its default chord (ctrl+r), not ctrl+c.
    expect(result.bindings.get('history-search')?.effective_chord).toBe(
      parseChord('ctrl+r'),
    )
    // ctrl+c still resolves to agent-interrupt in the effective map.
    expect(
      result.effective_chord_to_action.get(parseChord('ctrl+c')),
    ).toBe('agent-interrupt')
  })

  it('rejects remapping history-search onto ctrl+d (reserved session-exit)', () => {
    const result = loadUserBindings({
      path: '<test:collide-ctrl-d-remap>',
      readFile: () => '{"ctrl+d": "history-search"}',
      onWarning: () => {},
    })
    expect(result.warnings.some((w) => w.kind === 'reserved-chord-collision'))
      .toBe(true)
    expect(result.bindings.get('history-search')?.effective_chord).toBe(
      parseChord('ctrl+r'),
    )
    expect(
      result.effective_chord_to_action.get(parseChord('ctrl+d')),
    ).toBe('session-exit')
  })

  it('emits reserved-chord-collision warning for `ctrl+c: null` (not just silent)', () => {
    // FR-028 already silences the disable; this guard makes the feedback
    // channel explicit rather than having the chord fall into `disabled`
    // and get silently ignored later.
    const result = loadUserBindings({
      path: '<test:collide-ctrl-c-disable>',
      readFile: () => '{"ctrl+c": null}',
      onWarning: () => {},
    })
    expect(result.warnings.some((w) => w.kind === 'reserved-chord-collision'))
      .toBe(true)
    // Backwards-compatible: FR-028 state guarantees still hold.
    expect(result.bindings.get('agent-interrupt')?.effective_chord).toBe(
      parseChord('ctrl+c'),
    )
    expect(result.disabled_chords.length).toBe(0)
  })

  it('warning message cites the rejected chord for diagnostics', () => {
    const result = loadUserBindings({
      path: '<test:collide-diag>',
      readFile: () => '{"ctrl+c": "history-search"}',
      onWarning: () => {},
    })
    const collision = result.warnings.find(
      (w) => w.kind === 'reserved-chord-collision',
    )
    expect(collision?.message).toContain('ctrl+c')
  })
})

// ---------------------------------------------------------------------------
// Robustness — invalid chord syntax + unknown action
// ---------------------------------------------------------------------------

describe('Loader robustness', () => {
  it('warns on unknown chord syntax and otherwise returns defaults', () => {
    const result = loadUserBindings({
      path: '<test:bad-chord>',
      readFile: () => '{"shoof+x": "history-search"}',
      onWarning: () => {},
    })
    expect(result.warnings.some((w) => w.kind === 'invalid-chord')).toBe(
      true,
    )
    // Default chord for history-search untouched.
    expect(result.bindings.get('history-search')?.effective_chord).toBe(
      parseChord('ctrl+r'),
    )
  })

  it('warns on unknown action and otherwise returns defaults', () => {
    const result = loadUserBindings({
      path: '<test:bad-action>',
      readFile: () => '{"ctrl+f": "not-a-real-action"}',
      onWarning: () => {},
    })
    expect(result.warnings.some((w) => w.kind === 'unknown-action')).toBe(
      true,
    )
    expect(
      result.effective_chord_to_action.has(parseChord('ctrl+f')),
    ).toBe(false)
  })
})
