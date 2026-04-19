#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 032 T054 (TUI side of Scenario C).
//
// Quickstart § 3.2 companion for `src/kosmos/ipc/demo/upstream_429_probe.py`.
//
// Loads a persisted `BackpressureSignalFrame(signal="throttle", source="upstream_429")`
// from disk (written by the Python probe), validates it through the real
// `IPCFrameSchema` discriminated union, and renders the Korean HUD banner with
// a live retry countdown.
//
// FR-014..016 invariants this probe proves visually:
//   * `hud_copy_ko` / `hud_copy_en` are bilingual strings the TUI can surface.
//   * `retry_after_ms` arrives clamped to [1000, 900000] and feeds the countdown.
//   * Zod validation of `backpressure` arm with `signal="throttle"` succeeds.
//
// Usage::
//
//   bun tui/src/ipc/demo/hud_probe.ts --fixture /tmp/backpressure-throttle.json
//
// Exit codes:
//   0 — banner rendered, countdown completed.
//   1 — fixture missing / schema invalid / wrong kind.
//
// The Ink render loop self-exits once the countdown hits zero so the probe
// returns synchronously to the shell.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import React from 'react'
import { Box, Text, render } from 'ink'

import { IPCFrameSchema, isBackpressureSignal } from '../codec'
import type { BackpressureSignalFrame } from '../frames.generated'

// ---------------------------------------------------------------------------
// CLI parsing
// ---------------------------------------------------------------------------

type Args = {
  fixture: string
  tickMs: number
}

function parseArgs(argv: readonly string[]): Args {
  const parsed: Partial<Args> = {}
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    switch (arg) {
      case '--fixture':
        parsed.fixture = argv[++i]
        break
      case '--tick-ms':
        parsed.tickMs = Number(argv[++i])
        break
      default:
        if (arg?.startsWith('--')) {
          throw new Error(`unknown flag: ${arg}`)
        }
    }
  }
  return {
    fixture: parsed.fixture ?? '/tmp/backpressure-throttle.json',
    tickMs: parsed.tickMs ?? 1000,
  }
}

// ---------------------------------------------------------------------------
// Fixture loader — JSON → Zod validator → discriminated-union narrow
// ---------------------------------------------------------------------------

function loadBackpressureFrame(path: string): BackpressureSignalFrame {
  const absolute = resolve(path)
  let raw: string
  try {
    raw = readFileSync(absolute, 'utf-8')
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    throw new Error(`failed to read fixture ${absolute}: ${msg}`)
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    throw new Error(`fixture ${absolute} is not valid JSON: ${msg}`)
  }

  const result = IPCFrameSchema.safeParse(parsed)
  if (!result.success) {
    throw new Error(`fixture schema mismatch: ${result.error.message}`)
  }
  const frame = result.data
  if (!isBackpressureSignal(frame)) {
    throw new Error(`expected backpressure kind, got kind=${frame.kind}`)
  }
  if (frame.signal !== 'throttle' || frame.source !== 'upstream_429') {
    throw new Error(
      `expected signal=throttle source=upstream_429, got signal=${frame.signal} source=${frame.source}`,
    )
  }
  return frame
}

// ---------------------------------------------------------------------------
// Ink HUD component — Korean banner with live countdown
// ---------------------------------------------------------------------------

type HudProps = {
  frame: BackpressureSignalFrame
  tickMs: number
  onExpired: () => void
}

function HudBanner({ frame, tickMs, onExpired }: HudProps): React.JSX.Element {
  const retryMs = frame.retry_after_ms ?? 0
  const [remainingMs, setRemainingMs] = React.useState(retryMs)

  React.useEffect(() => {
    if (remainingMs <= 0) {
      onExpired()
      return
    }
    const timer = setTimeout(() => {
      setRemainingMs((prev) => Math.max(0, prev - tickMs))
    }, tickMs)
    return () => clearTimeout(timer)
  }, [remainingMs, tickMs, onExpired])

  const remainingS = Math.ceil(remainingMs / 1000)
  // Re-interpolate the countdown into the Korean copy so the banner updates
  // each second rather than freezing on the initial render.
  const koCopy = frame.hud_copy_ko.replace(
    /\d+\s*초/,
    `${remainingS}초`,
  )
  const enCopy = frame.hud_copy_en.replace(
    /\d+s/,
    `${remainingS}s`,
  )

  return React.createElement(
    Box,
    { flexDirection: 'column', borderStyle: 'round', borderColor: 'yellow', paddingX: 1 },
    React.createElement(
      Box,
      null,
      React.createElement(Text, { color: 'yellow', bold: true }, '⚠  부처 API 혼잡 알림'),
    ),
    React.createElement(Text, null, koCopy),
    React.createElement(Text, { dimColor: true }, enCopy),
    React.createElement(
      Box,
      { marginTop: 1 },
      React.createElement(Text, { color: 'cyan' }, `재시도까지: ${remainingS}s`),
    ),
  )
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

function main(argv: readonly string[]): number {
  let args: Args
  try {
    args = parseArgs(argv)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`[hud_probe] bad args: ${msg}`)
    return 1
  }

  let frame: BackpressureSignalFrame
  try {
    frame = loadBackpressureFrame(args.fixture)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`[hud_probe] FAIL: ${msg}`)
    return 1
  }

  let finished = false
  const handleExpired = (): void => {
    if (finished) return
    finished = true
    instance.unmount()
  }

  const instance = render(
    React.createElement(HudBanner, { frame, tickMs: args.tickMs, onExpired: handleExpired }),
  )

  // Block on Ink's wait-until-exit so the Bun process lives through the countdown.
  void instance.waitUntilExit().then(() => {
    console.log('[hud_probe] countdown expired ✓')
  })

  return 0
}

const rc = main(process.argv.slice(2))
if (rc !== 0) process.exit(rc)
