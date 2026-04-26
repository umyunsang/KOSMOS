# Feature Specification: Query Engine Core

**Feature Branch**: `feat/005-query-engine`
**Created**: 2026-04-13
**Status**: Draft
**Input**: Epic #5 — Query Engine Core (Layer 1)

## User Scenarios & Testing

### User Story 1 - Single-Turn Query Resolution (Priority: P1)

A citizen submits a natural-language question about a government service. The query engine processes the request through one or more tool calls and returns a consolidated answer.

**Why this priority**: This is the fundamental loop — without single-turn resolution, no other scenario works. It validates the core preprocess → LLM call → tool dispatch → answer pipeline.

**Independent Test**: Can be fully tested by sending a query like "서울 강남구 교통사고 현황 알려줘" with a mocked LLM and recorded tool fixtures. The engine should cycle through tool selection, execution, and response synthesis, then terminate with `task_complete`.

**Acceptance Scenarios**:

1. **Given** a citizen session with valid authentication, **When** the citizen asks a question that requires one tool call, **Then** the engine calls the LLM, dispatches the tool, injects the result, re-calls the LLM, and yields a final answer with `StopReason.task_complete`.
2. **Given** a citizen session, **When** the citizen asks a question that requires two sequential tool calls (e.g., get region code → get accident data), **Then** the engine loops twice through tool dispatch before yielding the final answer.
3. **Given** a citizen session, **When** the LLM responds without requesting any tool, **Then** the engine yields the assistant message directly and terminates with `end_turn`.

---

### User Story 2 - Multi-Turn Conversation (Priority: P2)

A citizen engages in a back-and-forth conversation where later questions reference earlier answers. The engine maintains conversation history across turns while managing the context window budget.

**Why this priority**: Real citizen interactions are rarely single-turn. The engine must accumulate history, apply compression when needed, and maintain cache-friendly message snapshots.

**Independent Test**: Can be tested by sending 5+ sequential queries in the same session, verifying that the engine references prior context and applies the preprocessing pipeline (snip, microcompact, autocompact) when token counts approach the limit.

**Acceptance Scenarios**:

1. **Given** a session with 3 prior turns, **When** the citizen asks a follow-up referencing earlier data, **Then** the LLM receives the full mutable history and produces a contextually relevant answer.
2. **Given** a session approaching the context window limit, **When** a new turn begins, **Then** the preprocessing pipeline compresses older turns and the session continues without error.
3. **Given** a session with mutable message history, **When** the engine calls the LLM, **Then** it passes an immutable snapshot (copy) of the history to preserve cache stability.

---

### User Story 3 - Budget Enforcement and Graceful Termination (Priority: P3)

The engine enforces session-level cost and turn budgets, terminating gracefully when limits are exceeded and communicating the reason to the citizen.

**Why this priority**: Government AI services operate under taxpayer-funded budget constraints. The engine must prevent runaway cost while providing a clear explanation when it stops.

**Independent Test**: Can be tested by configuring a low budget (e.g., 3 turns, $0.01 USD) and verifying the engine terminates with the appropriate `StopReason` and a user-friendly message.

**Acceptance Scenarios**:

1. **Given** a session budget of N turns, **When** the engine reaches turn N, **Then** it yields `StopReason.api_budget_exceeded` with a message explaining the limit.
2. **Given** a per-API daily quota tracker, **When** a tool call would exceed the remaining quota, **Then** the engine skips that tool and either uses cached data or informs the citizen.
3. **Given** an unrecoverable error from a tool, **When** the error recovery layer reports no fallback available, **Then** the engine yields `StopReason.error_unrecoverable` with guidance to contact a human service channel.

---

### User Story 4 - Concurrent Tool Execution (Priority: P3)

When the LLM requests multiple independent tool calls in a single turn, the engine executes them concurrently to reduce citizen wait time.

**Why this priority**: Multi-ministry queries (e.g., KOROAD + KMA) involve independent API calls that can run in parallel. Sequential execution would double or triple latency unnecessarily.

**Independent Test**: Can be tested by mocking an LLM response that requests two tool calls simultaneously, then verifying both execute concurrently (total time closer to max(tool_a, tool_b) rather than sum).

**Acceptance Scenarios**:

