# Implementation Plan: Scenario 1 E2E — Route Safety

**Branch**: `013-scenario1-e2e-route-safety` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/012-scenario1-e2e-route-safety/spec.md`

## Summary

End-to-end integration test for the Phase 1 capstone: a citizen's route safety query flows through the complete KOSMOS pipeline (QueryEngine → ContextBuilder → MockLLM → ToolDispatch → KOROAD/KMA adapters → RecoveryExecutor → PermissionPipeline → Response synthesis). All API calls use recorded JSON fixtures; LLM responses use MockLLMClient. Tests validate happy-path, degraded-path, cost accounting, and permission audit scenarios.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: pytest, pytest-asyncio, httpx (mock targets), pydantic v2 (existing)
**Storage**: N/A (in-memory test state only)
**Testing**: pytest + pytest-asyncio, `unittest.mock.AsyncMock`
**Target Platform**: macOS/Linux (CI)
**Project Type**: Integration test suite (no new production code)
**Performance Goals**: Full E2E test suite completes in <10 seconds
**Constraints**: Zero live API calls; zero new production dependencies
**Scale/Scope**: ~6-8 test files, ~20-30 test cases, ~800-1200 lines of test code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | Design decisions mapped to claude-code-sourcemap, claude-reviews-claude, claw-code, Claude Agent SDK, OpenAI Agents SDK |
| II. Fail-Closed Security | PASS | No new production code; tests verify existing fail-closed behavior |
| III. Pydantic v2 Strict Typing | PASS | No new I/O schemas; tests use existing Pydantic models |
| IV. Government API Compliance | PASS | All API calls use recorded fixtures; `@pytest.mark.live` for any future live tests |
| V. Policy Alignment | N/A | No policy changes in test code |
| VI. Deferred Work Accountability | PASS | All deferred items tracked; NEEDS TRACKING resolved → #317 |

**Post-Phase 1 re-check**: PASS — no new violations introduced by design artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/012-scenario1-e2e-route-safety/
├── plan.md              # This file
├── research.md          # Phase 0: research decisions
├── data-model.md        # Phase 1: test fixture data models
├── contracts/           # Phase 1: test interface contracts
│   └── e2e-test-contract.md
└── tasks.md             # Phase 2: task breakdown (next step)
```

### Source Code (repository root)

```text
tests/
├── e2e/                        # NEW — E2E integration tests
│   ├── __init__.py
│   ├── conftest.py             # E2EFixtureBuilder, shared fixtures
│   ├── test_route_safety_happy.py      # P1: happy-path scenario
│   ├── test_route_safety_degraded.py   # P2: degraded-path scenarios
│   ├── test_route_safety_budget.py     # P3: cost accounting
│   ├── test_route_safety_permission.py # P3: permission audit
│   └── test_route_safety_edge.py       # Edge cases
├── tools/koroad/fixtures/      # EXISTING — reuse koroad fixtures
├── tools/kma/fixtures/         # EXISTING — reuse kma fixtures
└── fixtures/koroad/            # EXISTING — reuse koroad fixtures
```

**Structure Decision**: New `tests/e2e/` directory for integration tests. Reuse existing per-adapter fixtures. No new production source directories.

## Implementation Approach

### Layer Integration Map

```
tests/e2e/conftest.py (E2EFixtureBuilder)
    │
    ├── MockLLMClient (from tests/engine/conftest.py pattern)
    │   └── Pre-configured StreamEvent sequences
    │
    ├── ContextBuilder (real, from src/kosmos/context/)
    │   └── build_system_message() with real ToolRegistry
    │
    ├── ToolRegistry (real, from src/kosmos/tools/)
    │   ├── koroad_accident_search (registered)
    │   ├── kma_weather_alert_status (registered)
    │   ├── kma_current_observation (registered)
    │   └── road_risk_score (registered)
    │
    ├── ToolExecutor (real, from src/kosmos/tools/)
    │   ├── Real adapters registered
    │   └── RecoveryExecutor (real, from src/kosmos/recovery/)
    │       ├── RetryPolicy
    │       ├── CircuitBreaker (per-adapter)
    │       └── ErrorClassifier
    │
    ├── PermissionPipeline (real, optional)
    │   └── SessionContext (public-auth for P1)
    │
    └── httpx.AsyncClient.get ← PATCHED (mock seam)
        └── URL-matched fixture responses
```

### MockLLMClient Response Design

**Happy-path (2-iteration):**
1. Iteration 1: LLM emits `tool_call_delta` for `road_risk_score` with appropriate input args
2. Iteration 2: LLM emits `content_delta` with Korean route safety recommendation text

**Degraded-path (2-iteration):**
1. Same as happy-path iteration 1 (LLM still requests tool)
2. LLM receives tool result with `data_gaps` → synthesizes degraded response

**Edge cases:**
- Unknown tool: LLM requests `nonexistent_tool` → ToolNotFoundError captured
- Budget exceeded: MockLLMClient with budget=1 → BudgetExceededError
- Stream interrupted: MockLLMClient raises StreamInterruptedError on first call
- Max iterations: MockLLMClient always returns tool calls → iteration guard

### Reference Mapping (Constitution Principle I)

| Design Decision | Primary Reference | Secondary Reference |
|----------------|-------------------|---------------------|
| Async generator E2E test structure | Claude Agent SDK (tool loop) | claude-code-sourcemap (`query.ts` tool dispatch) |
| MockLLMClient replay pattern | claude-reviews-claude (state management) | claw-code (`conversation.rs` agentic loop) |
| Tool dispatch verification | Pydantic AI (schema-driven registry) | Claude Agent SDK (tool definitions) |
| Degraded-path fault injection | OpenAI Agents SDK (retry matrix) | LangGraph (ToolNode handle_tool_errors) |
| Permission audit assertion | OpenAI Agents SDK (guardrail pipeline) | claude-code-sourcemap (permission model) |
| httpx mock seam pattern | PublicDataReader (data.go.kr wire format) | stamina/aiobreaker (retry/circuit breaker) |

## Complexity Tracking

No constitution violations to justify. All design decisions align with existing patterns.
