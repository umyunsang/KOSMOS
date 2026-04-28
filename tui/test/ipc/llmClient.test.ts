// SPDX-License-Identifier: Apache-2.0
// T018 — LLMClient happy-path streaming contract
// Contract ref: specs/1633-dead-code-friendli-migration/contracts/llm-client.md § 1.1 / § 1.2 G1..G6

import { describe, test, expect, beforeEach } from 'bun:test'
import { LLMClient } from '../../src/ipc/llmClient.js'
import type { IPCBridge } from '../../src/ipc/bridge.js'
import type { IPCFrame, AssistantChunkFrame } from '../../src/ipc/frames.generated.js'
import type { KosmosRawMessageStreamEvent, KosmosMessageFinal } from '../../src/ipc/llmTypes.js'

// ---------------------------------------------------------------------------
// Helpers: minimal fake AssistantChunkFrame builder
// ---------------------------------------------------------------------------

const SESSION_ID = 'sess-1'
const MESSAGE_ID = 'msg-test-001'

function makeChunk(
  correlationId: string,
  delta: string,
  done: boolean,
  extra?: Record<string, unknown>,
): AssistantChunkFrame {
  return {
    kind: 'assistant_chunk',
    session_id: SESSION_ID,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'backend',
    frame_seq: 0,
    transaction_id: null,
    trailer: done ? { final: true, transaction_id: null, checksum_sha256: null } : null,
    message_id: MESSAGE_ID,
    delta,
    done,
    ...extra,
  } as AssistantChunkFrame
}

// ---------------------------------------------------------------------------
// Mock IPCBridge factory
// ---------------------------------------------------------------------------

function makeMockBridge(frames: IPCFrame[]): {
  bridge: IPCBridge
  sentFrames: IPCFrame[]
} {
  const sentFrames: IPCFrame[] = []

  // We need to capture the correlation_id that stream() mints so we can
  // replay frames with the right id. We do this lazily: the frame generator
  // reads from the sent frames list to know what correlation_id was used.
  let capturedCorrelationId: string | null = null

  const bridge: IPCBridge = {
    send(frame: IPCFrame): boolean {
      sentFrames.push(frame)
      // Capture correlation_id from the first sent frame (UserInputFrame).
      if (capturedCorrelationId === null) {
        capturedCorrelationId = frame.correlation_id
      }
      return true
    },
    async *frames(): AsyncIterable<IPCFrame> {
      // Wait for the first send so we know the correlation_id.
      while (capturedCorrelationId === null) {
        await new Promise<void>(r => setTimeout(r, 0))
      }
      const cid = capturedCorrelationId
      for (const f of frames) {
        // Stamp the captured correlation_id onto the frames.
        yield { ...f, correlation_id: cid } as IPCFrame
      }
    },
    async close(): Promise<void> {},
    // Cast proc to satisfy the interface; not exercised in unit tests.
    proc: undefined as unknown as ReturnType<typeof Bun.spawn>,
    applied_frame_seqs: new Set<string>(),
    setSessionCredentials(_sid: string, _tok: string): void {},
    lastSeenCorrelationId: null,
    lastSeenFrameSeq: null,
    signalDrop(): void {},
  }

  return { bridge, sentFrames }
}

// ---------------------------------------------------------------------------
// T018: happy-path streaming
// ---------------------------------------------------------------------------

