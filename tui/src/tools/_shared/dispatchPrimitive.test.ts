// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic ζ #2297 Phase 0b · T008
//
// Unit tests for dispatchPrimitive.ts + PendingCallRegistry.
//
// Contract coverage (I-D10):
//   ✅ Successful round-trip (mock bridge: send → fake tool_result → resolve)
//   ✅ Timeout rejection
//   ✅ Error envelope passthrough
//   ✅ Concurrent calls don't cross-resolve
//   ✅ verify args preserve tool_id field name (FR-009 / I-D8 + I-V6)

import { test, expect, describe, beforeEach } from 'bun:test'
import { dispatchPrimitive, _resetCheckpointState } from './dispatchPrimitive.js'
import { PendingCallRegistry } from './pendingCallRegistry.js'
import type { ToolResultFrame } from '../../ipc/frames.generated.js'
import type { IPCBridge } from '../../ipc/bridge.js'
import type { ToolUseContext } from '../../Tool.js'

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/** Build a minimal fake ToolResultFrame for tests. */
function fakeToolResultFrame(opts: {
  callId: string
  envelope?: Record<string, unknown>
  transactionId?: string
}): ToolResultFrame {
  return {
    kind: 'tool_result',
    role: 'backend',
    version: '1.0',
    session_id: 'test-session',
    correlation_id: 'test-correlation',
    ts: new Date().toISOString(),
    call_id: opts.callId,
    envelope: {
      kind: 'lookup',
      ...opts.envelope,
    },
    transaction_id: opts.transactionId ?? null,
  } as unknown as ToolResultFrame
}

/** Build a minimal fake ToolUseContext for tests. */
function fakeContext(): ToolUseContext {
  return {
    toolUseId: 'test-tool-use-id',
    options: {
      sessionId: 'test-session',
      commands: [],
      debug: false,
      mainLoopModel: 'test',
      tools: [],
      verbose: false,
      thinkingConfig: {},
      mcpClients: [],
      mcpResources: {},
      isNonInteractiveSession: true,
      agentDefinitions: { definitions: [] },
    },
    abortController: new AbortController(),
    readFileState: new Map() as unknown as import('../../Tool.js').FileStateCache,
    getAppState: () => ({} as import('../../Tool.js').AppState),
    setAppState: () => {},
  } as unknown as ToolUseContext
}

/** Build a mock IPCBridge that captures sent frames. */
function mockBridge(opts?: {
  onSend?: (frame: import('../../ipc/frames.generated.js').IPCFrame) => void
}): IPCBridge {
  const sentFrames: import('../../ipc/frames.generated.js').IPCFrame[] = []
  return {
    send(frame) {
      sentFrames.push(frame)
      opts?.onSend?.(frame)
      return true
    },
    frames() { return (async function* () {})() },
    close: async () => {},
    proc: {} as ReturnType<typeof Bun.spawn>,
    onFrame: undefined,
    applied_frame_seqs: new Set(),
    lastSeenCorrelationId: null,
    lastSeenFrameSeq: null,
    setSessionCredentials: () => {},
    signalDrop: () => {},
  }
}

// ---------------------------------------------------------------------------
// Test: PendingCallRegistry basics
// ---------------------------------------------------------------------------

