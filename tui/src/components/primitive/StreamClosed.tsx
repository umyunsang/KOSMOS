/**
 * KOSMOS-original — StreamClosed renderer.
 *
 * Shown when a subscribe stream has terminated.  Displays the close_reason,
 * optional final cursor, and a summary event count.
 *
 * FR-029: subscribe closed stream renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { StreamClosedPayload } from './types'

const REASON_COLOR: Record<string, string> = {
  exhausted: 'success',
  revoked: 'warning',
  timeout: 'warning',
}

export interface StreamClosedProps {
  payload: StreamClosedPayload
}

export function StreamClosed({ payload }: StreamClosedProps): React.JSX.Element {
  const theme = useTheme()
  const reasonKey = REASON_COLOR[payload.close_reason] ?? 'inactive'
  const color = theme[reasonKey as keyof typeof theme] as string ?? theme.inactive

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor={theme.inactive}
      paddingX={1}
    >
      <Box flexDirection="row" gap={1}>
        <Text bold color={theme.inactive}>{'\u25a0 Stream closed'}</Text>
        <Text color={color}>{`[${payload.close_reason}]`}</Text>
        <Text color={theme.subtle}>{`[${payload.modality}]`}</Text>
      </Box>
      <Text color={theme.subtle}>{`${payload.events.length} events received`}</Text>
      {payload.final_cursor !== undefined && (
        <Text color={theme.inactive}>{`Cursor: ${payload.final_cursor}`}</Text>
      )}
    </Box>
  )
}
