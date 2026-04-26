# Phase 1 Data Model: TUI ↔ K-EXAONE wiring closure

**Feature**: Epic #1978
**Plan**: [plan.md](./plan.md)
**Date**: 2026-04-27

## Entities

### `ChatRequestFrame` (NEW IPC arm)

Full-context conversational request from TUI to backend harness.

| Field | Type | Constraint | Notes |
|---|---|---|---|
| (envelope: session_id, correlation_id, ts, version, role, frame_seq, transaction_id, trailer) | from `_BaseFrame` | E1–E6 invariants | Standard Spec 032 envelope |
| `kind` | `Literal["chat_request"]` | discriminator | New union arm |
| `messages` | `list[ChatMessage]` | non-empty | Conversation history including the new user turn at the tail |
| `tools` | `list[ToolDefinition]` | may be empty | Tools available to the model this turn |
| `system` | `str | None` | optional | Effective system prompt assembled by TUI side |
| `max_tokens` | `int` | ≥ 1, ≤ 32000 | Model max-output budget; defaults to 8192 |
| `temperature` | `float` | 0.0–2.0 | Defaults to 1.0 |
| `top_p` | `float` | 0.0–1.0 | Defaults to 0.95 |

**Pydantic v2** (frozen, `extra="forbid"`). Role allow-list: `{"tui"}` only. Not terminal (`_TERMINAL_KINDS` excludes `chat_request`). Validates per Spec 032 invariants E1–E6.

**Lifetime**: One frame per turn, in transit only. Backend reads, processes, forgets.

**Validation rules**:
- `messages[0]` MAY be system role; if absent, `system` field provides it.
- `messages[-1].role` MUST be `"user"` or `"tool"` (a tool result feeding back into the loop).
- Sum of message string lengths SHOULD NOT exceed `LLMClientConfig.session_budget` × ~4 chars/token; over-budget rejected with `error{code="budget_exceeded"}`.

### `ChatMessage` (re-used from `kosmos.llm.models`)

| Field | Type | Constraint |
|---|---|---|
| `role` | `Literal["system","user","assistant","tool"]` | required |
| `content` | `str` | UTF-8 |
| `name` | `str | None` | required when `role="tool"` (matches the `tool_call.name`) |
| `tool_call_id` | `str | None` | required when `role="tool"`, ULID matching the originating `tool_call` |

### `ToolDefinition` (re-used from `kosmos.llm.models`)

| Field | Type | Source |
|---|---|---|
| `type` | `Literal["function"]` | OpenAI/Friendli compat |
| `function.name` | `str` | from registered Tool |
| `function.description` | `str` | from registered Tool |
| `function.parameters` | `dict` (JSON Schema) | exported via `ToolRegistry.export_core_tools_openai()` |

### `ToolCallFrame` (existing schema, NOW emitted)

| Field | Type | Notes |
|---|---|---|
| `kind` | `Literal["tool_call"]` | Spec 032 |
| `call_id` | `str` (ULID) | Pairs 1:1 with subsequent `tool_result` |
| `name` | `Literal["lookup","resolve_location","submit","subscribe","verify"]` | Primitive name; non-primitive tools nest under `lookup` per Spec 031 |
| `arguments` | `dict[str, object]` | Resolved JSON |

Emitted by backend `_handle_chat_request` when K-EXAONE returns a function-call response. Role: `"backend"`. Not terminal (paired with `tool_result`).

### `ToolResultFrame` (existing schema, NOW consumed)

| Field | Type | Notes |
|---|---|---|
| `kind` | `Literal["tool_result"]` | Spec 032 |
| `call_id` | `str` | matches `tool_call.call_id` |
| `envelope` | `ToolResultEnvelope` | 5-primitive discriminated union per Spec 031 |

Sent by **TUI** (role `"tui"`) when its tool dispatcher (`Tool.ts` + `mcp.ts`) returns. Backend's pending-call dictionary keyed by `call_id` resolves the `await`, injects `{role: "tool", content: <result>, name, tool_call_id}` into `messages[]`, and triggers the next LLM turn (a fresh `ChatRequestFrame` round trip OR backend-internal re-stream — see ADR-0005).

### `PermissionRequestFrame` (existing schema, NOW emitted)

