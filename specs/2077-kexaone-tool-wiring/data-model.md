# Phase 1 Data Model: K-EXAONE Tool Wiring

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> Companion to [plan.md](./plan.md). Defines every entity surfaced by the migration, with field shapes, validation rules, lifecycle, and pairing invariants.

## Overview

Five entities cross the migration boundary:

1. **Tool inventory entry** — one element of `ChatRequestFrame.tools` (TUI emits, backend consumes).
2. **Tool-use content block** — what `AssistantToolUseMessage` renders (TUI internal, derived from `tool_call` frame).
3. **Tool-result content block** — what next-turn LLM context carries (TUI internal, derived from `tool_result` frame).
4. **Pending permission slot** — what `PermissionGauntletModal` reads from `sessionStore` (TUI internal).
5. **System prompt augmentation** — what `system_prompt_builder.build_system_prompt_with_tools()` emits (Python, ephemeral string).

No new IPC frame arms are introduced — every entity is either an existing IPC frame, a TUI-internal data structure, or an ephemeral text augmentation. No new on-disk schemas.

---

## 1. Tool inventory entry

**Source of truth**: TUI side — derived from `tui/src/tools.ts:getAllBaseTools()`. Backend fallback is `ToolRegistry().export_core_tools_openai()`.

**Carrier**: existing `ChatRequestFrame.tools` field (Spec 032). Type: `list[ToolDefinition]` (Pydantic v2).

**Shape (each entry)**:

```python
class ToolDefinition(BaseModel):
    type: Literal["function"]
    function: FunctionSchema

class FunctionSchema(BaseModel):
    name: str                       # e.g. "lookup", "submit", "verify", "subscribe", "resolve_location"
    description: str                # human-readable; used by both LLM and Available Tools section
    parameters: dict[str, Any]      # JSON Schema 2020-12 object
```

> The `dict[str, Any]` for `parameters` is the **only** sanctioned `Any` in this epic. JSON Schema is by definition open-shape; the type is a forwarded JSON Schema document. Constitution Principle III's "no Any in tool I/O" applies to *Pydantic-typed adapter inputs/outputs*, not to schema-as-data forwarding (where the document itself is the data).

**Validation rules**:

- `name` MUST match `^[a-z][a-z0-9_]*$` (registry naming invariant); the LLM-visible primitive surface (`lookup`, `submit`, `verify`, `subscribe`, `resolve_location`) is the canonical 5 + MVP-7 auxiliary.
- `description` MUST be non-empty and bilingual-safe (Korean + English content acceptable; the citizen never reads it directly, but the LLM consumes it).
- `parameters` MUST validate as a JSON Schema 2020-12 document — verified by the schema itself declaring `"$schema": "https://json-schema.org/draft/2020-12/schema"`.

**Lifecycle**:

- Generated **per turn** (FR-001): every `chat_request` frame carries the inventory snapshot. No caching, no staleness window.
- TUI emission: `getToolDefinitionsForFrame()` walks the local catalog, filters by user-state (ministry-scope opt-in from Spec 035), serializes via `toolToFunctionSchema()`.
- Backend fallback: when `frame.tools` is empty/absent, `_ensure_tool_registry().export_core_tools_openai()` returns the registry-default inventory.
- Backend authority: even when TUI provides `frame.tools`, backend MUST refuse to execute any tool whose `name` is not in `_ensure_tool_registry()` (FR-005).

**Pairing invariants**: none at this layer; pairing applies only to tool-use ↔ tool-result content blocks (Entity 3).

---

## 2. Tool-use content block

**Source of truth**: backend `tool_call` IPC frame (Spec 032 unchanged). The TUI projects each frame into one CC stream-event sequence.

**TUI internal shape** (CC mirror, defined in `tui/src/utils/messages.ts` already):

```typescript
type ToolUseBlockParam = {
  type: 'tool_use'
  id: string                     // matches the tool_call frame's call_id (uuid)
  name: string                   // tool function name
  input: unknown                 // arguments object — typed at the tool layer, not at this transport layer
}
```

**Derivation from `tool_call` frame**:

| `tool_call` frame field | `ToolUseBlockParam` field | Notes |
|---|---|---|
| `call_id` (uuid string) | `id` | Stable across the turn; pairs with `tool_result.tool_use_id` |
| `name` (str) | `name` | Must match a registered tool (backend enforces FR-005) |
| `arguments` (any) | `input` | Already JSON-deserialized by backend; passed through |

**Lifecycle**:

- Created when `deps.ts` receives `tool_call` frame.
- Yielded as part of two stream events:
  - `stream_event{content_block_start, index: N+1, content_block: <ToolUseBlockParam>}`
  - `stream_event{content_block_stop, index: N+1}`
- `handleMessageFromStream` (utils/messages.ts:3024-3037) routes the start event into `streamingToolUses` array.
- Once the assistant message terminates (`message_stop`), the block is committed as a permanent transcript entry.
- Persists across session save/resume (FR-008) via the existing AssistantMessage JSONL serialization.

