/**
 * Snapshot tests for subscribe primitive renderers.
 * Uses ink-testing-library for output capture.
 * FR-028, FR-029, FR-034, FR-035.
 */
import { describe, test, expect } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ThemeProvider } from '@/theme/provider'
import { EventStream } from '@/components/primitive/EventStream'
import { StreamClosed } from '@/components/primitive/StreamClosed'

import eventStreamFixture from '../fixtures/subscribe/event-stream.json'
import streamClosedFixture from '../fixtures/subscribe/stream-closed.json'

import type { EventStreamPayload, StreamClosedPayload } from '@/components/primitive/types'

function wrap(element: React.ReactElement): React.ReactElement {
  return <ThemeProvider>{element}</ThemeProvider>
}

describe('EventStream', () => {
  test('renders live badge, modality, and event bodies', () => {
    const payload = eventStreamFixture.envelope as EventStreamPayload
    const { lastFrame } = render(wrap(<EventStream payload={payload} />))
    const frame = lastFrame() ?? ''
    // Strip terminal wrapping by collapsing whitespace-split lines for partial checks
    const compact = frame.replace(/\s+/g, ' ')
    expect(compact).toContain('Live')
    expect(compact).toContain(payload.modality)
    // Event body may be wrapped; check a distinguishing substring
    expect(compact).toContain('[KR:강풍경보]')
    expect(frame).toMatchSnapshot()
  })
})

describe('StreamClosed', () => {
  test('renders closed badge, close_reason, event count, and cursor', () => {
    const payload = streamClosedFixture.envelope as StreamClosedPayload
    const { lastFrame } = render(wrap(<StreamClosed payload={payload} />))
    const frame = lastFrame() ?? ''
    expect(frame).toContain('Stream closed')
    expect(frame).toContain(payload.close_reason)
    expect(frame).toContain(`${payload.events.length} events received`)
    expect(frame).toContain(payload.final_cursor ?? '')
    expect(frame).toMatchSnapshot()
  })
})
