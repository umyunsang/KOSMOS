// T018 — AnimatedAsterisk snapshot (Epic H #1302)
// Two frames: shimmering (reduced-motion OFF) and static (reduced-motion ON).
// Verifies FR-018 (asterisk rendering) + FR-024 (reduced-motion fallback).
//
// Contract: specs/035-onboarding-brand-port/contracts/logov2-rewrite-visual-specs.md § 1

import { describe, expect, it, afterEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { AnimatedAsterisk } from '../../src/components/onboarding/LogoV2/AnimatedAsterisk'
import { ThemeProvider } from '../../src/theme/provider'

const SAVED_NO_COLOR = process.env.NO_COLOR
const SAVED_REDUCED_MOTION = process.env.KOSMOS_REDUCED_MOTION

afterEach(() => {
  if (SAVED_NO_COLOR !== undefined) process.env.NO_COLOR = SAVED_NO_COLOR
  else delete process.env.NO_COLOR
  if (SAVED_REDUCED_MOTION !== undefined)
    process.env.KOSMOS_REDUCED_MOTION = SAVED_REDUCED_MOTION
  else delete process.env.KOSMOS_REDUCED_MOTION
})

describe('AnimatedAsterisk', () => {
  it('renders the asterisk glyph at t=0 with shimmer enabled', () => {
    delete process.env.NO_COLOR
    delete process.env.KOSMOS_REDUCED_MOTION
    const { lastFrame } = render(
      <ThemeProvider>
        <AnimatedAsterisk width={5} height={3} prefersReducedMotion={false} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('*')
    expect(frame).toMatchSnapshot()
  })

  it('renders a static asterisk under reduced-motion', () => {
    process.env.KOSMOS_REDUCED_MOTION = '1'
    const { lastFrame } = render(
      <ThemeProvider>
        <AnimatedAsterisk width={5} height={3} prefersReducedMotion={true} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('*')
    expect(frame).toMatchSnapshot()
  })
})
