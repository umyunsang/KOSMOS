# Tasks: Scenario 1 E2E — Route Safety

**Input**: Design documents from `specs/012-scenario1-e2e-route-safety/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create E2E test directory structure and package files

- [X] T001 Create tests/e2e/ directory and tests/e2e/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the E2EFixtureBuilder and shared test infrastructure that ALL user stories depend on

**CRITICAL**: No user story tests can be written until this phase is complete

- [X] T002 Implement E2EFixtureBuilder in tests/e2e/conftest.py — builder pattern that assembles a fully-wired QueryEngine with MockLLMClient, real ToolRegistry (with all Phase 1 tools registered via register_all), real ToolExecutor with RecoveryExecutor, real ContextBuilder, and optional PermissionPipeline. Include methods: with_llm_responses(), with_api_fixture(), with_api_failure(), with_permission_pipeline(), with_budget(), build().
- [X] T003 Implement httpx mock fixture in tests/e2e/conftest.py — a pytest fixture that patches httpx.AsyncClient.get to route requests based on URL pattern matching ("/getOldRoadTrficAccidentDeath" → koroad, "/getWthrWrnList" → kma_alert, "/getUltraSrtNcst" → kma_obs). Load JSON fixtures from existing tests/tools/*/fixtures/ directories. Support configurable failure injection per adapter.
- [X] T004 Implement MockLLMClient response sequences for route safety in tests/e2e/conftest.py — create StreamEvent sequences for: (a) tool_call_delta requesting road_risk_score with RoadRiskScoreInput args, (b) content_delta with Korean route safety recommendation text, (c) usage events with deterministic token counts. Provide both 2-iteration happy-path and degraded-path variants.
- [X] T005 Implement assertion helper functions in tests/e2e/conftest.py — assert_tool_calls_dispatched(events, expected_tool_ids), assert_final_response_contains(events, keywords), assert_usage_matches(engine, expected_tokens), assert_stop_reason(events, expected_reason), assert_data_gaps(events, expected_gaps).

**Checkpoint**: Foundation ready — all E2E test infrastructure is in place, user story tests can begin

---

## Phase 3: User Story 1 — Happy-Path Route Safety Query (Priority: P1)

**Goal**: Prove the entire Phase 1 pipeline works end-to-end: citizen query → tool dispatch → multi-API fusion → Korean safety response

**Independent Test**: Run `uv run pytest tests/e2e/test_route_safety_happy.py -v` — all tests pass with recorded fixtures and mock LLM

- [X] T006 [US1] Implement happy-path E2E test in tests/e2e/test_route_safety_happy.py — test that a citizen query "내일 부산에서 서울 가는데, 안전한 경로 추천해줘" dispatches road_risk_score tool, receives fused results from 3 APIs, and produces a Korean text response containing route safety information.
- [X] T007 [US1] Implement conversation history verification test in tests/e2e/test_route_safety_happy.py — verify that after the E2E flow, the message history contains: system message, user message, assistant message with tool_calls, tool result messages, and final assistant text message in correct order.
- [X] T008 [US1] Implement multi-tool fan-out verification test in tests/e2e/test_route_safety_happy.py — verify that the road_risk_score composite adapter actually invoked all 3 inner adapters (koroad_accident_search, kma_weather_alert_status, kma_current_observation) by checking httpx mock call counts.

**Checkpoint**: Happy-path E2E passing — the Phase 1 pipeline is proven end-to-end

---

## Phase 4: User Story 2 — Degraded-Path: Single API Failure (Priority: P2)

**Goal**: Prove graceful degradation when 1 or 2 government APIs fail

**Independent Test**: Run `uv run pytest tests/e2e/test_route_safety_degraded.py -v`

- [X] T009 [P] [US2] Implement KOROAD failure degraded test in tests/e2e/test_route_safety_degraded.py — configure httpx mock to return HTTP 500 for koroad, verify composite result has data_gaps for accident data and still returns weather-based safety info.
- [X] T010 [P] [US2] Implement KMA alert failure degraded test in tests/e2e/test_route_safety_degraded.py — configure httpx mock to raise httpx.TimeoutException for kma_weather_alert_status, verify composite result has data_gaps for alert data.
- [X] T011 [US2] Implement all-adapters-failure test in tests/e2e/test_route_safety_degraded.py — configure all 3 inner adapters to fail, verify ToolExecutionError is raised and engine produces a graceful error message with stop_reason=error_unrecoverable.
- [X] T012 [US2] Implement circuit breaker integration test in tests/e2e/test_route_safety_degraded.py — verify that when a circuit breaker is open for an API, the RecoveryExecutor returns a cached or error result without attempting the call.

**Checkpoint**: Degraded-path E2E passing — citizens get useful responses even when APIs fail

---

## Phase 5: User Story 3 — Cost Accounting Verification (Priority: P3)

**Goal**: Prove that token usage and API call counts are accurately tracked

**Independent Test**: Run `uv run pytest tests/e2e/test_route_safety_budget.py -v`

- [X] T013 [P] [US3] Implement token usage tracking test in tests/e2e/test_route_safety_budget.py — run happy-path E2E flow with known mock token counts, assert UsageTracker total_input_tokens and total_output_tokens match the sum of all StreamEvent usage values exactly.
- [X] T014 [P] [US3] Implement budget exceeded test in tests/e2e/test_route_safety_budget.py — configure MockLLMClient with a token budget of 1, run E2E flow, verify BudgetExceededError yields stop event with api_budget_exceeded reason.
- [X] T015 [US3] Implement rate limiter call count test in tests/e2e/test_route_safety_budget.py — after happy-path E2E flow, verify rate limiter recorded exactly the expected number of calls per API adapter.

**Checkpoint**: Cost accounting E2E passing — every token and API call is tracked

---

## Phase 6: User Story 4 — Permission Pipeline Integration (Priority: P3)

**Goal**: Prove that tool calls pass through the 7-step permission gauntlet and audit entries are recorded

**Independent Test**: Run `uv run pytest tests/e2e/test_route_safety_permission.py -v`

- [X] T016 [US4] Implement permission pipeline E2E test in tests/e2e/test_route_safety_permission.py — configure E2EFixtureBuilder with a PermissionPipeline and public-auth SessionContext, run happy-path E2E flow, verify audit step recorded entries for each tool invocation.
- [X] T017 [US4] Implement permission denial test in tests/e2e/test_route_safety_permission.py — configure a SessionContext that lacks required auth for a requires_auth=True tool, verify the permission pipeline denies the call and the engine includes a denial message.

**Checkpoint**: Permission audit E2E passing — compliance verification complete

---

## Phase 7: Edge Cases

**Purpose**: Cover boundary conditions and error handling across the pipeline

- [X] T018 [P] Implement unknown tool handling test in tests/e2e/test_route_safety_edge.py — mock LLM requests a non-existent tool, verify ToolNotFoundError is captured in ToolResult and engine continues to produce a response.
- [X] T019 [P] Implement max iterations guard test in tests/e2e/test_route_safety_edge.py — mock LLM always returns tool calls, verify engine stops after max_iterations with appropriate stop reason.
- [X] T020 [P] Implement stream interruption retry test in tests/e2e/test_route_safety_edge.py — mock LLM raises StreamInterruptedError on first call then succeeds on retry, verify engine recovers and produces a response.
- [X] T021 [P] Implement invalid tool arguments test in tests/e2e/test_route_safety_edge.py — mock LLM provides arguments that fail Pydantic validation, verify ToolResult captures ValidationError with success=False.
- [X] T022 Implement preprocessing pipeline test in tests/e2e/test_route_safety_edge.py — configure a very small context_window so preprocessing triggers, verify messages are compressed and query still completes.

**Checkpoint**: All edge cases covered — pipeline is resilient to unexpected inputs

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T023 Run full E2E test suite with `uv run pytest tests/e2e/ -v` and verify all tests pass
- [X] T024 Verify zero live API calls — assert no unpatched httpx requests escape during test runs
- [X] T025 Verify test suite completes in under 10 seconds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 only
- **Foundational (Phase 2)**: Depends on Phase 1 — T002-T005 BLOCK all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3): Can start immediately after Phase 2
  - US2 (Phase 4): Can start immediately after Phase 2 (parallel with US1)
  - US3 (Phase 5): Can start immediately after Phase 2 (parallel with US1/US2)
  - US4 (Phase 6): Can start immediately after Phase 2 (parallel with US1/US2/US3)
- **Edge Cases (Phase 7)**: Can start after Phase 2 (parallel with user stories)
- **Polish (Phase 8)**: Depends on ALL phases completing

### User Story Independence

- **US1 (Happy-Path)**: Fully independent — core pipeline proof
- **US2 (Degraded-Path)**: Independent — uses same fixtures with failure injection
- **US3 (Cost Accounting)**: Independent — asserts on UsageTracker state
- **US4 (Permission Audit)**: Independent — adds PermissionPipeline to builder

### Within Phase 2 (Foundational)

```
T002 (E2EFixtureBuilder) ← T003 (httpx mock) and T004 (LLM responses) depend on T002
T005 (assertion helpers) — independent, can parallel with T003/T004
```

### Parallel Opportunities

After Phase 2 completes, **ALL user stories and edge cases can run in parallel**:

```
Phase 2 complete
  ├── [Agent A] Phase 3: US1 (T006, T007, T008)
  ├── [Agent B] Phase 4: US2 (T009, T010, T011, T012)
  ├── [Agent C] Phase 5: US3 (T013, T014, T015) + Phase 6: US4 (T016, T017)
  └── [Agent D] Phase 7: Edge Cases (T018-T022)