1. **Given** an LLM response requesting tools A and B with no dependency between them, **When** the engine dispatches tools, **Then** both execute concurrently and results are injected in the order the LLM requested them.
2. **Given** concurrent tool execution, **When** one tool fails and the other succeeds, **Then** the engine injects both results (success and error) and lets the LLM decide next steps.

---

### Edge Cases

- What happens when the LLM produces a tool call for a tool not in the registry? The engine must return a structured error result to the LLM, not crash.
- What happens when the LLM enters an infinite tool-calling loop? A `max_iterations` guard per turn must break the cycle.
- What happens when the citizen cancels mid-turn? All in-flight tool calls and the LLM stream must be cancelled via async generator cancellation.
- What happens when the session is resumed after a crash? The mutable history must be recoverable from persisted state.

## Requirements

### Functional Requirements

- **FR-001**: System MUST implement an async generator loop that cycles through preprocess → LLM call → tool dispatch → decide until a stop condition is met.
- **FR-002**: System MUST maintain a mutable conversation history that persists across turns within a session.
- **FR-003**: System MUST create an immutable snapshot of the message history before each LLM call to preserve prompt cache stability.
- **FR-004**: System MUST enforce a per-turn iteration limit (`max_iterations`) to prevent infinite tool-calling loops.
- **FR-005**: System MUST track and enforce session-level budgets across three dimensions: USD cost, turn count, and token count.
- **FR-006**: System MUST yield structured progress events (tool dispatched, tool completed, LLM streaming) that callers can consume at their own rate via the async generator protocol.
- **FR-007**: System MUST execute independent tool calls concurrently within a single turn.
- **FR-008**: System MUST run a multi-stage preprocessing pipeline before each LLM call to manage context window size (tool-result budget, snip, microcompact, collapse, autocompact).
- **FR-009**: System MUST terminate the loop with a specific `StopReason` enum value communicating why the session ended.
- **FR-010**: System MUST propagate cancellation through async generator protocol when the citizen or caller stops consuming events.
- **FR-011**: System MUST record per-API and per-LLM-call usage metrics via an observability interface (counters for tokens, cache hits, API calls per ministry).
- **FR-012**: System MUST separate session-level state management (QueryEngine) from per-turn execution logic (query function) to enable independent testing and reuse.

### Key Entities

- **QueryEngine**: Per-conversation orchestrator that owns the session state and dispatches individual turns.
- **QueryState**: Accumulated state for the current session — citizen session info, messages, active agents, usage tracker, pending API calls, resolved tasks.
- **StopReason**: Enumeration of why a query loop terminated — task_complete, needs_citizen_input, needs_authentication, api_budget_exceeded, error_unrecoverable.
- **QueryEvent**: Discriminated union of progress events yielded by the async generator — text_delta, tool_use, tool_result, usage_update, stop.
- **PreprocessingPipeline**: Ordered sequence of context compression stages applied before each LLM call.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Single-turn queries resolve in 3 or fewer engine iterations for 90% of recorded test scenarios.
- **SC-002**: Multi-turn conversations maintain coherent context across at least 20 turns without manual intervention.
- **SC-003**: Budget enforcement terminates sessions within 1 iteration of the configured limit (no budget overrun beyond a single tool call).
- **SC-004**: Concurrent tool execution reduces total turn latency by at least 30% compared to sequential execution for multi-tool turns.
- **SC-005**: The preprocessing pipeline keeps context within the model window budget for conversations up to 50 turns.
- **SC-006**: All unit tests pass with mocked LLM and recorded tool fixtures, with no live API calls required.

## Assumptions

- The LLM Client (Epic #4, completed) provides a stable async streaming interface that yields content block deltas.
- The Tool System (Epic #6, completed) provides a ToolRegistry with `lookup()`, `search()`, and a ToolExecutor with `dispatch()`.
- Context Assembly (Epic #9, in progress) will provide the system prompt and per-turn context; for v1, the query engine uses a minimal hardcoded system prompt.
- Error Recovery (Epic #10, in progress) will provide retry and circuit breaker logic; for v1, the query engine does basic try/except with logged errors.
- The Permission Pipeline (Epic #8, future) will gate tool calls; for v1, the engine executes tools directly without permission checks.
- The model context window is at least 128K tokens (FriendliAI EXAONE via OpenAI-compatible API).
