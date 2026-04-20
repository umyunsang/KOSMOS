// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/match.ts (CC 2.1.88, research-use)
// Spec 288 · T005 — chord-to-event matcher.
//
// Responsibilities:
//   1. Normalise Ink's `input` + `Key` pair into a canonical `ChordEvent`
//      whose `chord` is a `ChordString` parsed through `./parser`.
//   2. Detect raw control bytes (`\x03` = ctrl+c, `\x04` = ctrl+d) that Ink
//      sometimes surfaces without setting `key.ctrl=true` — FR-016 requires
//      reserved-action chords to fire even when terminals bypass Ink's Key
//      modifier flags.
//   3. Resolve a `ChordEvent` to at most one `KeybindingEntry` under a given
//      context by consulting the effective-chord map.
//
// Consumed by `resolver.ts` (T013) and by `useGlobalKeybindings.tsx` (T020).

import { parseChord, tryParseChord } from './parser'
import {
  type ChordEvent,
  type ChordString,
  type KeybindingContext,
  type KeybindingEntry,
  type KeybindingRegistry,
} from './types'

// ---------------------------------------------------------------------------
// Ink Key shape — structurally typed to avoid a hard dep on `ink`'s Key
// export (the module itself does not require the dep to resolve).
// ---------------------------------------------------------------------------

export interface InkKeyLike {
  ctrl: boolean
  shift: boolean
  meta: boolean
  escape?: boolean
  return?: boolean
  tab?: boolean
  backspace?: boolean
  delete?: boolean
  upArrow?: boolean
  downArrow?: boolean
  leftArrow?: boolean
  rightArrow?: boolean
  pageUp?: boolean
  pageDown?: boolean
  home?: boolean
  end?: boolean
}

// ---------------------------------------------------------------------------
// Raw-byte interception — FR-016
// ---------------------------------------------------------------------------

const RAW_BYTE_CHORDS: ReadonlyMap<string, ChordString> = new Map([
  ['\x03', parseChord('ctrl+c')],
  ['\x04', parseChord('ctrl+d')],
])

function detectRawByte(input: string): ChordString | null {
  return RAW_BYTE_CHORDS.get(input) ?? null
}

// ---------------------------------------------------------------------------
// Ink Key → key name
// ---------------------------------------------------------------------------

function keyName(input: string, key: InkKeyLike): string | null {
  if (key.escape === true) return 'escape'
  if (key.return === true) return 'enter'
  if (key.tab === true) return 'tab'
  if (key.backspace === true) return 'backspace'
  if (key.delete === true) return 'delete'
  if (key.upArrow === true) return 'up'
  if (key.downArrow === true) return 'down'
  if (key.leftArrow === true) return 'left'
  if (key.rightArrow === true) return 'right'
  if (key.pageUp === true) return 'pageup'
  if (key.pageDown === true) return 'pagedown'
  if (key.home === true) return 'home'
  if (key.end === true) return 'end'
  if (input.length === 1) return input.toLowerCase()
  return null
}

// ---------------------------------------------------------------------------
// Build ChordEvent from Ink input + Key
// ---------------------------------------------------------------------------

export function buildChordEvent(
  input: string,
  key: InkKeyLike,
  now: () => number = Date.now,
): ChordEvent | null {
  // Raw-byte fast-path — FR-016 reserved actions fire even when Ink's Key
  // modifier flags are stripped by the terminal (Windows Terminal without VT
  // mode, tmux pass-through, etc.). We derive the modifier booleans from the
  // canonical chord string so downstream consumers see a consistent surface.
  const rawChord = detectRawByte(input)
  if (rawChord !== null) {
    return Object.freeze({
      raw: input,
      chord: rawChord,
      ctrl: true,
      shift: false,
      alt: false,
      meta: false,
      timestamp: now(),
    })
  }

  const name = keyName(input, key)
  if (name === null) return null

  // QUIRK ported from CC: Ink sets `key.meta=true` on escape. Filter it so
  // `escape` bindings actually match.
  const meta = key.escape === true ? false : key.meta

  const parts: string[] = []
  if (key.ctrl) parts.push('ctrl')
  if (key.shift) parts.push('shift')
  // Ink collapses alt/meta into a single `meta` flag. We emit it as `alt` in
  // the chord string because that is the KOSMOS canonical form (see parser).
  if (meta) parts.push('alt')
  parts.push(name)

  const chord = tryParseChord(parts.join('+'))
  if (chord === null) return null

  return Object.freeze({
    raw: input,
    chord,
    ctrl: key.ctrl,
    shift: key.shift,
    alt: meta,
    meta,
    timestamp: now(),
  })
}

// ---------------------------------------------------------------------------
// Registry lookup — lightweight wrapper so callers don't import the registry
// type directly.
// ---------------------------------------------------------------------------

export function lookupChord(
  event: ChordEvent,
  context: KeybindingContext,
  registry: KeybindingRegistry,
): KeybindingEntry | null {
  return registry.lookupByChord(event.chord, context)
}
