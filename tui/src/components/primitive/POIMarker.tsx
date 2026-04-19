/**
 * KOSMOS-original — POIMarker renderer.
 *
 * Marker indicating a resolved named place from the poi slot of a
 * resolve_location result.  Shows name, optional category, and source.
 *
 * FR-025: resolve_location POI renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { PoiSlot } from './types'

export interface POIMarkerProps {
  poi: PoiSlot
}

export function POIMarker({ poi }: POIMarkerProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box flexDirection="column" paddingX={1}>
      <Box flexDirection="row" gap={1}>
        <Text color={theme.success} bold>{'\u25cf'}</Text>
        <Text color={theme.text} bold>{poi.name}</Text>
      </Box>
      {poi.category !== undefined && (
        <Text color={theme.inactive}>{`Category: ${poi.category}`}</Text>
      )}
      {poi.source !== undefined && (
        <Text color={theme.subtle}>{`Source: ${poi.source}`}</Text>
      )}
    </Box>
  )
}
