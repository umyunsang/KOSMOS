---
description: "Task list for Scenario 1 E2E — Route Safety (Re-baseline)"
---

# Tasks: Scenario 1 E2E — Route Safety (Re-baseline)

**Input**: Design documents from `/specs/030-scenario1-route-safety-rebase/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUESTED and are the primary deliverable of this spec — this feature IS a test suite. Every user story phase therefore produces test files, not production code. Production edits are scoped to the two FR-017/018 instrumentation tasks and the chore-level FR-017 wording tidy.

**Organization**: Tasks are grouped by user story (US1–US4, matching spec.md §User Scenarios) to enable independent implementation and testing. The runner layer reuses the existing `QueryEngine.run()` — no new builder is authored (research.md §RQ-1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact, absolute-safe repo-relative file paths in descriptions

## Path Conventions

Single-project layout per plan.md §Project Structure. Repo root = `/Users/um-yunsang/KOSMOS-17/`. All test code under `tests/e2e/` and `tests/fixtures/{kakao,koroad,kma}/`. Production edits limited to `src/kosmos/tools/executor.py` and `src/kosmos/tools/lookup.py`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment knobs, fixture directories, and the `RunReport` data-model module that every user-story phase depends on.

- [ ] T001 [P] Create `tests/fixtures/kakao/` directory with `.gitkeep` so the Kakao geocoding tapes have a canonical home (plan.md §Project Structure; quickstart.md §5).
- [ ] T002 [P] Author `tests/e2e/models.py` containing the Pydantic v2 **frozen** `RunReport`, `ObservabilitySnapshot`, `CapturedSpan`, `ScenarioTurn`, and `ScenarioScript` models per `data-model.md §2.1–§2.5`; include `schema_version: Literal["030-runreport-v1"]` and invariants I1–I9 via `@model_validator(mode="after")`.
- [ ] T003 [P] Author `tests/e2e/run_report_io.py` with a single helper `dump_run_report(report: RunReport, dump_dir: Path) -> Path | None` that writes `030-<scenario_id>-<unix_ms>.json` when `dump_dir` is set, returning `None` otherwise; MUST reject non-writable directories with the exit-code-3 semantics (contracts/scenario-runner-cli.md §2). JSON serialization via `RunReport.model_dump_json()` only — no bespoke encoders.

**Checkpoint**: Setup artifacts in place; no user-story tasks touch these files after Phase 1.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Production instrumentation and the scenario `conftest.py` that every user-story test file imports. User-story phases CANNOT begin until this phase is complete (RQ-6; research.md §Carry-forward note 3).

**⚠️ CRITICAL**: T004, T005, and T006 all touch production span emission. They MUST land before T011 (US1 happy path) or any span-assertion test (US4) so assertions pass on a clean run.

- [ ] T004 Edit `src/kosmos/tools/executor.py` to set `span.set_attribute("kosmos.tool.outcome", "ok" | "error")` exactly once in the `finally` block of the `execute_tool` span, derived from `_final_result.success` — no new span, no new dependency (plan.md §Production edits #1; FR-017; research.md §RQ-6).
- [ ] T005 Edit `src/kosmos/tools/lookup.py` to, on the `LookupInput.mode == "fetch"` branch only, call `trace.get_current_span().set_attribute("kosmos.tool.adapter", input.tool_id)` before adapter dispatch; `mode="search"` MUST NOT emit this attribute (plan.md §Production edits #2; FR-018).
- [ ] T006 [P] Chore wording tidy in `/Users/um-yunsang/KOSMOS-17/specs/030-scenario1-route-safety-rebase/spec.md` §FR-017: replace `"gen_ai.tool.execute" span` wording with `"execute_tool" span (gen_ai.operation.name = "execute_tool")` per RQ-5 alignment decision, cross-linking `src/kosmos/observability/semconv.py` as the single source of truth. No code change.
- [ ] T007 Author `tests/e2e/conftest.py` (REPLACE the spec-012 builder-based file): expose an `autouse`, session-scoped fixture that `monkeypatch.setenv`s `KOSMOS_DATA_GO_KR_API_KEY="test-dummy"` and `KOSMOS_KAKAO_REST_KEY="test-dummy"` (research.md §RQ-7; FR-011/FR-012); register both facade tools and both adapters via `ToolRegistry.register()` so V1–V6 backstop runs (FR-010); provide a `scenario_runner(script: ScenarioScript) -> RunReport` fixture that wires `QueryEngine.run()`, `InMemorySpanExporter`, and the HTTP mock (no new builder class).
- [ ] T008 [P] Extend `tests/e2e/conftest.py` with the `httpx.AsyncClient.get` seam: a `unittest.mock.AsyncMock`-based side_effect function that URL-pattern-matches each request to the correct tape under `tests/fixtures/{kakao,koroad,kma}/`; unmatched URLs MUST raise to fail-close (research.md §RQ-1; FR-004). Verify **no** `respx` or `vcrpy` import.
- [ ] T009 [P] Extend `tests/e2e/conftest.py` with the `OTelSpanCaptureFixture` helper: installs `opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter` at fixture setup, tears down at teardown; exposes a typed `ObservabilitySnapshot` (per `data-model.md §2.3`) to tests. Respect `OTEL_SDK_DISABLED="true"` by populating `sdk_disabled=True` and returning an empty `spans` tuple (FR-020).
- [ ] T010 [P] Extend `tests/e2e/conftest.py` with `MockLLMClient` script-loader helpers (reusing the existing stub from `tests/engine/conftest.py`): one builder per `scenario_id` literal from the `ScenarioScript` enum — `happy`, `degraded_kma_retry`, `degraded_koroad_no_retry`, `both_down`, `quirk_2023_gangwon`, `quirk_2023_jeonbuk`, `quirk_2022_control`. Each builder returns a `ScenarioScript` with the exact scripted `StreamEvent` sequence (FR-003).

**Checkpoint**: Foundation ready — user story implementation can now proceed. All four user stories can be worked on in parallel because they land on distinct test files.

---

## Phase 3: User Story 1 — Happy-Path Route Safety Query (Priority: P1) 🎯 MVP

**Goal**: Prove the full 6-turn `resolve → search → fetch → fetch → synthesize` pipeline runs green against recorded fixtures and produces a `RunReport` matching the frozen contract.

**Independent Test**: `uv run pytest tests/e2e/test_route_safety_happy.py -v` passes in < 5 s with zero network I/O and returns `stop_reason="end_turn"`, `fetched_adapter_ids=("koroad_accident_hazard_search","kma_forecast_fetch")`, and a Korean `final_response` containing ≥ 1 hazard spot + ≥ 1 weather field (spec.md §User Story 1 Acceptance; SC-1, SC-6).

### Tests for User Story 1 (primary deliverable)

- [ ] T011 [US1] Author `tests/e2e/test_route_safety_happy.py` (REPLACE existing spec-012 body) driving the `happy` `ScenarioScript` through `scenario_runner`; assert `RunReport.tool_call_order == ("resolve_location","resolve_location","lookup","lookup","lookup","lookup")`, `RunReport.stop_reason == "end_turn"`, `RunReport.usage_totals` equals the mock script sums (FR-015, 0% tolerance), `adapter_rate_limit_hits == {"koroad_accident_hazard_search":1,"kma_forecast_fetch":1}` (FR-016), and `RunReport.final_response` contains ≥ 1 string from the KOROAD fixture's `location_name` set AND ≥ 1 KMA semantic field token (FR-023; SC-1).

### Fixture wiring for User Story 1

- [ ] T012 [P] [US1] Record/author the Kakao geocoding tape pair under `tests/fixtures/kakao/`: `local_search_address_강남구.json` and `local_search_address_서울역.json`, each containing the canonical Kakao Local API response with `coords=(37.518, 127.047)` and `coords=(37.554, 126.970)` respectively and the corresponding `adm_cd` values from spec.md §Overview.
- [ ] T013 [P] [US1] Record/author the KOROAD happy-path tape at `tests/fixtures/koroad/accident_hazard_siDo=11_guGun=680_year=2023.json` containing a `LookupCollection`-conformant payload with ≥ 2 hazard items (each with a non-empty `location_name`) so the FR-023 string-presence assertion has a canonical match.
- [ ] T014 [P] [US1] Record/author the KMA happy-path tape at `tests/fixtures/kma/forecast_lat=37.518_lon=127.047_base=20260419_0500.json` containing a `LookupTimeseries`-conformant payload with ≥ 3 points, using semantic field names (`temperature_c`, `precipitation_mm`, `humidity_pct`, `wind_ms`, `pop_pct`) per FR-006.
- [ ] T015 [US1] Wire the three new tapes into the URL-pattern → file mapping table in `tests/e2e/conftest.py` (extends T008); include a `meta`-block assertion helper (FR-007 — `source`, `fetched_at`, `request_id`, `elapsed_ms`) reused by US2 and US3.

**Checkpoint**: User Story 1 green in isolation — demonstrates the MVP acceptance bar for Phase 1 / KSC 2026.

---

## Phase 4: User Story 2 — Degraded-Path: Single Adapter Failure (Priority: P2)

**Goal**: Prove the engine degrades gracefully when one adapter returns `LookupError(retryable=True)` (one-shot retry) or `retryable=False` (no retry, partial synthesis), and terminates with `stop_reason=error_unrecoverable` when both adapters fail.

**Independent Test**: `uv run pytest tests/e2e/test_route_safety_degraded.py -v` passes three parametrised cases covering FR-021 and FR-022 without raising unhandled exceptions to the CLI layer (SC-3, SC-4).

### Tests for User Story 2

- [ ] T016 [US2] Author `tests/e2e/test_route_safety_degraded.py` (REPLACE) as a `pytest.mark.parametrize` over the three scripts `degraded_kma_retry`, `degraded_koroad_no_retry`, `both_down`; assert: (a) KMA-down-retryable case produces exactly one retry then includes KMA data in the final response (FR-021), (b) KOROAD-down-no-retry case produces a partial Korean response referencing KMA data plus an explicit data-gap note (FR-022; SC-3), (c) both-down case yields `stop_reason="error_unrecoverable"` with a graceful Korean error message and zero unhandled exceptions (FR-022; SC-4).

### Fixture wiring for User Story 2

- [ ] T017 [P] [US2] Author `tests/fixtures/koroad/accident_hazard_ERROR_upstream_down.json` and `tests/fixtures/kma/forecast_ERROR_upstream_down.json`: each encodes a `LookupError` envelope with `reason="upstream_down"`, `retryable=True|False` variants selectable by the mock URL matcher (FR-008).
- [ ] T018 [US2] Extend the URL matcher in `tests/e2e/conftest.py` with a per-scenario error-injection table so `degraded_kma_retry` returns the retryable error on first call and the happy tape on second call; `degraded_koroad_no_retry` returns a non-retryable error once; `both_down` returns non-retryable errors for both adapters.

**Checkpoint**: Degraded path green; combined with US1 this demonstrates the pipeline is robust to upstream failure.

---

## Phase 5: User Story 3 — KOROAD Year-Code Quirk Path (Priority: P2)

**Goal**: Prove the adapter's year-aware sido/gugun code mapping (강원 42→51, 전북 45→52 from 2023) is exercised end-to-end through a fixture whose recorded URL contains the post-shift code.

**Independent Test**: `uv run pytest tests/e2e/test_route_safety_quirk.py -v` passes three parametrised cases (`quirk_2023_gangwon`, `quirk_2023_jeonbuk`, `quirk_2022_control`) with non-empty `LookupCollection` assertions for each (FR-013, FR-014; SC-5).

### Tests for User Story 3

- [ ] T019 [US3] Author `tests/e2e/test_route_safety_quirk.py` (NEW) as a `pytest.mark.parametrize` over the three quirk scripts; assert for 2023 cases that the outbound URL captured by the `httpx` mock contains `siDo=51` (강원) or `siDo=52` (전북) — NOT the legacy `42`/`45`; assert the 2022 control case keeps `siDo=42`; all three must return a non-empty `LookupCollection.items` from the matched tape (fixture mismatch surfaces as empty — intentional failure signal per spec.md §User Story 3 Independent Test).

### Fixture wiring for User Story 3

- [ ] T020 [P] [US3] Record/author `tests/fixtures/koroad/accident_hazard_siDo=51_guGun=<chuncheon>_year=2023.json` (강원도 춘천시 post-shift) with ≥ 1 hazard item.
- [ ] T021 [P] [US3] Record/author `tests/fixtures/koroad/accident_hazard_siDo=52_guGun=<jeonju>_year=2023.json` (전북 전주 post-shift) with ≥ 1 hazard item.
- [ ] T022 [P] [US3] Record/author `tests/fixtures/koroad/accident_hazard_siDo=42_guGun=<chuncheon>_year=2022.json` (강원도 pre-shift control) with ≥ 1 hazard item; confirms the adapter does NOT substitute for `year < 2023`.
- [ ] T023 [US3] Extend the URL matcher so the recorded `siDo` in the URL is the authoritative lookup key — a mismatch yields no fixture, which the test interprets as a quirk-table regression (research.md §Carry-forward note 2).

**Checkpoint**: Quirk path green; data-correctness invariant protected at the scenario level, not only at unit level.

---

## Phase 6: User Story 4 — Observability Span Assertions (Priority: P3)

**Goal**: Prove every tool call emits exactly one `execute_tool` span with `gen_ai.operation.name="execute_tool"`, `kosmos.tool.outcome ∈ {"ok","error"}`, `kosmos.tool.adapter` on fetch spans only, no Korean citizen query in any attribute, and graceful skip when `OTEL_SDK_DISABLED=true`.

**Independent Test**: `uv run pytest tests/e2e/test_route_safety_spans.py -v` passes all FR-017/018/019 assertions against the in-memory exporter, and `OTEL_SDK_DISABLED=true uv run pytest tests/e2e/test_route_safety_spans.py` reports SKIPPED (not FAILED) per FR-020 (quickstart.md §4; SC-7).

### Tests for User Story 4

- [ ] T024 [US4] Author `tests/e2e/test_route_safety_spans.py` (NEW) wired to the `happy` script via `scenario_runner`; assert: (a) every span in `RunReport.observability.spans` satisfies I4 (outcome-error ⇒ status ERROR + error_type present); (b) `fetched_adapter_ids` length equals the count of spans with `adapter_id is not None` (I7; FR-017/018 cross-check); (c) no span `attribute_keys` value equals the citizen trigger query or any `resolve_location` `query=` argument (I6; FR-019); (d) spans for `mode="search"` and `resolve_location` have `adapter_id is None` (I5; FR-018 gate). Apply `@pytest.mark.skipif(os.getenv("OTEL_SDK_DISABLED") == "true", reason="FR-020 graceful skip")`.
- [ ] T025 [US4] Add a focused negative test in the same file asserting that a span for a `lookup(mode="fetch")` call that fails with `LookupError` carries `kosmos.tool.outcome="error"`, `status_code="ERROR"`, and `error_type` names the error class — drive it via the `degraded_kma_retry` script's first (failing) call and assert on that specific captured span.

**Checkpoint**: Observability story green; FR-017/018/019/020 closed end-to-end; remaining work from spec 021 (FR-017/018 wiring) is satisfied by T004 + T005.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, documentation alignment, and the deferred-item placeholder issues. No new production code.

- [ ] T026 [P] Author `tests/e2e/test_route_safety_edge.py` (UPDATE the spec-012 edge cases to the two-tool facade) as a `pytest.mark.parametrize` over the seven cases in spec.md §Edge Cases: unregistered `tool_id`, max-iterations guard, Pydantic validation failure, budget exceeded mid-turn, `ResolveError(not_found)` retry, KMA `base_time` validation error, `ResolveError(ambiguous)` disambiguation loop. Each case asserts the loop does not raise and the `stop_reason` matches the documented expectation.
- [ ] T027 [P] Validate `specs/030-scenario1-route-safety-rebase/quickstart.md` commands manually by running `uv run pytest tests/e2e/ -k route_safety -v` and `KOSMOS_E2E_DUMP_DIR=$(pwd)/.run-reports uv run pytest tests/e2e/test_route_safety_happy.py -v` from the repo root; confirm green and that the dumped JSON validates against `contracts/eval-output.schema.json` using the snippet in quickstart §3.
- [ ] T028 [P] Run `uv run pytest tests/e2e/ -k route_safety --durations=10` and confirm the full suite completes in < 5 s wall-clock (SC-8). Record the measured duration in the PR description.
- [ ] T029 [P] Confirm V1–V6 security invariants (FR-009/010; SC-9) by asserting `ToolRegistry.register()` raises on a deliberately misconfigured adapter — add a one-off negative unit test at `tests/e2e/test_route_safety_security_invariants.py` that registers a broken clone of `koroad_accident_hazard_search` (e.g., `auth_type="public"` with `auth_level="AAL2"`) and expects `ValidationError`.
- [ ] T030 Open three DEFERred-item placeholder issues via `/speckit-taskstoissues` (triggered after `tasks.md` is approved): one under the Context Assembly v2 epic (multi-turn follow-up E2E), one under the observability/eval epic (DeepEval harness), one under the Context Assembly / cache epic (prompt-cache instrumentation). Each issue body links back to `specs/030-scenario1-route-safety-rebase/research.md` RQ-2, RQ-3, RQ-4 respectively.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 (needs `RunReport` from T002, `dump_run_report` from T003). **BLOCKS** all user stories.
- **Phase 3–6 (User Stories)**: All depend on Phase 2. US1, US2, US3, US4 can then proceed in parallel.
- **Phase 7 (Polish)**: Depends on all user stories.

### Within-Phase Ordering

- Phase 2: T004 + T005 (production edits) MUST complete before T024/T025 (span assertions) can pass. T006 (chore wording) is independent and [P]. T007 precedes T008/T009/T010 because it establishes the `conftest.py` module that the three extensions add to.
- Phase 3: T012/T013/T014 (fixture tapes) are [P] among themselves; T015 (URL mapping) depends on all three; T011 (test body) depends on T015.
- Phase 4: T017 is [P]; T018 depends on T017; T016 depends on T018.
- Phase 5: T020/T021/T022 are [P] among themselves; T023 depends on all three; T019 depends on T023.
- Phase 6: T024 and T025 both depend on T009 (span capture fixture) from Phase 2.

### Parallel Opportunities

- **Phase 1**: T001, T002, T003 all [P] — three different files.
- **Phase 2**: T006 [P] independent chore; T008, T009, T010 [P] after T007 lands (they extend the same `conftest.py` but target distinct, non-overlapping sections — merge conflict risk is low and reviewable). T004 and T005 target different files and are therefore parallelisable but kept sequential here to keep the FR-017/018 story auditable as a single reviewable diff.
- **Phase 3**: T012, T013, T014 [P] — three different fixture files.
- **Phase 4**: T017 [P] — single file, independent of US1 fixtures.
- **Phase 5**: T020, T021, T022 [P] — three different fixture files.
- **Phase 6**: No [P] within — both tasks target the same test file.
- **Phase 7**: T026, T027, T028, T029 all [P] — distinct files / distinct validations. T030 is sequential (requires the other four green before opening placeholders).
- **User stories**: US1, US2, US3, US4 can all proceed in parallel once Phase 2 is green — staffed via Agent Teams at `/speckit-implement` (AGENTS.md §Agent Teams; 3+ independent tasks).

---

## Parallel Example: Phase 2 fan-out after T007

```bash
# Once T007 has landed the conftest skeleton:
Task: "Extend tests/e2e/conftest.py with the httpx.AsyncClient.get AsyncMock seam (T008)"
Task: "Extend tests/e2e/conftest.py with the InMemorySpanExporter helper (T009)"
Task: "Extend tests/e2e/conftest.py with MockLLMClient script builders (T010)"
Task: "Chore: align spec.md FR-017 wording with execute_tool span (T006)"
```

## Parallel Example: Fixture authoring across US1 + US3

```bash
# Any time after Phase 2:
Task: "Record Kakao tape for 강남구 (T012)"
Task: "Record KOROAD siDo=11 2023 happy tape (T013)"
Task: "Record KMA 단기예보 happy tape (T014)"
Task: "Record KOROAD siDo=51 강원 2023 quirk tape (T020)"
Task: "Record KOROAD siDo=52 전북 2023 quirk tape (T021)"
Task: "Record KOROAD siDo=42 강원 2022 control tape (T022)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (T001–T003) → Phase 2 (T004–T010) → Phase 3 (T011–T015).
2. **STOP and VALIDATE**: run the happy-path test in isolation; confirm Korean synthesis matches FR-023 and span assertions are not yet in scope.
3. Proceed to US4 next (span story) because T004/T005 production edits are already in place — span assertions are the highest-value follow-up.

