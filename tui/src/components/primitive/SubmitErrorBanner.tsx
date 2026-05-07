/**
 * KOSMOS-original — SubmitErrorBanner renderer.
 *
 * Failure banner shown when a submit primitive returns ok=false.
 * Includes error code, message, optional retry guidance, and mock chip.
 *
 * FR-027: submit error renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { SubmitErrorPayload } from './types'

export interface SubmitErrorBannerProps {
  payload: SubmitErrorPayload
}

export function SubmitErrorBanner({ payload }: SubmitErrorBannerProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.error}
      paddingX={1}
    >
      <Box flexDirection="row" gap={1}>
        <Text bold color={theme.error}>{`\u2718 Submit failed [${payload.error_code}]`}</Text>
        {payload.mock_reason !== undefined && (
          <Text color={theme.warning}>{`[MOCK: ${payload.mock_reason}]`}</Text>
        )}
      </Box>
      <Text color={theme.text}>{payload.message}</Text>
      {payload.retry_hint !== undefined && (
        <Text color={theme.warning}>{`Retry: ${payload.retry_hint}`}</Text>
      )}
    </Box>
  )
}
