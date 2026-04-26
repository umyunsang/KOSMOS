/**
 * Spec 1978 Phase 5 — AuthContextDisplay render tests (T064, T066).
 *
 * Asserts that the AuthContextDisplay component renders all required fields
 * for a gongdong_injeungseo context and does not crash on missing optional fields.
 */
import { describe, test, expect } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ThemeProvider } from '@/theme/provider'
import { AuthContextDisplay, type AuthContext } from '@/components/verify/AuthContextDisplay'

function wrap(element: React.ReactElement): React.ReactElement {
  return <ThemeProvider>{element}</ThemeProvider>
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const gongdongContext: AuthContext = {
  family: 'gongdong_injeungseo',
  published_tier: 'gongdong_injeungseo_personal_aal3',
  nist_aal_hint: 'AAL3',
  verified_at: '2026-04-27T12:00:00Z',
  certificate_issuer: 'KICA',
}

const minimalContext: AuthContext = {
  family: 'digital_onepass',
  published_tier: 'digital_onepass_level2_aal2',
  nist_aal_hint: 'AAL2',
  // No verified_at, no extra fields — tests crash-resistance
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuthContextDisplay', () => {
  test('renders family name (공동인증서) for gongdong_injeungseo', () => {
    const { lastFrame } = render(wrap(<AuthContextDisplay context={gongdongContext} />))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('공동인증서')
  })

  test('renders published_tier', () => {
    const { lastFrame } = render(wrap(<AuthContextDisplay context={gongdongContext} />))
    const frame = lastFrame() ?? ''
    expect(frame).toContain(gongdongContext.published_tier)
  })

  test('renders nist_aal_hint', () => {
    const { lastFrame } = render(wrap(<AuthContextDisplay context={gongdongContext} />))
    const frame = lastFrame() ?? ''
    expect(frame).toContain(gongdongContext.nist_aal_hint)
  })

  test('renders family-specific certificate_issuer field', () => {
    const { lastFrame } = render(wrap(<AuthContextDisplay context={gongdongContext} />))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('certificate_issuer')
    expect(frame).toContain('KICA')
  })

  test('does not crash on minimal context (no optional fields)', () => {
    expect(() => {
      const { lastFrame } = render(wrap(<AuthContextDisplay context={minimalContext} />))
      const frame = lastFrame() ?? ''
      expect(frame).toContain('Digital Onepass')
      expect(frame).toContain('AAL2')
    }).not.toThrow()
  })
})
