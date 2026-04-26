# Contract: `ChatRequestFrame` IPC arm

**Status**: NEW (this Epic)
**Replaces**: `UserInputFrame` for tools-aware chat requests
**Coexists with**: `UserInputFrame` (kept for echo / plain-text fallback paths)
**Direction**: TUI → backend
**Pydantic location**: `src/kosmos/ipc/frame_schema.py` (new arm under the existing 19-arm union)
**JSON Schema location**: `tui/src/ipc/schema/frame.schema.json` (lockstep with Pydantic; SHA-256 hash will change — re-published at backend boot via `kosmos.ipc.schema.hash` OTEL attribute per Spec 032 FR-037)

## Envelope (inherited from `_BaseFrame`)

| Field | Type | Constraint |
|---|---|---|
| `session_id` | `str` | Opaque, may be `""` before first session_event handshake |
| `correlation_id` | `str` (UUIDv7) | non-empty (E5) |
| `ts` | `str` (ISO-8601 UTC, ms precision) | required |
| `version` | `Literal["1.0"]` | hard-fail on mismatch (E1) |
| `role` | `Literal["tui"]` | role allow-list adds `chat_request → {"tui"}` (E3) |
| `frame_seq` | `int ≥ 0` | per-session monotonic |
| `transaction_id` | `str | None` | usually None for chat_request; set if the request is a retry of a transactionally idempotent operation |
| `trailer` | `FrameTrailer | None` | usually None; not a terminal frame |

## Payload

| Field | Type | Constraint | Comment |
|---|---|---|---|
| `kind` | `Literal["chat_request"]` | discriminator | |
| `messages` | `list[ChatMessage]` | min length 1 | Conversation history; tail message has `role` ∈ {`"user"`, `"tool"`} |
| `tools` | `list[ToolDefinition]` | may be empty list | Tools available to the model this turn |
| `system` | `str | None` | optional | Effective system prompt |
| `max_tokens` | `int` | `1 ≤ x ≤ 32000`, default 8192 | |
| `temperature` | `float` | `0.0 ≤ x ≤ 2.0`, default 1.0 | |
| `top_p` | `float` | `0.0 ≤ x ≤ 1.0`, default 0.95 | |

## Validation rules

- `messages` must contain at least one entry.
- If any `messages[i].role == "tool"`, then `messages[i].name` and `messages[i].tool_call_id` must both be set.
- `tools[].function.parameters` must be a valid JSON Schema object (Pydantic accepts `dict[str, object]`; deeper validation deferred to LLMClient).
- Total approximate token estimate (sum of message lengths × 4) must be ≤ `KOSMOS_LLM_SESSION_BUDGET` env (default 100,000); over-budget rejected with `error{code="budget_exceeded"}` frame.

## Round-trip pairing

A `ChatRequestFrame` MAY produce zero-to-many of these on the same `correlation_id`:

| Effect | Frame kind | Notes |
|---|---|---|
| Streaming text | `assistant_chunk` (×N) | Final has `done=True` |
| Tool decision | `tool_call` | Followed (eventually) by matching `tool_result` |
| Permission ask | `permission_request` | Awaits `permission_response` from TUI |
| Failure | `error` | Terminal; `assistant_chunk{done=True}` not emitted |

Backend MUST emit either a terminal `assistant_chunk{done=True}` or a terminal `error` for every received `ChatRequestFrame`. No silent drops.

## Backward compatibility

- Existing `UserInputFrame` consumers / emitters unchanged.
- Backend retains a path: a `UserInputFrame` is treated as `ChatRequestFrame{messages=[{role:"user", content:text}], tools=[]}` for echo / smoke-test parity. This means existing PTY harnesses keep working.
- Frame schema hash change is recorded as a Phase C migration task; no rollback required because the new arm is purely additive.

## Telemetry attributes (per ADR-0004)

When `_handle_chat_request` receives this frame, a new OTEL span `kosmos.turn` is opened with:

```
kosmos.session_id      = <envelope.session_id>
kosmos.correlation_id  = <envelope.correlation_id>
kosmos.frame.kind      = "chat_request"
kosmos.frame.seq       = <envelope.frame_seq>
gen_ai.system          = "friendliai"
gen_ai.request.model   = "LGAI-EXAONE/K-EXAONE-236B-A23B"
```

Closes when the matched terminal frame (`assistant_chunk{done=True}` or `error`) is emitted.

## Audit trail

Every `ChatRequestFrame` is logged to the structured observability event log (`kosmos.observability.event_logger.ObservabilityEventLogger`) with `event_type="chat_request_received"`. Tool dispatches inside the turn append `chat_request.{call_id}.invoked` events. This stitches into Spec 024 `ToolCallAuditRecord` chain via `correlation_id`.
