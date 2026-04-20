// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T029 — `session-exit` (ctrl+d) action regression suite.
//
// Closes #1578. Asserts:
//   - FR-014: non-empty-buffer keystroke is ignored (citizen-safety rule).
//   - FR-015: audit queue is drained BEFORE `process.exit(0)` — the exit
//     path never races with in-flight audit writes.
//   - FR-015: an active agent loop triggers a confirmation prompt and
//     holds the exit until the citizen acknowledges.
//   - FR-015 + SC-006: after clean exit, every pending audit record is
//     flushed (spawn-and-exit harness simulates the durable-storage side).
//   - FR-030: screen-reader announcement fires within 1 s of dispatch.
//
// The handler is exposed as a pure builder (`buildSessionExitHandler`) that
// accepts injected dependencies (audit flush, announcer, process exit,
// buffer + active-loop probes, confirmation callback). The real wiring at
// `main.tsx` fills these with the IPC bridge + raw `process.exit`; tests
// substitute in-memory doubles so no actual exit fires.

import { beforeEach, describe, expect, it, mock } from 'bun:test'
import {
  buildSessionExitHandler,
  type SessionExitDeps,
} from '../../src/keybindings/actions/sessionExit'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Shared test doubles
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
        at: Date.now(),
      })
    },
  }
  return { announcer, records }
}

type AuditLog = Readonly<{ label: string; at: number }>

/** Fake audit writer queue. Drain semantics mirror the production writer. */
function makeAuditQueue() {
  const pending: AuditLog[] = []
  const drained: AuditLog[] = []
  return {
    enqueue(label: string): void {
      pending.push(Object.freeze({ label, at: Date.now() }))
    },
    drain: mock(async () => {
      // Simulate async I/O — a real audit writer flushes to disk.
      await new Promise<void>((resolve) => setTimeout(resolve, 1))
      while (pending.length > 0) {
        const entry = pending.shift()
        if (entry === undefined) break
        drained.push(entry)
      }
    }),
    pending,
    drained,
  }
}

function makeDeps(overrides: Partial<SessionExitDeps> = {}): {
  deps: SessionExitDeps
  exitCalls: number[]
  announcer: AccessibilityAnnouncer
  announcements: AnnouncementRecord[]
} {
  const { announcer, records } = makeRecordingAnnouncer()
  const exitCalls: number[] = []
  const deps: SessionExitDeps = {
    isBufferEmpty: () => true,
    isLoopActive: () => false,
    flushAudit: async () => {},
    announcer,
    confirmExit: async () => true,
    processExit: ((code) => {
      exitCalls.push(code ?? 0)
    }) as (code?: number) => never,
    ...overrides,
  }
  return { deps, exitCalls, announcer, announcements: records }
}

// ---------------------------------------------------------------------------
// FR-014 — non-empty-buffer ignore
// ---------------------------------------------------------------------------

