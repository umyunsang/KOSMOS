import { randomUUID } from 'crypto'
import { APIUserAbortError } from 'src/sdk-compat.js'
import { autoCompactIfNeeded } from '../services/compact/autoCompact.js'
import { microcompactMessages } from '../services/compact/microCompact.js'
import { getOrCreateKosmosBridge, getKosmosBridgeSessionId } from '../ipc/bridgeSingleton.js'
import type { ChatMessage, ChatRequestFrame, IPCFrame } from '../ipc/frames.generated.js'
import { createAssistantMessage, createSystemMessage, SYNTHETIC_MODEL } from '../utils/messages.js'

/**
 * KOSMOS-1633 P3 wire-up — replaces the Anthropic-SDK queryModelWithStreaming.
 *
 * Bridges CC's `query()` agentic loop to the Spec 1978 ADR-0001 backend
 * (kosmos.ipc.stdio._handle_chat_request) over the existing Spec 032 IPC
 * envelope. CC's call shape is preserved: yields `AssistantMessage` on
 * completion (CC's query.ts collapses streaming events into a single
 * assistant message anyway). System prompt, tools, and signal are wired
 * through; the rich `options.*` shape is accepted but most fields are
 * informational at this layer — the backend owns model selection,
 * streaming, and tool-call dispatch.
 *
 * Single-frame protocol on this hop:
 *   TUI → backend: ChatRequestFrame { messages, system?, tools? }
 *   backend → TUI: AssistantChunkFrame{...delta, done:true} | ErrorFrame
 *
 * The backend's CC-engine-mirroring native FC dispatch handles tool calls
 * server-side and streams only the final assistant text deltas back; tool
 * results are emitted as separate frames consumed by other TUI subsystems.
 */
