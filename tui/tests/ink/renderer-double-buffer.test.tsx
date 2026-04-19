// SPDX-License-Identifier: Apache-2.0
// T119 — Double-buffered redraw component test (US7, FR-049).
//
// The renderer.ts double-buffer pattern (frontFrame / backFrame) ensures that
// only diffs between frames are emitted to the terminal — unchanged cells are
// blitted from prevScreen without re-rendering. FR-049 requires redraw-batch
// coalescing: multiple in-flight state mutations before the next React commit
// must collapse into a single frame output, matching Claude Code behavior.
//
// Strategy: importing `src/ink/renderer.ts` directly is not viable because
// `@alcalzone/ansi-tokenize` (used by output.ts / screen.ts) is not installed
// in this environment. Instead, we exercise the observable coalescing boundary
// through `ink-testing-library`'s `frames` array, which captures every
// terminal write. The ink-testing-library uses `debug: true` — renders are
// unthrottled but still async (Ink.onRender is an async function). We await
// a microtask flush between mutations and assertions.
//
// Test plan:
//   1. Static render identity — a static component produces a stable frame.
//   2. Single mutation → frame update — store change triggers exactly one
//      new frame (visible-content change = one buffer swap).
//   3. Synchronous-batch coalescing — three rapid mutations produce a final
//      frame showing only the last state, not intermediate states.
//   4. Content mutation replaces old content — back-buffer swap discards
//      the front-buffer's stale content.
//   5. Stable content idempotency — re-rendering identical content does not
//      corrupt the frame.
//   6. Assembled message text from sequential chunks appears in final frame.

import { describe, it, expect, beforeEach } from 'bun:test'
import React from 'react'
import { Text, Box } from 'ink'
import { render } from 'ink-testing-library'
import {
  dispatchSessionAction,
  useSessionStore,
} from '../../src/store/session-store'
import type { Phase } from '../../src/store/session-store'

// ---------------------------------------------------------------------------
// Store reset helper
// ---------------------------------------------------------------------------

function resetStore(): void {
  dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

// ---------------------------------------------------------------------------
// Async helper: flush React/Ink's async onRender pipeline
// ---------------------------------------------------------------------------

/**
 * Yield to the event loop enough times for Ink's async onRender() to complete.
 * Ink schedules render via `void this.onRender()` (an async function), so we
 * need at least two microtask flushes: one for the React reconciler commit,
 * one for the Ink frame write.
 */
async function flushRender(): Promise<void> {
  await new Promise<void>(r => setTimeout(r, 0))
  await new Promise<void>(r => setTimeout(r, 0))
}

// ---------------------------------------------------------------------------
// Test components
// ---------------------------------------------------------------------------

/** Reads coordinator_phase from the store via stable primitive selector. */
function PhaseDisplay() {
  const phase = useSessionStore(s => s.coordinator_phase)
  return <Text>{phase ?? 'none'}</Text>
}

/** Reads a single message's joined chunk text. Returns empty string if absent. */
function MessageText({ messageId }: { messageId: string }) {
  // Selector returns a primitive string — no infinite-loop from new array ref.
  const text = useSessionStore(
    s => s.messages.get(messageId)?.chunks.join('') ?? '',
  )
  return <Text>{text}</Text>
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  resetStore()
})

describe('Renderer double-buffer coalescing (T119, FR-049)', () => {
  it('static render produces a stable frame with expected content', async () => {
    const { frames, lastFrame } = render(<Text>hello-world</Text>)
    await flushRender()

    // Ink renders synchronously on mount in debug mode, then async-flushes
    expect(frames.length).toBeGreaterThanOrEqual(1)
    expect(lastFrame()).toContain('hello-world')
  })

  it('single store mutation triggers a re-render with updated content', async () => {
    const { lastFrame } = render(<PhaseDisplay />)
    await flushRender()

    // Initially "none"
    expect(lastFrame()).toContain('none')

    // Single mutation
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Research' })
    await flushRender()

    // Frame must now show the updated phase
    expect(lastFrame()).toContain('Research')
  })

  it('synchronous multi-mutation batch: final frame shows last state only', async () => {
    const { lastFrame } = render(<PhaseDisplay />)
    await flushRender()

    // Three synchronous mutations — React 19 + Ink batches these.
    // The back-buffer accumulates all mutations before the next paint;
    // only the last state (Verification) should appear in the frame.
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Research' })
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Synthesis' })
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Verification' })
    await flushRender()

    const last = lastFrame() ?? ''
    // The final frame must show the last mutation's state
    expect(last).toContain('Verification')

    // Intermediate states must NOT be the painted final state (FR-049 coalescing)
    // If batching worked perfectly, Research/Synthesis never appear at all.
    // If only partial batching, they appear in earlier frames but NOT the last.
    expect(last).not.toContain('Research')
    expect(last).not.toContain('Synthesis')
  })

  it('content mutation replaces old content — back-buffer swap', async () => {
    const { lastFrame, rerender } = render(<Text>before-mutation</Text>)
    await flushRender()

    expect(lastFrame()).toContain('before-mutation')

    // Rerender with new content — triggers a diff, back-buffer absorbs the
    // new tree, front-buffer swaps in with the new content.
    rerender(<Text>after-mutation</Text>)
    await flushRender()

    expect(lastFrame()).toContain('after-mutation')
    // Old content is gone from the current frame
    expect(lastFrame()).not.toContain('before-mutation')
  })

  it('identical content rerender does not corrupt the frame', async () => {
    const { lastFrame, rerender } = render(<Text>stable-content</Text>)
    await flushRender()

    const frameAfterMount = lastFrame()

    // Identical rerenders — charCache reuse means the output is identical.
    // The frame must remain stable and correct.
    rerender(<Text>stable-content</Text>)
    await flushRender()
    rerender(<Text>stable-content</Text>)
    await flushRender()

    expect(lastFrame()).toContain('stable-content')
    // The content is identical to the mount frame (no corruption)
    expect(lastFrame()).toBe(frameAfterMount)
  })

  it('box layout with multiple text nodes renders as one cohesive frame', async () => {
    const { lastFrame } = render(
      <Box flexDirection="column">
        <Text>line-alpha</Text>
        <Text>line-beta</Text>
      </Box>,
    )
    await flushRender()

    const last = lastFrame() ?? ''
    // Both text nodes must appear in the SAME frame — the back-buffer
    // accumulates all write operations from the full render tree before
    // committing a frame to the terminal.
    expect(last).toContain('line-alpha')
    expect(last).toContain('line-beta')
  })

  it('sequential ASSISTANT_CHUNK actions: final assembled text appears in last frame', async () => {
    const MESSAGE_ID = 'render-test-msg-t119'

    const { lastFrame } = render(<MessageText messageId={MESSAGE_ID} />)
    await flushRender()

    // Dispatch three chunks. Selector returns a string (primitive) so
    // useSyncExternalStore does not cause infinite loops.
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'Hello',
      done: false,
    })
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: ' ',
      done: false,
    })
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'World',
      done: true,
    })
    await flushRender()

    // The fully assembled text must appear in the last rendered frame.
    expect(lastFrame()).toContain('Hello World')
  })

  it('phase transitions across all four coordinator phases render correctly', async () => {
    const { lastFrame } = render(<PhaseDisplay />)
    await flushRender()

    const phases: Phase[] = ['Research', 'Synthesis', 'Implementation', 'Verification']
    for (const phase of phases) {
      dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase })
      await flushRender()
      expect(lastFrame()).toContain(phase)
    }
  })
})
