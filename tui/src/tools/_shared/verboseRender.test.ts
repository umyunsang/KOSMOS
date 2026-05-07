// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from 'bun:test'
import { formatTraceUrlForHeader } from './verboseRender.js'

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
