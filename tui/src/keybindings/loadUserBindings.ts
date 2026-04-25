// SPDX-License-Identifier: Apache-2.0
// Spec 288 — User keybinding override loader.
//
// Exports a SYNC `loadUserBindings(opts)` that:
//   1. Reads defaults from DEFAULT_BINDINGS (KeybindingEntry[]).
//   2. If opts.readFile is provided, calls it with opts.path to get JSON text.
//      Returns null → treated as ENOENT (degrade to defaults, FR-023).
//   3. Parses the JSON as a flat `{ <chord>: <action> | null }` map
//      (the new simple format; no `bindings`-wrapper, no `$schema`).
//   4. Validates each entry; emits LoaderWarning for errors; skips bad entries.
//   5. Applies surviving overrides to a mutable copy of the defaults map.
//   6. Returns a frozen LoaderResult.
//
// Reserved chords (ctrl+c, ctrl+d) and reserved actions (agent-interrupt,
// session-exit) are immutable — override attempts emit a warning and are
// silently discarded (FR-027, FR-028, Codex P1 on PR #1591).
//
// COMPATIBILITY: The legacy async `loadKeybindings()` and sync
// `loadKeybindingsSyncWithWarnings()` functions are preserved for the
// KeybindingSetup component. They delegate to the new sync function.

import { readFileSync } from 'fs'
import { parseChord, tryParseChord } from './chord'
import { DEFAULT_BINDINGS, defaultBindingsByAction, getKeybindingsPath } from './defaultBindings'
import type {
  ChordString,
  KeybindingEntry,
  TierOneAction,
} from './types'
import { TIER_ONE_ACTIONS } from './types'

// ---------------------------------------------------------------------------
// Re-export getKeybindingsPath for external callers that imported it from here
// ---------------------------------------------------------------------------
export { getKeybindingsPath }

// ---------------------------------------------------------------------------
// Warning types
// ---------------------------------------------------------------------------

export type LoaderWarningKind =
  | 'parse-error'
  | 'shape-invalid'
  | 'invalid-chord'
  | 'unknown-action'
  | 'reserved-action-remap'
  | 'reserved-chord-collision'

export type LoaderWarning = Readonly<{
  kind: LoaderWarningKind
  message: string
  chord?: string
  action?: string
}>

// Back-compat alias for the legacy validate module.
export type KeybindingWarning = LoaderWarning

// ---------------------------------------------------------------------------
// Loader result
// ---------------------------------------------------------------------------

export type LoaderResult = Readonly<{
  /** Per-action effective binding map (defaults + overrides applied). */
  bindings: ReadonlyMap<TierOneAction, KeybindingEntry>
  /** All warnings emitted during loading. */
  warnings: ReadonlyArray<LoaderWarning>
  /** Chords that were explicitly disabled (effective_chord = null). */
  disabled_chords: ReadonlyArray<ChordString>
  /** Reverse map: effective_chord → action (disabled chords excluded). */
  effective_chord_to_action: ReadonlyMap<ChordString, TierOneAction>
}>

// Back-compat alias.
export type KeybindingsLoadResult = LoaderResult

// ---------------------------------------------------------------------------
// Reserved sets (FR-027, FR-028, Codex P1)
// ---------------------------------------------------------------------------

const RESERVED_ACTIONS: ReadonlySet<TierOneAction> = new Set([
  'agent-interrupt',
  'session-exit',
])

function reservedDefaultChords(): ReadonlySet<ChordString> {
  const s = new Set<ChordString>()
  for (const e of DEFAULT_BINDINGS) {
    if (e.reserved && e.default_chord !== null) {
      s.add(e.default_chord)
    }
  }
  return s
}

// ---------------------------------------------------------------------------
// Loader options
// ---------------------------------------------------------------------------

