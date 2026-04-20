// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/AnimatedAsterisk.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9

import React, { useEffect, useState } from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../../../theme/provider'
import { useReducedMotion } from '../../../hooks/useReducedMotion'

// Frame interval matching CC useShimmerAnimation.ts budget: 6 fps ≈ 166 ms.
const SHIMMER_INTERVAL_MS = 166

type ShimmerPhase = 'base' | 'shimmer'

type Props = {
  width?: number
  height?: number
  prefersReducedMotion?: boolean
}

/**
 * AnimatedAsterisk — KOSMOS orbital-core glyph.
 *
 * Renders a U+002A asterisk centred inside an Ink Box.  When reduced-motion
 * is off, the glyph cycles between `kosmosCore` and `kosmosCoreShimmer` at
 * 6 fps (166 ms frame interval), matching CC useShimmerAnimation.ts cadence.
 * When reduced-motion is on the interval is never created, eliminating
 * re-render overhead entirely.
 *
 * Token bindings: kosmosCore, kosmosCoreShimmer (ThemeToken).
 * Accessibility: [ag-logov2] row 31 — no motion artefacts under NO_COLOR /
 * KOSMOS_REDUCED_MOTION.
 */
export function AnimatedAsterisk({
  width = 5,
  height = 3,
  prefersReducedMotion: prefersReducedMotionProp,
}: Props): React.ReactElement {
  const theme = useTheme()
  const { prefersReducedMotion: hookValue } = useReducedMotion()

  // Caller-supplied prop takes precedence; fall back to the hook.
  const reducedMotion =
    prefersReducedMotionProp !== undefined ? prefersReducedMotionProp : hookValue

  const [phase, setPhase] = useState<ShimmerPhase>('base')

  useEffect(() => {
    // Do not start the animation loop when reduced-motion is requested.
    if (reducedMotion) {
      return
    }

    const id = setInterval(() => {
      setPhase((prev) => (prev === 'base' ? 'shimmer' : 'base'))
    }, SHIMMER_INTERVAL_MS)

    return () => {
      clearInterval(id)
    }
  }, [reducedMotion])

  const currentColor =
    reducedMotion || phase === 'base' ? theme.kosmosCore : theme.kosmosCoreShimmer

  return (
    <Box
      flexDirection="column"
      width={width}
      height={height}
      alignItems="center"
      justifyContent="center"
    >
      <Text color={currentColor}>*</Text>
    </Box>
  )
}
