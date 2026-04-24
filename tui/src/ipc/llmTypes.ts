// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · Anthropic→FriendliAI type shim.
//
// Structural replacements for the `@anthropic-ai/sdk` types that QueryEngine.ts
// and query.ts import. These types are in-process only; they never reach the
// wire. The Spec 032 IPC envelope (frames.generated.ts) carries actual frames
// to / from the Python backend.
//
// Responsibility: keep the TS agentic loop compiling after @anthropic-ai/sdk
// is removed, without rewriting the loop's control flow (rewrite-boundary
// rule, Constitution Principle I).

// ---------------------------------------------------------------------------
// Message roles and content blocks
// ---------------------------------------------------------------------------

export type KosmosRole = 'user' | 'assistant'

export type KosmosTextBlockParam = {
  type: 'text'
  text: string
}

export type KosmosToolUseBlockParam = {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
}

export type KosmosToolResultBlockParam = {
  type: 'tool_result'
  tool_use_id: string
  content: string | KosmosContentBlockParam[]
  is_error?: boolean
}

export type KosmosContentBlockParam =
  | KosmosTextBlockParam
  | KosmosToolUseBlockParam
  | KosmosToolResultBlockParam

// ---------------------------------------------------------------------------
// Messages + tool definitions
// ---------------------------------------------------------------------------

export type KosmosMessageParam = {
  role: KosmosRole
  content: string | KosmosContentBlockParam[]
}

export type KosmosToolDefinition = {
  name: string
  description?: string
  input_schema: { type: 'object'; [k: string]: unknown }
}

// ---------------------------------------------------------------------------
// Stream parameters + usage
// ---------------------------------------------------------------------------

export type KosmosMessageStreamParams = {
  model: string
  system?: string
  messages: KosmosMessageParam[]
  tools?: KosmosToolDefinition[]
  max_tokens: number
  temperature?: number
  metadata?: Record<string, string>
}

export type KosmosUsage = {
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens?: number
}

// ---------------------------------------------------------------------------
// Streaming events (structural compatibility with Anthropic's SDK event shape)
// ---------------------------------------------------------------------------

export type KosmosStopReason = 'end_turn' | 'max_tokens' | 'tool_use' | 'stop_sequence'

export type KosmosMessageStart = {
  type: 'message_start'
  message: {
    id: string
    role: 'assistant'
    model: string
  }
}

export type KosmosContentBlockStart = {
  type: 'content_block_start'
  index: number
  content_block: KosmosContentBlockParam
}

export type KosmosTextDelta = {
  type: 'text_delta'
  text: string
}

export type KosmosInputJsonDelta = {
  type: 'input_json_delta'
  partial_json: string
}

export type KosmosContentBlockDelta = {
  type: 'content_block_delta'
  index: number
  delta: KosmosTextDelta | KosmosInputJsonDelta
}

export type KosmosContentBlockStop = {
  type: 'content_block_stop'
  index: number
}

export type KosmosMessageDelta = {
  type: 'message_delta'
  delta: {
    stop_reason?: KosmosStopReason
  }
  usage?: KosmosUsage
}

export type KosmosMessageStop = {
  type: 'message_stop'
}

export type KosmosRawMessageStreamEvent =
  | KosmosMessageStart
  | KosmosContentBlockStart
  | KosmosContentBlockDelta
  | KosmosContentBlockStop
  | KosmosMessageDelta
  | KosmosMessageStop

// ---------------------------------------------------------------------------
// Finalized message returned by LLMClient.complete() + LLMClient.stream() return
// ---------------------------------------------------------------------------

export type KosmosMessageFinal = {
  id: string
  role: 'assistant'
  model: string
  content: KosmosContentBlockParam[]
  stop_reason: KosmosStopReason
  usage: KosmosUsage
}
