// Source: .references/claude-code-sourcemap/restored-src/src/components/AgentProgressLine.tsx (Claude Code 2.1.88, research-use)
// Note: Original attribution listed CoordinatorProgressLine.tsx which does not exist in restored-src.
//       AgentProgressLine.tsx is the closest upstream analog (phase glyph + progress line pattern).
// KOSMOS adaptation: maps CoordinatorPhaseFrame.phase to phase-indicator glyph.
//
// FR-043 (coordinator phase indicator), FR-050 (selector-isolated subscription).
// US4 scenario 1.

import React from 'react'
import { Box, Text } from 'ink'
import { useSessionStore } from '../../store/session-store'
import type { Phase } from '../../store/session-store'
import { useTheme } from '../../theme/provider'

// ---------------------------------------------------------------------------
// Phase glyph + label mapping (ASCII-safe, no Korean — FR-043)
// ---------------------------------------------------------------------------

const PHASE_GLYPH: Record<Phase, string> = {
  Research: '●',
  Synthesis: '◆',
  Implementation: '▶',
  Verification: '✓',
}

const PHASE_LABEL: Record<Phase, string> = {
  Research: 'Research',
  Synthesis: 'Synthesis',
  Implementation: 'Implementation',
  Verification: 'Verification',
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders the current coordinator phase as a single-line status bar at the
 * top of the conversation layout.
 *
 * Subscribes exclusively to `coordinator_phase` via selector isolation
 * (FR-050) — does NOT re-render on message or worker state changes.
 *
 * Returns null when `coordinator_phase` is null (session not yet started).
 */
export function PhaseIndicator(): React.ReactElement | null {
  const theme = useTheme()

  // Selector-isolated: only re-renders when coordinator_phase changes (FR-050).
  const phase = useSessionStore((s) => s.coordinator_phase)

  if (!phase) return null

  const glyph = PHASE_GLYPH[phase]
  const label = PHASE_LABEL[phase]

  return (
    <Box flexDirection="row" marginBottom={1}>
      <Text bold color={theme.orbitalRing}>
        {`${glyph} Phase: `}
      </Text>
      <Text bold color={theme.text}>
        {label}
      </Text>
    </Box>
  )
}
