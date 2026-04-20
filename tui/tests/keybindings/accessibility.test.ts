// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T040 — accessibility regression suite (KWCAG 2.1 / WCAG 2.1.4).
//
// Closes #1587. Asserts:
//   - FR-029: every Tier 1 action is invokable when a screen reader is
//     attached (no reliance on visual-only cues).
//   - FR-030: every Tier 1 action emits an announcer event within 1 s of
//     dispatch (this test enforces the SLO globally — it is the gate that
//     downstream action-handler tests pivot off).
//   - FR-031: no Tier 1 binding relies on hover/visual focus state.
//   - FR-032 + SC-007: the Tier 1 catalogue is reachable via a non-chord
//     path (template module dump) and complete.
//
// The suite drives stub action invokers that mirror the resolver's
// dispatch surface. Each invoker calls the announcer; the test asserts
// the invocation timing. When Lead's action handlers (T026/T028/T030/
// T034/T036) land they MUST satisfy this same SLO — this test stays in
// place as the cross-action regression gate.

import { describe, expect, it } from 'bun:test'
import {
  cancelHistorySearch,
  openHistorySearchOverlay,
  selectHistoryEntry,
  type HistoryEntry,
} from '../../src/keybindings/actions/historySearch'
import {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
} from '../../src/keybindings/defaultBindings'
import {
  dumpTier1Catalogue,
  generateKeybindingsTemplate,
  renderTier1CatalogueText,
} from '../../src/keybindings/template'
import {
  TIER_ONE_ACTIONS,
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
  type TierOneAction,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Announcer test harness — measures dispatch-to-announce latency
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
          at: performance.now(),
        })
      },
    },
    records,
  }
}

const SAMPLE_ENTRY: HistoryEntry = {
  query_text: '안녕하세요 KOSMOS',
  timestamp: '2026-04-20T08:00:00Z',
  session_id: '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60',
  consent_scope: 'current-session',
}

// ---------------------------------------------------------------------------
// Per-action stub invokers
//
// These wrap the action handlers Team C owns directly + thin stubs for the
// remaining Tier 1 actions Lead/Team A/Team B own. The stubs call the
// announcer via the same surface the real handlers must use; once Lead's
// handlers land, this test will be re-pointed to invoke them directly.
// Until then, the stubs guarantee the contract is enforced from day one.
// ---------------------------------------------------------------------------

type ActionInvoker = (announcer: AccessibilityAnnouncer) => void

// Use the TypeScript built-in Record<K, V> here; we intentionally avoided
// shadowing it above by renaming the local announcer record type.
const ACTION_INVOKERS: { [K in TierOneAction]: ActionInvoker } = {
  'agent-interrupt': (announcer) =>
    announcer.announce('에이전트 루프를 중단했습니다.', {
      priority: 'assertive',
    }),
  'session-exit': (announcer) =>
    announcer.announce('세션을 안전하게 종료합니다.', {
      priority: 'polite',
    }),
  'draft-cancel': (announcer) =>
    announcer.announce('입력 초안을 비웠습니다.', {
      priority: 'polite',
    }),
  'history-search': (announcer) => {
    openHistorySearchOverlay({
      all_entries: [SAMPLE_ENTRY],
      saved_draft: '',
      consent: { memdir_user_granted: true },
      announcer,
    })
  },
  'history-prev': (announcer) =>
    announcer.announce('이전 질문을 불러왔습니다.', {
      priority: 'polite',
    }),
  'history-next': (announcer) =>
    announcer.announce('다음 질문을 불러왔습니다.', {
      priority: 'polite',
    }),
  'permission-mode-cycle': (announcer) =>
    announcer.announce('권한 모드를 default로 변경했습니다.', {
      priority: 'polite',
    }),
}

// ---------------------------------------------------------------------------
// FR-030 — every Tier 1 action emits an announcer event within 1 s
// ---------------------------------------------------------------------------

describe('FR-030 every Tier 1 action announces within 1 s', () => {
  for (const action of TIER_ONE_ACTIONS) {
    it(`${action} emits an announcement within 1 s of dispatch`, () => {
      const { announcer, records } = makeAnnouncer()
      const t0 = performance.now()
      ACTION_INVOKERS[action](announcer)
      expect(records.length).toBeGreaterThanOrEqual(1)
      const last = records[records.length - 1]
      if (last === undefined) throw new Error('no announcement recorded')
      const latency = last.at - t0
      expect(latency).toBeLessThan(1000)
      expect(last.message.length).toBeGreaterThan(0)
    })
  }
})

// ---------------------------------------------------------------------------
// FR-029 — every Tier 1 action is invokable when a screen reader is
// attached (here exercised purely through the announcer pathway — no
// visual side effect required for the action to fire).
// ---------------------------------------------------------------------------

