// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T038
// bun:test units for /consent list ordering and revoke idempotency (FR-019/020/021).
//
// Covers:
//   - buildConsentListRows: reverse chronological order (FR-019)
//   - buildConsentListRows: empty array
//   - formatConsentListRow: expected columns
//   - parseConsentArgs: 'list', 'revoke rcpt-<id>', unknown
//   - executeConsentRevoke: first revoke → 'revoked'
//   - executeConsentRevoke: second revoke → 'already_revoked' (FR-021 idempotent)
//   - executeConsentRevoke: unknown ID → 'not_found'
//   - executeConsentRevoke: invalid format → 'invalid_id'

import { describe, test, expect } from 'bun:test'
import {
  buildConsentListRows,
  formatConsentListRow,
  executeConsentRevoke,
  parseConsentArgs,
  type ConsentListRow,
} from '../../src/commands/consent'
import type { PermissionReceiptT } from '../../src/schemas/ui-l2/permission'
import type { PermissionReceiptContextValue } from '../../src/context/PermissionReceiptContext'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeReceipt(
  id: string,
  ts: string,
  layer: 1 | 2 | 3 = 2,
  revokedAt: string | null = null,
): PermissionReceiptT {
  return {
    receipt_id: id,
    layer,
    tool_name: 'test_tool',
    decision: 'allow_once',
    decided_at: ts,
    session_id: 'sess-01',
    revoked_at: revokedAt,
  }
}

// ---------------------------------------------------------------------------
// buildConsentListRows — FR-019 ordering
// ---------------------------------------------------------------------------

describe('buildConsentListRows — reverse chronological order (FR-019)', () => {
  test('returns empty array when no receipts', () => {
    expect(buildConsentListRows([])).toEqual([])
  })

  test('single receipt passes through unchanged', () => {
    const r = makeReceipt('rcpt-aaaaaaaa', '2026-04-25T10:00:00.000Z')
    const rows = buildConsentListRows([r])
    expect(rows).toHaveLength(1)
    expect(rows[0]?.receipt_id).toBe('rcpt-aaaaaaaa')
  })

  test('returns newest receipt first (reverse chrono)', () => {
    const older = makeReceipt('rcpt-aaaaaaaa', '2026-04-25T09:00:00.000Z')
    const newer = makeReceipt('rcpt-bbbbbbbb', '2026-04-25T10:00:00.000Z')
    // Pass in chronological order
    const rows = buildConsentListRows([older, newer])
    expect(rows[0]?.receipt_id).toBe('rcpt-bbbbbbbb') // newest first
    expect(rows[1]?.receipt_id).toBe('rcpt-aaaaaaaa')
  })

  test('three receipts in arbitrary order → sorted newest first', () => {
    const receipts = [
      makeReceipt('rcpt-cccccccc', '2026-04-25T08:00:00.000Z'),
      makeReceipt('rcpt-aaaaaaaa', '2026-04-25T10:00:00.000Z'),
      makeReceipt('rcpt-bbbbbbbb', '2026-04-25T09:00:00.000Z'),
    ]
    const rows = buildConsentListRows(receipts)
    expect(rows[0]?.receipt_id).toBe('rcpt-aaaaaaaa')
    expect(rows[1]?.receipt_id).toBe('rcpt-bbbbbbbb')
    expect(rows[2]?.receipt_id).toBe('rcpt-cccccccc')
  })

  test('does not mutate the input array', () => {
    const receipts = [
      makeReceipt('rcpt-cccccccc', '2026-04-25T08:00:00.000Z'),
      makeReceipt('rcpt-aaaaaaaa', '2026-04-25T10:00:00.000Z'),
    ]
    const original = [...receipts]
    buildConsentListRows(receipts)
    // Original order must be preserved
    expect(receipts[0]?.receipt_id).toBe(original[0]?.receipt_id)
    expect(receipts[1]?.receipt_id).toBe(original[1]?.receipt_id)
  })
})

// ---------------------------------------------------------------------------
// formatConsentListRow
// ---------------------------------------------------------------------------

describe('formatConsentListRow', () => {
  test('contains all five columns', () => {
    const row: ConsentListRow = {
      receipt_id: 'rcpt-abc12345',
      layer: 2,
      tool_name: 'hira_search',
      decision: 'allow_once',
      decided_at: '2026-04-25T10:30:00.000Z',
      revoked_at: null,
    }
    const line = formatConsentListRow(row)
    expect(line).toContain('rcpt-abc12345')
    expect(line).toContain('L2')
    expect(line).toContain('hira_search')
    expect(line).toContain('allow_once')
    expect(line).toContain('2026-04-25')
  })

  test('revoked receipt has [REVOKED] suffix', () => {
    const row: ConsentListRow = {
      receipt_id: 'rcpt-abc12345',
      layer: 2,
      tool_name: 'test_tool',
      decision: 'allow_session',
      decided_at: '2026-04-25T10:30:00.000Z',
      revoked_at: '2026-04-25T11:00:00.000Z',
    }
    expect(formatConsentListRow(row)).toContain('[REVOKED]')
  })
})

// ---------------------------------------------------------------------------
// parseConsentArgs
// ---------------------------------------------------------------------------

