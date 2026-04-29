// SPDX-License-Identifier: Apache-2.0
// KOSMOS Epic β #2293 — services/tokenEstimation stub:
//   AWS Bedrock + Anthropic SDK token-counting APIs removed;
//   uses simple heuristic (character length / 4) for all estimates.
//   Callers receive the same numeric type as before — accuracy is
//   sufficient for UI hints and context-window tracking.

/**
 * Rough token count for a string (or serialised JSON string).
 * Heuristic: 1 token ≈ 4 characters (BPE average for mixed en/ko text).
 */
export function roughTokenCountEstimation(input: string | unknown): number {
  if (typeof input === 'string') {
    return Math.ceil(input.length / 4)
  }
  try {
    const s = JSON.stringify(input) ?? ''
    return Math.ceil(s.length / 4)
  } catch {
    return 0
  }
}

/**
 * Rough token count for an array of messages.
 * Each message's content (string or blocks) is stringified and divided by 4.
 */
export function roughTokenCountEstimationForMessages(
  messages: readonly unknown[],
): number {
  let total = 0
  for (const msg of messages) {
    if (msg == null) continue
    const m = msg as Record<string, unknown>
    // Handle both raw API message shapes and internal Message wrappers.
    const content =
      (m as { message?: { content?: unknown } }).message?.content ??
      (m as { content?: unknown }).content ??
      msg
    if (typeof content === 'string') {
      total += Math.ceil(content.length / 4)
    } else if (Array.isArray(content)) {
      for (const block of content) {
        if (block == null) continue
        const b = block as Record<string, unknown>
        if (typeof b['text'] === 'string') {
          total += Math.ceil(b['text'].length / 4)
        } else if (typeof b['thinking'] === 'string') {
          total += Math.ceil(b['thinking'].length / 4)
        } else if (typeof b['data'] === 'string') {
          total += Math.ceil(b['data'].length / 4)
        } else {
          try {
            total += Math.ceil((JSON.stringify(b) ?? '').length / 4)
          } catch {
            // skip unserializable blocks
          }
        }
      }
    } else {
      try {
        total += Math.ceil((JSON.stringify(content) ?? '').length / 4)
      } catch {
        // skip
      }
    }
  }
  return total
}

/**
 * Rough token count for file content.  The `ext` parameter is accepted for
 * API compatibility but is not used — all file types use the same heuristic.
 */
export function roughTokenCountEstimationForFileType(
  content: string,
  _ext: string,
): number {
  return Math.ceil(content.length / 4)
}

/**
 * Count tokens by calling the provider counting API.
 * KOSMOS uses FriendliAI (no dedicated counting endpoint) — always returns null
 * so callers fall through to their heuristic fallback.
 */
export async function countTokensWithAPI(
  _content: string,
): Promise<number | null> {
  return null
}

/**
 * Count tokens via the messages counting API.
 * KOSMOS uses FriendliAI (no dedicated counting endpoint) — always returns null
 * so callers fall through to roughTokenCountEstimation.
 */
export async function countMessagesTokensWithAPI(
  _messages: unknown[],
  _tools: unknown[],
): Promise<number | null> {
  return null
}

/**
 * Count tokens via a small model (Haiku/fallback).
 * KOSMOS has a single fixed model (K-EXAONE on FriendliAI) with no dedicated
 * counting call — always returns null so callers fall through to heuristics.
 */
export async function countTokensViaHaikuFallback(
  _messages: unknown[],
  _tools: unknown[],
): Promise<number | null> {
  return null
}
