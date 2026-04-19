/**
 * KOSMOS-original — TimeseriesTable renderer.
 *
 * Renders a table of time-value rows for a lookup timeseries result.
 * Displays a sticky header row and a capped list of data rows.
 *
 * FR-018: lookup timeseries renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { LookupTimeseriesPayload } from './types'

/** Maximum rows to render before truncating (performance guard). */
const MAX_ROWS = 20

export interface TimeseriesTableProps {
  payload: LookupTimeseriesPayload
}

export function TimeseriesTable({ payload }: TimeseriesTableProps): React.JSX.Element {
  const theme = useTheme()
  const rows = payload.rows.slice(0, MAX_ROWS)
  const truncated = payload.rows.length > MAX_ROWS

  return (
    <Box flexDirection="column" borderStyle="single" borderColor={theme.professionalBlue} paddingX={1}>
      {/* Header */}
      <Box flexDirection="row">
        <Box width={24}>
          <Text bold color={theme.inactive}>Timestamp</Text>
        </Box>
        <Box>
          <Text bold color={theme.inactive}>
            Value{payload.unit !== undefined ? ` (${payload.unit})` : ''}
          </Text>
        </Box>
      </Box>
      {/* Data rows */}
      {rows.map((row, i) => (
        <Box key={`${row.ts}-${i}`} flexDirection="row">
          <Box width={24}>
            <Text color={theme.subtle}>{row.ts}</Text>
          </Box>
          <Box>
            <Text color={theme.text}>{row.value}</Text>
          </Box>
        </Box>
      ))}
      {truncated && (
        <Text color={theme.inactive}>
          {`\u2026 ${payload.rows.length - MAX_ROWS} more rows`}
        </Text>
      )}
    </Box>
  )
}
