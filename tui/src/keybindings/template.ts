// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/template.ts (CC 2.1.88, research-use)
// Spec 288 · narrowed for the seven Tier 1 actions (FR-032, SC-007).
//
// Two surfaces:
//   1. `generateKeybindingsTemplate()` — emits the citizen-editable JSON
//      override file template (ports CC's template).
//   2. `dumpTier1Catalogue()` — emits the human-readable catalogue used by
//      the help-surface menu so a screen-reader user can discover every
//      Tier 1 binding without pressing any key (FR-032 / SC-007).
//
// Both surfaces deliberately exclude reserved actions from the *editable*
// template (CC pattern) but the dump *includes* every action so the citizen
// can still hear the binding via screen reader (the reserved binding cannot
// be remapped — but it must remain discoverable).

import { DEFAULT_BINDINGS } from './defaultBindings'
import {
  type KeybindingEntry,
  type TierOneAction,
} from './types'

// ---------------------------------------------------------------------------
// Editable JSON template
// ---------------------------------------------------------------------------

// Schema + docs URLs are preserved here as non-emitted constants so that
// `/doctor` and docs surfaces can still surface the reference pointers
// without polluting the override file itself. The override schema
// (`schemas/user-override.schema.json`) declares `additionalProperties:
// false` over a chord-string `patternProperties`, so `$schema` / `$docs`
// CANNOT appear at the top level — doing so would (a) fail JSON Schema
// validation and (b) be parsed by `loadUserBindings()` as invalid chords
// (emitting `invalid-chord` warnings and ignoring every intended remap).
// Citizens discover the schema via the catalogue menu + onboarding docs,
// not via an inline JSON-pointer header (JSON has no comment syntax).
export const KEYBINDINGS_OVERRIDE_SCHEMA_URL =
  'https://kosmos.dev/schemas/keybindings-override-v1.json'
export const KEYBINDINGS_OVERRIDE_DOCS_URL =
  'https://github.com/umyunsang/KOSMOS/tree/main/specs/288-shortcut-tier1-port'

export function generateKeybindingsTemplate(): string {
  // Flat chord→action map, matching the shape `loadUserBindings()` expects
  // and `schemas/user-override.schema.json` declares (FR-023..FR-028).
  //
  // Reserved actions (agent-interrupt, session-exit) are intentionally
  // excluded from the editable surface per FR-027: remapping them is
  // rejected by the loader; surfacing them in the template would mislead
  // citizens into writing rejected JSON.
  const editable: Record<string, TierOneAction> = {}
  for (const e of DEFAULT_BINDINGS) {
    if (e.reserved === false && e.effective_chord !== null) {
      editable[e.effective_chord as unknown as string] = e.action
    }
  }
  return `${JSON.stringify(editable, null, 2)}\n`
}

// ---------------------------------------------------------------------------
// Tier 1 catalogue dump (FR-032 / SC-007)
//
// Returns one entry per Tier 1 action with citizen-readable + chord display
// strings. The help-surface menu renders this through Ink `<Text>` so screen
// readers stream every line. Order matches `TIER_ONE_ACTIONS` so the dump
// is stable across renders (no flicker).
// ---------------------------------------------------------------------------

export type CatalogueLine = Readonly<{
  action: TierOneAction
  chord_display: string
  description: string
  reserved: boolean
  remappable: boolean
  status: 'active' | 'disabled' | 'reserved'
}>

function statusOf(e: KeybindingEntry): CatalogueLine['status'] {
  if (e.reserved) return 'reserved'
  if (e.effective_chord === null) return 'disabled'
  return 'active'
}

function chordDisplay(e: KeybindingEntry): string {
  // Format `ctrl+c` → `Ctrl+C`.  Display string MUST cover both the
  // active and disabled cases — disabled chords still surface their
  // default so citizens can recognise what they turned off.
  const chord = (e.effective_chord ?? e.default_chord) as unknown as string
  return chord
    .split('+')
    .map((tok) =>
      tok.length === 1
        ? tok.toUpperCase()
        : tok.charAt(0).toUpperCase() + tok.slice(1),
    )
    .join('+')
}

export function dumpTier1Catalogue(
  bindings: ReadonlyArray<KeybindingEntry> = DEFAULT_BINDINGS,
): ReadonlyArray<CatalogueLine> {
  return Object.freeze(
    bindings.map((e) =>
      Object.freeze({
        action: e.action,
        chord_display: chordDisplay(e),
        description: e.description,
        reserved: e.reserved,
        remappable: e.remappable,
        status: statusOf(e),
      }),
    ),
  )
}

/**
 * Render the catalogue as plain text suitable for piping to a screen
 * reader announce channel or rendering inside an Ink `<Text>` block.
 *
 * Lines are separated by `\n`; each line carries the chord, the action
 * name, the bilingual description, and a status suffix when the binding
 * is disabled or reserved (citizens hear the suffix and learn that the
 * binding is off / cannot be remapped).
 */
export function renderTier1CatalogueText(
  bindings: ReadonlyArray<KeybindingEntry> = DEFAULT_BINDINGS,
): string {
  const lines = dumpTier1Catalogue(bindings).map((line) => {
    const suffix =
      line.status === 'disabled'
        ? '  [비활성 / disabled]'
        : line.status === 'reserved'
        ? '  [예약 / reserved — cannot remap]'
        : ''
    return `${line.chord_display}  ${line.action}  —  ${line.description}${suffix}`
  })
  return lines.join('\n')
}
