// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · LookupPrimitive.
//
// LLM-visible tool name: "lookup"
// Primitive wrapper over Spec 022 kosmos.tools.lookup — two modes:
//   search: BM25+dense hybrid retrieval over registered adapters
//   fetch:  direct adapter invocation by tool_id
//
// P3 MVP: returns a structured stub indicating T028 registry closure is pending.
// Real dispatch is wired in T028 (registry closure) and exercised by T029 (E2E).
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 2

import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { LOOKUP_TOOL_NAME, DESCRIPTION, LOOKUP_TOOL_PROMPT } from './prompt.js'

// ---------------------------------------------------------------------------
// Input schema — discriminated union on "mode"
// ---------------------------------------------------------------------------

const searchModeSchema = z.object({
  mode: z.literal('search'),
  query: z.string().min(1).describe('Citizen prompt fragment in Korean or English'),
  primitive_filter: z
    .enum(['lookup', 'submit', 'verify', 'subscribe'])
    .nullable()
    .optional()
    .describe('Restrict results to a single primitive type; null or omit for all'),
  top_k: z
    .number()
    .int()
    .min(1)
    .max(50)
    .optional()
    .describe('Maximum number of results to return (default 5)'),
})

const fetchModeSchema = z.object({
  mode: z.literal('fetch'),
  tool_id: z.string().min(1).describe('Registered adapter identifier, e.g. "hira_hospital_search"'),
  params: z
    .record(z.string(), z.unknown())
    .describe('Adapter-defined Pydantic-validated parameter body'),
})

const inputSchema = lazySchema(() =>
  z.discriminatedUnion('mode', [searchModeSchema, fetchModeSchema]),
)
type InputSchema = ReturnType<typeof inputSchema>

// ---------------------------------------------------------------------------
// Output schema — discriminated union on "ok"
// ---------------------------------------------------------------------------

const outputSchema = lazySchema(() =>
  z.discriminatedUnion('ok', [
    z.object({
      ok: z.literal(true),
      result: z.unknown().describe('Adapter result or search results array'),
    }),
    z.object({
      ok: z.literal(false),
      error: z.object({
        kind: z.string().describe('Error classification, e.g. "tool_not_found"'),
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

export const LookupPrimitive = buildTool({
  name: LOOKUP_TOOL_NAME,

  /** Bilingual keyword hint for ToolSearch deferred-tool discovery. */
  searchHint: '조회 검색 lookup discover search adapter 공공 API 어댑터',

  maxResultSizeChars: 100_000,

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
    // lookup is read-only and side-effect-free.
    return true
  },

  isReadOnly() {
    return true
  },

  async description() {
    return DESCRIPTION
  },

  async prompt() {
    return LOOKUP_TOOL_PROMPT
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
  // Real validateInput + renderToolResultMessage land in T006/T007.
  isMcp: false,

  async validateInput() {
    // T005 stub — fail-open. T006 replaces with adapter-resolve + citation
    // populate + Korean diagnostic per contracts/primitive-shape.md.
    return { result: true } as const
  },

  renderToolResultMessage() {
    // T005 stub — render nothing. T007 replaces with citizen-facing Korean
    // rendering per contracts/primitive-shape.md § Lookup row.
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
          primitive: 'lookup',
          echo: input,
        },
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
