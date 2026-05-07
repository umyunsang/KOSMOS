/**
 * KOSMOS-original — AdmCodeBadge renderer.
 *
 * Displays the administrative region code and name from the adm_cd slot
 * of a resolve_location result.
 *
 * FR-023: resolve_location administrative code renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { AdmCodeSlot } from './types'

export interface AdmCodeBadgeProps {
  admCode: AdmCodeSlot
}

export function AdmCodeBadge({ admCode }: AdmCodeBadgeProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box flexDirection="row" gap={1}>
      <Text color={theme.suggestion} bold>{'[ADM]'}</Text>
      <Text color={theme.inactive}>{admCode.code}</Text>
      <Text color={theme.text}>{admCode.name}</Text>
    </Box>
  )
}
