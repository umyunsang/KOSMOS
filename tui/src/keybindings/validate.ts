// SPDX-License-Identifier: Apache-2.0
// Spec 288 — Registry invariant validator.
//
// `validateEntries(entries: KeybindingEntry[])` checks four invariants:
//   I1 — reserved action MUST NOT be marked remappable.
//   I2 — reserved action MUST NOT have effective_chord !== default_chord.
//   I3 — default_chord MUST round-trip through parseChord().
//   I4 — two-layer collision guard (reserved chord backstop in buildRegistry).
//
// Throws `RegistryInvariantError` on the first violation found.
// The error exposes `.invariant` (label string) and `.entry` (violating row)
// so test assertions can be precise.

import { tryParseChord } from './chord'
import type { KeybindingEntry, TierOneAction } from './types'

// ---------------------------------------------------------------------------
// RegistryInvariantError
// ---------------------------------------------------------------------------

export class RegistryInvariantError extends Error {
  readonly invariant: string
  readonly entry: KeybindingEntry

  constructor(invariant: string, entry: KeybindingEntry, detail?: string) {
    super(
      detail
        ? `Registry invariant ${invariant} violated: ${detail}`
        : `Registry invariant ${invariant} violated for action "${entry.action}"`,
    )
    this.name = 'RegistryInvariantError'
    this.invariant = invariant
    this.entry = entry
  }
}

// ---------------------------------------------------------------------------
// Invariant checks
// ---------------------------------------------------------------------------

/**
 * Validate a list of KeybindingEntry rows against all registry invariants.
 * Throws RegistryInvariantError on the first violation.
 */
export function validateEntries(entries: ReadonlyArray<KeybindingEntry>): void {
  for (const entry of entries) {
    // I1 — reserved action MUST NOT be remappable.
    if (entry.reserved && entry.remappable) {
      throw new RegistryInvariantError('I1', entry,
        `reserved action "${entry.action}" must not be marked remappable`)
    }

    // I2 — reserved action MUST NOT have a diverged effective_chord.
    if (entry.reserved && entry.effective_chord !== entry.default_chord) {
      throw new RegistryInvariantError('I2', entry,
        `reserved action "${entry.action}" has effective_chord (${String(entry.effective_chord)}) !== default_chord (${String(entry.default_chord)})`)
    }

    // I3 — default_chord MUST be a valid chord (round-trip through parser).
    const rt = tryParseChord(String(entry.default_chord))
    if (rt === null || rt !== entry.default_chord) {
      throw new RegistryInvariantError('I3', entry,
        `default_chord "${String(entry.default_chord)}" does not round-trip through parseChord`)
    }
  }
}

// ---------------------------------------------------------------------------
// Legacy surface — the legacy validate functions are kept for the
// KeybindingSetup component and older internal callers.
// ---------------------------------------------------------------------------

import { plural } from '../utils/stringUtils.js'
import { chordToString, parseChord as legacyParseChord, parseKeystroke } from './parser.js'
import {
  getReservedShortcuts,
  normalizeKeyForComparison,
} from './reservedShortcuts.js'
import type {
  KeybindingBlock,
  ParsedBinding,
} from './types.js'

export type KeybindingWarningType =
  | 'parse_error'
  | 'duplicate'
  | 'reserved'
  | 'invalid_context'
  | 'invalid_action'

export type KeybindingWarning = {
  kind?: string
  type?: KeybindingWarningType
  severity?: 'error' | 'warning'
  message: string
  key?: string
  context?: string
  action?: string
  suggestion?: string
}

function isKeybindingBlock(obj: unknown): obj is KeybindingBlock {
  if (typeof obj !== 'object' || obj === null) return false
  const b = obj as Record<string, unknown>
  return (
    typeof b.context === 'string' &&
    typeof b.bindings === 'object' &&
    b.bindings !== null
  )
}

function isKeybindingBlockArray(arr: unknown): arr is KeybindingBlock[] {
  return Array.isArray(arr) && arr.every(isKeybindingBlock)
}

