// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T013 — Tier 1 key event resolver.
//
// `resolve(ev, opts)` maps a `ChordEvent` to a `ResolutionResult`:
//   - dispatched: action fired, optional OTel span emitted
//   - blocked: IME gate or other guard
//   - no-match: no binding found
//
// The resolver also maintains an in-process span ring buffer that
// `drainBindingSpans()` empties. This lets the OTel collector pull spans
// without coupling the hot path to async I/O.

import type {
  AuditWriter,
  ChordEvent,
  KeybindingContext,
  KeybindingRegistry,
  ResolutionResult,
  TierOneAction,
} from './types'

// ---------------------------------------------------------------------------
// OTel span surface
// ---------------------------------------------------------------------------

export type BindingSpanAttributes = Readonly<{
  'kosmos.tui.binding': TierOneAction
  'kosmos.tui.binding.context': KeybindingContext
  'kosmos.tui.binding.chord': string
  'kosmos.tui.binding.reserved': boolean
  'kosmos.tui.binding.blocked.reason'?: string
}>

export interface SpanEmitter {
  emitBinding(attrs: BindingSpanAttributes): void
}

// In-memory ring buffer (max 1024 entries; wraps on overflow).
const RING_SIZE = 1024
const _ring: BindingSpanAttributes[] = []

function ringPush(attrs: BindingSpanAttributes): void {
  if (_ring.length >= RING_SIZE) {
    _ring.shift()
  }
  _ring.push(attrs)
}

/**
 * Drain all pending binding spans from the in-memory ring.
 * Returns all accumulated entries and empties the ring.
 */
export function drainBindingSpans(): ReadonlyArray<BindingSpanAttributes> {
  const snapshot = _ring.slice()
  _ring.length = 0
  return Object.freeze(snapshot)
}

// ---------------------------------------------------------------------------
// Resolve options
// ---------------------------------------------------------------------------

export type ResolveOptions = {
  /** Active context stack (most-specific first). */
  active: ReadonlyArray<KeybindingContext>
  /** Registry to look up entries from. */
  registry: KeybindingRegistry
  /** Current IME composition state. */
  ime: { isComposing: boolean }
  /** Optional span emitter (defaults to the in-process ring). */
  spans?: SpanEmitter
  /** Session id for audit records. */
  sessionId?: string
  /** Audit writer for reserved actions. */
  audit?: AuditWriter
}

// ---------------------------------------------------------------------------
// Resolve
// ---------------------------------------------------------------------------

/**
 * Resolve a ChordEvent against the registry in the given context stack.
 *
 * Precedence: first context in `active` that has a binding wins.
 * Reserved (Global) chords resolve from any surface via Global fallback.
 */
export function resolve(
  ev: ChordEvent,
  opts: ResolveOptions,
): ResolutionResult {
  const { active, registry, ime, spans, sessionId, audit } = opts

  // Look up entry (tries each active context, then falls through to Global).
  let entry = null
  for (const ctx of active) {
    const candidate = registry.lookupByChord(ev.chord, ctx)
    if (candidate !== null) {
      entry = candidate
      break
    }
  }

  if (entry === null) {
    return { kind: 'no-match' }
  }

  const action = entry.action
  const context = entry.context

  // IME gate: mutates_buffer actions are blocked while composing (FR-005).
  if (ime.isComposing && entry.mutates_buffer) {
    const attrs: BindingSpanAttributes = {
      'kosmos.tui.binding': action,
      'kosmos.tui.binding.context': context,
      'kosmos.tui.binding.chord': String(ev.chord),
      'kosmos.tui.binding.reserved': entry.reserved,
      'kosmos.tui.binding.blocked.reason': 'ime-composing',
    }
    const emitter = spans ?? { emitBinding: ringPush }
    emitter.emitBinding(attrs)
    return { kind: 'blocked', action, reason: 'ime-composing' }
  }

  // Emit OTel span.
  const attrs: BindingSpanAttributes = {
    'kosmos.tui.binding': action,
    'kosmos.tui.binding.context': context,
    'kosmos.tui.binding.chord': String(ev.chord),
    'kosmos.tui.binding.reserved': entry.reserved,
  }
  const emitter = spans ?? { emitBinding: ringPush }
  emitter.emitBinding(attrs)

  // Emit audit record for reserved actions (fire-and-forget, FR-013).
  if (entry.reserved && audit !== undefined && sessionId !== undefined) {
    void audit
      .writeReservedAction({
        event_type: action === 'agent-interrupt' ? 'user-interrupted' : 'session-exited',
        session_id: sessionId,
      })
      .catch(() => {
        // FR-013: audit failure MUST NOT abort the dispatch.
      })
  }

  return { kind: 'dispatched', action, context }
}

