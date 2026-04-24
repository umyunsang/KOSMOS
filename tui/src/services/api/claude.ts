// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 FR-007 / FR-017 IPC rewire.
//
// The legacy CC `services/api/claude` surface is preserved for `query.ts` /
// compact / WebSearch call-sites, but its runtime now routes through Spec 032
// stdio IPC to the Python backend (`uv run kosmos --ipc stdio`) rather than
// calling FriendliAI HTTPS directly. The Python backend wraps
// `kosmos.llm.client::LLMClient` and emits `AssistantChunkFrame` deltas that
// `ipc/llmClient.ts::stream()` translates back into Anthropic-shaped stream
// events. Here we collapse those events into the `{type:'assistant', message:
// {...}}` envelope `query.ts::queryLoop` consumes.

import type { KosmosUsage } from '../../ipc/llmTypes.js'
import { LLMClient } from '../../ipc/llmClient.js'
import {
  getOrCreateKosmosBridge,
  getKosmosBridgeSessionId,
} from '../../ipc/bridgeSingleton.js'

const KOSMOS_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'

export function getAPIMetadata(): Record<string, string> {
  return {}
}

export function getCacheControl(): null {
  return null
}

const EMPTY_USAGE: KosmosUsage = {
  input_tokens: 0,
  output_tokens: 0,
  cache_read_input_tokens: 0,
}

export function accumulateUsage(
  _a: KosmosUsage | undefined,
  _b: KosmosUsage | undefined,
): KosmosUsage {
  return EMPTY_USAGE
}

export function updateUsage(_usage: KosmosUsage | undefined): KosmosUsage {
  return EMPTY_USAGE
}

// ---------------------------------------------------------------------------
// Message normalization helpers — CC's internal shape → KosmosMessageParam.
// ---------------------------------------------------------------------------

type NormalizedMessage = { role: 'user' | 'assistant'; content: string }

function _normalizeOneMessage(m: unknown): NormalizedMessage | null {
  const mAny = m as {
    role?: string
    content?: unknown
    type?: string
    message?: { role?: string; content?: unknown }
  }
  const roleRaw =
    mAny.role ??
    mAny.message?.role ??
    (mAny.type === 'assistant' ? 'assistant' : 'user')
  const role: 'user' | 'assistant' =
    roleRaw === 'assistant' ? 'assistant' : 'user'

  const rawContent = mAny.content ?? mAny.message?.content
  let content = ''
  if (typeof rawContent === 'string') {
    content = rawContent
  } else if (Array.isArray(rawContent)) {
    const parts: string[] = []
    for (const block of rawContent) {
      if (typeof block === 'string') {
        parts.push(block)
        continue
      }
      const b = block as { type?: string; text?: string; content?: unknown }
      if (b?.type === 'text' && typeof b.text === 'string') {
        parts.push(b.text)
      } else if (
        b?.type === 'tool_result' &&
        typeof b.content === 'string'
      ) {
        parts.push(b.content)
      }
    }
    content = parts.filter(Boolean).join('\n')
  }
  if (!content) return null
  return { role, content }
}

function _coerceSystemPrompt(systemPrompt: unknown): string | undefined {
  if (Array.isArray(systemPrompt)) {
    const parts = systemPrompt
      .map((b) =>
        typeof b === 'string'
          ? b
          : typeof (b as { text?: unknown })?.text === 'string'
            ? (b as { text: string }).text
            : '',
      )
      .filter(Boolean)
    return parts.length > 0 ? parts.join('\n\n') : undefined
  }
  return typeof systemPrompt === 'string' && systemPrompt.length > 0
    ? systemPrompt
    : undefined
}

// ---------------------------------------------------------------------------
// Main entry point — IPC-routed LLM turn.
// ---------------------------------------------------------------------------

