// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · Anthropic→FriendliAI LLM client.
//
// Emulates the `@anthropic-ai/sdk` Messages.create streaming-generator surface
// consumed by QueryEngine.ts and query.ts, but all wire traffic goes over the
// Spec 032 stdio IPC bridge (TS) → Python backend → FriendliAI Serverless.
// TS never speaks HTTPS to FriendliAI directly (docs/vision.md § L1-A A1,
// Constitution Principle I rewrite boundary).
//
// T007: stream() — async generator body translating Spec 032 frames into
//       KosmosRawMessageStreamEvent values.
// T008: complete() — drives stream() to exhaustion, returns KosmosMessageFinal.
// T009: OTEL gen_ai.client.invoke span — emitted on every stream() call.
// T010: kosmos.prompt.hash — sourced from bridge.systemPromptHash if available;
//       placeholder empty string with TODO(T091) if not yet wired.

import { trace, SpanStatusCode } from '@opentelemetry/api'
import type { Span } from '@opentelemetry/api'
import type { IPCBridge } from './bridge.js'
import { makeUUIDv7, makeBaseEnvelope } from './envelope.js'
import type { UserInputFrame, AssistantChunkFrame, ErrorFrame, BackpressureSignalFrame, ToolCallFrame } from './frames.generated.js'
import type {
  KosmosMessageStreamParams,
  KosmosRawMessageStreamEvent,
  KosmosMessageFinal,
  KosmosUsage,
  KosmosContentBlockParam,
  KosmosStopReason,
} from './llmTypes.js'

export const KOSMOS_DEFAULT_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'

export type LLMClientErrorClass = 'llm' | 'tool' | 'network'

export class LLMClientError extends Error {
  readonly errorClass: LLMClientErrorClass
  readonly code: string
  readonly retryAfterMs?: number

  constructor(
    errorClass: LLMClientErrorClass,
    code: string,
    message: string,
    retryAfterMs?: number,
  ) {
    super(message)
    this.name = 'LLMClientError'
    this.errorClass = errorClass
    this.code = code
    this.retryAfterMs = retryAfterMs
  }
}

export interface LLMClientOptions {
  bridge: IPCBridge
  model?: string
  sessionId: string
}

// ---------------------------------------------------------------------------
// OTEL tracer (T009)
// ---------------------------------------------------------------------------

const _tracer = trace.getTracer('kosmos.tui.llm', '0.1.0')

// ---------------------------------------------------------------------------
// Internal usage accumulator populated from the done-frame trailer
// ---------------------------------------------------------------------------

interface _TurnAccumulator {
  messageId: string | null
  contentBlocks: KosmosContentBlockParam[]
  usage: KosmosUsage
  stopReason: KosmosStopReason
  blockIndex: number
  seenFirstChunk: boolean
}

function _defaultAccumulator(): _TurnAccumulator {
  return {
    messageId: null,
    contentBlocks: [],
    usage: { input_tokens: 0, output_tokens: 0 },
    stopReason: 'end_turn',
    blockIndex: 0,
    seenFirstChunk: false,
  }
}

// ---------------------------------------------------------------------------
// Helper: extract usage from an AssistantChunkFrame done-trailer.
//
// Spec 032 does not currently define a typed usage payload on the frame itself;
// the Python backend is expected to embed usage counts in the frame's `trailer`
// extra fields or in a sibling ephemeral dict.  Until the backend-side contract
// is finalised in Spec 032 US4, we read from `(frame as any).usage` first
// (a forward-compatible extension field the backend may include) and fall back
// to zeros.  A TODO(T091) marks the binding point for the actual backend wiring.
// ---------------------------------------------------------------------------

function _extractUsage(frame: AssistantChunkFrame): KosmosUsage {
  // TODO(T091): Once the Python backend embeds usage in the done-frame's trailer
  // extension fields, read them here.  For now, read from an optional `usage`
  // property that the backend may attach to the frame as a forward-compat field.
  const raw = (frame as Record<string, unknown>)['usage']
  if (raw && typeof raw === 'object') {
    const u = raw as Record<string, unknown>
    return {
      input_tokens: typeof u['input_tokens'] === 'number' ? u['input_tokens'] : 0,
      output_tokens: typeof u['output_tokens'] === 'number' ? u['output_tokens'] : 0,
      cache_read_input_tokens:
        typeof u['cache_read_input_tokens'] === 'number'
          ? u['cache_read_input_tokens']
          : undefined,
    }
  }
  return { input_tokens: 0, output_tokens: 0 }
}

/**
 * LLMClient — stdio-IPC-backed LLM client.
 *
 * Contracts/llm-client.md § 1.1 / § 1.2 define the full surface.
 */
