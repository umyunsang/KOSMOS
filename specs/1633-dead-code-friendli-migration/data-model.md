# Data Model — P1+P2 · Dead code + Anthropic→FriendliAI migration

**Feature**: [spec.md](./spec.md)
**Research**: [research.md](./research.md)
**Branch**: `1633-dead-code-friendli-migration`
**Date**: 2026-04-24

## Scope

This Epic does **not** introduce new domain entities or persistent state. It performs a transport-layer rewrite: replacing TS-side `@anthropic-ai/sdk` client instantiation with a Spec 032 stdio-IPC-backed `LLMClient`. The sole data-model concern is **how LLM turns are packed into existing Spec 032 frame types** — no frame-schema changes, no new persistent entities, no database columns.

## Existing entities consumed (no modification)

### Spec 032 frame envelope (`tui/src/ipc/frames.generated.ts`)

- **`Role`** — existing enum `'tui' | 'backend' | 'tool' | 'llm' | 'notification'`. The `'llm'` variant is already reserved and used below.
- **`CorrelationId`** — UUIDv7 string per envelope (from `makeUUIDv7()` in `tui/src/ipc/envelope.ts`).
- **`TransactionId`** — UUIDv7 for idempotent state-change frames; `null` for streaming chunks.
- **`FrameSeq`** — per-session monotonic ordering (used for gap detection during resume).
- **`FrameTrailer`** — `{ final, transaction_id, checksum_sha256 }`, terminates logical payloads.

### Spec 026 prompt entities (`src/kosmos/prompts/`)

- **`PromptManifest`** (Python, already implemented) — parses `prompts/manifest.yaml`, validates SHA-256 integrity at boot.
- **`PromptLoader`** (Python, already implemented) — returns `(content, hash)` tuple for `system_v1`.

### Spec 021 OTEL span attributes (Python, already implemented)

- **`gen_ai.*`** — GenAI semconv v1.40 attributes already emitted by `src/kosmos/llm/client.py`.
- **`kosmos.prompt.hash`** — KOSMOS extension from Spec 026; already emitted Python-side.

## Frame usage for LLM turns (this Epic's contribution)

A single LLM invocation is a **sequence of frames** flowing through the Spec 032 NDJSON envelope. No frame kinds are added; the table below fixes the role assignment.

### Outbound (TUI → Python backend) — initiating an LLM request

| Frame kind | Role | Direction | Purpose |
|---|---|---|---|
| `UserInputFrame` | `tui` | TUI → backend | Citizen text + system prompt reference + tool list hint. Carries `text` (raw user input) plus metadata injected via envelope `correlation_id` for turn grouping. |

The `UserInputFrame` payload is defined by Spec 032; this Epic does **not** extend its shape. System-prompt SHA-256 propagation happens via the envelope's `kosmos.prompt.hash` OTEL attribute, not a new payload field.

### Inbound (Python backend → TUI) — streaming LLM response

| Frame kind | Role | Direction | Purpose |
|---|---|---|---|
| `AssistantChunkFrame` | `llm` | backend → TUI | Streaming token delta. Shape: `{ message_id, delta, done }`. Final chunk carries `done=true` and its envelope trailer contains the final usage totals. |
| `ToolCallFrame` | `llm` | backend → TUI | LLM-emitted tool invocation. Envelope's `transaction_id` is set (idempotent). |
| `ToolResultFrame` | `tool` | backend → TUI | Tool-adapter output (after tool execution roundtrip). |
| `ErrorFrame` | `backend` or `llm` | backend → TUI | Any of the Decision-6 error classes. |
| `BackpressureSignalFrame` | `backend` | backend → TUI | 429 / throttle signals from FriendliAI (Spec 032 Story 2). |

### Turn lifecycle

```
Citizen types → TUI emits UserInputFrame
                    ↓
        Python backend receives, calls LLMClient (existing),
        streams back:
                    ↓
        AssistantChunkFrame (delta)
        AssistantChunkFrame (delta) ... N times
        [optional] ToolCallFrame (LLM requests tool use)
                    ↓
        TUI executes tool (locally or via another backend call),
        emits ToolResultFrame back
                    ↓
        Backend continues LLMClient loop,
        streams more AssistantChunkFrames
                    ↓
        Final AssistantChunkFrame with done=true +
        trailer containing usage totals
                    ↓
        TUI finalizes OTEL span (gen_ai.client.invoke)
```

