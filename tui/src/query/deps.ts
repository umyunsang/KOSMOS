import { randomUUID } from 'crypto'
import { APIUserAbortError } from 'src/sdk-compat.js'
import { autoCompactIfNeeded } from '../services/compact/autoCompact.js'
import { microcompactMessages } from '../services/compact/microCompact.js'
import { getOrCreateKosmosBridge, getKosmosBridgeSessionId } from '../ipc/bridgeSingleton.js'
import type { ChatMessage, ChatRequestFrame, IPCFrame } from '../ipc/frames.generated.js'
import { getToolDefinitionsForFrame } from './toolSerialization.js'
import { createAssistantMessage, createSystemMessage, createUserMessage, SYNTHETIC_MODEL } from '../utils/messages.js'

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

  // Publish the active tool inventory to the LLM on every turn (FR-001).
  // Backend authoritative-execution rule (FR-005): backend rejects any
  // tool name not in its registry, so unknown entries here are harmless.
  // Per data-model.md § 1: emit per turn, no caching.
  const tools = await getToolDefinitionsForFrame()

  const frame: ChatRequestFrame = {
    session_id: sessionId,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'tui',
    kind: 'chat_request',
    messages: chatMessages as ChatRequestFrame['messages'],
    ...(systemText ? { system: systemText } : {}),
    tools: tools as ChatRequestFrame['tools'],
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
  // Epic #2077 T012 — turn-scoped CC content-block index. Index 0 is the
  // text block opened on the first ``assistant_chunk``; tool_use blocks
  // claim 1, 2, 3, … in arrival order. ``pendingContentBlocks`` mirrors the
  // CC pattern of ``messages.ts:normalizeContentFromAPI`` — every tool_use
  // block emitted during the turn is also accumulated so the terminal
  // ``createAssistantMessage`` carries the canonical ``BetaContentBlock[]``
  // shape (text + tool_use blocks) instead of a raw string. Required by
  // FR-006 (transcript-native invocation record) + FR-009 (one-to-one
  // pairing with tool_result content blocks).
  let blockIndex = 0
  const pendingContentBlocks: Array<{
    type: 'tool_use'
    id: string
    name: string
    input: unknown
  }> = []
  // Epic #2077 T016 — FR-009 one-to-one pairing invariant.
  // Every tool_call frame registers its call_id here; every tool_result frame
  // checks against this set. An unmatched tool_use_id surfaces as a visible
  // error (orphan), satisfying FR-009 "no orphan results".
  const seenToolUseIds = new Set<string>()
  for await (const f of bridge.frames()) {
    frameCount++
    if (frameCount <= 30) {
      const fAll = f as { kind?: string; correlation_id?: string; delta?: string; thinking?: string; done?: boolean; message_id?: string }
      const dStr = JSON.stringify(fAll.delta ?? '').slice(0, 40)
      const tStr = JSON.stringify(fAll.thinking ?? '').slice(0, 40)
      __t(`recv #${frameCount} kind=${fAll.kind} corr=${fAll.correlation_id?.slice(-8)} done=${fAll.done} delta=${dStr} thinking=${tStr}`)
    }
    if (signal?.aborted) {
      throw new APIUserAbortError()
    }
    const fa = f as {
      kind?: string
      correlation_id?: string
      delta?: string
      thinking?: string
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
      const thinkingText = fa.thinking ?? ''
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

      // K-EXAONE chain-of-thought channel — backend forwards
      // delta.reasoning_content here. Mirror Anthropic's thinking_delta
      // (kosmos/llm/_cc_reference/claude.ts:2148-2161). handleMessageFromStream
      // (utils/messages.ts:3080) routes thinking_delta through onUpdateLength
      // so AssistantThinkingMessage paints the reasoning inline.
      if (thinkingText.length > 0) {
        yield {
          type: 'stream_event' as const,
          event: {
            type: 'content_block_delta' as const,
            index: 0,
            delta: { type: 'thinking_delta' as const, thinking: thinkingText },
          },
        }
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
        // Epic #2077 T012 — when tool_use blocks accumulated during the
        // turn, the terminal AssistantMessage's content array carries them
        // alongside the text block (CC's BetaContentBlock[] shape). Empty
        // text + tool blocks stays valid (the assistant did only tool calls
        // before yielding); empty text + no tool blocks falls through to the
        // string path and createAssistantMessage substitutes NO_CONTENT_MESSAGE.
        const trimmedText = accumulated.trimStart()
        const finalContent =
          pendingContentBlocks.length > 0
            ? trimmedText.length > 0
              ? ([{ type: 'text' as const, text: trimmedText }, ...pendingContentBlocks] as Parameters<
                  typeof createAssistantMessage
                >[0]['content'])
              : (pendingContentBlocks as unknown as Parameters<
                  typeof createAssistantMessage
                >[0]['content'])
            : trimmedText
        const finalMsg = createAssistantMessage({ content: finalContent }) as {
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
      // Epic #2077 T012 (Step 5) — CC stream-event projection. Mirrors
      // ``_cc_reference/claude.ts:1995-2052`` (content_block_start tool_use
      // case). ``handleMessageFromStream`` (utils/messages.ts:3024-3037)
      // routes the start event into ``streamingToolUses`` so the existing
      // ``AssistantToolUseMessage`` component (367 LOC, REPL-mounted)
      // renders the invocation as a transcript-native record (FR-006).
      // ``pendingContentBlocks.push`` accumulates the same block so the
      // terminal AssistantMessage's ``content`` array carries it (CC's
      // ``messages.ts:normalizeContentFromAPI`` shape).
      const toolUseBlock = {
        type: 'tool_use' as const,
        id: fa.call_id ?? '',
        name: fa.name ?? '(unknown tool)',
        input: fa.arguments ?? {},
      }
      // Register the call_id so tool_result frames can verify pairing (FR-009).
      if (fa.call_id) {
        seenToolUseIds.add(fa.call_id)
      }
      pendingContentBlocks.push(toolUseBlock)
      blockIndex += 1
      yield {
        type: 'stream_event' as const,
        event: {
          type: 'content_block_start' as const,
          index: blockIndex,
          content_block: toolUseBlock,
        },
      }
      yield {
        type: 'stream_event' as const,
        event: { type: 'content_block_stop' as const, index: blockIndex },
      }
    } else if (fa.kind === 'tool_result') {
      // Epic #2077 T012 (Step 6) — user-role tool_result content block.
      // Mirrors ``_cc_reference/messages.ts:ensureToolResultPairing`` (line
      // 1150-1250). The result enters the transcript as a user message so
      // the next agentic-loop turn picks it up as LLM context (FR-010).
      // Pairing to the originating tool_use is by ``tool_use_id`` (FR-009).
      // ``is_error: true`` flag is set when the envelope's discriminator is
      // ``'error'`` so downstream rendering can surface it distinctly.
      //
      // Epic #2077 T016 — FR-009 orphan detection. A tool_result whose
      // call_id was NOT registered by any prior tool_call in this turn is an
      // orphan. The tool_result user-message is still emitted (transcript
      // preservation), but a visible error SystemMessage precedes it so the
      // citizen sees the pairing failure immediately.
      const resultCallId = fa.call_id ?? ''
      if (resultCallId && !seenToolUseIds.has(resultCallId)) {
        yield createSystemMessage(
          `tool_result_orphan: Tool result references unknown tool_use_id "${resultCallId}"`,
          'error',
          resultCallId,
        )
      }
      const env = fa.envelope ?? {}
      const isError = env.kind === 'error'
      yield createUserMessage({
        content: [
          {
            type: 'tool_result' as const,
            tool_use_id: resultCallId,
            content: JSON.stringify(env),
            ...(isError ? { is_error: true as const } : {}),
          },
        ] as Parameters<typeof createUserMessage>[0]['content'],
      })
    } else if (fa.kind === 'permission_request') {
      // Epic #2077 T020 (Step 7) — CC permission gauntlet wire. Routes the
      // backend permission_request frame through sessionStore's pending
      // permission slot (T018 / contracts/pending-permission-slot.md). The
      // store dispatches the request to the mounted PermissionGauntletModal
      // (T021), awaits the citizen's Y/N decision (or 5-min timeout), and
      // resolves the Promise here. We then send the permission_response
      // frame upstream with the resolved decision (granted / denied /
      // timeout). 'timeout' is treated by the backend as 'denied' for
      // fail-closed (Constitution §II + FR-017).
      const fp = f as {
        request_id?: string
        primitive_kind?: 'submit' | 'subscribe'
        description_ko?: string
        description_en?: string
        risk_level?: 'low' | 'medium' | 'high'
        receipt_id?: string
      }
      // Lazy import to avoid pulling the React store into modules that don't
      // need it; deps.ts is the only IPC↔store seam for this surface.
      const { setPendingPermission } = await import('../store/pendingPermissionSlot.js')
      const { dispatchSessionAction } = await import('../store/session-store.js')
      // Mirror the request into the reducer's pending_permission field so
      // KosmosIpcPermissionGauntletModal — which reads `s.pending_permission`
      // — actually paints. The pendingPermissionSlot owns the Promise +
      // FIFO queue lifecycle; the reducer field is a render-only mirror.
      const reducerRequest = {
        request_id: fp.request_id ?? '',
        correlation_id: correlationId,
        worker_id: '',
        primitive_kind: fp.primitive_kind ?? 'submit',
        description_ko: fp.description_ko ?? '',
        description_en: fp.description_en ?? '',
        risk_level: fp.risk_level ?? ('medium' as const),
      }
      dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: reducerRequest })
      try {
        var decision = await setPendingPermission({
          request_id: fp.request_id ?? '',
          primitive_kind: fp.primitive_kind ?? 'submit',
          description_ko: fp.description_ko ?? '',
          description_en: fp.description_en ?? '',
          risk_level: fp.risk_level ?? 'medium',
          receipt_id: fp.receipt_id ?? '',
          enqueued_at: performance.now(),
        })
      } finally {
        // Always clear the reducer mirror so a stale `pending_permission`
        // never blocks the next turn even on grant/deny/timeout/throw.
        dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
      }
      // Backend's permission_response schema accepts only granted/denied;
      // collapse 'timeout' into 'denied' at the wire boundary (the timeout
      // distinction stays in the audit ledger via Spec 035 receipt).
      const wireDecision = decision === 'timeout' ? 'denied' : decision
      const respFrame = {
        session_id: sessionId,
        correlation_id: correlationId,
        ts: new Date().toISOString(),
        role: 'tui' as const,
        kind: 'permission_response' as const,
        request_id: fp.request_id ?? '',
        decision: wireDecision,
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
  // AssistantMessage-first order. Epic #2077 T012 — same content-array
  // promotion as the done=true path so any tool_use blocks captured before
  // the abrupt close still appear in the persisted transcript.
  const trimmedTailText = accumulated.trimStart()
  const finalTailContent =
    pendingContentBlocks.length > 0
      ? trimmedTailText.length > 0
        ? ([{ type: 'text' as const, text: trimmedTailText }, ...pendingContentBlocks] as Parameters<
            typeof createAssistantMessage
          >[0]['content'])
        : (pendingContentBlocks as unknown as Parameters<typeof createAssistantMessage>[0]['content'])
      : trimmedTailText
  const finalMsg = createAssistantMessage({ content: finalTailContent }) as {
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

// ---------------------------------------------------------------------------
// Pure helpers (exported for unit tests — no bridge dependency)
// ---------------------------------------------------------------------------

// FR-009 pairing-invariant helpers live in a leaf module so unit tests can
// import them without dragging the deps.ts → autoCompact.ts → 'bun:bundle'
// chain through Bun's resolver.
export { isOrphanToolResult, orphanErrorMessage } from './orphanHelpers.js'
