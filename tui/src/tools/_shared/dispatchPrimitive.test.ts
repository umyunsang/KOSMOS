// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic ζ #2297 Phase 0b · T008 (revised post-smoke 2026-04-30)
//
// Unit tests for dispatchPrimitive.ts (server-side-ack architecture).
//
// Architecture note: live smoke on 2026-04-30 revealed the backend's
// `_handle_chat_request` runs the full agentic loop server-side and
// emits its own tool_result frames; the TUI's CC SDK Tool.call() has
// no inbound-tool_call counterpart on the backend, so the original
// IPC-dispatch design timed out. The revised dispatcher returns a
// synthetic-success ack envelope immediately so the SDK turn closes
// without re-triggering execution. See the dispatchPrimitive.ts header
// for the full rationale.

import { test, expect, describe, beforeEach } from 'bun:test'
import { dispatchPrimitive } from './dispatchPrimitive.js'
import { PendingCallRegistry } from './pendingCallRegistry.js'
import type { IPCBridge } from '../../ipc/bridge.js'
import type { ToolUseContext } from '../../Tool.js'

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function fakeContext(toolUseId = 'test-tool-use-id'): ToolUseContext {
  return {
    toolUseId,
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
    },
  } as unknown as ToolUseContext
}

function fakeBridge(): IPCBridge {
  return {
    send: () => true,
    frames: () => ({ [Symbol.asyncIterator]: () => ({ next: () => Promise.resolve({ done: true, value: undefined }) }) }) as unknown as AsyncIterable<never>,
    close: () => Promise.resolve(),
    proc: {} as ReturnType<typeof Bun.spawn>,
    applied_frame_seqs: new Set(),
    setSessionCredentials: () => {},
    lastSeenCorrelationId: null,
    lastSeenFrameSeq: null,
  } as unknown as IPCBridge
}

// ---------------------------------------------------------------------------
// Tests — server-side-ack contract
// ---------------------------------------------------------------------------

describe('dispatchPrimitive (server-side-ack)', () => {
  let registry: PendingCallRegistry

  beforeEach(() => {
    registry = new PendingCallRegistry()
  })

  test('lookup returns ok=true with ack envelope', async () => {
    const result = (await dispatchPrimitive({
      primitive: 'lookup',
      args: { mode: 'search', query: '날씨' },
      context: fakeContext('lookup-use-1'),
      registry,
      bridge: fakeBridge(),
    })) as unknown as { data: { ok: boolean; result?: Record<string, unknown> } }

    expect(result.data.ok).toBe(true)
    expect(result.data.result?.['dispatched_via']).toBe('backend-server-side')
    expect(result.data.result?.['primitive']).toBe('lookup')
    expect(result.data.result?.['tool_use_id']).toBe('lookup-use-1')
  })

  test('verify forwards args verbatim — tool_id preserved (FR-009 / I-V6)', async () => {
    const args = {
      tool_id: 'mock_verify_module_modid',
      params: {
        scope_list: ['lookup:hometax.simplified'],
        purpose_ko: '종합소득세 신고',
        purpose_en: 'Tax return',
      },
    }

    const result = (await dispatchPrimitive({
      primitive: 'verify',
      args,
      context: fakeContext('verify-use-1'),
      registry,
      bridge: fakeBridge(),
    })) as unknown as { data: { ok: boolean; result?: Record<string, unknown> } }

    expect(result.data.ok).toBe(true)
    // The dispatcher does NOT translate tool_id at the TUI layer (FR-009).
    // The server-side-ack architecture leaves args untouched on the
    // wire — backend's `_VerifyInputForLLM` pre-validator owns translation.
    expect(args.tool_id).toBe('mock_verify_module_modid')
    expect(args.params.scope_list).toEqual(['lookup:hometax.simplified'])
  })

  test('submit returns ack with submit primitive name', async () => {
    const result = (await dispatchPrimitive({
      primitive: 'submit',
      args: { tool_id: 'mock_submit_module_hometax_taxreturn' },
      context: fakeContext('submit-use-1'),
      registry,
      bridge: fakeBridge(),
    })) as unknown as { data: { ok: boolean; result?: Record<string, unknown> } }

    expect(result.data.ok).toBe(true)
    expect(result.data.result?.['primitive']).toBe('submit')
  })

  test('subscribe returns ack with subscribe primitive name', async () => {
    const result = (await dispatchPrimitive({
      primitive: 'subscribe',
      args: { tool_id: 'mock_subscribe_module_test' },
      context: fakeContext('subscribe-use-1'),
      registry,
      bridge: fakeBridge(),
    })) as unknown as { data: { ok: boolean; result?: Record<string, unknown> } }

    expect(result.data.ok).toBe(true)
    expect(result.data.result?.['primitive']).toBe('subscribe')
  })

  test('missing toolUseId surfaces null in ack envelope', async () => {
    const ctx = {
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
      },
    } as unknown as ToolUseContext

    const result = (await dispatchPrimitive({
      primitive: 'lookup',
      args: {},
      context: ctx,
      registry,
      bridge: fakeBridge(),
    })) as unknown as { data: { ok: boolean; result?: Record<string, unknown> } }

    expect(result.data.ok).toBe(true)
    expect(result.data.result?.['tool_use_id']).toBe(null)
  })

  test('does NOT send IPC tool_call frame (server-side-ack architecture)', async () => {
    let sendCalled = false
    const bridge = {
      ...fakeBridge(),
      send: () => {
        sendCalled = true
        return true
      },
    } as unknown as IPCBridge

    await dispatchPrimitive({
      primitive: 'lookup',
      args: {},
      context: fakeContext(),
      registry,
      bridge,
    })

    // Per the server-side-ack architecture, the dispatcher does NOT emit
    // a fresh tool_call frame — the backend's `_handle_chat_request`
    // already dispatches internally.
    expect(sendCalled).toBe(false)
  })

  test('completes synchronously (no timeout path under default settings)', async () => {
    const start = Date.now()
    await dispatchPrimitive({
      primitive: 'lookup',
      args: {},
      context: fakeContext(),
      registry,
      bridge: fakeBridge(),
    })
    const elapsed = Date.now() - start
    // Server-side-ack returns immediately — should complete in well under 1s.
    expect(elapsed).toBeLessThan(1000)
  })
})
