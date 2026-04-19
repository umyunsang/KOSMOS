#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 032 T053 (TUI side of Scenario B).
//
// Quickstart § 2.2 companion for `src/kosmos/ipc/demo/session_backend.py`.
//
// Drives a single session through the FR-018..025 reconnect handshake:
//
//   1. Spawn the Python backend harness as a child process with piped stdio
//      (`uv run python -m kosmos.ipc.demo.session_backend`).
//   2. Apply the first `--after-frames` (default 20) `assistant_chunk` frames
//      from the backend's stdout, tracking `last_seen_frame_seq`.
//   3. Simulate a stdio drop: read the remaining pre-emitted frames off the
//      pipe and discard them (they are what a dead TUI would have missed).
//   4. Emit a `ResumeRequestFrame` to the backend's stdin with
//      `last_seen_frame_seq` + `tui_session_token`.
//   5. Validate the replay: one `ResumeResponseFrame` (replay_count + 5,
//      resumed_from_frame_seq + 20), 5 buffered `assistant_chunk` frames
//      (frame_seq 20..24), one terminal `PayloadEndFrame(trailer.final=true)`.
//
// Exit codes:
//   0 — handshake succeeded, replay frames applied in order.
//   1 — handshake failed (timeout, schema violation, frame_seq gap, etc.).
//
// Usage::
//
//   bun tui/src/ipc/demo/resume_probe.ts --session s-demo --after-frames 20 \
//       --then kill-stdin

import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

import { decodeFrames, isAssistantChunk, isPayloadEnd, isResumeResponse } from '../codec'
import { encodeFrame } from '../codec'
import { makeBaseEnvelope, makeUUIDv7 } from '../envelope'
import type { DecodeResult } from '../codec'
import type { IPCFrame, ResumeRequestFrame } from '../frames.generated'

// ---------------------------------------------------------------------------
// CLI parsing (no new deps — hand-rolled)
// ---------------------------------------------------------------------------

type Args = {
  session: string
  afterFrames: number
  totalFrames: number
  tuiToken: string
  then: 'kill-stdin'
  timeoutMs: number
}

function parseArgs(argv: readonly string[]): Args {
  const parsed: Partial<Args> = {}
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    switch (arg) {
      case '--session':
        parsed.session = argv[++i]
        break
      case '--after-frames':
        parsed.afterFrames = Number(argv[++i])
        break
      case '--total-frames':
        parsed.totalFrames = Number(argv[++i])
        break
      case '--tui-token':
        parsed.tuiToken = argv[++i]
        break
      case '--then':
        parsed.then = argv[++i] as 'kill-stdin'
        break
      case '--timeout-ms':
        parsed.timeoutMs = Number(argv[++i])
        break
      default:
        if (arg?.startsWith('--')) {
          throw new Error(`unknown flag: ${arg}`)
        }
    }
  }
  return {
    session: parsed.session ?? 's-demo',
    afterFrames: parsed.afterFrames ?? 20,
    totalFrames: parsed.totalFrames ?? 25,
    tuiToken: parsed.tuiToken ?? 'tok-demo',
    then: parsed.then ?? 'kill-stdin',
    timeoutMs: parsed.timeoutMs ?? 10_000,
  }
}

// ---------------------------------------------------------------------------
// Stdout line reader: accumulates chunks, yields DecodeResult entries in order
// ---------------------------------------------------------------------------

class FrameReader {
  private buffer = ''
  private queue: DecodeResult[] = []
  private waiters: Array<(r: DecodeResult | null) => void> = []
  private closed = false

  ingest(chunk: string): void {
    this.buffer += chunk
    const { frames, remainder } = decodeFrames(this.buffer)
    this.buffer = remainder
    for (const frame of frames) {
      this.queue.push(frame)
    }
    this.flushWaiters()
  }

  close(): void {
    this.closed = true
    // Drain any final line that lacks trailing newline.
    if (this.buffer.trim().length > 0) {
      this.ingest('\n')
    }
    this.flushWaiters()
  }

  private flushWaiters(): void {
    while (this.waiters.length > 0 && this.queue.length > 0) {
      const waiter = this.waiters.shift()!
      waiter(this.queue.shift()!)
    }
    if (this.closed && this.waiters.length > 0 && this.queue.length === 0) {
      for (const w of this.waiters) w(null)
      this.waiters = []
    }
  }

  async next(): Promise<DecodeResult | null> {
    if (this.queue.length > 0) return this.queue.shift()!
    if (this.closed) return null
    return new Promise((res) => {
      this.waiters.push(res)
    })
  }
}

// ---------------------------------------------------------------------------
// Frame builders
// ---------------------------------------------------------------------------

function buildResumeRequest(args: Args, lastSeenFrameSeq: number): ResumeRequestFrame {
  const env = makeBaseEnvelope({
    sessionId: args.session,
    correlationId: makeUUIDv7(),
    frameSeq: 0,
  })
  return {
    ...env,
    kind: 'resume_request',
    last_seen_correlation_id: null,
    last_seen_frame_seq: lastSeenFrameSeq,
    tui_session_token: args.tuiToken,
  }
}

// ---------------------------------------------------------------------------
// Main probe flow
// ---------------------------------------------------------------------------

