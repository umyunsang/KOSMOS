# Tasks: Phase 1 Final Validation & Stabilization (Live)

**Input**: Design documents from `/specs/014-phase1-live-validation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Live tests ARE the primary deliverable of this epic — all test file tasks are implementation tasks, not optional.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the live test infrastructure that all user stories depend on

- [ ] T001 Create root test conftest with live marker skip logic in tests/conftest.py
- [ ] T002 [P] Create tests/live/ package directory with tests/live/__init__.py
- [ ] T003 [P] Create shared live test fixtures and credential validation in tests/live/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix cross-layer defects and wiring gaps that MUST be resolved before ANY live test can succeed

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Fix environment variable naming in .env.example (KOSMOS_DATA_GO_KR_KEY → KOSMOS_DATA_GO_KR_API_KEY) and add base URL documentation comment
- [ ] T005 [P] Wire PermissionPipeline into QueryEngine.__init__ and QueryContext creation in src/kosmos/engine/engine.py

**Checkpoint**: Foundation ready — live tests can now be written and executed

---

## Phase 3: User Story 1 — Live API Test Suite Execution (Priority: P1) 🎯 MVP

**Goal**: Validate all Phase 1 adapters and the LLM client against real external APIs with `@pytest.mark.live` tests

**Independent Test**: Run `uv run pytest -m live -v --tb=long` with valid API credentials. All live tests pass; failures indicate real API integration issues, not test infrastructure problems.

### Implementation for User Story 1

- [ ] T006 [P] [US1] Implement KOROAD adapter live validation tests in tests/live/test_live_koroad.py
- [ ] T007 [P] [US1] Implement KMA weather alert and current observation live validation tests in tests/live/test_live_kma.py
- [ ] T008 [P] [US1] Implement FriendliAI LLM client live validation tests (SSE streaming, tool call parsing) in tests/live/test_live_llm.py
- [ ] T009 [P] [US1] Implement composite road_risk_score live validation tests in tests/live/test_live_composite.py
- [ ] T010 [US1] Verify all live tests pass via `uv run pytest -m live -v --tb=long` and all mock tests remain green via `uv run pytest -v`

**Checkpoint**: All individual adapter and LLM client live tests pass. Each adapter confirmed working against real APIs.

---

## Phase 4: User Story 2 — End-to-End CLI Scenario 1 Conversation (Priority: P1)

**Goal**: Validate the full Scenario 1 pipeline structure via automated live E2E test and document manual CLI validation steps

**Independent Test**: Run `uv run pytest tests/live/test_live_e2e.py -m live -v`. The test validates event sequence (tool_use → tool_result → text_delta → stop) without asserting on LLM-generated text content.

### Implementation for User Story 2

- [ ] T011 [US2] Implement full Scenario 1 pipeline structural live E2E test in tests/live/test_live_e2e.py
- [ ] T012 [US2] Verify E2E live test passes and validate multi-turn context retention in the pipeline event sequence

**Checkpoint**: Full pipeline from QueryEngine through ToolExecutor to adapters validated with real APIs. Event sequence structurally correct.

---

## Phase 5: User Story 3 — Cross-Layer Defect Discovery and Remediation (Priority: P2)

**Goal**: Discover and fix defects that only manifest against live APIs — SSE boundary issues, XML-in-JSON errors, schema drift, encoding problems

**Independent Test**: After all fixes, run `uv run pytest -v --tb=long` (full suite: mock + live). Zero failures across both test categories.

### Implementation for User Story 3

- [ ] T013 [US3] Run full live test suite, capture and document all failures with root cause analysis
- [ ] T014 [US3] Fix discovered live-only defects in adapter and client source code (exact files determined by T013 findings)
- [ ] T015 [US3] Verify full test suite (mock + live) passes with zero failures after all fixes

**Checkpoint**: All cross-layer defects discovered during live testing are fixed. Both mock and live test suites pass.

---

## Phase 6: User Story 4 — API Response Fixture Synchronization (Priority: P2)

**Goal**: Compare live API responses against existing test fixtures, update drifted fixtures, and ensure mock tests remain representative

**Independent Test**: After fixture updates, run `uv run pytest -v` (mock-based tests only). All mock tests pass with updated fixtures that match live response structures.

### Implementation for User Story 4

- [ ] T016 [P] [US4] Capture live KMA weather alert response and create fixture in tests/fixtures/kma/weather_alert_status.json
- [ ] T017 [P] [US4] Capture live KMA current observation response and create fixture in tests/fixtures/kma/current_observation.json
- [ ] T018 [US4] Compare live KOROAD response against existing fixture in tests/fixtures/koroad/koroad_accident_search.json, update if drifted
- [ ] T019 [US4] Verify all mock-based tests pass with updated fixtures via `uv run pytest -v`

**Checkpoint**: All fixtures synchronized with live API responses. Mock tests remain green with updated fixtures.

---

## Phase 7: User Story 5 — Stateful Component Live Behavior Verification (Priority: P3)

**Goal**: Verify RateLimiter, CircuitBreaker, and UsageTracker behave correctly under real API call patterns with actual network latency

**Independent Test**: Extend live tests to exercise stateful components. Run `uv run pytest -m live -v` and verify rate limiter activates at threshold, CircuitBreaker transitions observed, UsageTracker records real token counts.

### Implementation for User Story 5

- [ ] T020 [US5] Add stateful component verification assertions to existing live tests (rate limiter activation, CircuitBreaker state transitions, UsageTracker token counts) in tests/live/test_live_composite.py and tests/live/test_live_e2e.py
- [ ] T021 [US5] Verify stateful component assertions pass under real API conditions via `uv run pytest -m live -v`

**Checkpoint**: Stateful components verified under real network conditions. Rate limiter, CircuitBreaker, and UsageTracker confirmed working with real API timing.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories and documentation updates

- [ ] T022 Run complete test suite (mock + live) via `uv run pytest -v --tb=long` and verify SC-06 (zero failures)
- [ ] T023 Run type checking via `uv run mypy src/kosmos` and linting via `uv run ruff check src/ tests/` — fix any regressions
- [ ] T024 [P] Run quickstart.md validation — execute all commands from specs/014-phase1-live-validation/quickstart.md and verify accuracy
- [ ] T025 Document manual CLI Scenario 1 session results (SC-02 manual component) in PR description

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — no dependencies on other stories
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — can run in parallel with US1
- **US3 (Phase 5)**: Depends on US1 + US2 completion (defects discovered from live test runs)
- **US4 (Phase 6)**: Depends on US1 completion (needs live API responses to compare against fixtures)
- **US5 (Phase 7)**: Depends on US1 completion (extends existing live tests with stateful assertions)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent — can start immediately after Phase 2
- **US2 (P1)**: Independent — can start immediately after Phase 2 (parallel with US1)
- **US3 (P2)**: Depends on US1 + US2 (needs live test results to discover defects)
- **US4 (P2)**: Depends on US1 (needs live response data for fixture comparison)
- **US5 (P3)**: Depends on US1 (extends live test files created in US1)

### Within Each User Story

- Adapter tests (T006-T009) can run in parallel — they write to different files
- E2E test (T011) depends on all adapter tests passing conceptually but writes to a separate file
- Fixture tasks (T016-T017) can run in parallel — they capture different API responses
- Defect remediation (T013-T015) is sequential by nature — discover → fix → verify

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel (different files)
- **Phase 2**: T004 and T005 can run in parallel (different files)
- **Phase 3**: T006, T007, T008, T009 can ALL run in parallel (4 different test files)
- **Phase 3+4**: US1 and US2 can run in parallel after Phase 2
- **Phase 6**: T016 and T017 can run in parallel (different fixture files)

---

## Parallel Example: User Story 1

```bash
# Launch all adapter live tests together (all write to different files):
Task: "Implement KOROAD adapter live tests in tests/live/test_live_koroad.py"
Task: "Implement KMA adapter live tests in tests/live/test_live_kma.py"
Task: "Implement LLM client live tests in tests/live/test_live_llm.py"
Task: "Implement composite tool live tests in tests/live/test_live_composite.py"
```

## Parallel Example: Setup + Foundational

```bash
# Phase 1 parallel tasks:
Task: "Create tests/live/ package in tests/live/__init__.py"
Task: "Create shared live fixtures in tests/live/conftest.py"

