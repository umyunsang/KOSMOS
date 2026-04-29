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
  // Step 2: Mint a fresh callId (UUIDv7)
  // ------------------------------------------------------------------
  const callId = makeUUIDv7()

  // ------------------------------------------------------------------
  // Step 3: Derive session / correlation IDs from context
  // The ToolUseContext carries toolUseId (per-tool-use) which we use
  // as correlationId; sessionId from ambient context options where
  // available.
  // ------------------------------------------------------------------
  const correlationId: string =
    (opts.context as Record<string, unknown>)['toolUseId'] as string ?? makeUUIDv7()
  const sessionId: string =
    (opts.context.options as Record<string, unknown>)['sessionId'] as string ??
    'unknown-session'

  // ------------------------------------------------------------------
  // Step 4: Construct ToolCallFrame
  // ------------------------------------------------------------------
  const baseEnv = makeBaseEnvelope({ sessionId, correlationId })
  const frame: ToolCallFrame = {
    ...baseEnv,
    kind: 'tool_call',
    role: 'tui',
    call_id: callId,
    name: opts.primitive,
    arguments: opts.args,
  } as unknown as ToolCallFrame

  // ------------------------------------------------------------------
  // Step 5: Register pending call + send frame
  // ------------------------------------------------------------------
  let resolvedFrame: ToolResultFrame | null = null
  let timedOut = false

  try {
    resolvedFrame = await new Promise<ToolResultFrame>((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        timedOut = true
        opts.registry.reject(
          callId,
          new Error('응답 시간이 초과되었습니다'),
        )
      }, timeoutMs)

      opts.registry.register({
        callId,
        primitive: opts.primitive,
        resolve,
        reject,
        timeoutHandle,
      })

      opts.bridge.send(frame)
    })
  } catch (err: unknown) {
    if (timedOut || (err instanceof Error && err.message === '응답 시간이 초과되었습니다')) {
      span.setAttribute('kosmos.tui.primitive.timeout', true)
      span.end()
      return {
        data: { ok: false, error: '응답 시간이 초과되었습니다' } as unknown as O,
      }
    }
    span.end()
    const msg = err instanceof Error ? err.message : String(err)
    return { data: { ok: false, error: msg } as unknown as O }
  }

  // ------------------------------------------------------------------
  // Step 6: Handle error or success envelope
  // ------------------------------------------------------------------
  const envelope = resolvedFrame.envelope as Record<string, unknown>

  // I-D7: error envelope passthrough
  if (envelope && envelope['error']) {
    const errPayload = envelope['error']
    const errMsg =
      typeof errPayload === 'string'
        ? errPayload
        : typeof errPayload === 'object' && errPayload !== null
          ? ((errPayload as Record<string, unknown>)['message'] as string | undefined) ??
            JSON.stringify(errPayload)
          : String(errPayload)

    _maybeEmitCheckpoint(opts.primitive, resolvedFrame)
    span.end()
    return { data: { ok: false, error: errMsg } as unknown as O }
  }

  // Success path
  _maybeEmitCheckpoint(opts.primitive, resolvedFrame)
  span.end()
  return { data: { ok: true as const, result: envelope } as unknown as O }
}
