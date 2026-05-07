// SPDX-License-Identifier: Apache-2.0
// T042 — UmmayaCoreIcon snapshot (Epic H #1302).
// 2 snapshots: shimmering vs static; zero FastIcon/chromeYellow/lightning refs.

import { describe, expect, it, afterEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { UmmayaCoreIcon } from '../../src/components/chrome/UmmayaCoreIcon'
import { ThemeProvider } from '../../src/theme/provider'

const SAVED_REDUCED = process.env.UMMAYA_REDUCED_MOTION
const SAVED_NO_COLOR = process.env.NO_COLOR

afterEach(() => {
  if (SAVED_REDUCED !== undefined)
    process.env.UMMAYA_REDUCED_MOTION = SAVED_REDUCED
  else delete process.env.UMMAYA_REDUCED_MOTION
  if (SAVED_NO_COLOR !== undefined) process.env.NO_COLOR = SAVED_NO_COLOR
  else delete process.env.NO_COLOR
})

const BANNED = ['FastIcon', 'chromeYellow', 'lightning', '⚡']

describe('UmmayaCoreIcon', () => {
  it('renders a shimmering asterisk when shimmering=true + reduced-motion off', () => {
    delete process.env.UMMAYA_REDUCED_MOTION
    delete process.env.NO_COLOR
    const { lastFrame } = render(
      <ThemeProvider>
        <UmmayaCoreIcon shimmering={true} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('*')
    for (const banned of BANNED) expect(frame).not.toContain(banned)
    expect(frame).toMatchSnapshot()
  })

  it('renders a static asterisk under reduced-motion', () => {
    process.env.UMMAYA_REDUCED_MOTION = '1'
    const { lastFrame } = render(
      <ThemeProvider>
        <UmmayaCoreIcon shimmering={true} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('*')
    expect(frame).toMatchSnapshot()
  })
})
