# Research: Query Engine Core (Layer 1)

**Feature**: Epic #5 — Query Engine Core
**Date**: 2026-04-13
**Status**: Complete

## R-001: Async Generator Loop Pattern

**Decision**: Use `AsyncIterator[QueryEvent]` as the core communication protocol. The `query()` function is a standalone async generator; `QueryEngine` is a per-session orchestrator that owns state and delegates to `query()`.

**Rationale**: This separates session-level concerns (state, budget) from per-turn execution logic (FR-012). The async generator pattern provides natural backpressure, cancellation propagation, and streaming without callbacks or event buses.

**Reference analysis**:

- **Google ADK** (`google/adk-python`): Uses a three-layer stack: `Runner` → `BaseAgent.run_async()` → `BaseLlmFlow`. The flow engine runs `_preprocess_async()` → `_call_llm_async()` → `_postprocess_async()` → `handle_function_calls_async()` in a loop. Each step creates a fresh `LlmRequest` (immutable snapshot). The `Runner` yields `Event` objects via `async for event in _run_one_step_async()`. Termination is detected by `event.is_final_response()` — no function calls, not partial, not skipped.

- **Claude Agent SDK** (`anthropics/claude-agent-sdk-python`): `BaseAsyncToolRunner.__run__()` loops with `while not self._should_stop()`, yielding complete `ParsedBetaMessage` per iteration. Tool calls accumulate via `append_messages(message, response)`. Simpler than ADK but no streaming events during tool execution.

- **Claude Code reconstructed** (`ChinaSiro/claude-code-sourcemap`): The tool loop cycles through `preprocess → API stream → tool execute → decide`. Uses mutable conversation history with immutable per-call snapshots for prompt cache stability. `QueryEngine.ts` manages session state; `query.ts` handles per-turn execution.

**Alternatives considered**:
- Callback-based event bus (AutoGen style): Rejected — harder to propagate cancellation, no natural backpressure.
- State machine graph (Pydantic AI style): Rejected — over-engineered for v1 where the flow is linear. Can evolve to graph-based in Phase 2 for multi-agent swarms.

---

## R-002: Event Model Design

**Decision**: Use a discriminated union `QueryEvent` with Pydantic v2, keyed on a `type` literal field. Event types: `text_delta`, `tool_use`, `tool_result`, `usage_update`, `stop`.

**Rationale**: Discriminated unions are type-safe, serializable, and match the pattern used by both Google ADK (`Event` with `EventActions`) and the existing `StreamEvent` in `kosmos.llm.models`. The `type` field enables pattern matching and downstream routing.

**Reference analysis**:

- **Google ADK**: `Event` extends `LlmResponse` (Pydantic v2). Carries `EventActions` for side-effects (state_delta, artifact_delta, transfer_to_agent, requested_auth_configs). Each event has `invocation_id` (groups events per turn), `author`, `id` (UUID, refreshed on each yield), `timestamp`. Terminal detection via `is_final_response()`.

- **KOSMOS LLM module**: Existing `StreamEvent` uses `type: Literal["content_delta", "tool_call_delta", "usage", "done", "error"]`. The query engine `QueryEvent` sits one layer above — it wraps LLM stream events into higher-level engine events.

**Design**:
```
QueryEvent:
    type: "text_delta" | "tool_use" | "tool_result" | "usage_update" | "stop"
    # text_delta fields
    content: str | None
    # tool_use fields
    tool_name: str | None
    tool_call_id: str | None
    arguments: str | None
    # tool_result fields
    tool_result: ToolResult | None
    # usage_update fields
    usage: TokenUsage | None
    # stop fields
    stop_reason: StopReason | None
    stop_message: str | None
```

---

## R-003: Mutable History + Immutable Snapshots

**Decision**: Maintain a mutable `list[ChatMessage]` in `QueryState.messages`. Before each LLM call, create a shallow copy (`list(messages)`) as the immutable snapshot. The snapshot is what the LLM sees; the mutable list is what tool results append to.

