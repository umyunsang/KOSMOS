// Source: .references/claude-code-sourcemap/restored-src/src/components/FastIcon.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE + file rename per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9

import React, { useEffect, useState } from 'react'
import { Text } from 'ink'
import { useTheme } from '../../theme/provider'
import { useReducedMotion } from '../../hooks/useReducedMotion'

type Props = {
  shimmering?: boolean // defaults to false
}

/**
 * KosmosCoreIcon renders a single `*` (U+002A) glyph in the `kosmosCore`
 * theme token.  When `shimmering === true` AND reduced motion is not active,
 * the glyph cycles between `kosmosCore` and `kosmosCoreShimmer` at 6 fps
 * (166 ms interval), matching the AnimatedAsterisk cadence.
 *
 * Accessibility anchor: [ag-logo-wordmark] row 154 (component-catalog.md)
 * FR-023 (035-onboarding-brand-port spec)
 */
export function KosmosCoreIcon({ shimmering = false }: Props): React.ReactElement {
  const theme = useTheme()
  const { prefersReducedMotion } = useReducedMotion()

  const animationActive = shimmering && !prefersReducedMotion

  const [phase, setPhase] = useState<'base' | 'shimmer'>('base')

  useEffect(() => {
    if (!animationActive) {
      setPhase('base')
      return
    }

    const id = setInterval(() => {
      setPhase((prev) => (prev === 'base' ? 'shimmer' : 'base'))
    }, 166)

    return () => {
      clearInterval(id)
    }
  }, [animationActive])

  const currentColor =
    animationActive && phase === 'shimmer'
      ? theme.kosmosCoreShimmer
      : theme.kosmosCore

  return <Text color={currentColor}>*</Text>
}
