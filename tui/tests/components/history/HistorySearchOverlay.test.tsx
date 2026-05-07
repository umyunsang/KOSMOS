// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Codex P2 regression — `<HistorySearchOverlay>` scroll-offset.
//
// The pre-fix overlay rendered `filtered.slice(0, max_rows)` while allowing
// `cursor` to advance up to `filtered.length - 1`.  Once the result list
// exceeded `max_rows` the cursor could wander off-screen and `enter` would
// silently select a hidden entry.  This suite pins the post-fix behaviour:
//
//   (a) the cursor-marker "› " never leaves the visible window — if the
//       citizen holds down-arrow past the last visible row, the window
//       slides rather than stranding the highlight off-screen;
//   (b) the scroll offset advances when the cursor crosses the bottom of
//       the visible window and recedes symmetrically on up-arrow;
//   (c) `enter` always selects the row that is visually highlighted (the
//       onSelect callback receives `filtered[cursor]`, and `cursor` is
//       guaranteed to live inside the window);
//   (d) changing the filter needle resets both the cursor and the scroll
//       offset so the first render after a keystroke always shows the top
//       of the result list.
//
// Harness detail: `ink-testing-library`'s `stdin.write()` only queues data;
// Ink drains it on the next `readable` tick and React 19 batches the
// resulting state updates.  Tests `await tick()` between writes so the
// rendered frame reflects the latest keystroke before we sample it.

import { describe, expect, mock, test } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ThemeProvider } from '../../../src/theme/provider'
import { HistorySearchOverlay } from '../../../src/components/history/HistorySearchOverlay'
import {
  type HistoryEntry,
  type OverlayOpenRequest,
} from '../../../src/keybindings/actions/historySearch'
import { type AccessibilityAnnouncer } from '../../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Async tick — lets Ink drain stdin + React 19 flush renders.  20 ms is
// empirically enough for ink-testing-library's EventEmitter-based stream
// without slowing the suite perceptibly (each test ≈ 200 ms).
// ---------------------------------------------------------------------------

function tick(ms = 20): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ---------------------------------------------------------------------------
// Test doubles
// ---------------------------------------------------------------------------

function makeAnnouncer(): AccessibilityAnnouncer {
  return {
    announce() {
      // no-op — priority + timing are covered by the action-layer suite;
      // this file is only concerned with the visible-window invariants.
    },
  }
}

// Build a deterministic entry list large enough to overflow max_rows.
function makeEntries(n: number): HistoryEntry[] {
  const out: HistoryEntry[] = []
  for (let i = 0; i < n; i += 1) {
    out.push({
      query_text: `entry-${String(i).padStart(2, '0')}`,
      timestamp: new Date(Date.UTC(2026, 3, 20, 0, 0, i)).toISOString(),
      session_id: '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60',
      consent_scope: 'current-session',
    })
  }
  return out
}

function makeRequest(entries: ReadonlyArray<HistoryEntry>): OverlayOpenRequest {
  return Object.freeze({
    visible_entries: Object.freeze(entries.slice()),
    saved_draft: '',
    scope_notice: false,
    opened_at: Date.now(),
  })
}

// Terminal escape sequences for arrow keys as emitted by a VT100-compatible
// terminal — Ink parses these into `key.upArrow` / `key.downArrow`.
const DOWN = '\u001B[B'
const UP = '\u001B[A'

// Count highlighted rows by scanning for the "› " marker that the overlay
// draws in front of the cursor row.  Used to assert the marker appears
// exactly once — proving the cursor lives inside the rendered window.
function countCursorMarkers(frame: string): number {
  // Match only the literal marker characters; avoids false positives from
  // emoji or directional arrows that callers might feed into query_text.
  const matches = frame.match(/› /gu)
  return matches === null ? 0 : matches.length
}

