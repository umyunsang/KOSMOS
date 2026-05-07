// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original (no direct upstream; Claude Code's VirtualMessageList is
// significantly more complex — this is a plain skeleton per task spec).
//
// MessageList: renders the full conversation history from session-store.
// Tool results are rendered via <PrimitiveDispatcher> (T087).
//
// FR-050: each MessageToolResults subscribes only to its own slot.
// FR-051: subscribes to message_order only (not the full messages Map) so
//         individual message re-renders do not cascade.
// FR-052: overflowToBackbuffer enabled — historical messages are committed to
//         Ink's static scrollback region and never re-rendered.
// T120: replaced naive .map() over messageOrder with <VirtualizedList>.

import React, { useCallback } from 'react'
import { Box } from 'ink'
import { useSessionStore } from '../../store/session-store'
import type { ToolResult } from '../../store/session-store'
import { StreamingMessage, UserMessage } from './StreamingMessage'
import { PrimitiveDispatcher } from '../primitive'
import { VirtualizedList } from './VirtualizedList'

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
// MessageRow — renders one message entry (user or assistant+tool_results)
// ---------------------------------------------------------------------------

interface MessageRowProps {
  messageId: string
}

function MessageRow({ messageId }: MessageRowProps): React.ReactElement | null {
  const role = useSessionStore((s) => s.messages.get(messageId)?.role)

  if (role === undefined) return null

  if (role === 'user') {
    return <UserMessage messageId={messageId} />
  }

  return (
    <Box flexDirection="column">
      <StreamingMessage messageId={messageId} />
      {/* MessageToolResults is selector-isolated: subscribes only to its own
          slot so a new chunk on another message does not re-render this. */}
      <MessageToolResults messageId={messageId} />
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Stable keyExtractor (module-level so identity is stable across renders)
// ---------------------------------------------------------------------------

const messageKeyExtractor = (id: string): string => id

// ---------------------------------------------------------------------------
// MessageList
// ---------------------------------------------------------------------------

/**
 * Virtualized conversation list powered by <VirtualizedList>.
 *
 * Replaces the naive `.map()` over messageOrder with viewport-culled rendering
 * so only visible rows are mounted as React fibers (FR-048).
 *
 * overflowToBackbuffer=true: messages that scroll off the top are committed
 * to Ink's static scrollback region (FR-052) and are never re-rendered.
 *
 * Selector isolation (FR-050/FR-051) is preserved: MessageRow subscribes to
 * the role field only, while MessageToolResults subscribes only to its own
 * tool_results slot.
 */
export function MessageList(): React.ReactElement {
  // Subscribe to message_order only — a new chunk does not change the order.
  const messageOrder = useSessionStore((s) => s.message_order)

  const renderMessage = useCallback(
    (id: string, _index: number): React.ReactElement => (
      <MessageRow key={id} messageId={id} />
    ),
    [],
  )

  return (
    <VirtualizedList
      items={messageOrder}
      renderItem={renderMessage}
      keyExtractor={messageKeyExtractor}
      overflowToBackbuffer
    />
  )
}