const VALID_CONTEXTS: string[] = [
  'Global', 'Chat', 'Autocomplete', 'Confirmation', 'Help', 'Transcript',
  'HistorySearch', 'Task', 'ThemePicker', 'Settings', 'Tabs', 'Attachments',
  'Footer', 'MessageSelector', 'DiffDialog', 'ModelPicker', 'Select', 'Plugin',
]

function isValidContext(value: string): boolean {
  return VALID_CONTEXTS.includes(value)
}

function validateKeystroke(keystroke: string): KeybindingWarning | null {
  const parts = keystroke.toLowerCase().split('+')
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) {
      return {
        type: 'parse_error',
        severity: 'error',
        message: `Empty key part in "${keystroke}"`,
        key: keystroke,
        suggestion: 'Remove extra "+" characters',
      }
    }
  }
  const parsed = parseKeystroke(keystroke)
  if (!parsed.key && !parsed.ctrl && !parsed.alt && !parsed.shift && !parsed.meta) {
    return {
      type: 'parse_error',
      severity: 'error',
      message: `Could not parse keystroke "${keystroke}"`,
      key: keystroke,
    }
  }
  return null
}

function validateBlock(block: unknown, blockIndex: number): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  if (typeof block !== 'object' || block === null) {
    warnings.push({ type: 'parse_error', severity: 'error', message: `Keybinding block ${blockIndex + 1} is not an object` })
    return warnings
  }
  const b = block as Record<string, unknown>
  const rawContext = b.context
  let contextName: string | undefined
  if (typeof rawContext !== 'string') {
    warnings.push({ type: 'parse_error', severity: 'error', message: `Keybinding block ${blockIndex + 1} missing "context" field` })
  } else if (!isValidContext(rawContext)) {
    warnings.push({ type: 'invalid_context', severity: 'error', message: `Unknown context "${rawContext}"`, context: rawContext, suggestion: `Valid contexts: ${VALID_CONTEXTS.join(', ')}` })
  } else {
    contextName = rawContext
  }
  if (typeof b.bindings !== 'object' || b.bindings === null) {
    warnings.push({ type: 'parse_error', severity: 'error', message: `Keybinding block ${blockIndex + 1} missing "bindings" field` })
    return warnings
  }
  const bindings = b.bindings as Record<string, unknown>
  for (const [key, action] of Object.entries(bindings)) {
    const keyError = validateKeystroke(key)
    if (keyError) { keyError.context = contextName; warnings.push(keyError) }
    if (action !== null && typeof action !== 'string') {
      warnings.push({ type: 'invalid_action', severity: 'error', message: `Invalid action for "${key}": must be a string or null`, key, context: contextName })
    }
  }
  return warnings
}

export function checkDuplicateKeysInJson(jsonString: string): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  const bindingsBlockPattern = /"bindings"\s*:\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g
  let blockMatch
  while ((blockMatch = bindingsBlockPattern.exec(jsonString)) !== null) {
    const blockContent = blockMatch[1]
    if (!blockContent) continue
    const textBeforeBlock = jsonString.slice(0, blockMatch.index)
    const contextMatch = textBeforeBlock.match(/"context"\s*:\s*"([^"]+)"[^{]*$/)
    const context = contextMatch?.[1] ?? 'unknown'
    const keyPattern = /"([^"]+)"\s*:/g
    const keysByName = new Map<string, number>()
    let keyMatch
    while ((keyMatch = keyPattern.exec(blockContent)) !== null) {
      const key = keyMatch[1]
      if (!key) continue
      const count = (keysByName.get(key) ?? 0) + 1
      keysByName.set(key, count)
      if (count === 2) {
        warnings.push({ type: 'duplicate', severity: 'warning', message: `Duplicate key "${key}" in ${context} bindings`, key, context, suggestion: `This key appears multiple times in the same context. JSON uses the last value, earlier values are ignored.` })
      }
    }
  }
  return warnings
}

