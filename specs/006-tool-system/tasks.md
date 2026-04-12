# Tasks: Tool System & Registry (Layer 2)

**Input**: Design documents from `specs/006-tool-system/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure

- [ ] T001 Create `src/kosmos/tools/` package directory with `__init__.py` and create `tests/tools/` package directory with `__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error hierarchy and shared test infrastructure that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T002 [P] Implement error hierarchy (`KosmosToolError`, `DuplicateToolError`, `ToolNotFoundError`, `ToolValidationError`, `RateLimitExceededError`, `ToolExecutionError`) in `src/kosmos/tools/errors.py`
- [ ] T003 [P] Create test infrastructure with shared fixtures (mock Pydantic input/output schemas, sample `GovAPITool` factory, mock tool adapter function) in `tests/tools/conftest.py`

**Checkpoint**: Foundation ready — error types and test fixtures are importable

---

## Phase 3: User Story 1 — Tool Registration with Fail-Closed Defaults (Priority: P1) MVP

**Goal**: Define GovAPITool model with fail-closed defaults and register tools in ToolRegistry

**Independent Test**: Register a tool with only required fields, verify all defaults are fail-closed. Register with explicit overrides, verify overrides respected. Reject duplicate registrations.

### Implementation for User Story 1

- [ ] T004 [P] [US1] Implement `GovAPITool` Pydantic v2 model with all fields (id, name_ko, provider, category, endpoint, auth_type, input_schema, output_schema, search_hint) and fail-closed defaults (requires_auth=True, is_personal_data=True, is_concurrency_safe=False, cache_ttl_seconds=0, rate_limit_per_minute=10, is_core=False) including id pattern validation (`^[a-z][a-z0-9_]*$`), non-empty category, and `to_openai_tool()` method in `src/kosmos/tools/models.py`
- [ ] T005 [P] [US1] Implement `ToolResult`, `ToolSearchResult`, and `SearchToolMatch` Pydantic v2 models in `src/kosmos/tools/models.py` — ToolResult with success/data/error/error_type fields, ToolSearchResult with tool/score/matched_tokens
- [ ] T006 [US1] Implement `ToolRegistry` with `register()`, `lookup()`, `all_tools()`, `__len__()`, `__contains__()` methods in `src/kosmos/tools/registry.py` — register raises `DuplicateToolError`, lookup raises `ToolNotFoundError`
- [ ] T007 [P] [US1] Write unit tests for GovAPITool validation (fail-closed defaults, id pattern rejection, non-empty category, explicit overrides, to_openai_tool format) in `tests/tools/test_models.py`
- [ ] T008 [P] [US1] Write unit tests for ToolRegistry registration and lookup (register success, duplicate rejection, lookup success, not-found error, __len__, __contains__) in `tests/tools/test_registry.py`

**Checkpoint**: Tool registration works with fail-closed defaults. `uv run pytest tests/tools/` passes.

---

## Phase 4: User Story 2 — Lazy Tool Discovery via search_tools (Priority: P1)

**Goal**: Search tools by Korean and English keywords in search_hint with token-overlap scoring

**Independent Test**: Register multiple tools with varied search_hints, query with Korean keywords, verify relevant tools returned. Query with English keywords, verify same. Query with empty string, verify empty results.

### Implementation for User Story 2

- [ ] T009 [US2] Implement bilingual search logic with token-overlap scoring (case-insensitive substring matching, query tokenization, score computation, ranking) in `src/kosmos/tools/search.py`
- [ ] T010 [US2] Add `search()` method to `ToolRegistry` that delegates to search logic, accepts `query: str` and `max_results: int = 5`, returns `list[ToolSearchResult]` in `src/kosmos/tools/registry.py`
- [ ] T011 [P] [US2] Implement `SearchToolsInput` and `SearchToolsOutput` Pydantic v2 models, and `create_search_meta_tool()` factory function that creates a `GovAPITool` for `search_tools` in `src/kosmos/tools/search.py`
- [ ] T012 [P] [US2] Write unit tests for bilingual search (Korean keyword match, English keyword match, mixed query, empty query returns empty, max_results limit, score ranking, no-match returns empty) in `tests/tools/test_search.py`

**Checkpoint**: Tool search works for Korean and English queries. Relevant tools are ranked correctly.

---

## Phase 5: User Story 3 — Prompt Cache Partitioning (Priority: P2)

**Goal**: Separate core tools (always loaded) from situational tools (on-demand), export core tools deterministically

**Independent Test**: Register tools with is_core=True and is_core=False, verify core_tools() returns only core tools sorted by id, verify situational_tools() returns only non-core tools, verify export_core_tools_openai() output is byte-for-byte identical across calls.

### Implementation for User Story 3

- [ ] T013 [US3] Add `core_tools()`, `situational_tools()`, and `export_core_tools_openai()` methods to `ToolRegistry` — core_tools sorted by id for deterministic output, export uses `to_openai_tool()` in `src/kosmos/tools/registry.py`
- [ ] T014 [P] [US3] Write unit tests for prompt cache partitioning (core vs situational partition is disjoint, core_tools sorted by id, export_core_tools_openai deterministic across calls, empty core list, mixed registration order) in `tests/tools/test_registry.py`

**Checkpoint**: Prompt cache partitioning works. Core tool export is deterministic.

---

## Phase 6: User Story 4 — Rate Limit Tracking (Priority: P2)

**Goal**: Track per-tool call frequency with sliding-window rate limiting, reject calls exceeding limits

**Independent Test**: Create a tool with rate_limit_per_minute=5, make 5 calls within one minute, verify 6th is rejected. Wait for window expiry, verify calls are allowed again.

### Implementation for User Story 4

