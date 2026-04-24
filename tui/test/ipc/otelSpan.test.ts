// SPDX-License-Identifier: Apache-2.0
// T021 — LLMClient.complete() emits gen_ai.client.invoke OTEL span with required attributes
// Contract ref: specs/1633-dead-code-friendli-migration/contracts/llm-client.md § 4
// SC refs: SC-008, SC-010

import { describe, test, expect, beforeEach } from 'bun:test'
import { trace, SpanStatusCode } from '@opentelemetry/api'
import {
  BasicTracerProvider,
  InMemorySpanExporter,
  SimpleSpanProcessor,
} from '@opentelemetry/sdk-trace-base'
import { LLMClient, KOSMOS_DEFAULT_MODEL } from '../../src/ipc/llmClient.js'
import type { IPCBridge } from '../../src/ipc/bridge.js'
import type { IPCFrame, AssistantChunkFrame } from '../../src/ipc/frames.generated.js'

// ---------------------------------------------------------------------------
// OTEL in-memory provider — initialized once at module level.
//
// @opentelemetry/api enforces a singleton global provider: calls to
// trace.setGlobalTracerProvider() after the first registration are silently
// ignored (OTEL design intent — prevents accidental provider replacement).
// Therefore we create one exporter + provider here and call reset() in
// beforeEach to clear accumulated spans between tests.
// ---------------------------------------------------------------------------

const _exporter = new InMemorySpanExporter()
const _provider = new BasicTracerProvider({
  spanProcessors: [new SimpleSpanProcessor(_exporter)],
})
// Register once. If another test file has already registered a provider this
// call is a no-op; tests below still work because they check _exporter which
// is wired into the processor above.
trace.setGlobalTracerProvider(_provider)

// ---------------------------------------------------------------------------
// Helpers: minimal canned bridge
// ---------------------------------------------------------------------------

const SESSION_ID = 'sess-1'
const FAKE_PROMPT_HASH = 'a'.repeat(64)

function makeDoneChunk(correlationId: string): AssistantChunkFrame {
  return {
    kind: 'assistant_chunk',
    session_id: SESSION_ID,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'backend',
    frame_seq: 1,
    transaction_id: null,
    trailer: { final: true, transaction_id: null, checksum_sha256: null },
    message_id: 'msg-otel-001',
    delta: '안녕',
    done: true,
    // Forward-compat usage extension field (read by _extractUsage in llmClient.ts)
    usage: { input_tokens: 7, output_tokens: 3 },
  } as AssistantChunkFrame & { usage: { input_tokens: number; output_tokens: number } }
}

function makeMockBridgeWithPromptHash(systemPromptHash: string): {
  bridge: IPCBridge
  sentFrames: IPCFrame[]
} {
  const sentFrames: IPCFrame[] = []
  let capturedCorrelationId: string | null = null

  const bridge = {
    // T010: systemPromptHash is read via (this.bridge as any).systemPromptHash in llmClient.ts
    systemPromptHash,

    send(frame: IPCFrame): boolean {
      sentFrames.push(frame)
      if (capturedCorrelationId === null) {
        capturedCorrelationId = frame.correlation_id
      }
      return true
    },
    async *frames(): AsyncIterable<IPCFrame> {
      while (capturedCorrelationId === null) {
        await new Promise<void>(r => setTimeout(r, 0))
      }
      yield makeDoneChunk(capturedCorrelationId)
    },
    async close(): Promise<void> {},
    proc: undefined as unknown as ReturnType<typeof Bun.spawn>,
    applied_frame_seqs: new Set<string>(),
    setSessionCredentials(_sid: string, _tok: string): void {},
    lastSeenCorrelationId: null,
    lastSeenFrameSeq: null,
    signalDrop(): void {},
  } as IPCBridge & { systemPromptHash: string }

  return { bridge, sentFrames }
}

// ---------------------------------------------------------------------------
// T021 tests
// ---------------------------------------------------------------------------

describe('LLMClient.complete() — OTEL gen_ai.client.invoke span (T021, SC-008/SC-010)', () => {
  beforeEach(() => {
    // Reset exporter so each test starts with a clean span list.
    _exporter.reset()
  })

  test('emits exactly one gen_ai.client.invoke span on complete()', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const spans = _exporter.getFinishedSpans()
    const invokeSpans = spans.filter(s => s.name === 'gen_ai.client.invoke')
    expect(invokeSpans).toHaveLength(1)
  })

  test('span has gen_ai.system === friendli_exaone', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    expect(span!.attributes['gen_ai.system']).toBe('friendli_exaone')
  })

  test('span gen_ai.request.model equals KOSMOS_DEFAULT_MODEL', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    expect(span!.attributes['gen_ai.request.model']).toBe(KOSMOS_DEFAULT_MODEL)
  })

  test('span has kosmos.session_id === sess-1', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    expect(span!.attributes['kosmos.session_id']).toBe(SESSION_ID)
  })

  test('span kosmos.correlation_id matches UUIDv7 pattern', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    const correlationId = span!.attributes['kosmos.correlation_id']
    expect(typeof correlationId).toBe('string')
    expect(correlationId as string).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-/)
  })

  test('span kosmos.prompt.hash equals the bridge systemPromptHash', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    expect(span!.attributes['kosmos.prompt.hash']).toBe(FAKE_PROMPT_HASH)
  })

  test('span is ended with status OK on successful complete()', async () => {
    const { bridge } = makeMockBridgeWithPromptHash(FAKE_PROMPT_HASH)
    const client = new LLMClient({
      bridge,
      model: KOSMOS_DEFAULT_MODEL,
      sessionId: SESSION_ID,
    })

    await client.complete({
      model: KOSMOS_DEFAULT_MODEL,
      messages: [{ role: 'user', content: '테스트' }],
      max_tokens: 50,
    })

    const span = _exporter.getFinishedSpans().find(s => s.name === 'gen_ai.client.invoke')
    expect(span).toBeDefined()
    expect(span!.status.code).toBe(SpanStatusCode.OK)
    // A finished span has a non-zero end time (SDK stores as HrTime [sec, ns]).
    // endTime[0] > 0 confirms span.end() was called.
    expect(span!.endTime[0]).toBeGreaterThan(0)
  })
})