export function validateUserConfig(userBlocks: unknown): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  if (!Array.isArray(userBlocks)) {
    warnings.push({ type: 'parse_error', severity: 'error', message: 'keybindings.json must contain an array', suggestion: 'Wrap your bindings in [ ]' })
    return warnings
  }
  for (let i = 0; i < userBlocks.length; i++) {
    warnings.push(...validateBlock(userBlocks[i], i))
  }
  return warnings
}

export function checkDuplicates(blocks: KeybindingBlock[]): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  const seenByContext = new Map<string, Map<string, string>>()
  for (const block of blocks) {
    const contextMap = seenByContext.get(block.context) ?? new Map<string, string>()
    seenByContext.set(block.context, contextMap)
    for (const [key, action] of Object.entries(block.bindings)) {
      const normalizedKey = normalizeKeyForComparison(key)
      const existingAction = contextMap.get(normalizedKey)
      if (existingAction && existingAction !== action) {
        warnings.push({ type: 'duplicate', severity: 'warning', message: `Duplicate binding "${key}" in ${block.context} context`, key, context: block.context, action: action ?? 'null (unbind)', suggestion: `Previously bound to "${existingAction}". Only the last binding will be used.` })
      }
      contextMap.set(normalizedKey, action ?? 'null')
    }
  }
  return warnings
}

function getUserBindingsForValidation(userBlocks: KeybindingBlock[]): ParsedBinding[] {
  const bindings: ParsedBinding[] = []
  for (const block of userBlocks) {
    for (const [key, action] of Object.entries(block.bindings)) {
      const chord = key.split(' ').map(k => parseKeystroke(k))
      bindings.push({ chord, action, context: block.context })
    }
  }
  return bindings
}

export function checkReservedShortcuts(bindings: ParsedBinding[]): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  const reserved = getReservedShortcuts()
  for (const binding of bindings) {
    const keyDisplay = chordToString(binding.chord)
    const normalizedKey = normalizeKeyForComparison(keyDisplay)
    for (const res of reserved) {
      if (normalizeKeyForComparison(res.key) === normalizedKey) {
        warnings.push({ type: 'reserved', severity: res.severity, message: `"${keyDisplay}" may not work: ${res.reason}`, key: keyDisplay, context: binding.context, action: binding.action ?? undefined })
      }
    }
  }
  return warnings
}

export function validateBindings(userBlocks: unknown, _parsedBindings: ParsedBinding[]): KeybindingWarning[] {
  const warnings: KeybindingWarning[] = []
  warnings.push(...validateUserConfig(userBlocks))
  if (isKeybindingBlockArray(userBlocks)) {
    warnings.push(...checkDuplicates(userBlocks))
    const userBindings = getUserBindingsForValidation(userBlocks)
    warnings.push(...checkReservedShortcuts(userBindings))
  }
  const seen = new Set<string>()
  return warnings.filter(w => {
    const key = `${w.type}:${w.key}:${w.context}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function formatWarning(warning: KeybindingWarning): string {
  const icon = warning.severity === 'error' ? '✗' : '⚠'
  let msg = `${icon} Keybinding ${warning.severity}: ${warning.message}`
  if (warning.suggestion) msg += `\n  ${warning.suggestion}`
  return msg
}

export function formatWarnings(warnings: KeybindingWarning[]): string {
  if (warnings.length === 0) return ''
  const errors = warnings.filter(w => w.severity === 'error')
  const warns = warnings.filter(w => w.severity === 'warning')
  const lines: string[] = []
  if (errors.length > 0) {
    lines.push(`Found ${errors.length} keybinding ${plural(errors.length, 'error')}:`)
    for (const e of errors) lines.push(formatWarning(e))
  }
  if (warns.length > 0) {
    if (lines.length > 0) lines.push('')
    lines.push(`Found ${warns.length} keybinding ${plural(warns.length, 'warning')}:`)
    for (const w of warns) lines.push(formatWarning(w))
  }
  return lines.join('\n')
}
