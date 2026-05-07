/**
 * KOSMOS-original — CollectionList renderer.
 *
 * Renders a numbered list of records.  Each item shows a left-padded index,
 * a title, and optional trailing metadata.
 *
 * FR-019: lookup collection list renderer.
 */
import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '@/theme/provider'
import type { LookupCollectionPayload } from './types'

/** Maximum items rendered before truncation. */
const MAX_ITEMS = 50

export interface CollectionListProps {
  payload: LookupCollectionPayload
}

export function CollectionList({ payload }: CollectionListProps): React.JSX.Element {
  const theme = useTheme()
  const items = payload.items.slice(0, MAX_ITEMS)
  const truncated = payload.items.length > MAX_ITEMS

  return (
    <Box flexDirection="column" paddingX={1}>
      {items.map((item) => (
        <Box key={item.index} flexDirection="row" gap={1}>
          <Text color={theme.inactive}>{String(item.index).padStart(3, ' ')}.</Text>
          <Text color={theme.text}>{item.title}</Text>
          {item.meta !== undefined && (
            <Text color={theme.subtle}>{item.meta}</Text>
          )}
        </Box>
      ))}
      {truncated && (
        <Text color={theme.inactive}>
          {`\u2026 ${payload.items.length - MAX_ITEMS} more items`}
        </Text>
      )}
    </Box>
  )
}
