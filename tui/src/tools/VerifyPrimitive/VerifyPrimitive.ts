// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · VerifyPrimitive.
//
// LLM-visible tool name: "verify"
// Primitive wrapper over Spec 031 kosmos.primitives.verify.
// Delegates credential verification to an auth vendor — never mints credentials.
//
// P3 MVP: returns a structured stub indicating T028 registry closure is pending.
// Real dispatch is wired in T028 (registry closure) and exercised by T029 (E2E).
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 4

import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { VERIFY_TOOL_NAME, DESCRIPTION, VERIFY_TOOL_PROMPT } from './prompt.js'

// ---------------------------------------------------------------------------
// Input schema
// ---------------------------------------------------------------------------

const inputSchema = lazySchema(() =>
  z.strictObject({
    tool_id: z
      .string()
      .min(1)
      .describe('Auth adapter identifier, e.g. "gongdong_injeungseo", "mobile_id"'),
    params: z
      .record(z.string(), z.unknown())
      .describe('Adapter-defined credential parameter body'),
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
        'Verify result including auth_family, auth_level, and adapter-specific verification payload',
      ),
    }),
    z.object({
      ok: z.literal(false),
      error: z.object({
        kind: z.string().describe('Error classification, e.g. "verification_failed", "tool_not_found"'),
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

export const VerifyPrimitive = buildTool({
  name: VERIFY_TOOL_NAME,

  /** Bilingual keyword hint for ToolSearch deferred-tool discovery. */
  searchHint: '인증 검증 verify credential auth 공인인증서 간편인증 본인확인',

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
    // verify is read-only (delegates, never mints) — concurrency safe.
    return true
  },

  isReadOnly() {
    return true
  },

  async description() {
    return DESCRIPTION
  },

  async prompt() {
    return VERIFY_TOOL_PROMPT
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

  // Epic γ #2294 · T005 · 9-member compliance stubs.
  // Real validateInput + renderToolResultMessage land in T013/T014.
  isMcp: false,

  async validateInput() {
    // T005 stub — fail-open. T013 replaces with adapter-resolve + citation
    // populate + Korean diagnostic per contracts/primitive-shape.md.
    return { result: true } as const
  },

  renderToolResultMessage() {
    // T005 stub — render nothing. T014 replaces with citizen-facing Korean
    // rendering per contracts/primitive-shape.md § Verify row.
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
          primitive: 'verify',
          echo: input,
        },
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