describe('LLMClient.stream() — happy-path (T018)', () => {
  let sentFrames: IPCFrame[]
  let client: LLMClient

  beforeEach(() => {
    // Build a 3-frame response sequence. correlation_id stamped at yield time.
    const cannedFrames = [
      makeChunk('placeholder', '안녕', false),
      makeChunk('placeholder', '하세요', false),
      makeChunk('placeholder', '', true, {
        usage: { input_tokens: 10, output_tokens: 5 },
      }),
    ]
    const mock = makeMockBridge(cannedFrames)
    sentFrames = mock.sentFrames
    client = new LLMClient({
      bridge: mock.bridge,
      model: 'test-model',
      sessionId: SESSION_ID,
    })
  })

  test('yields correct event sequence', async () => {
    const gen = client.stream({
      model: 'test-model',
      messages: [{ role: 'user', content: '안녕' }],
      max_tokens: 100,
    })

    const events: KosmosRawMessageStreamEvent[] = []
    let finalValue: KosmosMessageFinal | null = null

    while (true) {
      const result = await gen.next()
      if (result.done) {
        finalValue = result.value as KosmosMessageFinal
        break
      }
      events.push(result.value)
    }

    // Verify event types in order
    const types = events.map(e => e.type)
    expect(types).toEqual([
      'message_start',
      'content_block_start',
      'content_block_delta',
      'content_block_delta',
      'content_block_stop',
      'message_delta',
      'message_stop',
    ])

    // Verify message_start has correct model
    const msgStart = events.find(e => e.type === 'message_start') as Extract<
      KosmosRawMessageStreamEvent,
      { type: 'message_start' }
    >
    expect(msgStart).toBeDefined()
    expect(msgStart!.message.model).toBe('test-model')

    // Verify content_block_start at index 0 with type text
    const blockStart = events.find(
      e => e.type === 'content_block_start',
    ) as Extract<KosmosRawMessageStreamEvent, { type: 'content_block_start' }>
    expect(blockStart).toBeDefined()
    expect(blockStart!.index).toBe(0)
    expect(blockStart!.content_block.type).toBe('text')

    // Verify the two content_block_delta events
    const deltas = events.filter(
      e => e.type === 'content_block_delta',
    ) as Extract<KosmosRawMessageStreamEvent, { type: 'content_block_delta' }>[]
    expect(deltas).toHaveLength(2)
    expect(deltas[0]!.delta.type).toBe('text_delta')
    expect((deltas[0]!.delta as { type: 'text_delta'; text: string }).text).toBe('안녕')
    expect((deltas[1]!.delta as { type: 'text_delta'; text: string }).text).toBe('하세요')

    // Verify content_block_stop at index 0
    const blockStop = events.find(
      e => e.type === 'content_block_stop',
    ) as Extract<KosmosRawMessageStreamEvent, { type: 'content_block_stop' }>
    expect(blockStop).toBeDefined()
    expect(blockStop!.index).toBe(0)

    // Verify message_delta with stop_reason and usage
    const msgDelta = events.find(e => e.type === 'message_delta') as Extract<
      KosmosRawMessageStreamEvent,
      { type: 'message_delta' }
    >
    expect(msgDelta).toBeDefined()
    expect(msgDelta!.delta.stop_reason).toBe('end_turn')
    expect(msgDelta!.usage?.input_tokens).toBe(10)

    // Verify message_stop present
    const msgStop = events.find(e => e.type === 'message_stop')
    expect(msgStop).toBeDefined()

    // Verify generator return value (KosmosMessageFinal)
    expect(finalValue).not.toBeNull()
    expect(finalValue!.stop_reason).toBe('end_turn')
    expect(finalValue!.usage.input_tokens).toBe(10)

    // Verify concatenated content
    const textBlock = finalValue!.content.find(b => b.type === 'text') as
      | { type: 'text'; text: string }
      | undefined
    expect(textBlock).toBeDefined()
    expect(textBlock!.text).toContain('안녕')
    expect(textBlock!.text).toContain('하세요')
  })

  test('sends exactly one ChatRequestFrame with UUIDv7 correlation_id', async () => {
    const gen = client.stream({
      model: 'test-model',
      messages: [{ role: 'user', content: '안녕' }],
      max_tokens: 100,
    })

    // Drain the generator
    while (!(await gen.next()).done) {}

    expect(sentFrames).toHaveLength(1)
    // Epic #2112: TUI now emits ChatRequestFrame (Spec 1978 ADR-0001) so the
    // backend's _handle_chat_request runs the CC agentic loop with tools.
    expect(sentFrames[0]!.kind).toBe('chat_request')

    // UUIDv7 regex: 8-4-7xxx-... pattern
    const uuidV7Regex = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-/
    expect(sentFrames[0]!.correlation_id).toMatch(uuidV7Regex)
  })
})