# Phase 2 parallel tasks:
Task: "Fix .env.example naming in .env.example"
Task: "Wire PermissionPipeline in src/kosmos/engine/engine.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T005)
3. Complete Phase 3: US1 — Live adapter tests (T006-T010)
4. Complete Phase 4: US2 — E2E pipeline test (T011-T012)
5. **STOP and VALIDATE**: `uv run pytest -m live -v` — all live tests pass
6. This delivers SC-01 and SC-02 (automated part)

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. US1 (adapter tests) → SC-01 satisfied (MVP!)
3. US2 (E2E test) → SC-02 automated part satisfied
4. US3 (defect fixes) → SC-04 satisfied
5. US4 (fixture sync) → SC-05 satisfied
6. US5 (stateful verification) → Refinement
7. Polish → SC-06, SC-07 verified

### Agent Team Strategy

With parallel Teammates (Sonnet):

1. Lead completes Setup + Foundational (sequential, small)
2. Once Phase 2 done:
   - Teammate A: T006 (KOROAD live tests)
   - Teammate B: T007 (KMA live tests)
   - Teammate C: T008 (LLM live tests)
   - Teammate D: T009 (composite live tests) + T011 (E2E test)
3. Lead reviews, runs verification (T010, T012)
4. Teammates handle US3-US5 based on discovered defects

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Live tests are NOT optional in this epic — they ARE the primary deliverable
- Tests must hard-fail on API unavailability (no `pytest.skip()` on network errors)
- E2E test asserts on event structure only (tool_use, tool_result, text_delta, stop), never on LLM content
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
