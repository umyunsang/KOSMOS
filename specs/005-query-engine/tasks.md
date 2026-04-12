# Tasks: Query Engine Core

**Input**: Design documents from `/specs/005-query-engine/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/query-engine.md, quickstart.md

**Tests**: Included — SC-006 explicitly requires all unit tests to pass with mocked LLM and recorded tool fixtures.

**Organization**: Tasks grouped by user story (US1-US4) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `kosmos.engine` package structure and test scaffolding

- [ ] T001 Create src/kosmos/engine/ package directory and tests/engine/ test directory with __init__.py files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, enums, and config that ALL user stories depend on. No user story work can begin until this phase is complete.

- [ ] T002 [P] Implement QueryEngineConfig with validators in src/kosmos/engine/config.py (fields: max_iterations, max_turns, context_window, preprocessing_threshold, tool_result_budget, snip_turn_age, microcompact_turn_age — all positive-int validated, threshold in (0.0, 1.0])
- [ ] T003 [P] Implement StopReason enum and QueryEvent discriminated union with model validators in src/kosmos/engine/events.py (8 stop reasons, 5 event types with type-specific field enforcement)
- [ ] T004 [P] Implement QueryEngineError hierarchy in src/kosmos/engine/errors.py (base KosmosEngineError, BudgetExhaustedError, MaxIterationsError, QueryCancelledError)
- [ ] T005 [P] Implement QueryState, QueryContext, and SessionBudget models in src/kosmos/engine/models.py (QueryState mutable with messages/turn_count/usage/resolved_tasks; QueryContext frozen Pydantic with arbitrary_types_allowed; SessionBudget frozen read-only view)
- [ ] T006 [P] Implement estimate_tokens() heuristic in src/kosmos/engine/tokens.py (Korean U+AC00-U+D7A3 at 2 chars/token, other at 4 chars/token)
- [ ] T007 Create shared test fixtures in tests/engine/conftest.py (mock LLM client with streaming, mock tool registry with 4 tools, mock tool executor with adapters, sample QueryEngineConfig, sample ChatMessage histories)
- [ ] T008 [P] Unit tests for QueryEngineConfig validation in tests/engine/test_config.py (positive-int enforcement, threshold range, defaults, frozen immutability)
- [ ] T009 [P] Unit tests for StopReason and QueryEvent in tests/engine/test_events.py (all 8 stop reasons, all 5 event types, type-specific field validators, discriminated union serialization)
- [ ] T010 [P] Unit tests for estimate_tokens() in tests/engine/test_tokens.py (pure Korean, pure English, mixed content, empty string, edge cases)

**Checkpoint**: All foundational models tested and passing. User story implementation can begin.

---

## Phase 3: User Story 1 — Single-Turn Query Resolution (Priority: P1) MVP

**Goal**: A citizen submits a natural-language question; the engine processes it through one or more tool calls and returns a consolidated answer via the async generator protocol.

**Independent Test**: Send "서울 강남구 교통사고 현황 알려줘" with mocked LLM and recorded tool fixtures. Engine should cycle through tool selection, execution, response synthesis, then terminate with StopReason.task_complete.

### Implementation for User Story 1

- [ ] T011 [US1] Implement query() async generator core loop in src/kosmos/engine/query.py (preprocess -> immutable snapshot -> LLM stream -> collect response -> check tool_calls -> dispatch tools sequentially -> append results -> yield events -> decide continue/stop; max_iterations guard)
- [ ] T012 [US1] Implement QueryEngine class with run() and properties in src/kosmos/engine/engine.py (constructor with LLM client/registry/executor/config/system_prompt; run() creates QueryContext, appends user message, delegates to query(), increments turn_count; budget and message_count properties; basic observability logging per FR-011: log token usage, cache hit ratio, per-tool call counts via stdlib logging)
- [ ] T013 [US1] Create module exports in src/kosmos/engine/__init__.py (export QueryEngine, QueryEngineConfig, QueryEvent, StopReason, QueryState, QueryContext, SessionBudget)
- [ ] T014 [P] [US1] Unit tests for query() in tests/engine/test_query.py (single tool call loop, no-tool direct answer, two sequential tool calls, unknown tool error injection, max_iterations termination, usage_update event emission, cancellation via async generator break cancels in-flight work per FR-010)
- [ ] T015 [P] [US1] Integration tests for single-turn scenarios in tests/engine/test_engine.py (US1 acceptance scenarios 1-3: one tool call -> task_complete, two sequential tool calls -> task_complete, no tool call -> end_turn; event ordering guarantee; no-raise contract verification)

**Checkpoint**: Single-turn query resolution fully functional. `uv run pytest tests/engine/ -v` passes.

---

## Phase 4: User Story 2 — Multi-Turn Conversation (Priority: P2)

**Goal**: The engine maintains conversation history across turns, applying compression when needed to manage the 128K context window.

**Independent Test**: Send 5+ sequential queries in the same session, verify context accumulation and preprocessing pipeline activation when approaching token limits.

### Implementation for User Story 2

- [ ] T016 [US2] Implement PreprocessingPipeline with 4 stage functions in src/kosmos/engine/preprocessing.py (tool_result_budget: truncate oversized results; snip: remove stale tool results older than N turns; microcompact: strip whitespace and compact JSON for old messages; collapse: merge consecutive same-role messages; pipeline.run() applies stages sequentially without mutating original list)
- [ ] T017 [US2] Integrate preprocessing pipeline into query() loop in src/kosmos/engine/query.py (call pipeline.run() before creating immutable snapshot each iteration; pass config thresholds)
- [ ] T018 [P] [US2] Unit tests for each preprocessing stage in tests/engine/test_preprocessing.py (tool_result_budget truncation with token estimation; snip removes old synthesized results; microcompact strips whitespace/JSON; collapse merges consecutive same-role; pipeline.run() sequential application; original list not mutated)
- [ ] T019 [US2] Multi-turn integration tests in tests/engine/test_engine.py (US2 acceptance scenarios: 3-turn history accumulation, immutable snapshot verification, preprocessing triggers near context limit, turn_count tracking across turns, 20-turn coherence stress test per SC-002, 50-turn preprocessing window test per SC-005)

**Checkpoint**: Multi-turn conversations work with history management. All US1 + US2 tests pass.

---

## Phase 5: User Story 3 — Budget Enforcement and Graceful Termination (Priority: P3)

**Goal**: The engine enforces session-level cost and turn budgets, terminating gracefully with clear StopReason when limits are exceeded.

**Independent Test**: Configure a 2-turn budget, verify engine stops at turn 3 with StopReason.api_budget_exceeded and a user-friendly message.

### Implementation for User Story 3

- [ ] T020 [US3] Add turn budget check and token budget check at the start of QueryEngine.run() in src/kosmos/engine/engine.py (check turn_count < max_turns before processing; check usage.can_afford() before LLM call in query(); yield stop with api_budget_exceeded and remaining budget info as stop_message; integrate SessionBudget into usage_update events)
- [ ] T021 [US3] Budget enforcement tests in tests/engine/test_engine_budget.py (US3 acceptance scenarios: turn limit reached, token budget exceeded via UsageTracker, graceful stop_message content, SessionBudget property accuracy, error_unrecoverable with guidance message for hard failures)

**Checkpoint**: Budget enforcement works across all dimensions. All US1 + US2 + US3 tests pass.

---

## Phase 6: User Story 4 — Concurrent Tool Execution (Priority: P3)

**Goal**: When the LLM requests multiple independent tool calls, execute them concurrently to reduce citizen wait time (SC-004: 30%+ latency reduction).

**Independent Test**: Mock LLM response requesting 2 concurrent-safe tools with 0.5s artificial delay each; verify total time is ~0.5s (not ~1.0s).

### Implementation for User Story 4

- [ ] T022 [US4] Implement dispatch_tool_calls() with partition-sort algorithm in src/kosmos/engine/query.py (lookup is_concurrency_safe per tool; group consecutive safe tools; execute safe groups via asyncio.TaskGroup; serialize non-safe tools; preserve result ordering; replace sequential dispatch in query() loop)
- [ ] T023 [US4] Concurrent dispatch tests in tests/engine/test_engine_concurrent.py (US4 acceptance scenarios: two concurrent-safe tools execute in parallel with timing assertion; one fails + one succeeds both results injected; non-safe tool forces sequential; mixed safe/non-safe partition-sort correctness; result ordering preserved)

**Checkpoint**: Concurrent tool dispatch operational. All US1-US4 tests pass. SC-004 latency target met.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all user stories

- [ ] T024 [P] Add module-level docstrings and SPDX headers to all src/kosmos/engine/*.py files
- [ ] T025 Run mypy strict type checking across src/kosmos/engine/ and fix any type errors
- [ ] T026 Run ruff linting and formatting across src/kosmos/engine/ and tests/engine/
- [ ] T027 Run full test suite with coverage: `uv run pytest tests/engine/ --cov=kosmos.engine --cov-fail-under=80` and verify all quickstart.md scenarios pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP target
- **US2 (Phase 4)**: Depends on Phase 2 + T011 (query.py must exist for preprocessing integration)
- **US3 (Phase 5)**: Depends on Phase 2 + T012 (engine.py must exist for budget checks)
- **US4 (Phase 6)**: Depends on Phase 2 + T011 (query.py must exist for dispatch replacement)
- **Polish (Phase 7)**: Depends on all user stories

### User Story Dependencies

- **US1 (P1)**: Blocked by Phase 2 only. No dependencies on other stories.
- **US2 (P2)**: Blocked by Phase 2 + US1 (T011 query.py). Creates preprocessing.py (new file) + modifies query.py.
- **US3 (P3)**: Blocked by Phase 2 + US1 (T012 engine.py). Modifies engine.py only.
- **US4 (P3)**: Blocked by Phase 2 + US1 (T011 query.py). Modifies query.py only.

**Note**: US3 and US4 are independent of each other (different files: engine.py vs query.py) and can run in parallel after US1 completes.

### Within Each User Story

- Implementation before tests (tests depend on the code they test)
- Core module before integration module (query.py before engine.py)
- Tests marked [P] within a story can run in parallel

### Parallel Opportunities

- **Phase 2**: T002-T006 (all [P] — 5 different source files); T008-T010 (all [P] — 3 different test files)
- **Phase 3**: T014 + T015 (both [P] — different test files)
- **Phase 5 + Phase 6**: US3 and US4 can run in parallel (US3 modifies engine.py, US4 modifies query.py — no file conflicts)
- **Phase 7**: T024-T026 (all [P] — independent quality checks)

---

## Parallel Example: Foundational Phase

```bash
# Launch all model files in parallel (5 different source files):
Task: "Implement QueryEngineConfig in src/kosmos/engine/config.py"        # T002
Task: "Implement StopReason + QueryEvent in src/kosmos/engine/events.py"  # T003
Task: "Implement error hierarchy in src/kosmos/engine/errors.py"          # T004
Task: "Implement QueryState/QueryContext/SessionBudget in models.py"      # T005
Task: "Implement estimate_tokens() in src/kosmos/engine/tokens.py"        # T006

