// SPDX-License-Identifier: Apache-2.0
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), task T020
// Contract: specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md § 3
//
// Zod mirror of the Python `PIPAConsentRecord` model (src/kosmos/memdir/
// user_consent.py).  The TUI validates records at write-time before handing
// them over to the Python backend via stdio IPC; the Python side revalidates
// with Pydantic as a second-layer guard per fail-closed security principle.

import { z } from 'zod'

export const PIPAConsentRecordSchema = z.object({
  consent_version: z.string().regex(/^v\d+$/, {
    message: 'consent_version must match /^v\\d+$/',
  }),
  // `offset: false` rejects `+09:00`-style offsets — only `Z`-suffixed UTC
  // is accepted per contract § 3.
  timestamp: z.string().datetime({ offset: false }),
  aal_gate: z.enum(['AAL1', 'AAL2', 'AAL3']),
  session_id: z.string().uuid(),
  citizen_confirmed: z.literal(true),
  schema_version: z.literal('1'),
})

export type PIPAConsentRecord = z.infer<typeof PIPAConsentRecordSchema>

/**
 * Version constant kept in lock-step with
 * `src/kosmos/memdir/user_consent.py::CURRENT_CONSENT_VERSION`.  Bump both
 * in the same PR.
 */
export const CURRENT_CONSENT_VERSION = 'v1'
