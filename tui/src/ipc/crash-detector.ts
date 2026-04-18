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
}

/**
 * Wire a crash detector to the given Bun subprocess.
 *
 * 1. Drains stderr into a rolling 20-line buffer.
 * 2. Resolves `proc.exited`; if exit code is non-zero (or the process was
 *    killed) builds a CrashNotice with the stderr tail.
 * 3. Redacts KOSMOS_*_KEY/SECRET/TOKEN/PASSWORD values from the tail.
 * 4. Calls `onCrash` with the notice.
 *
 * The detector is passive — it does not kill the process itself.  Killing is
 * the bridge's responsibility (bridge.ts `close()`).
 */
export function startCrashDetector(
  proc: ReturnType<typeof Bun.spawn>,
  opts: CrashDetectorOptions,
): void {
  const stderrBuf = new StderrBuffer()

  // Drain stderr in the background
  ;(async () => {
    const reader = proc.stderr.getReader()
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

  // Watch for process exit
  ;(async () => {
    const exitCode = await proc.exited
    const raw = stderrBuf.tail()
    const redacted = redactKosmosSecrets(raw)

    // Exit 0 is clean shutdown — no crash notice needed.
    // Exit null means the process is still running (should not happen here).
    if (exitCode === 0 || exitCode === null) return

    const notice: CrashNotice = {
      exitCode,
      stderrTail: raw,
      redactedStderrTail: redacted,
    }
    opts.onCrash(notice)
  })()
}