describe('PendingCallRegistry', () => {
  let registry: PendingCallRegistry

  beforeEach(() => {
    registry = new PendingCallRegistry()
  })

  test('register + has + size', () => {
    let timeoutHandle: ReturnType<typeof setTimeout> | undefined
    const frame = new Promise<ToolResultFrame>((resolve, reject) => {
      timeoutHandle = setTimeout(() => reject(new Error('timeout')), 5000)
      registry.register({
        callId: 'call-1',
        primitive: 'lookup',
        resolve,
        reject,
        timeoutHandle: timeoutHandle!,
      })
    })

    expect(registry.has('call-1')).toBe(true)
    expect(registry.size()).toBe(1)

    // Clean up
    clearTimeout(timeoutHandle)
    registry.reject('call-1', new Error('cleanup'))
    void frame.catch(() => {})
  })

  test('duplicate register throws', () => {
    const noop = () => {}
    const th = setTimeout(noop, 5000)
    registry.register({ callId: 'dup', primitive: 'lookup', resolve: noop as never, reject: noop as never, timeoutHandle: th })

    expect(() => {
      const th2 = setTimeout(noop, 5000)
      registry.register({ callId: 'dup', primitive: 'lookup', resolve: noop as never, reject: noop as never, timeoutHandle: th2 })
    }).toThrow(/duplicate callId/)

    clearTimeout(th)
    registry.reject('dup', new Error('cleanup'))
  })

  test('resolve returns true when found, false when not found', () => {
    const noop = () => {}
    let resolvedFrame: ToolResultFrame | null = null
    const th = setTimeout(noop, 5000)
    const p = new Promise<ToolResultFrame>((resolve, reject) => {
      registry.register({
        callId: 'call-ok',
        primitive: 'verify',
        resolve: (f) => { resolvedFrame = f; resolve(f) },
        reject,
        timeoutHandle: th,
      })
    })
    const frame = fakeToolResultFrame({ callId: 'call-ok' })
    const found = registry.resolve('call-ok', frame)
    expect(found).toBe(true)
    expect(registry.has('call-ok')).toBe(false)

    const notFound = registry.resolve('non-existent', frame)
    expect(notFound).toBe(false)

    void p.then(() => {})
  })

  test('clear() cancels all pending calls', () => {
    const noop = () => {}
    const th1 = setTimeout(noop, 5000)
    const th2 = setTimeout(noop, 5000)
    const errors: Error[] = []

    const p1 = new Promise<ToolResultFrame>((resolve, reject) => {
      registry.register({ callId: 'c1', primitive: 'lookup', resolve, reject: (e) => { errors.push(e); reject(e) }, timeoutHandle: th1 })
    })
    const p2 = new Promise<ToolResultFrame>((resolve, reject) => {
      registry.register({ callId: 'c2', primitive: 'submit', resolve, reject: (e) => { errors.push(e); reject(e) }, timeoutHandle: th2 })
    })

    registry.clear()
    expect(registry.size()).toBe(0)

    // Both promises should be rejected via clear()
    void p1.catch(() => {})
    void p2.catch(() => {})
  })
})

// ---------------------------------------------------------------------------
// Test: dispatchPrimitive — successful round-trip
// ---------------------------------------------------------------------------

