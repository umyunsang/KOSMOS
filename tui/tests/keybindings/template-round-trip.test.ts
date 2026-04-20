// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Codex P2 fix on PR #1591 — template ↔ loader round-trip.
//
// Regression guard: `generateKeybindingsTemplate()` previously wrapped the
// chord map under a `bindings` object with `$schema` / `$docs` siblings.
// `loadUserBindings()` iterates top-level keys through `tryParseChord`, so
// the three wrapper keys surfaced as `invalid-chord` warnings and every
// intended remap/disable was silently dropped — WCAG-driven customization
// could not survive a copy-from-template workflow (FR-023..FR-028 violated
// in practice even though the isolated loader/schema tests passed).
//
// This suite asserts the template, after re-parsing through the loader,
// yields EXACTLY the default bindings with ZERO warnings of any kind.

import { describe, expect, it } from 'bun:test'
import {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
} from '../../src/keybindings/defaultBindings'
import { loadUserBindings } from '../../src/keybindings/loadUserBindings'
import { generateKeybindingsTemplate } from '../../src/keybindings/template'

describe('template ↔ loader round-trip (Codex P2 regression guard)', () => {
  it('template re-parsed through the loader yields defaults with zero warnings', () => {
    const template = generateKeybindingsTemplate()
    const result = loadUserBindings({
      path: '<test:template-round-trip>',
      readFile: () => template,
      onWarning: () => {
        /* swallow — asserted via result.warnings */
      },
    })

    // Core contract: no warnings means no `$schema`/`$docs`/`bindings`
    // wrapper keys leaked into the top-level chord namespace.
    expect(result.warnings.length).toBe(0)

    // Every default binding survives the round-trip exactly — the template
    // encodes the defaults, so parsing it must reproduce them.
    expect(result.bindings.size).toBe(DEFAULT_BINDINGS.length)
    const defaults = defaultBindingsByAction()
    for (const [action, def] of defaults) {
      const got = result.bindings.get(action)
      expect(got).toBeDefined()
      expect(got?.effective_chord).toBe(def.effective_chord)
    }

    // No chord should be listed as disabled — the template has no `null`
    // values (disabling is a citizen-authored edit, not a default).
    expect(result.disabled_chords.length).toBe(0)
  })

  it('loader emits ZERO `invalid-chord` warnings on the template', () => {
    // Narrow regression — the pre-fix bug emitted exactly three
    // `invalid-chord` warnings, one each for `$schema`, `$docs`, and
    // `bindings`. This is the assertion that would have failed under
    // the old implementation and now passes.
    const template = generateKeybindingsTemplate()
    const result = loadUserBindings({
      path: '<test:template-no-invalid-chord>',
      readFile: () => template,
      onWarning: () => {},
    })
    const invalidChords = result.warnings.filter(
      (w) => w.kind === 'invalid-chord',
    )
    expect(invalidChords.length).toBe(0)
  })

  it('loader emits ZERO `shape-invalid` warnings on the template', () => {
    const template = generateKeybindingsTemplate()
    const result = loadUserBindings({
      path: '<test:template-no-shape-invalid>',
      readFile: () => template,
      onWarning: () => {},
    })
    const shapeWarnings = result.warnings.filter(
      (w) => w.kind === 'shape-invalid',
    )
    expect(shapeWarnings.length).toBe(0)
  })

  it('citizen edit on a template-derived file is honoured (disable ctrl+r)', () => {
    // Simulates the exact copy-paste-edit workflow Codex flagged: citizen
    // copies the template, disables ctrl+r, saves, relaunches. The
    // disable MUST take effect — the pre-fix implementation would have
    // dropped it alongside the wrapper-key warnings.
    const template = generateKeybindingsTemplate()
    const parsed = JSON.parse(template) as Record<string, string | null>
    parsed['ctrl+r'] = null
    const edited = JSON.stringify(parsed, null, 2) + '\n'

    const result = loadUserBindings({
      path: '<test:template-plus-disable-ctrl-r>',
      readFile: () => edited,
      onWarning: () => {},
    })
    expect(result.warnings.length).toBe(0)
    expect(result.bindings.get('history-search')?.effective_chord).toBeNull()
  })
})
