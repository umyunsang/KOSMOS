// SPDX-License-Identifier: Apache-2.0
// Epic #2077 K-EXAONE tool wiring · T013
//
// CC provider-contract invariants from contracts/stream-event-projection.md:
//   I1 — tool_call frame yields two stream events, not SystemMessage
//   I2 — content_block_start carries id/name/input from frame fields
//   I3 — provider stops at assistant(tool_use), matching Claude Code's
//        provider/query boundary; tool_result emission belongs to runTools
//   I4 — same backend-turn final prose is not emitted after tool_use
//
// Test harness: Bun mock.module() replaces bridgeSingleton and toolSerialization
// before the legacy backend-chat provider is loaded so queryModelWithStreaming
// drives against a FakeBridge that captures the
// ChatRequestFrame's correlation_id from send() and yields pre-staged IPC
// frames tagged with that exact id.
//
// Module paths are absolute so Bun's module-specifier cache key matches the
// key used by deps.ts (which imports via relative paths that resolve to the
// same absolute paths). Using relative paths from a different directory caused
// cache-key mismatches in Bun v1.3.12.

import { describe, test, expect, mock } from 'bun:test'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const TUI_ROOT = join(__dirname, '../..')

// ---------------------------------------------------------------------------
// FakeBridge factory
//
// send() captures the correlation_id from the ChatRequestFrame. The
// correlation_id is generated inside queryModelWithStreaming via randomUUID()
// and embedded in every outgoing ChatRequestFrame. deps.ts then filters
// incoming frames with `if (fa.correlation_id !== correlationId) continue`
// (line 156), so test frames MUST carry the exact same id.
//
// frames() spins-yields until send() has been called (which happens before
// the first for-await iteration inside deps.ts), then yields the staged
// frames built by the per-test factory function.
// ---------------------------------------------------------------------------

interface StagedFrame {
  kind: string
  correlation_id: string
  session_id: string
  ts: string
  role: string
  [k: string]: unknown
}

type FrameFactory = (correlationId: string) => StagedFrame[]

function makeFakeBridge(frameFactory: FrameFactory) {
  let capturedCorrelationId: string | null = null

  return {
    send(frame: unknown): boolean {
      const f = frame as { correlation_id?: string }
      capturedCorrelationId = f.correlation_id ?? null
      return true
    },
    async *frames(): AsyncIterable<unknown> {
      while (capturedCorrelationId === null) {
        await Promise.resolve()
      }
      const corrId = capturedCorrelationId
      for (const f of frameFactory(corrId)) {
        yield f
      }
    },
    close: async () => {},
    applied_frame_seqs: new Set<string>(),
    setSessionCredentials: (_sid: string, _tok: string) => {},
    lastSeenCorrelationId: null as string | null,
    lastSeenFrameSeq: null as number | null,
    signalDrop: () => {},
    // bridge.proc is read by crash-detector only; not exercised in unit tests.
    proc: {} as ReturnType<typeof Bun.spawn>,
  }
}

// ---------------------------------------------------------------------------
// Module mock setup
//
// mock.module() must be called BEFORE the module under test is imported.
// _currentBridge is swapped before each test via installBridge() and is
// returned by the mocked getOrCreateUmmayaBridge() as a live closure,
// so each test sees its own fresh FakeBridge.
// ---------------------------------------------------------------------------

let _currentBridge: ReturnType<typeof makeFakeBridge> | null = null

function installBridge(factory: FrameFactory): void {
  _currentBridge = makeFakeBridge(factory)
}

// deps.ts statically imports `services/compact/autoCompact.js`, which itself
// `import { feature } from 'bun:bundle'`. Bun 1.2.x in CI does not honour
// preload plugin onResolve for `bun:bundle` under the test runner, so mocking
// autoCompact directly is the most reliable way to keep this test self-
// contained — productionDeps().callModel does not invoke autocompact() in
// any of these scenarios anyway.
// deps.ts statically imports from services/compact/{autoCompact,microCompact}.ts,
// both of which `import { feature } from 'bun:bundle'`. Bun 1.2.x in CI does
// not honour preload plugin onResolve for `bun:bundle` under the test runner,
// so mocking these compact modules directly is the most reliable way to keep
// this test self-contained — productionDeps().callModel does not invoke
// autocompact() or microcompact() in any of these scenarios.
mock.module(join(TUI_ROOT, 'src/services/compact/autoCompact.js'), () => ({
  autoCompactIfNeeded: async () => ({ messages: [], compacted: false }),
  getEffectiveContextWindowSize: () => 200_000,
  AUTOCOMPACT_BUFFER_TOKENS: 13_000,
  WARNING_THRESHOLD_BUFFER_TOKENS: 20_000,
  ERROR_THRESHOLD_BUFFER_TOKENS: 20_000,
  MANUAL_COMPACT_BUFFER_TOKENS: 3_000,
  getAutoCompactThreshold: () => 100_000,
  calculateTokenWarningState: () => null,
  isAutoCompactEnabled: () => false,
  shouldAutoCompact: async () => false,
}))

