// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T037 (partial)
// bun:test units for ReceiptToast (FR-018).
//
// Covers:
//   - 'issued' variant shows receipt ID
//   - 'revoked' variant shows revoke message with ID
//   - 'already_revoked' variant shows idempotent message (no ID expected)

import { describe, test, expect } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ReceiptToast } from '../../../src/components/permissions/ReceiptToast'

describe('ReceiptToast — FR-018', () => {
  test('issued variant renders receipt ID', () => {
    const { lastFrame } = render(
      <ReceiptToast variant="issued" receiptId="rcpt-abc12345" />,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('rcpt-abc12345')
  })

  test('issued variant contains brand glyph ✻', () => {
    const { lastFrame } = render(
      <ReceiptToast variant="issued" receiptId="rcpt-abc12345" />,
    )
    expect(lastFrame()).toContain('✻')
  })

  test('revoked variant renders receipt ID', () => {
    const { lastFrame } = render(
      <ReceiptToast variant="revoked" receiptId="rcpt-xyz99999" />,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain('rcpt-xyz99999')
  })

  test('already_revoked variant renders without ID', () => {
    const { lastFrame } = render(<ReceiptToast variant="already_revoked" />)
    const frame = lastFrame() ?? ''
    // Should contain the "already revoked" message (Korean or English)
    expect(
      frame.includes('이미 철회됨') || frame.includes('Already revoked'),
    ).toBe(true)
  })
})
