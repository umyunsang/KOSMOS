// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · SubscribePrimitive.
//
// LLM-visible tool name: "subscribe"
// Primitive wrapper over Spec 031 kosmos.primitives.subscribe.
// Returns a SubscriptionHandle with session-lifetime; stream delivered out-of-band.
//
// Epic γ #2294 · T016/T017/T018: real validateInput + renderToolResultMessage.
//
// I/O contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 5

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
import { SUBSCRIBE_TOOL_NAME, DESCRIPTION, SUBSCRIBE_TOOL_PROMPT } from './prompt.js'

// ---------------------------------------------------------------------------
// KOSMOS citation extension — augments context at runtime for permission UI.
// Does NOT modify Tool.ts or ToolPermissionContext; uses a local cast to attach
// the citation so FallbackPermissionRequest can surface verbatim agency text.
// ---------------------------------------------------------------------------
type ContextWithCitation = ToolUseContext & {
  kosmosCitations?: AdapterCitation[]
}

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

  // Epic γ #2294 · T016/T017 · real validateInput + renderToolResultMessage.
  isMcp: false,

  async validateInput(
    input: z.infer<ReturnType<typeof inputSchema>>,
    context: ToolUseContext,
  ) {
    // Step 1: subscribe always requires a tool_id — resolve adapter from registry.
    const adapter = context.options.tools.find(
      (t) => t.name === input.tool_id,
    ) as AdapterWithPolicy | undefined

    if (!adapter) {
      return {
        result: false as const,
        message: `도구 '${input.tool_id}'을(를) 찾을 수 없습니다.`,
        errorCode: PrimitiveErrorCode.AdapterNotFound,
      }
    }

    // Step 2: Read citation — fail-closed if either field is empty.
    const citation = extractCitation(adapter)
    if (!citation) {
      return {
        result: false as const,
        message: `도구 '${input.tool_id}'에 정책 인용 정보가 없어 호출할 수 없습니다.`,
        errorCode: PrimitiveErrorCode.CitationMissing,
      }
    }

    // Step 3: Populate citation slot on context for permission UI consumption.
    ;(context as ContextWithCitation).kosmosCitations = [citation]

    return { result: true as const }
  },

  renderToolResultMessage(output: Output) {
    if (output.ok === true) {
      // Extract handle metadata from the result payload.
      const result = output.result as Record<string, unknown> | null | undefined
      const handleId =
        result && typeof result === 'object' ? result['handle_id'] : undefined
      const lifetime =
        result && typeof result === 'object' ? result['lifetime'] : undefined
      const kind =
        result && typeof result === 'object' ? result['kind'] : undefined

      const handleLabel = handleId
        ? String(handleId)
        : '핸들 ID 없음'
      const kindLabel = kind ? `(${String(kind)})` : ''
      const lifetimeLabel = lifetime
        ? `유지 시간: ${String(lifetime)}`
        : undefined

      return React.createElement(
        Box,
        { flexDirection: 'column', paddingY: 0 },
        React.createElement(
          Text,
          null,
          React.createElement(Text, { bold: true }, '구독 완료: '),
          React.createElement(Text, null, `${handleLabel} ${kindLabel}`.trim()),
        ),
        lifetimeLabel
          ? React.createElement(Text, { dimColor: true }, lifetimeLabel)
          : null,
        React.createElement(
          Text,
          { dimColor: true },
          '⎿ 실시간 스트림은 대화창에서 ⎿ 접두어로 전달됩니다. 구독을 취소하려면 구독 핸들 ID를 사용하세요.',
        ),
      )
    }

    // output.ok === false: render error message in Korean.
    const errorMsg = output.error?.message ?? '구독 요청이 실패하였습니다.'
    return React.createElement(
      Box,
      { flexDirection: 'column', paddingY: 0 },
      React.createElement(
        Text,
        { color: 'red' as never },
        `구독 실패: ${errorMsg}`,
      ),
    )
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
