// SPDX-License-Identifier: Apache-2.0
// T050 (partial) — ThemeStep unit tests (FR-001 step 2, FR-035, T041).

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ThemeStep } from '../../../src/components/onboarding/ThemeStep'
import { ThemeProvider } from '../../../src/theme/provider'
import { UFO_PALETTE } from '../../../src/schemas/ui-l2/ufo'

describe('ThemeStep — initial render', () => {
  it('renders the theme step title and step progress', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('테마 미리보기')
    expect(frame).toContain('2 / 5')
  })

  it('renders the UFO mascot purple palette tokens (FR-035)', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    // Palette values should appear in the rendered output
    expect(frame).toContain(UFO_PALETTE.body)
    expect(frame).toContain(UFO_PALETTE.background)
  })

  it('renders English title when locale=en', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="en"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Theme preview')
    expect(frame).toContain('2 / 5')
  })

  it('shows UFO dome and saucer ASCII art', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    // The UFO's dome (▛███▜) or saucer should appear
    expect(frame.length).toBeGreaterThan(0)
    // At least one of the saucer characters
    expect(frame).toContain('█')
  })
})

describe('ThemeStep — keyboard navigation', () => {
  it('calls onAdvance with selected theme on Enter', async () => {
    const onAdvance = mock((_theme: 'dark' | 'light' | 'system') => {})
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={onAdvance}
          onExit={onExit}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\r') // Enter with default selection (dark)
    await new Promise((r) => setTimeout(r, 10))

    expect(onAdvance).toHaveBeenCalledTimes(1)
    expect(onAdvance.mock.calls[0]?.[0]).toBe('dark')
    expect(onExit).not.toHaveBeenCalled()
  })

  it('calls onExit on Escape', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <ThemeStep
          onAdvance={onAdvance}
          onExit={onExit}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\x1b')
    await new Promise((r) => setTimeout(r, 10))

    expect(onExit).toHaveBeenCalledTimes(1)
    expect(onAdvance).not.toHaveBeenCalled()
  })
})
