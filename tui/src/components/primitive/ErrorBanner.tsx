/**
 * KOSMOS-original — ErrorBanner renderer.
 *
 * Displays a red banner with a title, description, and optional retry hint.
 * Used for lookup-level errors surfaced from a tool result envelope.
 *
 * FR-021: lookup error renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { LookupErrorPayload } from './types'

export interface ErrorBannerProps {
  payload: LookupErrorPayload
}

export function ErrorBanner({ payload }: ErrorBannerProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.error}
      paddingX={1}
    >
      <Text bold color={theme.error}>{`\u2718 ${payload.title}`}</Text>
      <Text color={theme.text}>{payload.description}</Text>
      {payload.retry_hint !== undefined && (
        <Text color={theme.warning}>{`Hint: ${payload.retry_hint}`}</Text>
      )}
    </Box>
  )
}