mock.module(join(TUI_ROOT, 'src/services/compact/microCompact.js'), () => ({
  microcompactMessages: async (messages: unknown[]) => messages,
  TIME_BASED_MC_CLEARED_MESSAGE: '[Old tool result content cleared]',
  consumePendingCacheEdits: () => null,
  getPinnedCacheEdits: () => [],
  pinCacheEdits: () => {},
  markToolsSentToAPIState: () => {},
  resetMicrocompactState: () => {},
  estimateMessageTokens: () => 0,
  evaluateTimeBasedTrigger: () => null,
}))

mock.module(join(TUI_ROOT, 'src/ipc/bridgeSingleton.js'), () => ({
  getOrCreateUmmayaBridge: () => _currentBridge,
  getUmmayaBridgeSessionId: () => 'test-session-handlers',
  closeUmmayaBridge: async () => {},
}))

mock.module(join(TUI_ROOT, 'src/query/toolSerialization.js'), () => ({
  getToolDefinitionsForFrame: async () => [],
  toolToFunctionSchema: async () => ({}),
}))

mock.module(join(TUI_ROOT, 'src/utils/messages.js'), () => ({
  SYNTHETIC_MODEL: 'ummaya-test-model',
  SYNTHETIC_MESSAGES: new Set<string>(),
  isEmptyMessageText: (text: unknown) => text === '',
  createAssistantMessage: ({ content }: { content: unknown }) => ({
    type: 'assistant',
    uuid: 'assistant-message-stub',
    timestamp: new Date().toISOString(),
    message: {
      id: 'assistant-inner-stub',
      type: 'message',
      role: 'assistant',
      content:
        typeof content === 'string'
          ? [{ type: 'text', text: content }]
          : content,
      model: 'ummaya-test-model',
      stop_reason: null,
      stop_sequence: null,
      usage: {
        input_tokens: 0,
        output_tokens: 0,
        cache_creation_input_tokens: 0,
        cache_read_input_tokens: 0,
      },
    },
  }),
  createSystemMessage: (
    content: string,
    subtype = 'info',
    uuid = 'system-message-stub',
  ) => ({
    type: 'system',
    uuid,
    content,
    subtype,
    timestamp: new Date().toISOString(),
  }),
  createUserMessage: ({
    content,
    toolUseResult,
    sourceToolAssistantUUID,
  }: {
    content: unknown
    toolUseResult?: unknown
    sourceToolAssistantUUID?: string
  }) => ({
    type: 'user',
    uuid: 'user-message-stub',
    timestamp: new Date().toISOString(),
    message: { role: 'user', content },
    toolUseResult,
    sourceToolAssistantUUID,
  }),
}))

// Dynamic import AFTER mock.module() so the mocked bindings are in place
// when the legacy backend-chat provider resolves bridgeSingleton /
// toolSerialization. Production deps intentionally use services/api/claude.ts;
// this file now guards only the compatibility provider.
const { queryModelWithStreaming } = await import(
  join(TUI_ROOT, 'src/services/api/ummaya.js')
)

// ---------------------------------------------------------------------------
// Shared test runner
//
// Installs a fresh FakeBridge whose frames() yields the frames built by
// buildFrames(correlationId) — called after send() has captured the real
// correlation_id so every frame carries the correct id for deps.ts filtering.
// ---------------------------------------------------------------------------

function makeFrame(
  kind: string,
  corrId: string,
  extra: Record<string, unknown> = {},
): StagedFrame {
  return {
    kind,
    correlation_id: corrId,
    session_id: 'test-session-handlers',
    ts: new Date().toISOString(),
    role: 'backend',
    ...extra,
  }
}

