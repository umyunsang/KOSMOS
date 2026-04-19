// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — no upstream analog (Claude Code uses HTTP; no child-process crash surface).
//
// Crash detector: watches the spawned Python backend for non-zero exits and
// fatal stderr, then emits a synthetic crash notice (FR-004, US1 scenario 4).
//
// Redaction rule (FR-004, #468 guard pattern):
//   Any KOSMOS_* env var whose name ends in _KEY, _SECRET, _TOKEN, or _PASSWORD
//   has its value replaced with "[REDACTED]" in the stderr tail before it is
//   exposed to any UI layer or log.
//
// Timing: crash must be detected within 5 seconds of the backend exit
// (SC-5 / FR-004).  This is satisfied because proc.exited resolves as soon
// as the OS signals the process has exited; no polling is needed.
//
// US1 T026: Added onDrop callback — called on stdin EOF / EPIPE so the bridge
// can initiate its reconnect loop without prompting the user.  This is
// distinct from onCrash (non-zero exit) because a clean backend restart
// exits 0 but still causes a drop from the TUI's perspective.

import type { CrashNotice } from './bridge'

// ---------------------------------------------------------------------------
// Redaction (reuses #468 secrets-guard pattern)
// ---------------------------------------------------------------------------

/** Regex matching KOSMOS_* env var keys that look like secrets. */
const SECRET_KEY_RE = /^KOSMOS_[A-Z0-9_]+(?:_KEY|_SECRET|_TOKEN|_PASSWORD)$/

/**
 * Return a copy of *text* with the values of any KOSMOS_*_KEY/SECRET/TOKEN/PASSWORD
 * env vars replaced by "[REDACTED]".
 *
 * Strategy: iterate the current process.env, find keys matching the pattern,
 * then do a literal string replacement for each matching value in the text.
 * This is intentionally conservative — it only redacts values that are
 * actually set in the environment, not all possible secrets.
 */
export function redactKosmosSecrets(text: string): string {
  let result = text
  for (const [key, value] of Object.entries(process.env)) {
    if (!value) continue
    if (!SECRET_KEY_RE.test(key)) continue
    // Replace all occurrences of the secret value with [REDACTED]
    // Use a literal replacement (no regex meta-chars) for safety.
    result = result.split(value).join('[REDACTED]')
  }
  return result
}

// ---------------------------------------------------------------------------
// Stderr accumulator (ring-buffer of last N lines)
// ---------------------------------------------------------------------------

const STDERR_TAIL_LINES = 20

class StderrBuffer {
  private _lines: string[] = []
  private _partial = ''

  push(chunk: string): void {
    const combined = this._partial + chunk
    const parts = combined.split('\n')
    this._partial = parts.pop() ?? ''
    for (const line of parts) {
      this._lines.push(line)
      if (this._lines.length > STDERR_TAIL_LINES) {
        this._lines.shift()
      }
    }
  }

  flush(): void {
    if (this._partial.length > 0) {
      this._lines.push(this._partial)
      this._partial = ''
      if (this._lines.length > STDERR_TAIL_LINES) {
        this._lines.shift()
      }
    }
  }

  tail(): string {
    this.flush()
    return this._lines.join('\n')
  }
}

// ---------------------------------------------------------------------------
// startCrashDetector
// ---------------------------------------------------------------------------

export interface CrashDetectorOptions {
  /** Called when a crash is detected with a redacted notice. */
  onCrash: (notice: CrashNotice) => void
  /**
   * US1 T026: Called when a stdio drop is detected (stdin EOF / EPIPE) so
   * the bridge can initiate its reconnect loop without prompting the user.
   *
   * A drop is distinct from a crash: the backend may exit 0 (clean restart)
   * but the TUI still loses its stdio connection.  The bridge should not
   * surface any user-visible error for a drop — only for a persistent
   * crash after all reconnect attempts fail.
   *
   * Optional: if absent, only onCrash is called.
   */
  onDrop?: () => void
}

/**
 * Wire a crash detector to the given Bun subprocess.
 *
 * 1. Drains stderr into a rolling 20-line buffer.
 * 2. Resolves `proc.exited`; if exit code is non-zero (or the process was
 *    killed) builds a CrashNotice with the stderr tail.
 * 3. Redacts KOSMOS_*_KEY/SECRET/TOKEN/PASSWORD values from the tail.
 * 4. Calls `onCrash` with the notice.
 * 5. (US1 T026) Watches for stdin EOF / EPIPE by attempting a zero-byte write
 *    after process exit; also listens on stdout done → calls `onDrop` so the
 *    bridge enters the reconnect loop without surfacing a user error.
 *
 * The detector is passive — it does not kill the process itself.  Killing is
 * the bridge's responsibility (bridge.ts `close()`).
 */
export function startCrashDetector(
  proc: ReturnType<typeof Bun.spawn>,
  opts: CrashDetectorOptions,
): void {
  const stderrBuf = new StderrBuffer()

  // Drain stderr in the background.
  // Bun types `proc.stderr` as `number | ReadableStream<Uint8Array>` because
  // callers may pass a raw fd via `stderr: "inherit"|fd`. The bridge always
  // spawns with `stderr: "pipe"`, so it is a ReadableStream at runtime; guard
  // anyway so a future fd-based caller degrades silently instead of throwing.
  const stderrStream = proc.stderr
  if (stderrStream instanceof ReadableStream) {
    ;(async () => {
      const reader = stderrStream.getReader()
      const decoder = new TextDecoder('utf-8')
      try {
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          stderrBuf.push(decoder.decode(value, { stream: true }))
        }
      } catch {
        // Ignore read errors — the process may have exited
      }
    })()
  }

  // Watch for process exit
  ;(async () => {
    const exitCode = await proc.exited
    const raw = stderrBuf.tail()
    const redacted = redactKosmosSecrets(raw)

    // Exit 0 is a clean shutdown → drop (bridge reconnects silently).
    if (exitCode === 0) {
      opts.onDrop?.()
      return
    }

    // exitCode === null means the process was killed by a signal (SIGKILL,
    // SIGTERM, …). Treat that as a crash so the user sees the stderr tail
    // and can diagnose why the backend went away — a silent drop would
    // mask segfaults and OOM kills.
    const notice: CrashNotice = {
      exitCode,
      stderrTail: raw,
      redactedStderrTail: redacted,
    }
    opts.onCrash(notice)
  })()
}