function visibleEntryLabels(frame: string): string[] {
  // The overlay prefixes every row with either "› " (cursor) or "  "
  // (blank).  Extract just the entry labels for order-sensitive assertions.
  const labels: string[] = []
  const lines = frame.split('\n')
  for (const line of lines) {
    const m = line.match(/(?:› |  )(entry-\d{2})/u)
    if (m !== null && m[1] !== undefined) labels.push(m[1])
  }
  return labels
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const MAX_ROWS = 4

type RenderOpts = Readonly<{
  entries: ReadonlyArray<HistoryEntry>
  onSelect?: (next_draft: string) => void
  onCancel?: (next_draft: string) => void
}>

function mount(opts: RenderOpts) {
  const onSelect = opts.onSelect ?? mock((_: string) => {})
  const onCancel = opts.onCancel ?? mock((_: string) => {})
  const announcer = makeAnnouncer()
  const request = makeRequest(opts.entries)
  const tree = render(
    <ThemeProvider>
      <HistorySearchOverlay
        request={request}
        announcer={announcer}
        onSelect={onSelect}
        onCancel={onCancel}
        max_rows={MAX_ROWS}
      />
    </ThemeProvider>,
  )
  return { ...tree, onSelect, onCancel }
}

async function press(
  stdin: { write: (s: string) => void },
  seq: string,
  repeat = 1,
): Promise<void> {
  for (let i = 0; i < repeat; i += 1) {
    stdin.write(seq)
    await tick()
  }
}

// ---------------------------------------------------------------------------
// (a) Cursor marker stays inside the visible window
// ---------------------------------------------------------------------------

describe('HistorySearchOverlay — cursor stays in visible window', () => {
  test('down-arrow past the last visible row slides the window rather than losing the cursor', async () => {
    const entries = makeEntries(10) // 10 entries, max_rows = 4
    const { stdin, lastFrame } = mount({ entries })
    await tick()

    // Start state: window shows entry-00..entry-03, cursor on entry-00.
    const initial = lastFrame() ?? ''
    expect(visibleEntryLabels(initial)).toEqual([
      'entry-00',
      'entry-01',
      'entry-02',
      'entry-03',
    ])
    expect(countCursorMarkers(initial)).toBe(1)
    expect(initial).toContain('› entry-00')

    // Hold down-arrow 6 times → cursor should reach entry-06.  If the
    // pre-fix logic were still in place the marker would vanish once the
    // cursor stepped past entry-03 (index 3 in a 0..3 window).
    await press(stdin, DOWN, 6)

    const after = lastFrame() ?? ''
    // Exactly one row is highlighted — the cursor is never off-screen.
    expect(countCursorMarkers(after)).toBe(1)
    // Window slid down: entry-03..entry-06 visible, cursor on entry-06.
    expect(visibleEntryLabels(after)).toEqual([
      'entry-03',
      'entry-04',
      'entry-05',
      'entry-06',
    ])
    expect(after).toContain('› entry-06')
  })

  test('cursor is clamped at filtered.length - 1 — down-arrow past the end is a no-op', async () => {
    const entries = makeEntries(5)
    const { stdin, lastFrame } = mount({ entries })
    await tick()

    // 5 entries, max_rows = 4.  Press down-arrow 20× — cursor must clamp
    // at entry-04 and the window must show entry-01..entry-04.
    await press(stdin, DOWN, 20)
    const frame = lastFrame() ?? ''
    expect(countCursorMarkers(frame)).toBe(1)
    expect(frame).toContain('› entry-04')
    expect(visibleEntryLabels(frame)).toEqual([
      'entry-01',
      'entry-02',
      'entry-03',
      'entry-04',
    ])
  })
})

// ---------------------------------------------------------------------------
// (b) Scroll offset advances / recedes symmetrically
// ---------------------------------------------------------------------------

describe('HistorySearchOverlay — scroll offset symmetry', () => {
  test('up-arrow past the top of the window slides the window back up', async () => {
    const entries = makeEntries(10)
    const { stdin, lastFrame } = mount({ entries })
    await tick()

    // Walk all the way to the bottom so the window is at its lowest.
    await press(stdin, DOWN, 9)
    let frame = lastFrame() ?? ''
    expect(frame).toContain('› entry-09')
    expect(visibleEntryLabels(frame)).toEqual([
      'entry-06',
      'entry-07',
      'entry-08',
      'entry-09',
    ])

    // Walk back up past the visible window — cursor on entry-03 should now
    // pull the window up so entry-03 is the top-most visible row.
    await press(stdin, UP, 6)
    frame = lastFrame() ?? ''
    expect(countCursorMarkers(frame)).toBe(1)
    expect(frame).toContain('› entry-03')
    expect(visibleEntryLabels(frame)).toEqual([
      'entry-03',
      'entry-04',
      'entry-05',
      'entry-06',
    ])
  })
})

// ---------------------------------------------------------------------------
// (c) Enter selects the HIGHLIGHTED row
// ---------------------------------------------------------------------------

describe('HistorySearchOverlay — enter selects highlighted row', () => {
  test('after scrolling into the lower window, enter emits the cursor row (never a hidden entry)', async () => {
    const entries = makeEntries(10)
    const onSelect = mock((_: string) => {})
    const { stdin, lastFrame } = mount({ entries, onSelect })
    await tick()

    // Scroll to entry-07 — this is well past max_rows so a pre-fix overlay
    // would have rendered only entry-00..entry-03 while the cursor pointed
    // at an off-screen row.  Post-fix, entry-07 is both highlighted AND
    // visible.
    await press(stdin, DOWN, 7)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('› entry-07')
    expect(countCursorMarkers(frame)).toBe(1)

    stdin.write('\r') // Enter
    await tick()
    expect(onSelect).toHaveBeenCalledTimes(1)
    const call = onSelect.mock.calls[0] as [string] | undefined
    if (call === undefined) throw new Error('onSelect was not invoked')
    expect(call[0]).toBe('entry-07')
  })
})

// ---------------------------------------------------------------------------
// (d) Filter change resets scrollOffset + cursor
// ---------------------------------------------------------------------------

describe('HistorySearchOverlay — needle change resets the window', () => {
  test('typing a character after scrolling pulls the window back to the top', async () => {
    const entries = makeEntries(10)
    const { stdin, lastFrame } = mount({ entries })
    await tick()

    // Scroll deep into the list.
    await press(stdin, DOWN, 8)
    let frame = lastFrame() ?? ''
    expect(frame).toContain('› entry-08')

    // Type a digit that still matches the 10-entry haystack.  `entry-` is
    // a substring of every row, so the result list length is unchanged —
    // what we're asserting is that the cursor + scroll offset both reset
    // to 0 on the keystroke, not that the filter culls anything.
    stdin.write('e')
    await tick()
    frame = lastFrame() ?? ''
    expect(countCursorMarkers(frame)).toBe(1)
    expect(frame).toContain('› entry-00')
    expect(visibleEntryLabels(frame)).toEqual([
      'entry-00',
      'entry-01',
      'entry-02',
      'entry-03',
    ])
  })

  test('narrowing the needle to a smaller result set keeps the cursor inside the new list', async () => {
    const entries = makeEntries(10)
    const { stdin, lastFrame } = mount({ entries })
    await tick()

    // Scroll past what will be the new result set.
    await press(stdin, DOWN, 8)

    // "entry-01" matches only one row (entry-01 itself).  After the filter,
    // cursor must be 0 and the single row must be highlighted.
    for (const ch of 'entry-01') {
      stdin.write(ch)
      await tick()
    }
    const frame = lastFrame() ?? ''
    expect(countCursorMarkers(frame)).toBe(1)
    expect(frame).toContain('› entry-01')
  })
})
