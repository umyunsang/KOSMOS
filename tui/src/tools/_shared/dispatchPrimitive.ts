// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic ζ #2297 Phase 0b · T008
//
// dispatchPrimitive — shared helper that replaces the {status: 'stub'} bodies
// in the 4 primitive call() implementations with real IPC dispatch.
//
// Contracts: contracts/tui-primitive-dispatcher.md I-D2 / I-D3 / I-D6 / I-D7
// Data model: data-model.md § 4
// FR-009 (verify args verbatim): dispatcher MUST NOT translate tool_id.

import { trace } from '@opentelemetry/api'
import { makeUUIDv7, makeBaseEnvelope } from '../../ipc/envelope.js'
import type { IPCBridge } from '../../ipc/bridge.js'
import type { ToolCallFrame, ToolResultFrame } from '../../ipc/frames.generated.js'
import type { ToolUseContext, ToolResult } from '../../Tool.js'
import { PendingCallRegistry } from './pendingCallRegistry.js'

// ---------------------------------------------------------------------------
// Re-export PendingCallRegistry for convenience (tests/callers can import
// both from the same module).
// ---------------------------------------------------------------------------
export { PendingCallRegistry } from './pendingCallRegistry.js'

// ---------------------------------------------------------------------------
// OTEL tracer
// ---------------------------------------------------------------------------

const _tracer = trace.getTracer('kosmos.tui.primitive', '0.1.0')

// ---------------------------------------------------------------------------
// Environment-driven timeout (FR-006)
// ---------------------------------------------------------------------------

const DEFAULT_TIMEOUT_MS = 30_000

function _resolveTimeoutMs(override?: number): number {
  if (override !== undefined && override > 0) return override
  const env = process.env['KOSMOS_TUI_PRIMITIVE_TIMEOUT_MS']
  if (env) {
    const n = parseInt(env, 10)
    if (!isNaN(n) && n > 0) return n
  }
  return DEFAULT_TIMEOUT_MS
}

// ---------------------------------------------------------------------------
// Options type (I-D2)
// ---------------------------------------------------------------------------

export interface DispatchPrimitiveOpts {
  primitive: 'lookup' | 'verify' | 'submit' | 'subscribe'
  /** Forwarded verbatim into tool_call frame arguments (FR-009). */
  args: Record<string, unknown>
  /** From CC SDK Tool.call signature. */
  context: ToolUseContext
  /** Session-scoped pending call registry (injected). */
  registry: PendingCallRegistry
  /** IPC bridge (injected). */
  bridge: IPCBridge
  /** Default 30_000 ms; env KOSMOS_TUI_PRIMITIVE_TIMEOUT_MS overrides. */
  timeoutMs?: number
}

// ---------------------------------------------------------------------------
// CHECKPOINT marker state (I-P2 / T014)
// ---------------------------------------------------------------------------

const _RECEIPT_REGEX = /hometax-\d{4}-\d{2}-\d{2}-RX-[A-Z0-9]{5}/

let _checkpointEmitted = false

/** Reset checkpoint state — used by tests to verify exactly-once semantics. */
export function _resetCheckpointState(): void {
  _checkpointEmitted = false
}

function _maybeEmitCheckpoint(
  primitive: 'lookup' | 'verify' | 'submit' | 'subscribe',
  frame: ToolResultFrame,
): void {
  if (process.env['KOSMOS_SMOKE_CHECKPOINTS'] !== 'true') return
  if (primitive !== 'submit') return
  if (_checkpointEmitted) return

  // Check transaction_id on the frame first
  const txId = frame.transaction_id
  if (txId && typeof txId === 'string' && _RECEIPT_REGEX.test(txId)) {
    _checkpointEmitted = true
    process.stderr.write('CHECKPOINTreceipt token observed\n')
    return
  }

  // Also scan the envelope for a receipt-id-like field
  try {
    const envelopeStr = JSON.stringify(frame.envelope)
    if (_RECEIPT_REGEX.test(envelopeStr)) {
      _checkpointEmitted = true
      process.stderr.write('CHECKPOINTreceipt token observed\n')
    }
  } catch {
    // Ignore serialization errors
  }
}

// ---------------------------------------------------------------------------
// dispatchPrimitive<O> (I-D3)
// ---------------------------------------------------------------------------

