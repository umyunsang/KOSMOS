// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T036b — `history-prev` / `history-next` action regression suite.
//
// Closes #1582 / #1583.  FR-017 / FR-018 / FR-019.
//
// Scope:
//   - Empty-buffer `up` loads the prior query; subsequent `up` descends
//     further; `down` returns toward the present.
//   - Non-empty buffer `up`/`down` pass through (draft is never overwritten).
//   - memdir USER consent gating: without consent, only current-session
//     entries are traversed; with consent, cross-session entries become
//     reachable and an assertive a11y announcement fires on the crossing
//     (FR-019 scope-boundary visibility).
//   - Graceful degradation when the memdir USER tier is absent — the
//     controller MUST behave correctly with an empty cross-session list
//     instead of throwing.

import { describe, expect, it } from 'bun:test'
import {
  createHistoryNavigator,
  type HistoryNavigatorDeps,
  type HistoryNavigationEntry,
} from '../../src/keybindings/actions/historyNavigate'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Test doubles
// ---------------------------------------------------------------------------

type AnnouncementRecord = Readonly<{
  message: string
  priority: AnnouncementPriority
  at: number
}>

function makeAnnouncer(): {
  announcer: AccessibilityAnnouncer
  records: AnnouncementRecord[]
} {
  const records: AnnouncementRecord[] = []
  return {
    announcer: {
      announce(message, options) {
        records.push({
          message,
          priority: options?.priority ?? 'polite',
          at: Date.now(),
        })
      },
    },
    records,
  }
}

const CURRENT_SESSION = '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60'
const PRIOR_SESSION = '01956a00-aaaa-7a1e-9c8b-0b2c3d4e5f60'

// Current-session + prior-session entries ordered oldest → newest.
const CROSS_SESSION_HISTORY: ReadonlyArray<HistoryNavigationEntry> = [
  { query_text: '작년 날씨', timestamp: '2026-04-18T09:00:00Z', session_id: PRIOR_SESSION, consent_scope: 'cross-session' },
  { query_text: '부산 응급실', timestamp: '2026-04-19T10:00:00Z', session_id: PRIOR_SESSION, consent_scope: 'cross-session' },
  { query_text: '오늘 날씨', timestamp: '2026-04-20T08:00:00Z', session_id: CURRENT_SESSION, consent_scope: 'current-session' },
  { query_text: '내일 비 와?', timestamp: '2026-04-20T08:01:00Z', session_id: CURRENT_SESSION, consent_scope: 'current-session' },
]

const CURRENT_ONLY_HISTORY: ReadonlyArray<HistoryNavigationEntry> = [
  { query_text: '오늘 날씨', timestamp: '2026-04-20T08:00:00Z', session_id: CURRENT_SESSION, consent_scope: 'current-session' },
  { query_text: '내일 비 와?', timestamp: '2026-04-20T08:01:00Z', session_id: CURRENT_SESSION, consent_scope: 'current-session' },
]

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

type Fixture = {
  nav: ReturnType<typeof createHistoryNavigator>
  draft: () => string
  setDraft: (value: string) => void
  records: AnnouncementRecord[]
}

function makeFixture(options: {
  history?: ReadonlyArray<HistoryNavigationEntry>
  consentGranted?: boolean
  initialDraft?: string
  memdirAbsent?: boolean
} = {}): Fixture {
  const history = options.history ?? CURRENT_ONLY_HISTORY
  const consentGranted = options.consentGranted ?? false
  let draft = options.initialDraft ?? ''
  const { announcer, records } = makeAnnouncer()
  const deps: HistoryNavigatorDeps = {
    readDraft: () => draft,
    setDraft: (value: string) => {
      draft = value
    },
    getHistory: () => history,
    consentState: { memdir_user_granted: consentGranted },
    memdirAvailable: !(options.memdirAbsent ?? false),
    currentSessionId: CURRENT_SESSION,
    announcer,
  }
  return {
    nav: createHistoryNavigator(deps),
    draft: () => draft,
    setDraft: (v) => {
      draft = v
    },
    records,
  }
}

// ---------------------------------------------------------------------------
// FR-017 — prev on empty buffer loads the most-recent query
// ---------------------------------------------------------------------------

describe('FR-017 history-prev on empty buffer', () => {
  it('loads the most-recent query into the draft', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    const outcome = f.nav.prev()
    expect(outcome.kind).toBe('loaded')
    expect(f.draft()).toBe('내일 비 와?')
    expect(f.records.length).toBe(1)
    expect(f.records[0]?.priority).toBe('polite')
  })

  it('walks backward through the history with repeated prev', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    f.nav.prev()
    f.nav.prev()
    expect(f.draft()).toBe('오늘 날씨')
  })

  it('is a no-op when the history is empty', () => {
    const f = makeFixture({ history: [] })
    const outcome = f.nav.prev()
    expect(outcome.kind).toBe('empty')
    expect(f.draft()).toBe('')
    expect(f.records.length).toBe(0)
  })

  it('passes through on a non-empty buffer (draft not overwritten)', () => {
    const f = makeFixture({
      history: CURRENT_ONLY_HISTORY,
      initialDraft: 'user typed',
    })
    const outcome = f.nav.prev()
    expect(outcome.kind).toBe('pass-through')
    expect(f.draft()).toBe('user typed')
    expect(f.records.length).toBe(0)
  })

  it('holds at the oldest entry rather than overshooting', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    f.nav.prev() // newest
    f.nav.prev() // oldest
    const held = f.nav.prev() // no further history
    expect(held.kind).toBe('at-bound')
    expect(f.draft()).toBe('오늘 날씨')
  })
})

