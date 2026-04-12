# Data Model: LLM Client Integration

**Feature**: Epic #4 — LLM Client Integration
**Date**: 2026-04-12

## Entities

### 1. LLMClientConfig

Configuration for the LLM client, loaded from environment variables.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `token` | `SecretStr` | Yes | — | FriendliAI API token (`KOSMOS_FRIENDLI_TOKEN`) |
| `base_url` | `HttpUrl` | No | `https://api.friendli.ai/v1` | API base URL |
| `model` | `str` | No | `dep89a2fde0e09` | Model identifier |
| `session_budget` | `int` | No | `100000` | Max tokens per session |
| `timeout` | `float` | No | `60.0` | Request timeout in seconds |
| `max_retries` | `int` | No | `3` | Max retry attempts for transient errors |

**Validation**: `token` must not be empty. `session_budget` must be > 0. `timeout` must be > 0.

---

### 2. ChatMessage

A message in the conversation. Follows OpenAI format.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `role` | `Literal["system", "user", "assistant", "tool"]` | Yes | — | Message role |
| `content` | `str \| None` | No | `None` | Text content |
| `name` | `str \| None` | No | `None` | Name for tool messages |
| `tool_calls` | `list[ToolCall] \| None` | No | `None` | Tool calls (assistant only) |
| `tool_call_id` | `str \| None` | No | `None` | Tool call ID (tool role only) |

**Validation**: `tool` role requires `tool_call_id`. `assistant` role may have `tool_calls`. `system` and `user` roles must have `content`.

---

### 3. ToolCall

A tool invocation requested by the model.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `str` | Yes | — | Unique call identifier |
| `type` | `Literal["function"]` | Yes | `"function"` | Always "function" |
| `function` | `FunctionCall` | Yes | — | Function name and arguments |

---

### 4. FunctionCall

Function name and serialized arguments within a tool call.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Function/tool name |
| `arguments` | `str` | Yes | — | JSON-serialized arguments |

---

### 5. ToolDefinition

Tool schema sent to the model for function calling.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | `Literal["function"]` | Yes | `"function"` | Always "function" |
| `function` | `FunctionSchema` | Yes | — | Function metadata and parameters |

---

### 6. FunctionSchema

Schema definition for a function/tool.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Function name |
| `description` | `str` | Yes | — | Human-readable description |
| `parameters` | `dict[str, Any]` | Yes | — | JSON Schema for parameters |

**Note**: `parameters` uses `dict[str, Any]` because it holds a JSON Schema object. This is the one case where `Any` is acceptable — it represents an external schema, not internal I/O.

---

### 7. TokenUsage

Token counts from a single LLM call.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `input_tokens` | `int` | Yes | `0` | Prompt/input tokens |
| `output_tokens` | `int` | Yes | `0` | Completion/output tokens |
| `cache_read_tokens` | `int` | No | `0` | Cache read tokens |
| `cache_write_tokens` | `int` | No | `0` | Cache write tokens |
| `total_tokens` | `int` | computed | — | `input_tokens + output_tokens` |

---

### 8. ChatCompletionResponse

Complete response from a non-streaming LLM call.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `str` | Yes | — | Response identifier |
| `content` | `str \| None` | No | `None` | Text content |
| `tool_calls` | `list[ToolCall]` | No | `[]` | Tool calls if any |
| `usage` | `TokenUsage` | Yes | — | Token usage statistics |
| `model` | `str` | Yes | — | Model that generated the response |
| `finish_reason` | `Literal["stop", "tool_calls", "length"]` | Yes | — | Why generation stopped |

---

### 9. StreamEvent

A single event from a streaming LLM response.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | `Literal["content_delta", "tool_call_delta", "usage", "done", "error"]` | Yes | — | Event type |
| `content` | `str \| None` | No | `None` | Content delta text |
| `tool_call_index` | `int \| None` | No | `None` | Index of tool call being built |
| `tool_call_id` | `str \| None` | No | `None` | Tool call ID (first chunk only) |
| `function_name` | `str \| None` | No | `None` | Function name (first chunk only) |
| `function_args_delta` | `str \| None` | No | `None` | Partial function arguments JSON |
| `usage` | `TokenUsage \| None` | No | `None` | Final usage (last event only) |

---

### 10. UsageTracker

Session-level token budget tracker (not persisted).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `budget` | `int` | Yes | — | Max tokens for this session |
| `input_tokens_used` | `int` | No | `0` | Cumulative input tokens |
| `output_tokens_used` | `int` | No | `0` | Cumulative output tokens |
| `call_count` | `int` | No | `0` | Number of LLM calls made |

**Methods**:
- `can_afford(estimated_input: int) -> bool`: Pre-flight budget check
- `debit(usage: TokenUsage) -> None`: Record usage after a call
- `remaining -> int`: Computed remaining budget
- `is_exhausted -> bool`: Whether budget is fully consumed

**State transitions**:
```
Created(budget=N) → debit() → Active(used < budget) → debit() → Exhausted(used >= budget)
                                                                    ↓
                                                               Rejects further calls
```

---

### 11. RetryPolicy

Configuration for retry behavior.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_retries` | `int` | No | `3` | Maximum retry attempts |
| `base_delay` | `float` | No | `1.0` | Base delay in seconds |
| `multiplier` | `float` | No | `2.0` | Backoff multiplier |
| `max_delay` | `float` | No | `60.0` | Maximum delay cap |
| `retryable_status_codes` | `frozenset[int]` | No | `{429, 503}` | HTTP status codes to retry |

## Relationships

```
LLMClientConfig ──configures──→ LLMClient
LLMClient ──uses──→ RetryPolicy
LLMClient ──tracks──→ UsageTracker
LLMClient ──sends──→ list[ChatMessage] + list[ToolDefinition]
LLMClient ──receives──→ ChatCompletionResponse | AsyncIterator[StreamEvent]
ChatMessage ──contains──→ ToolCall? (assistant role)
ChatCompletionResponse ──contains──→ TokenUsage
StreamEvent ──final──→ TokenUsage
UsageTracker ──debits──→ TokenUsage
```
