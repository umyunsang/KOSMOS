// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/loadUserBindings.ts (CC 2.1.88, research-use)
// Spec 288 · narrowed to KOSMOS schema (chord-keyed object, value = action | null).
//
// Contract surface (FR-023..FR-028):
//   - Missing or unreadable file → silent degrade to defaults (FR-023).
//   - Malformed JSON or shape-invalid → silent degrade, parse error logged (FR-024).
//   - `<chord>: null` → disable binding (FR-025).
//   - `<new-chord>: <action>` → remap action (FR-026).
//   - Reserved-action remap attempt → reject + log warning, defaults kept (FR-027).
//   - All non-reserved Tier 1 bindings disableable; reserved bindings are not (FR-028).
//
// Consumed by registry assembler (T012). Tested by T039.

import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { tryParseChord } from './chord'
import {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
} from './defaultBindings'
import {
  type ChordString,
  type KeybindingEntry,
  type TierOneAction,
  TIER_ONE_ACTIONS,
} from './types'

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

export type LoaderWarning = Readonly<{
  kind:
    | 'file-missing'
    | 'parse-error'
    | 'shape-invalid'
    | 'reserved-action-remap'
    | 'unknown-action'
    | 'invalid-chord'
  message: string
}>

export type LoaderResult = Readonly<{
  bindings: ReadonlyMap<TierOneAction, KeybindingEntry>
  warnings: ReadonlyArray<LoaderWarning>
  /** chords that were explicitly disabled via `null` override (FR-025). */
  disabled_chords: ReadonlyArray<ChordString>
  /** map of effective chord → action, including remaps (FR-026). */
  effective_chord_to_action: ReadonlyMap<ChordString, TierOneAction>
}>

const TIER_ONE_ACTION_SET: ReadonlySet<TierOneAction> = new Set(
  TIER_ONE_ACTIONS,
)

function isTierOneAction(s: unknown): s is TierOneAction {
  return typeof s === 'string' && TIER_ONE_ACTION_SET.has(s as TierOneAction)
}

// ---------------------------------------------------------------------------
// Default override path — `~/.kosmos/keybindings.json`
// ---------------------------------------------------------------------------

export function defaultOverridePath(): string {
  return join(homedir(), '.kosmos', 'keybindings.json')
}

// ---------------------------------------------------------------------------
// Main loader (sync — runs once at TUI boot)
// ---------------------------------------------------------------------------

function logWarning(w: LoaderWarning): void {
  // Stdlib console; the TUI process tees to ~/.kosmos/logs/. Per AGENTS.md
  // hard rule "no print() outside CLI output layer" applies to Python only —
  // TS source uses `console.warn` for diagnostics surfaces by precedent
  // (see Onboarding stderr envelope writers).
  process.stderr.write(`[keybindings] ${w.kind}: ${w.message}\n`)
}

function defaultsResult(
  warnings: LoaderWarning[],
): LoaderResult {
  const m = defaultBindingsByAction()
  const chordMap = new Map<ChordString, TierOneAction>()
  for (const e of DEFAULT_BINDINGS) {
    if (e.effective_chord !== null) {
      chordMap.set(e.effective_chord, e.action)
    }
  }
  return Object.freeze({
    bindings: m,
    warnings: Object.freeze(warnings.slice()),
    disabled_chords: Object.freeze([]),
    effective_chord_to_action: chordMap,
  })
}

export type LoadUserBindingsOptions = {
  /** Defaults to `~/.kosmos/keybindings.json`. */
  path?: string
  /**
   * Test injection point — read function. Defaults to `readFileSync`.
   * Returning `null` simulates ENOENT (silent degrade per FR-023).
   */
  readFile?: (path: string) => string | null
  /**
   * Test injection — warning sink. Defaults to stderr.
   * Receives every warning emitted during the load.
   */
  onWarning?: (w: LoaderWarning) => void
}

function defaultRead(path: string): string | null {
  try {
    return readFileSync(path, 'utf-8')
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code
    if (code === 'ENOENT' || code === 'EACCES' || code === 'EISDIR') {
      return null
    }
    // Surface other I/O issues as missing — silent degrade.
    return null
  }
}