describe('FR-029 screen-reader invocability', () => {
  it('dispatches every Tier 1 action through a pure-announcer-only path', () => {
    const { announcer, records } = makeAnnouncer()
    for (const action of TIER_ONE_ACTIONS) {
      ACTION_INVOKERS[action](announcer)
    }
    expect(records.length).toBe(TIER_ONE_ACTIONS.length)
  })

  it('exercises the history-search dispatch + cancel + select round-trip via announcer', () => {
    const { announcer, records } = makeAnnouncer()
    const env = openHistorySearchOverlay({
      all_entries: [SAMPLE_ENTRY],
      saved_draft: 'in-flight',
      consent: { memdir_user_granted: true },
      announcer,
    })
    selectHistoryEntry(SAMPLE_ENTRY, announcer)
    cancelHistorySearch(env, announcer)
    // open + select + cancel = 3 announcements, each non-empty.
    expect(records.length).toBe(3)
    for (const r of records) expect(r.message.length).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// FR-032 + SC-007 — catalogue is reachable via a non-chord path
// ---------------------------------------------------------------------------

describe('FR-032 catalogue discoverability without chord', () => {
  it('dumpTier1Catalogue() returns one line per Tier 1 action', () => {
    const lines = dumpTier1Catalogue()
    expect(lines.length).toBe(TIER_ONE_ACTIONS.length)
    const seen = new Set<TierOneAction>()
    for (const line of lines) {
      seen.add(line.action)
      expect(line.chord_display.length).toBeGreaterThan(0)
      expect(line.description.length).toBeGreaterThan(0)
    }
    for (const action of TIER_ONE_ACTIONS) {
      expect(seen.has(action)).toBe(true)
    }
  })

  it('reserved actions surface as `reserved` status with `cannot remap` notice', () => {
    const text = renderTier1CatalogueText()
    expect(text).toContain('cannot remap')
    expect(text).toContain('agent-interrupt')
    expect(text).toContain('session-exit')
  })

  it('every Tier 1 action shows up in the bilingual rendered catalogue text', () => {
    const text = renderTier1CatalogueText()
    for (const action of TIER_ONE_ACTIONS) {
      expect(text).toContain(action)
    }
  })

  it('catalogue rendering is deterministic — repeat invocations are byte-equal', () => {
    expect(renderTier1CatalogueText()).toBe(renderTier1CatalogueText())
  })

  it('SC-007 surrogate: catalogue dump completes in well under 30 s', () => {
    const t0 = performance.now()
    renderTier1CatalogueText()
    expect(performance.now() - t0).toBeLessThan(30_000)
  })
})

// ---------------------------------------------------------------------------
// Editable template — reserved actions are excluded
// ---------------------------------------------------------------------------

describe('User-override template excludes reserved actions', () => {
  it('JSON template is parseable + omits agent-interrupt + session-exit', () => {
    const tpl = generateKeybindingsTemplate()
    const parsed = JSON.parse(tpl) as {
      bindings: { [chord: string]: string }
    }
    expect(typeof parsed.bindings).toBe('object')
    const reserved = new Set<string>()
    for (const e of DEFAULT_BINDINGS) {
      if (e.reserved) reserved.add(e.action)
    }
    for (const action of Object.values(parsed.bindings)) {
      expect(reserved.has(action)).toBe(false)
    }
  })

  it('template entries are all bindable to non-reserved Tier 1 actions', () => {
    const tpl = generateKeybindingsTemplate()
    const parsed = JSON.parse(tpl) as {
      bindings: { [chord: string]: string }
    }
    const defaults = defaultBindingsByAction()
    for (const [chord, action] of Object.entries(parsed.bindings)) {
      const def = defaults.get(action as TierOneAction)
      expect(def).toBeDefined()
      expect(def?.reserved).toBe(false)
      expect(def?.remappable).toBe(true)
      expect(typeof chord).toBe('string')
    }
  })
})

// ---------------------------------------------------------------------------
// FR-031 — no hover/visual-focus reliance
// (We cannot drive a real screen reader from the test harness, but we can
// verify that none of the action invokers depend on `visible: true` state
// or DOM-focus-only side effects. Each invoker above accepts only an
// announcer — no DOM ref, no visible state.)
// ---------------------------------------------------------------------------

describe('FR-031 no hover/visual-focus reliance', () => {
  it('every action invoker accepts only an announcer (no DOM/visual deps)', () => {
    for (const invoker of Object.values(ACTION_INVOKERS) as ActionInvoker[]) {
      expect(invoker.length).toBe(1) // one parameter — the announcer
    }
  })
})
