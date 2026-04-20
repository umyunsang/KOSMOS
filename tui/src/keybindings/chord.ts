// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Team C local helper.
//
// Minimal chord-string canonicaliser. The full grammar lives in Lead's
// `parser.ts` (T004) which lands together with `match.ts` / `validate.ts`.
// This file contributes ONLY the brand-narrowing helper the Team C action
// handlers need so they compile + test independently of Lead's port. Once
// `parser.ts` lands, prefer importing `parseChord` from there — this file
// stays as a thin alias.

import { MODIFIER_ORDER, type ChordString, type Modifier } from './types'

const VALID_KEYS = new Set<string>([
  'tab',
  'enter',
  'escape',
  'up',
  'down',
  'left',
  'right',
  'pageup',
  'pagedown',
  'home',
  'end',
  'space',
  'backspace',
  'delete',
])

function isLetter(s: string): boolean {
  return /^[a-z]$/.test(s)
}

function isDigit(s: string): boolean {
  return /^[0-9]$/.test(s)
}

function isFunctionKey(s: string): boolean {
  return /^f([1-9]|1[0-2])$/.test(s)
}

function isValidKey(s: string): boolean {
  return (
    VALID_KEYS.has(s) || isLetter(s) || isDigit(s) || isFunctionKey(s)
  )
}

const MODIFIER_SET: ReadonlySet<Modifier> = new Set(MODIFIER_ORDER)

function isModifier(s: string): s is Modifier {
  return (MODIFIER_SET as Set<string>).has(s)
}

/**
 * Parse + canonicalise a chord string. Throws on malformed input.
 *
 * Canonical form: modifiers in `ctrl→shift→alt→meta` order, lowercased,
 * single trailing key. Examples: `ctrl+c`, `ctrl+shift+p`, `escape`.
 *
 * `meta` normalises to `alt` during parsing. Ink collapses terminal
 * alt/meta into a single `key.meta` flag and `buildChordEvent()` emits
 * `alt+<key>` at runtime — so accepting `meta` as a distinct modifier
 * would let user overrides like `{"meta+k": "history-search"}` load but
 * never match. The schema + `Modifier` union still document `meta` as
 * valid spelling; the normalisation happens silently here to preserve
 * the KOSMOS invariant that loader-accepted strings match matcher-emitted
 * ones. Addresses Codex P2 on PR #1591.
 */
export function parseChord(input: string): ChordString {
  if (typeof input !== 'string' || input.length === 0) {
    throw new Error(`invalid chord: ${JSON.stringify(input)}`)
  }
  const tokens = input.toLowerCase().split('+')
  if (tokens.length === 0) {
    throw new Error(`invalid chord: ${JSON.stringify(input)}`)
  }
  const key = tokens[tokens.length - 1] ?? ''
  if (!isValidKey(key)) {
    throw new Error(`invalid key in chord: ${JSON.stringify(input)}`)
  }
  const seenMods = new Set<Modifier>()
  for (let i = 0; i < tokens.length - 1; i += 1) {
    const tok = tokens[i] ?? ''
    if (!isModifier(tok)) {
      throw new Error(`invalid modifier in chord: ${JSON.stringify(input)}`)
    }
    if (seenMods.has(tok)) {
      throw new Error(`duplicate modifier in chord: ${JSON.stringify(input)}`)
    }
    seenMods.add(tok)
  }
  // `meta` → `alt` canonicalisation. If both modifiers are spelled in the
  // same chord (e.g. `alt+meta+m`), the collapse is idempotent — we silently
  // coalesce to `alt` rather than raising a duplicate-modifier error.
  if (seenMods.has('meta')) {
    seenMods.delete('meta')
    seenMods.add('alt')
  }
  const ordered: string[] = []
  for (const m of MODIFIER_ORDER) {
    if (seenMods.has(m)) ordered.push(m)
  }
  ordered.push(key)
  return ordered.join('+') as unknown as ChordString
}

/**
 * Construct a ChordString without throwing. Returns `null` if invalid.
 * Useful for the user-override loader where invalid chords are logged
 * but never crash the TUI (FR-024).
 */
export function tryParseChord(input: string): ChordString | null {
  try {
    return parseChord(input)
  } catch {
    return null
  }
}