**Pairing invariants**:

- For every `ToolUseBlockParam` with `id = X` emitted in a turn, there MUST eventually be a `ToolResultBlockParam` with `tool_use_id = X` in a subsequent user-role message (FR-009).
- Multiple `ToolUseBlockParam` may share the same turn (parallel tool calls); each gets its own `id` and its own pairing.
- Orphan tool-use (no matching tool-result by end of agentic loop) MUST be visible as a transcript-level error (FR-009).

**State transitions**:

```
backend_tool_call_frame
  → stream_event{content_block_start}
    → handleMessageFromStream pushes to streamingToolUses
      → stream_event{content_block_stop}
        → block index sealed
          → on terminal message_stop: AssistantMessage.content array materializes
            → persistent transcript entry
              → (next turn) tool_result content block links by tool_use_id
```

---

## 3. Tool-result content block

**Source of truth**: backend `tool_result` IPC frame (Spec 032 unchanged). TUI projects each frame into a user-role message carrying a single content block.

**TUI internal shape** (CC mirror):

```typescript
type ToolResultBlockParam = {
  type: 'tool_result'
  tool_use_id: string             // matches the originating tool_use block's id
  content: string | ContentBlock[]  // typically JSON-serialized envelope; CC also allows image / citation blocks
  is_error?: boolean              // optional flag; backend signals via envelope.kind === 'error' for KOSMOS
}
```

**Derivation from `tool_result` frame**:

| `tool_result` frame field | `ToolResultBlockParam` field | Notes |
|---|---|---|
| `call_id` | `tool_use_id` | Pairing key |
| `envelope` (PrimitiveOutput discriminated union) | `content` | `JSON.stringify(envelope)` — preserves the existing `_dispatch_primitive` payload shape |
| `envelope.kind === 'error'` | `is_error: true` | KOSMOS convention |

**Lifecycle**:

- Created when `deps.ts` receives `tool_result` frame.
- Yielded as: `createUserMessage([{type: 'tool_result', ...}])`.
- Becomes a user-role message in the transcript — distinct from the assistant message that emitted the prior tool-use.
- On the next agentic-loop iteration, `stdio.py` translates the user message back to `LLMChatMessage(role="tool", content=..., tool_call_id=...)` for the LLM, preserving multi-turn context (FR-010).

**Pairing invariants**: same as Entity 2.

**Token budgeting** (from CC `_cc_reference/toolResultStorage.ts:processToolResultBlock`):

- Out of scope for this epic — the existing `_dispatch_primitive` returns the raw envelope without truncation.
- Future work: if envelope size exceeds context budget, truncate via the CC `processToolResultBlock` pattern (Deferred D-7-adjacent).

---

## 4. Pending permission slot

**Source of truth**: TUI side — in-memory `sessionStore` slot.

**TUI internal shape**:

```typescript
interface PendingPermissionRequest {
  request_id: string                          // matches PermissionRequestFrame.request_id (uuid)
  primitive_kind: 'submit' | 'subscribe'      // currently the only gated primitives (Spec 033)
  description_ko: string                      // citizen-facing description (primary)
  description_en: string                      // citizen-facing description (fallback)
  risk_level: 'low' | 'medium' | 'high'
  receipt_id: string                          // stable receipt for audit ledger (Spec 035)
  enqueued_at: number                         // performance.now() timestamp (used for SC-003 measurement)
  resolver: (decision: PermissionDecision) => void  // private — Promise resolver
}

type PermissionDecision = 'granted' | 'denied' | 'timeout'
```

**Store API additions** (in `tui/src/store/sessionStore.ts`):

```typescript
interface SessionStoreActions {
  // existing actions ...

  // NEW (Step 7)
  setPendingPermission: (request: Omit<PendingPermissionRequest, 'resolver' | 'enqueued_at'>) => Promise<PermissionDecision>
  resolvePermissionDecision: (request_id: string, decision: PermissionDecision) => void
}
```

**Lifecycle**:

```
permission_request frame arrives in deps.ts
  → setPendingPermission({request_id, primitive_kind, ..., risk_level})
    → store internally creates PendingPermissionRequest with resolver Promise
    → if no slot occupied: write to head; PermissionGauntletModal subscribes and renders
    → if slot occupied: append to internal FIFO queue (FR-018)
    → returns Promise<PermissionDecision>

PermissionGauntletModal Y/N or 5-min timeout
  → resolvePermissionDecision(request_id, 'granted'|'denied'|'timeout')
    → store finds request in head or queue
    → calls request.resolver(decision)
    → if head: shifts queue; next request becomes head
    → modal re-subscribes to new head (or unmounts if empty)

deps.ts await resolves
  → emits PermissionResponseFrame{request_id, decision}
  → backend resumes _dispatch_primitive flow
```

