// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T035 — `permission-mode-cycle` (shift+tab) regression suite.
//
// Closes #1583 (US4 regression). Asserts:
//   - FR-008: shift+tab cycles plan → default → acceptEdits →
//     bypassPermissions → plan (wrap) when no irreversible action is
//     pending.
//   - FR-009: cycling into bypassPermissions is blocked whenever the
//     session carries an outstanding irreversible-action flag. On
//     block, the mode holds at the previous step and the handler
//     surfaces a citizen-readable notice.
//   - FR-010: indicator-update pathway fires within 200 ms of the
//     shift+tab dispatch.
//   - FR-011: ModeCycle.tsx (Spec 033) remains the sole authority on
//     permitted transitions — the handler is a thin adapter.
//   - FR-030: announcer fires within 1 s of dispatch on success.
//   - SC-005: the block fires on 100% of test-suite attempts that
//     inject the irreversible-action flag.

import { describe, expect, it, mock } from 'bun:test'
import {
  buildPermissionModeCycleHandler,
  computeTier1NextMode,
  type PermissionModeCycleDeps,
} from '../../src/keybindings/actions/permissionModeCycle'
import type { PermissionMode } from '../../src/permissions/types'
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
        at: performance.now(),
      })
    },
  }
  return { announcer, records }
}

function makeDeps(
  overrides: Partial<PermissionModeCycleDeps> = {},
): {
  deps: PermissionModeCycleDeps
  announcer: AccessibilityAnnouncer
  announcements: AnnouncementRecord[]
  modeLog: PermissionMode[]
} {
  const { announcer, records } = makeRecordingAnnouncer()
  const modeLog: PermissionMode[] = []
  let currentMode: PermissionMode = 'plan'
  const deps: PermissionModeCycleDeps = {
    getMode: () => currentMode,
    setMode: (m) => {
      currentMode = m
      modeLog.push(m)
    },
    hasPendingIrreversibleAction: () => false,
    getSessionId: () => 'test-session-id',
    announcer,
    ...overrides,
  }
  return { deps, announcer, announcements: records, modeLog }
}

// ---------------------------------------------------------------------------
// FR-008 — Tier 1 cycle ordering: plan → default → acceptEdits →
//           bypassPermissions → plan (wrap)
// ---------------------------------------------------------------------------

describe('FR-008 Tier 1 cycle ordering', () => {
  it('computeTier1NextMode(plan) === default', () => {
    expect(computeTier1NextMode('plan')).toBe('default')
  })

  it('computeTier1NextMode(default) === acceptEdits', () => {
    expect(computeTier1NextMode('default')).toBe('acceptEdits')
  })

  it('computeTier1NextMode(acceptEdits) === bypassPermissions', () => {
    expect(computeTier1NextMode('acceptEdits')).toBe('bypassPermissions')
  })

  it('computeTier1NextMode(bypassPermissions) === plan (wrap)', () => {
    expect(computeTier1NextMode('bypassPermissions')).toBe('plan')
  })

  it('computeTier1NextMode(dontAsk) returns to plan (escape hatch)', () => {
    // dontAsk is NOT in the Tier 1 cycle but is reachable via
    // /permissions dontAsk. Shift+Tab from dontAsk returns to the
    // front of the cycle per Spec 033 S1 escape-hatch spirit.
    expect(computeTier1NextMode('dontAsk')).toBe('plan')
  })

  it('completes a full 4-step cycle and returns to the origin', () => {
    let m: PermissionMode = 'plan'
    m = computeTier1NextMode(m)
    expect(m).toBe('default')
    m = computeTier1NextMode(m)
    expect(m).toBe('acceptEdits')
    m = computeTier1NextMode(m)
    expect(m).toBe('bypassPermissions')
    m = computeTier1NextMode(m)
    expect(m).toBe('plan')
  })
})

// ---------------------------------------------------------------------------
// End-to-end handler: wraps the cycle across the 4 steps.
// ---------------------------------------------------------------------------