| Field | Type | Notes |
|---|---|---|
| `kind` | `Literal["permission_request"]` | Spec 032 |
| `transaction_id` | `str` (UUIDv7) | Required for sync correlation per ADR-0002 |
| `primitive_kind` | `Literal["lookup","resolve_location","submit","subscribe","verify"]` | |
| `tool_id` | `str` | Adapter ID (e.g., `nmc_emergency_search`) |
| `gauntlet_step` | `int` | Step in the 7-step pipeline (Spec 033) — typically 4 or 5 |
| `pii_class` | `Literal["none","public","sensitive","ssn"]` | From adapter `pipa_class` |
| `data_recipient_ministry` | `str` | Korean name + acronym (e.g., "국립중앙의료원 (NMC)") |
| `proposed_arguments` | `dict[str, object]` | What the model wants to call with — for citizen review |

Emitted by backend permission pipeline when `decision == ASK`. Role: `"backend"`. Terminal flag: `False` (matched with `permission_response`).

### `PermissionResponseFrame` (existing schema, NOW consumed)

| Field | Type | Notes |
|---|---|---|
| `kind` | `Literal["permission_response"]` | Spec 032 |
| `transaction_id` | `str` | matches `permission_request.transaction_id` |
| `decision` | `Literal["allow_once","allow_session","deny"]` | The three citizen choices |
| `receipt_id` | `str` | UUIDv7 for the consent receipt the citizen can later reference |

Sent by TUI (role `"tui"`) after the modal closes. Backend awaits this with 60 s timeout; on timeout treats as `deny` and emits a synthetic frame to the audit log.

### `ConsentReceipt` (existing memdir entity, populated through this Epic)

| Field | Type | Source |
|---|---|---|
| `receipt_id` | `str` (UUIDv7) | Same value as `PermissionResponseFrame.receipt_id` |
| `session_id` | `str` | From envelope |
| `tool_id` | `str` | From `permission_request.tool_id` |
| `decision` | `str` | `allow_once \| allow_session \| deny` |
| `gauntlet_step` | `int` | From request |
| `granted_at` | `str` (ISO-8601 UTC) | Time of citizen choice |
| `revoked_at` | `str | None` | Set if citizen revokes via `/consent revoke` |

**Storage**: append-only JSON file at `~/.kosmos/memdir/user/consent/<receipt_id>.json` (Spec 035 + Spec 027 paths). Listed by `/consent list` slash command. Revocation marker is a sibling `<receipt_id>.json.revoked` (Spec 027 marker pattern).

### `Citizen Session`

Already exists in TUI memory; this Epic does NOT change its shape. Reference only:

| Aspect | Storage | Owner |
|---|---|---|
| Conversation history (`Messages[]`) | `tui/src/query.ts` in-memory | TUI (canonical per ADR-0005) |
| Persisted JSONL | `~/.kosmos/memdir/user/sessions/<session_id>.jsonl` | TUI writer (Spec 027) |
| Session-scoped consent grants | TUI `useStore` permissions slice | TUI |
| OTEL session span | OpenTelemetry SDK in-process | Backend (per ADR-0004) |

### `Conversation Turn`

Logical entity, not a stored record. Boundaries:

- **Open**: receipt of `ChatRequestFrame` on backend, or `query.ts` agentic-loop iteration start on TUI
- **Close**: emit of `assistant_chunk{done=True}` AND no pending tool calls

Telemetry: `kosmos.turn` span (ADR-0004). One turn may contain ≥0 tool calls and ≥0 permission requests.

## Frame schema integration table

| Frame arm | Defined in 032? | Schema hash | Emit code (before this Epic) | Emit code (after this Epic) | Consume code (TUI) |
|---|:---:|---|---|---|---|
| `user_input` | ✅ | unchanged | (TUI emit only) | (TUI emit only — kept for echo + plain-text fallback) | (backend echo only) |
| `chat_request` | NEW | re-hashed | n/a | TUI `llmClient.ts`:send | backend `stdio.py:_handle_chat_request` |
| `assistant_chunk` | ✅ | unchanged | backend `stdio.py:514, 551` | backend (unchanged path) | TUI `llmClient.ts:268` |
| `tool_call` | ✅ | unchanged | demo only | backend `stdio.py:_emit_tool_call` (new) | TUI `llmClient.ts:367` |
| `tool_result` | ✅ | unchanged | demo only | TUI tool dispatcher (existing) | backend `_handle_chat_request._await_tool_results` (new) |
| `permission_request` | ✅ | unchanged | none | backend permission pipeline (new) | TUI `codec.ts:271` (existing renderer) |
| `permission_response` | ✅ | unchanged | n/a | (TUI emit only) | backend permission pipeline (new) |
| `error` | ✅ | unchanged | backend ×5 | unchanged | TUI |
| `session_event` | ✅ | unchanged | backend ×4 | unchanged | TUI |
| (15 other dead arms) | ✅ | unchanged | none | none (deferred per spec.md) | partial |

