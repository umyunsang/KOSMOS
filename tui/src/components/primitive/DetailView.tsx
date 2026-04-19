/**
 * KOSMOS-original — DetailView renderer.
 *
 * Renders key/value pairs for a single structured record in a two-column
 * grid layout.  Labels are right-aligned; values are left-aligned.
 *
 * FR-020: lookup detail view renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { LookupDetailPayload } from './types'

export interface DetailViewProps {
  payload: LookupDetailPayload
}

export function DetailView({ payload }: DetailViewProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.professionalBlue} paddingX={1}>
      {payload.fields.map((field) => (
        <Box key={field.label} flexDirection="row" gap={1}>
          <Box width={22}>
            <Text color={theme.inactive} bold>{field.label}</Text>
          </Box>
          <Text color={theme.text}>{field.value}</Text>
        </Box>
      ))}
    </Box>
  )
}
