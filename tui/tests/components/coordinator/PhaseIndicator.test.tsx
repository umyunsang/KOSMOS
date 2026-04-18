// T089 — PhaseIndicator component tests
// Asserts all 4 coordinator phase values render correctly.
// Also verifies that an active StreamingMessage is not disrupted when phase changes.
// FR-043 (phase indicator), US4 scenario 1.

import { describe, expect, it, beforeEach } from 'bun:test'
import React from 'react'
import { Box, Text } from 'ink'
import { render } from 'ink-testing-library'
import { PhaseIndicator } from '../../../src/components/coordinator/PhaseIndicator'
import { ThemeProvider } from '../../../src/theme/provider'
import { dispatchSessionAction, sessionStore } from '../../../src/store/session-store'
import type { Phase } from '../../../src/store/session-store'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore() {
  sessionStore.dispatch({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

function Harness() {
  return (
    <ThemeProvider>
      <PhaseIndicator />
    </ThemeProvider>
  )
}

/** Minimal streaming message stub to confirm it is not disrupted. */
function HarnessWithStreaming() {
  return (
    <ThemeProvider>
      <Box flexDirection="column">
        <PhaseIndicator />
        <Text>streaming-content-marker</Text>
      </Box>
    </ThemeProvider>
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  resetStore()
})

describe('PhaseIndicator — null phase', () => {
  it('renders nothing when coordinator_phase is null', () => {
    const { lastFrame } = render(<Harness />)
    // Component returns null — frame should be empty or whitespace only
    expect((lastFrame() ?? '').trim()).toBe('')
  })
})

describe('PhaseIndicator — Research', () => {
  it('renders Research phase glyph and label', () => {
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Research' })
    const { lastFrame } = render(<Harness />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Research')
    expect(frame).toContain('●')
  })
})

describe('PhaseIndicator — Synthesis', () => {
  it('renders Synthesis phase glyph and label', () => {
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Synthesis' })
    const { lastFrame } = render(<Harness />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Synthesis')
    expect(frame).toContain('◆')
  })
})

describe('PhaseIndicator — Implementation', () => {
  it('renders Implementation phase glyph and label', () => {
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Implementation' })
    const { lastFrame } = render(<Harness />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Implementation')
    expect(frame).toContain('▶')
  })
})

describe('PhaseIndicator — Verification', () => {
  it('renders Verification phase glyph and label', () => {
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Verification' })
    const { lastFrame } = render(<Harness />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Verification')
    expect(frame).toContain('✓')
  })
})

describe('PhaseIndicator — all four phases cycle', () => {
  it('renders all 4 phase values without throwing', () => {
    const phases: Phase[] = ['Research', 'Synthesis', 'Implementation', 'Verification']
    for (const phase of phases) {
      dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase })
      const { lastFrame } = render(<Harness />)
      const frame = lastFrame() ?? ''
      expect(frame).toContain(phase)
    }
  })
})

describe('PhaseIndicator — does not disrupt StreamingMessage', () => {
  it('streaming content marker is still present when phase indicator is rendered', () => {
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Implementation' })
    const { lastFrame } = render(<HarnessWithStreaming />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Implementation')
    expect(frame).toContain('streaming-content-marker')
  })
})