// ---------------------------------------------------------------------------
// Legacy surface — the old resolver API is kept for useKeybinding.ts and
// other internal callers that still use ParsedBinding[].
// ---------------------------------------------------------------------------

import type { Key } from '../ink.js'
import { getKeyName, matchesBinding } from './match.js'
import { chordToString } from './parser.js'
import type {
  KeybindingContextName,
  ParsedBinding,
  ParsedKeystroke,
} from './types.js'

export type ResolveResult =
  | { type: 'match'; action: string }
  | { type: 'none' }
  | { type: 'unbound' }

export type ChordResolveResult =
  | { type: 'match'; action: string }
  | { type: 'none' }
  | { type: 'unbound' }
  | { type: 'chord_started'; pending: ParsedKeystroke[] }
  | { type: 'chord_cancelled' }

export function resolveKey(
  input: string,
  key: Key,
  activeContexts: KeybindingContextName[],
  bindings: ParsedBinding[],
): ResolveResult {
  let match: ParsedBinding | undefined
  const ctxSet = new Set(activeContexts)
  for (const binding of bindings) {
    if (binding.chord.length !== 1) continue
    if (!ctxSet.has(binding.context)) continue
    if (matchesBinding(input, key, binding)) match = binding
  }
  if (!match) return { type: 'none' }
  if (match.action === null) return { type: 'unbound' }
  return { type: 'match', action: match.action }
}

export function getBindingDisplayText(
  action: string,
  context: KeybindingContextName,
  bindings: ParsedBinding[],
): string | undefined {
  const binding = bindings.findLast(b => b.action === action && b.context === context)
  return binding ? chordToString(binding.chord) : undefined
}

function buildKeystroke(input: string, key: Key): ParsedKeystroke | null {
  const keyName = getKeyName(input, key)
  if (!keyName) return null
  const effectiveMeta = key.escape ? false : key.meta
  return { key: keyName, ctrl: key.ctrl, alt: effectiveMeta, shift: key.shift, meta: effectiveMeta, super: key.super }
}

export function keystrokesEqual(a: ParsedKeystroke, b: ParsedKeystroke): boolean {
  return (
    a.key === b.key &&
    a.ctrl === b.ctrl &&
    a.shift === b.shift &&
    (a.alt || a.meta) === (b.alt || b.meta) &&
    a.super === b.super
  )
}

function chordPrefixMatches(prefix: ParsedKeystroke[], binding: ParsedBinding): boolean {
  if (prefix.length >= binding.chord.length) return false
  for (let i = 0; i < prefix.length; i++) {
    const prefixKey = prefix[i]
    const bindingKey = binding.chord[i]
    if (!prefixKey || !bindingKey) return false
    if (!keystrokesEqual(prefixKey, bindingKey)) return false
  }
  return true
}

function chordExactlyMatches(chord: ParsedKeystroke[], binding: ParsedBinding): boolean {
  if (chord.length !== binding.chord.length) return false
  for (let i = 0; i < chord.length; i++) {
    const chordKey = chord[i]
    const bindingKey = binding.chord[i]
    if (!chordKey || !bindingKey) return false
    if (!keystrokesEqual(chordKey, bindingKey)) return false
  }
  return true
}

export function resolveKeyWithChordState(
  input: string,
  key: Key,
  activeContexts: KeybindingContextName[],
  bindings: ParsedBinding[],
  pending: ParsedKeystroke[] | null,
): ChordResolveResult {
  if (key.escape && pending !== null) return { type: 'chord_cancelled' }
  const currentKeystroke = buildKeystroke(input, key)
  if (!currentKeystroke) {
    if (pending !== null) return { type: 'chord_cancelled' }
    return { type: 'none' }
  }
  const testChord = pending ? [...pending, currentKeystroke] : [currentKeystroke]
  const ctxSet = new Set(activeContexts)
  const contextBindings = bindings.filter(b => ctxSet.has(b.context))
  const chordWinners = new Map<string, string | null>()
  for (const binding of contextBindings) {
    if (binding.chord.length > testChord.length && chordPrefixMatches(testChord, binding)) {
      chordWinners.set(chordToString(binding.chord), binding.action)
    }
  }
  let hasLongerChords = false
  for (const action of chordWinners.values()) {
    if (action !== null) { hasLongerChords = true; break }
  }
  if (hasLongerChords) return { type: 'chord_started', pending: testChord }
  let exactMatch: ParsedBinding | undefined
  for (const binding of contextBindings) {
    if (chordExactlyMatches(testChord, binding)) exactMatch = binding
  }
  if (exactMatch) {
    if (exactMatch.action === null) return { type: 'unbound' }
    return { type: 'match', action: exactMatch.action }
  }
  if (pending !== null) return { type: 'chord_cancelled' }
  return { type: 'none' }
}
