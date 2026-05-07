/**
 * KOSMOS-original — AddressBlock renderer.
 *
 * Multi-line Korean address display from the address slot of a
 * resolve_location result.  Shows road address, parcel address,
 * detail address, and zip code on separate lines as available.
 *
 * FR-024: resolve_location address renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { AddressSlot } from './types'

export interface AddressBlockProps {
  address: AddressSlot
}

export function AddressBlock({ address }: AddressBlockProps): React.JSX.Element {
  const theme = useTheme()

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text color={theme.professionalBlue} bold>{'[Address]'}</Text>
      {address.road !== undefined && (
        <Box flexDirection="row" gap={1}>
          <Text color={theme.inactive}>Road</Text>
          <Text color={theme.text}>{address.road}</Text>
        </Box>
      )}
      {address.parcel !== undefined && (
        <Box flexDirection="row" gap={1}>
          <Text color={theme.inactive}>Parcel</Text>
          <Text color={theme.text}>{address.parcel}</Text>
        </Box>
      )}
      {address.detail !== undefined && (
        <Box flexDirection="row" gap={1}>
          <Text color={theme.inactive}>Detail</Text>
          <Text color={theme.text}>{address.detail}</Text>
        </Box>
      )}
      {address.zip !== undefined && (
        <Box flexDirection="row" gap={1}>
          <Text color={theme.inactive}>ZIP</Text>
          <Text color={theme.text}>{address.zip}</Text>
        </Box>
      )}
    </Box>
  )
}
