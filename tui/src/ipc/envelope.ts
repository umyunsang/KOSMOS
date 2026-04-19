// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 032 WS1 T018
//
// UUIDv7 minting helpers and trailer construction for the TUI-side
// NDJSON IPC envelope.
//
// Responsibilities:
//   - makeUUIDv7(): mint a fresh UUIDv7 string using crypto.randomUUID() +
//     millisecond-precision timestamp prepend (no new deps, AGENTS.md hard rule).
//   - makeTrailer(): build a FrameTrailer object for terminal frames.
//   - escapeNewlines(): escape bare \n in string values before JSON serialisation
//     so NDJSON line integrity is maintained (FR-009).
//   - makeBaseEnvelope(): convenience factory for the shared envelope fields.

import type { FrameTrailer } from './frames.generated'

// ---------------------------------------------------------------------------
// UUIDv7 (RFC 9562) — stdlib only, no new deps
// ---------------------------------------------------------------------------

/**
 * Mint a UUIDv7-format string.
 *
 * UUIDv7 structure (128 bits):
 *   48 bits — unix_ts_ms  (big-endian milliseconds)
 *   4 bits  — version = 0x7
 *   12 bits — random_a
 *   2 bits  — variant = 0b10
 *   62 bits — random_b
 *
 * Implementation uses ``crypto.randomUUID()`` (Bun stdlib) for the random
 * bits and overwrites the high 48 bits with the current millisecond timestamp.
 * This is not a spec-perfect UUIDv7 but is monotonic, sortable, and correct
 * enough for the KOSMOS correlation-id use-case.
 */
export function makeUUIDv7(): string {
  const nowMs = Date.now()

  // crypto.randomUUID() → 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
  const raw = crypto.randomUUID()

  // Overwrite first 12 hex digits (48 bits) with unix_ts_ms in hex.
  const tsHex = nowMs.toString(16).padStart(12, '0')

  // raw format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  // positions:  [0..7]-[9..12]-[14..17]-[19..22]-[24..35]
  // We replace chars 0..7 (8 hex = 32 bits) and 9..12 (4 hex = 16 bits)
  const result =
    tsHex.slice(0, 8) +
    '-' +
    tsHex.slice(8, 12) +
    '-' +
    '7' + raw.slice(15, 18) +   // version nibble = 7, keep 3 random hex
    '-' +
    raw.slice(19, 23) +          // variant + random_b start
    '-' +
    raw.slice(24)                 // lower 48 bits random

  return result
}

// ---------------------------------------------------------------------------
// Newline escape (FR-009)
// ---------------------------------------------------------------------------

/**
 * Recursively escape bare ``\n`` in string leaf values so that NDJSON lines
 * stay single-line after JSON.stringify().  The resulting JSON is valid —
 * ``\\n`` decodes back to ``\n`` on the receiver.
 */
export function escapeNewlines(obj: unknown): unknown {
  if (typeof obj === 'string') {
    return obj.replace(/\n/g, '\\n')
  }
  if (Array.isArray(obj)) {
    return obj.map(escapeNewlines)
  }
  if (obj !== null && typeof obj === 'object') {
    const result: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
      result[k] = escapeNewlines(v)
    }
    return result
  }
  return obj
}

// ---------------------------------------------------------------------------
// FrameTrailer factory
// ---------------------------------------------------------------------------

/**
 * Build a ``FrameTrailer`` for terminal frames (payload_end, resume_response,
 * resume_rejected, error, tool_result).
 */
export function makeTrailer(opts: {
  final: boolean
  transaction_id?: string | null
  checksum_sha256?: string | null
}): FrameTrailer {
  return {
    final: opts.final,
    transaction_id: opts.transaction_id ?? null,
    checksum_sha256: opts.checksum_sha256 ?? null,
  }
}

// ---------------------------------------------------------------------------
// Base envelope factory
// ---------------------------------------------------------------------------

/**
 * Envelope field defaults injected into every outgoing TUI frame.
 * Callers spread this and then override ``kind`` + arm-specific fields.
 */
export function makeBaseEnvelope(opts: {
  sessionId: string
  correlationId?: string
  frameSeq?: number
  transactionId?: string | null
}): {
  version: '1.0'
  session_id: string
  correlation_id: string
  role: 'tui'
  frame_seq: number
  transaction_id: string | null
  ts: string
  trailer: null
} {
  return {
    version: '1.0',
    session_id: opts.sessionId,
    correlation_id: opts.correlationId ?? makeUUIDv7(),
    role: 'tui',
    frame_seq: opts.frameSeq ?? 0,
    transaction_id: opts.transactionId ?? null,
    ts: new Date().toISOString(),
    trailer: null,
  }
}