```

---

## Parallel Example: Post-Foundational

```bash
# After Phase 2 is complete, launch 4 agents in parallel:
Agent A: "Implement tests/e2e/test_route_safety_happy.py (T006-T008)"
Agent B: "Implement tests/e2e/test_route_safety_degraded.py (T009-T012)"
Agent C: "Implement tests/e2e/test_route_safety_budget.py and test_route_safety_permission.py (T013-T017)"
Agent D: "Implement tests/e2e/test_route_safety_edge.py (T018-T022)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T005)
3. Complete Phase 3: US1 Happy-Path (T006-T008)
4. **STOP and VALIDATE**: Run `uv run pytest tests/e2e/test_route_safety_happy.py -v`
5. If passing → Phase 1 pipeline is proven end-to-end

### Incremental Delivery

1. Setup + Foundational → test infrastructure ready
2. Add US1 (Happy-Path) → pipeline proven → MVP!
3. Add US2 (Degraded-Path) → resilience proven
4. Add US3 + US4 (Cost + Permission) → accountability proven
5. Add Edge Cases → robustness proven
6. Polish → ship-ready

---

## Notes

- All tasks produce test code only — no new production source files
- Existing JSON fixtures from tests/tools/*/fixtures/ are reused — no new fixture recording needed
- MockLLMClient pattern from tests/engine/conftest.py is reused
- [P] tasks = different files, no dependencies
- Commit after each phase or logical group
- Total: 25 tasks across 8 phases
