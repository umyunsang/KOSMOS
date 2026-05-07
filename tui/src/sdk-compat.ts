// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Epic #1633 P2 · @anthropic-ai/sdk compatibility shim.
//
// Purpose: every TS/TSX file that used to import from '@anthropic-ai/sdk'
// (or any sub-path like '/resources', '/resources/beta/messages/messages.mjs',
// '/streaming.mjs', '/error') now imports from 'src/sdk-compat.js' instead.
// The exports below are structural aliases into the KOSAX-native
// `tui/src/ipc/llmTypes.ts` type catalog, plus minimal stub classes for
// the two runtime error types that propagate through catch sites.
//
// This shim keeps 115+ caller files compiling without editing each one,
// while guaranteeing SC-002 (zero literal `@anthropic-ai/sdk` strings in
// runtime code) and FR-001 (no Anthropic SDK in the runtime graph).

import type {
  KosaxContentBlockParam,
  KosaxTextBlockParam,
  KosaxToolUseBlockParam,
  KosaxToolResultBlockParam,
  KosaxMessageParam,
  KosaxMessageStreamParams,
  KosaxRawMessageStreamEvent,
  KosaxToolDefinition,
  KosaxUsage,
  KosaxStopReason,
} from './ipc/llmTypes.js'

// ---------------------------------------------------------------------------
// Content block aliases (from the SDK's @anthropic-ai/sdk/resources/* tree)
// ---------------------------------------------------------------------------

export type ContentBlockParam = KosaxContentBlockParam
export type TextBlockParam = KosaxTextBlockParam
export type ToolUseBlock = KosaxToolUseBlockParam
export type ToolUseBlockParam = KosaxToolUseBlockParam
export type ToolResultBlockParam = KosaxToolResultBlockParam
export type MessageParam = KosaxMessageParam

/** Closed content-block representation (post-stream). Structurally identical
 * to the input-block form for KOSAX purposes. */
export type ContentBlock = KosaxContentBlockParam

// Image and thinking blocks are carried as opaque records — KOSAX does not
// introspect these but they must compile in the callers' type positions.
export type Base64ImageSource = {
  type: 'base64'
  media_type: string
  data: string
}

export type ImageBlockParam = {
  type: 'image'
  source: Base64ImageSource | { type: 'url'; url: string }
}

export type ThinkingBlock = {
  type: 'thinking'
  thinking: string
  signature?: string
}

export type ThinkingBlockParam = ThinkingBlock

// ---------------------------------------------------------------------------
// Beta-prefixed aliases (SDK's @anthropic-ai/sdk/resources/beta/* tree)
// ---------------------------------------------------------------------------
//
// All Beta* names resolve to the same Kosax structures — the "beta"
// namespace existed in CC because Anthropic shipped thinking + tool-use
// behind a beta flag; KOSAX merges them into a single surface.

export type BetaContentBlock = KosaxContentBlockParam
export type BetaContentBlockParam = KosaxContentBlockParam
export type BetaTextBlockParam = KosaxTextBlockParam
export type BetaImageBlockParam = ImageBlockParam
export type BetaToolResultBlockParam = KosaxToolResultBlockParam
export type BetaToolUseBlock = KosaxToolUseBlockParam
export type BetaToolUseBlockParam = KosaxToolUseBlockParam
export type BetaMessageParam = KosaxMessageParam
export type BetaMessage = {
  id: string
  role: 'assistant'
  model: string
  content: KosaxContentBlockParam[]
  stop_reason: KosaxStopReason
  usage: KosaxUsage
}
export type BetaMessageStreamParams = KosaxMessageStreamParams
export type BetaMessageStreamEvent = KosaxRawMessageStreamEvent
export type BetaRawMessageStreamEvent = KosaxRawMessageStreamEvent
export type BetaMessageDeltaUsage = KosaxUsage
export type BetaUsage = KosaxUsage
export type BetaStopReason = KosaxStopReason
export type BetaTool = KosaxToolDefinition
export type BetaToolUnion = KosaxToolDefinition
export type BetaToolChoiceAuto = { type: 'auto' }
export type BetaToolChoiceTool = { type: 'tool'; name: string }
export type BetaJSONOutputFormat = { type: 'json_object' }
export type BetaOutputConfig = Record<string, unknown>
export type BetaRequestDocumentBlock = Record<string, unknown>

// Some call sites import `Usage` via alias (`BetaUsage as Usage`). Keep a
// direct alias too.
export type Usage = KosaxUsage

// ---------------------------------------------------------------------------
// Streaming generator (SDK's @anthropic-ai/sdk/streaming.mjs)
// ---------------------------------------------------------------------------
//
// The SDK's Stream<T> is an async iterable with a synchronous abort hook.
// KOSAX streams come from the Spec 032 IPC bridge, which naturally provides
// AsyncIterable. We expose a structurally compatible shape.

