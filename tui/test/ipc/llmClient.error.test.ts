// SPDX-License-Identifier: Apache-2.0
// T019 — LLMClient error path: ErrorFrame(class='llm', code='auth') triggers immediate throw
// Contract ref: specs/1633-dead-code-friendli-migration/contracts/llm-client.md § 1.2 G4

import { describe, test, expect, beforeEach } from 'bun:test'
import { LLMClient, LLMClientError } from '../../src/ipc/llmClient.js'
import type { IPCBridge } from '../../src/ipc/bridge.js'
import type { IPCFrame, ErrorFrame } from '../../src/ipc/frames.generated.js'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SESSION_ID = 'sess-error-1'

function makeErrorFrame(correlationId: string): ErrorFrame {
  return {
    kind: 'error',
    session_id: SESSION_ID,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'backend',
    frame_seq: 1,
    transaction_id: null,
    trailer: { final: true, transaction_id: null, checksum_sha256: null },
    code: 'auth',
    message: 'FRIENDLI_API_KEY invalid',
    // details carries the class discriminator as per the error handling in llmClient.ts:
    // errClass = details['class'] === 'llm' ? 'llm' : ...
    details: { class: 'llm', code: 'auth' },
  } as ErrorFrame
}

// Mock IPCBridge that yields a single ErrorFrame matching the sent correlation_id.
function makeMockBridgeWithError(): {
  bridge: IPCBridge
  sentFrames: IPCFrame[]
} {
  const sentFrames: IPCFrame[] = []
  let capturedCorrelationId: string | null = null

  const bridge: IPCBridge = {
    send(frame: IPCFrame): boolean {
      sentFrames.push(frame)
      if (capturedCorrelationId === null) {
        capturedCorrelationId = frame.correlation_id
      }
      return true
    },
    async *frames(): AsyncIterable<IPCFrame> {
      // Wait for send to be called to capture the correlation_id.
      while (capturedCorrelationId === null) {
        await new Promise<void>(r => setTimeout(r, 0))
      }
      yield makeErrorFrame(capturedCorrelationId)
    },
    async close(): Promise<void> {},
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
// T019: error path — auth ErrorFrame triggers LLMClientError, no retry
// ---------------------------------------------------------------------------

describe('LLMClient.stream() — ErrorFrame auth fail-closed (T019, G4)', () => {
  let sentFrames: IPCFrame[]
  let client: LLMClient

  beforeEach(() => {
    const mock = makeMockBridgeWithError()
    sentFrames = mock.sentFrames
    client = new LLMClient({
      bridge: mock.bridge,
      model: 'test-model',
      sessionId: SESSION_ID,
    })
  })

  test('throws LLMClientError when ErrorFrame(class=llm, code=auth) is received', async () => {
    let thrown: unknown = null

    try {
      const gen = client.stream({
        model: 'test-model',
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 100,
      })
      // Consume the generator; it should throw before yielding any events.
      for await (const _ of gen) {
        // Should not reach here
      }
    } catch (err) {
      thrown = err
    }

    // Error must be an LLMClientError
    expect(thrown).not.toBeNull()
    expect(thrown).toBeInstanceOf(LLMClientError)
  })

  test('thrown LLMClientError has errorClass=llm and code=auth', async () => {
    let thrown: LLMClientError | null = null

    try {
      for await (const _ of client.stream({
        model: 'test-model',
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 100,
      })) {}
    } catch (err) {
      if (err instanceof LLMClientError) {
        thrown = err
      }
    }

    expect(thrown).not.toBeNull()
    expect(thrown!.errorClass).toBe('llm')
    expect(thrown!.code).toBe('auth')
  })

  test('exactly one outbound ChatRequestFrame sent — no retry (G4)', async () => {
    try {
      for await (const _ of client.stream({
        model: 'test-model',
        messages: [{ role: 'user', content: 'test' }],
        max_tokens: 100,
      })) {}
    } catch {
      // Expected throw — we only care about sentFrames count
    }

    // G4: fail-closed on auth — no retry means exactly one outbound frame.
    // Epic #2112: TUI now emits ChatRequestFrame (Spec 1978 ADR-0001).
    expect(sentFrames).toHaveLength(1)
    expect(sentFrames[0]!.kind).toBe('chat_request')
  })
})
