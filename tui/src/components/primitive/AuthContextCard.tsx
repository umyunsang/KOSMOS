/**
 * KOSMOS-original — AuthContextCard renderer.
 *
 * Success card shown after a verify primitive completes.
 * Displays authenticated identity, Korea tier (primary label per FR-030),
 * and optional NIST AAL hint.
 *
 * FR-030 / FR-031: verify success renderer; korea_tier is always the primary label.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { VerifySuccessPayload } from './types'

export interface AuthContextCardProps {
  payload: VerifySuccessPayload
}

export function AuthContextCard({ payload }: AuthContextCardProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.success}
      paddingX={1}
    >
      <Text bold color={theme.success}>{'\u2714 Verified'}</Text>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>Identity</Text>
        <Text color={theme.text}>{payload.identity_label}</Text>
      </Box>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive} bold>Level</Text>
        {/* korea_tier is always primary label (FR-030) */}
        <Text color={theme.success} bold>{payload.korea_tier}</Text>
      </Box>
      {payload.nist_aal_hint !== undefined && (
        <Box flexDirection="row" gap={1}>
          <Text color={theme.inactive}>NIST</Text>
          <Text color={theme.subtle}>{payload.nist_aal_hint}</Text>
        </Box>
      )}
      <Box flexDirection="row" gap={1}>
        <Text color={theme.inactive}>Family</Text>
        <Text color={theme.text}>{payload.family}</Text>
      </Box>
    </Box>
  )
}
