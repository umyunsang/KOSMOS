/**
 * Session title generation.
 *
 * KOSMOS Epic #2293: Anthropic queryHaiku removed (Spec 1633 + Spec 2293
 * closure). generateSessionTitle always returns null — the REPL title bar
 * falls back to the session-ID short form. The extractConversationText
 * utility is preserved for callers that inspect message history.
 */

import type { Message } from '../types/message.js'

const MAX_CONVERSATION_TEXT = 1000

/**
 * Flatten a message array into a single text string for session title input.
 * Skips meta/non-human messages. Tail-slices to the last 1000 chars so
 * recent context wins when the conversation is long.
 */
export function extractConversationText(messages: Message[]): string {
  const parts: string[] = []
  for (const msg of messages) {
    if (msg.type !== 'user' && msg.type !== 'assistant') continue
    if ('isMeta' in msg && msg.isMeta) continue
    if ('origin' in msg && msg.origin && msg.origin.kind !== 'human') continue
    const content = msg.message.content
    if (typeof content === 'string') {
      parts.push(content)
    } else if (Array.isArray(content)) {
      for (const block of content) {
        if ('type' in block && block.type === 'text' && 'text' in block) {
          parts.push(block.text as string)
        }
      }
    }
  }
  const text = parts.join('\n')
  return text.length > MAX_CONVERSATION_TEXT
    ? text.slice(-MAX_CONVERSATION_TEXT)
    : text
}

/**
 * Generate a session title from a description.
 * KOSMOS Epic #2293: Anthropic queryHaiku removed. Returns null unconditionally;
 * session title display falls back to the session-ID short form.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function generateSessionTitle(
  _description: string,
  _signal: AbortSignal,
): Promise<string | null> {
  return null
}
