# Phase 0 Research: Scenario 1 E2E — Route Safety

**Date**: 2026-04-13
**Spec**: [spec.md](./spec.md)

---

## Research Questions

### RQ-1: How to structure E2E test fixtures for the full pipeline?

**Decision**: Reuse the existing MockLLMClient pattern from `tests/engine/conftest.py` for LLM mocking, combined with `unittest.mock.AsyncMock` patching of `httpx.AsyncClient.get` for API fixtures. No new dependencies required.

**Rationale**: The codebase already has a proven MockLLMClient that replays pre-configured StreamEvent sequences. API adapter tests already load JSON fixtures from `tests/tools/*/fixtures/`. The E2E test combines both patterns: MockLLMClient drives the tool loop while patched httpx returns recorded API responses. This avoids adding VCR.py/pytest-recording as new dependencies — the existing approach is sufficient for deterministic replay.

**Alternatives considered**:
- **pytest-recording + VCR.py**: Cassette-based HTTP recording/replay. Rejected because all API adapters already have hand-crafted JSON fixtures and the project avoids adding dependencies outside spec-driven PRs. Revisit if fixture maintenance becomes burdensome.
- **respx**: httpx-native mock library. The project doesn't list it as a dependency; `unittest.mock.AsyncMock` on `httpx.AsyncClient.get` is already used in adapter tests and is zero-dependency.

### RQ-2: How to wire the full pipeline in a test?

**Decision**: Create an `E2EFixtureBuilder` helper in a dedicated `tests/e2e/conftest.py` that assembles a complete QueryEngine with real ToolRegistry, real tool registrations, real ToolExecutor (with RecoveryExecutor), real PermissionPipeline, real ContextBuilder — but with MockLLMClient and patched httpx. This gives maximum integration coverage while remaining deterministic.

**Rationale**: The query loop in `engine/query.py` dispatches tool calls through `dispatch_tool_calls()` which routes through the permission pipeline and tool executor. The tool executor delegates to RecoveryExecutor which calls the real adapter functions. The adapter functions call `httpx.AsyncClient.get` — this is the seam where we inject recorded fixtures. Everything above httpx runs as production code.

**Reference mapping**:
- `claude-code-sourcemap` → `query.ts` tool loop flow: streaming LLM → tool dispatch → result injection (our `query.py` mirrors this)
- `claude-reviews-claude` → `architecture/01-query-engine.md` full pipeline (our QueryEngine.run() → query() generator)
- `claw-code` → `runtime/src/conversation.rs` agentic loop (our async generator pattern)

### RQ-3: How to test degraded paths?

**Decision**: Create separate MockLLMClient response sequences for degraded scenarios. Patch individual API adapter httpx calls to raise `httpx.TimeoutException` or return error JSON. The road_risk_score composite adapter already handles partial failures via `asyncio.gather(return_exceptions=True)`.

**Rationale**: The composite adapter's `_call()` function already tolerates 1-2 inner adapter failures and populates `data_gaps`. The E2E test just needs to trigger these code paths by making specific httpx calls fail. No Chaos Toolkit needed — simple mock patching is sufficient for unit/integration tests.

**Reference mapping**:
- OpenAI Agents SDK → retry matrix with composable policies (our RecoveryExecutor)
- LangGraph → `ToolNode(handle_tool_errors=True)` fail-closed at tool boundary (our ToolExecutor never raises)
- stamina → enforced jitter and capped backoff (our RetryPolicy)
- aiobreaker → per-API circuit breaker (our CircuitBreaker)

### RQ-4: How to verify cost accounting?

**Decision**: Assert UsageTracker totals after E2E flow completion. MockLLMClient emits deterministic TokenUsage in StreamEvent(type="usage"), so expected totals are known at test authoring time. Assert `usage.total_input_tokens` and `usage.total_output_tokens` match the sum of all mock StreamEvent usage values.

**Rationale**: The UsageTracker is already debited by LLMClient.stream() internally. Since MockLLMClient emits the same StreamEvent types, the tracker accumulates usage identically to production. No tokencost dependency needed.

### RQ-5: MockLLMClient response design for multi-tool E2E

**Decision**: Design a 2-iteration MockLLMClient sequence:
1. **Iteration 1**: LLM requests `road_risk_score` tool → engine dispatches composite adapter → adapter fans out to 3 APIs → results injected into history
2. **Iteration 2**: LLM receives tool results and generates a Korean text response with route safety recommendation

This mirrors the real flow: the LLM decides which tool to call, the engine executes it, injects the result, and the LLM synthesizes a final answer.

**Reference mapping**:
- Claude Agent SDK → async generator tool loop pattern (yield tool_use → yield tool_result → yield text_delta)
- Anthropic docs → tool use protocol (assistant message with tool_calls → tool results → assistant synthesis)

---

## Deferred Items Validation

| Item | Tracking Issue | Status |
|------|---------------|--------|
| Multi-turn conversation E2E | #317 | OPEN, created by `/speckit-taskstoissues` |
| Geocoding integration | #288 | OPEN, verified |
| LLM output quality metrics | #290 | OPEN, verified |
| Scenario 2 E2E | #18 | OPEN, verified |
| Scenario 3 E2E | #19 | OPEN, verified |
| Scenario 4 E2E | #23 | OPEN, verified |
| Scenario 5 E2E | #24 | OPEN, verified |

**Unregistered deferral pattern scan**: No untracked "separate epic", "future phase", or "v2" references found in spec.md outside the Deferred Items table. PASS.

---

## New Reference Sources (from deep research)

These sources were identified during research but are **not added as dependencies**. They inform test design patterns only:

| Source | License | What we learn |
|--------|---------|---------------|
| inline-snapshot (`15r10nk/inline-snapshot`) | MIT | AST-based snapshot testing pattern — informs how we could snapshot fusion outputs for regression detection. Not adopted as dependency; manual assertions are sufficient for P1 scope. |
| pytest-httpx (`Colin-b/pytest_httpx`) | MIT | Strict unmatched-request assertion pattern — we replicate this by asserting mock call counts after each E2E test. |
| DeepEval (`confident-ai/deepeval`) | Apache-2.0 | LLM evaluation metrics taxonomy — informs future observability epic (#290). Not needed for pipeline correctness testing. |
