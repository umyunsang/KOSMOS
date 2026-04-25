// SPDX-License-Identifier: Apache-2.0
// T050 (partial) — PipaConsentStep unit tests (FR-001 step 3, FR-006, T042).

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PipaConsentStep } from '../../../src/components/onboarding/PipaConsentStep'
import { ThemeProvider } from '../../../src/theme/provider'

const FIXTURE_SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

describe('PipaConsentStep — initial render (Korean)', () => {
  it('renders PIPA title, trustee notice, step 3/5 (FR-006)', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={FIXTURE_SESSION}
          locale="ko"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('PIPA 동의')
    expect(frame).toContain('3 / 5')
    // FR-006: trustee notice must be visible
    expect(frame).toContain('수탁자 책임 안내')
    expect(frame).toContain('§26')
    // Ministry data categories
    expect(frame).toContain('KOROAD')
    expect(frame).toContain('HIRA')
    // Audit preservation note (FR-007)
    expect(frame).toContain('FR-007')
  })
})

describe('PipaConsentStep — initial render (English)', () => {
  it('renders English trustee notice', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={() => {}}
          onExit={() => {}}
          sessionId={FIXTURE_SESSION}
          locale="en"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('PIPA consent')
    expect(frame).toContain('Trustee Responsibility Notice')
    expect(frame).toContain('PIPA §26')
    expect(frame).toContain('3 / 5')
  })
})

describe('PipaConsentStep — accept branch', () => {
  it('calls writeRecord and onAdvance on Enter / Y', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})
    const writeRecord = mock((_sid: string, _ts: string) => {})

    const { stdin } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={onAdvance}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          writeRecord={writeRecord}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\r') // Enter
    await new Promise((r) => setTimeout(r, 20))

    expect(writeRecord).toHaveBeenCalledTimes(1)
    expect(onAdvance).toHaveBeenCalledTimes(1)
    expect(onExit).not.toHaveBeenCalled()

    const [sid, ts] = writeRecord.mock.calls[0] ?? []
    expect(sid).toBe(FIXTURE_SESSION)
    expect(typeof ts).toBe('string')
    expect(ts?.length).toBeGreaterThan(0)
  })

  it('accepts Y key to consent', async () => {
    const onAdvance = mock(() => {})
    const writeRecord = mock((_sid: string, _ts: string) => {})

    const { stdin } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={onAdvance}
          onExit={() => {}}
          sessionId={FIXTURE_SESSION}
          writeRecord={writeRecord}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('y')
    await new Promise((r) => setTimeout(r, 20))

    expect(onAdvance).toHaveBeenCalledTimes(1)
  })
})

describe('PipaConsentStep — decline branch', () => {
  it('calls onExit on Escape without writing record', async () => {
    const onAdvance = mock(() => {})
    const onExit = mock(() => {})
    const writeRecord = mock((_sid: string, _ts: string) => {})

    const { stdin } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={onAdvance}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          writeRecord={writeRecord}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('\x1b') // Escape
    await new Promise((r) => setTimeout(r, 10))

    expect(onExit).toHaveBeenCalledTimes(1)
    expect(onAdvance).not.toHaveBeenCalled()
    expect(writeRecord).not.toHaveBeenCalled()
  })

  it('accepts N key to decline', async () => {
    const onExit = mock(() => {})

    const { stdin } = render(
      <ThemeProvider>
        <PipaConsentStep
          onAdvance={() => {}}
          onExit={onExit}
          sessionId={FIXTURE_SESSION}
          locale="ko"
        />
      </ThemeProvider>,
    )

    stdin.write('n')
    await new Promise((r) => setTimeout(r, 10))

    expect(onExit).toHaveBeenCalledTimes(1)
  })
})