### Correlation and idempotency

- A **conversation turn** = one `correlation_id` across all its AssistantChunk/ToolCall/ToolResult frames.
- A **tool invocation** = one `transaction_id` (set on `ToolCallFrame`, mirrored on `ToolResultFrame`). Spec 032 LRU dedup handles retries.
- A **session** = one `session_id` across many turns. Spec 027 memdir backs the session JSONL log.

## TS type translation layer (in-process only, no wire change)

The new file `tui/src/ipc/llmTypes.ts` defines KOSMOS-scoped types **structurally compatible** with the existing Anthropic SDK type surface that `QueryEngine.ts` + `query.ts` consume as type-only imports. These types are not serialized to the wire — they exist only so the agentic-loop code keeps compiling after `@anthropic-ai/sdk` imports are removed.

### Types to introduce (TS-only, zero wire impact)

```ts
// tui/src/ipc/llmTypes.ts (new — outline only, exact shape at contracts/)

export type KosmosContentBlockParam =
  | KosmosTextBlockParam
  | KosmosToolUseBlockParam
  | KosmosToolResultBlockParam;

export type KosmosTextBlockParam = { type: 'text'; text: string };

export type KosmosMessageParam = {
  role: 'user' | 'assistant';
  content: string | KosmosContentBlockParam[];
};

export type KosmosMessageStreamParams = {
  model: string;            // 'LGAI-EXAONE/K-EXAONE-236B-A23B'
  system?: string;          // loaded via PromptLoader
  messages: KosmosMessageParam[];
  tools?: KosmosToolDefinition[];
  max_tokens: number;
};

export type KosmosRawMessageStreamEvent =
  | { type: 'message_start'; message: { id: string; role: 'assistant' } }
  | { type: 'content_block_start'; index: number; content_block: KosmosContentBlockParam }
  | { type: 'content_block_delta'; index: number; delta: { type: 'text_delta'; text: string } }
  | { type: 'content_block_stop'; index: number }
  | { type: 'message_delta'; delta: { stop_reason?: string }; usage?: KosmosUsage }
  | { type: 'message_stop' };

export type KosmosUsage = {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;  // rewired from FriendliAI prompt_tokens_details.cached_tokens
};
```

**Mapping from `AssistantChunkFrame` to `KosmosRawMessageStreamEvent`**:
- First chunk for a `message_id` → emit `message_start` + `content_block_start`.
- Subsequent chunks with `delta.text` → emit `content_block_delta`.
- Chunk with `done=true` → emit `content_block_stop` + `message_delta` + `message_stop`. Usage totals pulled from the envelope trailer metadata (propagated by Python backend).

### Types to delete

All imports of the form `import type { ... } from '@anthropic-ai/sdk/...'` in non-test TS files. The translation layer above eliminates the need for them.

## Validation invariants

Carried forward to `tasks.md` / `contracts/`:

- **V1**: Every `UserInputFrame` emitted for an LLM turn has a **fresh** `correlation_id` (UUIDv7).
- **V2**: Every `AssistantChunkFrame` sequence terminates with exactly one `done=true` frame. Missing `done=true` is a protocol violation; TUI surfaces `ErrorFrame(class=network, code=ipc_transport)`.
- **V3**: `ToolCallFrame` MUST have a non-null `transaction_id` (idempotency for irreversible operations).
- **V4**: OTEL `gen_ai.client.invoke` span on the TUI side MUST attach `kosmos.prompt.hash` attribute with a 64-char hex SHA-256 value.
- **V5**: FriendliAI usage fields from backend MUST map to `KosmosUsage.input_tokens` / `output_tokens` / `cache_read_input_tokens`. Ignore fields not in the KOSMOS schema (forward compatibility).

## State transitions

This Epic introduces no new state machines. The existing Spec 032 session-ring-buffer + transaction-LRU + resume-handshake carry all the state. TS `LLMClient` is a **stateless per-call wrapper** over Spec 032's existing bridge.

## Persistence

**None introduced by this Epic.** Sessions remain in `~/.kosmos/memdir/user/sessions/` (Spec 027). OTEL spans go to local Langfuse via Spec 028 OTLP collector. Consent records in Spec 035 memdir. No schema changes to any persistent store.

## Schema change log

Empty — this Epic makes zero schema changes.
