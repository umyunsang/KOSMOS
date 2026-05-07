/**
 * KOSMOS-original — UnrecognizedPayload renderer.
 *
 * Yellow warning banner displayed when the dispatcher receives a tool_result
 * envelope whose `kind` (or `subtype`) does not match any known renderer.
 * No attempt is made to guess or display the raw payload structure.
 *
 * FR-033: unrecognized primitive kind → yellow banner; no structure-guessing.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { UnrecognizedPayloadData } from './types'

export interface UnrecognizedPayloadProps {
  data: UnrecognizedPayloadData
}

export function UnrecognizedPayload({ data }: UnrecognizedPayloadProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.warning}
      paddingX={1}
    >
      <Text bold color={theme.warning}>{'\u26a0 Unrecognized tool result'}</Text>
      <Text color={theme.text}>{`Kind: ${data.raw_kind}`}</Text>
      <Text color={theme.inactive}>
        This renderer cannot display this payload. Please report the tool_id.
      </Text>
    </Box>
  )
}
