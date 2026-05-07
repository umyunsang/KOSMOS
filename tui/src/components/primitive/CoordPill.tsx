/**
 * KOSMOS-original — CoordPill renderer.
 *
 * Compact inline pill showing latitude and longitude from the coords slot
 * of a resolve_location result.  Includes a copy hint in the inactive color.
 *
 * FR-022: resolve_location coords renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { CoordsSlot } from './types'

export interface CoordPillProps {
  coords: CoordsSlot
}

export function CoordPill({ coords }: CoordPillProps): React.JSX.Element {
  const theme = useTheme()

  const lat = coords.lat.toFixed(6)
  const lon = coords.lon.toFixed(6)

  return (
    <Box flexDirection="row" gap={1}>
      <Text color={theme.professionalBlue} bold>{'[GPS]'}</Text>
      <Text color={theme.text}>{`${lat}\u00b0N`}</Text>
      <Text color={theme.inactive}>/</Text>
      <Text color={theme.text}>{`${lon}\u00b0E`}</Text>
    </Box>
  )
}
