// SPDX-License-Identifier: Apache-2.0
// T040 — Feed family tests (Epic H #1302).
// Covers:
//   - Feed.snap.test: two-column composition with mock sessionHistory + ministryStatus
//   - FeedColumn.snap.test: primitive PORT render
//   - feedConfigs.test: factory output shape

import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import {
  Feed,
  KosmosOnboardingFeed,
  calculateFeedWidth,
} from '../../src/components/onboarding/LogoV2/Feed'
import { FeedColumn } from '../../src/components/onboarding/LogoV2/FeedColumn'
import {
  createKosmosSessionHistoryFeed,
  createMinistryAvailabilityFeed,
  type KosmosSession,
  type MinistryStatus,
} from '../../src/components/onboarding/LogoV2/feedConfigs'
import { ThemeProvider } from '../../src/theme/provider'

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
// feedConfigs — factory shape tests
// ---------------------------------------------------------------------------

describe('createKosmosSessionHistoryFeed', () => {
  it('produces "최근 세션" title and 1 row per session', () => {
    const config = createKosmosSessionHistoryFeed(FIXTURE_SESSIONS)
    expect(config.title).toBe('최근 세션')
    expect(config.rows).toHaveLength(2)
    expect(config.rows[0]?.kind).toBe('session')
    expect(config.rows[0]?.primary).toBe('교통 사고 다발 구간')
  })

  it('caps at 5 rows', () => {
    const many: KosmosSession[] = Array.from({ length: 8 }).map((_, i) => ({
      sessionId: `018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f6${i}`,
      queryLabel: `q${i}`,
      timestampIso: '2026-04-20T14:32:05Z',
    }))
    const config = createKosmosSessionHistoryFeed(many)
    expect(config.rows.length).toBeLessThanOrEqual(5)
  })
})

describe('createMinistryAvailabilityFeed', () => {
  it('produces "부처 상태" title and 1 row per ministry with dot indicators', () => {
    const config = createMinistryAvailabilityFeed(FIXTURE_MINISTRIES)
    expect(config.title).toBe('부처 상태')
    expect(config.rows).toHaveLength(4)
    const available = config.rows.filter((r) => r.secondary === '●')
    const unavailable = config.rows.filter((r) => r.secondary === '○')
    expect(available).toHaveLength(3)
    expect(unavailable).toHaveLength(1)
  })

  it('accentFor resolves ministry token names for each row', () => {
    const config = createMinistryAvailabilityFeed(FIXTURE_MINISTRIES)
    expect(config.accentFor).toBeDefined()
    if (config.accentFor === undefined) throw new Error('accentFor missing')
    expect(config.accentFor(config.rows[0]!)).toBe('agentSatelliteKoroad')
    expect(config.accentFor(config.rows[1]!)).toBe('agentSatelliteKma')
    expect(config.accentFor(config.rows[2]!)).toBe('agentSatelliteHira')
    expect(config.accentFor(config.rows[3]!)).toBe('agentSatelliteNmc')
  })
})

// ---------------------------------------------------------------------------
// Feed primitive — snapshot
// ---------------------------------------------------------------------------

describe('Feed primitive', () => {
  it('renders title + rows for a session feed', () => {
    const config = createKosmosSessionHistoryFeed(FIXTURE_SESSIONS)
    const { lastFrame } = render(
      <ThemeProvider>
        <Feed config={config} actualWidth={40} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('최근 세션')
    expect(frame).toContain('교통 사고 다발 구간')
    expect(frame).toMatchSnapshot()
  })
})

describe('calculateFeedWidth', () => {
  it('returns at least the title length', () => {
    const config = createKosmosSessionHistoryFeed(FIXTURE_SESSIONS)
    const width = calculateFeedWidth(config)
    expect(width).toBeGreaterThanOrEqual(config.title.length)
  })
})

// ---------------------------------------------------------------------------
// FeedColumn primitive — snapshot
// ---------------------------------------------------------------------------

describe('FeedColumn primitive (PORT)', () => {
  it('stacks a single feed configuration', () => {
    const config = createMinistryAvailabilityFeed(FIXTURE_MINISTRIES)
    const { lastFrame } = render(
      <ThemeProvider>
        <FeedColumn feeds={[config]} maxWidth={40} />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('부처 상태')
    expect(frame).toMatchSnapshot()
  })
})

// ---------------------------------------------------------------------------
// KOSMOS two-column composition
// ---------------------------------------------------------------------------

describe('KosmosOnboardingFeed', () => {
  it('renders two columns side-by-side', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <KosmosOnboardingFeed
          sessionHistory={FIXTURE_SESSIONS}
          ministryStatus={FIXTURE_MINISTRIES}
        />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('최근 세션')
    expect(frame).toContain('부처 상태')
    expect(frame).toMatchSnapshot()
  })
})
