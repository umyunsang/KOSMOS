// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/resolver.ts (CC 2.1.88, research-use)
// Spec 288 · T013 / T014 / T014b — resolver with IME gate + OTel span + audit hook.
//
// Responsibilities:
//   T013 — Walk contexts in precedence order (modal → form → context → global)
//          per D7, return the first matching entry's action.
//   T014 — Inject the Korean IME gate at the entry point; when the composition
//          state is active, every action with `mutates_buffer === true` is
//          short-circuited to `{ kind: 'blocked', reason: 'ime-composing' }`
//          (FR-005 / FR-006 / FR-007 / D4).
//   T014b — Emit an OTel span for every dispatched / blocked result with
//          attributes `kosmos.tui.binding{,.context,.chord,.reserved,.blocked.reason}`
//          (FR-033 / FR-034). On reserved-action dispatch, additionally call
//          the Spec 024 `writeReservedAction` audit hook (FR-015 / SC-006).

import { type ChordEvent, type KeybindingContext, type KeybindingEntry, type KeybindingRegistry, type ResolutionResult, type AuditWriter, type AccessibilityAnnouncer, type ReservedActionAuditPayload } from './types'

// ---------------------------------------------------------------------------
// Precedence order — D7
// ---------------------------------------------------------------------------

const CONTEXT_PRECEDENCE: readonly KeybindingContext[] = [
  'Confirmation', // modal (PermissionGauntletModal / ConsentPrompt)
  'HistorySearch', // form (history-search overlay)
  'Chat', // context (InputBar focused)
  'Global', // fallback
] as const

// ---------------------------------------------------------------------------
// IME gate contract — structurally typed against `useKoreanIME`'s return shape
// so the resolver does not carry a React dep.
// ---------------------------------------------------------------------------

export interface ImeStateLike {
  readonly isComposing: boolean
}

// ---------------------------------------------------------------------------
// Span emitter — structurally typed; the Ink-side consumer injects a writer
// that forwards to the Python OTLP exporter over IPC. When no emitter is
// provided the resolver records to an in-memory ring for tests (drainable
// via `drainSpans`).
// ---------------------------------------------------------------------------

export type BindingSpanAttributes = Readonly<{
  'kosmos.tui.binding': string
  'kosmos.tui.binding.context': KeybindingContext
  'kosmos.tui.binding.chord': string
  'kosmos.tui.binding.reserved': boolean
  'kosmos.tui.binding.blocked.reason'?: string
}>

export interface SpanEmitter {
  emitBinding(attrs: BindingSpanAttributes): void
}

const inMemorySpans: BindingSpanAttributes[] = []
export function drainBindingSpans(): ReadonlyArray<BindingSpanAttributes> {
  const snapshot = Object.freeze(inMemorySpans.slice())
  inMemorySpans.length = 0
  return snapshot
}
const inMemorySpanEmitter: SpanEmitter = {
  emitBinding(attrs) {
    inMemorySpans.push(Object.freeze({ ...attrs }))
  },
}

// ---------------------------------------------------------------------------
// Resolve
// ---------------------------------------------------------------------------

export type ResolveContext = Readonly<{
  /** Active contexts from outermost modal to innermost focus owner. */
  active: ReadonlyArray<KeybindingContext>
  registry: KeybindingRegistry
  ime: ImeStateLike
  /** Span emitter — defaults to the in-memory ring for tests. */
  spans?: SpanEmitter
  /**
   * Session ID used when emitting reserved-action audit records.
   * Optional — when omitted, audit emission is skipped (tests without a
   * session still exercise span emission).
   */
  sessionId?: string
  /** Spec 024 audit hook — optional; wired at TUI boot. */
  audit?: AuditWriter
  /**
   * Announcer — optional at this layer (Tier 1 actions inject their own).
   */
  announcer?: AccessibilityAnnouncer
  /**
   * Interrupted tool-call id when the active agent loop was running (for
   * `user-interrupted` audit records). Optional.
   */
  interruptedToolCallId?: string
}>

export function resolve(
  event: ChordEvent,
  ctx: ResolveContext,
): ResolutionResult {
  const emitter = ctx.spans ?? inMemorySpanEmitter
  const contexts = orderActiveContexts(ctx.active)

  for (const context of contexts) {
    const entry = ctx.registry.lookupByChord(event.chord, context)
    if (entry === null) continue

    // FR-005 / FR-006 / FR-007 — IME gate.
    if (ctx.ime.isComposing && entry.mutates_buffer) {
      emitter.emitBinding(
        blockedAttrs(entry, context, 'ime-composing'),
      )
      return Object.freeze({
        kind: 'blocked',
        action: entry.action,
        reason: 'ime-composing',
      })
    }

    // Dispatch path.
    emitter.emitBinding(dispatchedAttrs(entry, context))
    if (entry.reserved && ctx.audit !== undefined && ctx.sessionId !== undefined) {
      void emitAuditSafe(ctx.audit, {
        event_type:
          entry.action === 'agent-interrupt'
            ? 'user-interrupted'
            : 'session-exited',
        session_id: ctx.sessionId,
        ...(ctx.interruptedToolCallId !== undefined
          ? { interrupted_tool_call_id: ctx.interruptedToolCallId }
          : {}),
      })
    }
    return Object.freeze({
      kind: 'dispatched',
      action: entry.action,
      context,
    })
  }

  return Object.freeze({ kind: 'no-match' })
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Re-order the caller-supplied active contexts to honour the precedence rule.
 * Unknown contexts are dropped (defensive; the type system already enforces).
 */
function orderActiveContexts(
  active: ReadonlyArray<KeybindingContext>,
): KeybindingContext[] {
  const set = new Set(active)
  return CONTEXT_PRECEDENCE.filter((c) => set.has(c))
}

function dispatchedAttrs(
  entry: KeybindingEntry,
  context: KeybindingContext,
): BindingSpanAttributes {
  return Object.freeze({
    'kosmos.tui.binding': entry.action,
    'kosmos.tui.binding.context': context,
    'kosmos.tui.binding.chord': entry.effective_chord ?? entry.default_chord,
    'kosmos.tui.binding.reserved': entry.reserved,
  })
}

function blockedAttrs(
  entry: KeybindingEntry,
  context: KeybindingContext,
  reason: string,
): BindingSpanAttributes {
  return Object.freeze({
    'kosmos.tui.binding': entry.action,
    'kosmos.tui.binding.context': context,
    'kosmos.tui.binding.chord': entry.effective_chord ?? entry.default_chord,
    'kosmos.tui.binding.reserved': entry.reserved,
    'kosmos.tui.binding.blocked.reason': reason,
  })
}

async function emitAuditSafe(
  audit: AuditWriter,
  payload: ReservedActionAuditPayload,
): Promise<void> {
  try {
    await audit.writeReservedAction(payload)
  } catch (err) {
    // Audit failure must never abort the reserved action — FR-013 requires
    // the interrupt to fire regardless. Surface via stderr for observability.
    process.stderr.write(
      `[keybindings] audit write failed: ${(err as Error).message}\n`,
    )
  }
}