export async function* queryModelWithStreaming(params: {
  messages: ReadonlyArray<unknown>
  systemPrompt?: unknown
  options: { model?: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  const kosmosMessages: NormalizedMessage[] = []
  for (const m of params.messages) {
    const norm = _normalizeOneMessage(m)
    if (norm) kosmosMessages.push(norm)
  }
  if (!kosmosMessages.some((m) => m.role === 'user')) {
    kosmosMessages.push({ role: 'user', content: 'Continue.' })
  }

  const system = _coerceSystemPrompt(params.systemPrompt)

  let bridge
  try {
    bridge = getOrCreateKosmosBridge()
  } catch (err) {
    yield {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      message: {
        id: `msg_err_${Date.now().toString(36)}`,
        role: 'assistant',
        model: KOSMOS_MODEL,
        content: [
          {
            type: 'text',
            text: `KOSMOS bridge error: ${(err as Error).message}`,
          },
        ],
        stop_reason: 'end_turn',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    }
    return
  }

  const client = new LLMClient({
    bridge,
    model: KOSMOS_MODEL,
    sessionId: getKosmosBridgeSessionId(),
  })

  const accumulated: string[] = []
  let messageId: string | null = null
  let usage: KosmosUsage = { input_tokens: 0, output_tokens: 0 }
  let stopReason: 'end_turn' | 'max_tokens' | 'tool_use' | 'stop_sequence' =
    'end_turn'

  try {
    const stream = client.stream({
      model: KOSMOS_MODEL,
      messages: kosmosMessages,
      max_tokens: Math.min(
        params.options.maxOutputTokensOverride ?? 2_048,
        32_768,
      ),
      system,
    })

    // Drain the stream for side-effect token streaming (the bridge forwards
    // AssistantChunkFrames to the UI directly for rendering). queryLoop only
    // needs the final aggregated assistant message.
    for await (const evt of stream) {
      if (evt.type === 'message_start') {
        messageId = evt.message.id
      } else if (evt.type === 'content_block_delta') {
        if (evt.delta.type === 'text_delta') {
          accumulated.push(evt.delta.text)
        }
      } else if (evt.type === 'message_delta') {
        if (evt.delta.stop_reason) stopReason = evt.delta.stop_reason
        if (evt.usage) usage = evt.usage
      }
      if (params.signal?.aborted) break
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') return
    yield {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      message: {
        id: `msg_err_${Date.now().toString(36)}`,
        role: 'assistant',
        model: KOSMOS_MODEL,
        content: [
          {
            type: 'text',
            text: `KOSMOS LLM error: ${(err as Error).message}`,
          },
        ],
        stop_reason: 'end_turn',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    }
    return
  }

  const text = accumulated.join('')
  yield {
    type: 'assistant',
    uuid: crypto.randomUUID(),
    message: {
      id: messageId ?? `msg_${Date.now().toString(36)}`,
      role: 'assistant',
      model: KOSMOS_MODEL,
      content: [{ type: 'text', text }],
      stop_reason: stopReason,
      usage,
    },
  }
}

export async function* queryHaiku(params: {
  messages: ReadonlyArray<unknown>
  systemPrompt?: unknown
  options?: { model?: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming({
    messages: params.messages,
    systemPrompt: params.systemPrompt,
    options: {
      model: params.options?.model ?? KOSMOS_MODEL,
      maxOutputTokensOverride: params.options?.maxOutputTokensOverride,
    },
    signal: params.signal,
  })
}

export async function* queryModelWithoutStreaming(params: {
  messages: ReadonlyArray<unknown>
  systemPrompt?: unknown
  options: { model?: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming(params)
}

export async function* queryWithModel(params: {
  messages: ReadonlyArray<unknown>
  systemPrompt?: unknown
  options: { model?: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming(params)
}

export async function verifyApiKey(): Promise<boolean> {
  return Boolean(process.env.FRIENDLI_API_KEY)
}

export function getMaxOutputTokensForModel(_model: string): number {
  return 32_768
}

export function getExtraBodyParams(): Record<string, never> {
  return {}
}
