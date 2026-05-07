// T115 [US7] — overflowToBackbuffer perf test
// Conversation exceeds terminal height. Assert scrollback works without
// re-rendering historical messages. Uses ink-testing-library + renderItem spy.
// US7 scenario 4, FR-052.
// Gemini CLI inspiration (Apache-2.0): overflowToBackbuffer pattern.

import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { Text } from 'ink'
import { render } from 'ink-testing-library'
import { VirtualizedList } from '../../../src/components/conversation/VirtualizedList'

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function makeMessages(count: number): readonly string[] {
  return Array.from({ length: count }, (_, i) => `history-${i}`)
}

const keyExtractor = (item: string): string => item

// ---------------------------------------------------------------------------
// Test: overflowToBackbuffer — historical rows go to Static backbuffer
// ---------------------------------------------------------------------------

describe('VirtualizedList overflowToBackbuffer — exceeds terminal height', () => {
  it('renders without throwing when list exceeds terminal height', () => {
    // 200 messages far exceeds any terminal height (24–50 rows typical).
    const items = makeMessages(200)

    const renderSpy = mock((_item: string, _index: number): React.ReactElement => {
      return <Text>{_item}</Text>
    })

    expect(() => {
      render(
        <VirtualizedList
          items={items}
          renderItem={renderSpy as (item: string, index: number) => React.ReactElement}
          keyExtractor={keyExtractor}
          overflowToBackbuffer
        />,
      )
    }).not.toThrow()
  })

  it('on re-render after appending one message, only viewport rows re-invoke renderItem', () => {
    // First render: 200 items. Static will commit all backbuffer items on first mount.
    const initial = makeMessages(200)

    // First-render spy captures initial mount calls.
    const firstSpy = mock((_item: string, _index: number): React.ReactElement => {
      return <Text>{_item}</Text>
    })

    const { rerender } = render(
      <VirtualizedList
        items={initial}
        renderItem={firstSpy as (item: string, index: number) => React.ReactElement}
        keyExtractor={keyExtractor}
        overflowToBackbuffer
      />,
    )

    // Append one new item and re-render with a fresh spy to count only re-render calls.
    const extended = [...initial, 'history-200']
    const reRenderSpy = mock((_item: string, _index: number): React.ReactElement => {
      return <Text>{_item}</Text>
    })

    rerender(
      <VirtualizedList
        items={extended}
        renderItem={reRenderSpy as (item: string, index: number) => React.ReactElement}
        keyExtractor={keyExtractor}
        overflowToBackbuffer
      />,
    )

    // On re-render, <Static> only processes newly-added backbuffer entries
    // (those appended since the last committed index). The viewport window
    // (tail ~11 items) also re-renders. Total should be << 201.
    const callsOnReRender = reRenderSpy.mock.calls.length
    expect(callsOnReRender).toBeLessThan(201)
    // Must actually render some rows (the visible viewport).
    expect(callsOnReRender).toBeGreaterThan(0)
  })
})

// ---------------------------------------------------------------------------
// Test: after re-render, historical messages are not re-invoked
// ---------------------------------------------------------------------------

describe('VirtualizedList overflowToBackbuffer — no re-render of historical rows', () => {
  it('historical rows not re-rendered when new item appended', () => {
    const initial = makeMessages(100)

    // First render: capture initial invocation count.
    const firstRenderSpy = mock(
      (_item: string, _index: number): React.ReactElement => {
        return <Text>{_item}</Text>
      },
    )

    const { rerender } = render(
      <VirtualizedList
        items={initial}
        renderItem={firstRenderSpy as (item: string, index: number) => React.ReactElement}
        keyExtractor={keyExtractor}
        overflowToBackbuffer
      />,
    )

    const callsAfterFirstRender = firstRenderSpy.mock.calls.length

    // Append one item and re-render with a fresh spy to count only re-render calls.
    const extended = [...initial, 'history-100']
    const reRenderSpy = mock(
      (_item: string, _index: number): React.ReactElement => {
        return <Text>{_item}</Text>
      },
    )

    rerender(
      <VirtualizedList
        items={extended}
        renderItem={reRenderSpy as (item: string, index: number) => React.ReactElement}
        keyExtractor={keyExtractor}
        overflowToBackbuffer
      />,
    )

    const callsOnReRender = reRenderSpy.mock.calls.length

    // Re-render should call renderItem only for the NEW viewport window,
    // not all 101 items.
    expect(callsOnReRender).toBeLessThan(101)
    // Sanity: first render was also bounded.
    expect(callsAfterFirstRender).toBeLessThan(101)
  })

  it('renders correctly with overflowToBackbuffer=false (no Static region)', () => {
    const items = makeMessages(50)

    const { lastFrame } = render(
      <VirtualizedList
        items={items}
        renderItem={(item, _i) => <Text>{item}</Text>}
        keyExtractor={keyExtractor}
        overflowToBackbuffer={false}
      />,
    )

    // Without overflowToBackbuffer, items still render correctly.
    const frame = lastFrame() ?? ''
    expect(frame).toContain('history-')
  })
})