export function loadUserBindings(
  options: LoadUserBindingsOptions = {},
): LoaderResult {
  const path = options.path ?? defaultOverridePath()
  const read = options.readFile ?? defaultRead
  const warnings: LoaderWarning[] = []
  const sink = options.onWarning ?? logWarning

  const raw = read(path)
  if (raw === null) {
    // FR-023 — missing/unreadable file is not an error.
    return defaultsResult(warnings)
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw) as unknown
  } catch (err) {
    const w: LoaderWarning = {
      kind: 'parse-error',
      message: `failed to parse override file at ${path}: ${
        (err as Error).message
      }`,
    }
    warnings.push(w)
    sink(w)
    return defaultsResult(warnings) // FR-024
  }

  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    Array.isArray(parsed)
  ) {
    const w: LoaderWarning = {
      kind: 'shape-invalid',
      message: `override file at ${path} must be a JSON object`,
    }
    warnings.push(w)
    sink(w)
    return defaultsResult(warnings) // FR-024
  }

  // Walk every chord-keyed entry in the override map and accumulate effects.
  // Two operation kinds are distinguished:
  //   1. <chord>: null              ⇒ disable any default that lives on this chord.
  //   2. <chord>: <action-name>     ⇒ remap (action moves from its default chord
  //                                   to <chord>), unless the action is reserved.

  const disabled = new Set<ChordString>()
  const remap = new Map<TierOneAction, ChordString>()

  for (const [rawChord, rawValue] of Object.entries(
    parsed as Record<string, unknown>,
  )) {
    const chord = tryParseChord(rawChord)
    if (chord === null) {
      const w: LoaderWarning = {
        kind: 'invalid-chord',
        message: `unknown chord syntax: ${rawChord}`,
      }
      warnings.push(w)
      sink(w)
      continue
    }

    if (rawValue === null) {
      disabled.add(chord)
      continue
    }

    if (!isTierOneAction(rawValue)) {
      const w: LoaderWarning = {
        kind: 'unknown-action',
        message: `unknown action ${JSON.stringify(rawValue)} for chord ${rawChord}`,
      }
      warnings.push(w)
      sink(w)
      continue
    }

    // FR-027 — reserved actions cannot be remapped.
    const defaultEntry = defaultBindingsByAction().get(rawValue)
    if (defaultEntry?.reserved === true) {
      const w: LoaderWarning = {
        kind: 'reserved-action-remap',
        message: `rejected remap of reserved action: ${rawValue}`,
      }
      warnings.push(w)
      sink(w)
      continue
    }
    remap.set(rawValue, chord)
  }

  // Apply effects.  Disable beats remap when the same chord shows up in both:
  // a citizen who writes `{"ctrl+r": null}` plus `{"ctrl+r": "history-search"}`
  // sees the disable win, because the JSON parser already kept the last value;
  // we only re-affirm the rule here for the reserved-disable edge case below.
  const merged = new Map<TierOneAction, KeybindingEntry>()
  for (const e of DEFAULT_BINDINGS) {
    let effective: ChordString | null = e.default_chord
    const remapTarget = remap.get(e.action)
    if (remapTarget !== undefined) {
      effective = remapTarget
    }
    // FR-028 — reserved bindings cannot be disabled.
    if (
      effective !== null &&
      disabled.has(effective) &&
      e.reserved === false
    ) {
      effective = null
    }
    merged.set(e.action, Object.freeze({ ...e, effective_chord: effective }))
  }

  // Build the chord → action lookup excluding disabled entries.
  const chordMap = new Map<ChordString, TierOneAction>()
  for (const e of merged.values()) {
    if (e.effective_chord !== null) {
      chordMap.set(e.effective_chord, e.action)
    }
  }

  // Surface the disabled chords for diagnostics (catalogue dump, /doctor).
  const disabledChords: ChordString[] = []
  for (const chord of disabled) {
    // Only count as disabled if it actually corresponded to a default chord
    // that was non-reserved — reserved disables are silently ignored.
    const action = (() => {
      for (const e of DEFAULT_BINDINGS) {
        if (e.default_chord === chord) return e.action
      }
      return null
    })()
    if (action === null) continue
    const entry = merged.get(action)
    if (entry !== undefined && entry.effective_chord === null) {
      disabledChords.push(chord)
    }
  }

  return Object.freeze({
    bindings: merged,
    warnings: Object.freeze(warnings.slice()),
    disabled_chords: Object.freeze(disabledChords),
    effective_chord_to_action: chordMap,
  })
}
