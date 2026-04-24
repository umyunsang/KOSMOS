# Contract — TS `LLMClient` interface + IPC LLM turn protocol

**Feature**: [../spec.md](../spec.md) · **Research**: [../research.md](../research.md) · **Data model**: [../data-model.md](../data-model.md)

This contract fixes the TypeScript surface that `tui/src/query.ts` and `tui/src/QueryEngine.ts` rely on after the Anthropic SDK is removed. It also fixes the Spec 032 frame sequence that the TS client and Python backend agree on for a single LLM turn.

## 1. TS surface — `tui/src/ipc/llmClient.ts`

### 1.1 `LLMClient` class

```ts
import type {
  KosmosMessageStreamParams,
  KosmosRawMessageStreamEvent,
  KosmosMessageFinal,
} from './llmTypes.js';
import type { IPCBridge } from './bridge.js';

export class LLMClient {
  constructor(opts: { bridge: IPCBridge; model: string /* = 'LGAI-EXAONE/EXAONE-4.0-32B' */; sessionId: string });

  /**
   * Start an LLM turn. Returns an async generator yielding stream events
   * structurally compatible with @anthropic-ai/sdk's BetaRawMessageStreamEvent.
   *
   * Implementation flow:
   *  1. Construct UserInputFrame with fresh correlation_id (makeUUIDv7).
   *  2. Push via bridge.sendFrame(frame); start OTEL gen_ai.client.invoke span.
   *  3. Consume inbound AssistantChunkFrame/ToolCallFrame stream on the correlation_id.
   *  4. Translate each inbound frame to a KosmosRawMessageStreamEvent; yield.
   *  5. On done=true trailer, emit message_stop + finalize span, close generator.
   *  6. On ErrorFrame, throw LLMClientError(class, code, message).
   */
  stream(params: KosmosMessageStreamParams): AsyncGenerator<KosmosRawMessageStreamEvent, KosmosMessageFinal, void>;

  /**
   * Non-streaming convenience — awaits stream to completion and collects text.
   * Used for short synchronous classifier calls that don't need token-by-token UI.
   */
  complete(params: KosmosMessageStreamParams): Promise<KosmosMessageFinal>;
}

export class LLMClientError extends Error {
  readonly class: 'llm' | 'tool' | 'network';
  readonly code: string;
  readonly retryAfterMs?: number;
}
```

### 1.2 Guarantees

- **G1** `stream()` MUST NOT call any HTTPS endpoint directly. All outbound traffic goes via `bridge.sendFrame()` (stdio IPC to Python backend).
- **G2** `stream()` MUST emit exactly one OTEL `gen_ai.client.invoke` span per call. Span ends on generator exhaustion, early return, or thrown error.
- **G3** The `model` constructor argument MUST be `'LGAI-EXAONE/EXAONE-4.0-32B'` in production builds. Tests may pass a mock value.
- **G4** If the bridge emits an `ErrorFrame` with `class=llm, code=auth` (missing `FRIENDLI_API_KEY`), `stream()` MUST throw `LLMClientError` without retrying.
- **G5** Rate-limit handling: `BackpressureSignalFrame` with `kind=llm_rate_limit` pauses consumption until `retry_after_ms` elapses; `stream()` does NOT retry the full turn — that is the Python backend's responsibility (Spec 019 semantics).
- **G6** The generator's return value (final `KosmosMessageFinal`) carries `{ stop_reason, usage: { input_tokens, output_tokens, cache_read_input_tokens? } }` populated from the Python backend's done-frame trailer.

### 1.3 Non-goals

- `LLMClient` does NOT persist messages to disk — Spec 027 session memdir handles that on the Python side.
- `LLMClient` does NOT implement retry — Python-side `LLMClient` owns retry policy (Decision 7).
- `LLMClient` does NOT know FriendliAI URLs, headers, or credentials — those never touch TS runtime.

## 2. TS type surface — `tui/src/ipc/llmTypes.ts`

