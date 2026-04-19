// Source: .references/claude-code-sourcemap/restored-src/src/components/MessageResponse.tsx (Claude Code 2.1.88, research-use)
// Source: .references/claude-code-sourcemap/restored-src/src/components/Message.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: renders streaming assistant messages from the session-store.
// Replaces Claude Code's Anthropic REST streaming model with KOSMOS IPCFrame
// assistant_chunk / message_complete (done: true) frames.
//
// FR-050 (only re-renders own slot on new chunks via selector isolation)
// US1 scenario 2 (streaming text appears as chunks arrive)

import React from 'react'
import { Box, Text } from 'ink'
import { useSessionStore } from '../../store/session-store'
import type { Message } from '../../store/session-store'
import { useTheme } from '../../theme/provider'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface StreamingMessageProps {
  /** message_id to render — drives selector isolation (FR-050) */
  messageId: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders a single streaming assistant message.
 *
 * Subscribes to only its own message slot via `useSessionStore(selector)` so
 * that concurrent `assistant_chunk` frames for other message slots do NOT
 * trigger a re-render of this component (FR-050 / useSyncExternalStore).
 *
 * The text is built by joining all `chunks` in insertion order.
 * A blinking cursor is appended while `done === false`.
 */
export function StreamingMessage({ messageId }: StreamingMessageProps): React.ReactElement | null {
  const theme = useTheme()

  // Selector-isolated subscription: only re-renders when *this* message changes.
  const message: Message | undefined = useSessionStore(
    (s) => s.messages.get(messageId),
  )

  if (!message) return null

  const text = message.chunks.join('')
  const isStreaming = !message.done

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Assistant label */}
      <Box>
        <Text bold color={theme.claude}>
          {'  '}⎿{'  '}
        </Text>
      </Box>
      {/* Message body */}
      <Box paddingLeft={4}>
        <Text color={theme.text} wrap="wrap">
          {text}
          {isStreaming && (
            <Text color={theme.inactive}>▋</Text>
          )}
        </Text>
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// User message variant (same module — used by MessageList)
// ---------------------------------------------------------------------------

interface UserMessageProps {
  messageId: string
}

/**
 * Renders a user message (single-chunk, never streams).
 * Selector-isolated like StreamingMessage.
 */
export function UserMessage({ messageId }: UserMessageProps): React.ReactElement | null {
  const theme = useTheme()
  const message: Message | undefined = useSessionStore(
    (s) => s.messages.get(messageId),
  )

  if (!message) return null

  const text = message.chunks.join('')

  return (
    <Box flexDirection="row" marginBottom={1}>
      <Text bold color={theme.briefLabelYou}>{'> '}</Text>
      <Text color={theme.text} wrap="wrap">{text}</Text>
    </Box>
  )
}
