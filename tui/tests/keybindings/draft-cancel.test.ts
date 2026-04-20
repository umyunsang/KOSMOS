// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T030/T031 companion — draft-cancel action handler regression
// suite.
//
// The resolver already short-circuits buffer-mutating actions while the IME
// composes (FR-005 / FR-007 — tested in resolver.test.ts).  This suite covers
// the handler-level assertion that catches regressions where a future Tier 2/
// 3 binding, or a consumer that routes to the handler outside the resolver,
// might call `cancelDraft()` mid-composition.  FR-005 demands a no-op in
// that case.
//
// Scope:
//   - Empty-IME state + non-empty draft: draft clears, announcer fires
//     within 1 s.
//   - Empty-IME state + empty draft: no-op, no announcer event, no audit.
//   - Composing IME: no-op regardless of draft state — defensive second
//     gate per FR-007.
//   - FR-030: announcer contract.

import { describe, expect, it } from 'bun:test'
import {
  cancelDraft,
  type DraftCancelDeps,
} from '../../src/keybindings/actions/draftCancel'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../../src/keybindings/types'

type AnnouncementRecord = Readonly<{
  message: string
  priority: AnnouncementPriority
  at: number
}>

function makeAnnouncer(now: () => number = () => Date.now()): {
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
          at: now(),
        })
      },
    },
    records,
  }
}

type FixtureHandle = DraftCancelDeps & {
  readonly _records: AnnouncementRecord[]
  readonly _clears: () => number
  readonly _buffer: () => string
}

function makeDeps(
  overrides: {
    readDraft?: () => string
    isComposing?: () => boolean
  } = {},
): FixtureHandle {
  let buffer = overrides.readDraft?.() ?? ''
  const composingGetter = overrides.isComposing ?? (() => false)
  let clears = 0
  const { announcer, records } = makeAnnouncer()
  return {
    readDraft: () => buffer,
    isComposing: () => composingGetter(),
    clearDraft: () => {
      clears += 1
      buffer = ''
    },
    announcer,
    _records: records,
    _clears: () => clears,
    _buffer: () => buffer,
  }
}

describe('cancelDraft — FR-005 IME gate (handler-level backstop)', () => {
  it('no-ops while the IME is composing, even with draft text present', () => {
    const deps = makeDeps({
      readDraft: () => '안녕하세요',
      isComposing: () => true,
    })
    const outcome = cancelDraft(deps)
    expect(outcome.kind).toBe('ignored-composing')
    expect(deps._clears()).toBe(0)
    expect(deps._records.length).toBe(0)
  })

  it('no-ops on empty draft (no audit, no announcement)', () => {
    const deps = makeDeps({ readDraft: () => '', isComposing: () => false })
    const outcome = cancelDraft(deps)
    expect(outcome.kind).toBe('ignored-empty')
    expect(deps._clears()).toBe(0)
    expect(deps._records.length).toBe(0)
  })

  it('clears a non-empty buffer when the IME is idle', () => {
    const deps = makeDeps({
      readDraft: () => '부산 응급실 알려줘',
      isComposing: () => false,
    })
    const outcome = cancelDraft(deps)
    expect(outcome.kind).toBe('cleared')
    expect(deps._clears()).toBe(1)
    expect(deps._buffer()).toBe('')
  })
})

describe('cancelDraft — FR-030 announcement within 1 s', () => {
  it('emits a polite announcement on clear', () => {
    const t0 = Date.now()
    const { announcer, records } = makeAnnouncer(() => Date.now())
    cancelDraft({
      readDraft: () => 'typed',
      isComposing: () => false,
      clearDraft: () => undefined,
      announcer,
    })
    expect(records.length).toBe(1)
    const rec = records[0]
    if (rec === undefined) throw new Error('no announcement')
    expect(rec.at - t0).toBeLessThan(1000)
    expect(rec.priority).toBe('polite')
    expect(rec.message.length).toBeGreaterThan(0)
  })

  it('does NOT announce on ignored-empty or ignored-composing outcomes', () => {
    const idle = makeDeps({ readDraft: () => '', isComposing: () => false })
    cancelDraft(idle)
    expect(idle._records.length).toBe(0)

    const composing = makeDeps({
      readDraft: () => 'partial',
      isComposing: () => true,
    })
    cancelDraft(composing)
    expect(composing._records.length).toBe(0)
  })
})
