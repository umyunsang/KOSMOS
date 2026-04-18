// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original (no direct upstream; Claude Code's VirtualMessageList is
// significantly more complex — this is a plain skeleton per task spec).
//
// MessageList: renders the full conversation history from session-store.
// Tool results are rendered via <PrimitiveDispatcher> (T087).
//
// FR-051: subscribes to message_order only (not the full messages Map) so
//         individual message re-renders do not cascade.

import React from 'react'
import { Box } from 'ink'
import { useSessionStore } from '../../store/session-store'
import type { Message, ToolResult } from '../../store/session-store'
import { StreamingMessage, UserMessage } from './StreamingMessage'
import { PrimitiveDispatcher } from '../primitive'

// ---------------------------------------------------------------------------
// MessageToolResults — selector-isolated renderer for a single message's
// tool_results. Subscribes only to the slot it owns so a new chunk on some
// other message does not re-render the dispatcher tree (FR-050/FR-051).
// ---------------------------------------------------------------------------

interface MessageToolResultsProps {
  messageId: string
}

function MessageToolResults({ messageId }: MessageToolResultsProps): React.ReactElement | null {
  const toolResults = useSessionStore(
    (s) => s.messages.get(messageId)?.tool_results,
  )

  if (toolResults === undefined || toolResults.length === 0) return null

  return (
    <Box flexDirection="column">
      {toolResults.map((result: ToolResult) => (
        <PrimitiveDispatcher
          key={result.call_id}
          payload={result.envelope}
        />
      ))}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// MessageList
// ---------------------------------------------------------------------------

/**
 * Skeleton conversation list that renders every message in FIFO order.
 *
 * User messages → `<UserMessage />`
 * Assistant messages → `<StreamingMessage />` followed by every attached
 *                      `<PrimitiveDispatcher />` for its tool_results.
 *
 * Each child renders its own selector-isolated subscription (FR-050), so
 * a new assistant_chunk frame for message N does not re-render message M.
 */
export function MessageList(): React.ReactElement {
  // Subscribe to message_order only — a new chunk does not change the order.
  const messageOrder = useSessionStore((s) => s.message_order)
  const messages = useSessionStore((s) => s.messages)

  return (
    <Box flexDirection="column">
      {messageOrder.map((id) => {
        const msg: Message | undefined = messages.get(id)
        if (msg === undefined) return null
        if (msg.role === 'user') {
          return <UserMessage key={id} messageId={id} />
        }
        return (
          <Box key={id} flexDirection="column">
            <StreamingMessage messageId={id} />
            <MessageToolResults messageId={id} />
          </Box>
        )
      })}
    </Box>
  )
}
