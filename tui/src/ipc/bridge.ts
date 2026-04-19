// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — no upstream analog (Claude Code uses HTTP SSE, not stdio JSONL).
//
// IPC Bridge: spawns the Python backend and exposes a typed async interface.
//
// Design decisions:
//   - Uses Bun.spawn() with { stdin: "pipe", stdout: "pipe", stderr: "pipe" }
//     because Bun#4670 blocks extra fds; all IPC must fit on stdin/stdout/stderr.
//   - stdout frames are pushed into a FIFO async queue (no reordering).
//   - DEBUG-level frame logging controlled by KOSMOS_TUI_LOG_LEVEL (FR-010).
//   - crashDetector is wired via crash-detector.ts; this module only exposes
//     the send/close/frames API surface.
//
// FR-054 (fire-and-forget telemetry hook):
//   - Callers may attach bridge.onFrame to observe frame events with latency.
//   - Implementations MUST return synchronously and MUST NOT throw.
//   - If an implementation throws or returns a rejected Promise the bridge
//     swallows the error via a queueMicrotask wrapper so the frame-dispatch
//     loop is never blocked.
//   - OTEL span emission lives in the Python backend (Spec 031 / T121).
//     The TUI surfaces metrics only through this hook + the store subscriber
//     pattern; no opentelemetry-sdk dependency is added to the TUI package.

import { decodeFrames, encodeFrame } from './codec'
import { startCrashDetector } from './crash-detector'
import type { IPCFrame } from './frames.generated'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * FR-054 telemetry hook.
 *
 * Called fire-and-forget after every frame is pushed to the dispatch queue.
 * Implementations MUST:
 *   - return synchronously (or return void — a resolved Promise is fine)
 *   - never throw (errors are caught and logged at WARN level)
 *
 * The hook is invoked inside a queueMicrotask() wrapper so it cannot block
 * the frame-dispatch loop under any circumstances.
 */
export type FrameHook = (
  frame: IPCFrame,
  direction: 'recv' | 'send',
  latencyMs: number,
) => void

export interface BridgeOptions {
  /**
   * Command to spawn.  Defaults to ['uv', 'run', 'kosmos', '--ipc', 'stdio'].
   * Override via KOSMOS_BACKEND_CMD env var (space-split) or this option.
   */
  cmd?: string[]
  /**
   * Milliseconds to wait for the backend process to start before considering
   * it as having crashed.  Default: 5000.
   */
  startupTimeoutMs?: number
  /**
   * Called whenever a crash is detected (non-zero exit or fatal stderr).
   * The bridge emits a synthetic error frame to the store separately via the
   * crash-detector; this hook is for callers who need additional side-effects.
   */
  onCrash?: (notice: CrashNotice) => void
  /**
   * FR-054 fire-and-forget telemetry hook.
   * Invoked in a queueMicrotask after each frame is dispatched or sent.
   * Must not throw; errors are caught and logged at WARN level.
   */
  onFrame?: FrameHook
}

export interface CrashNotice {
  exitCode: number | null
  stderrTail: string
  redactedStderrTail: string
}

export interface IPCBridge {
  /**
   * Send a frame to the Python backend via stdin.
   * Returns false if the backend has already exited.
   */
  send(frame: IPCFrame): boolean
  /**
   * Async iterable of decoded frames from the backend.
   * Yields until the bridge is closed or the process exits.
   */
  frames(): AsyncIterable<IPCFrame>
  /** Gracefully close the bridge (SIGTERM → 3 s → SIGKILL). */
  close(): Promise<void>
  /** Underlying Bun subprocess (for crash detector, tests, etc.) */
  readonly proc: ReturnType<typeof Bun.spawn>
  /**
   * FR-054 fire-and-forget telemetry hook.
   * May be set or replaced at any time after bridge creation.
   * Invoked in a queueMicrotask after each dispatched/sent frame.
   */
  onFrame?: FrameHook
}

// ---------------------------------------------------------------------------
// Log helper (FR-010: KOSMOS_TUI_LOG_LEVEL)
// ---------------------------------------------------------------------------

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'

const _levelOrder: Record<LogLevel, number> = {
  DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3,
}

function _getLogLevel(): LogLevel {
  const raw = (process.env['KOSMOS_TUI_LOG_LEVEL'] ?? 'WARN').toUpperCase()
  if (raw in _levelOrder) return raw as LogLevel
  return 'WARN'
}

function _log(level: LogLevel, ...args: unknown[]): void {
  if (_levelOrder[level] >= _levelOrder[_getLogLevel()]) {
    // Write to stderr so frame logs do not corrupt the IPC protocol on stdout.
    process.stderr.write(`[KOSMOS IPC ${level}] ${args.map(String).join(' ')}\n`)
  }
}

// ---------------------------------------------------------------------------
// Async FIFO queue (single-producer, single-consumer)
// ---------------------------------------------------------------------------

class AsyncQueue<T> {
  private _queue: T[] = []
  private _resolve: ((value: IteratorResult<T>) => void) | null = null
  private _closed = false

  push(item: T): void {
    if (this._closed) return
    if (this._resolve) {
      const r = this._resolve
      this._resolve = null
      r({ value: item, done: false })
    } else {
      this._queue.push(item)
    }
  }