describe('permission-mode-cycle handler — wrap order', () => {
  it('cycles plan → default → acceptEdits → bypassPermissions → plan', async () => {
    const { deps, modeLog } = makeDeps()
    const handler = buildPermissionModeCycleHandler(deps)
    await handler() // plan → default
    await handler() // default → acceptEdits
    await handler() // acceptEdits → bypassPermissions
    await handler() // bypassPermissions → plan (wrap)
    expect(modeLog).toEqual([
      'default',
      'acceptEdits',
      'bypassPermissions',
      'plan',
    ])
  })
})

// ---------------------------------------------------------------------------
// FR-009 / SC-005 — irreversible-action flag blocks bypassPermissions
// ---------------------------------------------------------------------------

describe('FR-009 / SC-005 irreversible-action block', () => {
  it('blocks when the next computed mode is bypassPermissions and the flag is set', async () => {
    const { deps, modeLog, announcements } = makeDeps({
      getMode: () => 'acceptEdits', // next step is bypassPermissions
      hasPendingIrreversibleAction: () => true,
    })
    const handler = buildPermissionModeCycleHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('blocked')
    if (result.kind !== 'blocked') throw new Error('unreachable')
    expect(result.reason).toBe('permission-mode-blocked')
    // setMode was never invoked — the mode holds at the previous step.
    expect(modeLog).toEqual([])
    // A citizen-readable notice explains why (FR-009).
    const notice = announcements.find((r) =>
      r.message.includes('되돌릴 수 없는'),
    )
    expect(notice).toBeDefined()
    expect(notice?.priority).toBe('assertive')
  })

  it('does NOT block non-bypass transitions even when the flag is set', async () => {
    // plan → default is a benign transition; the irreversible flag
    // only matters when the candidate mode is bypassPermissions.
    const { deps, modeLog } = makeDeps({
      getMode: () => 'plan',
      hasPendingIrreversibleAction: () => true,
    })
    const handler = buildPermissionModeCycleHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('cycled')
    expect(modeLog).toEqual(['default'])
  })

  it('allows bypassPermissions when the flag is cleared (T035 round-trip)', async () => {
    let flag = true
    const { deps, modeLog } = makeDeps({
      getMode: () => 'acceptEdits',
      hasPendingIrreversibleAction: () => flag,
    })
    const handler = buildPermissionModeCycleHandler(deps)
    // First press — blocked.
    expect((await handler()).kind).toBe('blocked')
    expect(modeLog).toEqual([])
    // Flag cleared — second press dispatches.
    flag = false
    expect((await handler()).kind).toBe('cycled')
    expect(modeLog).toEqual(['bypassPermissions'])
  })

  it('SC-005: 100% block rate over 50 injected flag samples', async () => {
    let blocks = 0
    for (let i = 0; i < 50; i += 1) {
      const { deps } = makeDeps({
        getMode: () => 'acceptEdits',
        hasPendingIrreversibleAction: () => true,
      })
      const handler = buildPermissionModeCycleHandler(deps)
      const result = await handler()
      if (result.kind === 'blocked') blocks += 1
    }
    expect(blocks).toBe(50)
  })
})

// ---------------------------------------------------------------------------
// FR-010 — indicator-update SLO (200 ms)
// ---------------------------------------------------------------------------

describe('FR-010 indicator-update SLO', () => {
  it('setMode is invoked within 200 ms of handler dispatch', async () => {
    let setModeAt = -1
    const { deps } = makeDeps({
      setMode: () => {
        setModeAt = performance.now()
      },
    })
    const handler = buildPermissionModeCycleHandler(deps)
    const t0 = performance.now()
    await handler()
    expect(setModeAt).toBeGreaterThanOrEqual(t0)
    expect(setModeAt - t0).toBeLessThan(200)
  })

  it('the announcer fires within 200 ms (status-indicator parity)', async () => {
    const { deps, announcements } = makeDeps()
    const t0 = performance.now()
    const handler = buildPermissionModeCycleHandler(deps)
    await handler()
    const successMsg = announcements.find((r) => r.message.includes('권한'))
    expect(successMsg).toBeDefined()
    if (successMsg === undefined) throw new Error('unreachable')
    expect(successMsg.at - t0).toBeLessThan(200)
  })
})

