// SPDX-License-Identifier: Apache-2.0
//
// DO NOT IMPORT THIS FILE FROM RUNTIME CODE.
//
// Spec 2642 / Epic F · S7 / US3 — negative-fixture for the
// codec.ts ↔ Python `_BaseFrame` envelope parity gate.
//
// `tests/ipc/test_codec_envelope_parity.py` reads this file when the
// env-var ``UMMAYA_IPC_PARITY_DRIFT_FIXTURE=1`` is set; the parity
// check MUST fail on `correlation_id` because this fixture has been
// intentionally drifted: `correlation_id` is declared optional +
// nullable here, while the canonical Pydantic `_BaseFrame` requires
// it (with min_length=1).
//
// `tests/ipc/conftest.py` enforces ``UMMAYA_IPC_PARITY_DRIFT_FIXTURE``
// is unset by default; only the dedicated negative-test opts in via
// `monkeypatch.setenv`.

import { z } from 'zod'

// Match the same `BaseFrame = z.object({...})` anchor the parity test
// looks for, but with `correlation_id` made optional/nullable.
const BaseFrame = z.object({
  version: z.literal('1.0'),
  session_id: z.string(),
  // DRIFT vs Pydantic: correlation_id is required + min(1) on the
  // backend; declaring it optional/nullable here must trip the gate.
  correlation_id: z.string().nullable().optional(),
  role: z.enum(['tui', 'backend', 'tool', 'llm', 'notification']),
  frame_seq: z.number().int().min(0),
  transaction_id: z.string().min(1).nullable().optional(),
  ts: z.string(),
  trailer: z
    .object({
      final: z.boolean(),
      transaction_id: z.string().min(1).nullable().optional(),
      checksum_sha256: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
})

export type _DriftFixtureType = z.infer<typeof BaseFrame>
