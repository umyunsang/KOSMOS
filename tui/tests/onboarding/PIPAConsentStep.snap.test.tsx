// SPDX-License-Identifier: Apache-2.0
// T025 — PIPAConsentStep snapshot (Epic H #1302).
// Three snapshots: initial render, accept branch, decline branch.

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PIPAConsentStep } from '../../src/components/onboarding/PIPAConsentStep'
import { ThemeProvider } from '../../src/theme/provider'
import type { PIPAConsentRecord } from '../../src/memdir/consent'

const FIXTURE_SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

describe('PIPAConsentStep — initial render', () => {
  it('renders consent version, § 26 summary, ministries, and AAL label', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <PIPAConsentStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={FIXTURE_SESSION}
          aalGate="AAL1"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('개인정보 활용 동의 (v1)')
    expect(frame).toContain('개인정보 보호법 § 26 수탁자')
    expect(frame).toContain('한국도로공사')
    expect(frame).toContain('KOROAD')
    expect(frame).toContain('기상청')
    expect(frame).toContain('건강보험심사평가원')
    expect(frame).toContain('국립중앙의료원')
    expect(frame).toContain('기본 인증 단계')
    expect(frame).toContain('AAL1')
    expect(frame).toMatchSnapshot()
  })
})

describe('PIPAConsentStep — accept branch', () => {
  it('calls writeRecord and onAdvance exactly once on Enter', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})
    const writeRecord = mock((_record: PIPAConsentRecord) => {})

    const { stdin, lastFrame, rerender } = render(
      <ThemeProvider>
        <PIPAConsentStep
          onAdvance={onAdvance}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          aalGate="AAL1"
          writeRecord={writeRecord}
        />
      </ThemeProvider>,
    )

    stdin.write('\r') // Enter
    // Ink's render loop is async; yield to let the submit promise resolve.
    await new Promise((r) => setTimeout(r, 10))
    rerender(
      <ThemeProvider>
        <PIPAConsentStep
          onAdvance={onAdvance}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          aalGate="AAL1"
          writeRecord={writeRecord}
        />
      </ThemeProvider>,
    )

    expect(writeRecord).toHaveBeenCalledTimes(1)
    expect(onAdvance).toHaveBeenCalledTimes(1)
    expect(onExit).not.toHaveBeenCalled()

    const record = writeRecord.mock.calls[0]?.[0]
    expect(record).toBeDefined()
    expect(record?.consent_version).toBe('v1')
    expect(record?.aal_gate).toBe('AAL1')
    expect(record?.citizen_confirmed).toBe(true)
    expect(record?.session_id).toBe(FIXTURE_SESSION)
    expect(lastFrame()).toMatchSnapshot()
  })
})

describe('PIPAConsentStep — decline branch', () => {
  it('calls onExit once and writeRecord zero times on Escape', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})
    const writeRecord = mock((_record: PIPAConsentRecord) => {})

    const { stdin, lastFrame } = render(
      <ThemeProvider>
        <PIPAConsentStep
          onAdvance={onAdvance}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          aalGate="AAL1"
          writeRecord={writeRecord}
        />
      </ThemeProvider>,
    )

    stdin.write('\x1b') // Escape
    await new Promise((r) => setTimeout(r, 10))

    expect(onExit).toHaveBeenCalledTimes(1)
    expect(onAdvance).not.toHaveBeenCalled()
    expect(writeRecord).not.toHaveBeenCalled()
    expect(lastFrame()).toMatchSnapshot()
  })
})
