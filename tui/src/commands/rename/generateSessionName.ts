// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T007 — `queryHaiku` import severed.
//
// Original CC module: .references/claude-code-sourcemap/restored-src/src/commands/rename/generateSessionName.ts
// CC version: 2.1.88
// KOSMOS deviation: Auto session-name generation called Anthropic Haiku to
// produce a kebab-case session label. KOSMOS routes all LLM traffic to
// FriendliAI K-EXAONE via stdio bridge (Spec 1633 P2) — calling the
// deprecated `queryHaiku` from the rename path would either reach
// `anthropic.com` (FR-004 violation) or throw the Anthropic-removed
// stub error mid-bridge call.
//
// Cheaper, deterministic alternative: derive the session name from the
// first non-empty user message via the same `extractConversationText`
// helper CC already used for the prompt. Lowercase, hyphenate, truncate.
// No LLM call, no network, no `anthropic.com`. Same call-site contract
// (`Promise<string | null>`) so consumers see no shape change.

import type { Message } from '../../types/message.js'
import { extractConversationText } from '../../utils/sessionTitle.js'

const MAX_NAME_WORDS = 4
const MAX_NAME_CHARS = 48

/**
 * KOSMOS-1978 T007: deterministic session name from conversation text.
 * Returns kebab-case (e.g. `fix-login-bug`) or null when the conversation
 * is too short / empty to summarise. Mirrors the CC contract — null is a
 * legal "skip rename" signal.
 */
function deriveKebabName(conversationText: string): string | null {
  const cleaned = conversationText
    // Strip control / non-printable / punctuation runs, keep word characters
    // and CJK letters (Spec 1633 P2 keeps Korean intact in domain text).
    .replace(/[^\p{L}\p{N}\s-]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
  if (!cleaned) {
    return null
  }
  const words = cleaned.split(' ').filter((w) => w.length >= 2).slice(0, MAX_NAME_WORDS)
  if (words.length === 0) {
    return null
  }
  let name = words.join('-')
  if (name.length > MAX_NAME_CHARS) {
    name = name.slice(0, MAX_NAME_CHARS).replace(/-+$/, '')
  }
  return name || null
}

export async function generateSessionName(
  messages: Message[],
  _signal: AbortSignal,
): Promise<string | null> {
  const conversationText = extractConversationText(messages)
  if (!conversationText) {
    return null
  }
  return deriveKebabName(conversationText)
}