async function* queryModelWithStreaming(params: {
  messages: readonly unknown[]
  systemPrompt: unknown
  thinkingConfig?: unknown
  tools?: unknown
  signal?: AbortSignal
  options?: { model?: string; querySource?: string; [k: string]: unknown }
}): AsyncGenerator<unknown> {
  const { messages, systemPrompt, signal } = params
  const correlationId = randomUUID()
  // Outer transcript uuid + inner BetaMessage.id are fixed at turn start so
  // the final AssistantMessage carries stable React keys; rebuilding either
  // mid-stream would collide with the streamingText preview's atomic
  // transition (utils/messages.ts:2984 onStreamingText(() => null)).
  const messageUuid = randomUUID()
  const innerMessageId = randomUUID()
  const turnStartedAt = performance.now()
  const __t = (s: string) => {
    if (process.env.KOSMOS_QUERY_TRACE === '1') {
      try { require('fs').writeSync(2, `[KOSMOS-QUERY] ${s}\n`) } catch {}
    }
  }
  __t(`callModel:enter messages=${messages.length}`)

  // Convert CC `Message[]` → ChatRequestFrame.messages.
  // Tolerates the loose stub-typed Message shape; only user/assistant turns
  // with extractable text are forwarded. Tool messages stay server-side.
  const chatMessages: ChatMessage[] = []
  for (const m of messages) {
    const ma = m as { type?: string; message?: { role?: string; content?: unknown } }
    if (!ma || (ma.type !== 'user' && ma.type !== 'assistant')) continue
    const role: 'user' | 'assistant' = ma.type === 'user' ? 'user' : 'assistant'
    const content = extractText(ma.message?.content)
    if (!content) continue
    chatMessages.push({ role, content })
  }
  if (chatMessages.length === 0) {
    chatMessages.push({ role: 'user', content: '' })
  }

  const systemText = extractText(systemPrompt)
  const bridge = getOrCreateKosmosBridge()
  const sessionId = getKosmosBridgeSessionId()

  const frame: ChatRequestFrame = {
    session_id: sessionId,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'tui',
    kind: 'chat_request',
    messages: chatMessages as ChatRequestFrame['messages'],
    ...(systemText ? { system: systemText } : {}),
  }

  // Flip the spinner from idle → 'requesting' before the network round-trip
  // so the user sees instant feedback even if the first backend chunk takes
  // a few seconds (handleMessageFromStream:line 2989).
  yield { type: 'stream_request_start' as const }

  __t(`sending chat_request corr=${correlationId} chatMessages=${chatMessages.length}`)
  const sent = bridge.send(frame as unknown as IPCFrame)
  __t(`bridge.send returned ${sent}`)
  if (!sent) {
    throw new Error('KOSMOS bridge send failed (backend exited)')
  }

  // Stream-event projection — yield CC-shape Anthropic SSE events per
  // assistant_chunk frame so handleMessageFromStream pipes text_delta
  // events into onStreamingText for incremental paint
  // (utils/messages.ts:3055-3059). The terminal AssistantMessage with the
  // accumulated text is yielded once on done=true; its outer uuid + inner
  // message.id are pinned to turn-start values so the React message store
  // never sees a duplicate key (the streaming preview lives in separate
  // React state, atomically cleared at line 2984 when the final message
  // arrives).
  let accumulated = ''
  let messageStartEmitted = false
  let frameCount = 0
  for await (const f of bridge.frames()) {
    frameCount++
    if (frameCount <= 20) {
      const fAll = f as { kind?: string; correlation_id?: string; delta?: string; done?: boolean; message_id?: string }
      __t(`recv #${frameCount} kind=${fAll.kind} corr=${fAll.correlation_id?.slice(-8)} done=${fAll.done} delta=${JSON.stringify(fAll.delta).slice(0, 60)}`)
    }
    if (signal?.aborted) {
      throw new APIUserAbortError()
    }
    const fa = f as {
      kind?: string
      correlation_id?: string
      delta?: string
      done?: boolean
      message?: string
      // tool_call fields
      call_id?: string
      name?: string
      arguments?: unknown
      // tool_result fields
      envelope?: { kind?: string; [k: string]: unknown }
    }
    if (fa.correlation_id !== correlationId) continue
    if (fa.kind === 'assistant_chunk') {
      const deltaText = fa.delta ?? ''
      // First chunk: emit message_start (carries ttftMs for OTPS) +
      // content_block_start so the spinner flips to 'responding'.
      if (!messageStartEmitted) {
        const ttftMs = performance.now() - turnStartedAt
        yield {
          type: 'stream_event' as const,
          event: {
            type: 'message_start' as const,
            message: {
              id: innerMessageId,
              type: 'message',
              role: 'assistant',
              content: [],
              model: SYNTHETIC_MODEL,
              stop_reason: null,
              stop_sequence: null,
              usage: {
                input_tokens: 0,
                output_tokens: 0,
                cache_creation_input_tokens: 0,
                cache_read_input_tokens: 0,
              },
            },
          },
          ttftMs,
        }
        yield {
          type: 'stream_event' as const,
          event: {
            type: 'content_block_start' as const,
            index: 0,
            content_block: { type: 'text' as const, text: '' },
          },
        }
        messageStartEmitted = true
      }

      accumulated += deltaText
      if (deltaText.length > 0) {
        yield {
          type: 'stream_event' as const,
          event: {
            type: 'content_block_delta' as const,
            index: 0,
            delta: { type: 'text_delta' as const, text: deltaText },
          },
        }
      }

      if (fa.done) {
        // CC mirror (claude.ts:2192-2303): the AssistantMessage is yielded
        // *inside* the content_block_stop branch (line 2210) before the
        // outer for-loop yields stream_event{content_block_stop} (line
        // 2299). handleMessageFromStream then runs onStreamingText(() =>
        // null) at line 2984 against the AssistantMessage, clearing the
        // streamingText preview before message_delta / message_stop drive
        // the spinner from 'responding' to 'tool-use'. Same order here so
        // the deferred → final transition is atomic and matches CC behavior.
        // K-EXAONE often prefixes its first delta with `\n\n`; trim leading
        // whitespace so the rendered turn doesn't open with blank lines.
        const finalMsg = createAssistantMessage({ content: accumulated.trimStart() }) as {
          uuid: string
          message: { id: string }
        }
        finalMsg.uuid = messageUuid
        finalMsg.message.id = innerMessageId
        yield finalMsg
        yield {
          type: 'stream_event' as const,
          event: { type: 'content_block_stop' as const, index: 0 },
        }
        yield {
          type: 'stream_event' as const,
          event: {
            type: 'message_delta' as const,
            delta: { stop_reason: 'end_turn', stop_sequence: null },
            usage: { output_tokens: 0 },
          },
        }
        yield {
          type: 'stream_event' as const,
          event: { type: 'message_stop' as const },
        }
        return
      }
    } else if (fa.kind === 'tool_call') {
      // Backend executes the tool itself (Spec 1978 ADR-0001 _pending_calls
      // futures); the TUI only paints a display-only progress line so users
      // see what the agentic loop is doing in real time.
      const argsPreview = summarizeArgs(fa.arguments)
      yield createSystemMessage(`🔧 ${fa.name ?? '(unknown tool)'}${argsPreview}`, 'info', fa.call_id)
    } else if (fa.kind === 'tool_result') {
      // Tool finished server-side; surface the outcome as a progress line.
      // The envelope's `kind` is the result discriminator (ok / error / etc).
      const env = fa.envelope ?? {}
      const status = (env.kind as string | undefined) ?? 'done'
      const summary = summarizeResult(env)
      yield createSystemMessage(`✓ ${status}${summary}`, 'info', fa.call_id)
    } else if (fa.kind === 'permission_request') {
      // KOSMOS permission gauntlet — backend asks before running gated
      // primitives (submit, etc). The full UI modal (consent capture +
      // session-scope cache + audit ledger receipt) is a separate spec;
      // this minimum wire surfaces the request and auto-denies so the
      // backend can move on with a synthetic error instead of hanging on
      // its 60s timeout.
      const fp = f as {
        request_id?: string
        primitive_kind?: string
        description_ko?: string
        description_en?: string
        risk_level?: string
      }
      const desc = fp.description_ko || fp.description_en || fp.primitive_kind || '(unknown primitive)'
      const risk = fp.risk_level ? ` [risk=${fp.risk_level}]` : ''
      yield createSystemMessage(`🛡️  permission_request${risk} ${desc} — 자동 거부 (UI 모달 미구현, 별도 spec)`, 'warning', fp.request_id)
      const respFrame = {
        session_id: sessionId,
        correlation_id: correlationId,
        ts: new Date().toISOString(),
        role: 'tui' as const,
        kind: 'permission_response' as const,
        request_id: fp.request_id ?? '',
        decision: 'denied' as const,
      }
      bridge.send(respFrame as unknown as IPCFrame)
    } else if (fa.kind === 'error') {
      const reason = fa.message ?? 'KOSMOS backend error'
      // CC mirror: yield the (error) AssistantMessage first so
      // handleMessageFromStream clears the streamingText preview, then
      // close the open block + message so the spinner reaches its terminal
      // state.
      yield createAssistantMessage({ content: `[KOSMOS backend error] ${reason}` })
      if (messageStartEmitted) {
        yield {
          type: 'stream_event' as const,
          event: { type: 'content_block_stop' as const, index: 0 },
        }
        yield {
          type: 'stream_event' as const,
          event: { type: 'message_stop' as const },
        }
      }
      return
    }
  }
  // Stream ended without a `done:true` chunk — yield the accumulated text
  // (so the turn isn't silently dropped), then close any open block in CC's
  // AssistantMessage-first order.
  const finalMsg = createAssistantMessage({ content: accumulated.trimStart() }) as {
    uuid: string
    message: { id: string }
  }
  finalMsg.uuid = messageUuid
  finalMsg.message.id = innerMessageId
  yield finalMsg
  if (messageStartEmitted) {
    yield {
      type: 'stream_event' as const,
      event: { type: 'content_block_stop' as const, index: 0 },
    }
    yield {
      type: 'stream_event' as const,
      event: { type: 'message_stop' as const },
    }
  }
}

