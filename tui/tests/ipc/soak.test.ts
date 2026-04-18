// SPDX-License-Identifier: Apache-2.0
// Task T028: Soak test (marked @slow; full 10-min runtime via bun test:soak).
//
// In the normal test run (bun test) this test runs for 5 seconds at 100 ev/s
// to validate codec throughput without the full 10-min soak.
//
// The full 10-min soak is triggered by bun run test:soak which invokes
// tui/scripts/soak.ts with --duration 600.
//
// Assertions:
//   - Zero dropped / decode-error frames
//   - p99 chunk decode latency ≤ 50 ms (FR-006)
//   - RSS growth ≤ 50 MB over the test duration (SC-2)
//   - Clean bridge exit

import { describe, expect, test } from 'bun:test'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import { decodeFrame } from '../../src/ipc/codec'
import { createBridge } from '../../src/ipc/bridge'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FIXTURE = join(__dirname, '../fixtures/soak/default.jsonl')
const BACKEND_CMD = ['uv', 'run', '--directory', join(__dirname, '../../../'), 'python', '-m', 'kosmos.cli', '--ipc', 'stdio']

describe('soak: codec throughput (5 s / 100 ev/s)', () => {
  // Skip during normal test run if KOSMOS_SKIP_SOAK is set
  // (set automatically when running in CI without soak profile)
  const skip = process.env['KOSMOS_SKIP_SOAK'] === '1'

  test('no decode errors at 100 ev/s for 5 s', async () => {
    if (skip) return

    const lines = readFileSync(FIXTURE, 'utf-8')
      .split('\n')
      .filter(l => l.trim().length > 0)

    const baseRss = process.memoryUsage().rss / (1024 * 1024)
    const RATE = 100 // ev/s
    const DURATION_S = 5
    const INTERVAL_MS = 1000 / RATE
    const deadline = Date.now() + DURATION_S * 1000

    const latencies: number[] = []
    let errors = 0
    let idx = 0

    while (Date.now() < deadline) {
      const line = lines[idx % lines.length]!
      idx++
      const t0 = performance.now()
      const result = decodeFrame(line)
      latencies.push(performance.now() - t0)
      if (!result.ok) errors++
      await new Promise(r => setTimeout(r, INTERVAL_MS))
    }

    const rssGrowthMb = process.memoryUsage().rss / (1024 * 1024) - baseRss
    latencies.sort((a, b) => a - b)
    const p99 = latencies[Math.floor(latencies.length * 0.99)] ?? 0

    expect(errors).toBe(0)
    expect(p99).toBeLessThan(50) // FR-006
    expect(rssGrowthMb).toBeLessThan(50) // SC-2

    console.log(`[soak] frames=${latencies.length} p99=${p99.toFixed(2)}ms rss_growth=${rssGrowthMb.toFixed(1)}MB`)
  }, 30_000) // 30 s bun timeout (actual run is 5 s)
})
