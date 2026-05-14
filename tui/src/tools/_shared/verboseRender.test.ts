// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from 'bun:test'
import { render } from 'ink-testing-library'
import type React from 'react'
import {
  formatTraceUrlForHeader,
  renderVerboseOutputJson,
} from './verboseRender.js'

describe('formatTraceUrlForHeader', () => {
  test('keeps detailed URL evidence bounded in the trace heading', () => {
    const formatted = formatTraceUrlForHeader(
      'https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytListInfoInqire?serviceKey=***&pageNo=1&numOfRows=10&_type=json&Q0=%EB%B6%80%EC%82%B0%EA%B4%91%EC%97%AD%EC%8B%9C&Q1=%EC%82%AC%ED%95%98%EA%B5%AC&ORD=ADDR',
    )

    expect(formatted.length).toBeLessThanOrEqual(96)
    expect(formatted).toContain('https://apis.data.go.kr')
    expect(formatted).toContain('getEgytListInfoInqire')
    expect(formatted).toContain('serviceKey&pageNo&numOfRows')
    expect(formatted).not.toContain('%EB%B6%80')
  })

  test('returns an empty string for non-string values', () => {
    expect(formatTraceUrlForHeader(null)).toBe('')
  })
})

describe('renderVerboseOutputJson', () => {
  test('renders English UI labels for transcript details', () => {
    const node = renderVerboseOutputJson({
      ok: true,
      result: {
        outbound_traces: [
          {
            method: 'GET',
            url: 'https://apis.data.go.kr/example?serviceKey=***',
            request_body: '{"q":"test"}',
            response_status: 200,
            response_body: '{"ok":true}',
            elapsed_ms: 42,
          },
        ],
      },
    })
    const { lastFrame } = render(node as React.ReactElement)
    const frame = lastFrame() ?? ''

    expect(frame).toContain('Response envelope:')
    expect(frame).toContain('Outbound API request #1')
    expect(frame).toContain('Request body:')
    expect(frame).toContain('Response body:')
    expect(frame).not.toContain('응답')
    expect(frame).not.toContain('요청')
  })
})
