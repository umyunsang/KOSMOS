---

description: "Task list for Phase 1 Live Validation Coverage Extension — Post #291 Modules"
---

# Tasks: Phase 1 Live Validation Coverage Extension — Post #291 Modules

**Input**: Design documents from `/specs/018-phase1-live-extension/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓
**Epic**: #380

**Tests**: This is a **test-only** epic. Every "implementation" task writes a live test. No production source is modified.

**Organization**: Tasks are grouped by user story (spec.md US1/US2/US3) to enable independent story-by-story verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / different test functions, no shared writes)
- **[Story]**: `[US1]`, `[US2]`, `[US3]` map to spec.md user stories
- All paths are repo-relative

## Path Conventions

- Repo root: `/Users/um-yunsang/KOSMOS/`
- Live tests: `tests/live/`
- No new source files anywhere under `src/`

---

## Phase 1: Setup (Shared Test Infrastructure)

**Purpose**: Create new test module files with live/asyncio markers and required imports. No test bodies yet — stubs only.

- [ ] T001 [P] Create new test module `tests/live/test_live_geocoding.py` with SPDX header, module docstring noting Kakao Local API prerequisite (console: 제품 설정 → 카카오맵 → 상태 ON), and `pytest` + `pytest_asyncio` imports. File ends with no test functions yet.
- [ ] T002 [P] Create new test module `tests/live/test_live_observability.py` with SPDX header, module docstring noting required env vars (`KOSMOS_FRIENDLI_TOKEN`, `KOSMOS_DATA_GO_KR_API_KEY`), and pytest imports. File ends with no test functions yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend `tests/live/conftest.py` with the Kakao fixtures per `contracts/fixtures.md`. **Blocks US1 and US3** (both consume `kakao_api_key`). Does NOT block US2.

**⚠️ CRITICAL**: T003 and T004 must land before any US1/US3 test can be written or run.

- [ ] T003 Add `kakao_api_key` session-scoped fixture to `tests/live/conftest.py`. Reads `KOSMOS_KAKAO_API_KEY`; on unset/whitespace-only, calls `pytest.fail("set KOSMOS_KAKAO_API_KEY to run live geocoding tests")` — exact string per FR-004/contracts/fixtures.md. No silent skip, no xfail, no formatting variation.
- [ ] T004 Add `kakao_rate_limit_delay` function-scoped async fixture to `tests/live/conftest.py`. Yields an awaitable callable (or async helper) that sleeps a private module-level constant default of 200 ms. NOT autouse. Must not interfere with the existing autouse `_live_rate_limit_pause` cooldown.

**Checkpoint**: Foundation ready — US1, US2, US3 implementation can begin (US2 has no dependency on T003/T004).

---

## Phase 3: User Story 1 — Live Geocoding Safety Net (Priority: P1) 🎯 MVP

**Goal**: Seven live tests in `tests/live/test_live_geocoding.py` that exercise the Kakao Local API through the three geocoding adapters (`search_address`, `address_to_grid`, `address_to_region`) and verify structural contracts per `data-model.md § Validation Rules — Geocoding (Story 1)` and `contracts/test-interfaces.md § test_live_geocoding.py`.

**Independent Test**: `uv run pytest -m live -v tests/live/test_live_geocoding.py` — all 7 pass with valid `KOSMOS_KAKAO_API_KEY` and Kakao Local API activated. Verifies SC-001.

- [ ] T005 [P] [US1] Implement `test_live_kakao_search_address_happy` in `tests/live/test_live_geocoding.py`. Calls real `search_address("서울특별시 강남구 테헤란로 152")`. Asserts `len(documents) >= 1`, each of `{"address_name","x","y"}` present, `float(x) ∈ [124.0, 132.0]` and `float(y) ∈ [33.0, 39.0]`. Decorators: `@pytest.mark.live`, `@pytest.mark.asyncio`. Consumes `kakao_api_key`, `kakao_rate_limit_delay`.
- [ ] T006 [P] [US1] Implement `test_live_kakao_search_address_nonsense` in `tests/live/test_live_geocoding.py`. Calls `search_address` with a nonsense string (e.g., `"zzzxxx999notarealplace"`). Asserts `documents == []` and no exception raised. Decorators: `@pytest.mark.live`, `@pytest.mark.asyncio`.
- [ ] T007 [P] [US1] Implement `test_live_address_to_grid_seoul_landmark` in `tests/live/test_live_geocoding.py`. Calls `address_to_grid` for a Seoul landmark address. Asserts `nx ∈ [57, 63]` and `ny ∈ [124, 130]` (center 60/127 ±3). Decorators + fixtures as above.
- [ ] T008 [P] [US1] Implement `test_live_address_to_grid_busan_landmark` in `tests/live/test_live_geocoding.py`. Calls `address_to_grid` for a Busan landmark address. Asserts `nx ∈ [95, 100]` and `ny ∈ [73, 78]`. Decorators + fixtures as above.
- [ ] T009 [P] [US1] Implement `test_live_address_to_region_gangnam` in `tests/live/test_live_geocoding.py`. Calls `address_to_region` for a Gangnam address. Asserts `sido == "SEOUL"` and `gugun == "SEOUL_GANGNAM"`. Decorators + fixtures as above.
- [ ] T010 [P] [US1] Implement `test_live_address_to_region_busan` in `tests/live/test_live_geocoding.py`. Calls `address_to_region` for a Busan address. Asserts `sido == "BUSAN"`. Decorators + fixtures as above.
- [ ] T011 [P] [US1] Implement `test_live_address_to_region_unmapped_region` in `tests/live/test_live_geocoding.py`. Calls `address_to_region("울릉도")` (or another documented unmapped area). Asserts tool returns a structured `ToolResult` whose output signals unmapped status per adapter's fail-closed contract; **no exception raised**. Decorators + fixtures as above.

**Checkpoint**: US1 complete — all 7 geocoding live tests green against live Kakao. SC-001 satisfied.

---

## Phase 4: User Story 2 — Live Observability Pipeline Verification (Priority: P1)

**Goal**: Four live tests in `tests/live/test_live_observability.py` that wire a real `MetricsCollector` + `ObservabilityEventLogger` through real KOROAD and FriendliAI traffic and assert counter deltas and event-schema presence per `data-model.md § Validation Rules — Observability (Story 2)` and `contracts/test-interfaces.md § test_live_observability.py`.

**Independent Test**: `uv run pytest -m live -v tests/live/test_live_observability.py` — all 4 pass with valid FriendliAI and KOROAD credentials. No dependency on US1 or US3. Verifies SC-002.

- [ ] T012 [P] [US2] Implement `test_live_metrics_collector_under_live_tool_call` in `tests/live/test_live_observability.py`. Instantiate fresh `MetricsCollector`, wire into tool executor, snapshot counters pre-call, run real KOROAD accident search, snapshot post-call. Assert `tool.calls.total` delta == 1 and `tool.latency_ms` has ≥1 new sample > 0. Consumes `koroad_api_key`. Decorators: `@pytest.mark.live`, `@pytest.mark.asyncio`.
- [ ] T013 [P] [US2] Implement `test_live_metrics_collector_under_live_llm_stream` in `tests/live/test_live_observability.py`. Instantiate fresh `MetricsCollector`, wire into `LLMClient`, snapshot pre-call, run real FriendliAI K-EXAONE streaming completion, snapshot post-call. Assert `llm.requests.total` delta ≥ 1; `llm.tokens.prompt` and `llm.tokens.completion` each have ≥1 new sample > 0. Consumes `friendli_token`. Decorators as above.
- [ ] T014 [P] [US2] Implement `test_live_event_logger_emits_tool_events` in `tests/live/test_live_observability.py`. Instantiate fresh `ObservabilityEventLogger`, wire into tool executor, snapshot event log pre-call, run real KOROAD call, snapshot post-call. Assert ≥1 `tool.call.started` and ≥1 `tool.call.completed` events captured, each with non-empty `tool_id`, numeric non-negative `latency_ms`, populated `outcome`. Consumes `koroad_api_key`. Decorators as above.
- [ ] T015 [P] [US2] Implement `test_live_event_logger_emits_llm_events` in `tests/live/test_live_observability.py`. Instantiate fresh `ObservabilityEventLogger`, wire into `LLMClient`, run real LLM streaming request, snapshot events. Assert ≥1 `llm.stream.started` and ≥1 `llm.stream.completed` events captured with valid schemas. Consumes `friendli_token`. Decorators as above.

**Checkpoint**: US2 complete — metrics and event logger wiring verified under real traffic. SC-002 satisfied.

---

## Phase 5: User Story 3 — End-to-End Natural-Address Scenario 1 (Priority: P2)

**Goal**: One new test appended to existing `tests/live/test_live_e2e.py` verifying the full LLM → geocoding → KOROAD → response chain from a natural Korean prompt, per `data-model.md § Validation Rules — E2E Natural-Address (Story 3)` and `contracts/test-interfaces.md § test_live_e2e.py`.

**Independent Test**: `uv run pytest -m live -v tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address` — passes with all credentials set. Verifies SC-003.

**Preconditions**: US1 passing (confirms geocoding layer live-green), US2 passing (confirms observability wiring). US3 is the composite checkpoint; per spec P2 reasoning it runs last.

- [ ] T016 [US3] Append `test_live_scenario1_from_natural_address` to `tests/live/test_live_e2e.py`. Build a `QueryEngine` with real LLM client, real tool registry (including geocoding + KOROAD adapters), and a real `ObservabilityEventLogger` wired in. Drive `engine.run()` with user message `"강남역 근처 사고 정보 알려줘"`. Collect recorded tool-call sequence, final response text, and observability event log. Assertions: (1) sequence contains ≥1 geocoding call and exactly 1 `koroad_accident_search` call; (2) first geocoding-call index < first KOROAD-call index; (3) `len(final_response.strip()) > 0`; (4) final response contains ≥1 Hangul char (Unicode `\uac00-\ud7af`); (5) event log contains ≥1 LLM stream pair, ≥1 geocoding tool pair, ≥1 KOROAD tool pair. Consumes `kakao_api_key`, `koroad_api_key`, `friendli_token`, `kakao_rate_limit_delay`. Decorators: `@pytest.mark.live`, `@pytest.mark.asyncio`.

**Checkpoint**: US3 complete — full Scenario 1 chain verified from a natural Korean prompt. SC-003 satisfied.

---

## Phase 6: Polish & Cross-Cutting Validation

**Purpose**: Verify the acceptance criteria that span all stories (SC-004 hard-fail, SC-005 CI safety, SC-006 rate-limit envelope) and run the full extended live suite.

- [ ] T017 [P] Verify SC-004 (hard-fail contract). Run `unset KOSMOS_KAKAO_API_KEY && uv run pytest -m live -v tests/live/test_live_geocoding.py 2>&1 | grep -F "set KOSMOS_KAKAO_API_KEY to run live geocoding tests"`. Expect: exact string in failure output; exit code non-zero; no `SKIPPED` or `XFAIL` lines for geocoding tests. Document the command output in the PR body.
- [ ] T018 [P] Verify SC-005 (CI safety). Run `uv run pytest` (no `-m live`) in a clean checkout and confirm runtime matches pre-PR baseline; run `uv run pytest tests/live/ -v` and confirm all 12 new live tests report `SKIPPED` (not collected-and-run). No new CI minutes required.
- [ ] T019 Verify SC-006 (rate-limit envelope). Run `uv run pytest -m live -v tests/live/test_live_geocoding.py` and measure real Kakao call count (≤~15 per full run under the 200 ms delay). Confirm KOROAD call count in `test_live_observability.py` stays ≤2 per run. Document in PR body.
- [ ] T020 Run the full extended live suite end-to-end: `uv run pytest -m live -v tests/live/test_live_geocoding.py tests/live/test_live_observability.py tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address`. All 12 tests green. Capture log for PR body.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup T001, T002)**: no dependencies; [P]-parallel
- **Phase 2 (Foundational T003, T004)**: depends on Phase 1; blocks US1 and US3 (not US2)
- **Phase 3 (US1 T005–T011)**: depends on Phase 2 (T003, T004)
- **Phase 4 (US2 T012–T015)**: depends on Phase 1 (T002) only; independent of T003/T004 and of US1
- **Phase 5 (US3 T016)**: depends on US1 and US2 green per spec P2 reasoning
- **Phase 6 (Polish T017–T020)**: depends on US1, US2, US3 complete

### Story Dependencies

- **US1 (P1)**: needs T003 + T004; independent of US2 and US3
- **US2 (P1)**: independent of US1 and US3; no Kakao dependency
- **US3 (P2)**: composite — spec marks it P2 explicitly because it combines US1 + US2; runs after both

### Within Each Story

- US1: all 7 test functions are independent (different functions, same file but different line ranges). Mark all [P].
- US2: all 4 test functions are independent. Mark all [P].
- US3: single test — no parallelism.

### Parallel Opportunities

- T001 ∥ T002 (Phase 1).
- After Phase 2 done: T005–T011 can all run in parallel (US1), T012–T015 can all run in parallel (US2). US2 actually can begin in parallel with T003/T004 since US2 does not need Kakao fixtures.
- T017, T018 parallel (both read-only verification).
- T019 and T020 are non-parallel: both issue live API calls and should serialize to keep rate-limit accounting clean.

---

## Parallel Example: Agent Teams at `/speckit-implement`

With 2-3 Sonnet Teammates available after Phase 2 lands:

```bash
# Teammate A: US1 geocoding tests (after T003, T004 merged)
Task: "T005–T011: implement 7 geocoding live tests in tests/live/test_live_geocoding.py"