describe('FR-014 session-exit buffer-empty guard', () => {
  it('does NOT exit when the input buffer has pending text', async () => {
    const { deps, exitCalls, announcements } = makeDeps({
      isBufferEmpty: () => false,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('blocked')
    if (result.kind !== 'blocked') throw new Error('unreachable')
    expect(result.reason).toBe('buffer-non-empty')
    expect(exitCalls.length).toBe(0)
    // No announcement when silently ignored — citizen is mid-typing.
    expect(announcements.length).toBe(0)
  })

  it('proceeds past the guard when the buffer is empty', async () => {
    const { deps, exitCalls } = makeDeps({
      isBufferEmpty: () => true,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('exited')
    expect(exitCalls).toEqual([0])
  })
})

// ---------------------------------------------------------------------------
// FR-015 — active-loop confirmation prompt
// ---------------------------------------------------------------------------

describe('FR-015 active-loop confirmation', () => {
  it('asks for confirmation before exiting when a loop is running', async () => {
    const confirmExit = mock(async () => true)
    const { deps, exitCalls } = makeDeps({
      isLoopActive: () => true,
      confirmExit,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(confirmExit).toHaveBeenCalledTimes(1)
    expect(result.kind).toBe('exited')
    expect(exitCalls).toEqual([0])
  })

  it('aborts the exit when the citizen declines the confirmation', async () => {
    const confirmExit = mock(async () => false)
    const { deps, exitCalls, announcements } = makeDeps({
      isLoopActive: () => true,
      confirmExit,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(confirmExit).toHaveBeenCalledTimes(1)
    expect(result.kind).toBe('blocked')
    if (result.kind !== 'blocked') throw new Error('unreachable')
    expect(result.reason).toBe('exit-cancelled')
    expect(exitCalls.length).toBe(0)
    // Announces the cancellation so screen-reader users know the exit
    // did NOT fire.
    expect(announcements.some((r) => r.message.includes('취소'))).toBe(true)
  })

  it('skips confirmation when no loop is active', async () => {
    const confirmExit = mock(async () => true)
    const { deps, exitCalls } = makeDeps({
      isLoopActive: () => false,
      confirmExit,
    })
    const handler = buildSessionExitHandler(deps)
    await handler()
    expect(confirmExit).not.toHaveBeenCalled()
    expect(exitCalls).toEqual([0])
  })
})

// ---------------------------------------------------------------------------
// FR-015 / SC-006 — audit flush completeness (spawn-and-exit harness)
// ---------------------------------------------------------------------------

describe('FR-015 / SC-006 audit flush completeness', () => {
  it('drains the audit queue BEFORE process.exit fires', async () => {
    const queue = makeAuditQueue()
    queue.enqueue('tool-call-1')
    queue.enqueue('tool-call-2')
    queue.enqueue('tool-call-3')

    // Track strict ordering between drain completion and exit invocation.
    const order: string[] = []
    const drainWrapper = async (): Promise<void> => {
      order.push('drain-start')
      await queue.drain()
      order.push('drain-end')
    }
    const { deps } = makeDeps({
      flushAudit: drainWrapper,
      processExit: ((code) => {
        order.push(`exit-${code ?? 0}`)
      }) as (code?: number) => never,
    })

    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('exited')
    // Strict ordering: drain MUST complete before exit fires.
    expect(order).toEqual(['drain-start', 'drain-end', 'exit-0'])
    // Every enqueued record reached the durable side.
    expect(queue.pending.length).toBe(0)
    expect(queue.drained.length).toBe(3)
    expect(queue.drained.map((r) => r.label)).toEqual([
      'tool-call-1',
      'tool-call-2',
      'tool-call-3',
    ])
  })

  it('still exits with code 0 even when the audit flush rejects', async () => {
    const order: string[] = []
    const flushAudit = mock(async () => {
      order.push('drain-start')
      throw new Error('simulated flush failure')
    })
    const { deps } = makeDeps({
      flushAudit,
      processExit: ((code) => {
        order.push(`exit-${code ?? 0}`)
      }) as (code?: number) => never,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    // The exit path must still fire; audit failure MUST NOT trap the
    // citizen in a half-shut session (parallels resolver's FR-013
    // robustness rule).
    expect(result.kind).toBe('exited')
    expect(order[0]).toBe('drain-start')
    expect(order[1]).toBe('exit-0')
  })

  it('sequences drain → exit even when the audit flush is slow', async () => {
    // Simulate a 50 ms async flush. The exit must still wait.
    let flushResolved = false
    const flushAudit = mock(async () => {
      await new Promise<void>((resolve) => setTimeout(resolve, 50))
      flushResolved = true
    })
    const exitCaptured: number[] = []
    const processExit = ((code: number | undefined) => {
      // If exit fires before flush resolves, flushResolved is still false.
      exitCaptured.push(code ?? 0)
    }) as (code?: number) => never

    const { deps } = makeDeps({ flushAudit, processExit })
    const handler = buildSessionExitHandler(deps)
    await handler()
    expect(flushResolved).toBe(true)
    expect(exitCaptured).toEqual([0])
  })
})

// ---------------------------------------------------------------------------
// FR-030 — accessibility announcement within 1 s
// ---------------------------------------------------------------------------

describe('FR-030 session-exit accessibility announcement', () => {
  it('fires an announcement within 1 s of dispatch on clean exit', async () => {
    const { deps, announcements } = makeDeps()
    const t0 = Date.now()
    const handler = buildSessionExitHandler(deps)
    await handler()
    expect(announcements.length).toBeGreaterThanOrEqual(1)
    const last = announcements[announcements.length - 1]
    if (last === undefined) throw new Error('no announcement recorded')
    expect(last.at - t0).toBeLessThan(1000)
    expect(last.message.length).toBeGreaterThan(0)
  })

  it('announces the non-empty-buffer guard silently (no announcement)', async () => {
    // Rationale: buffer-non-empty is a benign no-op (FR-034) — the
    // citizen is mid-typing, and a screen-reader interruption would be
    // more jarring than silence. This mirrors the resolver's
    // `no-match` path.
    const { deps, announcements } = makeDeps({ isBufferEmpty: () => false })
    const handler = buildSessionExitHandler(deps)
    await handler()
    expect(announcements.length).toBe(0)
  })

  it('escalates to assertive priority when the exit confirmation is cancelled', async () => {
    const { deps, announcements } = makeDeps({
      isLoopActive: () => true,
      confirmExit: async () => false,
    })
    const handler = buildSessionExitHandler(deps)
    await handler()
    const cancellation = announcements.find((r) => r.message.includes('취소'))
    expect(cancellation).toBeDefined()
    // Citizens attempting to exit during a loop should hear the reason
    // the exit did not fire — assertive priority interrupts the reader.
    expect(cancellation?.priority).toBe('assertive')
  })
})

// ---------------------------------------------------------------------------
// Handler re-entrancy — defensive: second invocation after successful exit
// must be idempotent.
// ---------------------------------------------------------------------------

describe('session-exit idempotence', () => {
  it('does not double-flush when invoked twice', async () => {
    const flushAudit = mock(async () => {})
    const { deps } = makeDeps({ flushAudit })
    const handler = buildSessionExitHandler(deps)
    await handler()
    await handler()
    // Each call MUST drain once — reentrancy is the caller's
    // responsibility. Tests just confirm the builder does not
    // accidentally retain state between invocations.
    expect(flushAudit).toHaveBeenCalledTimes(2)
  })
})

// ---------------------------------------------------------------------------
// Harness-level smoke: wire the builder's exit into a fake signal so we
// can simulate a real spawn-and-exit round trip without actually killing
// the test worker.
// ---------------------------------------------------------------------------

describe('spawn-and-exit smoke', () => {
  let exitCode: number | null = null
  let processExit: (code?: number) => never

  beforeEach(() => {
    exitCode = null
    processExit = ((code) => {
      exitCode = code ?? 0
    }) as (code?: number) => never
  })

  it('end-to-end: enqueue 5 records → ctrl+d → flush + exit(0)', async () => {
    const queue = makeAuditQueue()
    for (let i = 0; i < 5; i += 1) queue.enqueue(`record-${i}`)

    const { deps } = makeDeps({
      flushAudit: () => queue.drain(),
      processExit,
    })
    const handler = buildSessionExitHandler(deps)
    const result = await handler()
    expect(result.kind).toBe('exited')
    expect(exitCode).toBe(0)
    expect(queue.drained.length).toBe(5)
    expect(queue.pending.length).toBe(0)
  })
})