export class LLMClient {
  readonly bridge: IPCBridge
  readonly model: string
  readonly sessionId: string

  constructor(opts: LLMClientOptions) {
    this.bridge = opts.bridge
    this.model = opts.model ?? KOSMOS_DEFAULT_MODEL
    this.sessionId = opts.sessionId
  }

  // -------------------------------------------------------------------------
  // T007: stream() — async generator body
  // -------------------------------------------------------------------------

  /**
   * Begin an LLM turn.
   *
   * Yields {@link KosmosRawMessageStreamEvent} values, returning a
   * {@link KosmosMessageFinal} from the generator on normal completion.
   *
   * Implementation follows contracts/llm-client.md § 1.1 / § 1.2 (G1..G6):
   *  G1 — no direct HTTPS; all traffic via bridge.send().
   *  G2 — exactly one OTEL gen_ai.client.invoke span per call.
   *  G3 — model is forwarded from constructor (caller's responsibility).
   *  G4 — ErrorFrame(class=llm, code=auth) → immediate LLMClientError, no retry.
   *  G5 — BackpressureSignalFrame → pause until retry_after_ms; Python owns retry.
   *  G6 — return value carries stop_reason + usage from done-frame trailer.
   */
  async *stream(
    params: KosmosMessageStreamParams,
  ): AsyncGenerator<KosmosRawMessageStreamEvent, KosmosMessageFinal, void> {
    // ------------------------------------------------------------------
    // Step 1: mint a fresh correlation_id for this turn (V1 invariant).
    // ------------------------------------------------------------------
    const correlationId = makeUUIDv7()

    // ------------------------------------------------------------------
    // Step 2: open OTEL span gen_ai.client.invoke (T009).
    //
    // T010: kosmos.prompt.hash — read from bridge.systemPromptHash if
    // present; US4 task T091 wires the actual handshake extension.
    // TODO(T091): replace placeholder once bridge exposes systemPromptHash.
    // ------------------------------------------------------------------
    const promptHash: string = (this.bridge as unknown as Record<string, unknown>)['systemPromptHash'] as string ?? ''
    // TODO(T091): Once US4 wires bridge.systemPromptHash from the backend
    // handshake, the placeholder above becomes the real 64-char SHA-256 hex.

    const span: Span = _tracer.startSpan('gen_ai.client.invoke', {
      attributes: {
        'gen_ai.system': 'friendli_exaone',
        'gen_ai.operation.name': 'chat',
        'gen_ai.request.model': this.model,
        'gen_ai.request.max_tokens': params.max_tokens,
        ...(params.temperature !== undefined
          ? { 'gen_ai.request.temperature': params.temperature }
          : {}),
        'kosmos.correlation_id': correlationId,
        'kosmos.session_id': this.sessionId,
        // T010: kosmos.prompt.hash from bridge handshake metadata.
        'kosmos.prompt.hash': promptHash,
      },
    })

    // ------------------------------------------------------------------
    // Per-turn state accumulator (used to construct the return value).
    // ------------------------------------------------------------------
    const acc = _defaultAccumulator()

    try {
      // ----------------------------------------------------------------
      // Step 3: construct UserInputFrame.
      //
      // The UserInputFrame shape is defined in frames.generated.ts; `text`
      // carries the last user message.  System prompt (params.system) is
      // loaded once per session at handshake time and cached on the bridge;
      // every UserInputFrame is correlated with it implicitly via the
      // bridge's cached session state.  We do NOT embed it in the frame.
      //
      // TODO(T007b): params.tools — the current UserInputFrame schema has
      // no slot for a tool-definition list.  When Spec 032 adds a
      // `tool_hints` field to UserInputFrame, forward params.tools here.
      // ----------------------------------------------------------------

      // Resolve last user message text.
      const lastMessage = params.messages[params.messages.length - 1]
      let userText = ''
      if (lastMessage) {
        if (typeof lastMessage.content === 'string') {
          userText = lastMessage.content
        } else {
          // Concatenate text blocks; ignore non-text (tool_use, tool_result).
          userText = lastMessage.content
            .filter((b): b is { type: 'text'; text: string } => b.type === 'text')
            .map(b => b.text)
            .join('')
        }
      }

      const baseEnvelope = makeBaseEnvelope({
        sessionId: this.sessionId,
        correlationId,
      })

      const userInputFrame: UserInputFrame = {
        ...baseEnvelope,
        kind: 'user_input',
        role: 'tui',
        text: userText,
      }

      // ----------------------------------------------------------------
      // Step 4: send the frame.
      // ----------------------------------------------------------------
      const sent = this.bridge.send(userInputFrame)
      if (!sent) {
        throw new LLMClientError(
          'network',
          'ipc_transport',
          'Backend has exited; cannot start LLM turn',
        )
      }

      // ----------------------------------------------------------------
      // Step 5: consume inbound frames filtered on correlation_id.
      // ----------------------------------------------------------------
      let streamDone = false

      for await (const frame of this.bridge.frames()) {
        // Filter: only process frames for this turn's correlation_id.
        if (frame.correlation_id !== correlationId) continue

        // ---- AssistantChunkFrame ----------------------------------------
        if (frame.kind === 'assistant_chunk') {
          const chunk = frame as AssistantChunkFrame

          if (!chunk.done) {
            // First chunk: emit message_start + content_block_start.
            if (!acc.seenFirstChunk) {
              acc.seenFirstChunk = true
              acc.messageId = chunk.message_id

              yield {
                type: 'message_start',
                message: {
                  id: chunk.message_id,
                  role: 'assistant',
                  model: this.model,
                },
              } satisfies KosmosRawMessageStreamEvent

              yield {
                type: 'content_block_start',
                index: 0,
                content_block: { type: 'text', text: '' },
              } satisfies KosmosRawMessageStreamEvent

              acc.blockIndex = 0
            }

            // Emit text delta (even if delta is empty — forward compat).
            if (chunk.delta.length > 0) {
              yield {
                type: 'content_block_delta',
                index: acc.blockIndex,
                delta: { type: 'text_delta', text: chunk.delta },
              } satisfies KosmosRawMessageStreamEvent

              // Accumulate text into the content block for the final object.
              const existing = acc.contentBlocks[acc.blockIndex]
              if (existing && existing.type === 'text') {
                existing.text += chunk.delta
              } else {
                // First delta for this block index.
                acc.contentBlocks[acc.blockIndex] = { type: 'text', text: chunk.delta }
              }
            }
          } else {
            // done=true: terminal chunk (V2 invariant satisfied here).

            // If we never saw a first chunk (edge: backend sends done=true
            // immediately on an empty response), bootstrap the message events.
            if (!acc.seenFirstChunk) {
              acc.seenFirstChunk = true
              acc.messageId = chunk.message_id
              yield {
                type: 'message_start',
                message: { id: chunk.message_id, role: 'assistant', model: this.model },
              } satisfies KosmosRawMessageStreamEvent
              yield {
                type: 'content_block_start',
                index: 0,
                content_block: { type: 'text', text: '' },
              } satisfies KosmosRawMessageStreamEvent
              acc.blockIndex = 0
            }

            // Emit any final delta text if present.
            if (chunk.delta.length > 0) {
              yield {
                type: 'content_block_delta',
                index: acc.blockIndex,
                delta: { type: 'text_delta', text: chunk.delta },
              } satisfies KosmosRawMessageStreamEvent
              const existing = acc.contentBlocks[acc.blockIndex]
              if (existing && existing.type === 'text') {
                existing.text += chunk.delta
              } else {
                acc.contentBlocks[acc.blockIndex] = { type: 'text', text: chunk.delta }
              }
            }

            // Extract usage from the done-frame.
            const usage = _extractUsage(chunk)
            acc.usage = usage

            yield { type: 'content_block_stop', index: acc.blockIndex } satisfies KosmosRawMessageStreamEvent

            yield {
              type: 'message_delta',
              delta: { stop_reason: acc.stopReason },
              usage,
            } satisfies KosmosRawMessageStreamEvent

            yield { type: 'message_stop' } satisfies KosmosRawMessageStreamEvent

            streamDone = true
            break
          }
        }

        // ---- ToolCallFrame ----------------------------------------------
        else if (frame.kind === 'tool_call') {
          const toolFrame = frame as ToolCallFrame
          // tool_call frames may arrive interleaved with text streaming in
          // a multi-turn or parallel-tool scenario. Emit as a content block.
          const toolBlockIndex = ++acc.blockIndex
          yield {
            type: 'content_block_start',
            index: toolBlockIndex,
            content_block: {
              type: 'tool_use',
              id: toolFrame.call_id,
              name: toolFrame.name,
              input: toolFrame.arguments as Record<string, unknown>,
            },
          } satisfies KosmosRawMessageStreamEvent

          yield {
            type: 'content_block_stop',
            index: toolBlockIndex,
          } satisfies KosmosRawMessageStreamEvent

          acc.contentBlocks[toolBlockIndex] = {
            type: 'tool_use',
            id: toolFrame.call_id,
            name: toolFrame.name,
            input: toolFrame.arguments as Record<string, unknown>,
          }
        }

        // ---- ErrorFrame -------------------------------------------------
        else if (frame.kind === 'error') {
          const errFrame = frame as ErrorFrame
          // Map ErrorFrame to LLMClientError (G4 fast-path for auth errors).
          const details = errFrame.details as Record<string, unknown>
          const errClass: LLMClientErrorClass =
            details['class'] === 'llm' || details['class'] === 'tool'
              ? (details['class'] as LLMClientErrorClass)
              : 'network'
          throw new LLMClientError(
            errClass,
            errFrame.code,
            errFrame.message,
          )
        }

        // ---- BackpressureSignalFrame (source=upstream_429) ---------------
        else if (frame.kind === 'backpressure') {
          const bpFrame = frame as BackpressureSignalFrame
          // G5: pause until retry_after_ms, then continue (Python owns retry).
          if (bpFrame.source === 'upstream_429' && bpFrame.retry_after_ms != null && bpFrame.retry_after_ms > 0) {
            await new Promise<void>((resolve) =>
              setTimeout(resolve, bpFrame.retry_after_ms!),
            )
          }
          // continue consuming the frame iterable — no re-send.
          continue
        }

        // ---- Unknown frame kind (matching correlation_id) ----------------
        else {
          // Log at WARN and skip (forward compatibility).
          process.stderr.write(
            `[KOSMOS LLMClient WARN] Unexpected frame kind="${(frame as { kind?: string }).kind}" for correlation_id=${correlationId}\n`,
          )
        }
      }

      // ------------------------------------------------------------------
      // Step 6: stream closed without done=true → protocol violation (V2).
      // ------------------------------------------------------------------
      if (!streamDone) {
        throw new LLMClientError(
          'network',
          'ipc_transport',
          'Stream ended before done=true',
        )
      }

      // ------------------------------------------------------------------
      // Step 7: finalize OTEL span — status OK (T009).
      // ------------------------------------------------------------------
      span.setAttribute('gen_ai.usage.input_tokens', acc.usage.input_tokens)
      span.setAttribute('gen_ai.usage.output_tokens', acc.usage.output_tokens)
      if (acc.usage.cache_read_input_tokens !== undefined) {
        span.setAttribute('gen_ai.usage.cache_read_input_tokens', acc.usage.cache_read_input_tokens)
      }
      span.setStatus({ code: SpanStatusCode.OK })
      span.end()

      // ------------------------------------------------------------------
      // Step 8: return KosmosMessageFinal (G6).
      // ------------------------------------------------------------------
      const finalMessage: KosmosMessageFinal = {
        id: acc.messageId ?? correlationId,
        role: 'assistant',
        model: this.model,
        content: acc.contentBlocks,
        stop_reason: acc.stopReason,
        usage: acc.usage,
      }

      return finalMessage
    } catch (err: unknown) {
      // Finalize OTEL span with ERROR status.
      if (err instanceof LLMClientError) {
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: err.message,
        })
        span.setAttribute('error.type', `${err.errorClass}:${err.code}`)
        span.end()
        throw err
      }
      // Unexpected non-LLMClientError (e.g. bridge internals).
      const msg = err instanceof Error ? err.message : String(err)
      span.setStatus({ code: SpanStatusCode.ERROR, message: msg })
      span.setAttribute('error.type', 'network:unknown')
      span.end()
      throw new LLMClientError('network', 'unknown', msg)
    }
  }

  // -------------------------------------------------------------------------
  // T008: complete() — drives stream() to exhaustion
  // -------------------------------------------------------------------------

  /**
   * Non-streaming convenience — awaits stream() and collects text deltas into
   * a single {@link KosmosMessageFinal}.
   *
   * The generator's return value already includes the assembled content blocks
   * built inside stream(); we simply drain events and return the final object.
   */
  async complete(params: KosmosMessageStreamParams): Promise<KosmosMessageFinal> {
    const chunks: string[] = []
    let final: KosmosMessageFinal | null = null

    const gen = this.stream(params)
    while (true) {
      const result = await gen.next()
      if (result.done) {
        // result.value is the KosmosMessageFinal returned by stream().
        final = result.value as KosmosMessageFinal
        break
      }
      const event = result.value
      if (
        event.type === 'content_block_delta' &&
        event.delta.type === 'text_delta'
      ) {
        chunks.push(event.delta.text)
      }
    }

    if (final !== null) {
      return final
    }

    // Fallback: fabricate a minimal KosmosMessageFinal from accumulated chunks.
    // This path should not be reached in normal operation because stream()
    // always returns the final object — it's here as a safety net.
    return {
      id: makeUUIDv7(),
      role: 'assistant',
      model: this.model,
      content: [{ type: 'text', text: chunks.join('') }],
      stop_reason: 'end_turn',
      usage: { input_tokens: 0, output_tokens: 0 },
    }
  }
}
