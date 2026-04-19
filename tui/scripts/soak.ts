#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// Task T038: soak replay helper.
//
// Replays a JSONL fixture file through the IPC bridge at a configurable rate,
// validating that every frame decodes cleanly and the bridge sustains throughput
// without crashes.
//
// Usage:
//   bun run tui/scripts/soak.ts [options]
//
// Options:
//   --fixture <path>    JSONL fixture file to replay (default: tests/fixtures/soak/default.jsonl)
//   --rate <n>          Events per second (default: KOSMOS_TUI_SOAK_EVENTS_PER_SEC or 100)
//   --duration <n>      Duration in seconds (default: 60; use 600 for the full 10-min soak)
//   --loops <n>         Number of times to loop the fixture (overrides --duration if set)
//
// Exit codes:
//   0 — clean stream (all frames decoded, no crashes, RSS growth within limits)
//   1 — any crash, decode error, or RSS growth > 50 MB

import { parseArgs } from 'node:util'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { decodeFrame } from '../src/ipc/codec'
import { createBridge } from '../src/ipc/bridge'
import type { IPCFrame } from '../src/ipc/frames.generated'

const __dirname = dirname(fileURLToPath(import.meta.url))

// ---------------------------------------------------------------------------
// Arg parsing
// ---------------------------------------------------------------------------

const { values } = parseArgs({
  args: process.argv.slice(2),
  options: {
    fixture: { type: 'string' },
    rate: { type: 'string' },
    duration: { type: 'string' },
    loops: { type: 'string' },
  },
  strict: false,
})

const FIXTURE_PATH =
  values.fixture ??
  join(__dirname, '../tests/fixtures/soak/default.jsonl')

const RATE = parseInt(
  values.rate ?? process.env['KOSMOS_TUI_SOAK_EVENTS_PER_SEC'] ?? '100',
  10,
)

const DURATION_S = values.loops ? null : parseInt(values.duration ?? '60', 10)
const LOOPS = values.loops ? parseInt(values.loops, 10) : null

const INTERVAL_MS = 1000 / RATE
const RSS_LIMIT_MB = 50

// ---------------------------------------------------------------------------
// Load fixture
// ---------------------------------------------------------------------------

if (!existsSync(FIXTURE_PATH)) {
  process.stderr.write(`[soak] fixture not found: ${FIXTURE_PATH}\n`)
  process.exit(1)
}

const lines = readFileSync(FIXTURE_PATH, 'utf-8')
  .split('\n')
  .map(l => l.trim())
  .filter(l => l.length > 0)

if (lines.length === 0) {
  process.stderr.write(`[soak] fixture is empty: ${FIXTURE_PATH}\n`)
  process.exit(1)
}

process.stderr.write(
  `[soak] fixture=${FIXTURE_PATH} lines=${lines.length} rate=${RATE}/s\n`,
)

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

let framesEmitted = 0
let frameErrors = 0
let crashes = 0
const baseRss = process.memoryUsage().rss / (1024 * 1024)
const latencies: number[] = []

// ---------------------------------------------------------------------------
// Bridge setup (no real backend needed — we decode locally to validate frames)
// ---------------------------------------------------------------------------

// For soak purposes we decode the fixture frames locally (they are replayed
// as send() calls on the bridge), then verify the echo responses.
// This tests codec throughput without requiring a live backend.

// We create a bridge pointed at the real backend to test the full path.
// For CI / offline mode, set KOSMOS_BACKEND_CMD=cat to get a trivial echo.
const bridge = createBridge({
  onCrash: () => {
    crashes++
    process.stderr.write(`[soak] CRASH DETECTED\n`)
  },
})

// ---------------------------------------------------------------------------
// Soak loop
// ---------------------------------------------------------------------------

let lineIdx = 0
let loopCount = 0
const startTime = Date.now()

async function runSoak(): Promise<void> {
  const deadline = DURATION_S ? startTime + DURATION_S * 1000 : Infinity
  const maxLoops = LOOPS ?? Infinity

  while (Date.now() < deadline && loopCount < maxLoops) {
    const line = lines[lineIdx % lines.length]!
    lineIdx++

    // Decode locally first
    const t0 = performance.now()
    const result = decodeFrame(line)
    const latencyMs = performance.now() - t0

    if (!result.ok) {
      frameErrors++
      process.stderr.write(`[soak] DECODE ERROR: ${result.error}\n`)
    } else {
      latencies.push(latencyMs)
      framesEmitted++
      // Send to backend
      bridge.send(result.frame)
    }

    // End of one full loop through the fixture
    if (lineIdx % lines.length === 0) {
      loopCount++
    }

    // Rate throttle
    await new Promise(r => setTimeout(r, INTERVAL_MS))
  }
}

// Drain response frames in background
let responsesReceived = 0
;(async () => {
  for await (const _frame of bridge.frames()) {
    responsesReceived++
  }
})()

// Run
await runSoak()
await bridge.close()

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

const durationMs = Date.now() - startTime
const rssGrowthMb = process.memoryUsage().rss / (1024 * 1024) - baseRss

latencies.sort((a, b) => a - b)
const p50 = latencies[Math.floor(latencies.length * 0.5)] ?? 0
const p99 = latencies[Math.floor(latencies.length * 0.99)] ?? 0
const actualRate = (framesEmitted / durationMs) * 1000

process.stderr.write(`
[soak] Results:
  duration:          ${(durationMs / 1000).toFixed(1)} s
  frames emitted:    ${framesEmitted}
  responses:         ${responsesReceived}
  decode errors:     ${frameErrors}
  crashes:           ${crashes}
  actual rate:       ${actualRate.toFixed(1)} ev/s (target ${RATE})
  decode p50:        ${p50.toFixed(2)} ms
  decode p99:        ${p99.toFixed(2)} ms
  RSS growth:        ${rssGrowthMb.toFixed(1)} MB (limit ${RSS_LIMIT_MB} MB)
`)

const ok =
  frameErrors === 0 &&
  crashes === 0 &&
  rssGrowthMb <= RSS_LIMIT_MB

if (!ok) {
  process.stderr.write('[soak] FAIL\n')
  process.exit(1)
}

process.stderr.write('[soak] PASS\n')
process.exit(0)
