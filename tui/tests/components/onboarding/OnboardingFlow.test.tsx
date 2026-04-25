// SPDX-License-Identifier: Apache-2.0
// T050 (partial) — OnboardingFlow unit tests (FR-001/002, T045).

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { OnboardingFlow, resetOnboardingState } from '../../../src/components/onboarding/OnboardingFlow'
import { ThemeProvider } from '../../../src/theme/provider'
import {
  freshOnboardingState,
  isOnboardingComplete,
  type OnboardingStateT,
} from '../../../src/schemas/ui-l2/onboarding'

const SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

function mockLoader(state: OnboardingStateT) {
  return () => Promise.resolve(state)
}

function mockSaver() {
  return mock((_s: OnboardingStateT) => Promise.resolve())
}

describe('OnboardingFlow — loading state', () => {
  it('shows a loading indicator while state is loading', () => {
    // Delay the load resolution to catch the loading frame
    let resolve!: (s: OnboardingStateT) => void
    const loader = () => new Promise<OnboardingStateT>((r) => { resolve = r })

    const { lastFrame } = render(
      <ThemeProvider>
        <OnboardingFlow
          onComplete={() => {}}
          sessionId={SESSION}
          locale="ko"
          onLoadState={loader}
        />
      </ThemeProvider>,
    )

    const frame = lastFrame() ?? ''
    expect(frame).toContain('온보딩 로딩 중')
    resolve(freshOnboardingState())
  })
})

describe('OnboardingFlow — initial state renders preflight', () => {
  it('renders PreflightStep when current_step_index=0', async () => {
    const state = freshOnboardingState()

    const { lastFrame } = render(
      <ThemeProvider>
        <OnboardingFlow
          onComplete={() => {}}
          sessionId={SESSION}
          locale="ko"
          onLoadState={mockLoader(state)}
          onSaveState={mockSaver()}
        />
      </ThemeProvider>,
    )

    // Wait for async state load and re-render
    await new Promise((r) => setTimeout(r, 100))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('환경 점검')
    expect(frame).toContain('1 / 5')
  })
})

describe('OnboardingFlow — isolation mode', () => {
  it('renders the isolated step (theme, step 2) when isolatedStep=theme', async () => {
    const state = freshOnboardingState()

    const { lastFrame } = render(
      <ThemeProvider>
        <OnboardingFlow
          onComplete={() => {}}
          isolatedStep="theme"
          sessionId={SESSION}
          locale="ko"
          onLoadState={mockLoader(state)}
          onSaveState={mockSaver()}
        />
      </ThemeProvider>,
    )

    await new Promise((r) => setTimeout(r, 100))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('테마 미리보기')
    expect(frame).toContain('2 / 5')
  })

  it('renders ministry-scope step (step 4) when isolatedStep=ministry-scope', async () => {
    const state = freshOnboardingState()

    const { lastFrame } = render(
      <ThemeProvider>
        <OnboardingFlow
          onComplete={() => {}}
          isolatedStep="ministry-scope"
          sessionId={SESSION}
          locale="ko"
          onLoadState={mockLoader(state)}
          onSaveState={mockSaver()}
        />
      </ThemeProvider>,
    )

    await new Promise((r) => setTimeout(r, 100))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('부처 API 사용 동의')
  })
})

describe('OnboardingFlow — advance from preflight saves state', () => {
  it('calls onSaveState when preflight step advances', async () => {
    const state = freshOnboardingState()
    const saver = mockSaver()

    const { stdin } = render(
      <ThemeProvider>
        <OnboardingFlow
          onComplete={() => {}}
          sessionId={SESSION}
          locale="ko"
          onLoadState={mockLoader(state)}
          onSaveState={saver}
        />
      </ThemeProvider>,
    )

    await new Promise((r) => setTimeout(r, 100))
    stdin.write('\r') // Enter on preflight
    await new Promise((r) => setTimeout(r, 100))

    expect(saver).toHaveBeenCalled()
    const savedState = saver.mock.calls[0]?.[0]
    expect(savedState?.current_step_index).toBe(1)
    // completed_at should be set for step 0
    expect(savedState?.steps[0]?.completed_at).not.toBeNull()
  })
})

describe('resetOnboardingState', () => {
  it('resets current_step_index to 0 but preserves completed_at audit trail', async () => {
    const state: OnboardingStateT = {
      ...freshOnboardingState(),
      current_step_index: 3,
      steps: freshOnboardingState().steps.map((s, i) =>
        i < 3 ? { ...s, completed_at: '2026-04-25T00:00:00.000Z' } : s,
      ),
    }

    const saver = mock((_s: OnboardingStateT) => Promise.resolve())
    const reset = await resetOnboardingState(state, saver)

    expect(reset.current_step_index).toBe(0)
    // Audit trail preserved
    for (let i = 0; i < 3; i++) {
      expect(reset.steps[i]?.completed_at).toBe('2026-04-25T00:00:00.000Z')
    }
    expect(saver).toHaveBeenCalledTimes(1)
    expect(isOnboardingComplete(reset)).toBe(false)
  })
})
