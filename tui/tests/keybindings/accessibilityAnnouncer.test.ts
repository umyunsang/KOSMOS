// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Codex P2 regression — accessibility announcer priority order.
//
// Closes the Codex P2 finding on PR #1591: `announce()` previously appended
// every message to a shared FIFO buffer and then called `flushQueued()` for
// assertive events, so a queued polite message was emitted first — delaying
// the urgent cue. The fix: assertive messages bypass the polite queue and
// are written synchronously, matching WAI-ARIA `aria-live="assertive"`
// semantics. These tests lock the fix in.
//
// Contract under test (`tui/src/keybindings/accessibilityAnnouncer.ts`):
//   - polite messages go through a buffered queue + scheduler (microtask).
//   - assertive messages bypass the queue entirely and write synchronously.
//   - on a same-tick (polite, assertive) pair, the assertive write MUST
//     land before the polite write.

import { describe, expect, it } from 'bun:test'
import { createAccessibilityAnnouncer } from '../../src/keybindings/accessibilityAnnouncer'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeCollectingSink(): {
  writes: string[]
  write: (chunk: string) => void
} {
  const writes: string[] = []
  return {
    writes,
    write(chunk) {
      writes.push(chunk)
    },
  }
}

/**
 * Deferred scheduler — captures the callback and fires it only when the
 * test explicitly flushes. Lets us assert write order without racing
 * against `queueMicrotask`.
 */
function makeDeferredScheduler(): {
  pending: Array<() => void>
  schedule: (cb: () => void) => void
  flush: () => void
} {
  const pending: Array<() => void> = []
  return {
    pending,
    schedule(cb) {
      pending.push(cb)
    },
    flush() {
      while (pending.length > 0) {
        const cb = pending.shift()
        if (cb !== undefined) cb()
      }
    },
  }
}

// ---------------------------------------------------------------------------
// Codex P2 regression — assertive bypasses queued polite
// ---------------------------------------------------------------------------

describe('Codex P2 — assertive bypasses queued polite', () => {
  it('assertive write lands BEFORE an earlier same-tick polite write', () => {
    // BEFORE the fix: `A` (polite) flushes first because assertive calls
    // flushQueued() which drains the FIFO in order, so the write sink saw
    // [polite A, assertive B]. AFTER: assertive bypasses the queue, so
    // the sink sees [assertive B, ...] and `A` drains later on the
    // scheduled polite flush.
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })

    // Same-tick pair: polite first, then assertive.
    announcer.announce('A', { priority: 'polite' })
    announcer.announce('B', { priority: 'assertive' })

    // Before any scheduled flush, the sink must already hold the assertive
    // write and ONLY the assertive write (the polite one is still queued).
    expect(sink.writes.length).toBe(1)
    expect(sink.writes[0]).toContain('assertive')
    expect(sink.writes[0]).toContain('B')
    expect(sink.writes[0]).not.toContain(' A\n')

    // Now drain the polite queue via the deferred scheduler.
    sched.flush()

    // Final order: assertive B, then polite A.
    expect(sink.writes.length).toBe(2)
    const first = sink.writes[0]
    const second = sink.writes[1]
    if (first === undefined || second === undefined) {
      throw new Error('sink missing expected writes')
    }
    expect(first).toContain('assertive')
    expect(first).toContain('B')
    expect(second).toContain('polite')
    expect(second).toContain('A')
  })

  it('multiple polite messages still drain in FIFO on the scheduled flush', () => {
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })

    announcer.announce('one', { priority: 'polite' })
    announcer.announce('two', { priority: 'polite' })
    announcer.announce('three', { priority: 'polite' })

    // Nothing emitted until the scheduler fires.
    expect(sink.writes.length).toBe(0)
    sched.flush()
    expect(sink.writes.length).toBe(3)
    const [w0, w1, w2] = sink.writes
    if (w0 === undefined || w1 === undefined || w2 === undefined) {
      throw new Error('sink missing expected writes')
    }
    expect(w0).toContain('one')
    expect(w1).toContain('two')
    expect(w2).toContain('three')
  })

  it('assertive-only path writes synchronously with no scheduler dependency', () => {
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })

    announcer.announce('urgent', { priority: 'assertive' })

    // Sync write — no need to flush the scheduler.
    expect(sink.writes.length).toBe(1)
    expect(sched.pending.length).toBe(0)
    const [only] = sink.writes
    if (only === undefined) throw new Error('sink missing assertive write')
    expect(only).toContain('assertive')
    expect(only).toContain('urgent')
  })

  it('interleaved polite → assertive → polite preserves the priority invariant', () => {
    // Scenario: two polite messages bracket an assertive one in the same
    // synchronous tick. The assertive MUST land first; the two polite
    // entries drain in insertion order on the scheduled flush.
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })

    announcer.announce('polite-1', { priority: 'polite' })
    announcer.announce('URGENT', { priority: 'assertive' })
    announcer.announce('polite-2', { priority: 'polite' })

    // Immediate: only the assertive has been written.
    expect(sink.writes.length).toBe(1)
    const [immediate] = sink.writes
    if (immediate === undefined) throw new Error('sink missing assertive')
    expect(immediate).toContain('URGENT')
    expect(immediate).toContain('assertive')

    // Drain polite queue.
    sched.flush()
    expect(sink.writes.length).toBe(3)
    const second = sink.writes[1]
    const third = sink.writes[2]
    if (second === undefined || third === undefined) {
      throw new Error('sink missing polite writes')
    }
    expect(second).toContain('polite-1')
    expect(third).toContain('polite-2')
  })

  it('drain() snapshots only the still-queued polite buffer, not delivered assertive', () => {
    // Assertive writes bypass the buffer entirely — they are never
    // `drain()`able because they are already gone. Polite messages that
    // have not yet flushed are visible in `drain()`.
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })

    announcer.announce('queued-polite', { priority: 'polite' })
    announcer.announce('sync-assertive', { priority: 'assertive' })

    const snapshot = announcer.drain()
    expect(snapshot.length).toBe(1)
    const [record] = snapshot
    if (record === undefined) throw new Error('snapshot missing polite record')
    expect(record.priority).toBe('polite')
    expect(record.message).toBe('queued-polite')

    // Assertive is already on the sink (synchronous path).
    expect(sink.writes.length).toBe(1)
    const [assertiveWrite] = sink.writes
    if (assertiveWrite === undefined) {
      throw new Error('sink missing assertive write')
    }
    expect(assertiveWrite).toContain('sync-assertive')
  })
})

// ---------------------------------------------------------------------------
// Default priority + format contract
// ---------------------------------------------------------------------------

describe('accessibility announcer formatting', () => {
  it('omitted priority defaults to `polite`', () => {
    const sink = makeCollectingSink()
    const sched = makeDeferredScheduler()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: sched.schedule,
    })
    announcer.announce('default-priority')
    sched.flush()
    expect(sink.writes.length).toBe(1)
    const [only] = sink.writes
    if (only === undefined) throw new Error('sink missing polite write')
    expect(only).toContain('polite')
    expect(only).toContain('default-priority')
  })

  it('each write ends with a newline so screen-reader stdin forwarding splits cleanly', () => {
    const sink = makeCollectingSink()
    const announcer = createAccessibilityAnnouncer({
      write: sink.write,
      schedule: (cb) => cb(),
    })
    announcer.announce('msg-sync', { priority: 'assertive' })
    const [only] = sink.writes
    if (only === undefined) throw new Error('sink missing write')
    expect(only.endsWith('\n')).toBe(true)
  })
})
