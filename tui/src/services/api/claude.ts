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

// Query helpers: the real LLM round-trip lives in `ipc/llmClient.ts`.
// Consumers that still import these helpers receive a fail-closed error so
// the UI surfaces the stub rather than silently hanging.
function stubThrow(name: string): never {
  throw new Error(
    `KOSMOS: services/api/claude.${name} is a stub — use ipc/llmClient directly`,
  )
}

export async function queryHaiku(): Promise<never> {
  return stubThrow('queryHaiku')
}

export async function queryModelWithStreaming(): Promise<never> {
  return stubThrow('queryModelWithStreaming')
}

export async function queryModelWithoutStreaming(): Promise<never> {
  return stubThrow('queryModelWithoutStreaming')
}

export async function queryWithModel(): Promise<never> {
  return stubThrow('queryWithModel')
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
