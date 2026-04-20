// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T038 — `history-search` action + overlay regression suite.
//
// Closes #1585. Asserts:
//   - FR-020: overlay open envelope built ≤ 300 ms.
//   - FR-021: consent-scope filter excludes cross-session entries when
//     memdir USER tier consent is absent; surfaces them when granted.
//   - FR-022: escape restores the saved draft byte-for-byte.
//   - 초성 + diacritic-insensitive substring matching (research D9 +
//     T037 constraint).
//   - FR-030: announcer fires within 1 s of dispatch.

import { describe, expect, it } from 'bun:test'
import {
  cancelHistorySearch,
  filterByConsentScope,
  openHistorySearchOverlay,
  selectHistoryEntry,
  type ConsentState,
  type HistoryEntry,
} from '../../src/keybindings/actions/historySearch'
import {
  filterHistoryEntries,
  matchesHistoryQuery,
  toChoseongString,
} from '../../src/keybindings/hangulSearch'
import { type AccessibilityAnnouncer } from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Test doubles
// ---------------------------------------------------------------------------

type AnnouncementRecord = Readonly<{
  message: string
  priority: 'polite' | 'assertive'
  at: number
}>

function makeRecordingAnnouncer(): {
  announcer: AccessibilityAnnouncer
  records: AnnouncementRecord[]
} {
  const records: AnnouncementRecord[] = []
  const announcer: AccessibilityAnnouncer = {
    announce(message, options) {
      records.push({
        message,
        priority: options?.priority ?? 'polite',
        at: Date.now(),
      })
    },
  }
  return { announcer, records }
}

const CURRENT_SESSION = '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60'
const PRIOR_SESSION = '01956a00-aaaa-7a1e-9c8b-0b2c3d4e5f60'

const SAMPLE_HISTORY: ReadonlyArray<HistoryEntry> = [
  {
    query_text: '날씨 알려줘',
    timestamp: '2026-04-20T08:00:00Z',
    session_id: CURRENT_SESSION,
    consent_scope: 'current-session',
  },
  {
    query_text: '내일 비 와?',
    timestamp: '2026-04-20T08:01:00Z',
    session_id: CURRENT_SESSION,
    consent_scope: 'current-session',
  },
  {
    query_text: '부산 응급실 알려줘',
    timestamp: '2026-04-19T23:30:00Z',
    session_id: PRIOR_SESSION,
    consent_scope: 'cross-session',
  },
  {
    query_text: 'Café 위치',
    timestamp: '2026-04-19T22:00:00Z',
    session_id: PRIOR_SESSION,
    consent_scope: 'cross-session',
  },
]

const CONSENT_GRANTED: ConsentState = { memdir_user_granted: true }
const CONSENT_DECLINED: ConsentState = { memdir_user_granted: false }

// ---------------------------------------------------------------------------
// FR-021 — consent scope
// ---------------------------------------------------------------------------

describe('FR-021 consent-scope filtering', () => {
  it('returns every entry when memdir USER consent is granted', () => {
    const out = filterByConsentScope(SAMPLE_HISTORY, CONSENT_GRANTED)
    expect(out.length).toBe(SAMPLE_HISTORY.length)
  })

  it('excludes cross-session entries when consent is declined', () => {
    const out = filterByConsentScope(SAMPLE_HISTORY, CONSENT_DECLINED)
    expect(out.every((e) => e.consent_scope === 'current-session')).toBe(true)
    expect(out.length).toBe(2)
  })
})

// ---------------------------------------------------------------------------
// 초성 + diacritic + substring matching
// ---------------------------------------------------------------------------

describe('hangulSearch matcher', () => {
  it('decomposes Hangul syllables into 초성 sequence', () => {
    expect(toChoseongString('부산')).toBe('ㅂㅅ')
    expect(toChoseongString('날씨')).toBe('ㄴㅆ')
    expect(toChoseongString('응급실')).toBe('ㅇㄱㅅ')
  })

  it('matches Korean substring in haystack', () => {
    expect(matchesHistoryQuery('부산 응급실 알려줘', '부산')).toBe(true)
    expect(matchesHistoryQuery('부산 응급실 알려줘', '응급')).toBe(true)
    expect(matchesHistoryQuery('부산 응급실 알려줘', '서울')).toBe(false)
  })

  it('matches 초성-only needle against Hangul haystack', () => {
    expect(matchesHistoryQuery('부산 응급실 알려줘', 'ㅂㅅ')).toBe(true)
    expect(matchesHistoryQuery('내일 비 와?', 'ㄴㅇ')).toBe(true)
    expect(matchesHistoryQuery('내일 비 와?', 'ㄴㅁ')).toBe(false)
  })

  it('strips diacritics from Latin-script haystack', () => {
    // 'Café' (U+00E9 é) NFD decomposes to e + U+0301 — needle 'cafe' matches.
    expect(matchesHistoryQuery('Café 위치', 'cafe')).toBe(true)
  })

  it('returns true on empty needle (open-overlay default)', () => {
    expect(matchesHistoryQuery('anything', '')).toBe(true)
  })

  it('filters list while preserving order', () => {
    const filtered = filterHistoryEntries(SAMPLE_HISTORY, 'ㅂㅅ')
    expect(filtered.length).toBe(1)
    expect(filtered[0]?.query_text).toBe('부산 응급실 알려줘')
  })
})

