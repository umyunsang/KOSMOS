// SPDX-License-Identifier: Apache-2.0
// T041 — WelcomeV2 snapshot (Epic H #1302).
// Korean welcome header + kosmosCore cluster; zero Apple-Terminal ASCII art.

import { describe, expect, it, afterEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { WelcomeV2 } from '../../src/components/onboarding/LogoV2/WelcomeV2'
import { ThemeProvider } from '../../src/theme/provider'

const SAVED_REDUCED = process.env.KOSMOS_REDUCED_MOTION
const SAVED_NO_COLOR = process.env.NO_COLOR

afterEach(() => {
  if (SAVED_REDUCED !== undefined)
    process.env.KOSMOS_REDUCED_MOTION = SAVED_REDUCED
  else delete process.env.KOSMOS_REDUCED_MOTION
  if (SAVED_NO_COLOR !== undefined) process.env.NO_COLOR = SAVED_NO_COLOR
  else delete process.env.NO_COLOR
})

const BANNED = ['Welcome to Claude Code', 'Apple Terminal']

describe('WelcomeV2', () => {
  it('renders the Korean welcome header + kosmosCore cluster (shimmer on)', () => {
    delete process.env.KOSMOS_REDUCED_MOTION
    delete process.env.NO_COLOR
    const { lastFrame } = render(
      <ThemeProvider>
        <WelcomeV2 version="0.1.0" />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS에 오신 것을 환영합니다')
    expect(frame).toContain('v0.1.0')
    expect(frame).toContain('*')
    for (const banned of BANNED) expect(frame).not.toContain(banned)
    expect(frame).toMatchSnapshot()
  })

  it('renders identically under reduced-motion', () => {
    process.env.KOSMOS_REDUCED_MOTION = '1'
    const { lastFrame } = render(
      <ThemeProvider>
        <WelcomeV2 version="0.1.0" />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('KOSMOS에 오신 것을 환영합니다')
    expect(frame).toMatchSnapshot()
  })
})