**SHA-256 contract** (Spec 032 FR-037): `frame.schema.json` SHA-256 will change due to new arm. Backend `kosmos.ipc.schema.hash` OTEL attribute updated at boot — verified by Phase C task `T021_schema_hash_update`.

## State transitions

### Conversation turn (happy path — no tools, no permission)

```
[idle]
   │ TUI: PromptInput.onSubmit("안녕하세요")
   ▼
[building chat_request]
   │ TUI: assemble messages + tools + system
   ▼
[chat_request emitted]    correlation_id = UUIDv7()
   │ backend: _handle_chat_request receives
   ▼
[LLM streaming]   gen_ai.* spans
   │ backend: assistant_chunk × N
   ▼
[turn close]   assistant_chunk{done=True}
   │ TUI: render complete
   ▼
[idle]
```

### Tool turn (1 tool, no permission gauntlet escalation)

```
[idle] → [chat_request emitted] → [LLM streaming]
   │ backend: K-EXAONE returns function_call
   ▼
[tool_call emitted]   call_id = ULID()
   │ TUI: dispatch via Tool.ts + mcp.ts
   ▼
[tool executing]   visible to citizen via Tool.ts UI
   │ TUI: tool_result emitted
   ▼
[tool result received]   backend: inject {role:"tool", ...} into messages
   │ backend: continue stream (or new internal LLM call with augmented messages)
   ▼
[LLM streaming - cont.]
   │ backend: assistant_chunk × M
   ▼
[turn close]
```

### Tool turn with permission gauntlet (Story 3 path)

```
... [LLM streaming] → backend gets function_call →
[permission_check]   PermissionPipeline.evaluate(tool, ctx)
   │ decision == ASK
   ▼
[permission_request emitted]   transaction_id = UUIDv7()
   │ TUI: render modal (citizen sees three buttons)
   │ <citizen chooses>
   ▼
[permission_response emitted]   decision in {allow_once, allow_session, deny}
   │ backend: write ConsentReceipt to memdir
   ▼
[branch: deny]                            [branch: allow_*]
   │ inject synthetic tool_result        │ proceed to tool_call emit
   │ {error: "permission_denied",        │ (above)
   │  receipt_id}                        ▼
   ▼                              [tool executing] → [tool_result]
[LLM streaming - cont. without tool]
```

## Integrity invariants

| ID | Invariant | Enforcement |
|---|---|---|
| **D1** | Every `tool_call` has a matching `tool_result` (or terminal `error` with same `call_id`) before turn close | `stdio.py` pending-call dict tracked, `assistant_chunk{done=True}` blocked while pending non-empty |
| **D2** | Every `permission_request` has a matching `permission_response` within 60 s OR a synthetic `deny` is generated | `asyncio.wait_for(timeout=60)` |
| **D3** | `tool_call.call_id` is ULID, monotonically increasing within a turn | UUIDv7 generator (Spec 032 envelope) |
| **D4** | `messages[].name` and `messages[].tool_call_id` are populated together when `role="tool"` | Pydantic model_validator |
| **D5** | Anthropic SDK byte path is unreachable in normal operation | Phase B regression test: `pytest tests/ipc/test_anthropic_residue_zero.py` greps for forbidden imports |
| **D6** | `ChatRequestFrame.messages[-1].role` is `"user"` or `"tool"` | Pydantic model_validator |

## Open follow-ups (deferred per spec.md)

- Multi-tool parallel execution (CC's `dispatch_tool_calls` already supports it; backend permission gauntlet sequencing needs design — Phase F deferred).
- Streamed `assistant_chunk` cancellation mid-flight (Citizen Ctrl-C).
- `payload_*` frame chunked tool result delivery for large adapter payloads (deferred per spec.md table).
