// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · SubscribePrimitive.
//
// LLM-visible tool name: "subscribe"
// Primitive wrapper over Spec 031 kosmos.primitives.subscribe.
// Returns a SubscriptionHandle with session-lifetime; stream delivered out-of-band.
//
// P3 MVP: returns a structured stub indicating T028 registry closure is pending.
// Real dispatch is wired in T028 (registry closure) and exercised by T029 (E2E).
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 5

import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { SUBSCRIBE_TOOL_NAME, DESCRIPTION, SUBSCRIBE_TOOL_PROMPT } from './prompt.js'

// ---------------------------------------------------------------------------
// Input schema
// ---------------------------------------------------------------------------

const inputSchema = lazySchema(() =>
  z.strictObject({
    tool_id: z
      .string()
      .min(1)
      .describe('Streaming adapter identifier (obtain via lookup mode=search)'),
    params: z
      .record(z.string(), z.unknown())
      .describe('Adapter-defined Pydantic-validated subscription parameter body'),
    lifetime_hint: z
      .enum(['session', 'short', 'long'])
      .optional()
      .describe(
        'Requested handle lifetime: "session" (default, entire REPL session), "short" (≤5 min), "long" (≤24 h)',
      ),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

// ---------------------------------------------------------------------------
// Output schema — discriminated union on "ok"
// ---------------------------------------------------------------------------

const outputSchema = lazySchema(() =>
  z.discriminatedUnion('ok', [
    z.object({
      ok: z.literal(true),
      result: z.unknown().describe(
        'SubscriptionHandle: { handle_id, lifetime, kind } — stream delivered out-of-band via TUI ⎿ prefix',
      ),
    }),
    z.object({
      ok: z.literal(false),
      error: z.object({
        kind: z.string().describe('Error classification, e.g. "tool_not_found", "permission_denied"'),
        message: z.string().describe('Human-readable error description'),
      }),
    }),
  ]),
)
type OutputSchema = ReturnType<typeof outputSchema>

export type Output = z.infer<OutputSchema>

// ---------------------------------------------------------------------------
// Tool definition
// ---------------------------------------------------------------------------

export const SubscribePrimitive = buildTool({
  name: SUBSCRIBE_TOOL_NAME,

  /** Bilingual keyword hint for ToolSearch deferred-tool discovery. */
  searchHint: '구독 스트리밍 subscribe streaming 재난 알림 실시간 alert realtime',

  maxResultSizeChars: 50_000,

  get inputSchema(): InputSchema {
    return inputSchema()
  },

  get outputSchema(): OutputSchema {
    return outputSchema()
  },

  isEnabled() {
    return true
  },

  isConcurrencySafe() {
    // subscribe is session-scoped and side-effecting — not concurrency safe.
    return false
  },

  isReadOnly() {
    return false
  },

  async description() {
    return DESCRIPTION
  },

  async prompt() {
    return SUBSCRIBE_TOOL_PROMPT
  },

  mapToolResultToToolResultBlockParam(output, toolUseID) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result',
      content: JSON.stringify(output),
    }
  },

  renderToolUseMessage() {
    return null
  },

  /**
   * P3 MVP stub — real dispatch wired by T028 registry closure + T029 E2E test.
   */
  async call(input, _context) {
    return {
      data: {
        ok: true as const,
        result: {
          status: 'stub',
          note: 'Primitive wrapper stub — real dispatch wired by T028 registry closure + T029 E2E test.',
          primitive: 'subscribe',
          echo: input,
        },
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
