// SPDX-License-Identifier: Apache-2.0
// T024 — Zod mirror tests for PIPAConsentRecord (Epic H #1302).
// Contract: specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md § 3.

import { describe, expect, it } from 'bun:test'
import {
  CURRENT_CONSENT_VERSION,
  PIPAConsentRecordSchema,
} from '../../src/memdir/consent'

const FIXTURE_UUID = '018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60'

function validRecord() {
  return {
    consent_version: CURRENT_CONSENT_VERSION,
    timestamp: '2026-04-20T14:32:05Z',
    aal_gate: 'AAL1' as const,
    session_id: FIXTURE_UUID,
    citizen_confirmed: true as const,
    schema_version: '1' as const,
  }
}

describe('PIPAConsentRecordSchema', () => {
  it('accepts a valid record', () => {
    const result = PIPAConsentRecordSchema.safeParse(validRecord())
    expect(result.success).toBe(true)
  })

  it('rejects a missing citizen_confirmed field', () => {
    const record: Record<string, unknown> = validRecord()
    delete record.citizen_confirmed
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects citizen_confirmed=false', () => {
    const record = { ...validRecord(), citizen_confirmed: false }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a KST timestamp (non-UTC offset)', () => {
    const record = { ...validRecord(), timestamp: '2026-04-20T23:32:05+09:00' }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a consent_version not matching /^v\\d+$/', () => {
    const record = { ...validRecord(), consent_version: '1.0' }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects an aal_gate outside {AAL1, AAL2, AAL3}', () => {
    const record = { ...validRecord(), aal_gate: 'AAL0' as unknown as 'AAL1' }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a malformed UUID for session_id', () => {
    const record = { ...validRecord(), session_id: 'not-a-uuid' }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })

  it('rejects a schema_version other than "1"', () => {
    const record = { ...validRecord(), schema_version: '2' as unknown as '1' }
    const result = PIPAConsentRecordSchema.safeParse(record)
    expect(result.success).toBe(false)
  })
})
