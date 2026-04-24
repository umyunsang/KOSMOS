// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// The real Anthropic-backed `services/api/claude` module was deleted by Epic
// #1633 in favour of `ipc/llmClient.ts` (FriendliAI-via-IPC). Several legacy
// callers still import helper symbols from here. The stubs either delegate to
// the IPC path (via `llmClient.ts` when invoked) or return empty payloads.

import type { KosmosUsage } from '../../ipc/llmTypes.js'

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
  cache_creation_input_tokens: 0,
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

// Interim KOSMOS-original bridge — pending the full Epic #1633 rewire that
// wires `query/deps.ts::callModel` directly to `ipc/llmClient.ts::stream()`.
// For now, we short-circuit from this legacy CC entrypoint straight to
// FriendliAI Serverless via fetch, transforming the OpenAI-compatible
// response into the `{type:'assistant', message:{...}}` envelope that
// `query.ts::queryLoop` expects. This violates contract G1 (no direct
// HTTPS) but keeps the TUI demonstrably functional while the IPC path is
// plumbed through the Python backend.

const FRIENDLI_BASE_URL =
  process.env.FRIENDLI_BASE_URL ?? 'https://api.friendli.ai/serverless'

function kosmosFriendliRequestBody(
  messages: ReadonlyArray<{ role: string; content: unknown }>,
  systemPrompt: unknown,
  model: string,
  maxTokens: number,
): Record<string, unknown> {
  const normalizedMessages: Array<{ role: string; content: string }> = []
  // System prompt — CC sometimes passes array-of-TextBlock; coerce to string.
  const sys = Array.isArray(systemPrompt)
    ? systemPrompt
        .map((b) =>
          typeof b === 'string'
            ? b
            : typeof (b as { text?: unknown })?.text === 'string'
              ? (b as { text: string }).text
              : '',
        )
        .filter(Boolean)
        .join('\n\n')
    : typeof systemPrompt === 'string'
      ? systemPrompt
      : ''
  if (sys) normalizedMessages.push({ role: 'system', content: sys })
  for (const m of messages) {
    // CC's internal Message shape: { type: 'user'|'assistant', message: { role, content } }.
    // query.ts passes those directly, so we need to unwrap one level.
    const mAny = m as {
      role?: string
      content?: unknown
      type?: string
      message?: { role?: string; content?: unknown }
    }
    const role =
      mAny.role ??
      mAny.message?.role ??
      (mAny.type === 'assistant' ? 'assistant' : 'user')
    const rawContent = mAny.content ?? mAny.message?.content
    const content =
      typeof rawContent === 'string'
        ? rawContent
        : Array.isArray(rawContent)
          ? rawContent
              .map((block) => {
                if (typeof block === 'string') return block
                const b = block as {
                  type?: string
                  text?: string
                  content?: unknown
                }
                if (b?.type === 'text' && typeof b.text === 'string') {
                  return b.text
                }
                if (
                  b?.type === 'tool_result' &&
                  typeof b.content === 'string'
                ) {
                  return b.content
                }
                return ''
              })
              .filter(Boolean)
              .join('\n')
          : ''
    if (!content) continue
    normalizedMessages.push({ role, content })
  }
  // FriendliAI requires at least one user message — synthesize one if the
  // entire batch collapsed to system + assistant-only (e.g. tool-only turns).
  if (
    !normalizedMessages.some((m) => m.role === 'user') &&
    normalizedMessages.length > 0
  ) {
    normalizedMessages.push({ role: 'user', content: 'Continue.' })
  }
  // KOSMOS is a single-model system — always target K-EXAONE regardless of
  // what upstream passes (CC defaults still leak "claude-opus-*" strings
  // through commander parse).
  const KOSMOS_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'
  void model
  return {
    model: KOSMOS_MODEL,
    messages: normalizedMessages,
    max_tokens: Math.min(maxTokens, 32_768),
    stream: false,
  }
}

