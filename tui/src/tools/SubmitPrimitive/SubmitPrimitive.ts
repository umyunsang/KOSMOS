// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · SubmitPrimitive.
//
// LLM-visible tool name: "submit"
// Primitive wrapper over Spec 031 kosmos.primitives.submit.
// Permission-gated side-effecting citizen action (application, report, etc.)
//
// P3 MVP: returns a structured stub indicating T028 registry closure is pending.
// Real dispatch is wired in T028 (registry closure) and exercised by T029 (E2E).
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 3

import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { SUBMIT_TOOL_NAME, DESCRIPTION, SUBMIT_TOOL_PROMPT } from './prompt.js'

// ---------------------------------------------------------------------------
// Input schema
// ---------------------------------------------------------------------------

const inputSchema = lazySchema(() =>
  z.strictObject({
    tool_id: z
      .string()
      .min(1)
      .describe('Registered adapter identifier (obtain via lookup mode=search)'),
    params: z
      .record(z.string(), z.unknown())
      .describe('Adapter-defined Pydantic-validated parameter body'),
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
      result: z.unknown().describe('Submit result including transaction_id, status, adapter_receipt'),
    }),
    z.object({
      ok: z.literal(false),
      error: z.object({
        kind: z.string().describe('Error classification, e.g. "permission_denied", "tool_not_found"'),
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

export const SubmitPrimitive = buildTool({
  name: SUBMIT_TOOL_NAME,

  /** Bilingual keyword hint for ToolSearch deferred-tool discovery. */
  searchHint: '제출 신청 신고 submit apply report 공공 서비스 side-effect',

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
    // submit is side-effecting — not concurrency safe.
    return false
  },

  isReadOnly() {
    return false
  },

  isDestructive() {
    // submit can be irreversible (e.g., form submission, report filing).
    return true
  },

  async description() {
    return DESCRIPTION
  },

  async prompt() {
    return SUBMIT_TOOL_PROMPT
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
          primitive: 'submit',
          echo: input,
        },
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
