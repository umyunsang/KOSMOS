/**
 * KOSMOS-original — EventStream renderer.
 *
 * Live-updating scroll of events from a subscribe primitive.
 * Renders per-item timestamps and a modality badge.
 * Renders only the last MAX_VISIBLE events to keep output bounded.
 *
 * FR-028: subscribe open stream renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { EventStreamPayload } from './types'

/** Maximum visible events before truncating from the top. */
const MAX_VISIBLE = 10

export interface EventStreamProps {
  payload: EventStreamPayload
}

export function EventStream({ payload }: EventStreamProps): React.JSX.Element {
  const theme = useTheme()
  const visible = payload.events.slice(-MAX_VISIBLE)
  const hidden = payload.events.length - visible.length

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.professionalBlue} paddingX={1}>
      <Box flexDirection="row" gap={1}>
        <Text bold color={theme.professionalBlue}>{'\u25cf Live'}</Text>
        <Text color={theme.inactive}>{`[${payload.modality}]`}</Text>
        <Text color={theme.subtle}>{`${payload.tool_id}`}</Text>
      </Box>
      {hidden > 0 && (
        <Text color={theme.inactive}>{`\u2026 ${hidden} earlier events`}</Text>
      )}
      {visible.map((ev) => (
        <Box key={ev.id} flexDirection="row" gap={1}>
          <Text color={theme.subtle}>{ev.ts}</Text>
          <Text color={theme.text}>{ev.body}</Text>
        </Box>
      ))}
    </Box>
  )
}
