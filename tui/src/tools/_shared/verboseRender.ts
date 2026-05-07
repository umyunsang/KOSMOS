// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Spec 2521 / 2026-05-01.
//
// Verbose render helpers for the UMMAYA primitives. Mirrors the
// CC pattern used by BashTool / WebFetchTool: when ``verbose`` is set
// (Ctrl+O expand or transcript mode), surface the full request/response
// JSON to the citizen rather than the condensed summary.
//
// CC reference: tools/BashTool/UI.tsx:renderToolUseMessage(verbose)
//                tools/BashTool/UI.tsx:renderToolResultMessage(verbose)
//
// Citizen flow:
//   non-verbose → "● lookup(kma_forecast_fetch)" + condensed result
//   verbose     → "● lookup({\n  \"tool_id\": ..., \"params\": {...}\n})"
//                 + ⎿ Response: { "ok": true, "result": {...} }
//

import React from 'react'
import { Box, Text } from '../../ink.js'
import { MessageResponse } from '../../components/MessageResponse.js'

const TRACE_URL_HEADER_LIMIT = 96

/**
 * Format the full primitive input as a multi-line JSON string.
 *
 * The returned string is interpolated into AssistantToolUseMessage's
 * ``<Text>({rendered})</Text>`` wrapper, so the closing paren ends up
 * on its own line — matches CC BashTool's multi-line command rendering.
 */
export function renderVerboseInputJson(input: unknown): string {
  try {
    return '\n' + JSON.stringify(input, null, 2) + '\n'
  } catch {
    return String(input)
  }
}

/**
 * Render the full primitive output envelope as a JSON code block under
 * the standard ⎿ MessageResponse gutter glyph.
 *
 * Used by primitives' ``renderToolResultMessage`` when
 * ``options.verbose`` (or transcript mode) is set.
 *
 * If the output (or its ``result``) carries an ``outbound_traces`` array
 * (populated by :mod:`ummaya.tools._outbound_trace` on the backend), the
 * outbound HTTP request/response JSON is rendered as a sibling section
 * BELOW the envelope JSON so the citizen/operator can see exactly what
 * hit the agency API and what came back.
 */
export function renderVerboseOutputJson(
  output: unknown,
  label = '응답 envelope',
): React.ReactNode {
  let body: string
  try {
    body = JSON.stringify(output, null, 2)
  } catch {
    body = String(output)
  }

  const traces = extractOutboundTraces(output)

  const children: React.ReactNode[] = [
    React.createElement(Text, { bold: true, key: 'label' }, `${label}:`),
    React.createElement(Text, { dimColor: true, key: 'body' }, body),
  ]

  traces.forEach((trace, idx) => {
    const traceUrl = formatTraceUrlForHeader(trace.url)
    children.push(
      React.createElement(
        Text,
        { bold: true, color: 'cyan', key: `trace-${idx}-h` },
        `\n외부 API 요청 #${idx + 1} — ${trace.method ?? 'HTTP'} ${traceUrl}` +
          (typeof trace.response_status === 'number'
            ? ` → ${trace.response_status}`
            : '') +
          (typeof trace.elapsed_ms === 'number'
            ? ` (${trace.elapsed_ms}ms)`
            : ''),
      ),
    )
    if (trace.request_body) {
      children.push(
        React.createElement(
          Text,
          { dimColor: true, key: `trace-${idx}-rq-h` },
          '요청 body:',
        ),
        React.createElement(
          Text,
          { dimColor: true, key: `trace-${idx}-rq` },
          String(trace.request_body),
        ),
      )
    }
    if (trace.response_body) {
      children.push(
        React.createElement(
          Text,
          { dimColor: true, key: `trace-${idx}-rs-h` },
          '응답 body:',
        ),
        React.createElement(
          Text,
          { dimColor: true, key: `trace-${idx}-rs` },
          String(trace.response_body),
        ),
      )
    }
  })

  return React.createElement(
    MessageResponse,
    null,
    React.createElement(Box, { flexDirection: 'column' }, ...children),
  )
}

export function formatTraceUrlForHeader(url: unknown): string {
  if (typeof url !== 'string' || !url) return ''

  let display = url
  try {
    const parsed = new URL(url)
    const queryKeys = Array.from(parsed.searchParams.keys())
    const pathParts = parsed.pathname.split('/').filter(Boolean)
    const pathSummary =
      pathParts.length > 0 ? `/${pathParts[pathParts.length - 1]}` : parsed.pathname
    display = `${parsed.origin}${pathSummary}`
    if (queryKeys.length > 0) {
      const shownKeys = queryKeys.slice(0, 3).join('&')
      display += `?${shownKeys}${queryKeys.length > 3 ? '&...' : ''}`
    }
  } catch {
    display = url
  }

  if (display.length <= TRACE_URL_HEADER_LIMIT) return display
  return `${display.slice(0, TRACE_URL_HEADER_LIMIT - 3)}...`
}

type OutboundTrace = {
  method?: string
  url?: string
  request_body?: unknown
  response_status?: unknown
  response_body?: unknown
  elapsed_ms?: unknown
}

function extractOutboundTraces(output: unknown): OutboundTrace[] {
  if (!output || typeof output !== 'object') return []
  const obj = output as Record<string, unknown>
  // Primitive output schema: { ok: true, result: { outbound_traces: [...] } }
  // OR backend envelope: { kind, outbound_traces: [...] }
  const candidate =
    (obj.outbound_traces as unknown) ??
    ((obj.result as Record<string, unknown> | undefined)?.outbound_traces as unknown)
  if (!Array.isArray(candidate)) return []
  return candidate as OutboundTrace[]
}
