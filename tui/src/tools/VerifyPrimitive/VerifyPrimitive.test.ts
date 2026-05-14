// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — [H1] mismatch_error mis-info guard test (2026-05-04)
//
// Citizen-safety-critical regression test: ensure that a check primitive
// payload carrying ``family: "mismatch_error"`` (e.g. when no auth adapter
// is registered) renders as a rejection — NEVER as the legacy
// ``Result received`` success fallback.
//
// Companion of [C1] in the same dispatch batch (dispatchPrimitive inner-
// payload error classification).

import { test, expect, describe } from 'bun:test'
import { render } from 'ink-testing-library'
import type React from 'react'
import { VerifyPrimitive } from './VerifyPrimitive.js'
import type { Output } from './VerifyPrimitive.js'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderVerify(output: Output, opts: { verbose?: boolean } = {}): string {
  const element = VerifyPrimitive.renderToolResultMessage!(
    output,
    null,
    { verbose: opts.verbose ?? false },
  )
  // CheckPrimitive returns a React element directly (no string short-circuit
  // on the success/error paths exercised here).
  if (typeof element === 'string') return element
  if (element === null || element === undefined) return ''
  const { lastFrame } = render(element as React.ReactElement)
  return lastFrame() ?? ''
}

// ---------------------------------------------------------------------------
// [H1] mismatch_error rejection rendering
// ---------------------------------------------------------------------------

describe('CheckPrimitive renderToolResultMessage — [H1] mismatch_error guard', () => {
  test('dispatcher-classified mismatch_error (ok=false) renders auth-module rejection with message', () => {
    // Shape after dispatchPrimitive [H1] inner-payload classification:
    //   { ok: false, error: { kind: "mismatch_error", message: "..." }, result: <inner> }
    const output: Output = {
      ok: false,
      error: {
        kind: 'mismatch_error',
        message: "No verify adapter registered for family 'gongdong_injeungseo'.",
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Authentication module rejected')
    expect(frame).toContain("No verify adapter registered for family 'gongdong_injeungseo'.")
    // MUST NOT leak the legacy success fallback.
    expect(frame).not.toContain('Result received')
    expect(frame).not.toContain('Verification complete')
  })

  test('dispatcher-classified family_mismatch error (ok=false) also renders auth-module rejection', () => {
    // Defense-in-depth: if a caller only set error.kind = 'family_mismatch'
    // (without 'mismatch_error'), the renderer still surfaces the dedicated
    // auth-module-rejection prefix.
    const output: Output = {
      ok: false,
      error: {
        kind: 'family_mismatch',
        message: 'Family hint mobile_id disagrees with observed evidence.',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Authentication module rejected')
    expect(frame).toContain('Family hint mobile_id disagrees with observed evidence.')
  })

  test('legacy bypass — ok=true with inner family=mismatch_error STILL renders rejection (defense in depth)', () => {
    // If any caller path bypasses the dispatcher classification (older
    // fixture, manual envelope, future regression), the renderer's own
    // ``isMismatchHere`` guard at line ~270 of CheckPrimitive.ts MUST
    // catch it. This test pins that defense — without the guard, the code
    // would fall through to ``String(rawStatus ?? 'Result received')`` = mis-info.
    const output: Output = {
      ok: true,
      result: {
        family: 'mismatch_error',
        reason: 'family_mismatch',
        expected_family: 'gongdong_injeungseo',
        observed_family: '<no_adapter>',
        message:
          "No verify adapter registered for family 'gongdong_injeungseo'. " +
          'Register a mock or live adapter via register_verify_adapter().',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Authentication module rejected')
    expect(frame).toContain("No verify adapter registered for family 'gongdong_injeungseo'.")
    expect(frame).not.toContain('Result received')
    expect(frame).not.toContain('Verification complete')
  })

  test('generic ok=false (non-mismatch) still renders the generic authentication rejection prefix', () => {
    // The original dispatch_error / timeout / citation_missing branches
    // should preserve their existing rendering — only mismatch-class kinds
    // get the auth-module-rejection prefix.
    const output: Output = {
      ok: false,
      error: {
        kind: 'dispatch_error',
        message: 'Backend response timed out (30000ms)',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Authentication rejected')
    expect(frame).not.toContain('Authentication module rejected')
    expect(frame).toContain('Backend response timed out')
  })
})

// ---------------------------------------------------------------------------
// Verified success rendering preserved (regression guard)
// ---------------------------------------------------------------------------

describe('CheckPrimitive renderToolResultMessage — verified success path preserved', () => {
  test('verified status renders Verification result: Verification complete (green)', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'gongdong_injeungseo',
        status: 'verified',
        identity_label: 'Test User',
        korea_tier: 'IA2',
        policy_authority: 'KISA',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Verification result')
    expect(frame).toContain('Verification complete')
    expect(frame).toContain('Source: KISA')
    // MUST NOT leak the rejection-path string.
    expect(frame).not.toContain('Authentication module rejected')
  })

  test('failed status renders Verification failed (red) — distinct from mismatch path', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'gongdong_injeungseo',
        status: 'failed',
        message: 'Cert expired.',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Verification result')
    expect(frame).toContain('Verification failed')
    expect(frame).not.toContain('Authentication module rejected')
  })

  test('pending status renders Verification pending', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'mobile_id',
        status: 'pending',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Verification pending')
  })
})
