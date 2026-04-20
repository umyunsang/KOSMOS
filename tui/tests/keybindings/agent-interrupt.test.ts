// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T027 — `agent-interrupt` action regression suite.
//
// Closes #1577. Asserts:
//   - FR-012: first ctrl+c while an agent loop is running cancels the loop
//     and writes a Spec 024 `user-interrupted` audit record with the
//     session ID + interrupted tool_call_id (when present).
//   - FR-013: ctrl+c with no active loop arms a double-press exit; a second
//     ctrl+c within 2 s fires `session-exit`; a lone ctrl+c times out after
//     2 s and returns to idle.
//   - FR-030: every dispatch emits an accessibility announcement within 1 s.
//   - SC-001: loop-abort latency under the mocked Spec 027 cancellation
//     mailbox stays well below 500 ms.
//   - SC-006: the audit record content matches the Spec 024 payload shape.

import { describe, expect, it } from 'bun:test'
import {
  createAgentInterruptController,
  ARM_WINDOW_MS,
  type AgentInterruptDeps,
} from '../../src/keybindings/actions/agentInterrupt'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
  type AuditWriter,
  type CancellationSignal,
  type ReservedActionAuditPayload,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Test doubles
// ---------------------------------------------------------------------------

type AnnouncementRecord = Readonly<{
  message: string
  priority: AnnouncementPriority
  at: number
}>

function makeRecordingAnnouncer(now: () => number = () => Date.now()): {
  announcer: AccessibilityAnnouncer
  records: AnnouncementRecord[]
} {
  const records: AnnouncementRecord[] = []
  const announcer: AccessibilityAnnouncer = {
    announce(message, options) {
      records.push({
        message,
        priority: options?.priority ?? 'polite',
        at: now(),
      })
    },
  }
  return { announcer, records }
}

function makeAudit(): {
  audit: AuditWriter
  calls: ReservedActionAuditPayload[]
} {
  const calls: ReservedActionAuditPayload[] = []
  const audit: AuditWriter = {
    async writeReservedAction(payload) {
      calls.push(payload)
    },
  }
  return { audit, calls }
}

type CancelCall = Readonly<{ session_id: string; at: number }>

function makeCancellation(now: () => number = () => Date.now()): {
  signal: CancellationSignal
  calls: CancelCall[]
  failNextWith?: (err: Error) => void
} {
  const calls: CancelCall[] = []
  const signal: CancellationSignal = {
    async cancelActiveAgentLoop(session_id) {
      calls.push({ session_id, at: now() })
    },
  }
  return { signal, calls }
}

// ---------------------------------------------------------------------------
// Controller factory — wires in a virtual clock + stubs so assertions are
// deterministic.  The controller mirrors the shape the Ink-side dispatcher
// hands to `useKeybinding('Global', { 'agent-interrupt': ... })`.
// ---------------------------------------------------------------------------

type Fixture = {
  controller: ReturnType<typeof createAgentInterruptController>
  now: () => number
  advance: (ms: number) => void
  cancellation: ReturnType<typeof makeCancellation>
  audit: ReturnType<typeof makeAudit>
  recordings: AnnouncementRecord[]
  exitCalls: number[]
  beforeExitCalls: number[]
  isLoopActive: () => boolean
  setLoopActive: (v: boolean) => void
  toolCallId: string | null
  setToolCallId: (id: string | null) => void
}

