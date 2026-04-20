// T017 — LogoV2 snapshot matrix (Epic H #1302)
// Matrix: { 80, 60, 45 cols } × { prefersReducedMotion: true, false } = 6 snapshots
// Plus banned-import grep: rendered output must contain zero CC brand strings.
//
// Contract: specs/035-onboarding-brand-port/contracts/logov2-rewrite-visual-specs.md § 6
// FR-017, SC-006, SC-007.

import { describe, expect, it, afterEach, beforeEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { LogoV2 } from '../../src/components/onboarding/LogoV2/LogoV2'
import { ThemeProvider } from '../../src/theme/provider'
import type { KosmosSession, MinistryStatus } from '../../src/components/onboarding/LogoV2/feedConfigs'

// ---------------------------------------------------------------------------
// Deterministic fixtures
// ---------------------------------------------------------------------------

const FIXTURE_SESSIONS: KosmosSession[] = [
  {
    sessionId: '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60',
    queryLabel: '교통 사고 다발 구간',
    timestampIso: '2026-04-20T14:32:05Z',
  },
  {
    sessionId: '018f9123-abc4-7bef-8d1e-1a2b3c4d5e6f',
    queryLabel: '오늘 날씨',
    timestampIso: '2026-04-20T09:11:42Z',
  },
]

const FIXTURE_MINISTRIES: MinistryStatus[] = [
  { ministryCode: 'KOROAD', displayName: '한국도로공사', available: true },
  { ministryCode: 'KMA', displayName: '기상청', available: true },
  { ministryCode: 'HIRA', displayName: '건강보험심사평가원', available: false },
  { ministryCode: 'NMC', displayName: '국립중앙의료원', available: true },
]

// ---------------------------------------------------------------------------
// Env management — reduced-motion is read at useReducedMotion() call time.
// ---------------------------------------------------------------------------

const SAVED_NO_COLOR = process.env.NO_COLOR
const SAVED_REDUCED_MOTION = process.env.KOSMOS_REDUCED_MOTION

function setReducedMotion(on: boolean): void {
  if (on) {
    process.env.KOSMOS_REDUCED_MOTION = '1'
  } else {
    delete process.env.KOSMOS_REDUCED_MOTION
    delete process.env.NO_COLOR
  }
}

afterEach(() => {
  if (SAVED_NO_COLOR !== undefined) process.env.NO_COLOR = SAVED_NO_COLOR
  else delete process.env.NO_COLOR
  if (SAVED_REDUCED_MOTION !== undefined)
    process.env.KOSMOS_REDUCED_MOTION = SAVED_REDUCED_MOTION
  else delete process.env.KOSMOS_REDUCED_MOTION
})

// ---------------------------------------------------------------------------
// Banned-import / banned-string scan (I-22 — SC-006 citizen-visible surface)
// ---------------------------------------------------------------------------

const BANNED_STRINGS = [
  'Clawd',
  'Claude',
  'GuestPasses',
  'Anthropic',
  'Apple Terminal',
  'Opus 1M',
  'VoiceMode',
  'Channels',
  'Overage',
  'EmergencyTip',
] as const

function assertNoBannedStrings(frame: string): void {
  for (const banned of BANNED_STRINGS) {
    expect(frame).not.toContain(banned)
  }
}

// ---------------------------------------------------------------------------
// Snapshot matrix
// ---------------------------------------------------------------------------

type MatrixCase = {
  cols: number
  reduced: boolean
  label: string
}

const MATRIX: readonly MatrixCase[] = [
  { cols: 80, reduced: false, label: '80-cols-shimmer' },
  { cols: 80, reduced: true, label: '80-cols-reduced-motion' },
  { cols: 60, reduced: false, label: '60-cols-shimmer' },
  { cols: 60, reduced: true, label: '60-cols-reduced-motion' },
  { cols: 45, reduced: false, label: '45-cols-shimmer' },
  { cols: 45, reduced: true, label: '45-cols-reduced-motion' },
]

describe('LogoV2 snapshot matrix', () => {
  for (const tc of MATRIX) {
    describe(`case ${tc.label}`, () => {
      beforeEach(() => setReducedMotion(tc.reduced))

      it(`renders deterministically at ${tc.cols} cols (reduced-motion=${tc.reduced})`, () => {
        const { lastFrame } = render(
          <ThemeProvider>
            <LogoV2
              cols={tc.cols}
              sessionHistory={FIXTURE_SESSIONS}
              ministryStatus={FIXTURE_MINISTRIES}
              model="K-EXAONE"
              effort="normal"
              coordinatorMode="default"
              version="0.0.0"
            />
          </ThemeProvider>,
        )
        const frame = lastFrame() ?? ''
        expect(frame).toMatchSnapshot()
      })

      it(`contains zero banned CC brand strings at ${tc.cols} cols`, () => {
        const { lastFrame } = render(
          <ThemeProvider>
            <LogoV2
              cols={tc.cols}
              sessionHistory={FIXTURE_SESSIONS}
              ministryStatus={FIXTURE_MINISTRIES}
              model="K-EXAONE"
              effort="normal"
              coordinatorMode="default"
            />
          </ThemeProvider>,
        )
        const frame = lastFrame() ?? ''
        assertNoBannedStrings(frame)
      })
    })
  }
})

describe('LogoV2 wordmark presence', () => {
  it('renders "KOSMOS" wordmark at every breakpoint', () => {
    for (const cols of [80, 60, 45]) {
      const { lastFrame } = render(
        <ThemeProvider>
          <LogoV2
            cols={cols}
            sessionHistory={FIXTURE_SESSIONS}
            ministryStatus={FIXTURE_MINISTRIES}
            model="K-EXAONE"
            effort="normal"
            coordinatorMode="default"
          />
        </ThemeProvider>,
      )
      const frame = lastFrame() ?? ''
      expect(frame).toContain('KOSMOS')
    }
  })
})