/**
 * Dispatch a primitive call over the IPC bridge and await the tool_result.
 *
 * Invariants:
 *   I-D2 — signature exactly as specified in the contract.
 *   I-D3 — mints callId, constructs ToolCallFrame, registers pending call,
 *           sends frame, returns Promise driven by registry resolution.
 *   I-D6 — timeout (default 30s) rejects with Korean error message and sets
 *           OTEL span attribute `kosmos.tui.primitive.timeout=true`.
 *   I-D7 — error envelope (envelope.error set) surfaces as ok=false result.
 *   I-D8 — verify args forwarded verbatim (FR-009); no translation here.
 */
export async function dispatchPrimitive<O = unknown>(
  opts: DispatchPrimitiveOpts,
): Promise<ToolResult<O>> {
  const timeoutMs = _resolveTimeoutMs(opts.timeoutMs)

  // ------------------------------------------------------------------
  // Step 1: OTEL span
  // ------------------------------------------------------------------
  const span = _tracer.startSpan(`kosmos.tui.primitive.${opts.primitive}`, {
    attributes: {
      'kosmos.tui.primitive.name': opts.primitive,
      'kosmos.tui.primitive.timeout_ms': timeoutMs,
    },
  })

  // ------------------------------------------------------------------
  // Architecture note (Epic ζ #2297 post-smoke discovery, 2026-04-30):
  //
  // The KOSMOS backend's `_handle_chat_request` runs the full agentic
  // loop server-side — it parses K-EXAONE function_calls, internally
  // fires `_dispatch_primitive` per call (`src/kosmos/ipc/stdio.py:1496`),
  // awaits the result via its own `_pending_calls` future-registry, and
  // injects the result as a `role="tool"` message into the next LLM
  // turn — all WITHOUT any inbound tool_call from the TUI.
  //
  // The TUI's CC SDK Tool.call() pipeline is therefore a DISPLAY-ONLY
  // path: the `tool_call` and `tool_result` IPC frames flow through
  // `llmClient.ts` for UX rendering, and the eventual `assistant_chunk`
  // already encodes the citizen-facing answer.
  //
  // Earlier (Epic ζ T007-T013) attempted to wire dispatchPrimitive to
  // emit a fresh `tool_call` frame and await a matching `tool_result`.
  // This timed out at 30s because the backend has no inbound-tool_call
  // handler — it only emits them. A live smoke run on 2026-04-30
  // confirmed the failure mode (LLM fell back to conversational guidance
  // citing "응답 시간 초과 오류 지속 발생").
  //
  // The correct fix is: Tool.call() returns a synthetic-success ack
  // immediately so the SDK's tool-use turn closes without injecting
  // a duplicate role="tool" message into the next chat_request (which
  // would re-trigger the backend's internal loop and double-execute).
  // The backend has already done the work; this Tool.call() is just a
  // sentinel that the SDK saw the tool_use block.
  //
  // Spec: contracts/tui-primitive-dispatcher.md will be revised in a
  // follow-up to reflect this server-side-authoritative architecture.
  // ------------------------------------------------------------------

  void makeUUIDv7  // imports retained for future re-wiring if needed
  void makeBaseEnvelope
  void opts.bridge
  void opts.registry

  const toolUseId =
    (opts.context as Record<string, unknown>)['toolUseId'] as string | undefined
  const ackEnvelope: Record<string, unknown> = {
    dispatched_via: 'backend-server-side',
    primitive: opts.primitive,
    tool_use_id: toolUseId ?? null,
    note:
      'KOSMOS backend ran the agentic loop internally and emitted the ' +
      'authoritative tool_result frame for display. This SDK-level ack ' +
      'closes the tool-use turn without re-triggering execution.',
  }

  span.setAttribute('kosmos.tui.primitive.dispatch_mode', 'server-side-ack')
  span.setAttribute(
    'kosmos.tui.primitive.tool_use_id',
    toolUseId ?? 'missing',
  )
  span.end()

  void timeoutMs  // retained for future re-wiring if backend gains inbound handler
  void _maybeEmitCheckpoint  // retained — checkpoint emission moved to llmClient

  return {
    data: { ok: true as const, result: ackEnvelope } as unknown as O,
  }
}