**Validation rules**:

- `request_id` MUST be unique within the session (backend invariant).
- `primitive_kind` MUST be one of `{submit, subscribe}` per current Spec 033 gates. New gated primitives extending this set require Spec 033 amendment.
- `description_ko` MUST be non-empty (FR-014 Korean primary).
- `risk_level` follows existing Spec 033 mapping (`submit` → high, `subscribe` → medium).
- `receipt_id` MUST match a Spec 035 audit-ledger receipt id; emitted by backend.

**Timeout behavior**:

- Implemented via `setTimeout(resolver, timeoutMs)` set when the slot becomes head.
- `timeoutMs` reads `KOSMOS_PERMISSION_TIMEOUT_SEC * 1000` (Spec 033 default 300).
- On timeout, decision is `'timeout'`. The backend treats `'timeout'` identically to `'denied'` for fail-closed (Constitution §II).

**Edge cases**:

- Modal unmount while request is in-flight (e.g., session save mid-prompt): cleanup function calls `resolvePermissionDecision(active.request_id, 'denied')` to avoid hanging the backend.
- Same `request_id` arriving twice: idempotent — second call is dropped with a warning span.

---

## 5. System prompt augmentation

**Source of truth**: Python helper `kosmos.llm.system_prompt_builder.build_system_prompt_with_tools()`.

**Function signature**:

```python
def build_system_prompt_with_tools(
    base: str,
    tools: list[LLMToolDefinition],
) -> str:
    """Append a deterministic '## Available tools' section to base prompt.

    Args:
        base: The unmodified system prompt body (e.g., contents of prompts/system_v1.md).
        tools: The active inventory passed to the LLM on this turn.

    Returns:
        The augmented system prompt. If `tools` is empty, returns `base` unchanged.

    Determinism: the augmentation is byte-stable for a given (base, tools) input
    (sorted JSON, no timestamps, no env interpolation). Required by Spec 026
    prompt-hash invariant.
    """
```

**Output shape** (when tools is non-empty):

```
{base contents, unchanged}

## Available tools

### {tools[0].function.name}

{tools[0].function.description}

**Parameters**:

```json
{json.dumps(tools[0].function.parameters, indent=2, sort_keys=True, ensure_ascii=False)}
```

### {tools[1].function.name}

...
```

**Validation rules**:

- The augmentation MUST be byte-stable for byte-identical inputs (no timestamps, no random ordering, no env-dependent text).
- `tools` order is preserved as received (caller's responsibility — `getToolDefinitionsForFrame()` returns alphabetic).
- `ensure_ascii=False` so Korean descriptions in `description` field render natively.
- The leading `\n\n## Available tools\n` separator MUST be exactly two newlines + heading + one newline.

**Lifecycle**:

- Called once per `_handle_chat_request` invocation in `stdio.py`.
- Result is the LLM's system message text — held in memory for the duration of the turn, then GC'd.
- Never persisted to disk. Never logged at INFO level (the inventory section can be verbose). DEBUG-only logging.

**Spec 026 prompt-hash interaction**:

- The Spec 026 `kosmos.prompt.hash` OTEL span attribute hashes the **base** prompt (`prompts/system_v1.md`) — the augmentation is excluded from the hash so changing the inventory does not invalidate prompt-cache reuse.
- This is the documented behavior; this epic does not change it.

---

## Cross-entity invariants

| Invariant | Source | Validation point |
|---|---|---|
| `tool_use.id == tool_result.tool_use_id` | FR-009 | `ensureToolResultPairing()` mirror in `handleMessageFromStream` |
| Every `tool_call` frame produces exactly one `ToolUseBlockParam` | FR-006 | `deps.ts` projection |
| Every `tool_result` frame produces exactly one user-role message | FR-007 | `deps.ts` projection |
| `frame.tools` empty ⟹ backend uses registry fallback | FR-004 | `stdio.py:_handle_chat_request` |
| LLM-emitted unknown tool name ⟹ structured error to LLM next turn | FR-005, FR-010 | existing `stdio.py` whitelist + `LLMChatMessage(role="tool", ..., is_error=True)` |
| Permission denied/timeout ⟹ tool not invoked | FR-015, FR-017 | `stdio.py` `_check_permission_gate` |
| Permission granted ⟹ receipt emitted to audit ledger | FR-016 | Spec 035 ledger |
| System-prompt augmentation byte-stable | Spec 026 | `test_system_prompt_builder.py` golden |

---

## Out of scope (this data model)

- Composite tool envelopes — explicitly forbidden (Migration Tree § L1-B.B6).
- Plugin-tier tool entries — Epic #1979.
- Adapter-level Spec 033 receipt persistence — separate permission v2 epic.
- Long-lived `subscribe` stream lifecycle — separate subscribe-stream epic.
- Token-budgeting truncation of tool results — uses CC's `processToolResultBlock` pattern but deferred.