function makeFixture(
  options: {
    loopActive?: boolean
    beforeExit?: () => Promise<void>
  } = {},
): Fixture {
  let virtualTime = 1_000_000
  let loopActive = options.loopActive ?? false
  let toolCallId: string | null = null
  const exitCalls: number[] = []
  const beforeExitCalls: number[] = []
  const now = () => virtualTime
  const cancellation = makeCancellation(now)
  const audit = makeAudit()
  const { announcer, records } = makeRecordingAnnouncer(now)
  // Record every `beforeExit` invocation at virtual-time of the call so
  // ordering vs `exit(0)` is observable.  Tests that want to assert a
  // specific behaviour (await, rejection) override via `options.beforeExit`.
  const defaultBeforeExit = async (): Promise<void> => {
    beforeExitCalls.push(virtualTime)
  }
  const deps: AgentInterruptDeps = {
    sessionId: '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60',
    isAgentLoopActive: () => loopActive,
    currentToolCallId: () => toolCallId,
    cancellation: cancellation.signal,
    audit: audit.audit,
    announcer,
    now,
    exit: (code) => {
      exitCalls.push(code)
    },
    beforeExit: options.beforeExit ?? defaultBeforeExit,
  }
  const controller = createAgentInterruptController(deps)
  return {
    controller,
    now,
    advance: (ms) => {
      virtualTime += ms
    },
    cancellation,
    audit,
    recordings: records,
    exitCalls,
    beforeExitCalls,
    isLoopActive: () => loopActive,
    setLoopActive: (v) => {
      loopActive = v
    },
    toolCallId,
    setToolCallId: (id) => {
      toolCallId = id
    },
  }
}

// ---------------------------------------------------------------------------
// FR-012 — ctrl+c aborts an active agent loop + writes audit
// ---------------------------------------------------------------------------

