// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · LookupPrimitive.
//
// LLM-visible tool name: "lookup"
// Primitive wrapper over Spec 022 kosmos.tools.lookup — two modes:
//   search: BM25+dense hybrid retrieval over registered adapters
//   fetch:  direct adapter invocation by tool_id
//
// Epic γ #2294 · T006/T007: real validateInput + renderToolResultMessage.
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 2

import React from 'react'
import { z } from 'zod/v4'
import { Box, Text } from '../../ink.js'
import { buildTool, type ToolDef, type ToolUseContext } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import {
  extractCitation,
  PrimitiveErrorCode,
  type AdapterCitation,
  type AdapterWithPolicy,
} from '../shared/primitiveCitation.js'
import {
  isManifestSynced,
  resolveAdapter,
} from '../../services/api/adapterManifest.js'
import { LOOKUP_TOOL_NAME, DESCRIPTION, LOOKUP_TOOL_PROMPT } from './prompt.js'
import { dispatchPrimitive } from '../_shared/dispatchPrimitive.js'
import { getOrCreateKosmosBridge } from '../../ipc/bridgeSingleton.js'
import { getOrCreatePendingCallRegistry } from '../../ipc/pendingCallSingleton.js'

// ---------------------------------------------------------------------------
// KOSMOS citation extension — attaches resolved citation to the context so the
// permission UI can surface the verbatim agency policy URL. Does NOT modify
// Tool.ts or ToolPermissionContext (byte-identical CC port).
// ---------------------------------------------------------------------------
type ContextWithCitation = ToolUseContext & {
  kosmosCitations?: AdapterCitation[]
}

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

  // Epic γ #2294 · 9-member interface compliance.
  isMcp: false,

  /**
   * T006 — real validateInput per contracts/primitive-shape.md § validateInput.
   *
   * Steps:
   *  1. mode='search': skip adapter resolution (BM25 happens later in call()).
   *  2. mode='fetch': resolve tool_id against the tools registry.
   *  3. If not found: fail closed with Korean diagnostic.
   *  4. Read citation from adapter; fail closed if either field empty.
   *  5. Attach citation to context for permission UI surfacing.
   *  6. Return { result: true }.
   */
  async validateInput(
    input: z.infer<InputSchema>,
    context: ToolUseContext,
  ): Promise<import('../../Tool.js').ValidationResult> {
    // Step 1 — search mode: no adapter needed; BM25 runs inside call().
    if (input.mode === 'search') {
      return { result: true }
    }

    // Epic ε #2296 T011 — two-tier resolution (FR-017 / FR-018 / FR-019 / FR-020).

    // Tier 0 — fail closed if manifest not yet synced (FR-019).
    if (!isManifestSynced()) {
      return {
        result: false,
        message: 'Adapter manifest not yet synced from backend; retry once boot completes.',
        errorCode: PrimitiveErrorCode.AdapterNotFound,
      }
    }

    // Tier 1 — synced backend manifest (FR-017).
    const backendEntry = resolveAdapter(input.tool_id!)
    if (backendEntry) {
      const citation: AdapterCitation | null = backendEntry.policy_authority_url
        ? {
            real_classification_url: backendEntry.policy_authority_url,
            policy_authority: backendEntry.name,
          }
        : null
      ;(context as ContextWithCitation).kosmosCitations = citation ? [citation] : []
      return { result: true }
    }

    // Tier 2 — TS-side internal tools fallback (FR-018 / existing path).
    const internalAdapter = (context.options.tools as unknown as AdapterWithPolicy[]).find(
      (t) => t.name === input.tool_id,
    )
    if (internalAdapter) {
      const citation = extractCitation(internalAdapter)
      if (citation) {
        ;(context as ContextWithCitation).kosmosCitations = [citation]
      }
      return { result: true }
    }

    // Fail closed (FR-020).
    return {
      result: false,
      message: `AdapterNotFound: '${input.tool_id}' is not in the synced backend manifest or the internal tools list.`,
      errorCode: PrimitiveErrorCode.AdapterNotFound,
    }
  },

  /**
   * T007 — citizen-facing Korean rendering per contracts/primitive-shape.md
   * § renderToolResultMessage Lookup row.
   *
   * - mode='fetch', ok=true:  adapter name + result count + first-3 summary.
   * - mode='search', ok=true: ranked-hit list.
   * - ok=false:               Korean error message in citizen-friendly tone.
   */
  renderToolResultMessage(output: Output): React.ReactNode {
    if (!output.ok) {
      // Error path — surface the backend error message in citizen-friendly Korean.
      return React.createElement(
        Box,
        { flexDirection: 'column', marginTop: 1 },
        React.createElement(
          Text,
          { color: 'red' },
          `오류가 발생했습니다: ${output.error.message}`,
        ),
      )
    }

    // ok === true — inspect the result shape to determine mode.
    const result = output.result as Record<string, unknown>

    // mode='search' result: { mode: 'search', results: [...] }
    if (result.mode === 'search') {
      const hits = Array.isArray(result.results) ? result.results : []
      if (hits.length === 0) {
        return React.createElement(
          Box,
          { flexDirection: 'column', marginTop: 1 },
          React.createElement(Text, { dimColor: true }, '검색 결과가 없습니다.'),
        )
      }
      const hitRows = hits.slice(0, 10).map((hit: unknown, i: number) => {
        const h = hit as Record<string, unknown>
        const toolId = typeof h.tool_id === 'string' ? h.tool_id : '(알 수 없음)'
        const score =
          typeof h.score === 'number' ? ` [${h.score.toFixed(2)}]` : ''
        const hint =
          typeof h.search_hint === 'string' ? ` — ${h.search_hint}` : ''
        return React.createElement(
          Text,
          { key: i },
          `${i + 1}. ${toolId}${score}${hint}`,
        )
      })
      return React.createElement(
        Box,
        { flexDirection: 'column', marginTop: 1 },
        React.createElement(
          Text,
          { bold: true },
          `검색 결과 (${hits.length}건):`,
        ),
        ...hitRows,
      )
    }

    // mode='fetch' result: { mode: 'fetch', tool_id: string, result: object }
    const toolId =
      typeof result.tool_id === 'string' ? result.tool_id : '어댑터'
    const adapterResult = result.result
    let countText = ''
    let summaryRows: React.ReactNode[] = []

    if (Array.isArray(adapterResult)) {
      countText = `${adapterResult.length}건`
      summaryRows = adapterResult.slice(0, 3).map((item: unknown, i: number) => {
        const summary =
          typeof item === 'object' && item !== null
            ? JSON.stringify(item).slice(0, 120)
            : String(item).slice(0, 120)
        return React.createElement(
          Text,
          { key: i, dimColor: true },
          `  ${i + 1}. ${summary}`,
        )
      })
    } else if (adapterResult !== null && adapterResult !== undefined) {
      countText = '1건'
      const summary =
        typeof adapterResult === 'object'
          ? JSON.stringify(adapterResult).slice(0, 240)
          : String(adapterResult).slice(0, 240)
      summaryRows = [React.createElement(Text, { key: 0, dimColor: true }, `  ${summary}`)]
    }

    return React.createElement(
      Box,
      { flexDirection: 'column', marginTop: 1 },
      React.createElement(
        Text,
        null,
        React.createElement(Text, { bold: true }, toolId),
        countText ? ` — ${countText}` : '',
      ),
      ...summaryRows,
    )
  },

  /**
   * Dispatch lookup call via real IPC bridge (T009 — stub replaced).
   * validateInput has already resolved the adapter and populated kosmosCitations on the context.
   */
  async call(input, context) {
    return dispatchPrimitive<Output>({
      primitive: 'lookup',
      args: input as Record<string, unknown>,
      context,
      registry: getOrCreatePendingCallRegistry(),
      bridge: getOrCreateKosmosBridge(),
    })
  },
} satisfies ToolDef<InputSchema, Output>)