- [ ] T015 [US4] Implement `RateLimiter` with sliding-window algorithm using `collections.deque` — `check()`, `record()`, `remaining` property, `reset()` method in `src/kosmos/tools/rate_limiter.py`
- [ ] T016 [US4] Integrate `RateLimiter` into `ToolRegistry` — auto-create per-tool rate limiter on registration, expose `get_rate_limiter(tool_id: str) -> RateLimiter` method in `src/kosmos/tools/registry.py`
- [ ] T017 [P] [US4] Write unit tests for RateLimiter (check within limit, reject at limit, window expiry reset, remaining count, manual reset, independent per-tool limiters) in `tests/tools/test_rate_limiter.py`

**Checkpoint**: Rate limiting works. Per-tool call counts are tracked independently.

---

## Phase 7: User Story 5 — Tool Execution Dispatch (Priority: P3)

**Goal**: Dispatch tool calls with input/output validation, rate limit checking, and error handling

**Independent Test**: Register a mock tool, dispatch with valid arguments and verify validated response. Dispatch with invalid arguments and verify validation error. Dispatch unknown tool and verify not-found error.

### Implementation for User Story 5

- [ ] T018 [US5] Implement `ToolExecutor` with `dispatch(tool_name, arguments_json) -> ToolResult` pipeline — lookup → validate input → check rate limit → execute adapter → validate output — returns ToolResult with success=False for any failure (never raises) in `src/kosmos/tools/executor.py`
- [ ] T019 [P] [US5] Write unit tests for ToolExecutor dispatch (valid call returns success, invalid input returns validation error, unknown tool returns not-found, rate limit exceeded returns rate_limit error, adapter exception returns execution error, output schema mismatch returns schema_mismatch error) in `tests/tools/test_executor.py`

**Checkpoint**: Tool execution dispatch works. All error paths return ToolResult, never raise.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize public API and validate documentation

- [ ] T020 Finalize public exports in `src/kosmos/tools/__init__.py` — export `GovAPITool`, `ToolRegistry`, `ToolExecutor`, `ToolResult`, `ToolSearchResult`, `RateLimiter`, all error types, `SearchToolsInput`, `SearchToolsOutput`
- [ ] T021 Run `quickstart.md` code examples as validation (verify imports, API surface matches contract)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP delivery target (with US2)
- **US2 (Phase 4)**: Depends on Phase 3 (needs ToolRegistry to add search)
- **US3 (Phase 5)**: Depends on Phase 3 (needs ToolRegistry to add partitioning)
- **US4 (Phase 6)**: Depends on Phase 3 (needs ToolRegistry to integrate rate limiters)
- **US5 (Phase 7)**: Depends on Phase 3 + Phase 6 (needs registry + rate limiters for dispatch)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no story dependencies
- **US2 (P1)**: Depends on US1 (extends ToolRegistry with search)
- **US3 (P2)**: Depends on US1 (extends ToolRegistry with partitioning) — parallel-safe with US2
- **US4 (P2)**: Depends on US1 (integrates rate limiters into registry) — parallel-safe with US2/US3
- **US5 (P3)**: Depends on US1 + US4 (needs full registry with rate limiters for dispatch)

### Within Each User Story

- Models/infrastructure before registry integration
- Registry integration before tests (tests verify integrated behavior)
- All [P] tasks within a phase can run in parallel

### Parallel Opportunities

- **Phase 2**: T002, T003 — all parallel-safe (different files)
- **Phase 3**: T004, T005 parallel (models.py additions), then T006 (registry.py); T007, T008 parallel (test files)
- **Phase 4+5+6**: US2 search.py, US3 registry.py additions, US4 rate_limiter.py — infrastructure tasks are parallel-safe across stories, but registry.py edits must be serialized

---

## Parallel Example: Foundational Phase

```text
# Launch foundational tasks in parallel (different files):
Agent 1: T002 — errors.py
Agent 2: T003 — conftest.py
```

## Parallel Example: User Story 1 (after Foundational)

```text
# Launch model tasks in parallel (same file but additive):
Agent 1: T004 — models.py (GovAPITool)
Agent 2: T005 — models.py (ToolResult, ToolSearchResult)
# Then: T006 — registry.py (depends on models)
# Then launch test tasks in parallel:
Agent 3: T007 — test_models.py
Agent 4: T008 — test_registry.py
```

## Parallel Example: Cross-Story (after US1 complete)

```text
# US2, US3, US4 infrastructure tasks in parallel:
Agent 1: T009 [US2] — search.py (new file)
Agent 2: T015 [US4] — rate_limiter.py (new file)
# US3 T013 edits registry.py — serialize with T010, T016
# Then serialize registry.py integrations: T010, T013, T016
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T003) — parallel
3. Complete Phase 3: US1 (T004-T008)
4. Complete Phase 4: US2 (T009-T012)
5. **STOP and VALIDATE**: `uv run pytest tests/tools/` passes
6. Tool system is usable for registration and search

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Fail-closed registration works (MVP part 1)
3. Add US2 → Bilingual search works (MVP part 2)
4. Add US3 → Prompt cache partitioning active
5. Add US4 → Rate limiting enforced
6. Add US5 → Tool execution dispatch ready for Query Engine
7. Polish → Production-grade exports and validation

---

## Notes

- Total tasks: 21 (T001-T021)
- Parallel-safe tasks: 9 (marked [P])
- No new dependencies required (pydantic already in pyproject.toml)
- All tests use mock tools — no live API calls
- US2 and US3 are both independent from each other (parallel-safe with different stories)
- US5 depends on US4 (rate limit checking in dispatch pipeline)
- registry.py is the integration point — edits from different stories must be serialized
- models.py has additive tasks (T004, T005) that can be parallelized if working on non-overlapping sections
