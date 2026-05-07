// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — ResolveLocationPrimitive.
//
// LLM-visible tool name: "resolve_location"
// Primitive wrapper over Spec 031 ummaya.tools.resolve_location.

import React from 'react'
import { z } from 'zod/v4'
import { Box, Text } from '../../ink.js'
import { MessageResponse } from '../../components/MessageResponse.js'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import {
  RESOLVE_LOCATION_TOOL_NAME,
  DESCRIPTION,
  RESOLVE_LOCATION_TOOL_PROMPT,
} from './prompt.js'
import { dispatchPrimitive } from '../_shared/dispatchPrimitive.js'
import {
  renderVerboseInputJson,
  renderVerboseOutputJson,
} from '../_shared/verboseRender.js'
import { getOrCreateUmmayaBridge } from '../../ipc/bridgeSingleton.js'
import { getOrCreatePendingCallRegistry } from '../../ipc/pendingCallSingleton.js'

const WANT_VALUES = [
  'coords',
  'adm_cd',
  'coords_and_admcd',
  'road_address',
  'jibun_address',
  'poi',
  'region',
  'all',
] as const

const inputSchema = lazySchema(() =>
  z.strictObject({
    query: z
      .string()
      .min(1)
      .max(200)
      .describe('Free-text Korean or English place query from the citizen request.'),
    want: z
      .enum(WANT_VALUES)
      .default('coords_and_admcd')
      .describe('Identifier shape required by the downstream public-service adapter.'),
    near: z
      .tuple([z.number(), z.number()])
      .optional()
      .describe('Optional [lat, lon] tiebreaker for ambiguous place names.'),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

const outputSchema = lazySchema(() =>
  z.discriminatedUnion('ok', [
    z.object({
      ok: z.literal(true),
      result: z.unknown().describe('ResolveLocationOutput result.'),
      outbound_traces: z.array(z.unknown()).optional(),
    }),
    z.object({
      ok: z.literal(false),
      error: z.object({
        kind: z.string().describe('Error classification.'),
        message: z.string().describe('Human-readable error description.'),
      }),
      result: z.unknown().optional(),
      outbound_traces: z.array(z.unknown()).optional(),
    }),
  ]),
)
type OutputSchema = ReturnType<typeof outputSchema>

export type Output = z.infer<OutputSchema>

function stringField(obj: Record<string, unknown>, key: string): string | null {
  const value = obj[key]
  return typeof value === 'string' && value.length > 0 ? value : null
}

function numberField(obj: Record<string, unknown>, key: string): number | null {
  const value = obj[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function summarizeLocationResult(result: unknown): React.ReactNode[] {
  if (result === null || typeof result !== 'object') {
    return [React.createElement(Text, { key: 'raw', dimColor: true }, String(result))]
  }

  const obj = result as Record<string, unknown>
  const rows: React.ReactNode[] = []
  const kind = stringField(obj, 'kind')

  if (kind === 'bundle') {
    for (const key of ['coords', 'adm_cd', 'address', 'poi', 'region']) {
      const value = obj[key]
      if (value && typeof value === 'object') {
        rows.push(
          React.createElement(
            Text,
            { key },
            `${key}: ${JSON.stringify(value).slice(0, 160)}`,
          ),
        )
      }
    }
    return rows.length > 0
      ? rows
      : [React.createElement(Text, { key: 'empty', dimColor: true }, '해석 결과 없음')]
  }

  const lat = numberField(obj, 'lat')
  const lon = numberField(obj, 'lon')
  if (lat !== null && lon !== null) {
    rows.push(React.createElement(Text, { key: 'coords' }, `좌표: ${lat}, ${lon}`))
  }

  const code = stringField(obj, 'code') ?? stringField(obj, 'b_code') ?? stringField(obj, 'region_code')
  if (code) {
    rows.push(React.createElement(Text, { key: 'code' }, `행정/법정 코드: ${code}`))
  }

  const name =
    stringField(obj, 'address_name') ??
    stringField(obj, 'name') ??
    stringField(obj, 'road_address') ??
    stringField(obj, 'jibun_address')
  if (name) {
    rows.push(React.createElement(Text, { key: 'name' }, `위치명: ${name}`))
  }

  const source = stringField(obj, 'source')
  if (source) {
    rows.push(React.createElement(Text, { key: 'source', dimColor: true }, `source: ${source}`))
  }

  return rows.length > 0
    ? rows
    : [React.createElement(Text, { key: 'json', dimColor: true }, JSON.stringify(result).slice(0, 240))]
}

export const ResolveLocationPrimitive = buildTool({
  name: RESOLVE_LOCATION_TOOL_NAME,

  searchHint: '위치 주소 좌표 행정동 법정동 resolve_location geocode location',

  maxResultSizeChars: 40_000,

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
    return true
  },

  isReadOnly() {
    return true
  },

  async description() {
    return DESCRIPTION
  },

  async prompt() {
    return RESOLVE_LOCATION_TOOL_PROMPT
  },

  renderToolUseMessage(input: { query?: string; want?: string }, options: { verbose: boolean }) {
    if (options.verbose) {
      return renderVerboseInputJson(input)
    }
    return input.query ?? ''
  },

  isMcp: false,

  async validateInput() {
    return { result: true as const }
  },

  renderToolResultMessage(
    output: Output,
    _progress: unknown,
    options: { verbose: boolean; isTranscriptMode?: boolean } = { verbose: false },
  ): React.ReactNode {
    if (options.verbose || options.isTranscriptMode) {
      return renderVerboseOutputJson(output)
    }

    if (!output.ok) {
      return React.createElement(
        MessageResponse,
        null,
        React.createElement(Text, { color: 'red' }, `위치 해석 오류: ${output.error.message}`),
      )
    }

    return React.createElement(
      MessageResponse,
      null,
      React.createElement(
        Box,
        { flexDirection: 'column' },
        React.createElement(Text, { bold: true }, '위치 해석 결과'),
        ...summarizeLocationResult(output.result),
      ),
    )
  },

  async checkPermissions(input) {
    return { behavior: 'allow' as const, updatedInput: input }
  },

  async call(input, context) {
    return dispatchPrimitive<Output>({
      primitive: 'resolve_location',
      args: input as Record<string, unknown>,
      context,
      registry: getOrCreatePendingCallRegistry(),
      bridge: getOrCreateUmmayaBridge(),
    })
  },
} satisfies ToolDef<InputSchema, Output>)
