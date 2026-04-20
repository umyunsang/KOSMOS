// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/CondensedLogo.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'

type Props = {
  model?: string           // e.g. "K-EXAONE"
  effort?: string          // e.g. "normal"
  coordinatorMode?: string // from Spec 033 PermissionMode
}

/**
 * CondensedLogo renders a single-line header for terminals narrower than 80
 * columns.  Shape:
 *
 *   * KOSMOS — <model> · <effort> · <coordinatorMode>
 *
 * The asterisk is rendered in the `kosmosCore` token; "KOSMOS" is rendered in
 * the `wordmark` token (bold); the remainder is rendered in the `subtitle`
 * token.  All Text nodes carry `backgroundColor={theme.background}` so the
 * line stays on the KOSMOS navy background.
 *
 * If all three optional props are undefined / empty the tail is omitted and
 * the component renders:  * KOSMOS
 *
 * FR-019 · [ag-logov2] r32
 */
export function CondensedLogo({
  model,
  effort,
  coordinatorMode,
}: Props): React.ReactElement {
  const theme = useTheme()

  const segments: string[] = [model, effort, coordinatorMode].filter(
    (s): s is string => s !== undefined && s.length > 0,
  )

  const tail: string =
    segments.length > 0 ? ' \u2014 ' + segments.join(' \u00B7 ') : ''

  return (
    <Box flexDirection="row">
      <Text color={theme.kosmosCore} backgroundColor={theme.background}>
        {'*'}
      </Text>
      <Text backgroundColor={theme.background}>{' '}</Text>
      <Text bold color={theme.wordmark} backgroundColor={theme.background}>
        {'KOSMOS'}
      </Text>
      <Text color={theme.subtitle} backgroundColor={theme.background}>
        {tail}
      </Text>
    </Box>
  )
}