# Then fixtures (depends on models):
Task: "Create shared test fixtures in tests/engine/conftest.py"           # T007

# Then tests in parallel (3 different test files):
Task: "Unit tests for config in tests/engine/test_config.py"             # T008
Task: "Unit tests for events in tests/engine/test_events.py"             # T009
Task: "Unit tests for tokens in tests/engine/test_tokens.py"             # T010
```

## Parallel Example: US3 + US4 (after US1 complete)

```bash
# These two stories modify different files and can run simultaneously:
# Agent A: US3 — Budget Enforcement (modifies engine.py)
Task: "Add budget enforcement to QueryEngine in engine.py"               # T020
Task: "Budget enforcement tests in test_engine_budget.py"                # T021

# Agent B: US4 — Concurrent Dispatch (modifies query.py)
Task: "Implement dispatch_tool_calls() in query.py"                      # T022
Task: "Concurrent dispatch tests in test_engine_concurrent.py"           # T023
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (single-turn query resolution)
4. **STOP and VALIDATE**: `uv run pytest tests/engine/ -v` — all tests pass
5. This is a deployable increment: citizens can ask single-turn questions

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Single-turn works → **MVP!**
3. Add US2 → Multi-turn context management → conversations persist
4. Add US3 + US4 (parallel) → Budget + concurrency → production-ready engine
5. Polish → Coverage, types, docs → ship-quality

### Agent Teams Strategy

With 3+ agents available:

1. **All agents** complete Setup + Foundational together (parallel on T002-T006)
2. **Lead agent** handles US1 (core loop is architecturally critical)
3. Once US1 is complete:
   - **Agent A**: US3 (budget enforcement — engine.py)
   - **Agent B**: US4 (concurrent dispatch — query.py)
   - **Agent C**: US2 (preprocessing — preprocessing.py + query.py integration)
   
   Note: US2 and US4 both touch query.py, so schedule US4 before US2's T017, or have US2 agent rebase after US4 completes.
4. **All agents** handle Polish phase

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after completion
- All tests use mocked LLM and recorded fixtures — no live API calls (SC-006)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Total: 27 tasks across 7 phases
