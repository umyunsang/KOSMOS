// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original (no direct upstream; Claude Code's VirtualMessageList is
// significantly more complex — this is a plain skeleton per task spec).
//
// MessageList: renders the full conversation history from session-store.
// SKELETON ONLY — primitive tool results are not yet dispatched.
//
// FR-051: subscribes to message_order only (not the full messages Map) so
//         individual message re-renders do not cascade.

import React from 'react'
import { Box } from 'ink'
import { useSessionStore } from '../../store/session-store'
import { StreamingMessage, UserMessage } from './StreamingMessage'

// TODO(T087): plug PrimitiveDispatcher — tool_result envelopes need to be
//             routed to the appropriate primitive renderer (PointCard, etc.)
//             once Team C's PrimitiveDispatcher is wired in Phase 5.

// ---------------------------------------------------------------------------
// MessageList
// ---------------------------------------------------------------------------

/**
 * Skeleton conversation list that renders every message in FIFO order.
 *
 * User messages → `<UserMessage />`
 * Assistant messages → `<StreamingMessage />` (handles in-progress + done)
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
        const msg = messages.get(id)
        if (!msg) return null
        if (msg.role === 'user') {
          return <UserMessage key={id} messageId={id} />
        }
        return <StreamingMessage key={id} messageId={id} />
      })}
    </Box>
  )
}
