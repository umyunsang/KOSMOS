# Data Model: Query Engine Core

**Feature**: Epic #5 — Query Engine Core
**Date**: 2026-04-13
**Status**: Complete

## Entity Definitions

### QueryEngineConfig

Configuration for a query engine session. Immutable after construction.

```python
class QueryEngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_iterations: int = 10
    """Per-turn iteration limit to prevent infinite tool-calling loops (FR-004)."""

    max_turns: int = 50
    """Session-level turn limit for budget enforcement (FR-005)."""

    context_window: int = 128_000
    """Model context window in tokens. Used for preprocessing threshold."""

    preprocessing_threshold: float = 0.8
    """Fraction of context_window that triggers aggressive compression."""

    tool_result_budget: int = 2000
    """Max tokens per individual tool result before truncation."""

    snip_turn_age: int = 5
    """Tool results older than this many turns are candidates for snipping."""

    microcompact_turn_age: int = 3
    """Messages older than this many turns get whitespace compression."""
```

**Relationships**: Owned by `QueryEngine`. Passed by reference to `QueryContext`.
**Validation**: All int fields must be positive. `preprocessing_threshold` must be in (0.0, 1.0].

---

### QueryState

Accumulated state for the current session. Mutable across turns. Per-session lifecycle.

```python
class QueryState:
    messages: list[ChatMessage]
    """Mutable conversation history. Grows as tool results and assistant responses are appended."""

    turn_count: int = 0
    """Number of user-initiated turns completed in this session."""

    usage: UsageTracker
    """Token budget tracker (reused from kosmos.llm.usage)."""

    resolved_tasks: list[str] = []
    """Completed civil-affairs sub-goals tracked for session continuity."""
```

**Relationships**: Owned by `QueryEngine`. Passed by reference to `QueryContext` each turn. References `ChatMessage` (from `kosmos.llm.models`) and `UsageTracker` (from `kosmos.llm.usage`).
**State transitions**: `messages` grows monotonically (append-only). `turn_count` increments by 1 per `QueryEngine.run()` call.

---

### QueryContext

Lightweight per-turn context carrying references to shared infrastructure. Ephemeral — created and discarded each turn.

```python
class QueryContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    state: QueryState
    """Reference to the session-level mutable state."""

    llm_client: LLMClient
    """LLM client for streaming completions."""

    tool_executor: ToolExecutor
    """Dispatcher for tool calls."""

    tool_registry: ToolRegistry
    """Registry for tool lookup and schema export."""

    config: QueryEngineConfig
    """Session configuration."""

    iteration: int = 0
    """Current iteration within this turn (0-indexed)."""
```

**Relationships**: References `QueryState`, `LLMClient`, `ToolExecutor`, `ToolRegistry`, `QueryEngineConfig`. Created by `QueryEngine` at the start of each turn.
**Lifecycle**: Created at turn start. Discarded at turn end. Never persisted.

---

### StopReason

Enumeration of why a query loop terminated. Used in `QueryEvent(type="stop")`.

```python
class StopReason(str, Enum):
    task_complete = "task_complete"
    """Civil-affairs request fully resolved."""

    end_turn = "end_turn"
    """LLM responded without tool calls (simple answer or clarification)."""

    needs_citizen_input = "needs_citizen_input"
    """Awaiting citizen clarification before proceeding."""

    needs_authentication = "needs_authentication"
    """Higher identity verification level required."""

    api_budget_exceeded = "api_budget_exceeded"
    """Session token, turn, or API quota budget exhausted."""

    max_iterations_reached = "max_iterations_reached"
    """Per-turn iteration limit hit (FR-004 safety guard)."""

    error_unrecoverable = "error_unrecoverable"
    """No fallback path available; route citizen to human channel."""

    cancelled = "cancelled"
    """Citizen or caller cancelled the session (FR-010)."""
```

**Relationships**: Embedded in `QueryEvent(type="stop")`. Checked by `QueryEngine` to decide whether to continue the session.

---

### QueryEvent

Discriminated union of progress events yielded by the async generator. Keyed on `type` literal field.