**Rationale**: This is the single most important trick for prompt cache stability (per `docs/vision.md`). Without it, every tool response invalidates the prompt cache prefix, multiplying costs. The "Don't Break the Cache" paper (arxiv 2601.06007) confirms: static content should form a stable prefix, dynamic content (tool results, recent turns) should be placed at the suffix.

**Reference analysis**:

- **Claude Code reconstructed**: Explicitly uses mutable history + immutable per-call snapshots. The mutable list grows as tools append results; the snapshot is a frozen copy sent to the API.

- **Google ADK**: Creates a fresh `LlmRequest` per step (not per session). The `InvocationContext` holds the session, but each LLM call gets a new request built from the current state. `model_response_event.id` is refreshed on every yield to prevent conflicts.

- **"Don't Break the Cache" paper**: Recommends partitioning the prompt into a static prefix (system prompt + core tool schemas, high cache hit rate) and a dynamic suffix (conversation history + tool results, cache misses accepted). Tool results should NOT be part of the cached prefix block.

**Implementation**: `snapshot = list(state.messages)` before each `llm_client.complete()` call. The `ChatMessage` objects are frozen Pydantic models (`ConfigDict(frozen=True)`) so shallow copy suffices — no deep copy needed.

---

## R-004: Concurrent Tool Execution

**Decision**: Use `asyncio.TaskGroup` (Python 3.11+) for concurrent tool dispatch when the LLM requests multiple tools in a single response. All independent tool calls execute in parallel.

**Rationale**: Multi-ministry queries (e.g., KOROAD + KMA) involve independent API calls. Sequential execution would double or triple latency (SC-004 requires 30%+ reduction). `TaskGroup` provides structured concurrency with proper exception propagation — if one task fails, others are cancelled cleanly.

**Reference analysis**:

- **Google ADK**: Uses `asyncio.create_task()` + `asyncio.gather()` for parallel tool execution. Sync tools are offloaded to `ThreadPoolExecutor` via `run_in_executor`. Results are merged via `merge_parallel_function_response_events()`.

- **Claude Agent SDK**: Executes tools **sequentially** (for-loop over `tool_use_blocks`). No parallel execution — simpler but higher latency.

**Alternatives considered**:
- `asyncio.gather(*tasks)`: Works but `TaskGroup` is preferred in Python 3.11+ for structured concurrency and cleaner exception handling.
- Sequential execution only: Rejected — fails SC-004 (30% latency reduction requirement).

**Implementation**: `ToolExecutor.dispatch()` is already async. Wrap multiple dispatch calls in a `TaskGroup`. Fall back to sequential if `GovAPITool.is_concurrency_safe` is False for any tool in the batch (fail-closed per Constitution § II).

---

## R-005: Preprocessing Pipeline Architecture

**Decision**: Implement a multi-stage pipeline as an ordered list of transform functions. Each stage takes `list[ChatMessage]` and returns `list[ChatMessage]`. Stages run sequentially before each LLM call.

**Rationale**: The 128K context window fills quickly in multi-turn sessions with government API responses (often verbose XML/JSON). The pipeline must keep context within budget while preserving the most recent and relevant information.

**Reference analysis**:

- **Claude Code reconstructed**: Uses a multi-stage preprocessing pipeline: tool-result budget → snip → microcompact → collapse → autocompact. Each stage progressively compresses older content while preserving recent turns.

- **"Don't Break the Cache" paper**: Dynamic content placement matters. Compression should target the mutable suffix (older turns, verbose tool results) while leaving the static prefix (system prompt, core tools) untouched.

**Stage definitions (v1)**:

1. **tool_result_budget**: Truncate tool results that exceed a per-result token budget (e.g., 2000 tokens). Long API responses are summarized to `[truncated: {n} tokens → {budget} tokens]`.

