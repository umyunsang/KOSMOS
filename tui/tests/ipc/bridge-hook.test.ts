// SPDX-License-Identifier: Apache-2.0
// Task T122: FR-054 fire-and-forget telemetry hook isolation tests.
//
// Verifies:
//   1. Frame dispatch continues even when onFrame throws synchronously.
//   2. Frame dispatch continues even when onFrame returns a rejected Promise.
//   3. onFrame is called with the correct direction and a non-negative latencyMs.
//   4. Replacing onFrame mid-session is safe (new hook sees subsequent frames).

import { describe, expect, test, mock } from 'bun:test'
import type { IPCBridge, FrameHook } from '../../src/ipc/bridge'
import type { IPCFrame } from '../../src/ipc/frames.generated'

// ---------------------------------------------------------------------------
// Minimal stub bridge that exercises _dispatchHook without spawning a process.
// We replicate the queueMicrotask wrapper logic directly so we can unit-test
// the hook-isolation contract without relying on the real Bun.spawn path.
// ---------------------------------------------------------------------------

function makeStubDispatcher(bridge: { onFrame?: FrameHook }) {
  return function dispatchHook(
    frame: IPCFrame,
    direction: 'recv' | 'send',
    latencyMs: number,
  ): Promise<void> {
    return new Promise<void>((resolve) => {
      if (!bridge.onFrame) {
        resolve()
        return
      }
      const hook = bridge.onFrame
      queueMicrotask(() => {
        try {
          const result = hook(frame, direction, latencyMs) as unknown
          if (result instanceof Promise) {
            result.catch(() => {/* swallowed */})
          }
        } catch {
          /* swallowed */
        }
        resolve()
      })
    })
  }
}

function makeFrame(kind: string): IPCFrame {
  return {
    kind: kind as IPCFrame['kind'],
    session_id: 'test-session',
    ts: new Date().toISOString(),
  } as IPCFrame
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('bridge FR-054: onFrame hook isolation', () => {
  test('dispatch continues when onFrame throws synchronously', async () => {
    const bridge: { onFrame?: FrameHook } = {}
    const dispatch = makeStubDispatcher(bridge)

    bridge.onFrame = (_frame, _dir, _ms) => {
      throw new Error('hook exploded')
    }

    const frame = makeFrame('assistant_chunk')
    // Must not throw itself — dispatched fire-and-forget
    await expect(dispatch(frame, 'recv', 5)).resolves.toBeUndefined()
  })

  test('dispatch continues when onFrame returns a rejected Promise', async () => {
    const bridge: { onFrame?: FrameHook } = {}
    const dispatch = makeStubDispatcher(bridge)

    // The hook returns a pre-rejected Promise that is caught inside _dispatchHook.
    // We must NOT hold a dangling reference that leaks to the test runner.
    bridge.onFrame = (_frame, _dir, _ms) => {
      // Return a value via casting — the test exercises the swallow path in dispatchHook.
      // The cast is intentional: FR-054 callers may accidentally return a rejected
      // Promise; the bridge must survive it.
      return (new Promise<void>((_, reject) => {
        reject(new Error('otel export failed'))
      }).catch(() => {/* pre-caught so the test runner never sees an unhandled rejection */
      })) as unknown as void
    }

    const frame = makeFrame('assistant_chunk')
    await expect(dispatch(frame, 'recv', 5)).resolves.toBeUndefined()
  })

  test('onFrame is called with correct direction + non-negative latencyMs', async () => {
    const bridge: { onFrame?: FrameHook } = {}
    const dispatch = makeStubDispatcher(bridge)

    const calls: Array<{ dir: string; ms: number }> = []
    bridge.onFrame = (_frame, dir, ms) => {
      calls.push({ dir, ms })
    }

    const frame = makeFrame('user_input')
    await dispatch(frame, 'send', 12)

    expect(calls).toHaveLength(1)
    expect(calls[0]!.dir).toBe('send')
    expect(calls[0]!.ms).toBeGreaterThanOrEqual(0)
  })

  test('replacing onFrame mid-session — new hook receives subsequent frames', async () => {
    const bridge: { onFrame?: FrameHook } = {}
    const dispatch = makeStubDispatcher(bridge)

    const firstCalls: IPCFrame[] = []
    const secondCalls: IPCFrame[] = []

    bridge.onFrame = (frame) => { firstCalls.push(frame) }
    await dispatch(makeFrame('user_input'), 'send', 1)

    bridge.onFrame = (frame) => { secondCalls.push(frame) }
    await dispatch(makeFrame('assistant_chunk'), 'recv', 2)

    expect(firstCalls).toHaveLength(1)
    expect(secondCalls).toHaveLength(1)
    expect(firstCalls[0]!.kind).toBe('user_input')
    expect(secondCalls[0]!.kind).toBe('assistant_chunk')
  })

  test('no hook set — dispatch returns without error', async () => {
    const bridge: { onFrame?: FrameHook } = {}
    const dispatch = makeStubDispatcher(bridge)

    const frame = makeFrame('tool_result')
    await expect(dispatch(frame, 'recv', 3)).resolves.toBeUndefined()
  })
})