describe('dispatchPrimitive', () => {
  let registry: PendingCallRegistry
  let context: ToolUseContext

  beforeEach(() => {
    registry = new PendingCallRegistry()
    context = fakeContext()
    _resetCheckpointState()
  })

  test('successful round-trip (lookup)', async () => {
    let capturedCallId = ''

    const bridge = mockBridge({
      onSend: (frame) => {
        // Capture the callId from the emitted tool_call frame, then immediately
        // resolve the pending call to simulate a backend tool_result response.
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          capturedCallId = toolFrame.call_id
          // Resolve asynchronously so the registry.register() has returned first.
          queueMicrotask(() => {
            const resultFrame = fakeToolResultFrame({
              callId: capturedCallId,
              envelope: { kind: 'lookup', results: ['adapter-1'] },
            })
            registry.resolve(capturedCallId, resultFrame)
          })
        }
      },
    })

    const result = await dispatchPrimitive({
      primitive: 'lookup',
      args: { mode: 'search', query: '병원' },
      context,
      registry,
      bridge,
      timeoutMs: 5000,
    })

    expect((result.data as Record<string, unknown>)['ok']).toBe(true)
    const okData = result.data as { ok: true; result: Record<string, unknown> }
    expect(okData.result['kind']).toBe('lookup')
  })

  // ---------------------------------------------------------------------------
  // Test: Timeout rejection (I-D6)
  // ---------------------------------------------------------------------------

  test('timeout rejection returns ok=false with Korean message', async () => {
    // Bridge that never resolves the pending call
    const bridge = mockBridge()

    const result = await dispatchPrimitive({
      primitive: 'submit',
      args: { tool_id: 'test', params: {} },
      context,
      registry,
      bridge,
      timeoutMs: 50, // very short timeout for test speed
    })

    const errData = result.data as { ok: false; error: string }
    expect(errData.ok).toBe(false)
    expect(errData.error).toBe('응답 시간이 초과되었습니다')
  }, 2000)

  // ---------------------------------------------------------------------------
  // Test: Error envelope passthrough (I-D7)
  // ---------------------------------------------------------------------------

  test('error envelope passthrough returns ok=false', async () => {
    const bridge = mockBridge({
      onSend: (frame) => {
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          queueMicrotask(() => {
            const errorFrame = fakeToolResultFrame({
              callId: toolFrame.call_id,
              envelope: {
                kind: 'verify',
                error: '인증이 거부되었습니다',
              },
            })
            registry.resolve(toolFrame.call_id, errorFrame)
          })
        }
      },
    })

    const result = await dispatchPrimitive({
      primitive: 'verify',
      args: { tool_id: 'mock_verify_module_modid', params: {} },
      context,
      registry,
      bridge,
      timeoutMs: 5000,
    })

    const errData = result.data as { ok: false; error: string }
    expect(errData.ok).toBe(false)
    expect(errData.error).toBe('인증이 거부되었습니다')
  })

  // ---------------------------------------------------------------------------
  // Test: Concurrent calls don't cross-resolve (I-D10)
  // ---------------------------------------------------------------------------

  test('concurrent calls resolve independently (no cross-resolve)', async () => {
    const resolvedCallIds: string[] = []
    const bridge = mockBridge({
      onSend: (frame) => {
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          resolvedCallIds.push(toolFrame.call_id)
        }
      },
    })

    // Start 3 concurrent dispatches (don't await yet)
    const p1 = dispatchPrimitive({ primitive: 'lookup', args: { id: 1 }, context, registry, bridge, timeoutMs: 5000 })
    const p2 = dispatchPrimitive({ primitive: 'verify', args: { id: 2 }, context, registry, bridge, timeoutMs: 5000 })
    const p3 = dispatchPrimitive({ primitive: 'submit', args: { id: 3 }, context, registry, bridge, timeoutMs: 5000 })

    // Wait for all 3 frames to be sent (microtask boundary)
    await new Promise<void>((r) => setTimeout(r, 10))

    expect(resolvedCallIds.length).toBe(3)
    const [id1, id2, id3] = resolvedCallIds

    // Resolve in reverse order to ensure cross-resolve doesn't occur
    registry.resolve(id3!, fakeToolResultFrame({ callId: id3!, envelope: { kind: 'submit', id: 3 } }))
    registry.resolve(id1!, fakeToolResultFrame({ callId: id1!, envelope: { kind: 'lookup', id: 1 } }))
    registry.resolve(id2!, fakeToolResultFrame({ callId: id2!, envelope: { kind: 'verify', id: 2 } }))

    const [r1, r2, r3] = await Promise.all([p1, p2, p3])

    // Each result must carry its own envelope, not another's
    const d1 = (r1.data as { ok: true; result: Record<string, unknown> }).result
    const d2 = (r2.data as { ok: true; result: Record<string, unknown> }).result
    const d3 = (r3.data as { ok: true; result: Record<string, unknown> }).result

    expect(d1['kind']).toBe('lookup')
    expect(d2['kind']).toBe('verify')
    expect(d3['kind']).toBe('submit')
  }, 5000)

  // ---------------------------------------------------------------------------
  // Test: verify args preserve tool_id field name (FR-009 / I-D8 / I-V6)
  // ---------------------------------------------------------------------------

  test('verify args forwarded verbatim — tool_id preserved, no translation', async () => {
    let capturedArguments: Record<string, unknown> | null = null

    const bridge = mockBridge({
      onSend: (frame) => {
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          capturedArguments = toolFrame.arguments as Record<string, unknown>
          queueMicrotask(() => {
            registry.resolve(toolFrame.call_id, fakeToolResultFrame({
              callId: toolFrame.call_id,
              envelope: { kind: 'verify', ok: true },
            }))
          })
        }
      },
    })

    const inputArgs = {
      tool_id: 'mock_verify_module_modid',
      params: {
        scope_list: ['lookup:hometax.simplified'],
        purpose_ko: '세금 신고',
        purpose_en: 'Tax filing',
      },
    }

    await dispatchPrimitive({
      primitive: 'verify',
      args: inputArgs,
      context,
      registry,
      bridge,
      timeoutMs: 5000,
    })

    // The IPC frame MUST carry {tool_id, params} verbatim (FR-009)
    expect(capturedArguments).not.toBeNull()
    expect(capturedArguments!['tool_id']).toBe('mock_verify_module_modid')
    expect(capturedArguments!['params']).toEqual(inputArgs.params)
    // Ensure no family_hint field was injected by TUI (backend's job)
    expect(capturedArguments!['family_hint']).toBeUndefined()
  })

  // ---------------------------------------------------------------------------
  // Test: CHECKPOINT marker emitted for matching submit result (T014 / I-P2)
  // ---------------------------------------------------------------------------

  test('CHECKPOINTreceipt token emitted once for matching submit result', async () => {
    // Override env for this test
    const origEnv = process.env['KOSMOS_SMOKE_CHECKPOINTS']
    process.env['KOSMOS_SMOKE_CHECKPOINTS'] = 'true'
    _resetCheckpointState()

    const stderrLines: string[] = []
    const origWrite = process.stderr.write.bind(process.stderr)
    process.stderr.write = ((data: string | Uint8Array) => {
      if (typeof data === 'string') stderrLines.push(data)
      return origWrite(data)
    }) as typeof process.stderr.write

    const bridge = mockBridge({
      onSend: (frame) => {
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          queueMicrotask(() => {
            // Frame with matching receipt in transaction_id
            const resultFrame = fakeToolResultFrame({
              callId: toolFrame.call_id,
              envelope: { kind: 'submit', transaction_id: 'hometax-2026-04-30-RX-ABCDE' },
              transactionId: 'hometax-2026-04-30-RX-ABCDE',
            })
            registry.resolve(toolFrame.call_id, resultFrame)
          })
        }
      },
    })

    await dispatchPrimitive({
      primitive: 'submit',
      args: { tool_id: 'mock_submit_hometax', params: {} },
      context,
      registry,
      bridge,
      timeoutMs: 5000,
    })

    // Restore
    process.stderr.write = origWrite
    if (origEnv === undefined) {
      delete process.env['KOSMOS_SMOKE_CHECKPOINTS']
    } else {
      process.env['KOSMOS_SMOKE_CHECKPOINTS'] = origEnv
    }

    const checkpoints = stderrLines.filter(l => l.includes('CHECKPOINTreceipt token observed'))
    expect(checkpoints.length).toBe(1)
  })

  // ---------------------------------------------------------------------------
  // Test: CHECKPOINT marker NOT emitted when env is not set (T014)
  // ---------------------------------------------------------------------------

  test('CHECKPOINTreceipt NOT emitted when KOSMOS_SMOKE_CHECKPOINTS is not set', async () => {
    const origEnv = process.env['KOSMOS_SMOKE_CHECKPOINTS']
    delete process.env['KOSMOS_SMOKE_CHECKPOINTS']
    _resetCheckpointState()

    const stderrLines: string[] = []
    const origWrite = process.stderr.write.bind(process.stderr)
    process.stderr.write = ((data: string | Uint8Array) => {
      if (typeof data === 'string') stderrLines.push(data)
      return origWrite(data)
    }) as typeof process.stderr.write

    const bridge = mockBridge({
      onSend: (frame) => {
        if ((frame as { kind?: string }).kind === 'tool_call') {
          const toolFrame = frame as import('../../ipc/frames.generated.js').ToolCallFrame
          queueMicrotask(() => {
            registry.resolve(toolFrame.call_id, fakeToolResultFrame({
              callId: toolFrame.call_id,
              envelope: { kind: 'submit' },
              transactionId: 'hometax-2026-04-30-RX-ABCDE',
            }))
          })
        }
      },
    })

    await dispatchPrimitive({
      primitive: 'submit',
      args: {},
      context,
      registry,
      bridge,
      timeoutMs: 5000,
    })

    process.stderr.write = origWrite
    if (origEnv !== undefined) process.env['KOSMOS_SMOKE_CHECKPOINTS'] = origEnv

    const checkpoints = stderrLines.filter(l => l.includes('CHECKPOINTreceipt token observed'))
    expect(checkpoints.length).toBe(0)
  })
})
