// SPDX-License-Identifier: Apache-2.0
// T050 (partial) — PreflightStep unit tests (FR-001 step 1, T040).

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PreflightStep, runPreflightChecks } from '../../../src/components/onboarding/PreflightStep'
import { ThemeProvider } from '../../../src/theme/provider'

describe('runPreflightChecks', () => {
  it('returns at least 2 check items', () => {
    const checks = runPreflightChecks()
    expect(checks.length).toBeGreaterThanOrEqual(2)
  })

  it('each check has a label and a passed boolean', () => {
    const checks = runPreflightChecks()
    for (const check of checks) {
      expect(typeof check.label).toBe('string')
      expect(check.label.length).toBeGreaterThan(0)
      expect(typeof check.passed).toBe('boolean')
    }
  })

  it('Bun version check passes or has a note', () => {
    const checks = runPreflightChecks()
    const bunCheck = checks.find((c) => c.label.includes('Bun') || c.label === 'Bun ≥ 1.2')
    expect(bunCheck).toBeDefined()
  })
})

describe('PreflightStep — initial render (Korean)', () => {
  it('renders the preflight title and progress dots', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <PreflightStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('환경 점검')
    // Step 1 of 5 progress
    expect(frame).toContain('1 / 5')
  })
})

describe('PreflightStep — initial render (English)', () => {
  it('renders the English preflight title', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <PreflightStep
          onAdvance={() => {}}
          onExit={() => {}}
          locale="en"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Preflight check')
    expect(frame).toContain('1 / 5')
  })
})

describe('PreflightStep — Enter advances', () => {
  it('calls onAdvance on Enter keypress', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <PreflightStep
          onAdvance={onAdvance}
          onExit={onExit}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\r')
    await new Promise((r) => setTimeout(r, 10))

    expect(onAdvance).toHaveBeenCalledTimes(1)
    expect(onExit).not.toHaveBeenCalled()
  })
})

describe('PreflightStep — Esc exits', () => {
  it('calls onExit on Escape keypress', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <PreflightStep
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