export async function* queryModelWithStreaming(params: {
  messages: ReadonlyArray<{ role: string; content: unknown }>
  systemPrompt?: unknown
  options: { model: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  const apiKey = process.env.FRIENDLI_API_KEY
  if (!apiKey) {
    yield {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      message: {
        id: `msg_err_${Date.now().toString(36)}`,
        role: 'assistant',
        model: params.options.model,
        content: [
          {
            type: 'text',
            text: 'KOSMOS error: FRIENDLI_API_KEY is not set. Export it and restart the TUI.',
          },
        ],
        stop_reason: 'end_turn',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    }
    return
  }

  const body = kosmosFriendliRequestBody(
    params.messages,
    params.systemPrompt,
    params.options.model,
    params.options.maxOutputTokensOverride ?? 4_096,
  )

  try {
    const url = `${FRIENDLI_BASE_URL}/v1/chat/completions`
    if (process.env.KOSMOS_DEBUG_LLM === '1') {
      const b = JSON.stringify(body)
      process.stderr.write(
        `[KOSMOS/LLM] POST ${url} body_len=${b.length} head=${b.slice(0, 200)} tail=${b.slice(-300)}\n`,
      )
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
      signal: params.signal,
    })

    if (!response.ok) {
      const errText = await response.text().catch(() => '<no body>')
      yield {
        type: 'assistant',
        uuid: crypto.randomUUID(),
        message: {
          id: `msg_err_${Date.now().toString(36)}`,
          role: 'assistant',
          model: params.options.model,
          content: [
            {
              type: 'text',
              text: `KOSMOS API error ${response.status}: ${errText.slice(0, 500)}`,
            },
          ],
          stop_reason: 'end_turn',
          usage: { input_tokens: 0, output_tokens: 0 },
        },
      }
      return
    }

    const data = (await response.json()) as {
      id?: string
      model?: string
      choices?: Array<{
        message?: { content?: string | null }
        finish_reason?: string
      }>
      usage?: {
        prompt_tokens?: number
        completion_tokens?: number
        prompt_tokens_details?: { cached_tokens?: number }
      }
    }

    const choice = data.choices?.[0]
    const content = choice?.message?.content ?? ''
    yield {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      message: {
        id: data.id ?? `msg_${Date.now().toString(36)}`,
        role: 'assistant',
        model: data.model ?? params.options.model,
        content: [{ type: 'text', text: content }],
        stop_reason:
          choice?.finish_reason === 'length' ? 'max_tokens' : 'end_turn',
        usage: {
          input_tokens: data.usage?.prompt_tokens ?? 0,
          output_tokens: data.usage?.completion_tokens ?? 0,
          cache_read_input_tokens:
            data.usage?.prompt_tokens_details?.cached_tokens ?? 0,
        },
      },
    }
  } catch (err) {
    if ((err as Error).name === 'AbortError') return
    yield {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      message: {
        id: `msg_err_${Date.now().toString(36)}`,
        role: 'assistant',
        model: params.options.model,
        content: [
          {
            type: 'text',
            text: `KOSMOS network error: ${(err as Error).message}`,
          },
        ],
        stop_reason: 'end_turn',
        usage: { input_tokens: 0, output_tokens: 0 },
      },
    }
  }
}

export async function* queryHaiku(params: {
  messages: ReadonlyArray<{ role: string; content: unknown }>
  systemPrompt?: unknown
  options?: { model?: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming({
    messages: params.messages,
    systemPrompt: params.systemPrompt,
    options: {
      model: params.options?.model ?? 'LGAI-EXAONE/K-EXAONE-236B-A23B',
      maxOutputTokensOverride: params.options?.maxOutputTokensOverride,
    },
    signal: params.signal,
  })
}

export async function* queryModelWithoutStreaming(params: {
  messages: ReadonlyArray<{ role: string; content: unknown }>
  systemPrompt?: unknown
  options: { model: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming(params)
}

export async function* queryWithModel(params: {
  messages: ReadonlyArray<{ role: string; content: unknown }>
  systemPrompt?: unknown
  options: { model: string; maxOutputTokensOverride?: number }
  signal?: AbortSignal
}): AsyncGenerator<unknown, void, unknown> {
  yield* queryModelWithStreaming(params)
}

export async function verifyApiKey(): Promise<boolean> {
  return Boolean(process.env.FRIENDLI_API_KEY)
}

export function getMaxOutputTokensForModel(_model: string): number {
  // K-EXAONE-236B supports up to 32k output tokens on FriendliAI Serverless.
  // Callers use this to bound `max_tokens` in outbound requests.
  return 32_768
}

export function getExtraBodyParams(): Record<string, never> {
  return {}
}
