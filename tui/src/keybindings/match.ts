import type { Key } from '../ink.js'
import type { ChordEvent, ChordString, ParsedBinding, ParsedKeystroke } from './types.js'

// ---------------------------------------------------------------------------
// InkKeyLike — testable subset of Ink's Key type.
// Tests use this instead of the full Ink Key to avoid pulling in the full
// ink type surface. Structurally compatible with Ink's Key.
// ---------------------------------------------------------------------------
export type InkKeyLike = Partial<Key> & {
  ctrl?: boolean
  shift?: boolean
  meta?: boolean
  escape?: boolean
  tab?: boolean
  return?: boolean
  backspace?: boolean
  delete?: boolean
  upArrow?: boolean
  downArrow?: boolean
  leftArrow?: boolean
  rightArrow?: boolean
  pageUp?: boolean
  pageDown?: boolean
  wheelUp?: boolean
  wheelDown?: boolean
  home?: boolean
  end?: boolean
  super?: boolean
  fn?: boolean
  insert?: boolean
}

// ---------------------------------------------------------------------------
// Raw control-byte to (key, ctrl) mapping (FR-016: raw byte detection).
// Ink does not always set modifier flags for control characters sent as
// raw bytes; we detect these explicitly so ctrl+c / ctrl+d fire reliably.
// ---------------------------------------------------------------------------
const RAW_CTRL_MAP: ReadonlyMap<string, string> = new Map([
  ['\x01', 'a'], ['\x02', 'b'], ['\x03', 'c'], ['\x04', 'd'],
  ['\x05', 'e'], ['\x06', 'f'], ['\x07', 'g'], ['\x08', 'h'],
  ['\x09', 'i'], ['\x0b', 'k'], ['\x0c', 'l'], ['\x0e', 'n'],
  ['\x0f', 'o'], ['\x10', 'p'], ['\x11', 'q'], ['\x12', 'r'],
  ['\x13', 's'], ['\x14', 't'], ['\x15', 'u'], ['\x16', 'v'],
  ['\x17', 'w'], ['\x18', 'x'], ['\x19', 'y'], ['\x1a', 'z'],
  ['\x1f', '-'], // ctrl+-
])

/**
 * Build a ChordEvent from raw terminal input + Ink Key object.
 *
 * Returns null when the input cannot be interpreted as a known chord
 * (e.g., empty input with no key flags set — typically mouse move events).
 *
 * FR-016: raw control bytes (e.g., \x03 = ctrl+c) are detected even when
 * Ink's Key object does not set the ctrl modifier flag.
 */
export function buildChordEvent(
  raw: string,
  key: InkKeyLike,
  getNow: () => number = () => Date.now(),
): ChordEvent | null {
  const k = key as Key

  // -------------------------------------------------------------------------
  // 1. FR-016 raw control-byte detection (highest priority).
  //    Some terminals send ctrl+c as \x03 without setting key.ctrl.
  // -------------------------------------------------------------------------
  if (raw.length === 1 && !k.escape && !k.return && !k.tab) {
    const mapped = RAW_CTRL_MAP.get(raw)
    if (mapped) {
      const chord = `ctrl+${mapped}` as ChordString
      return {
        raw,
        chord,
        ctrl: true,
        shift: false,
        alt: false,
        meta: false,
        timestamp: getNow(),
      }
    }
  }

  // -------------------------------------------------------------------------
  // 2. Derive key name from Ink flags.
  // -------------------------------------------------------------------------
  let keyName: string | null = null
  if (k.escape) keyName = 'escape'
  else if (k.return) keyName = 'enter'
  else if (k.tab) keyName = 'tab'
  else if (k.backspace) keyName = 'backspace'
  else if (k.delete) keyName = 'delete'
  else if (k.upArrow) keyName = 'up'
  else if (k.downArrow) keyName = 'down'
  else if (k.leftArrow) keyName = 'left'
  else if (k.rightArrow) keyName = 'right'
  else if (k.pageUp) keyName = 'pageup'
  else if (k.pageDown) keyName = 'pagedown'
  else if (k.wheelUp) keyName = 'wheelup'
  else if (k.wheelDown) keyName = 'wheeldown'
  else if (k.home) keyName = 'home'
  else if (k.end) keyName = 'end'
  else if (raw.length === 1) keyName = raw.toLowerCase()

  if (!keyName) return null

  // -------------------------------------------------------------------------
  // 3. Derive modifier flags.
  // -------------------------------------------------------------------------
  const ctrl = k.ctrl ?? false
  const shift = k.shift ?? false
  // Ink uses key.meta for both Alt and Meta; canonicalise to alt.
  // Suppress meta on escape (Ink quirk: escape always sets meta=true).
  const rawMeta = k.escape ? false : (k.meta ?? false)
  const alt = rawMeta  // meta → alt per Codex P2 canonicalisation
  const meta = false    // never surfaced as distinct from alt

  // -------------------------------------------------------------------------
  // 4. Build chord string: canonical modifier order ctrl+shift+alt+<key>.
  // -------------------------------------------------------------------------
  const parts: string[] = []
  if (ctrl) parts.push('ctrl')
  if (shift) parts.push('shift')
  if (alt) parts.push('alt')
  parts.push(keyName)
  const chord = parts.join('+') as ChordString

  return { raw, chord, ctrl, shift, alt, meta, timestamp: getNow() }
}

