// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/FeedColumn.tsx (Claude Code 2.1.88, research-use)
// KOSMOS PORT per Epic H #1302 (035-onboarding-brand-port) — verbatim structure; token-only adaptation

import * as React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'
import type { FeedConfig } from './Feed'
import { Feed, calculateFeedWidth } from './Feed'

type FeedColumnProps = {
  feeds: FeedConfig[]
  maxWidth: number
}

export function FeedColumn({ feeds, maxWidth }: FeedColumnProps): React.ReactNode {
  const theme = useTheme()
  const feedWidths = feeds.map(feed => calculateFeedWidth(feed))
  const maxOfAllFeeds = Math.max(...feedWidths)
  const actualWidth = Math.min(maxOfAllFeeds, maxWidth)

  return (
    <Box flexDirection="column">
      {feeds.map((feed, index) => (
        <React.Fragment key={index}>
          <Feed config={feed} actualWidth={actualWidth} />
          {index < feeds.length - 1 && (
            <Text color={theme.subtle}>{'─'.repeat(actualWidth)}</Text>
          )}
        </React.Fragment>
      ))}
    </Box>
  )
}
