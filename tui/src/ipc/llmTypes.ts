// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Epic #1633 P2 · Anthropic→FriendliAI type shim.
//
// Structural replacements for the Anthropic SDK types that QueryEngine.ts
// and query.ts import. These types are in-process only; they never reach the
// wire. The Spec 032 IPC envelope (frames.generated.ts) carries actual frames
// to / from the Python backend.
//
// Responsibility: keep the TS agentic loop compiling after the Anthropic SDK
// is removed, without rewriting the loop's control flow (rewrite-boundary
// rule, Constitution Principle I).

// ---------------------------------------------------------------------------
// Message roles and content blocks
// ---------------------------------------------------------------------------

export type KosaxRole = 'user' | 'assistant'

export type KosaxTextBlockParam = {
  type: 'text'
  text: string
}

export type KosaxToolUseBlockParam = {
  type: 'tool_use'
  id: string
  name: string
  input: Record<string, unknown>
}

export type KosaxToolResultBlockParam = {
  type: 'tool_result'
  tool_use_id: string
  content: string | KosaxContentBlockParam[]
  is_error?: boolean
}

export type KosaxContentBlockParam =
  | KosaxTextBlockParam
  | KosaxToolUseBlockParam
  | KosaxToolResultBlockParam

// ---------------------------------------------------------------------------
// Messages + tool definitions
// ---------------------------------------------------------------------------

export type KosaxMessageParam = {
  role: KosaxRole
  content: string | KosaxContentBlockParam[]
}

export type KosaxToolDefinition = {
  name: string
  description?: string
  input_schema: { type: 'object'; [k: string]: unknown }
}

// ---------------------------------------------------------------------------
// Stream parameters + usage
// ---------------------------------------------------------------------------

export type KosaxMessageStreamParams = {
  model: string
  system?: string
  messages: KosaxMessageParam[]
  tools?: KosaxToolDefinition[]
  max_tokens: number
  temperature?: number
  metadata?: Record<string, string>
}

export type KosaxUsage = {
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens?: number
}

// ---------------------------------------------------------------------------
// Streaming events (structural compatibility with Anthropic's SDK event shape)
// ---------------------------------------------------------------------------

export type KosaxStopReason = 'end_turn' | 'max_tokens' | 'tool_use' | 'stop_sequence'

export type KosaxMessageStart = {
  type: 'message_start'
  message: {
    id: string
    role: 'assistant'
    model: string
  }
}

export type KosaxContentBlockStart = {
  type: 'content_block_start'
  index: number
  content_block: KosaxContentBlockParam
}

export type KosaxTextDelta = {
  type: 'text_delta'
  text: string
}

export type KosaxInputJsonDelta = {
  type: 'input_json_delta'
  partial_json: string
}

/**
 * KOSAX / Anthropic-compat thinking delta. Carries a chunk of the model's
 * chain-of-thought trace. The backend forwards K-EXAONE's
 * ``delta.reasoning_content`` (FriendliAI / vLLM separated reasoning channel)
 * via ``AssistantChunkFrame.thinking``, and llmClient.ts converts those frames
 * into one or more ``content_block_delta { delta: KosaxThinkingDelta }``
 * events on a dedicated thinking block index. The TUI's ``Message.tsx``
 * picks up ``type: 'thinking'`` content blocks and routes them to
 * ``AssistantThinkingMessage`` (``∴ Thinking`` in dim italic).
 */
export type KosaxThinkingDelta = {
  type: 'thinking_delta'
  thinking: string
}

export type KosaxContentBlockDelta = {
  type: 'content_block_delta'
  index: number
  delta: KosaxTextDelta | KosaxInputJsonDelta | KosaxThinkingDelta
}

export type KosaxContentBlockStop = {
  type: 'content_block_stop'
  index: number
}

export type KosaxMessageDelta = {
  type: 'message_delta'
  delta: {
    stop_reason?: KosaxStopReason
  }
  usage?: KosaxUsage
}

export type KosaxMessageStop = {
  type: 'message_stop'
}

export type KosaxRawMessageStreamEvent =
  | KosaxMessageStart
  | KosaxContentBlockStart
  | KosaxContentBlockDelta
  | KosaxContentBlockStop
  | KosaxMessageDelta
  | KosaxMessageStop

// ---------------------------------------------------------------------------
// Finalized message returned by LLMClient.complete() + LLMClient.stream() return
// ---------------------------------------------------------------------------

export type KosaxMessageFinal = {
  id: string
  role: 'assistant'
  model: string
  content: KosaxContentBlockParam[]
  stop_reason: KosaxStopReason
  usage: KosaxUsage
}
