// SPDX-License-Identifier: Apache-2.0
// WelcomeV2 snapshot — CC-fidelity English welcome header + orbital cluster.
// Per user directive (2026-04-24): match CC's English welcome pattern
// (`Welcome to KOSMOS` mirrors CC's `Welcome to Claude Code`) — prior
// Korean-header Spec 035 invariant superseded.

import { describe, expect, it, afterEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { WelcomeV2 } from '../../src/components/LogoV2/WelcomeV2'
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
    expect(frame).toContain('Welcome to KOSMOS')
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
    expect(frame).toContain('Welcome to KOSMOS')
    expect(frame).toMatchSnapshot()
  })
})