describe('FR-012 interrupt with active agent loop', () => {
  it('cancels the active loop and writes a Spec 024 audit record', async () => {
    const f = makeFixture({ loopActive: true })
    f.setToolCallId('tool-call-01H8XZ')

    const t0 = f.now()
    const outcome = await f.controller.handle()

    expect(outcome.kind).toBe('interrupted')
    // Cancellation MUST be invoked with the session id (SC-001 path).
    expect(f.cancellation.calls.length).toBe(1)
    expect(f.cancellation.calls[0]?.session_id).toBe(
      '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60',
    )
    // Audit record shape matches Spec 024 `user-interrupted`.
    expect(f.audit.calls.length).toBe(1)
    const payload = f.audit.calls[0]
    if (payload === undefined) throw new Error('no audit call')
    expect(payload.event_type).toBe('user-interrupted')
    expect(payload.session_id).toBe(
      '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60',
    )
    expect(payload.interrupted_tool_call_id).toBe('tool-call-01H8XZ')
    // Latency budget — SC-001 says 500 ms; this path uses a mocked signal
    // so we expect virtual time to be unchanged (≪ 500 ms).
    const elapsed = f.now() - t0
    expect(elapsed).toBeLessThan(500)
  })

  it('omits interrupted_tool_call_id when no tool call is in flight', async () => {
    const f = makeFixture({ loopActive: true })
    f.setToolCallId(null)

    await f.controller.handle()

    expect(f.audit.calls.length).toBe(1)
    expect(f.audit.calls[0]?.interrupted_tool_call_id).toBeUndefined()
  })

  it('announces the interrupt within 1 s at assertive priority (FR-030)', async () => {
    const f = makeFixture({ loopActive: true })
    const t0 = f.now()
    await f.controller.handle()
    expect(f.recordings.length).toBeGreaterThanOrEqual(1)
    const last = f.recordings[f.recordings.length - 1]
    if (last === undefined) throw new Error('no announcement')
    expect(last.at - t0).toBeLessThan(1000)
    expect(last.priority).toBe('assertive')
    expect(last.message.length).toBeGreaterThan(0)
  })

  it('still surfaces interrupted outcome when the audit writer rejects', async () => {
    const f = makeFixture({ loopActive: true })
    // Swap the audit writer mid-flight so we can observe failure resilience.
    f.audit.audit.writeReservedAction = async () => {
      throw new Error('simulated audit failure')
    }
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('interrupted')
    // Cancellation still fired.
    expect(f.cancellation.calls.length).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// FR-013 — double-press exit when no loop is active
// ---------------------------------------------------------------------------

describe('FR-013 double-press exit when idle', () => {
  it('first ctrl+c with no active loop arms the double-press window', async () => {
    const f = makeFixture({ loopActive: false })
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('armed')
    if (outcome.kind !== 'armed') throw new Error('unreachable')
    expect(outcome.expires_at).toBe(f.now() + ARM_WINDOW_MS)
    // No cancellation, no audit on arm.
    expect(f.cancellation.calls.length).toBe(0)
    expect(f.audit.calls.length).toBe(0)
    expect(f.exitCalls.length).toBe(0)
    // Arm announcement fires within 1 s with assertive priority.
    expect(f.recordings.length).toBe(1)
    expect(f.recordings[0]?.priority).toBe('assertive')
  })

  it('second ctrl+c within 2 s fires session-exit with exit code 0', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.advance(500) // 0.5 s later
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('exited')
    expect(f.exitCalls).toEqual([0])
    // Audit record for session-exited MUST be written (Spec 024 SC-006).
    expect(f.audit.calls.length).toBe(1)
    expect(f.audit.calls[0]?.event_type).toBe('session-exited')
  })

  it('arm times out after the 2 s window', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.advance(ARM_WINDOW_MS + 1)
    const outcome = await f.controller.handle()
    // Timeout + fresh ctrl+c behaves like a brand-new arm, not like exit.
    expect(outcome.kind).toBe('armed')
    expect(f.exitCalls.length).toBe(0)
  })

  it('reset() clears the armed state explicitly', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.controller.reset()
    // Next press re-arms, it does not fire exit.
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('armed')
    expect(f.exitCalls.length).toBe(0)
  })

  it('loop becoming active during arm window prefers interrupt over exit', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.setLoopActive(true)
    f.advance(100)
    const outcome = await f.controller.handle()
    // Interrupt path fires: cancel + user-interrupted audit, no process exit.
    expect(outcome.kind).toBe('interrupted')
    expect(f.cancellation.calls.length).toBe(1)
    expect(f.audit.calls.length).toBe(1)
    expect(f.audit.calls[0]?.event_type).toBe('user-interrupted')
    expect(f.exitCalls.length).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// Spec 288 Codex P1 — bridge close lifecycle on the double-press FIRE path.
//
// Regression guard for the legacy `useInput` ctrl+c handler removal: the
// controller now owns the `bridge.close()` call that previously lived in
// `tui.tsx`.  Asserts:
//   1. First press arms (no bridge close, no exit).
//   2. Second press within the arm window calls `beforeExit` EXACTLY ONCE
//      and then `exit(0)` — in that order.
//   3. Arm-window timeout (single press, let it expire, re-arm) never
//      touches `beforeExit` or `exit`.
//   4. `beforeExit` rejection is swallowed — the exit still fires (matches
//      the audit-resilience rule from FR-013).
//   5. Absent `beforeExit` (legacy callers, onboarding-pre-bridge mount),
//      the FIRE path still calls `exit(0)` — backwards-compatible.
// ---------------------------------------------------------------------------

describe('Spec 288 Codex P1 — bridge close before exit (FR-009)', () => {
  it('first press arms; no bridge close, no exit', async () => {
    const f = makeFixture({ loopActive: false })
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('armed')
    expect(f.beforeExitCalls.length).toBe(0)
    expect(f.exitCalls.length).toBe(0)
  })

  it('second press within arm window calls beforeExit then exit(0)', async () => {
    // Build a standalone controller so we can observe the invocation order
    // (beforeExit MUST complete before exit is called).  Using a pair of
    // captures (`beforeExitCalled`, `beforeExitCountAtExit`) avoids timing
    // flakes — the virtual clock is frozen at the time of both writes.
    let beforeExitCalled = 0
    let beforeExitCountAtExit = -1
    const exitCalls: number[] = []
    const { announcer } = makeRecordingAnnouncer()
    let virtualTime = 2_000_000
    const controller = createAgentInterruptController({
      sessionId: 'sess-order',
      isAgentLoopActive: () => false,
      currentToolCallId: () => null,
      cancellation: { async cancelActiveAgentLoop() {} },
      audit: { async writeReservedAction() {} },
      announcer,
      now: () => virtualTime,
      exit: (code) => {
        // Snapshot beforeExit count at the moment exit is invoked — if
        // beforeExit had not yet resolved, this would be 0 (bug).
        beforeExitCountAtExit = beforeExitCalled
        exitCalls.push(code)
      },
      beforeExit: async () => {
        beforeExitCalled++
      },
    })
    await controller.handle() // arm
    virtualTime += 500 // still inside the 2 s window
    const outcome = await controller.handle()

    expect(outcome.kind).toBe('exited')
    expect(beforeExitCalled).toBe(1)
    expect(exitCalls).toEqual([0])
    // Ordering assertion — beforeExit fully resolved before exit fired.
    expect(beforeExitCountAtExit).toBe(1)
  })

  it('beforeExit is invoked exactly once on the FIRE branch', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.advance(100)
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('exited')
    expect(f.beforeExitCalls.length).toBe(1)
    expect(f.exitCalls).toEqual([0])
  })

  it('beforeExit is NOT invoked when the arm window expires and the press re-arms', async () => {
    const f = makeFixture({ loopActive: false })
    await f.controller.handle() // arm
    f.advance(ARM_WINDOW_MS + 1) // timeout
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('armed')
    expect(f.beforeExitCalls.length).toBe(0)
    expect(f.exitCalls.length).toBe(0)
  })

  it('beforeExit is NOT invoked on the loop-active interrupt path', async () => {
    const f = makeFixture({ loopActive: true })
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('interrupted')
    // The interrupt path cancels the loop — it does not exit the process
    // and so MUST NOT tear the bridge down.
    expect(f.beforeExitCalls.length).toBe(0)
    expect(f.exitCalls.length).toBe(0)
  })

  it('rejected beforeExit still fires exit(0) — citizen never trapped', async () => {
    const f = makeFixture({
      loopActive: false,
      beforeExit: async () => {
        throw new Error('simulated bridge close failure')
      },
    })
    await f.controller.handle() // arm
    f.advance(100)
    const outcome = await f.controller.handle()
    expect(outcome.kind).toBe('exited')
    expect(f.exitCalls).toEqual([0])
  })

  it('omitting beforeExit preserves legacy direct-exit behaviour', async () => {
    const exitCalls: number[] = []
    const { announcer } = makeRecordingAnnouncer()
    let virtualTime = 1_000_000
    const controller = createAgentInterruptController({
      sessionId: 'sess-legacy',
      isAgentLoopActive: () => false,
      currentToolCallId: () => null,
      cancellation: { async cancelActiveAgentLoop() {} },
      audit: { async writeReservedAction() {} },
      announcer,
      now: () => virtualTime,
      exit: (code) => {
        exitCalls.push(code)
      },
      // beforeExit intentionally omitted — mimics callers that predate the
      // Spec 288 Codex P1 bridge wiring (tests, onboarding-pre-bridge mount).
    })
    await controller.handle() // arm
    virtualTime += 100
    const outcome = await controller.handle()
    expect(outcome.kind).toBe('exited')
    expect(exitCalls).toEqual([0])
  })
})

// ---------------------------------------------------------------------------
// SC-001 — loop-abort timing under the mocked mailbox
// ---------------------------------------------------------------------------

describe('SC-001 loop-abort timing budget', () => {
  it('dispatches the cancellation envelope in well under 500 ms wall-clock', async () => {
    const realNow = () => performance.now()
    const { announcer } = makeRecordingAnnouncer(realNow)
    const { audit } = makeAudit()
    const { signal, calls } = makeCancellation(realNow)
    const controller = createAgentInterruptController({
      sessionId: 'sess-timing',
      isAgentLoopActive: () => true,
      currentToolCallId: () => null,
      cancellation: signal,
      audit,
      announcer,
      now: realNow,
      exit: () => undefined,
    })

    const t0 = performance.now()
    const outcome = await controller.handle()
    const elapsed = performance.now() - t0

    expect(outcome.kind).toBe('interrupted')
    expect(calls.length).toBe(1)
    expect(elapsed).toBeLessThan(500)
  })
})