async function readFrameOrFail(
  reader: FrameReader,
  label: string,
  timeoutMs: number,
): Promise<IPCFrame> {
  const timer = new Promise<never>((_, rej) => {
    setTimeout(() => rej(new Error(`timeout waiting for ${label}`)), timeoutMs).unref?.()
  })
  const result = await Promise.race([reader.next(), timer])
  if (result === null) throw new Error(`stdout EOF before ${label}`)
  if (!result.ok) {
    throw new Error(`decode error while awaiting ${label}: ${result.error} | raw=${result.raw}`)
  }
  return result.frame
}

async function main(argv: readonly string[]): Promise<number> {
  const args = parseArgs(argv)

  const repoRoot = resolve(import.meta.dir, '../../../..')
  const child = spawn(
    'uv',
    [
      'run',
      'python',
      '-m',
      'kosmos.ipc.demo.session_backend',
      '--session-id',
      args.session,
      '--total-frames',
      String(args.totalFrames),
      '--after-frames',
      String(args.afterFrames),
      '--tui-token',
      args.tuiToken,
    ],
    {
      cwd: repoRoot,
      stdio: ['pipe', 'pipe', 'inherit'],
    },
  )

  const reader = new FrameReader()
  child.stdout!.setEncoding('utf8')
  child.stdout!.on('data', (chunk: string) => reader.ingest(chunk))
  child.stdout!.on('end', () => reader.close())

  try {
    // Phase 1: apply the first --after-frames assistant_chunk frames.
    let lastSeen = -1
    for (let expected = 0; expected < args.afterFrames; expected++) {
      const frame = await readFrameOrFail(reader, `assistant_chunk #${expected}`, args.timeoutMs)
      if (!isAssistantChunk(frame)) {
        throw new Error(`expected assistant_chunk at frame_seq=${expected}, got kind=${frame.kind}`)
      }
      if (frame.frame_seq !== expected) {
        throw new Error(
          `frame_seq gap: expected ${expected}, got ${frame.frame_seq} (role=${frame.role})`,
        )
      }
      lastSeen = frame.frame_seq
    }
    console.log(
      `[probe] applied ${args.afterFrames} frames (frame_seq 0..${args.afterFrames - 1})`,
    )

    // Phase 2: simulate a stdio drop.  The backend has already emitted the
    // remaining frames; drain + discard them so they represent what a dead
    // TUI would have missed.
    const expectedReplay = args.totalFrames - args.afterFrames
    for (let i = 0; i < expectedReplay; i++) {
      await readFrameOrFail(reader, `drain #${i}`, args.timeoutMs)
    }
    console.log('[probe] stdin closed; reconnecting …')

    // Phase 3: emit ResumeRequestFrame on the backend's stdin.
    const request = buildResumeRequest(args, lastSeen)
    child.stdin!.write(encodeFrame(request))
    console.log(`[probe] sent resume_request (last_seen_frame_seq=${lastSeen})`)

    // Phase 4: consume the handshake response.
    const response = await readFrameOrFail(reader, 'resume_response', args.timeoutMs)
    if (!isResumeResponse(response)) {
      throw new Error(`expected resume_response, got kind=${response.kind}`)
    }
    if (response.replay_count !== expectedReplay) {
      throw new Error(
        `replay_count mismatch: expected ${expectedReplay}, got ${response.replay_count}`,
      )
    }
    if (response.resumed_from_frame_seq !== lastSeen + 1) {
      throw new Error(
        `resumed_from_frame_seq mismatch: expected ${lastSeen + 1}, got ${response.resumed_from_frame_seq}`,
      )
    }
    console.log(
      `[probe] received resume_response (replay_count=${response.replay_count}, resumed_from_frame_seq=${response.resumed_from_frame_seq})`,
    )

    // Phase 5: validate replay frames in order.
    for (let offset = 0; offset < expectedReplay; offset++) {
      const expectedSeq = lastSeen + 1 + offset
      const frame = await readFrameOrFail(reader, `replay #${offset}`, args.timeoutMs)
      if (!isAssistantChunk(frame)) {
        throw new Error(`expected replayed assistant_chunk, got kind=${frame.kind}`)
      }
      if (frame.frame_seq !== expectedSeq) {
        throw new Error(
          `replay frame_seq gap: expected ${expectedSeq}, got ${frame.frame_seq}`,
        )
      }
    }
    console.log(
      `[probe] applied ${expectedReplay} replayed frames (frame_seq ${lastSeen + 1}..${lastSeen + expectedReplay})`,
    )

    // Phase 6: terminal payload_end with trailer.final = true.
    const terminal = await readFrameOrFail(reader, 'payload_end', args.timeoutMs)
    if (!isPayloadEnd(terminal)) {
      throw new Error(`expected payload_end, got kind=${terminal.kind}`)
    }
    if (terminal.trailer?.final !== true) {
      throw new Error('payload_end missing trailer.final=true (E6 violation)')
    }

    console.log('[probe] session recovered ✓')

    // Phase 7: close stdin → backend EOF → child exits 0.
    child.stdin!.end()
    const exitCode: number = await new Promise((res) => {
      child.once('exit', (code) => res(code ?? 0))
    })
    if (exitCode !== 0) {
      throw new Error(`backend exited non-zero: ${exitCode}`)
    }
    return 0
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`[probe] FAIL: ${msg}`)
    try {
      child.kill('SIGTERM')
    } catch {}
    return 1
  }
}

const rc = await main(process.argv.slice(2))
process.exit(rc)