/**
 * Modifier keys from Ink's Key type that we care about for matching.
 * Note: `fn` from Key is intentionally excluded as it's rarely used and
 * not commonly configurable in terminal applications.
 */
type InkModifiers = Pick<Key, 'ctrl' | 'shift' | 'meta' | 'super'>

/**
 * Extract modifiers from an Ink Key object.
 * This function ensures we're explicitly extracting the modifiers we care about.
 */
function getInkModifiers(key: Key): InkModifiers {
  return {
    ctrl: key.ctrl,
    shift: key.shift,
    meta: key.meta,
    super: key.super,
  }
}

/**
 * Extract the normalized key name from Ink's Key + input.
 * Maps Ink's boolean flags (key.escape, key.return, etc.) to string names
 * that match our ParsedKeystroke.key format.
 */
export function getKeyName(input: string, key: Key): string | null {
  if (key.escape) return 'escape'
  if (key.return) return 'enter'
  if (key.tab) return 'tab'
  if (key.backspace) return 'backspace'
  if (key.delete) return 'delete'
  if (key.upArrow) return 'up'
  if (key.downArrow) return 'down'
  if (key.leftArrow) return 'left'
  if (key.rightArrow) return 'right'
  if (key.pageUp) return 'pageup'
  if (key.pageDown) return 'pagedown'
  if (key.wheelUp) return 'wheelup'
  if (key.wheelDown) return 'wheeldown'
  if (key.home) return 'home'
  if (key.end) return 'end'
  if (input.length === 1) return input.toLowerCase()
  return null
}

/**
 * Check if all modifiers match between Ink Key and ParsedKeystroke.
 *
 * Alt and Meta: Ink historically set `key.meta` for Alt/Option. A `meta`
 * modifier in config is treated as an alias for `alt` — both match when
 * `key.meta` is true.
 *
 * Super (Cmd/Win): distinct from alt/meta. Only arrives via the kitty
 * keyboard protocol on supporting terminals. A `cmd`/`super` binding will
 * simply never fire on terminals that don't send it.
 */
function modifiersMatch(
  inkMods: InkModifiers,
  target: ParsedKeystroke,
): boolean {
  // Check ctrl modifier
  if (inkMods.ctrl !== target.ctrl) return false

  // Check shift modifier
  if (inkMods.shift !== target.shift) return false

  // Alt and meta both map to key.meta in Ink (terminal limitation)
  // So we check if EITHER alt OR meta is required in target
  const targetNeedsMeta = target.alt || target.meta
  if (inkMods.meta !== targetNeedsMeta) return false

  // Super (cmd/win) is a distinct modifier from alt/meta
  if (inkMods.super !== target.super) return false

  return true
}

/**
 * Check if a ParsedKeystroke matches the given Ink input + Key.
 *
 * The display text will show platform-appropriate names (opt on macOS, alt elsewhere).
 */
export function matchesKeystroke(
  input: string,
  key: Key,
  target: ParsedKeystroke,
): boolean {
  const keyName = getKeyName(input, key)
  if (keyName !== target.key) return false

  const inkMods = getInkModifiers(key)

  // QUIRK: Ink sets key.meta=true when escape is pressed (see input-event.ts).
  // This is a legacy behavior from how escape sequences work in terminals.
  // We need to ignore the meta modifier when matching the escape key itself,
  // otherwise bindings like "escape" (without modifiers) would never match.
  if (key.escape) {
    return modifiersMatch({ ...inkMods, meta: false }, target)
  }

  return modifiersMatch(inkMods, target)
}

/**
 * Check if Ink's Key + input matches a parsed binding's first keystroke.
 * For single-keystroke bindings only (Phase 1).
 */
export function matchesBinding(
  input: string,
  key: Key,
  binding: ParsedBinding,
): boolean {
  if (binding.chord.length !== 1) return false
  const keystroke = binding.chord[0]
  if (!keystroke) return false
  return matchesKeystroke(input, key, keystroke)
}
