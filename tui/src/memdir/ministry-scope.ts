// SPDX-License-Identifier: Apache-2.0
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), task T027
// Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md § 3
//
// Zod mirror of the Python `MinistryScopeAcknowledgment` model.  TUI
// validates records pre-IPC; Python revalidates server-side (fail-closed).

import { z } from 'zod'

export const MINISTRY_CODES = ['KOROAD', 'KMA', 'HIRA', 'NMC'] as const
export type MinistryCode = (typeof MINISTRY_CODES)[number]

export const MinistryOptInSchema = z.object({
  ministry_code: z.enum(MINISTRY_CODES),
  opt_in: z.boolean(),
})

export type MinistryOptIn = z.infer<typeof MinistryOptInSchema>

export const MinistryScopeAcknowledgmentSchema = z.object({
  scope_version: z.string().regex(/^v\d+$/, {
    message: 'scope_version must match /^v\\d+$/',
  }),
  timestamp: z.string().datetime({ offset: false }),
  session_id: z.string().uuid(),
  ministries: z
    .array(MinistryOptInSchema)
    .length(4)
    .refine(
      (arr) => new Set(arr.map((m) => m.ministry_code)).size === 4,
      { message: 'ministries must have 4 unique ministry codes' },
    )
    .refine(
      (arr) => {
        const codes = new Set(arr.map((m) => m.ministry_code))
        return MINISTRY_CODES.every((c) => codes.has(c))
      },
      { message: `ministries must cover ${MINISTRY_CODES.join(', ')}` },
    ),
  schema_version: z.literal('1'),
})

export type MinistryScopeAcknowledgment = z.infer<
  typeof MinistryScopeAcknowledgmentSchema
>

/**
 * Lock-stepped with
 * `src/kosmos/memdir/ministry_scope.py::CURRENT_SCOPE_VERSION`.  Bump
 * both in the same PR.
 */
export const CURRENT_SCOPE_VERSION = 'v1'