export type LoadUserBindingsOpts = {
  /** Path to the override file (default: getKeybindingsPath()). */
  path?: string
  /**
   * Synchronous file reader injection. Return null to signal ENOENT
   * (degrade silently to defaults, FR-023). Return the file contents
   * as a string. Throwing is treated as a hard error with a `parse-error`
   * warning.
   */
  readFile?: (path: string) => string | null
  /** Optional per-warning callback (fired before the warning is pushed). */
  onWarning?: (warning: LoaderWarning) => void
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ACTION_SET: ReadonlySet<string> = new Set(TIER_ONE_ACTIONS)

function isTierOneAction(s: string): s is TierOneAction {
  return ACTION_SET.has(s)
}

function warn(
  warnings: LoaderWarning[],
  onWarning: ((w: LoaderWarning) => void) | undefined,
  w: LoaderWarning,
): void {
  warnings.push(w)
  onWarning?.(w)
}

function buildResult(
  bindings: Map<TierOneAction, KeybindingEntry>,
  warnings: LoaderWarning[],
): LoaderResult {
  const disabled_chords: ChordString[] = []
  const effective_chord_to_action = new Map<ChordString, TierOneAction>()

  for (const [action, entry] of bindings) {
    if (entry.effective_chord === null) {
      // We track disabled chords only for non-reserved entries.
      if (!entry.reserved) {
        disabled_chords.push(entry.default_chord)
      }
    } else {
      effective_chord_to_action.set(entry.effective_chord, action)
    }
  }

  return Object.freeze({
    bindings,
    warnings: Object.freeze(warnings),
    disabled_chords: Object.freeze(disabled_chords),
    effective_chord_to_action,
  })
}

// ---------------------------------------------------------------------------
// Main sync loader
// ---------------------------------------------------------------------------

/**
 * Synchronously loads and merges user keybinding overrides.
 *
 * Contract (tests are the authoritative spec):
 *   - Returns default bindings unchanged when no override file exists (FR-023).
 *   - Emits `parse-error` and falls back to defaults for malformed JSON (FR-024).
 *   - `{"<chord>": null}` disables a non-reserved binding (FR-025).
 *   - `{"<chord>": "<action>"}` remaps an action (FR-026).
 *   - Reserved-action remap attempts emit `reserved-action-remap` (FR-027).
 *   - Reserved-binding disable attempts emit `reserved-chord-collision` (FR-028 + Codex P1).
 *   - Chord-onto-reserved-chord remap attempts emit `reserved-chord-collision` (Codex P1 PR #1591).
 *   - Unknown chord syntax emits `invalid-chord`.
 *   - Unknown action value emits `unknown-action`.
 */
export function loadUserBindings(opts: LoadUserBindingsOpts = {}): LoaderResult {
  const warnings: LoaderWarning[] = []
  const { onWarning, path = getKeybindingsPath() } = opts

  // Start with a mutable copy of the defaults keyed by action.
  const bindings = new Map<TierOneAction, KeybindingEntry>(
    defaultBindingsByAction() as Map<TierOneAction, KeybindingEntry>,
  )
  const reservedChords = reservedDefaultChords()

  // -------------------------------------------------------------------------
  // 1. Read the file.
  // -------------------------------------------------------------------------
  let content: string | null = null
  if (opts.readFile !== undefined) {
    try {
      content = opts.readFile(path)
    } catch (err) {
      warn(warnings, onWarning, {
        kind: 'parse-error',
        message: `Failed to read ${path}: ${err instanceof Error ? err.message : String(err)}`,
      })
      return buildResult(bindings, warnings)
    }
  } else {
    // Real filesystem read.
    try {
      content = readFileSync(path, 'utf-8')
    } catch {
      // ENOENT or unreadable → degrade silently (FR-023).
      return buildResult(bindings, warnings)
    }
  }

  // null from readFile = ENOENT sentinel (FR-023).
  if (content === null) {
    return buildResult(bindings, warnings)
  }

  // -------------------------------------------------------------------------
  // 2. Parse JSON.
  // -------------------------------------------------------------------------
  let raw: unknown
  try {
    raw = JSON.parse(content)
  } catch (err) {
    warn(warnings, onWarning, {
      kind: 'parse-error',
      message: `Invalid JSON in ${path}: ${err instanceof Error ? err.message : String(err)}`,
    })
    return buildResult(bindings, warnings)
  }

  // -------------------------------------------------------------------------
  // 3. Validate shape: must be a plain object (not array, not null).
  // -------------------------------------------------------------------------
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    warn(warnings, onWarning, {
      kind: 'shape-invalid',
      message: `${path} must be a plain JSON object with chord → action entries`,
    })
    return buildResult(bindings, warnings)
  }

  const overrideMap = raw as Record<string, unknown>

  // -------------------------------------------------------------------------
  // 4. Process each override entry.
  // -------------------------------------------------------------------------
  for (const [chordStr, rawAction] of Object.entries(overrideMap)) {
    // 4a. Validate chord syntax.
    const chord = tryParseChord(chordStr)
    if (chord === null) {
      warn(warnings, onWarning, {
        kind: 'invalid-chord',
        message: `Invalid chord syntax: ${JSON.stringify(chordStr)}`,
        chord: chordStr,
      })
      continue
    }

    // 4b. Validate action type.
    if (rawAction !== null && typeof rawAction !== 'string') {
      warn(warnings, onWarning, {
        kind: 'invalid-chord',
        message: `Action for ${JSON.stringify(chordStr)} must be a string or null`,
        chord: chordStr,
      })
      continue
    }

    // 4c. Reserved-chord collision guard (Codex P1 on PR #1591).
    //     Any override (remap OR null-disable) targeting a reserved chord is
    //     rejected with `reserved-chord-collision` regardless of the value.
    if (reservedChords.has(chord)) {
      warn(warnings, onWarning, {
        kind: 'reserved-chord-collision',
        message: `Cannot override reserved chord ${chordStr}; it is permanently bound to a reserved action`,
        chord: chordStr,
      })
      continue
    }

    // 4d. Validate action value (for non-null remaps).
    if (typeof rawAction === 'string') {
      // 4d-i. Reject remap to reserved action.
      if (isTierOneAction(rawAction) && RESERVED_ACTIONS.has(rawAction)) {
        warn(warnings, onWarning, {
          kind: 'reserved-action-remap',
          message: `Cannot remap chord ${chordStr} to reserved action ${rawAction}`,
          chord: chordStr,
          action: rawAction,
        })
        continue
      }

      // 4d-ii. Reject unknown action.
      if (!isTierOneAction(rawAction)) {
        warn(warnings, onWarning, {
          kind: 'unknown-action',
          message: `Unknown action: ${JSON.stringify(rawAction)} (chord ${chordStr})`,
          chord: chordStr,
          action: rawAction,
        })
        continue
      }
    }

    // -------------------------------------------------------------------------
    // 4e. Apply the override.
    //     Find the action currently bound to `chord` in defaults and override it.
    // -------------------------------------------------------------------------
    if (rawAction === null) {
      // Disable: find which action currently has this chord, set effective_chord = null.
      for (const [action, existing] of bindings) {
        if (existing.default_chord === chord || existing.effective_chord === chord) {
          if (!existing.reserved) {
            bindings.set(action, Object.freeze({ ...existing, effective_chord: null }))
          }
          break
        }
      }
    } else {
      // Remap: update the action's effective_chord to `chord`.
      const action = rawAction as TierOneAction

      // Clear the chord from any action that currently holds it
      // (so the old holder loses the chord).
      for (const [existingAction, existing] of bindings) {
        if (existingAction !== action && existing.effective_chord === chord) {
          if (!existing.reserved) {
            bindings.set(existingAction, Object.freeze({ ...existing, effective_chord: null }))
          }
          break
        }
      }

      const current = bindings.get(action)
      if (current !== undefined) {
        bindings.set(action, Object.freeze({ ...current, effective_chord: chord }))
      }
    }
  }

  return buildResult(bindings, warnings)
}

// ---------------------------------------------------------------------------
// Legacy API surface — keep existing callers compiling.
// ---------------------------------------------------------------------------

/** @deprecated Use loadUserBindings() instead. */
export async function loadKeybindings(): Promise<LoaderResult> {
  return loadUserBindings()
}

/** @deprecated Use loadUserBindings() instead. */
export function loadKeybindingsSyncWithWarnings(): LoaderResult {
  return loadUserBindings()
}

/** @deprecated Use loadUserBindings()?.bindings. */
export function loadKeybindingsSync(): ReadonlyArray<KeybindingEntry> {
  return Array.from(loadUserBindings().bindings.values())
}

export function isKeybindingCustomizationEnabled(): boolean {
  return true
}

export function resetKeybindingLoaderForTesting(): void {
  /* no-op: new implementation is stateless */
}

export function disposeKeybindingWatcher(): void {
  /* no-op */
}

export async function initializeKeybindingWatcher(): Promise<void> {
  /* no-op */
}

// Compat: subscribeToKeybindingChanges
export const subscribeToKeybindingChanges: (
  listener: (result: LoaderResult) => void,
) => () => void = (_listener) => {
  return () => {}
}

export function getCachedKeybindingWarnings(): LoaderWarning[] {
  return []
}