  close(): void {
    this._closed = true
    if (this._resolve) {
      this._resolve({ value: undefined as unknown as T, done: true })
      this._resolve = null
    }
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return {
      next: (): Promise<IteratorResult<T>> => {
        if (this._queue.length > 0) {
          return Promise.resolve({ value: this._queue.shift()!, done: false })
        }
        if (this._closed) {
          return Promise.resolve({ value: undefined as unknown as T, done: true })
        }
        return new Promise((resolve) => {
          this._resolve = resolve
        })
      },
    }
  }
}

// ---------------------------------------------------------------------------
// createBridge
// ---------------------------------------------------------------------------

/**
 * Spawn the Python backend and return an {@link IPCBridge}.
 *
 * The bridge:
 * 1. Resolves the backend command (option > env var > default).
 * 2. Spawns the process with stdio pipes.
 * 3. Starts a stdout reader that splits on `\n` and decodes frames into the
 *    internal FIFO queue.
 * 4. Wires the crash-detector to watch for non-zero exit / fatal stderr.
 * 5. Exposes `send()`, `frames()`, and `close()`.
 */
export function createBridge(opts: BridgeOptions = {}): IPCBridge {
  // Resolve command
  const envCmd = process.env['KOSMOS_BACKEND_CMD']
  const defaultCmd = ['uv', 'run', 'kosmos', '--ipc', 'stdio']
  const cmd: string[] = opts.cmd ?? (envCmd ? envCmd.split(' ') : defaultCmd)

  _log('INFO', `Spawning backend: ${cmd.join(' ')}`)

  const proc = Bun.spawn(cmd, {
    stdin: 'pipe',
    stdout: 'pipe',
    stderr: 'pipe',
  })

  const frameQueue = new AsyncQueue<IPCFrame>()
  let _remainder = ''
  let _closed = false

  // ---- FR-054 fire-and-forget hook dispatcher ----
  // Invokes bridge.onFrame inside queueMicrotask so the caller's hook
  // implementation can never block the frame-dispatch loop, even if it
  // throws synchronously or returns a rejected Promise.
  function _dispatchHook(
    frame: IPCFrame,
    direction: 'recv' | 'send',
    latencyMs: number,
  ): void {
    if (!bridge.onFrame) return
    // Capture reference so replacement between schedule and execute is safe.
    const hook = bridge.onFrame
    queueMicrotask(() => {
      try {
        const result = hook(frame, direction, latencyMs) as unknown
        // Swallow rejected promises to prevent unhandled rejection warnings.
        if (result instanceof Promise) {
          result.catch((e: unknown) => {
            _log('WARN', `onFrame hook rejected: ${e}`)
          })
        }
      } catch (e: unknown) {
        _log('WARN', `onFrame hook threw: ${e}`)
      }
    })
  }

  // ---- stdout reader ----
  ;(async () => {
    const reader = proc.stdout.getReader()
    const decoder = new TextDecoder('utf-8')
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        const t0 = Date.now()
        const chunk = decoder.decode(value, { stream: true })
        const buffered = _remainder + chunk
        const { frames, remainder } = decodeFrames(buffered)
        _remainder = remainder
        for (const result of frames) {
          if (result.ok) {
            _log('DEBUG', `recv kind=${result.frame.kind} session=${result.frame.session_id}`)
            frameQueue.push(result.frame)
            _dispatchHook(result.frame, 'recv', Date.now() - t0)
          } else {
            _log('ERROR', `decode error: ${result.error} | raw=${result.raw.slice(0, 200)}`)
          }
        }
      }
    } catch (e: unknown) {
      _log('WARN', `stdout reader error: ${e}`)
    } finally {
      frameQueue.close()
    }
  })()

  // ---- crash detector ----
  startCrashDetector(proc, {
    onCrash: (notice) => {
      _log('ERROR', `Backend crashed: exitCode=${notice.exitCode}`)
      opts.onCrash?.(notice)
      // Close the frame queue so frames() iterable exits
      frameQueue.close()
    },
  })

  // ---- bridge implementation ----
  const bridge: IPCBridge = {
    proc,
    onFrame: opts.onFrame,

    send(frame: IPCFrame): boolean {
      if (_closed || proc.killed) return false
      try {
        const t0 = Date.now()
        const encoded = encodeFrame(frame)
        _log('DEBUG', `send kind=${frame.kind} session=${frame.session_id}`)
        proc.stdin.write(encoded)
        _dispatchHook(frame, 'send', Date.now() - t0)
        return true
      } catch (e: unknown) {
        _log('WARN', `send error: ${e}`)
        return false
      }
    },

    frames(): AsyncIterable<IPCFrame> {
      return frameQueue
    },

    async close(): Promise<void> {
      if (_closed) return
      _closed = true
      _log('INFO', 'Closing bridge — sending SIGTERM')
      try {
        proc.stdin.end()
        proc.kill('SIGTERM')
        // Wait up to 3 s for graceful exit, then SIGKILL (FR-009)
        const exitPromise = proc.exited
        const timeoutPromise = new Promise<void>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 3000),
        )
        await Promise.race([exitPromise, timeoutPromise]).catch(() => {
          _log('WARN', 'Backend did not exit within 3 s — sending SIGKILL')
          proc.kill('SIGKILL')
        })
      } catch (e: unknown) {
        _log('WARN', `close error: ${e}`)
      }
      frameQueue.close()
    },
  }

  return bridge
}
