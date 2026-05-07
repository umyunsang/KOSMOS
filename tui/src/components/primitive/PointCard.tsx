/**
 * KOSMOS-original — PointCard renderer.
 *
 * Displays a single point-of-interest result from a lookup tool call.
 * Renders a title, optional subtitle, and a row of key/value fields.
 *
 * FR-017: lookup point-of-interest renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { LookupPointPayload } from './types'

export interface PointCardProps {
  payload: LookupPointPayload
}

export function PointCard({ payload }: PointCardProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={theme.professionalBlue} paddingX={1}>
      <Text bold color={theme.text}>{payload.title}</Text>
      {payload.subtitle !== undefined && (
        <Text color={theme.inactive}>{payload.subtitle}</Text>
      )}
      {payload.fields.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          {payload.fields.map((field) => (
            <Box key={field.label} flexDirection="row" gap={1}>
              <Text color={theme.subtle} bold>{field.label}:</Text>
              <Text color={theme.text}>{field.value}</Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}