// ---------------------------------------------------------------------------
// FR-018 — next on empty buffer returns toward the present
// ---------------------------------------------------------------------------

describe('FR-018 history-next on empty buffer', () => {
  it('loads the next (newer) entry after stepping back', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    f.nav.prev()
    f.nav.prev()
    expect(f.draft()).toBe('오늘 날씨')
    const out = f.nav.next()
    expect(out.kind).toBe('loaded')
    expect(f.draft()).toBe('내일 비 와?')
  })

  it('returns to an empty draft when stepping past the newest entry', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    f.nav.prev() // newest loaded
    const out = f.nav.next()
    expect(out.kind).toBe('returned-to-present')
    expect(f.draft()).toBe('')
  })

  it('is a no-op when there is no history state to return from', () => {
    const f = makeFixture({ history: CURRENT_ONLY_HISTORY })
    const out = f.nav.next()
    expect(out.kind).toBe('at-present')
    expect(f.draft()).toBe('')
  })

  it('passes through on a non-empty buffer (FR-018)', () => {
    const f = makeFixture({
      history: CURRENT_ONLY_HISTORY,
      initialDraft: 'typed',
    })
    const out = f.nav.next()
    expect(out.kind).toBe('pass-through')
    expect(f.draft()).toBe('typed')
  })
})

// ---------------------------------------------------------------------------
// FR-019 — memdir USER consent-scope visible boundary
// ---------------------------------------------------------------------------

describe('FR-019 consent-scope boundary', () => {
  it('without consent — only current-session entries are reachable', () => {
    const f = makeFixture({
      history: CROSS_SESSION_HISTORY,
      consentGranted: false,
    })
    f.nav.prev() // newest current-session
    expect(f.draft()).toBe('내일 비 와?')
    f.nav.prev() // oldest current-session
    expect(f.draft()).toBe('오늘 날씨')
    // Pressing prev again at the current-session boundary without consent
    // MUST stay put — cross-session entries are out of scope.
    const out = f.nav.prev()
    expect(out.kind).toBe('at-scope-boundary')
    expect(f.draft()).toBe('오늘 날씨')
    // Assertive announcement — tells the citizen why the boundary held.
    const last = f.records[f.records.length - 1]
    if (last === undefined) throw new Error('no announcement')
    expect(last.priority).toBe('assertive')
    expect(last.message).toContain('메모리 동의')
  })

  it('with consent — cross-session entries are reachable with an assertive crossing notice', () => {
    const f = makeFixture({
      history: CROSS_SESSION_HISTORY,
      consentGranted: true,
    })
    f.nav.prev() // 내일 비 와?
    f.nav.prev() // 오늘 날씨
    expect(f.records.every((r) => r.priority === 'polite')).toBe(true)
    const crossing = f.nav.prev() // crosses into prior session
    expect(crossing.kind).toBe('crossed-scope')
    expect(f.draft()).toBe('부산 응급실')
    // The crossing MUST be announced assertively per FR-019.
    const lastRec = f.records[f.records.length - 1]
    if (lastRec === undefined) throw new Error('no crossing announcement')
    expect(lastRec.priority).toBe('assertive')
    expect(lastRec.message).toContain('이전 세션')
  })
})

// ---------------------------------------------------------------------------
// Graceful degradation — memdir USER tier absent
// ---------------------------------------------------------------------------

describe('graceful degradation without memdir USER tier', () => {
  it('still traverses current-session history even when memdirAvailable is false', () => {
    const f = makeFixture({
      history: CURRENT_ONLY_HISTORY,
      consentGranted: false,
      memdirAbsent: true,
    })
    f.nav.prev()
    expect(f.draft()).toBe('내일 비 와?')
  })

  it('treats cross-session entries as out-of-scope when memdir is absent, regardless of consent state', () => {
    const f = makeFixture({
      history: CROSS_SESSION_HISTORY,
      consentGranted: true, // nominally granted, but memdir missing
      memdirAbsent: true,
    })
    f.nav.prev()
    f.nav.prev()
    const boundary = f.nav.prev()
    expect(boundary.kind).toBe('at-scope-boundary')
    // Assertive notice that memdir is unavailable — parallels the
    // consent-declined surface per FR-019.
    const lastRec = f.records[f.records.length - 1]
    if (lastRec === undefined) throw new Error('no announcement')
    expect(lastRec.priority).toBe('assertive')
  })
})