describe('parseConsentArgs', () => {
  test('"list" → sub: list', () => {
    expect(parseConsentArgs('list')).toEqual({ sub: 'list' })
  })

  test('"revoke rcpt-abc12345" → sub: revoke + receiptId', () => {
    const result = parseConsentArgs('revoke rcpt-abc12345')
    expect(result).toEqual({ sub: 'revoke', receiptId: 'rcpt-abc12345' })
  })

  test('revoke with long ID', () => {
    const result = parseConsentArgs('revoke rcpt-01943af2-5e27-72b5-abcd-ef1234567890')
    expect(result).toEqual({
      sub: 'revoke',
      receiptId: 'rcpt-01943af2-5e27-72b5-abcd-ef1234567890',
    })
  })

  test('unknown subcommand → sub: unknown', () => {
    const result = parseConsentArgs('delete all')
    expect(result).toEqual({ sub: 'unknown', raw: 'delete all' })
  })

  test('empty string → sub: unknown', () => {
    const result = parseConsentArgs('')
    expect(result).toEqual({ sub: 'unknown', raw: '' })
  })
})

// ---------------------------------------------------------------------------
// executeConsentRevoke — FR-020/021 idempotency
// ---------------------------------------------------------------------------

describe('executeConsentRevoke — FR-021 idempotency', () => {
  function makeCtx(outcome: 'revoked' | 'already_revoked' | 'not_found'): Pick<
    PermissionReceiptContextValue,
    'revokeReceipt'
  > {
    return {
      revokeReceipt: () => outcome,
    }
  }

  test('valid ID + first revoke → {kind: revoked}', () => {
    const ctx = makeCtx('revoked')
    const result = executeConsentRevoke('rcpt-abc12345', ctx)
    expect(result).toEqual({ kind: 'revoked', receiptId: 'rcpt-abc12345' })
  })

  test('valid ID + already revoked → {kind: already_revoked} (FR-021)', () => {
    const ctx = makeCtx('already_revoked')
    const result = executeConsentRevoke('rcpt-abc12345', ctx)
    expect(result).toEqual({ kind: 'already_revoked', receiptId: 'rcpt-abc12345' })
  })

  test('valid ID + not found → {kind: not_found}', () => {
    const ctx = makeCtx('not_found')
    const result = executeConsentRevoke('rcpt-zzzzzzzz', ctx)
    expect(result).toEqual({ kind: 'not_found', receiptId: 'rcpt-zzzzzzzz' })
  })

  test('invalid format → {kind: invalid_id}', () => {
    const ctx = makeCtx('revoked')
    const result = executeConsentRevoke('bad-format', ctx)
    expect(result).toEqual({ kind: 'invalid_id' })
  })

  test('short ID (7 chars after rcpt-) → {kind: invalid_id}', () => {
    const ctx = makeCtx('revoked')
    // 7 chars is one short of the minimum 8
    const result = executeConsentRevoke('rcpt-abcdefg', ctx)
    expect(result).toEqual({ kind: 'invalid_id' })
  })

  test('ID with exactly 8 chars after rcpt- is valid', () => {
    const ctx = makeCtx('revoked')
    const result = executeConsentRevoke('rcpt-abcdefgh', ctx)
    expect(result).toEqual({ kind: 'revoked', receiptId: 'rcpt-abcdefgh' })
  })
})

// ---------------------------------------------------------------------------
// PermissionReceiptContext in-memory revoke (integration-level unit test)
// ---------------------------------------------------------------------------

describe('PermissionReceiptContext revokeReceipt — idempotency (FR-021)', () => {
  // Test the revokeReceipt logic inline without React context
  function makeSimpleStore(): {
    receipts: PermissionReceiptT[]
    revokeReceipt: (id: string) => 'revoked' | 'already_revoked' | 'not_found'
  } {
    const receipts: PermissionReceiptT[] = []
    return {
      receipts,
      revokeReceipt(id: string) {
        const idx = receipts.findIndex((r) => r.receipt_id === id)
        if (idx === -1) return 'not_found'
        const existing = receipts[idx]!
        if (existing.revoked_at !== null) return 'already_revoked'
        receipts[idx] = { ...existing, revoked_at: new Date().toISOString() }
        return 'revoked'
      },
    }
  }

  test('first revoke → revoked, sets revoked_at', () => {
    const store = makeSimpleStore()
    store.receipts.push(makeReceipt('rcpt-testtest', '2026-04-25T10:00:00.000Z'))
    expect(store.revokeReceipt('rcpt-testtest')).toBe('revoked')
    expect(store.receipts[0]?.revoked_at).not.toBeNull()
  })

  test('second revoke → already_revoked, no new mutation (FR-021)', () => {
    const store = makeSimpleStore()
    store.receipts.push(makeReceipt('rcpt-testtest', '2026-04-25T10:00:00.000Z'))
    store.revokeReceipt('rcpt-testtest')
    const firstRevokedAt = store.receipts[0]?.revoked_at

    // Second call must not create a new entry or change revoked_at
    expect(store.revokeReceipt('rcpt-testtest')).toBe('already_revoked')
    expect(store.receipts[0]?.revoked_at).toBe(firstRevokedAt)
    expect(store.receipts).toHaveLength(1) // no new record appended
  })

  test('unknown ID → not_found', () => {
    const store = makeSimpleStore()
    expect(store.revokeReceipt('rcpt-unknownx')).toBe('not_found')
  })
})
