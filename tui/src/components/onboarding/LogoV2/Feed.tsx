// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/Feed.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9
//
// Two roles in one file (mirrors CC's Feed.tsx public API):
//   1. PRIMITIVE — `Feed` component + `calculateFeedWidth` util used by
//      `FeedColumn.tsx` as the per-feed row renderer.
//   2. COMPOSITION — `KosmosOnboardingFeed` stacks two `FeedColumn` instances
//      side-by-side for the onboarding splash: session history (left) and
//      ministry availability (right).
//
// Contract: specs/035-onboarding-brand-port/contracts/logov2-rewrite-visual-specs.md § 3
// Token tree: wordmark / text / subtle / agentSatelliteKoroad / agentSatelliteKma
//             / agentSatelliteHira / agentSatelliteNmc

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'
import type { ThemeToken } from '../../../theme/tokens'
import type {
  FeedConfig,
  FeedRow,
  KosmosSession,
  MinistryStatus,
} from './feedConfigs'
import {
  createKosmosSessionHistoryFeed,
  createMinistryAvailabilityFeed,
} from './feedConfigs'
import { FeedColumn } from './FeedColumn'

// Re-export so `FeedColumn.tsx` can import its `FeedConfig` type from `./Feed`
// (matches CC's public-API surface).
export type { FeedConfig, FeedRow, KosmosSession, MinistryStatus } from './feedConfigs'

// ---------------------------------------------------------------------------
// Width primitive
// ---------------------------------------------------------------------------

/**
 * Width of the longest display line in a feed, in terminal cells.  Used by
 * FeedColumn to size Divider widths consistently across stacked feeds.
 * Conservative approximation: counts code units (Hangul width handling
 * deferred to Spec 287 `stringWidth` when embedded into the broader layout).
 */
export function calculateFeedWidth(config: FeedConfig): number {
  const lines: string[] = [config.title]
  for (const row of config.rows) {
    const secondary = row.secondary !== undefined ? ` ${row.secondary}` : ''
    lines.push(`${row.primary}${secondary}`)
  }
  return lines.reduce((acc, line) => (line.length > acc ? line.length : acc), 0)
}

// ---------------------------------------------------------------------------
// Feed primitive (title + rows)
// ---------------------------------------------------------------------------

type FeedProps = {
  config: FeedConfig
  actualWidth: number
}

/**
 * Renders one feed: a heading row (`config.title` in `subtitle`), then each
 * row with optional per-row accent colour resolved via `config.accentFor`.
 */
export function Feed({ config, actualWidth }: FeedProps): React.ReactElement {
  const theme = useTheme()
  return (
    <Box flexDirection="column" width={actualWidth}>
      <Text color={theme.subtitle}>{config.title}</Text>
      {config.rows.map((row, idx) => {
        const accentToken = config.accentFor !== undefined
          ? config.accentFor(row)
          : 'text'
        const primaryColor = resolveTokenColor(theme, accentToken)
        return (
          <Box key={idx} flexDirection="row">
            <Text color={primaryColor}>{row.primary}</Text>
            {row.secondary !== undefined && (
              <>
                <Text color={theme.subtle}>{' '}</Text>
                <Text color={theme.subtle}>{row.secondary}</Text>
              </>
            )}
          </Box>
        )
      })}
    </Box>
  )
}

function resolveTokenColor(theme: ThemeToken, tokenName: string): string {
  const key = tokenName as keyof ThemeToken
  const value = theme[key]
  return typeof value === 'string' ? value : theme.text
}

// ---------------------------------------------------------------------------
// KOSMOS two-column composition
// ---------------------------------------------------------------------------

type KosmosOnboardingFeedProps = {
  sessionHistory: KosmosSession[]
  ministryStatus: MinistryStatus[]
  columnWidth?: number // default 32
}

/**
 * Stacks two FeedColumn instances horizontally:
 *   - Left:  '최근 세션'   (createKosmosSessionHistoryFeed)
 *   - Right: '부처 상태'   (createMinistryAvailabilityFeed)
 */
export function KosmosOnboardingFeed({
  sessionHistory,
  ministryStatus,
  columnWidth = 32,
}: KosmosOnboardingFeedProps): React.ReactElement {
  const leftConfig = createKosmosSessionHistoryFeed(sessionHistory)
  const rightConfig = createMinistryAvailabilityFeed(ministryStatus)
  return (
    <Box flexDirection="row">
      <FeedColumn feeds={[leftConfig]} maxWidth={columnWidth} />
      <Box width={2} />
      <FeedColumn feeds={[rightConfig]} maxWidth={columnWidth} />
    </Box>
  )
}
