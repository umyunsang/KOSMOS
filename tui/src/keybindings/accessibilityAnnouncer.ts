// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T015 — KOSMOS-original accessibility announcer.
//
// Implements `AccessibilityAnnouncer` from `./types`. Buffered text channel
// reaching screen readers (NVDA / VoiceOver / 센스리더) through the standard
// stderr announce pipeline per D8 and KWCAG 2.1 § 4.1.3.
//
// Design:
//   - `polite` messages are queued and flushed on the next microtask.
//   - `assertive` messages are written synchronously and bypass the polite
//     queue entirely — this mirrors WAI-ARIA `aria-live="assertive"`
//     semantics where an urgent announcement must interrupt anything the
//     screen reader is currently speaking, including any queued-but-not-yet
//     -emitted polite notices. If we routed assertive through the shared
//     FIFO, an earlier polite entry in the same tick (e.g. a status update)
//     would be spoken first, delaying the urgent cue (e.g. an interrupt
//     warning). See Codex P2 on PR #1591.
//   - Both write to stderr with an `[a11y]` prefix that screen readers in
//     terminal mode forward via their stdin channel.
//   - The contract mandates delivery within 1 s (FR-030). The implementation
//     uses `queueMicrotask` for polite delivery which is orders of magnitude
//     under that budget; assertive delivery is synchronous.

import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from './types'

export type AnnounceRecord = Readonly<{
  message: string
  priority: AnnouncementPriority
  at: number
}>

export type BufferedAnnouncer = AccessibilityAnnouncer & {
  /** Test helper — drain the queue and return captured messages. */
  drain(): ReadonlyArray<AnnounceRecord>
}

export type AccessibilityAnnouncerOptions = {
  /** Write sink — defaults to `process.stderr.write`. Injectable for tests. */
  write?: (chunk: string) => void
  /** Clock — injectable for tests. */
  now?: () => number
  /** Scheduler for polite flush — defaults to `queueMicrotask`. */
  schedule?: (cb: () => void) => void
}

export function createAccessibilityAnnouncer(
  options: AccessibilityAnnouncerOptions = {},
): BufferedAnnouncer {
  const write =
    options.write ?? ((chunk: string) => process.stderr.write(chunk))
  const now = options.now ?? Date.now
  const schedule = options.schedule ?? queueMicrotask

  const buffer: AnnounceRecord[] = []
  let scheduled = false

  function format(record: AnnounceRecord): string {
    return `[a11y ${record.priority}] ${record.message}\n`
  }

  function flushQueued(): void {
    scheduled = false
    while (buffer.length > 0) {
      const record = buffer.shift()
      if (record === undefined) break
      write(format(record))
    }
  }

  return {
    announce(message: string, opts) {
      const priority: AnnouncementPriority = opts?.priority ?? 'polite'
      const record: AnnounceRecord = Object.freeze({
        message,
        priority,
        at: now(),
      })
      if (priority === 'assertive') {
        // WAI-ARIA `aria-live="assertive"` semantics: bypass the polite
        // queue and emit synchronously so a same-tick urgent announcement
        // (e.g. interrupt warning) is not delayed behind an earlier polite
        // status update.  The polite queue drains on its own scheduled
        // flush and stays intact. Codex P2 on PR #1591.
        write(format(record))
        return
      }
      buffer.push(record)
      if (!scheduled) {
        scheduled = true
        schedule(flushQueued)
      }
    },
    drain() {
      const snapshot = Object.freeze(buffer.slice())
      buffer.length = 0
      return snapshot
    },
  }
}
