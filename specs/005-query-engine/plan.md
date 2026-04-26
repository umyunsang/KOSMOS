# Implementation Plan: Query Engine Core

**Branch**: `feat/005-query-engine` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/005-query-engine/spec.md`

## Summary

Implement the async generator tool loop (Layer 1) that is the heartbeat of a KOSMOS session. The engine cycles through `preprocess -> LLM call -> tool dispatch -> decide` until the citizen's request is resolved or unrecoverably blocked. Core patterns adapted from Claude Code reconstructed architecture (mutable history + immutable snapshots), Google ADK (event-driven runner loop), and Claude Agent SDK (async generator protocol). Full research in [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx >=0.27, pydantic >=2.0, pydantic-settings >=2.0
**Storage**: N/A (in-memory session state only)
**Testing**: pytest >=8.0, pytest-asyncio >=0.24, respx >=0.23.1
**Target Platform**: Linux/macOS server (CLI interface for Phase 1)
**Project Type**: Library (query engine module within the KOSMOS monorepo)
**Performance Goals**: SC-004 — concurrent tool dispatch reduces turn latency by 30%+
**Constraints**: 128K context window (FriendliAI K-EXAONE), <100K token session budget default
**Scale/Scope**: Single-session conversational agent, 50+ turns, 5,000+ potential tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Reference-Driven | **PASS** | All 8 research decisions map to concrete references: Claude Code reconstructed, Google ADK, Claude Agent SDK, "Don't Break the Cache" paper. See research.md R-001 through R-008. |
| II. Fail-Closed Security | **PASS** | Concurrent tool dispatch defaults to sequential (fail-closed) when `is_concurrency_safe=False`. All tool dispatch goes through existing `ToolExecutor` which enforces validation and rate limits. |
| III. Pydantic v2 Strict | **PASS** | All new models (`QueryEvent`, `QueryEngineConfig`, `SessionBudget`) use Pydantic v2 with `ConfigDict(frozen=True)`. No `Any` in I/O schemas. Reuses existing `ChatMessage`, `ToolResult`, `TokenUsage`. |
| IV. Government API Compliance | **PASS** | No live API calls in tests. Reuses existing `RateLimiter` and `UsageTracker` for budget tracking. All test scenarios use mocked LLM and recorded fixtures. |
| V. Policy Alignment | **PASS** | Session budget enforcement (FR-005) ensures taxpayer-funded cost control. Single conversational window aligns with Principle 8. |

**Post-Phase 1 re-check**: All PASS. No violations introduced by data model or contract design.

## Project Structure

### Documentation (this feature)

```text
specs/005-query-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output (8 research decisions)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (test scenarios)
├── contracts/
│   └── query-engine.md  # Phase 1 output (public API contracts)
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/kosmos/engine/
├── __init__.py          # Module exports: QueryEngine, QueryEvent, StopReason, etc.
├── config.py            # QueryEngineConfig (pydantic-settings)
├── engine.py            # QueryEngine class (per-session orchestrator)
├── errors.py            # QueryEngineError hierarchy
├── events.py            # QueryEvent discriminated union + StopReason enum
├── models.py            # QueryState, QueryContext, SessionBudget
├── preprocessing.py     # PreprocessingPipeline + 4 stage functions
├── query.py             # query() standalone async generator
└── tokens.py            # estimate_tokens() heuristic

tests/engine/
├── conftest.py          # Shared fixtures: mock LLM, mock tools, configs
├── test_config.py       # QueryEngineConfig validation
├── test_engine.py       # QueryEngine integration tests (US-1 through US-4)
├── test_events.py       # QueryEvent model validation + discriminated union
├── test_preprocessing.py # Each pipeline stage independently
├── test_query.py        # query() unit tests with mock context
└── test_tokens.py       # estimate_tokens() heuristic accuracy
```

**Structure Decision**: New `src/kosmos/engine/` package following the same pattern as existing `src/kosmos/llm/` and `src/kosmos/tools/`. The engine module depends on both `llm` and `tools` modules but does not modify them. Test directory mirrors source layout.

**Dependency Graph**:
```
kosmos.engine  --->  kosmos.llm    (LLMClient, ChatMessage, TokenUsage, UsageTracker)
               --->  kosmos.tools  (ToolRegistry, ToolExecutor, ToolResult, GovAPITool)
```

## Reference Analysis

Each design decision traces to concrete reference sources per Constitution § I:

| Decision | Primary Reference | Secondary Reference |
|---|---|---|
| R-001: Async generator loop | Claude Agent SDK (`BaseAsyncToolRunner.__run__()`) | Google ADK (`Runner._run_one_step_async()`) |
| R-002: QueryEvent discriminated union | Google ADK (`Event` + `EventActions`) | KOSMOS `StreamEvent` (existing) |
| R-003: Mutable history + immutable snapshots | Claude Code reconstructed (`QueryEngine.ts`) | "Don't Break the Cache" (arxiv 2601.06007) |
| R-004: Concurrent tool dispatch | Google ADK (`asyncio.gather()` + `ThreadPoolExecutor`) | Python 3.11+ `asyncio.TaskGroup` |
| R-005: Multi-stage preprocessing | Claude Code reconstructed (5-stage pipeline) | "Don't Break the Cache" paper |
| R-006: Token estimation heuristic | K-EXAONE Korean token density research | No public tokenizer available |
| R-007: Three-dimensional budget | Google ADK (`InvocationCostManager`) | KOSMOS `UsageTracker` (existing) |
| R-008: State isolation pattern | Google ADK (`InvocationContext`) | Claude Code reconstructed (`QueryState`) |

## Key Design Decisions

### 1. Separation of QueryEngine and query()

`QueryEngine` (session orchestrator) owns state and exposes `run()`. The `query()` function (per-turn generator) contains the loop logic. This separation enables:
- Independent unit testing of the loop without session management
- Future swapping of the loop implementation (e.g., graph-based in Phase 2)
- Clean boundary between session concerns and execution concerns

### 2. Prompt Cache Stability via Immutable Snapshots

Before each LLM call: `snapshot = list(state.messages)`. `ChatMessage` objects are frozen Pydantic models, so shallow copy suffices. The snapshot preserves the static prefix (system prompt + tool schemas) across calls, maintaining cache hits.

### 3. Concurrent Tool Dispatch with Fail-Closed Default

Partition-sort algorithm groups consecutive `is_concurrency_safe=True` tools for parallel execution via `asyncio.TaskGroup`. Any tool with `is_concurrency_safe=False` (the default) serializes the batch. This ensures new tools are safe-by-default while enabling latency optimization for verified tools.

### 4. No-Raise Public API

`QueryEngine.run()` never raises. All runtime errors are captured as `QueryEvent(type="stop")` with an appropriate `StopReason`. This simplifies consumer code (no try/except around the async for loop) and ensures the stop event is always delivered.

## Complexity Tracking

No constitution violations requiring justification. All design decisions use existing patterns from the codebase (`kosmos.llm`, `kosmos.tools`) and reference implementations.
