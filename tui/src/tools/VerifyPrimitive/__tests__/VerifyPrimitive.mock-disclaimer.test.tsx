// SPDX-License-Identifier: Apache-2.0
// Audit-2 P0 · CheckPrimitive mock-disclaimer unit tests.
//
// Citizen-safety: mock check results MUST display a Mock prefix and
// "Demo-only result" caveat.
// Live check results MUST NOT show any mock prefix.

import { test, expect, describe } from 'bun:test'
import { render } from 'ink-testing-library'
import type React from 'react'
import { VerifyPrimitive } from '../VerifyPrimitive.js'
import type { Output } from '../VerifyPrimitive.js'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderVerify(output: Output, opts: { verbose?: boolean } = {}): string {
  const element = VerifyPrimitive.renderToolResultMessage!(
    output,
    null,
    { verbose: opts.verbose ?? false },
  )
  if (typeof element === 'string') return element
  if (element === null || element === undefined) return ''
  const { lastFrame } = render(element as React.ReactElement)
  return lastFrame() ?? ''
}

// ---------------------------------------------------------------------------
// Mock path — disclaimer required
// ---------------------------------------------------------------------------

describe('CheckPrimitive renderToolResultMessage — mock disclaimer', () => {
  test('mock check (ok=true, _mode="mock" in result) shows Mock prefix', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'gongdong_injeungseo',
        status: 'verified',
        identity_label: 'Test User',
        korea_tier: 'IA2',
        policy_authority: 'KISA',
        _mode: 'mock',
        _reference_implementation: 'ax-infrastructure-callable-channel',
        _actual_endpoint_when_live: 'https://api.kisa.or.kr/v1/verify',
        _security_wrapping_pattern: 'OID4VP + DPoP',
        _policy_authority: 'https://www.kisa.or.kr/policy',
        _international_reference: 'Singapore APEX',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Mock Verification complete')
    expect(frame).toContain('Demo-only result')
  })

  test('mock check (pending status) shows Mock Verification pending', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'mobile_id',
        status: 'pending',
        _mode: 'mock',
        _reference_implementation: 'ax-infrastructure-callable-channel',
        _actual_endpoint_when_live: 'https://api.mois.go.kr/v1/mobile-id/verify',
        _security_wrapping_pattern: 'mDL ISO/IEC 18013-5',
        _policy_authority: 'https://www.mois.go.kr/policy',
        _international_reference: 'EU EUDI Wallet',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Mock Verification pending')
  })

  test('mock check keeps all rows when preview fits within three rows', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'ganpyeon_injeung',
        status: 'verified',
        _mode: 'mock',
        _reference_implementation: 'ax-infrastructure-callable-channel',
        _actual_endpoint_when_live: 'https://api.mois.go.kr/v1/verify/simple',
        _security_wrapping_pattern: 'OAuth2.1',
        _policy_authority: 'https://www.mois.go.kr/policy',
        _international_reference: 'UK GOV.UK One Login',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Live endpoint: https://api.mois.go.kr/v1/verify/simple')
    expect(frame).not.toContain('...')
  })
})

// ---------------------------------------------------------------------------
// Live path — NO mock disclaimer
// ---------------------------------------------------------------------------

describe('CheckPrimitive renderToolResultMessage — live path (no mock disclaimer)', () => {
  test('live check (no _mode field) shows Verification complete without Mock prefix', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'gongdong_injeungseo',
        status: 'verified',
        identity_label: 'Real User',
        policy_authority: 'KISA',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Verification result')
    expect(frame).toContain('Verification complete')
    expect(frame).not.toContain('Mock')
    expect(frame).not.toContain('Demo-only result')
  })

  test('live check with _mode="live" does NOT show mock disclaimer', () => {
    const output: Output = {
      ok: true,
      result: {
        family: 'gongdong_injeungseo',
        status: 'verified',
        _mode: 'live',
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).not.toContain('Mock')
    expect(frame).not.toContain('Demo-only result')
  })
})

// ---------------------------------------------------------------------------
// Regression guard: mismatch_error path unaffected by mock disclaimer
// ---------------------------------------------------------------------------

describe('CheckPrimitive renderToolResultMessage — mismatch guard unaffected', () => {
  test('[H1] mismatch_error (ok=false) still renders auth-module rejection regardless of mock', () => {
    const output: Output = {
      ok: false,
      error: {
        kind: 'mismatch_error',
        message: "No verify adapter registered for family 'gongdong_injeungseo'.",
      },
    } as unknown as Output

    const frame = renderVerify(output)
    expect(frame).toContain('Authentication module rejected')
    // mock disclaimer is irrelevant for error path
    expect(frame).not.toContain('Verification complete')
  })
})
