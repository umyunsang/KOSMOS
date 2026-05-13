import { feature } from 'bun:bundle'

import { isConnectorTextBlock } from '../types/connectorText.js'
import type { Message } from '../types/message.js'

function isThinkingBlock(block: { type?: string }): boolean {
  return block.type === 'thinking' || block.type === 'redacted_thinking'
}

/**
 * Strip signature-bearing blocks from assistant messages. Their signatures are
 * bound to the API key that generated them; after a credential change they're
 * invalid and the API rejects them.
 */
export function stripSignatureBlocks(messages: Message[]): Message[] {
  let changed = false
  const result = messages.map(msg => {
    if (msg.type !== 'assistant') return msg

    const content = msg.message.content
    if (!Array.isArray(content)) return msg

    const filtered = content.filter(block => {
      if (isThinkingBlock(block)) return false
      if (feature('CONNECTOR_TEXT')) {
        if (isConnectorTextBlock(block)) return false
      }
      return true
    })
    if (filtered.length === content.length) return msg

    changed = true
    return {
      ...msg,
      message: { ...msg.message, content: filtered },
    } as typeof msg
  })

  return changed ? result : messages
}
