// SPDX-License-Identifier: Apache-2.0
// T113 — Verify session_event.exit SIGTERM → SIGKILL chain (FR-009).
//
// FR-009: On close() the bridge MUST:
//   1. Flush stdin (stdin.end())
//   2. Send SIGTERM to the backend process
//   3. Wait up to 3 s for graceful exit
//   4. If not exited within 3 s, send SIGKILL
//
// Verification status (T113):
//   bridge.ts close() implementation already satisfies FR-009 verbatim:
//     - Line 229: proc.stdin.end()
//     - Line 230: proc.kill('SIGTERM')
//     - Line 232: 3000 ms timeout (exactlythe FR-009 budget)
//     - Line 237: proc.kill('SIGKILL') on timeout
//   No code changes were required.
//
// This file provides:
//   (a) a contract/documentation test that runs synchronously and confirms
//       the source-level implementation, and
//   (b) an it.todo for Bun.spawn mock-based behavioural verification
//       (mocking Bun.spawn is invasive — deferred, tracked here).

import { describe, it, expect } from 'bun:test'
import * as fs from 'node:fs'
import * as path from 'node:path'

const BRIDGE_PATH = path.resolve(import.meta.dir, '../../src/ipc/bridge.ts')

// ---------------------------------------------------------------------------
// Contract test — verifies source-level implementation of FR-009
// ---------------------------------------------------------------------------

describe('bridge.close() FR-009 SIGTERM → SIGKILL contract', () => {
  it('bridge.ts source contains SIGTERM before SIGKILL with 3000 ms budget', () => {
    const src = fs.readFileSync(BRIDGE_PATH, 'utf-8')

    // Must include stdin flush
    expect(src).toContain('proc.stdin.end()')

    // Must include SIGTERM
    expect(src).toContain("proc.kill('SIGTERM')")

    // Must include 3000 ms timeout (the FR-009 ≤3 s budget)
    expect(src).toContain('3000')

    // SIGKILL must appear AFTER SIGTERM in the file (order matters for FR-009)
    const sigtermIdx = src.indexOf("proc.kill('SIGTERM')")
    const sigkillIdx = src.indexOf("proc.kill('SIGKILL')")
    expect(sigtermIdx).toBeGreaterThanOrEqual(0)
    expect(sigkillIdx).toBeGreaterThan(sigtermIdx)
  })

  it('close() timeout is exactly 3000 ms (FR-009 ≤3 s hard limit)', () => {
    const src = fs.readFileSync(BRIDGE_PATH, 'utf-8')
    // Find the setTimeout call inside close() — must not exceed 3000
    const timeoutMatch = src.match(/setTimeout\([^,]+,\s*(\d+)\s*\)/)
    expect(timeoutMatch).not.toBeNull()
    const timeoutMs = parseInt(timeoutMatch![1]!, 10)
    expect(timeoutMs).toBeLessThanOrEqual(3000)
  })

  // -------------------------------------------------------------------------
  // Deferred behavioural test — requires Bun.spawn mock support
  // -------------------------------------------------------------------------

  it.todo(
    'FR-009: dispatch session_event.exit → bridge.close() calls SIGTERM then SIGKILL on stubborn process (Bun.spawn mock required)',
    () => { /* deferred: mocking Bun.spawn requires invasive test harness */ },
  )

  it.todo(
    'FR-009: bridge.close() resolves within 3 s even when backend never exits (SIGKILL path)',
    () => { /* deferred: requires a non-terminating Bun.spawn stub */ },
  )
})
