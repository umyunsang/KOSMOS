// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — no upstream analog (Claude Code uses HTTP SSE, not stdio JSONL).
//
// Codec for the KOSMOS JSONL IPC protocol.
//
// Responsibilities:
//   - encodeFrame: serialise an IPCFrame to a newline-terminated JSON string
//   - decodeFrames: parse a buffer string into validated IPCFrame objects
//     (handles partial lines / multiple lines in one chunk)
//
// Validation strategy: two-layer (FR-003).
//   1. JSON.parse — catches syntax errors immediately.
//   2. Zod discriminated union — validates shape against the generated types.
//   Both layers must pass; a failure in either yields a DecodeError result.
//
// All frame types live in tui/src/ipc/frames.generated.ts (code-gen from
// src/kosmos/ipc/frame_schema.py via bun run gen:ipc).

import { z } from 'zod'
import type { IPCFrame } from './frames.generated'

// ---------------------------------------------------------------------------
// Zod schemas (belt-and-braces atop generated TypeScript types)
// ---------------------------------------------------------------------------

// Base fields present on every frame arm.
const BaseFrame = z.object({
  session_id: z.string(),
  correlation_id: z.string().nullable().optional(),
  ts: z.string(),
})

const UserInputFrame = BaseFrame.extend({
  kind: z.literal('user_input'),
  text: z.string(),
})

const AssistantChunkFrame = BaseFrame.extend({
  kind: z.literal('assistant_chunk'),
  message_id: z.string(),
  delta: z.string(),
  done: z.boolean(),
})

const ToolCallFrame = BaseFrame.extend({
  kind: z.literal('tool_call'),
  call_id: z.string(),
  name: z.enum(['lookup', 'resolve_location', 'submit', 'subscribe', 'verify']),
  arguments: z.record(z.unknown()),
})

const ToolResultEnvelope = z.object({
  kind: z.enum(['lookup', 'resolve_location', 'submit', 'subscribe', 'verify']),
}).passthrough()

const ToolResultFrame = BaseFrame.extend({
  kind: z.literal('tool_result'),
  call_id: z.string(),
  envelope: ToolResultEnvelope,
})

const CoordinatorPhaseFrame = BaseFrame.extend({
  kind: z.literal('coordinator_phase'),
  phase: z.enum(['Research', 'Synthesis', 'Implementation', 'Verification']),
})

const WorkerStatusFrame = BaseFrame.extend({
  kind: z.literal('worker_status'),
  worker_id: z.string(),
  role_id: z.string(),
  current_primitive: z.enum(['lookup', 'resolve_location', 'submit', 'subscribe', 'verify']),
  status: z.enum(['idle', 'running', 'waiting_permission', 'error']),
})

const PermissionRequestFrame = BaseFrame.extend({
  kind: z.literal('permission_request'),
  request_id: z.string(),
  worker_id: z.string(),
  primitive_kind: z.enum(['lookup', 'resolve_location', 'submit', 'subscribe', 'verify']),
  description_ko: z.string(),
  description_en: z.string(),
  risk_level: z.enum(['low', 'medium', 'high']),
})

const PermissionResponseFrame = BaseFrame.extend({
  kind: z.literal('permission_response'),
  request_id: z.string(),
  decision: z.enum(['granted', 'denied']),
})

const SessionEventFrame = BaseFrame.extend({
  kind: z.literal('session_event'),
  event: z.enum(['save', 'load', 'list', 'resume', 'new', 'exit']),
  payload: z.record(z.unknown()),
})

const ErrorFrame = BaseFrame.extend({
  kind: z.literal('error'),
  code: z.string(),
  message: z.string(),
  details: z.record(z.unknown()),
})

/** Zod discriminated-union validator for all 10 IPCFrame arms. */
export const IPCFrameSchema = z.discriminatedUnion('kind', [
  UserInputFrame,
  AssistantChunkFrame,
  ToolCallFrame,
  ToolResultFrame,
  CoordinatorPhaseFrame,
  WorkerStatusFrame,
  PermissionRequestFrame,
  PermissionResponseFrame,
  SessionEventFrame,
  ErrorFrame,
])

// ---------------------------------------------------------------------------
// Codec types
// ---------------------------------------------------------------------------

export type DecodeSuccess = { ok: true; frame: IPCFrame }
export type DecodeError = { ok: false; error: string; raw: string }
export type DecodeResult = DecodeSuccess | DecodeError

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Serialise *frame* to a JSON string terminated by a single newline.
 *
 * The backend parser expects exactly one JSON object per line; the trailing
 * `\n` is the line delimiter.
 */
export function encodeFrame(frame: IPCFrame): string {
  return JSON.stringify(frame) + '\n'
}

/**
 * Attempt to decode a single line of JSON into a validated IPCFrame.
 *
 * @param line - A single JSON string (without a trailing newline).
 * @returns A {@link DecodeResult}; check `.ok` before accessing `.frame`.
 */
export function decodeFrame(line: string): DecodeResult {
  let parsed: unknown
  try {
    parsed = JSON.parse(line)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    return { ok: false, error: `JSON parse error: ${msg}`, raw: line }
  }

  const result = IPCFrameSchema.safeParse(parsed)
  if (!result.success) {
    return {
      ok: false,
      error: `Zod validation error: ${result.error.message}`,
      raw: line,
    }
  }

  return { ok: true, frame: result.data as IPCFrame }
}

/**
 * Split a potentially-partial buffer string into complete frames + a remainder.
 *
 * The IPC protocol delimits frames with `\n`.  Since Bun's stdout pipe may
 * deliver multiple lines in a single chunk (or a partial line), this function
 * accumulates a remainder across calls.
 *
 * @param buffer - The current accumulated buffer (may include previous
 *   incomplete lines concatenated with new data from the pipe).
 * @returns
 *   - `frames`: Array of {@link DecodeResult} — one entry per complete line,
 *     in arrival order.
 *   - `remainder`: Incomplete trailing bytes (no newline yet) to prepend to
 *     the next buffer chunk.
 */
export function decodeFrames(buffer: string): { frames: DecodeResult[]; remainder: string } {
  const parts = buffer.split('\n')
  // The last element is either empty (if buffer ends with \n) or a partial
  // line that must be held over until the next chunk arrives.
  const remainder = parts.pop() ?? ''
  const frames: DecodeResult[] = []
  for (const part of parts) {
    const trimmed = part.trim()
    if (trimmed.length === 0) continue // skip blank lines
    frames.push(decodeFrame(trimmed))
  }
  return { frames, remainder }
}
