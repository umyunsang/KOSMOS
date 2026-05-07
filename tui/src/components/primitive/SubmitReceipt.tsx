/**
 * KOSMOS-original — SubmitReceipt renderer.
 *
 * Success receipt shown after a submit primitive completes.
 * Displays confirmation id, timestamp, and summary.
 * If mock_reason is present a [MOCK: <reason>] chip is rendered (FR-026).
 *
 * FR-026: submit success renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { SubmitSuccessPayload } from './types'

export interface SubmitReceiptProps {
  payload: SubmitSuccessPayload
}

export function SubmitReceipt({ payload }: SubmitReceiptProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.success}
      paddingX={1}
    >
      <Box flexDirection="row" gap={1}>
        <Text bold color={theme.success}>{'\u2714 Submitted'}</Text>
        {payload.mock_reason !== undefined && (
          <Text color={theme.warning}>{`[MOCK: ${payload.mock_reason}]`}</Text>
        )}
      </Box>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>ID</Text>
        <Text color={theme.text}>{payload.confirmation_id}</Text>
      </Box>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>Time</Text>
        <Text color={theme.text}>{payload.timestamp}</Text>
      </Box>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>Family</Text>
        <Text color={theme.text}>{payload.family}</Text>
      </Box>
      <Text color={theme.text}>{payload.summary}</Text>
    </Box>
  )
}