Complete structural definitions (extracted + finalized from [data-model.md § TS type translation layer](../data-model.md#ts-type-translation-layer-in-process-only-no-wire-change)).

```ts
// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · Anthropic→FriendliAI type shim.

export type KosmosRole = 'user' | 'assistant';

export type KosmosTextBlockParam = { type: 'text'; text: string };
export type KosmosToolUseBlockParam = {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
};
export type KosmosToolResultBlockParam = {
  type: 'tool_result';
  tool_use_id: string;
  content: string | KosmosContentBlockParam[];
  is_error?: boolean;
};
export type KosmosContentBlockParam =
  | KosmosTextBlockParam
  | KosmosToolUseBlockParam
  | KosmosToolResultBlockParam;

export type KosmosMessageParam = {
  role: KosmosRole;
  content: string | KosmosContentBlockParam[];
};

export type KosmosToolDefinition = {
  name: string;
  description?: string;
  input_schema: { type: 'object'; [k: string]: unknown };
};

export type KosmosMessageStreamParams = {
  model: string;
  system?: string;             // resolved from PromptLoader via backend
  messages: KosmosMessageParam[];
  tools?: KosmosToolDefinition[];
  max_tokens: number;
  temperature?: number;
  metadata?: Record<string, string>;
};

export type KosmosUsage = {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;
};

export type KosmosRawMessageStreamEvent =
  | { type: 'message_start'; message: { id: string; role: 'assistant'; model: string } }
  | { type: 'content_block_start'; index: number; content_block: KosmosContentBlockParam }
  | { type: 'content_block_delta'; index: number; delta: { type: 'text_delta'; text: string } | { type: 'input_json_delta'; partial_json: string } }
  | { type: 'content_block_stop'; index: number }
  | { type: 'message_delta'; delta: { stop_reason?: 'end_turn' | 'max_tokens' | 'tool_use' | 'stop_sequence' }; usage?: KosmosUsage }
  | { type: 'message_stop' };

export type KosmosMessageFinal = {
  id: string;
  role: 'assistant';
  model: string;
  content: KosmosContentBlockParam[];
  stop_reason: 'end_turn' | 'max_tokens' | 'tool_use' | 'stop_sequence';
  usage: KosmosUsage;
};
```

## 3. IPC protocol — LLM turn frame sequence

Canonical happy-path sequence (role in parens):

```
t=0   UserInputFrame(tui) [correlation_id=C]
      ├─ payload: { text, system_ref, tools }
t=Δ1  AssistantChunkFrame(llm) [correlation_id=C, frame_seq=1, done=false]
      ├─ payload: { message_id=M, delta: "안녕", done: false }
t=Δ2  AssistantChunkFrame(llm) [correlation_id=C, frame_seq=2, done=false]
      ├─ payload: { message_id=M, delta: "하세요 시민님", done: false }
t=Δ3  AssistantChunkFrame(llm) [correlation_id=C, frame_seq=3, done=true]
      ├─ payload: { message_id=M, delta: "", done: true }
      ├─ trailer: { final=true, transaction_id=null, usage: {input:120, output:45, cache_read_input:0} }
```

Tool-use extension:

```
...streaming assistant text...
AssistantChunkFrame(llm) [done=true]      ← turn 1 ends with stop_reason=tool_use
ToolCallFrame(llm) [tx_id=T1]             ← LLM's tool_use block materialized
ToolResultFrame(tool) [tx_id=T1]          ← TUI or backend adapter executes
UserInputFrame(tui) [correlation_id=C2]   ← backend re-invokes LLM with tool result (new correlation)
...streaming resumes...
```

Error path:

```
UserInputFrame(tui) [correlation_id=C]
ErrorFrame(backend) [correlation_id=C]
├─ payload: { class: 'llm', code: 'auth', message: 'FRIENDLI_API_KEY missing' }
└─ trailer: { final=true }
```

Rate-limit (Spec 019/020 semantics, mediated by backend):

```
UserInputFrame(tui) [correlation_id=C]
BackpressureSignalFrame(backend) [correlation_id=C]
├─ payload: { kind: 'llm_rate_limit', retry_after_ms: 2000, source: 'upstream_429' }
── (backend waits, retries FriendliAI internally, eventually:)
AssistantChunkFrame(llm) [correlation_id=C, frame_seq=N, done=false]
...
```

## 4. OTEL contract

### 4.1 Span — `gen_ai.client.invoke`

Emitted in TS by `LLMClient.stream()` on entry. Parent span set from the current REPL turn context.

| Attribute | Type | Required | Value / source |
|---|---|---|---|
| `gen_ai.system` | string | ✅ | `"friendli_exaone"` (constant) |
| `gen_ai.operation.name` | string | ✅ | `"chat"` |
| `gen_ai.request.model` | string | ✅ | `LLMClient` constructor `model` arg |
| `gen_ai.request.max_tokens` | int | ✅ | from `KosmosMessageStreamParams.max_tokens` |
| `gen_ai.request.temperature` | float | ⬜ | if provided |
| `gen_ai.usage.input_tokens` | int | ✅ | from final `KosmosMessageFinal.usage.input_tokens` |
| `gen_ai.usage.output_tokens` | int | ✅ | from final `KosmosMessageFinal.usage.output_tokens` |
| `kosmos.prompt.hash` | string | ✅ | SHA-256 hex, forwarded by backend in response metadata |
| `kosmos.correlation_id` | string | ✅ | the envelope `correlation_id` used for this turn |
| `kosmos.transaction_id` | string | ⬜ | envelope `transaction_id` if set |
| `kosmos.session_id` | string | ✅ | active session |

### 4.2 Span status

- `OK` on normal generator exhaustion.
- `ERROR` on any thrown `LLMClientError`, with `error.type` attribute = `error.class:error.code` (e.g. `"llm:auth"`).

## 5. Fail-closed boot contract

**Contract name**: `fail-closed-no-friendli-key`

Preconditions: TUI process starts with `FRIENDLI_API_KEY` unset.

Expected behavior:
1. TUI displays a terminal-friendly bilingual error envelope: `"FRIENDLI_API_KEY 환경변수가 필요합니다 / FRIENDLI_API_KEY environment variable required"`.
2. TUI exits with non-zero status (1).
3. Zero HTTP requests made to any host.
4. Zero `@anthropic-ai/sdk` modules loaded (verified by `require.cache` inspection in smoke test).

Must be implemented by `tui/src/entrypoints/init.ts` post-rewire — the check runs before the IPC bridge to the Python backend is even established, so Python backend never starts either.

## 6. Compatibility window for P3

During Epic #1633 merging, a few CC tool files (`FileWriteTool.ts`, `FileEditTool.ts`, `NotebookEditTool.ts`, `GlobTool.ts`, `PowerShellTool/pathValidation.ts`) still import `filesApi`. Per Research Decision 2, these imports get replaced with **no-op stubs** in this Epic, because the tool files themselves will be deleted or replaced in Epic #1634 (P3 tool system). The no-op stubs must:

- Export the same symbol names `filesApi` consumers expect (mostly `downloadFile`, `uploadFile`).
- Return a rejected promise with a clear error message (`"Files API removed in Epic #1633; P3 will replace file handling."`).
- Not import from `'axios'` or any Anthropic URL (hard dependency removal).

This gives a clean compile without pretending the feature works.
