// SPDX-License-Identifier: Apache-2.0
// T109 — Stateless-TUI invariant test (US6 scenario 4).
//
// Spec § Assumptions: The TUI holds no persistent state. All session data
// lives in the Python backend. Dispatching SESSION_EVENT actions (save/list/
// resume/load/new/exit) MUST NOT create, modify, or delete any files under
// the tui/ directory tree.
//
// Approach: snapshot tui/ directory entries before and after dispatching the
// full SESSION_EVENT lifecycle, assert the snapshot is byte-for-byte identical.

import { describe, it, expect } from 'bun:test'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { dispatchSessionAction } from '../../src/store/session-store'

// ---------------------------------------------------------------------------
// Directory snapshot helper
// ---------------------------------------------------------------------------

/** Entries excluded from the snapshot — these change legitimately during test runs. */
const EXCLUDED = new Set([
  'node_modules',
  '.turbo',
  'dist',
  'coverage',
  '__snapshots__',
])

/**
 * Walk `dir` recursively and collect {relPath, size, mtimeMs} for every file
 * that does not live under an EXCLUDED directory name or end with .log.
 * Returns a sorted, stable string summary suitable for deep equality.
 */
function snapshotDir(baseDir: string): string {
  const entries: string[] = []

  function walk(dir: string): void {
    let children: string[]
    try {
      children = fs.readdirSync(dir)
    } catch {
      return
    }
    for (const name of children) {
      if (EXCLUDED.has(name) || name.endsWith('.log')) continue
      const full = path.join(dir, name)
      let stat: fs.Stats
      try {
        stat = fs.statSync(full)
      } catch {
        continue
      }
      if (stat.isDirectory()) {
        walk(full)
      } else {
        const rel = path.relative(baseDir, full)
        // Include mtime at 1-second granularity and size.
        // Tests run fast enough that mtime granularity is not a concern,
        // but we avoid sub-millisecond noise by rounding to seconds.
        entries.push(`${rel}|${Math.floor(stat.mtimeMs / 1000)}|${stat.size}`)
      }
    }
  }

  walk(baseDir)
  return entries.sort().join('\n')
}

// ---------------------------------------------------------------------------
// Locate tui/ root (two directories up from tests/store/)
// ---------------------------------------------------------------------------

const TUI_ROOT = path.resolve(import.meta.dir, '../../')

// ---------------------------------------------------------------------------
// Test
// ---------------------------------------------------------------------------

describe('Stateless-TUI file-system invariant (US6 scenario 4)', () => {
  it('dispatching full SESSION_EVENT lifecycle creates no new files', () => {
    const before = snapshotDir(TUI_ROOT)

    // Full SESSION_EVENT lifecycle — covers all six event variants
    dispatchSessionAction({ type: 'SESSION_EVENT', event: 'save', payload: {} })
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'list',
      payload: { sessions: [{ id: 's1', created_at: '2026-01-01T00:00:00Z', turn_count: 1 }] },
    })
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'resume',
      payload: { id: 's1' },
    })
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        session_id: 's1',
        messages: [
          { id: 'm1', role: 'user', chunks: ['hello'], done: true, tool_calls: [], tool_results: [] },
        ],
      },
    })
    dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
    dispatchSessionAction({ type: 'SESSION_EVENT', event: 'exit', payload: {} })

    const after = snapshotDir(TUI_ROOT)

    expect(after).toBe(before)
  })
})
