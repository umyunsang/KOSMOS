// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/WelcomeV2.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'
import { useReducedMotion } from '../../../hooks/useReducedMotion'

type Props = {
  version?: string
}

/**
 * WelcomeV2 — KOSMOS citizen welcome screen.
 *
 * Renders the Korean welcome message followed by the version string, a
 * horizontal divider, and the kosmosCore asterisk cluster (3x7 grid).  The
 * centre `●` uses `kosmosCoreShimmer` when reduced-motion is off, and falls
 * back to `kosmosCore` when reduced-motion is on.
 *
 * CC content removed:
 *   - "Welcome to Claude Code" → "KOSMOS에 오신 것을 환영합니다"
 *   - Apple-Terminal special-case ASCII art branch → deleted
 *   - Light-theme branch → deleted (Phase 1 scope: dark only)
 *
 * Token bindings: wordmark, subtitle, kosmosCore, kosmosCoreShimmer.
 * Accessibility: [ag-logov2] row 37 — no motion artefacts under NO_COLOR /
 * KOSMOS_REDUCED_MOTION.
 */
export function WelcomeV2({ version = '0.0.0' }: Props): React.ReactElement {
  const theme = useTheme()
  const { prefersReducedMotion } = useReducedMotion()

  // Centre `●` colour: shimmer when motion is allowed, base otherwise.
  const centerColor = prefersReducedMotion
    ? theme.kosmosCore
    : theme.kosmosCoreShimmer

  return (
    <Box flexDirection="column" alignItems="center">
      {/* Welcome message line */}
      <Text bold color={theme.wordmark}>{`KOSMOS에 오신 것을 환영합니다  v${version}`}</Text>

      {/* Horizontal divider — 30 em-dashes */}
      <Text color={theme.subtitle}>{'─'.repeat(30)}</Text>

      {/* Asterisk cluster (3 rows) */}
      <Box flexDirection="column">
        {/* Row 1:  *  *  * */}
        <Text color={theme.kosmosCore}>{'  *  *  *  '}</Text>

        {/* Row 2: *  ●  *  — three Text elements so ● gets its own colour */}
        <Box flexDirection="row">
          <Text color={theme.kosmosCore}>{' *  '}</Text>
          <Text color={centerColor}>{'●'}</Text>
          <Text color={theme.kosmosCore}>{'  * '}</Text>
        </Box>

        {/* Row 3:  *  *  * */}
        <Text color={theme.kosmosCore}>{'  *  *  *  '}</Text>
      </Box>
    </Box>
  )
}