2. **snip**: Remove tool results older than N turns that have already been synthesized into assistant responses. The LLM has already incorporated this data; keeping it wastes context.

3. **microcompact**: For messages older than M turns, strip whitespace, remove redundant formatting, and compact JSON payloads. Low-effort compression that preserves semantic content.

4. **collapse**: Merge consecutive same-role messages (e.g., multiple sequential tool results) into single messages. Reduces message count without losing content.

5. **autocompact**: When total estimated tokens exceed a threshold (e.g., 80% of context window), trigger an LLM-based summarization of the oldest N turns. This is the most aggressive stage and only runs when other stages are insufficient. **Deferred to v2** — v1 uses a simpler token-count warning.

---

## R-006: Token Counting Strategy

**Decision**: Use a character-based heuristic for token estimation (4 chars ≈ 1 token for English, 2 chars ≈ 1 token for Korean). Actual token counts come from LLM API usage responses.

**Rationale**: The FriendliAI K-EXAONE tokenizer is not publicly available as a Python library. Exact token counting would require an API call, defeating the purpose of pre-flight budget checks. A heuristic suffices for preprocessing decisions; the actual usage from the API response is used for budget accounting.

**Alternatives considered**:
- `tiktoken` (OpenAI): Wrong tokenizer for K-EXAONE. Would give inaccurate estimates.
- Custom tokenizer: Requires model-specific vocabulary files. Not available for K-EXAONE.
- API-based counting: Adds latency and cost for every preprocessing decision. Rejected.

**Implementation**: `estimate_tokens(text: str) -> int` function using character ratio heuristic. Korean text detection via Unicode range check (Hangul syllables U+AC00–U+D7A3).

---

## R-007: Budget Enforcement Design

**Decision**: Three-dimensional budget: token count (existing `UsageTracker`), turn count (new), and per-API daily quota (existing `RateLimiter`). Budget checks happen at the start of each loop iteration.

**Rationale**: FR-005 requires three dimensions. The existing `UsageTracker` handles tokens; turn counting is a simple counter; API quotas are tracked per-tool by the existing `RateLimiter`.

**Reference analysis**:

- **Google ADK**: `InvocationCostManager` tracks `max_llm_calls` and raises `LlmCallsLimitExceededError` when exceeded. Simple counter-based approach.

- **Existing KOSMOS**: `UsageTracker` already tracks token budget with `can_afford()` pre-flight and `debit()` post-call. `RateLimiter` tracks per-tool per-minute limits. Both are reusable.

**Implementation**: Add `max_turns: int` to `QueryEngineConfig`. Check `state.turn_count < config.max_turns` at loop start. Map to `StopReason.api_budget_exceeded` on violation.

---

## R-008: State Isolation Pattern

**Decision**: `QueryEngine` owns a `QueryState` per session. Each `query()` call (per turn) receives the state by reference and mutates it. A fresh `QueryContext` (lightweight, per-turn) is created for each turn to carry turn-specific metadata.

**Rationale**: Follows the Google ADK pattern of `InvocationContext` per turn within a persistent `Session`. Session state persists across turns; turn context is ephemeral.

**Reference analysis**:

- **Google ADK**: `InvocationContext` (Pydantic model) is created per `Runner.run_async()` call. Carries `session`, `agent`, `run_config`, `end_invocation` flag, and cost manager. Session state persists via `session_service.append_event()`.

- **Claude Code reconstructed**: `QueryState` holds citizen_session, messages, active_agents, usage_tracker, pending_api_calls, resolved_tasks. Mutable across turns.

**Design**:
```
QueryState (per-session, mutable):
    messages: list[ChatMessage]
    turn_count: int
    usage: UsageTracker
    resolved_tasks: list[str]

QueryContext (per-turn, ephemeral):
    state: QueryState (reference)
    llm_client: LLMClient
    tool_executor: ToolExecutor
    tool_registry: ToolRegistry
    config: QueryEngineConfig
    iteration: int
```
