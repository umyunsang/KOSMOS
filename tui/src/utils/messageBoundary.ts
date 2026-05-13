import { feature } from 'bun:bundle'

import type {
  Message,
  NormalizedMessage,
  SystemCompactBoundaryMessage,
} from '../types/message.js'

/**
 * Checks if a message is a compact boundary marker.
 */
export function isCompactBoundaryMessage(
  message: Message | NormalizedMessage,
): message is SystemCompactBoundaryMessage {
  return message?.type === 'system' && message.subtype === 'compact_boundary'
}

/**
 * Finds the index of the last compact boundary marker in the messages array.
 *
 * @returns The index of the last compact boundary, or -1 if none found.
 */
export function findLastCompactBoundaryIndex<
  T extends Message | NormalizedMessage,
>(messages: T[]): number {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message && isCompactBoundaryMessage(message)) {
      return i
    }
  }
  return -1
}

/**
 * Returns messages from the last compact boundary onward (including the
 * boundary). If no boundary exists, returns all messages.
 */
export function getMessagesAfterCompactBoundary<
  T extends Message | NormalizedMessage,
>(messages: T[], options?: { includeSnipped?: boolean }): T[] {
  const boundaryIndex = findLastCompactBoundaryIndex(messages)
  const sliced = boundaryIndex === -1 ? messages : messages.slice(boundaryIndex)
  if (!options?.includeSnipped && feature('HISTORY_SNIP')) {
    /* eslint-disable @typescript-eslint/no-require-imports */
    const { projectSnippedView } =
      require('../services/compact/snipProjection.js') as typeof import('../services/compact/snipProjection.js')
    /* eslint-enable @typescript-eslint/no-require-imports */
    return projectSnippedView(sliced as Message[]) as T[]
  }
  return sliced
}
