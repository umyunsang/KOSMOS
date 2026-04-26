// SPDX-License-Identifier: Apache-2.0
// Spec 288 — Tier 1 keybinding template and catalogue.
//
// generateKeybindingsTemplate():
//   Returns a flat `{ "<chord>": "<action>" }` JSON string with NO wrapper
//   keys (`$schema`, `$docs`, `bindings`). The loader iterates top-level
//   keys through tryParseChord; wrapper keys would surface as invalid-chord
//   warnings and silently drop every intended remap/disable (Codex P2 fix
//   on PR #1591).
//
// renderTier1CatalogueText():
//   Returns bilingual (Korean + English) human-readable text that lists
//   every Tier 1 action with its chord, status, and description.
//
// dumpTier1Catalogue():
//   Returns a machine-readable array of { action, chord_display, description }
//   for every Tier 1 action (FR-032, SC-007).

import { DEFAULT_BINDINGS } from './defaultBindings'
import { TIER_ONE_ACTIONS, type TierOneAction } from './types'

// ---------------------------------------------------------------------------
// generateKeybindingsTemplate
// ---------------------------------------------------------------------------

/**
 * Generate a template keybindings JSON file content.
 * Format: flat `{ "<chord>": "<action>" }` — no wrapper, no metadata keys.
 * Only non-reserved, remappable Tier 1 actions are included.
 */
export function generateKeybindingsTemplate(): string {
  const obj: Record<string, string> = {}
  for (const entry of DEFAULT_BINDINGS) {
    if (entry.reserved || !entry.remappable) continue
    // Use the canonical chord string as key.
    const chordStr = String(entry.effective_chord ?? entry.default_chord)
    obj[chordStr] = entry.action
  }
  return JSON.stringify(obj, null, 2) + '\n'
}

// ---------------------------------------------------------------------------
// dumpTier1Catalogue
// ---------------------------------------------------------------------------

export type Tier1CatalogueLine = Readonly<{
  action: TierOneAction
  chord_display: string
  description: string
  reserved: boolean
  remappable: boolean
}>

/**
 * Returns one entry per Tier 1 action for machine consumption (FR-032, SC-007).
 */
export function dumpTier1Catalogue(): ReadonlyArray<Tier1CatalogueLine> {
  // Build a lookup from the DEFAULT_BINDINGS.
  const byAction = new Map<TierOneAction, (typeof DEFAULT_BINDINGS)[number]>()
  for (const e of DEFAULT_BINDINGS) byAction.set(e.action, e)

  return TIER_ONE_ACTIONS.map((action) => {
    const entry = byAction.get(action)
    const chord = entry ? String(entry.effective_chord ?? entry.default_chord) : '—'
    return Object.freeze({
      action,
      chord_display: chord,
      description: entry?.description ?? action,
      reserved: entry?.reserved ?? false,
      remappable: entry?.remappable ?? true,
    })
  })
}

// ---------------------------------------------------------------------------
// renderTier1CatalogueText
// ---------------------------------------------------------------------------

/**
 * Returns a bilingual (Korean + English) human-readable catalogue of every
 * Tier 1 action, suitable for `/help keybindings` or `/keybindings` output.
 * Reserved actions are labelled "cannot remap".
 */
export function renderTier1CatalogueText(): string {
  const lines: string[] = [
    '## KOSMOS Tier 1 Keybindings / 단축키 목록',
    '',
  ]
  for (const item of dumpTier1Catalogue()) {
    const status = item.reserved
      ? 'reserved · cannot remap'
      : item.remappable
        ? 'remappable'
        : 'fixed'
    lines.push(`  ${item.chord_display.padEnd(20)} ${item.action.padEnd(24)} (${status})`)
    lines.push(`    ${item.description}`)
    lines.push('')
  }
  return lines.join('\n')
}