function summarizeArgs(args: unknown): string {
  if (!args || typeof args !== 'object') return ''
  try {
    const json = JSON.stringify(args)
    return json.length > 80 ? ` ${json.slice(0, 77)}…` : ` ${json}`
  } catch {
    return ''
  }
}

function summarizeResult(env: { [k: string]: unknown }): string {
  const summary = (env.summary ?? env.message ?? env.text) as unknown
  if (typeof summary === 'string' && summary.length > 0) {
    return summary.length > 80 ? ` ${summary.slice(0, 77)}…` : ` ${summary}`
  }
  return ''
}

function extractText(v: unknown): string {
  if (typeof v === 'string') return v
  if (Array.isArray(v)) {
    return v
      .map((b) => {
        if (typeof b === 'string') return b
        const ba = b as { text?: string; content?: string }
        return ba?.text ?? ba?.content ?? ''
      })
      .filter(Boolean)
      .join('\n')
  }
  return ''
}

// -- deps

// I/O dependencies for query(). Passing a `deps` override into QueryParams
// lets tests inject fakes directly instead of spyOn-per-module — the most
// common mocks (callModel, autocompact) are each spied in 6-8 test files
// today with module-import-and-spy boilerplate.
//
// Using `typeof fn` keeps signatures in sync with the real implementations
// automatically. This file imports the real functions for both typing and
// the production factory — tests that import this file for typing are
// already importing query.ts (which imports everything), so there's no
// new module-graph cost.
//
// Scope is intentionally narrow (4 deps) to prove the pattern. Followup
// PRs can add runTools, handleStopHooks, logEvent, queue ops, etc.
export type QueryDeps = {
  // -- model
  callModel: typeof queryModelWithStreaming

  // -- compaction
  microcompact: typeof microcompactMessages
  autocompact: typeof autoCompactIfNeeded

  // -- platform
  uuid: () => string
}

export function productionDeps(): QueryDeps {
  return {
    callModel: queryModelWithStreaming,
    microcompact: microcompactMessages,
    autocompact: autoCompactIfNeeded,
    uuid: randomUUID,
  }
}
