# Contract — `ChatRequestFrame.tools` (TUI → backend)

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> The TUI publishes the active tool inventory on every conversation turn via the existing `ChatRequestFrame` arm. No new IPC frame arm is introduced.

## Direction

`tui` (sender) → `backend` (receiver), kind: `chat_request`.

## Schema (existing — Spec 032)

```python
class ChatRequestFrame(BaseFrame):
    kind: Literal["chat_request"]
    messages: list[ChatRequestMessage]
    system: str | None
    tools: list[ToolDefinition] = []   # ← this epic populates this field; default is empty list
    temperature: float | None
    top_p: float | None
    max_tokens: int | None
    # ... other Spec 032 fields unchanged
```

## Producer (TUI)

`tui/src/query/deps.ts` builds the frame at line ~73-81 (current pattern). After Step 2, the build adds:

```typescript
import { getToolDefinitionsForFrame } from './toolSerialization.js'

const frame: ChatRequestFrame = {
  session_id: sessionId,
  correlation_id: correlationId,
  ts: new Date().toISOString(),
  role: 'tui',
  kind: 'chat_request',
  messages: chatMessages as ChatRequestFrame['messages'],
  ...(systemText ? { system: systemText } : {}),
  tools: getToolDefinitionsForFrame(),     // ← NEW
}
```

## Consumer (backend)

`src/kosmos/ipc/stdio.py:_handle_chat_request` consumes at line ~1099-1101 (existing) plus Step 4 fallback:

```python
llm_tools: list[LLMToolDefinition] = []
for t in frame.tools:
    llm_tools.append(LLMToolDefinition.model_validate(t.model_dump()))

# NEW Step 4 — fallback when TUI omits tools
if not llm_tools:
    llm_tools = _ensure_tool_registry().export_core_tools_openai()
```

## Validation contract

- Each `ToolDefinition` MUST round-trip cleanly through Pydantic (`LLMToolDefinition.model_validate`).
- `function.name` MUST match an entry in the backend's `_ensure_tool_registry()` — backend silently drops unknown entries and logs a `kosmos.tool.unknown_in_frame` OTEL span event.
- `function.parameters` MUST be a valid JSON Schema 2020-12 document (verified by `$schema` field presence; validated by FriendliAI when invoking).
- `tools` MAY be empty — this triggers fallback to registry-default inventory.

## Authority semantics

- TUI is authoritative for **inventory composition** (e.g., user ministry-scope filtering, plugin opt-ins per Epic #1979).
- Backend is authoritative for **invocation execution** — it MUST refuse to execute any tool not in `_ensure_tool_registry()` regardless of `frame.tools` content (FR-005).
- The two are reconciled by the intersection rule: only tools present in BOTH the frame inventory AND the registry are eligible for invocation in the next LLM turn.

## Test coverage

- `tui/tests/ipc/handlers.test.ts` — assert `frame.tools.length >= 5` for a fresh session (5 primitives: lookup, resolve_location, submit, subscribe, verify).
- `tests/ipc/test_stdio.py` — assert backend receives non-empty `frame.tools` and uses them; assert empty `frame.tools` triggers registry fallback; assert unknown tool names are dropped with span event.

## OTEL attributes

- `kosmos.tools.frame.count` (int, gauge) — number of entries received in `frame.tools`.
- `kosmos.tools.frame.fallback_used` (bool) — true when fallback to registry was triggered.
- `kosmos.tools.frame.unknown_dropped` (int) — number of unknown entries silently dropped.