```python
class QueryEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["text_delta", "tool_use", "tool_result", "usage_update", "stop"]
    """Event discriminator."""

    # --- text_delta fields ---
    content: str | None = None
    """Incremental text content from the LLM stream."""

    # --- tool_use fields ---
    tool_name: str | None = None
    """Name of the tool being invoked."""

    tool_call_id: str | None = None
    """Unique identifier for this tool invocation."""

    arguments: str | None = None
    """JSON-serialized arguments for the tool call."""

    # --- tool_result fields ---
    tool_result: ToolResult | None = None
    """Structured result from tool execution (reused from kosmos.tools.models)."""

    # --- usage_update fields ---
    usage: TokenUsage | None = None
    """Token usage snapshot after an LLM call (reused from kosmos.llm.models)."""

    # --- stop fields ---
    stop_reason: StopReason | None = None
    """Why the loop terminated. Present only when type='stop'."""

    stop_message: str | None = None
    """Human-readable explanation for the stop event."""
```

**Relationships**: References `ToolResult` (from `kosmos.tools.models`), `TokenUsage` (from `kosmos.llm.models`), `StopReason`.
**Validation**: A model validator enforces that type-specific fields are populated correctly (e.g., `stop_reason` only when `type="stop"`).

---

### PreprocessingPipeline

Ordered sequence of context compression stages applied before each LLM call.

```python
PreprocessStage = Callable[[list[ChatMessage], QueryEngineConfig], list[ChatMessage]]

class PreprocessingPipeline:
    stages: list[PreprocessStage]
    """Ordered list of transform functions. Each stage receives the message list
    and config, returns a (possibly modified) message list."""
```

**Stage definitions (v1)**:

| Stage | Function | Description |
|---|---|---|
| `tool_result_budget` | Truncate oversized tool results | Tool results exceeding `config.tool_result_budget` tokens are truncated with `[truncated: N -> M tokens]` |
| `snip` | Remove stale tool results | Tool results older than `config.snip_turn_age` turns that were already synthesized by the assistant |
| `microcompact` | Compress old messages | Strip whitespace, compact JSON in messages older than `config.microcompact_turn_age` turns |
| `collapse` | Merge consecutive same-role messages | Reduce message count by merging sequential tool results or user messages |

**Relationships**: Used by the `query()` function before each LLM call. Operates on `list[ChatMessage]` from `QueryState.messages`. Uses `QueryEngineConfig` for thresholds.

**Note**: `autocompact` (LLM-based summarization) is deferred to v2. V1 uses a token-count warning when approaching limits.

---

### SessionBudget

Read-only view of the current budget status across all three dimensions.

```python
class SessionBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    tokens_used: int
    tokens_remaining: int
    tokens_budget: int

    turns_used: int
    turns_remaining: int
    turns_budget: int

    is_exhausted: bool
    """True if any dimension is fully consumed."""
```

**Relationships**: Computed from `QueryState.usage` and `QueryState.turn_count` + `QueryEngineConfig.max_turns`. Emitted as part of `QueryEvent(type="usage_update")` for observability.

---

## Entity Relationship Diagram

```
QueryEngine (per-session orchestrator)
  ├── owns QueryState (mutable, session lifecycle)
  │     ├── messages: list[ChatMessage]  (from kosmos.llm.models)
  │     ├── usage: UsageTracker          (from kosmos.llm.usage)
  │     └── resolved_tasks: list[str]
  ├── owns QueryEngineConfig (immutable)
  ├── references LLMClient              (from kosmos.llm.client)
  ├── references ToolExecutor            (from kosmos.tools.executor)
  └── references ToolRegistry            (from kosmos.tools.registry)
        │
        ▼
  query() async generator (per-turn)
  ├── receives QueryContext (ephemeral, per-turn)
  ├── yields QueryEvent (discriminated union)
  │     ├── text_delta  → content: str
  │     ├── tool_use    → tool_name, tool_call_id, arguments
  │     ├── tool_result → ToolResult (from kosmos.tools.models)
  │     ├── usage_update → TokenUsage + SessionBudget
  │     └── stop        → StopReason + stop_message
  └── uses PreprocessingPipeline (before each LLM call)
        ├── tool_result_budget
        ├── snip
        ├── microcompact
        └── collapse
```

## Token Estimation

```python
def estimate_tokens(text: str) -> int:
    """Character-based heuristic for token estimation.

    Korean (Hangul syllables U+AC00-U+D7A3): 2 chars ≈ 1 token
    Other (English, punctuation, etc.): 4 chars ≈ 1 token

    Used for preprocessing decisions only. Actual token counts
    come from the LLM API usage response.
    """
```

**Rationale**: FriendliAI EXAONE tokenizer is not publicly available. Heuristic suffices for preprocessing; actual usage from API is authoritative for budget accounting (R-006).
