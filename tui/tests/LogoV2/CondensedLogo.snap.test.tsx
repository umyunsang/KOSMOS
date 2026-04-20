// SPDX-License-Identifier: Apache-2.0
// T039 — CondensedLogo snapshot (Epic H #1302).
// Asserts wordmark = "KOSMOS" + zero CC brand strings in rendered output.

import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { CondensedLogo } from '../../src/components/onboarding/LogoV2/CondensedLogo'
import { ThemeProvider } from '../../src/theme/provider'

const BANNED = ['Claude', 'Clawd', 'GuestPasses', 'Anthropic', 'Apple Terminal']

describe('CondensedLogo', () => {
  it('renders the KOSMOS wordmark with model · effort · coordinatorMode segments', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <CondensedLogo
          model="K-EXAONE"
          effort="normal"
          coordinatorMode="default"
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS')
    expect(frame).toContain('K-EXAONE')
    expect(frame).toContain('normal')
    expect(frame).toContain('default')
    for (const banned of BANNED) expect(frame).not.toContain(banned)
    expect(frame).toMatchSnapshot()
  })

  it('omits segments when props undefined', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <CondensedLogo />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS')
    for (const banned of BANNED) expect(frame).not.toContain(banned)
    expect(frame).toMatchSnapshot()
  })
})
