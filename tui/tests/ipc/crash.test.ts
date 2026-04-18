// SPDX-License-Identifier: Apache-2.0
// Task T027: Crash detection test — kill stub backend mid-stream, assert crash
// is detected within 5 s and no KOSMOS_* env var values appear in the redacted
// stderr tail (US1 scenario 4; FR-004, SC-5).

import { describe, expect, test, beforeEach } from 'bun:test'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { redactKosmosSecrets } from '../../src/ipc/crash-detector'

const __dirname = dirname(fileURLToPath(import.meta.url))

const BACKEND_CMD = ['uv', 'run', '--directory', join(__dirname, '../../../'), 'python', '-m', 'kosmos.cli', '--ipc', 'stdio']

// ---------------------------------------------------------------------------
// Unit tests for redactKosmosSecrets
// ---------------------------------------------------------------------------

describe('crash-detector: redactKosmosSecrets', () => {
  test('redacts KOSMOS_*_KEY values', () => {
    const original = process.env['KOSMOS_TEST_REDACT_KEY']
    process.env['KOSMOS_TEST_REDACT_KEY'] = 'super-secret-key-value'
    try {
      const result = redactKosmosSecrets('the key is super-secret-key-value here')
      expect(result).not.toContain('super-secret-key-value')
      expect(result).toContain('[REDACTED]')
    } finally {
      if (original === undefined) {
        delete process.env['KOSMOS_TEST_REDACT_KEY']
      } else {
        process.env['KOSMOS_TEST_REDACT_KEY'] = original
      }
    }
  })

  test('redacts KOSMOS_*_TOKEN values', () => {
    const original = process.env['KOSMOS_TEST_REDACT_TOKEN']
    process.env['KOSMOS_TEST_REDACT_TOKEN'] = 'tok-abc123-secret'
    try {
      const result = redactKosmosSecrets('token: tok-abc123-secret\nother stuff')
      expect(result).not.toContain('tok-abc123-secret')
      expect(result).toContain('[REDACTED]')
    } finally {
      if (original === undefined) {
        delete process.env['KOSMOS_TEST_REDACT_TOKEN']
      } else {
        process.env['KOSMOS_TEST_REDACT_TOKEN'] = original
      }
    }
  })

  test('does NOT redact KOSMOS_TUI_THEME (not a secret key pattern)', () => {
    const original = process.env['KOSMOS_TUI_THEME']
    process.env['KOSMOS_TUI_THEME'] = 'dark'
    try {
      const result = redactKosmosSecrets('theme is dark')
      // 'dark' is a common word — we only redact keys ending in _KEY/_SECRET/_TOKEN/_PASSWORD
      // The actual env value 'dark' should not be replaced unless the key matches the pattern
      expect(result).toBe('theme is dark')
    } finally {
      if (original === undefined) {
        delete process.env['KOSMOS_TUI_THEME']
      } else {
        process.env['KOSMOS_TUI_THEME'] = original
      }
    }
  })

  test('does NOT redact KOSMOS_*_SECRET where value is absent/empty', () => {
    // Empty values are skipped
    const original = process.env['KOSMOS_EMPTY_SECRET']
    process.env['KOSMOS_EMPTY_SECRET'] = ''
    try {
      const result = redactKosmosSecrets('nothing should change here')
      expect(result).toBe('nothing should change here')
    } finally {
      if (original === undefined) {
        delete process.env['KOSMOS_EMPTY_SECRET']
      } else {
        process.env['KOSMOS_EMPTY_SECRET'] = original
      }
    }
  })

  test('plain text without secrets passes through unchanged', () => {
    const result = redactKosmosSecrets('no secrets in this string')
    expect(result).toBe('no secrets in this string')
  })
})

// ---------------------------------------------------------------------------
// Integration: crash detection within 5 s (FR-004, SC-5)
// ---------------------------------------------------------------------------

describe('crash-detector: process crash detection', () => {
  test('non-zero exit is detected within 5 s', async () => {
    // Spawn a backend and then kill it; verify crashDetector fires in time.
    const crashNotices: Array<{ exitCode: number | null; redactedStderrTail: string }> = []

    const { createBridge } = await import('../../src/ipc/bridge')
    const bridge = createBridge({
      cmd: BACKEND_CMD,
      onCrash: (notice) => {
        crashNotices.push(notice)
      },
    })

    // Wait a moment for the process to start
    await new Promise(r => setTimeout(r, 300))

    // Kill the backend abruptly
    bridge.proc.kill('SIGKILL')

    // Wait up to 5 s for crash detection
    const deadline = Date.now() + 5000
    while (crashNotices.length === 0 && Date.now() < deadline) {
      await new Promise(r => setTimeout(r, 100))
    }

    // On SIGKILL, exit code is typically non-zero (signal-terminated).
    // The crash detector should have fired.
    expect(crashNotices.length).toBeGreaterThan(0)

    // Verify redacted tail does not contain any KOSMOS_*_KEY/TOKEN/SECRET/PASSWORD values
    const notice = crashNotices[0]!
    // Inject a test secret and verify it would be redacted from real output
    // (we can only test the redactKosmosSecrets function here; the actual
    // stderr from SIGKILL will be empty or minimal)
    for (const [key, value] of Object.entries(process.env)) {
      if (!value) continue
      if (!/^KOSMOS_[A-Z0-9_]+(?:_KEY|_SECRET|_TOKEN|_PASSWORD)$/.test(key)) continue
      expect(notice.redactedStderrTail).not.toContain(value)
    }

    await bridge.close().catch(() => {})
  })
})