// ---------------------------------------------------------------------------
// FR-030 — accessibility announcement on success
// ---------------------------------------------------------------------------

describe('FR-030 success announcement', () => {
  it('announces the new mode within 1 s', async () => {
    const { deps, announcements } = makeDeps()
    const t0 = performance.now()
    const handler = buildPermissionModeCycleHandler(deps)
    await handler()
    expect(announcements.length).toBeGreaterThanOrEqual(1)
    const last = announcements[announcements.length - 1]
    if (last === undefined) throw new Error('no announcement recorded')
    expect(last.at - t0).toBeLessThan(1000)
    expect(last.message.length).toBeGreaterThan(0)
  })

  it('announcement mentions the new mode (citizen-readable)', async () => {
    const { deps, announcements } = makeDeps({
      getMode: () => 'plan', // next step is default
    })
    const handler = buildPermissionModeCycleHandler(deps)
    await handler()
    const msg = announcements[announcements.length - 1]?.message ?? ''
    expect(msg).toContain('default')
  })

  it('announcement is polite when the cycle succeeds', async () => {
    const { deps, announcements } = makeDeps()
    const handler = buildPermissionModeCycleHandler(deps)
    await handler()
    const success = announcements[announcements.length - 1]
    expect(success?.priority).toBe('polite')
  })
})

// ---------------------------------------------------------------------------
// OTel span emission — FR-010 requires `kosmos.permission.mode` attribute
// on the outgoing span. The Spec 033 `emitModeChangedOtel` helper wraps
// the stderr-JSONL bridge (no direct opentelemetry dep per SC-008).
// ---------------------------------------------------------------------------

describe('OTel span emission', () => {
  it('invokes the OTel emitter with from-mode + to-mode + shift_tab trigger', async () => {
    const emitSpan = mock((_args: unknown) => undefined)
    const { deps } = makeDeps({
      getMode: () => 'plan',
      emitSpan,
    })
    const handler = buildPermissionModeCycleHandler(deps)
    await handler()
    expect(emitSpan).toHaveBeenCalledTimes(1)
    const args = emitSpan.mock.calls[0]?.[0] as {
      fromMode: PermissionMode
      toMode: PermissionMode
      trigger: string
      confirmed: boolean
      sessionId: string
    }
    expect(args.fromMode).toBe('plan')
    expect(args.toMode).toBe('default')
    expect(args.trigger).toBe('shift_tab')
    expect(args.confirmed).toBe(true)
    expect(args.sessionId).toBe('test-session-id')
  })

  it('does NOT emit a span on a blocked transition (FR-034: benign block → no dispatch span)', async () => {
    const emitSpan = mock((_args: unknown) => undefined)
    const { deps } = makeDeps({
      getMode: () => 'acceptEdits',
      hasPendingIrreversibleAction: () => true,
      emitSpan,
    })
    const handler = buildPermissionModeCycleHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('blocked')
    // The resolver emits the blocked span (FR-034). The handler only
    // emits the `permission.mode.changed` span on successful dispatch.
    expect(emitSpan).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// FR-011 — ModeCycle is the sole authority
//
// The handler does not hard-code transition validity; it defers to the
// shared `computeTier1NextMode` + the injected irreversible-action probe.
// This test asserts that changing the probe output is sufficient to flip
// the block — proving the handler has no private policy.
// ---------------------------------------------------------------------------

describe('FR-011 ModeCycle is sole authority', () => {
  it('handler has no private transition policy — driven only by probe', async () => {
    let flagState = true
    const probe = () => flagState
    const { deps, modeLog } = makeDeps({
      getMode: () => 'acceptEdits',
      hasPendingIrreversibleAction: probe,
    })
    const handler = buildPermissionModeCycleHandler(deps)

    // Round 1 — probe returns true → blocked.
    expect((await handler()).kind).toBe('blocked')
    expect(modeLog).toEqual([])

    // Round 2 — flip probe → dispatches.
    flagState = false
    expect((await handler()).kind).toBe('cycled')
    expect(modeLog).toEqual(['bypassPermissions'])
  })
})