async function run(buildFrames: (corrId: string) => StagedFrame[]): Promise<unknown[]> {
  const previousPrimary = process.env.UMMAYA_FRIENDLI_TOKEN
  process.env.UMMAYA_FRIENDLI_TOKEN = 'test-token-handlers'
  installBridge(buildFrames)
  try {
    const results: unknown[] = []
    for await (const ev of queryModelWithStreaming({
      messages: [{ type: 'user', message: { role: 'user', content: 'hi' } }],
      systemPrompt: 'test system prompt',
    })) {
      results.push(ev)
    }
    return results
  } finally {
    if (previousPrimary === undefined) {
      delete process.env.UMMAYA_FRIENDLI_TOKEN
    } else {
      process.env.UMMAYA_FRIENDLI_TOKEN = previousPrimary
    }
  }
}

describe('thinking persistence guard', () => {
  test('streams thinking_delta but omits thinking from terminal AssistantMessage by default', async () => {
    const previousPersistThinking = process.env.UMMAYA_PERSIST_THINKING
    delete process.env.UMMAYA_PERSIST_THINKING
    try {
      const results = await run((corrId) => [
        makeFrame('assistant_chunk', corrId, {
          message_id: 'mid-thinking-redacted',
          delta: '답변입니다',
          thinking: '내부 추론 전문',
          done: true,
        }),
      ])

      const thinkingEvents = results.filter((r) => {
        const event = (r as { event?: { delta?: { type?: string } } }).event
        return event?.delta?.type === 'thinking_delta'
      })
      expect(thinkingEvents).toHaveLength(1)

      const assistantMessages = results.filter(
        (r) => (r as { type?: string }).type === 'assistant',
      ) as Array<{
        message: { content: Array<{ type?: string; text?: string; thinking?: string }> }
      }>
      const terminal = assistantMessages[assistantMessages.length - 1]!
      expect(terminal.message.content.some((b) => b.type === 'thinking')).toBe(false)
      expect(terminal.message.content).toEqual([
        { type: 'text', text: '답변입니다' },
      ])
    } finally {
      if (previousPersistThinking === undefined) {
        delete process.env.UMMAYA_PERSIST_THINKING
      } else {
        process.env.UMMAYA_PERSIST_THINKING = previousPersistThinking
      }
    }
  })
})

// ---------------------------------------------------------------------------
// I1 — tool_call frame yields two stream events (content_block_start +
//       content_block_stop), not a SystemMessage.
// ---------------------------------------------------------------------------