### Incremental Delivery

1. Setup + Foundational → Foundation ready (MVP demo-gate).
2. US1 green → KSC 2026 demo-path proof (FR-001, FR-005/006/007, FR-023).
3. US4 green → spec 021 FR-017/018 end-to-end closure.
4. US2 green → SC-3/SC-4 robustness proof.
5. US3 green → SC-5 data-correctness proof.
6. Phase 7 polish → suite-wide budget and deferred-item tracking.

### Parallel Team Strategy (Agent Teams at `/speckit-implement`)

Once Phase 2 is green, the four user stories are independent. Recommended allocation:

- Teammate A (Sonnet): US1 (happy) + US3 (quirk) — both are fixture-tape heavy, same KOROAD domain knowledge.
- Teammate B (Sonnet): US2 (degraded) — error-variant fixtures + parametrised assertions.
- Teammate C (Sonnet): US4 (spans) — isolated to the observability assertion file.
- Lead (Opus): code review each teammate's diff against spec.md FR-* and research.md RQ-*.

---

## Notes

- **Tests ARE the feature** in spec 030 — there is no separate implementation phase. The two production edits (T004, T005) are instrumentation in service of a pre-existing spec 021 contract, not a new feature.
- **No new runtime dependencies** — AGENTS.md hard rule. `rank_bm25`, `kiwipiepy`, `httpx`, `pydantic`, `opentelemetry-*` are all already present.
- **Fixtures only** — no `@pytest.mark.live` variants under this spec; live recording happens outside CI (quickstart.md §5).
- **`schema_version="030-runreport-v1"`** is frozen — bumping requires a spec amendment (contracts/eval-output.schema.json).
- **No hardcoding** — the mock LLM script is the only place where adapter IDs appear as string literals; neither retrieval nor synthesis pipelines reference adapter IDs (MEMORY.md `feedback_no_hardcoding`).
- **Deferred items** (multi-turn, DeepEval, prompt-cache) are captured in T030 as placeholder issues only — no code in this spec.
- Verify all assertions fail first (red-green-refactor) before landing the production edits for US4.
