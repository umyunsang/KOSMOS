// SPDX-License-Identifier: Apache-2.0
// T035 — Onboarding full 3-step snapshot (Epic H #1302).
// Covers FR-012 end-to-end + SC-002 + SC-012 (fast-path).

import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { Onboarding } from '../../src/components/onboarding/Onboarding'
import { ThemeProvider } from '../../src/theme/provider'

const SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

describe('Onboarding — initial splash', () => {
  it('renders the LogoV2 splash when no memdir state is supplied', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding sessionId={SESSION} startStep="splash" />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS')
    expect(frame).toMatchSnapshot()
  })
})

describe('Onboarding — direct pipa-consent', () => {
  it('renders PIPAConsentStep when startStep="pipa-consent"', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding sessionId={SESSION} startStep="pipa-consent" />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('개인정보 활용 동의')
    expect(frame).toMatchSnapshot()
  })
})

describe('Onboarding — direct ministry-scope-ack', () => {
  it('renders MinistryScopeStep when startStep="ministry-scope-ack"', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding sessionId={SESSION} startStep="ministry-scope-ack" />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('부처 API 사용 동의')
    expect(frame).toMatchSnapshot()
  })
})

describe('Onboarding — fast-path resolver', () => {
  it('resolves to splash when both records are fresh', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding
          sessionId={SESSION}
          memdir={{
            consentRecord: { consent_version: 'v1' },
            scopeRecord: { scope_version: 'v1' },
          }}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS')
    expect(frame).not.toContain('개인정보 활용 동의')
    expect(frame).not.toContain('부처 API 사용 동의')
  })

  it('resolves to ministry-scope-ack when consent fresh but scope stale', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding
          sessionId={SESSION}
          memdir={{ consentRecord: { consent_version: 'v1' } }}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('부처 API 사용 동의')
  })

  it('resolves to splash when both records absent (full flow start)', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <Onboarding sessionId={SESSION} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS')
  })
})