export interface Stream<T> extends AsyncIterable<T> {
  controller?: AbortController
}

// ---------------------------------------------------------------------------
// Client + ClientOptions (SDK's top-level `Anthropic` class)
// ---------------------------------------------------------------------------
//
// Any `new Anthropic(...)` call site is dead in KOSAX because LLM traffic
// goes through `tui/src/ipc/llmClient.ts` via the stdio bridge. If one
// remains, it throws at construction time — fail-closed.

export type ClientOptions = {
  apiKey?: string
  baseURL?: string
  timeout?: number
  maxRetries?: number
  defaultHeaders?: Record<string, string>
  dangerouslyAllowBrowser?: boolean
  [key: string]: unknown
}

class AnthropicClientRemoved {
  constructor(_opts?: ClientOptions) {
    throw new Error(
      'Anthropic SDK client removed in Epic #1633. All LLM traffic now goes ' +
        'through tui/src/ipc/llmClient.ts → Python backend → FriendliAI. ' +
        'If this exception fires, the caller should be rewired to use LLMClient.',
    )
  }
}

export const Anthropic = AnthropicClientRemoved as unknown as new (
  opts?: ClientOptions,
) => unknown

export type Anthropic = InstanceType<typeof AnthropicClientRemoved>

// Default export mirrors the SDK's `import Anthropic from '@anthropic-ai/sdk'`
// pattern.
export default Anthropic

// ---------------------------------------------------------------------------
// Error classes (SDK's @anthropic-ai/sdk/error)
// ---------------------------------------------------------------------------
//
// CC code catches these by instanceof. KOSAX preserves the class hierarchy
// so `catch (err) { if (err instanceof APIError) ... }` still compiles and
// matches at runtime when the wire layer rethrows these shapes.

export class APIError extends Error {
  readonly status?: number
  readonly headers?: Record<string, string>
  readonly error?: unknown

  constructor(
    status: number | undefined,
    error: unknown,
    message: string | undefined,
    headers?: Record<string, string>,
  ) {
    super(message ?? 'APIError')
    this.name = 'APIError'
    this.status = status
    this.error = error
    this.headers = headers
  }
}

export class APIUserAbortError extends APIError {
  constructor(message: string = 'Request was aborted.') {
    super(undefined, undefined, message)
    this.name = 'APIUserAbortError'
  }
}

export class APIConnectionError extends APIError {
  constructor(message: string = 'Connection error.') {
    super(undefined, undefined, message)
    this.name = 'APIConnectionError'
  }
}

export class APIConnectionTimeoutError extends APIConnectionError {
  constructor(message: string = 'Request timed out.') {
    super(message)
    this.name = 'APIConnectionTimeoutError'
  }
}

export class AuthenticationError extends APIError {
  constructor(message: string = 'Authentication failed.') {
    super(401, undefined, message)
    this.name = 'AuthenticationError'
  }
}

export class RateLimitError extends APIError {
  constructor(message: string = 'Rate limit exceeded.') {
    super(429, undefined, message)
    this.name = 'RateLimitError'
  }
}

export class InternalServerError extends APIError {
  constructor(message: string = 'Internal server error.') {
    super(500, undefined, message)
    this.name = 'InternalServerError'
  }
}

export class NotFoundError extends APIError {
  constructor(message: string = 'Not found.') {
    super(404, undefined, message)
    this.name = 'NotFoundError'
  }
}

export class BadRequestError extends APIError {
  constructor(message: string = 'Bad request.') {
    super(400, undefined, message)
    this.name = 'BadRequestError'
  }
}

export class PermissionDeniedError extends APIError {
  constructor(message: string = 'Permission denied.') {
    super(403, undefined, message)
    this.name = 'PermissionDeniedError'
  }
}

export class UnprocessableEntityError extends APIError {
  constructor(message: string = 'Unprocessable entity.') {
    super(422, undefined, message)
    this.name = 'UnprocessableEntityError'
  }
}

export class ConflictError extends APIError {
  constructor(message: string = 'Conflict.') {
    super(409, undefined, message)
    this.name = 'ConflictError'
  }
}

// Beta namespace surface — Anthropic SDK's `@anthropic-ai/sdk/resources/beta`
// exposed these via `Beta.Messages.*`. We re-expose as module-level type
// aliases where reachable; the following is a no-op value namespace stub for
// call sites that reference `Anthropic.Beta.Messages.MessageCreateParams` etc.
export const Beta = {}
export type Beta = typeof Beta
export interface RedactedThinkingBlock {
  type: 'redacted_thinking'
  data: string
}
export type RedactedThinkingBlockParam = RedactedThinkingBlock
export type BetaRedactedThinkingBlock = RedactedThinkingBlock
export type BetaThinkingBlock = ThinkingBlock
export type BetaWebSearchTool20250305 = Record<string, unknown>

