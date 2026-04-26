// SPDX-License-Identifier: Apache-2.0
// KOSMOS ReplHeader — CC-fidelity launch surface for an empty conversation.
//
// Visual source of truth:
//   .references/claude-code-sourcemap/restored-src/src/components/LogoV2/WelcomeV2.tsx
//   + CondensedLogo.tsx + the REPL "first-run" stack (Claude Code 2.1.88)
//
// Stack (top-to-bottom) mirrors CC's launch screen:
//   1. WelcomeV2 ASCII banner (orbital-satellite motif)
//   2. Tips section — slash-command prompt + discovery hints
//   3. Status band — cwd · session · ministry coverage · model
//   4. Trailing blank for breathing room above the prompt input
//
// The status band shows the four ministry agents (KOROAD · KMA · HIRA · NMC)
// as presence pills, reinforcing the six-layer harness identity on every
// launch. Session ready text flows in from i18n so Korean users see
// "준비 완료" here, English builds see "Ready" — both stay below the band.

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../theme/provider'
import { useSessionStore } from '../store/session-store'
import { WelcomeV2 } from './LogoV2/WelcomeV2'

export interface ReplHeaderProps {
  sessionReadyText: string
}

const MINISTRY_PILLS: ReadonlyArray<{ code: string; colorKey: 'agentSatelliteKoroad' | 'agentSatelliteKma' | 'agentSatelliteHira' | 'agentSatelliteNmc' }> = [
  { code: 'KOROAD', colorKey: 'agentSatelliteKoroad' },
  { code: 'KMA',    colorKey: 'agentSatelliteKma' },
  { code: 'HIRA',   colorKey: 'agentSatelliteHira' },
  { code: 'NMC',    colorKey: 'agentSatelliteNmc' },
]

const TIPS: ReadonlyArray<{ keys: string; hint: string }> = [
  { keys: '/help',         hint: '전체 커맨드 보기' },
  { keys: '/status',       hint: '현재 세션 진행 상태 확인' },
  { keys: '/new',          hint: '새 세션 시작' },
  { keys: 'Shift ⇧ + ⇥',   hint: '권한 모드 전환 (default → plan → acceptEdits)' },
  { keys: 'Ctrl-C',        hint: '진행 중단 · 한 번 더 누르면 종료' },
]

export function ReplHeader({ sessionReadyText }: ReplHeaderProps): React.ReactElement {
  const theme = useTheme()
  const sessionId = useSessionStore((s) => s.session_id)
  const cwd = process.cwd()
  const home = process.env.HOME
  const displayCwd = home !== undefined && cwd.startsWith(home) ? `~${cwd.slice(home.length)}` : cwd
  const shortSession = sessionId !== '' ? sessionId.slice(0, 8) : 'pending'

  return (
    <Box flexDirection="column" marginTop={1} marginBottom={1}>
      <WelcomeV2 />

      <Box flexDirection="column" marginTop={1} paddingX={2}>
        <Box>
          <Text color={theme.subtitle} bold>팁 · </Text>
          <Text color={theme.inactive}>자주 쓰는 커맨드</Text>
        </Box>
        {TIPS.map((tip) => (
          <Box key={tip.keys} flexDirection="row">
            <Text color={theme.suggestion}>  {tip.keys.padEnd(18, ' ')}</Text>
            <Text color={theme.inactive} dimColor>{tip.hint}</Text>
          </Box>
        ))}
      </Box>

      <Box flexDirection="column" marginTop={1} paddingX={2}>
        <Box flexDirection="row">
          <Text color={theme.inactive} dimColor>cwd     </Text>
          <Text color={theme.subtle}>{displayCwd}</Text>
        </Box>
        <Box flexDirection="row">
          <Text color={theme.inactive} dimColor>session </Text>
          <Text color={theme.subtle}>{shortSession}</Text>
          <Text color={theme.inactive} dimColor>   model   </Text>
          <Text color={theme.subtle}>EXAONE / FriendliAI</Text>
        </Box>
        <Box flexDirection="row" marginTop={1}>
          <Text color={theme.inactive} dimColor>agents  </Text>
          {MINISTRY_PILLS.map((pill, idx) => (
            <Box key={pill.code}>
              <Text color={theme[pill.colorKey]}>● </Text>
              <Text color={theme.subtle}>{pill.code}</Text>
              {idx < MINISTRY_PILLS.length - 1 && <Text color={theme.inactive}>  </Text>}
            </Box>
          ))}
        </Box>
      </Box>

      <Box marginTop={1} paddingX={2}>
        <Text color={theme.inactive} dimColor>{sessionReadyText}</Text>
      </Box>
    </Box>
  )
}
