/**
 * KOSMOS-original — AuthWarningBanner renderer.
 *
 * Failure banner shown when a verify primitive returns ok=false.
 * Displays the Korea tier, error code, message, and actionable remediation.
 *
 * FR-032: verify failure renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { VerifyFailPayload } from './types'

export interface AuthWarningBannerProps {
  payload: VerifyFailPayload
}

export function AuthWarningBanner({ payload }: AuthWarningBannerProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.error}
      paddingX={1}
    >
      <Text bold color={theme.error}>{`\u2718 Verification failed [${payload.error_code}]`}</Text>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>Level</Text>
        {/* korea_tier is always primary label (FR-030) */}
        <Text color={theme.warning} bold>{payload.korea_tier}</Text>
      </Box>
      <Text color={theme.text}>{payload.message}</Text>
      {payload.remediation !== undefined && (
        <Text color={theme.warning}>{`Action: ${payload.remediation}`}</Text>
      )}
    </Box>
  )
}
