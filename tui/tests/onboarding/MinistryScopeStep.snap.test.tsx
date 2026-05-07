// SPDX-License-Identifier: Apache-2.0
// T034 — MinistryScopeStep snapshot (Epic H #1302).
// 3 snapshots: initial 4-row render, partial opt-in (KOROAD+KMA only),
// all-declined terminal state.

import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { MinistryScopeStep } from '../../src/components/onboarding/MinistryScopeStep'
import { ThemeProvider } from '../../src/theme/provider'

const SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

describe('MinistryScopeStep — initial render (all opted in)', () => {
  it('renders all four ministries with Korean names + English codes', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <MinistryScopeStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={SESSION}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('부처 API 사용 동의 (v1)')
    expect(frame).toContain('한국도로공사')
    expect(frame).toContain('(KOROAD)')
    expect(frame).toContain('기상청')
    expect(frame).toContain('(KMA)')
    expect(frame).toContain('건강보험심사평가원')
    expect(frame).toContain('(HIRA)')
    expect(frame).toContain('국립중앙의료원')
    expect(frame).toContain('(NMC)')
    expect(frame).toMatchSnapshot()
  })
})

describe('MinistryScopeStep — partial opt-in (KOROAD+KMA)', () => {
  it('renders mixed toggle state', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <MinistryScopeStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={SESSION}
          initialOptIns={{
            KOROAD: true,
            KMA: true,
            HIRA: false,
            NMC: false,
          }}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toMatchSnapshot()
  })
})

describe('MinistryScopeStep — all declined', () => {
  it('renders all four rows declined', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <MinistryScopeStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={SESSION}
          initialOptIns={{
            KOROAD: false,
            KMA: false,
            HIRA: false,
            NMC: false,
          }}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toMatchSnapshot()
  })
})