# Teammate B: US2 observability tests (can start even before T003/T004 — only needs T002)
Task: "T012–T015: implement 4 observability live tests in tests/live/test_live_observability.py"

# Lead (Opus): US3 E2E natural-address + Phase 6 validation (after A and B green)
Task: "T016: append test_live_scenario1_from_natural_address to tests/live/test_live_e2e.py"
Task: "T017–T020: run SC-004/005/006 verification and full live suite"
```

---

## Implementation Strategy

### MVP First (US1 only) — delivers SC-001

1. Phase 1 (T001, T002)
2. Phase 2 (T003, T004)
3. Phase 3 (T005–T011)
4. **STOP and VALIDATE**: `uv run pytest -m live -v tests/live/test_live_geocoding.py` → all 7 green
5. Ship MVP PR at this point if time-constrained; US2/US3 can follow in a second PR against the same Epic #380.

### Recommended (full epic in one PR)

1. Phase 1 + Phase 2 in one commit
2. US1 + US2 in parallel (two commits), US2 does not wait on T003/T004
3. US3 after US1 + US2 green
4. Phase 6 validation as the final commit
5. Single PR `Closes #380` with all four checkpoints (SC-001/002/003/006) demonstrated in PR body

### Parallel Team Strategy

Preferred path per `AGENTS.md § Agent Teams` — 3 independent task groups (US1, US2, US3) → spawn 3 parallel Teammates after foundational phase lands.

---

## Notes

- **No production source changes** — if any task touches `src/`, it is a constitution violation per plan.md Constitution Check and must be rejected.
- **No mocks** — these tests exist precisely because mocked coverage already exists under `tests/tools/geocoding/` and `tests/observability/`. Adding mock-based assertions to the live suite defeats its purpose (FR-010).
- **No specific-value assertions** — contracts/test-interfaces.md § "Non-assertions" is a hard policy.
- **Exact hard-fail string** — `set KOSMOS_KAKAO_API_KEY to run live geocoding tests` (no period, no prefix). SC-004 greps for this literal.
- **Task ordering for PR commits**: group T001+T002 as `test: scaffold live geocoding+observability modules`, T003+T004 as `test(live): add Kakao fixtures`, T005–T011 as `test(live): geocoding coverage`, T012–T015 as `test(live): observability coverage`, T016 as `test(live): E2E natural-address Scenario 1`, T017–T020 as `test(live): acceptance verification`.
- **Live suite never runs in CI** — FR-007, SC-005. Inherited skip logic from root `tests/conftest.py` (#291).