describe('stream-event projection I1', () => {
  test('tool_call frame yields two stream events not SystemMessage', async () => {
    const results = await run((corrId) => [
      makeFrame('tool_call', corrId, {
        call_id: 'cid-001',
        name: 'lookup',
        arguments: { mode: 'fetch', tool_id: 'kma_forecast_fetch', query: 'test' },
      }),
      makeFrame('assistant_chunk', corrId, {
        message_id: 'mid-001',
        delta: '',
        done: true,
      }),
    ])

    type StreamEventItem = {
      type: 'stream_event'
      event: { type: string; index?: number; content_block?: { type?: string } }
    }

    const streamEvents = results.filter(
      (r) => (r as { type?: string }).type === 'stream_event',
    ) as StreamEventItem[]

    // content_block_start with content_block.type === 'tool_use' must be present
    const toolUseStart = streamEvents.find(
      (e) =>
        e.event.type === 'content_block_start' &&
        e.event.content_block?.type === 'tool_use',
    )
    expect(toolUseStart).toBeDefined()

    // A matching content_block_stop must follow
    const hasStop = streamEvents.some((e) => e.event.type === 'content_block_stop')
    expect(hasStop).toBe(true)

    // No SystemMessage must be yielded for a tool_call frame
    const systemMessages = results.filter(
      (r) => (r as { type?: string }).type === 'system',
    )
    expect(systemMessages).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// I2 — content_block_start carries id/name/input from frame fields.
// ---------------------------------------------------------------------------

describe('stream-event projection I2', () => {
  test('content_block_start carries id, name, input from frame fields', async () => {
    const callId = 'call-abc-123'
    const toolName = 'lookup'
    const toolArgs = { mode: 'fetch', tool_id: 'hira_hospital_search' }

    const results = await run((corrId) => [
      makeFrame('tool_call', corrId, {
        call_id: callId,
        name: toolName,
        arguments: toolArgs,
      }),
      makeFrame('assistant_chunk', corrId, {
        message_id: 'mid-002',
        delta: '',
        done: true,
      }),
    ])

    type StartEventItem = {
      type: 'stream_event'
      event: {
        type: string
        content_block?: { id?: string; name?: string; input?: unknown; type?: string }
      }
    }

    const streamEvents = results.filter(
      (r) => (r as { type?: string }).type === 'stream_event',
    ) as StartEventItem[]

    const toolUseStart = streamEvents.find(
      (e) =>
        e.event.type === 'content_block_start' &&
        e.event.content_block?.type === 'tool_use',
    )
    expect(toolUseStart).toBeDefined()

    const cb = toolUseStart!.event.content_block!
    expect(cb.id).toBe(callId)
    expect(cb.name).toBe(toolName)
    expect(cb.input).toEqual(toolArgs)
  })
})

// ---------------------------------------------------------------------------
// I3 — provider stops at assistant(tool_use); tool_result belongs to runTools.
// ---------------------------------------------------------------------------

describe('CC provider contract I3', () => {
  test('tool_result frame from the same backend turn is not yielded as a user message', async () => {
    const callId = 'call-res-001'
    const envelope = { kind: 'find', data: [{ name: '서울대병원' }] }

    const results = await run((corrId) => [
      makeFrame('tool_call', corrId, {
        call_id: callId,
        name: 'find',
        arguments: {},
      }),
      makeFrame('tool_result', corrId, {
        call_id: callId,
        envelope,
      }),
      makeFrame('assistant_chunk', corrId, {
        message_id: 'mid-003',
        delta: '',
        done: true,
      }),
    ])

    const userMessages = results.filter(
      (r) => (r as { type?: string }).type === 'user',
    )

    expect(userMessages).toHaveLength(0)
  })

  test('terminal assistant message contains tool_use only, not backend-completed final prose', async () => {
    const callId = 'call-render-order-001'

    const results = await run((corrId) => [
      makeFrame('tool_call', corrId, {
        call_id: callId,
        name: 'find',
        arguments: {
          mode: 'fetch',
          tool_id: 'kma_current_observation',
          params: { nx: 97, ny: 74 },
        },
      }),
      makeFrame('tool_result', corrId, {
        call_id: callId,
        envelope: {
          kind: 'find',
          result: { kind: 'record', items: [{ temperature_c: 21.8 }] },
        },
      }),
      makeFrame('assistant_chunk', corrId, {
        message_id: 'mid-render-order-001',
        delta: '현재 기온은 21.8도입니다.',
        done: true,
      }),
    ])

    type AssistantMsgItem = {
      type: 'assistant'
      message: {
        content: Array<{ type?: string; id?: string; text?: string }>
      }
    }

    const firstToolUseAssistantIndex = results.findIndex((r) => {
      const msg = r as AssistantMsgItem
      return (
        msg.type === 'assistant' &&
        msg.message.content.some(
          (block) => block.type === 'tool_use' && block.id === callId,
        )
      )
    })

    expect(firstToolUseAssistantIndex).toBeGreaterThanOrEqual(0)

    const assistantMessages = results.filter(
      (r) => (r as { type?: string }).type === 'assistant',
    ) as AssistantMsgItem[]
    const finalAssistant = assistantMessages[assistantMessages.length - 1]!
    expect(finalAssistant.message.content).toEqual([
      {
        type: 'tool_use',
        id: callId,
        name: 'find',
        input: {
          mode: 'fetch',
          tool_id: 'kma_current_observation',
          params: { nx: 97, ny: 74 },
        },
      },
    ])
    expect(JSON.stringify(results)).not.toContain('현재 기온은 21.8도입니다.')
  })
})

// ---------------------------------------------------------------------------
// I4 — backend-turn final prose after tool_use is ignored by provider.
// ---------------------------------------------------------------------------

describe('CC provider contract I4', () => {
  test('assistant final chunks staged after tool_call are not yielded in the same provider call', async () => {
    const results = await run((corrId) => [
      makeFrame('tool_call', corrId, {
        call_id: 'call-final-prose-001',
        name: 'find',
        arguments: {
          mode: 'fetch',
          tool_id: 'kma_forecast_fetch',
          params: {},
        },
      }),
      makeFrame('assistant_chunk', corrId, {
        message_id: 'mid-final-prose',
        delta: '이 문장은 같은 backend turn에서 나오면 안 됩니다.',
        done: true,
      }),
    ])

    expect(JSON.stringify(results)).not.toContain(
      '이 문장은 같은 backend turn에서 나오면 안 됩니다.',
    )
  })
})
