// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · Anthropic→FriendliAI LLM client.
//
// Emulates the `@anthropic-ai/sdk` Messages.create streaming-generator surface
// consumed by QueryEngine.ts and query.ts, but all wire traffic goes over the
// Spec 032 stdio IPC bridge (TS) → Python backend → FriendliAI Serverless.
// TS never speaks HTTPS to FriendliAI directly (docs/vision.md § L1-A A1,
// Constitution Principle I rewrite boundary).
//
// This file is a skeleton in Phase 2 (T003). Full stream() + complete() +
// OTEL wiring arrive in US1 tasks T007-T010.

import type { IPCBridge } from './bridge.js'
import type {
  KosmosMessageStreamParams,
  KosmosRawMessageStreamEvent,
  KosmosMessageFinal,
} from './llmTypes.js'

export const KOSMOS_DEFAULT_MODEL = 'LGAI-EXAONE/K-EXAONE-236B-A23B'

export type LLMClientErrorClass = 'llm' | 'tool' | 'network'

export class LLMClientError extends Error {
  readonly errorClass: LLMClientErrorClass
  readonly code: string
  readonly retryAfterMs?: number

  constructor(
    errorClass: LLMClientErrorClass,
    code: string,
    message: string,
    retryAfterMs?: number,
  ) {
    super(message)
    this.name = 'LLMClientError'
    this.errorClass = errorClass
    this.code = code
    this.retryAfterMs = retryAfterMs
  }
}

export interface LLMClientOptions {
  bridge: IPCBridge
  model?: string
  sessionId: string
}

/**
 * LLMClient — stdio-IPC-backed LLM client.
 *
 * Contracts/llm-client.md § 1.1 / § 1.2 define the full surface. This file is
 * currently a skeleton; stream() + complete() are wired in US1 tasks T007-T010.
 */
export class LLMClient {
  readonly bridge: IPCBridge
  readonly model: string
  readonly sessionId: string

  constructor(opts: LLMClientOptions) {
    this.bridge = opts.bridge
    this.model = opts.model ?? KOSMOS_DEFAULT_MODEL
    this.sessionId = opts.sessionId
  }

  /**
   * Begin an LLM turn.
   *
   * Not implemented in Phase 2 — see contracts/llm-client.md § 1.1 G1..G6.
   * Full async-generator body arrives in US1 task T007.
   */
  async *stream(
    _params: KosmosMessageStreamParams,
  ): AsyncGenerator<KosmosRawMessageStreamEvent, KosmosMessageFinal, void> {
    throw new LLMClientError(
      'network',
      'not_implemented',
      'LLMClient.stream() not implemented (Phase 2 skeleton; awaits US1 task T007)',
    )
    // Unreachable — present for type-checker happiness on the return type.
    // eslint-disable-next-line @typescript-eslint/no-unreachable
    yield undefined as never
  }

  /**
   * Non-streaming convenience — awaits stream() and collects into a final
   * KosmosMessageFinal. Stub in Phase 2.
   */
  async complete(_params: KosmosMessageStreamParams): Promise<KosmosMessageFinal> {
    throw new LLMClientError(
      'network',
      'not_implemented',
      'LLMClient.complete() not implemented (Phase 2 skeleton; awaits US1 task T008)',
    )
  }
}
