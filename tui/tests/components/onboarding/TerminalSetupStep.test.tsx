// SPDX-License-Identifier: Apache-2.0
// T050 (partial) — TerminalSetupStep unit tests (FR-001 step 5, FR-005, T044).

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { TerminalSetupStep } from '../../../src/components/onboarding/TerminalSetupStep'
import { ThemeProvider } from '../../../src/theme/provider'
import {
  freshAccessibilityPreference,
  type AccessibilityPreferenceT,
} from '../../../src/schemas/ui-l2/a11y'

describe('TerminalSetupStep — initial render', () => {
  it('renders the terminal setup title and step 5/5', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('터미널 설정')
    expect(frame).toContain('5 / 5')
  })

  it('renders four accessibility toggles (FR-005)', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('스크린리더 친화 모드')
    expect(frame).toContain('큰 글씨')
    expect(frame).toContain('고대비')
    expect(frame).toContain('애니메이션 줄이기')
  })

  it('renders Shift+Tab keybinding hint', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Shift+Tab')
  })

  it('renders English labels when locale=en', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="en"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Terminal setup')
    expect(frame).toContain('Screen-reader friendly mode')
    expect(frame).toContain('Large font')
    expect(frame).toContain('High contrast')
    expect(frame).toContain('Reduced motion')
  })
})

describe('TerminalSetupStep — initial preference values', () => {
  it('shows checked toggles for provided initial preference', () => {
    const initPref: AccessibilityPreferenceT = {
      ...freshAccessibilityPreference(),
      large_font: true,
      high_contrast: false,
    }

    const { lastFrame } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={() => {}}
          initialPreference={initPref}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    // large_font=true should show a ✓
    expect(frame).toContain('[✓]')
  })
})

describe('TerminalSetupStep — Enter advances with preferences', () => {
  it('calls onAdvance with the current preference on Enter', async () => {
    const onAdvance = mock((_pref: AccessibilityPreferenceT) => {})
    const onExit = mock(() => {})
    const writePreference = mock((_pref: AccessibilityPreferenceT) => {})

    const { stdin } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={onAdvance}
          onExit={onExit}
          writePreference={writePreference}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\r')
    await new Promise((r) => setTimeout(r, 20))

    expect(onAdvance).toHaveBeenCalledTimes(1)
    const pref = onAdvance.mock.calls[0]?.[0]
    expect(pref).toBeDefined()
    expect(typeof pref?.screen_reader).toBe('boolean')
    expect(typeof pref?.large_font).toBe('boolean')
    expect(typeof pref?.high_contrast).toBe('boolean')
    expect(typeof pref?.reduced_motion).toBe('boolean')
  })
})

describe('TerminalSetupStep — Space toggles and persists (FR-005 / SC-011)', () => {
  it('toggles the selected item and calls writePreference immediately', async () => {
    const onAdvance = mock((_pref: AccessibilityPreferenceT) => {})
    const writePreference = mock((_pref: AccessibilityPreferenceT) => {})

    const { stdin } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={onAdvance}
          onExit={() => {}}
          writePreference={writePreference}
          locale="ko"
        />
      </ThemeProvider>,
    )

    // Space toggles the currently selected (first) item
    stdin.write(' ')
    await new Promise((r) => setTimeout(r, 20))

    // writePreference is called immediately on toggle (SC-011 ≤500 ms)
    expect(writePreference).toHaveBeenCalledTimes(1)
    const savedPref = writePreference.mock.calls[0]?.[0]
    expect(savedPref).toBeDefined()
    // The first toggle key is screen_reader
    expect(savedPref?.screen_reader).toBe(true)
  })
})

describe('TerminalSetupStep — Esc exits', () => {
  it('calls onExit on Escape', async () => {
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <TerminalSetupStep
          onAdvance={() => {}}
          onExit={onExit}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\x1b')
    await new Promise((r) => setTimeout(r, 10))

    expect(onExit).toHaveBeenCalledTimes(1)
  })
})