// ---------------------------------------------------------------------------
// FR-020 — overlay open ≤ 300 ms (envelope build is the gating step)
// ---------------------------------------------------------------------------

describe('FR-020 overlay open SLO', () => {
  it('builds the open envelope in well under 300 ms even with 200 entries', () => {
    const big: HistoryEntry[] = []
    for (let i = 0; i < 200; i += 1) {
      big.push({
        query_text: `질문 ${i} 응급실 부산 ${i}`,
        timestamp: new Date(2026, 3, 20, 0, 0, i).toISOString(),
        session_id: i % 2 === 0 ? CURRENT_SESSION : PRIOR_SESSION,
        consent_scope: i % 2 === 0 ? 'current-session' : 'cross-session',
      })
    }
    const { announcer } = makeRecordingAnnouncer()
    const t0 = performance.now()
    const envelope = openHistorySearchOverlay({
      all_entries: big,
      saved_draft: '',
      consent: CONSENT_GRANTED,
      announcer,
    })
    const elapsed = performance.now() - t0
    expect(elapsed).toBeLessThan(300)
    expect(envelope.visible_entries.length).toBe(200)
  })
})

// ---------------------------------------------------------------------------
// FR-022 — escape byte-for-byte draft restore
// ---------------------------------------------------------------------------

describe('FR-022 escape draft restore', () => {
  it('restores the saved draft verbatim on cancel — multi-byte chars intact', () => {
    const { announcer } = makeRecordingAnnouncer()
    // Mixed Korean + emoji + combining mark to catch any naive .length /
    // codeunit truncation.
    const draft = '오늘 날씨 어때?  ☀️ 🌧️  Café'
    const envelope = openHistorySearchOverlay({
      all_entries: SAMPLE_HISTORY,
      saved_draft: draft,
      consent: CONSENT_DECLINED,
      announcer,
    })
    const result = cancelHistorySearch(envelope, announcer)
    expect(result.kind).toBe('cancelled')
    expect(result.next_draft).toBe(draft)
    // Byte-for-byte: identical UTF-8 byte sequence.
    const enc = new TextEncoder()
    expect(Array.from(enc.encode(result.next_draft))).toEqual(
      Array.from(enc.encode(draft)),
    )
  })

  it('restores the empty draft when the citizen had typed nothing', () => {
    const { announcer } = makeRecordingAnnouncer()
    const envelope = openHistorySearchOverlay({
      all_entries: SAMPLE_HISTORY,
      saved_draft: '',
      consent: CONSENT_GRANTED,
      announcer,
    })
    const result = cancelHistorySearch(envelope, announcer)
    expect(result.next_draft).toBe('')
  })
})

// ---------------------------------------------------------------------------
// FR-030 — announcer fires within 1 s
// ---------------------------------------------------------------------------

describe('FR-030 accessibility announcer', () => {
  it('fires an announcement within 1 s of opening the overlay', () => {
    const { announcer, records } = makeRecordingAnnouncer()
    const t0 = Date.now()
    openHistorySearchOverlay({
      all_entries: SAMPLE_HISTORY,
      saved_draft: '',
      consent: CONSENT_GRANTED,
      announcer,
      now: () => t0,
    })
    expect(records.length).toBe(1)
    const first = records[0]
    if (first === undefined) throw new Error('no announcement recorded')
    expect(first.at).toBeGreaterThanOrEqual(t0)
    expect(first.at - t0).toBeLessThan(1000)
    expect(first.priority).toBe('polite')
  })

  it('escalates the priority to assertive when consent gating reduces scope', () => {
    const { announcer, records } = makeRecordingAnnouncer()
    openHistorySearchOverlay({
      all_entries: SAMPLE_HISTORY,
      saved_draft: '',
      consent: CONSENT_DECLINED,
      announcer,
    })
    expect(records[0]?.priority).toBe('assertive')
    expect(records[0]?.message).toContain('이전 세션')
  })

  it('announces the loaded entry on selection', () => {
    const { announcer, records } = makeRecordingAnnouncer()
    const entry = SAMPLE_HISTORY[0]
    if (entry === undefined) throw new Error('fixture missing')
    const result = selectHistoryEntry(entry, announcer)
    expect(result.kind).toBe('selected')
    expect(result.next_draft).toBe(entry.query_text)
    expect(records[0]?.message).toContain(entry.query_text)
  })
})

// ---------------------------------------------------------------------------
// FR-029 — every Tier 1 action invokable under screen reader
// (Selection + cancel each emit announcements; openHistorySearchOverlay
// covered above. Together with the registry catalogue dump (T040), this
// closes the discoverability loop without any visual cue.)
// ---------------------------------------------------------------------------

describe('FR-029 screen-reader invocability', () => {
  it('emits announcer events for open + select + cancel without visual side effects', () => {
    const { announcer, records } = makeRecordingAnnouncer()
    const envelope = openHistorySearchOverlay({
      all_entries: SAMPLE_HISTORY,
      saved_draft: 'in-flight draft',
      consent: CONSENT_GRANTED,
      announcer,
    })
    const entry = envelope.visible_entries[0]
    if (entry === undefined) throw new Error('fixture missing')
    selectHistoryEntry(entry, announcer)
    cancelHistorySearch(envelope, announcer)
    expect(records.length).toBe(3) // open + select + cancel
  })
})
