// SPDX-License-Identifier: Apache-2.0
// T032 — Zod mirror tests for MinistryScopeAcknowledgment (Epic H #1302).
// Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md § 3.

import { describe, expect, it } from 'bun:test'
import {
  CURRENT_SCOPE_VERSION,
  MinistryScopeAcknowledgmentSchema,
} from '../../src/memdir/ministry-scope'

const SESSION = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

function validRecord() {
  return {
    scope_version: CURRENT_SCOPE_VERSION,
    timestamp: '2026-04-20T14:33:17Z',
    session_id: SESSION,
    ministries: [
      { ministry_code: 'KOROAD', opt_in: true },
      { ministry_code: 'KMA', opt_in: true },
      { ministry_code: 'HIRA', opt_in: false },
      { ministry_code: 'NMC', opt_in: false },
    ],
    schema_version: '1' as const,
  }
}

describe('MinistryScopeAcknowledgmentSchema', () => {
  it('accepts a valid 4-ministry record', () => {
    const result = MinistryScopeAcknowledgmentSchema.safeParse(validRecord())
    expect(result.success).toBe(true)
  })

  it('rejects a 3-item ministries array', () => {
    const record = validRecord()
    record.ministries = record.ministries.slice(0, 3)
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a 5-item ministries array', () => {
    const record = validRecord() as {
      ministries: Array<{ ministry_code: string; opt_in: boolean }>
      [key: string]: unknown
    }
    record.ministries = [
      ...record.ministries,
      { ministry_code: 'KOROAD', opt_in: true },
    ]
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects duplicate ministry codes (uniqueness refine)', () => {
    const record = validRecord()
    record.ministries[1] = { ministry_code: 'KOROAD', opt_in: true }
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects missing coverage of all four codes', () => {
    // Swap NMC for an extra HIRA — same length (4), unique codes are now only 3.
    const record = validRecord()
    record.ministries[3] = { ministry_code: 'HIRA' as const, opt_in: true }
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a non-UTC timestamp', () => {
    const record = { ...validRecord(), timestamp: '2026-04-20T23:33:17+09:00' }
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects scope_version not matching /^v\\d+$/', () => {
    const record = { ...validRecord(), scope_version: '1.0' }
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects an invalid UUID', () => {
    const record = { ...validRecord(), session_id: 'not-a-uuid' }
    const result = MinistryScopeAcknowledgmentSchema.safeParse(record)
    expect(result.success).toBe(false)
  })
})
