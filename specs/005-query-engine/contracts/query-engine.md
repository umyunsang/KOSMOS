# API Contracts: Query Engine Core

**Feature**: Epic #5 — Query Engine Core
**Date**: 2026-04-13
**Status**: Complete

## Public Interface: QueryEngine

The `QueryEngine` class is the per-session orchestrator. It is the only public entry point for consumers of the query engine module.

### Constructor

```python
class QueryEngine:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: QueryEngineConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """Create a query engine session.

        Args:
            llm_client: Configured LLM client for streaming completions.
            tool_registry: Registry with registered tools and rate limiters.
            tool_executor: Dispatcher with registered adapters.
            config: Engine configuration. Uses defaults if None.
            system_prompt: System prompt for the LLM. Uses a minimal
                          hardcoded prompt for v1 if None.
        """
```

**Preconditions**:
- `llm_client` must be fully configured (token, base_url, model set).
- `tool_executor` must have adapters registered for all tools the LLM might call.
- `tool_registry` must have all tools registered before the first `run()` call.

### Method: run()

```python
async def run(self, user_message: str) -> AsyncIterator[QueryEvent]:
    """Execute a single turn of the query engine.

    This is the primary public API. Each call represents one citizen turn:
    the user message is appended to history, and the engine loops through
    preprocess -> LLM call -> tool dispatch -> decide until a stop condition.

    Args:
        user_message: The citizen's natural-language input.

    Yields:
        QueryEvent: Progress events in order — text_delta, tool_use,
                    tool_result, usage_update, and finally stop.

    Raises:
        No exceptions propagate. All errors are captured as
        QueryEvent(type="stop", stop_reason=StopReason.error_unrecoverable).

    Cancellation:
        When the caller stops consuming events (breaks out of the async for),
        all in-flight tool calls and the LLM stream are cancelled via
        standard async generator cleanup (FR-010).
    """
```

**Postconditions**:
- `state.messages` includes the user message and all assistant/tool messages from this turn.
- `state.turn_count` is incremented by 1.
- `state.usage` is debited for all LLM calls made.
- The last event yielded is always `QueryEvent(type="stop")` with a `StopReason`.

**Event ordering guarantee**:
```
[text_delta]* [tool_use tool_result]* [usage_update] ... [stop]
```
Within a single LLM call: zero or more `text_delta` events, followed by zero or more `tool_use`/`tool_result` pairs, followed by one `usage_update`. The `stop` event is always the final event of the turn.

### Method: budget

```python
@property
def budget(self) -> SessionBudget:
    """Return a read-only snapshot of current budget status."""
```

### Method: message_count

```python
@property
def message_count(self) -> int:
    """Return the number of messages in the conversation history."""
```

---

## Internal Interface: query()

The `query()` function is a standalone async generator that handles per-turn execution logic. It is separated from `QueryEngine` to enable independent testing (FR-012).

```python
async def query(ctx: QueryContext) -> AsyncIterator[QueryEvent]:
    """Execute one turn of the query loop.

    The loop:
    1. Run preprocessing pipeline on ctx.state.messages
    2. Create immutable message snapshot: list(ctx.state.messages)
    3. Stream LLM completion with tool definitions
    4. Yield text_delta events as content streams
    5. If tool_calls in response:
       a. Yield tool_use events for each call
       b. Dispatch tools (concurrent if safe, sequential otherwise)
       c. Yield tool_result events
       d. Append tool results to ctx.state.messages
       e. Yield usage_update
       f. Continue loop (iteration += 1)
    6. If no tool_calls: yield usage_update, yield stop event, return
    7. If iteration >= config.max_iterations: yield stop(max_iterations_reached)

    Args:
        ctx: Per-turn context with references to state, LLM client, tools, config.

    Yields:
        QueryEvent stream as described above.
    """
```

---

## Internal Interface: PreprocessingPipeline

```python
class PreprocessingPipeline:
    def __init__(self, stages: list[PreprocessStage] | None = None) -> None:
        """Initialize with optional custom stages.

        Default stages (in order): tool_result_budget, snip, microcompact, collapse.
        """

    def run(
        self,
        messages: list[ChatMessage],
        config: QueryEngineConfig,
    ) -> list[ChatMessage]:
        """Apply all stages sequentially to the message list.

        Each stage receives a copy of the list and returns a new list.
        The original list is not modified.

        Args:
            messages: Current conversation history.
            config: Engine config with threshold parameters.

        Returns:
            Processed message list ready for LLM snapshot.
        """
```

---

## Internal Interface: Concurrent Tool Dispatch

```python
async def dispatch_tool_calls(
    tool_calls: list[ToolCall],
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
) -> list[ToolResult]:
    """Dispatch multiple tool calls with concurrency optimization.

    Partition-sort algorithm:
    1. Look up each tool's is_concurrency_safe flag.
    2. Group consecutive concurrency-safe tools together.
    3. Execute each safe group concurrently via asyncio.TaskGroup.
    4. Execute non-safe tools sequentially.
    5. Return results in the same order as the input tool_calls.

    Args:
        tool_calls: List of ToolCall objects from the LLM response.
        tool_registry: Registry for looking up tool concurrency flags.
        tool_executor: Executor for dispatching individual calls.

    Returns:
        List of ToolResult objects, one per input tool_call, in order.
    """
```

---

## Internal Interface: Token Estimation

```python
def estimate_tokens(text: str) -> int:
    """Estimate token count using character-based heuristic.

    Korean text (Hangul syllables U+AC00-U+D7A3): 2 chars per token.
    Other text: 4 chars per token.

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count (always >= 0).
    """
```

---

## Error Contract

The query engine module follows a **no-raise** contract at the public boundary:

| Error source | Handling |
|---|---|
| LLM call failure (timeout, auth, connection) | Yield `stop(error_unrecoverable)` with guidance message |
| Tool execution failure | Inject `ToolResult(success=False)` into history; let LLM decide |
| Budget exceeded (tokens/turns) | Yield `stop(api_budget_exceeded)` with remaining budget info |
| Unknown tool requested by LLM | Inject error ToolResult; let LLM retry with valid tool |
| Max iterations reached | Yield `stop(max_iterations_reached)` with iteration count |
| Caller cancellation | Async generator cleanup cancels in-flight work |

Internal functions may raise for programming errors (assertion failures, type errors), but all runtime errors are captured and surfaced as `QueryEvent(type="stop")`.

---

## Module Exports

```python
# src/kosmos/engine/__init__.py

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, QueryState, SessionBudget

__all__ = [
    "QueryEngine",
    "QueryEngineConfig",
    "QueryContext",
    "QueryEvent",
    "QueryState",
    "SessionBudget",
    "StopReason",
]
```
