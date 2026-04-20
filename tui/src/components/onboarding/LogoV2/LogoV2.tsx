// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/LogoV2.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9
//
// Composes the KOSMOS onboarding splash:
//   - orbital ring container with AnimatedAsterisk at its centre
//   - wordmark "KOSMOS" + Korean subtitle
//   - 4 ministry satellite nodes (KOROAD / KMA / HIRA / NMC)
//   - two-column KosmosOnboardingFeed
// Fallback ladder:
//   - 'full'      (>= 80 cols): full composition
//   - 'condensed' (50..79):      CondensedLogo
//   - 'fallback'  (< 50):        single-line `KOSMOS — 한국 공공서비스 대화창`
//
// BANNED IMPORTS (T043 compile-time guard will flag any reintroduction):
//   Clawd, AnimatedClawd, ChannelsNotice, GuestPassesUpsell, EmergencyTip,
//   VoiceModeNotice, Opus1mMergeNotice, OverageCreditUpsell.
//
// Contract: specs/035-onboarding-brand-port/contracts/logov2-rewrite-visual-specs.md § 6

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'
import { useReducedMotion } from '../../../hooks/useReducedMotion'
import { AnimatedAsterisk } from './AnimatedAsterisk'
import { CondensedLogo } from './CondensedLogo'
import { KosmosOnboardingFeed } from './Feed'
import type { KosmosSession, MinistryStatus } from './feedConfigs'
import {
  getLayoutMode,
  getKosmosSessionHistorySync,
  getMinistryAvailabilitySync,
} from './logoV2Utils'

// ---------------------------------------------------------------------------
// Ministry node table — citizen-facing Korean names plus token bindings.
// Ordering is fixed (KOROAD → KMA → HIRA → NMC) per AGENTS.md domain-data
// exception; KWCAG screen-reader narration enumerates in the same order.
// ---------------------------------------------------------------------------

type MinistryNode = {
  code: 'KOROAD' | 'KMA' | 'HIRA' | 'NMC'
  displayName: string
  tokenKey: 'agentSatelliteKoroad' | 'agentSatelliteKma' | 'agentSatelliteHira' | 'agentSatelliteNmc'
}

const MINISTRY_NODES: readonly MinistryNode[] = [
  { code: 'KOROAD', displayName: '한국도로공사', tokenKey: 'agentSatelliteKoroad' },
  { code: 'KMA', displayName: '기상청', tokenKey: 'agentSatelliteKma' },
  { code: 'HIRA', displayName: '건강보험심사평가원', tokenKey: 'agentSatelliteHira' },
  { code: 'NMC', displayName: '국립중앙의료원', tokenKey: 'agentSatelliteNmc' },
]

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type LogoV2Props = {
  /** Terminal column width override (defaults to `process.stdout.columns ?? 80`). */
  cols?: number
  /** Explicit mode override; when omitted, derived via `getLayoutMode(cols)`. */
  mode?: 'full' | 'condensed' | 'fallback'
  /** Session history entries (defaults to memdir Session-tier read). */
  sessionHistory?: KosmosSession[]
  /** Ministry availability snapshot (defaults to Spec 022 registry read). */
  ministryStatus?: MinistryStatus[]
  /** Model label for CondensedLogo mode. */
  model?: string
  /** Effort label for CondensedLogo mode. */
  effort?: string
  /** Coordinator-mode label for CondensedLogo mode. */
  coordinatorMode?: string
  /** Version string (used in full-mode subtitle). */
  version?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LogoV2({
  cols,
  mode,
  sessionHistory,
  ministryStatus,
  model,
  effort,
  coordinatorMode,
  version,
}: LogoV2Props): React.ReactElement {
  const theme = useTheme()
  const { prefersReducedMotion } = useReducedMotion()
  const termCols = cols ?? process.stdout.columns ?? 80
  const resolvedMode = mode ?? getLayoutMode(termCols)

  if (resolvedMode === 'fallback') {
    return (
      <Text color={theme.wordmark}>KOSMOS — 한국 공공서비스 대화창</Text>
    )
  }

  if (resolvedMode === 'condensed') {
    return (
      <CondensedLogo
        model={model}
        effort={effort}
        coordinatorMode={coordinatorMode}
      />
    )
  }

  const sessions = sessionHistory ?? getKosmosSessionHistorySync()
  const ministries = ministryStatus ?? getMinistryAvailabilitySync()
  const subtitleLine = version !== undefined
    ? `KOREAN PUBLIC SERVICE MULTI-AGENT OS · v${version}`
    : 'KOREAN PUBLIC SERVICE MULTI-AGENT OS'

  return (
    <Box flexDirection="column" alignItems="center">
      {/* Orbital ring container (rendered as a simple bracketed band; full  */}
      {/* vector arc is deferred to a future Epic — TUI cannot render SVG).   */}
      <Box flexDirection="column" alignItems="center">
        <Text color={theme.orbitalRing}>
          {prefersReducedMotion ? '╭───────────╮' : '╭─ orbital ─╮'}
        </Text>
        <Box flexDirection="row">
          <Text color={theme.orbitalRing}>│ </Text>
          <AnimatedAsterisk width={5} height={1} />
          <Text color={theme.orbitalRing}> │</Text>
        </Box>
        <Text color={theme.orbitalRing}>╰───────────╯</Text>
      </Box>
      {/* Wordmark + subtitle */}
      <Box marginTop={1} flexDirection="column" alignItems="center">
        <Text bold color={theme.wordmark}>KOSMOS</Text>
        <Text color={theme.subtitle}>{subtitleLine}</Text>
      </Box>
      {/* Ministry satellites */}
      <Box marginTop={1} flexDirection="row">
        {MINISTRY_NODES.map((node, idx) => (
          <React.Fragment key={node.code}>
            {idx > 0 && <Text color={theme.subtle}>{'  '}</Text>}
            <Text color={theme[node.tokenKey]}>●{node.code}</Text>
          </React.Fragment>
        ))}
      </Box>
      {/* Two-column feed */}
      <Box marginTop={1}>
        <KosmosOnboardingFeed
          sessionHistory={sessions}
          ministryStatus={ministries}
        />
      </Box>
    </Box>
  )
}
