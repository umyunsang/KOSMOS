---
description: "Task list for Epic #7: Phase 1 API Adapters (KOROAD, KMA, Road Risk)"
epic: 7
spec: specs/007-api-adapters/spec.md
plan: specs/007-api-adapters/plan.md
data_model: specs/007-api-adapters/data-model.md
created: 2026-04-13
layer: "Layer 2 — Tool System"
---

# Tasks: Phase 1 API Adapters (KOROAD, KMA, Road Risk)

**Epic**: #7
**Input**: `specs/007-api-adapters/spec.md`, `plan.md`, `data-model.md`
**Total tasks**: 44
**Parallel-safe tasks**: 21

---

## Phase 1: Package Structure Setup

**Purpose**: Create all empty package directories and `__init__.py` files so Phase 2+ tasks can work
in their target paths without conflict. No logic; no dependencies.

- [ ] T001 [P] Create `src/kosmos/tools/koroad/__init__.py` (empty package marker)
- [ ] T002 [P] Create `src/kosmos/tools/kma/__init__.py` (empty package marker)
- [ ] T003 [P] Create `src/kosmos/tools/composite/__init__.py` (empty package marker)
- [ ] T004 [P] Create `tests/tools/koroad/__init__.py` (empty package marker)
- [ ] T005 [P] Create `tests/tools/kma/__init__.py` (empty package marker)
- [ ] T006 [P] Create `tests/tools/composite/__init__.py` (empty package marker)
- [ ] T007 [P] Create `tests/fixtures/koroad/` directory with `.gitkeep`
- [ ] T008 [P] Create `tests/fixtures/kma/` directory with `.gitkeep`

**Checkpoint**: All package directories exist. All Phase 2 tasks can begin.

---

## Phase 2: Foundational Infrastructure (Blocking)

**Purpose**: Shared code that ALL adapter tasks in Phase 3+ require. Must be complete before any
adapter can be written. These are serial within this phase due to file-level dependencies, but
the phase itself has no dependency on any other work.

**CRITICAL**: No user story task can begin until T009 through T012 are all complete.

- [ ] T009 Add `ConfigurationError` class and `_require_env()` helper to `src/kosmos/tools/errors.py`
- [ ] T010 Implement `SidoCode`, `GugunCode`, `SearchYearCd`, `HazardType` enums and `SIDO_GUGUN_MAP` validation dict in `src/kosmos/tools/koroad/code_tables.py` (depends on T001)
- [ ] T011 Implement `REGION_TO_GRID` lookup dict and `lookup_grid()` utility in `src/kosmos/tools/kma/grid_coords.py` with minimum 17 metro city centroids (depends on T002)
- [ ] T012 [P] Write unit tests for `SidoCode`/`GugunCode`/`SearchYearCd` enum members and `SIDO_GUGUN_MAP` correctness in `tests/tools/koroad/test_code_tables.py` (depends on T004, T010)
- [ ] T013 [P] Write unit tests for `lookup_grid()` covering known grid points and unknown region fallback in `tests/tools/kma/test_grid_coords.py` (depends on T005, T011)

**Checkpoint**: Shared infrastructure is complete and tested. US1, US2, US3 can now start in parallel.

---

## Phase 3: US1 — KOROAD Accident Search Adapter

**Goal**: Deliver a fully working `koroad_accident_search` tool that queries `getRestFrequentzoneLg`,
normalizes single-item vs. array responses, and validates input enums against the official code table.

**User Story**: US-001 (spec § US-001), US-006 (spec § US-006)
**Independent Test**: `uv run pytest tests/tools/koroad/test_koroad_accident_search.py`

**Depends on**: T001, T004, T009, T010 (Phase 1 + Phase 2 completion)
**Parallel-safe with**: Phase 3 tasks for US2 and US3 (different subpackages, no shared files)

- [ ] T014 [P] [US1] Implement `AccidentHotspot`, `KoroadAccidentSearchInput` (with cross-validator for legacy sido codes), and `KoroadAccidentSearchOutput` Pydantic v2 models in `src/kosmos/tools/koroad/koroad_accident_search.py`
- [ ] T015 [US1] Implement `_normalize_items()` helper and `_parse_response()` function in `src/kosmos/tools/koroad/koroad_accident_search.py` (depends on T014)
- [ ] T016 [US1] Implement `_call()` async adapter function with httpx client injection, `_require_env("KOSMOS_KOROAD_API_KEY")` key loading, XML fallback guard, and `resultCode != "00"` error mapping in `src/kosmos/tools/koroad/koroad_accident_search.py` (depends on T015)
- [ ] T017 [US1] Declare `KOROAD_ACCIDENT_SEARCH_TOOL` as a `GovAPITool` instance and implement `register(registry, executor)` helper in `src/kosmos/tools/koroad/koroad_accident_search.py` (depends on T016)
- [ ] T018 [P] [US1] Create recorded fixture `tests/fixtures/koroad/koroad_accident_search.json` (realistic synthetic JSON for sido=11, gugun=680 with 3+ hotspot records; no PII)
- [ ] T019 [US1] Write `test_happy_path_from_fixture()`, `test_error_path_bad_input()` (sido=99), `test_missing_api_key()`, and `@pytest.mark.live` test in `tests/tools/koroad/test_koroad_accident_search.py` (depends on T014, T016, T018)
- [ ] T020 [US1] Write `test_legacy_sido_cross_validator()`: verify `ValidationError` is raised for sido=42 + 2023+ year code, and sido=51 passes cleanly in `tests/tools/koroad/test_koroad_accident_search.py` (depends on T014, T019)
- [ ] T021 [US1] Write `test_single_item_normalization()`: verify `_normalize_items()` handles both dict (single result) and list (multiple results) shapes in `tests/tools/koroad/test_koroad_accident_search.py` (depends on T015, T019)

**Checkpoint**: `koroad_accident_search` fully implemented and tested. US-001 and US-006 acceptance scenarios covered.

---

## Phase 4: US2 — KMA Weather Alert Status Adapter

**Goal**: Deliver a working `kma_weather_alert_status` tool that queries `getPwnStatus`, filters out
cancelled warnings (`cancel=1`), and handles empty-string / null `items` responses gracefully.

**User Story**: US-002 (spec § US-002)
**Independent Test**: `uv run pytest tests/tools/kma/test_kma_weather_alert_status.py`

**Depends on**: T002, T005, T009, T011 (Phase 1 + Phase 2 completion)
**Parallel-safe with**: Phase 3 (US1) and Phase 5 (US3) tasks

- [ ] T022 [P] [US2] Implement `WeatherWarning`, `KmaWeatherAlertStatusInput` (with `numOfRows` defaulting to 2000), and `KmaWeatherAlertStatusOutput` Pydantic v2 models in `src/kosmos/tools/kma/kma_weather_alert_status.py`
- [ ] T023 [US2] Implement `_normalize_items()` helper that treats `items=""`, `items=None`, and `items=[]` all as empty list, and filters `cancel=1` records before building output in `src/kosmos/tools/kma/kma_weather_alert_status.py` (depends on T022)
- [ ] T024 [US2] Implement `_call()` async adapter function with httpx client injection, `_require_env("KOSMOS_DATA_GO_KR_KEY")` key loading, and `resultCode != "00"` error mapping in `src/kosmos/tools/kma/kma_weather_alert_status.py` (depends on T023)
- [ ] T025 [US2] Declare `KMA_WEATHER_ALERT_STATUS_TOOL` as a `GovAPITool` instance and implement `register(registry, executor)` helper in `src/kosmos/tools/kma/kma_weather_alert_status.py` (depends on T024)
- [ ] T026 [P] [US2] Create recorded fixture `tests/fixtures/kma/kma_weather_alert_status.json` (realistic synthetic JSON with 2 active warnings and 1 cancelled warning; no PII)
- [ ] T027 [US2] Write `test_happy_path_from_fixture()`, `test_empty_warnings_no_error()` (items="" response), `test_cancelled_warnings_filtered()`, `test_missing_api_key()`, and `@pytest.mark.live` test in `tests/tools/kma/test_kma_weather_alert_status.py` (depends on T022, T024, T026)

**Checkpoint**: `kma_weather_alert_status` fully implemented and tested. US-002 acceptance scenarios covered.

---

## Phase 5: US3 — KMA Current Observation Adapter

**Goal**: Deliver a working `kma_current_observation` tool that queries `getUltraSrtNcst`, pivots the
row-per-category wire format into a flat model, normalizes `RN1="-"` to `0.0`, and retries with the
previous hour's `base_time` on first-call failure (EC-002).

**User Story**: US-003 (spec § US-003)
**Independent Test**: `uv run pytest tests/tools/kma/test_kma_current_observation.py`

**Depends on**: T002, T005, T009, T011 (Phase 1 + Phase 2 completion)
**Parallel-safe with**: Phase 3 (US1) and Phase 4 (US2) tasks

- [ ] T028 [P] [US3] Implement `KmaCurrentObservationInput` (with `base_time` normalizer stripping minutes to nearest hour) and `KmaCurrentObservationOutput` (with `rn1` field validator normalizing `"-"`, `None`, `""` to `0.0`) Pydantic v2 models in `src/kosmos/tools/kma/kma_current_observation.py`
- [ ] T029 [US3] Implement `_pivot_rows()` helper that converts `[{category, obsrValue}, ...]` list into a flat dict keyed by category in `src/kosmos/tools/kma/kma_current_observation.py` (depends on T028)
- [ ] T030 [US3] Implement `_call()` async adapter function with httpx client injection, `_require_env("KOSMOS_DATA_GO_KR_KEY")` key loading, `resultCode != "00"` error mapping, and one-time retry with previous hour's `base_time` (EC-002) in `src/kosmos/tools/kma/kma_current_observation.py` (depends on T029)
- [ ] T031 [US3] Declare `KMA_CURRENT_OBSERVATION_TOOL` as a `GovAPITool` instance and implement `register(registry, executor)` helper in `src/kosmos/tools/kma/kma_current_observation.py` (depends on T030)
- [ ] T032 [P] [US3] Create recorded fixture `tests/fixtures/kma/kma_current_observation.json` (realistic synthetic JSON for nx=61, ny=125 with 8 category rows including RN1="-"; no PII)
- [ ] T033 [US3] Write `test_happy_path_from_fixture()`, `test_rn1_dash_normalizes_to_zero()`, `test_base_time_rounded_down()`, `test_base_time_retry_on_no_data()` (mock first call returning `resultCode != "00"`, assert second call uses previous hour; covers EC-002), `test_missing_api_key()`, and `@pytest.mark.live` test in `tests/tools/kma/test_kma_current_observation.py` (depends on T028, T030, T032)

**Checkpoint**: `kma_current_observation` fully implemented and tested. US-003 acceptance scenarios covered. All three leaf adapters are ready; Phase 6 (US4) can begin.

---

## Phase 6: US4 — Road Risk Composite Adapter

**Goal**: Deliver the `road_risk_score` composite tool that concurrently calls all three inner adapters
via `asyncio.gather`, applies the scoring algorithm, handles partial failure with `data_gaps`, and
returns a Korean-language `summary` string.

**User Story**: US-004 (spec § US-004)
**Independent Test**: `uv run pytest tests/tools/composite/test_road_risk_score.py`

**Depends on**: T017 (US1 complete), T025 (US2 complete — required by T036 for kma_alert inner call), T031 (US3 complete)
**NOT parallel-safe with Phase 3, 4, or 5** — must wait for all three leaf adapters.

- [ ] T034 [US4] Implement `RoadRiskScoreInput` and `RoadRiskScoreOutput` Pydantic v2 models in `src/kosmos/tools/composite/road_risk_score.py`; `RoadRiskScoreInput` defaults `search_year_cd` to `SearchYearCd.GENERAL_2024` when `None`
- [ ] T035 [US4] Implement `_compute_risk_score()` pure function applying the scoring algorithm (hotspot_count weights 0.5, weather weights 0.5; `min(1.0, base_score)`) and `_risk_level()` classifier (`[0,0.3)=low`, `[0.3,0.6)=moderate`, `[0.6,0.8)=high`, `[0.8,1.0]=severe`) in `src/kosmos/tools/composite/road_risk_score.py` (depends on T034)
- [ ] T036 [US4] Implement `_call()` async composite adapter: import `_call` from all three inner adapters, fan-out with `asyncio.gather(return_exceptions=True)`, handle partial failure producing `data_gaps` list, generate Korean `summary` string, and return total failure as `error_type="execution"` when all inner calls fail in `src/kosmos/tools/composite/road_risk_score.py` (depends on T035)
- [ ] T037 [US4] Declare `ROAD_RISK_SCORE_TOOL` (`requires_auth=False`, `auth_type="public"`, `endpoint=""`, `is_core=True`) as a `GovAPITool` instance and implement `register(registry, executor)` helper in `src/kosmos/tools/composite/road_risk_score.py` (depends on T036)
- [ ] T038 [US4] Write `test_high_risk_scenario()` (5 hotspots + 20 mm precip → risk_level="high"), `test_low_risk_scenario()` (0 hotspots + 0 mm → risk_level="low"), `test_partial_failure_kma_obs()` (KOROAD ok + kma_obs fails → data_gaps=["kma_obs"]), `test_partial_failure_kma_alert()` (KOROAD ok + kma_alert fails → data_gaps=["kma_alert"]), and `test_total_failure()` (all inner adapters fail → error_type="execution") using mocked inner `_call` functions in `tests/tools/composite/test_road_risk_score.py` (depends on T034, T036)

**Checkpoint**: `road_risk_score` fully implemented and tested. US-004 acceptance scenarios covered. All four tools are ready.

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Tool registry wiring, discovery smoke tests, scenario integration test, and documentation.
All tasks depend on Phase 6 completion.

- [ ] T039 Register all four tools by calling each `register()` helper from `src/kosmos/tools/__init__.py` or a dedicated entrypoint; verify no import errors at module load in `tests/tools/test_registration.py`
- [ ] T040 [P] Write `test_search_discovery()`: assert `road_risk_score` appears in top-5 search results for the Scenario 1 query "오늘 서울 가는 길 안전해" via `ToolRegistry.search()` in `tests/tools/test_search_integration.py`
- [ ] T041 [P] Write `test_scenario1_flow_simulation()`: load all three fixtures, call `road_risk_score._call()` with mocked inner adapters returning fixture data, assert `risk_level` is a valid value and `summary` is a non-empty Korean string in `tests/tools/test_search_integration.py`
- [ ] T042 [P] Write `docs/tools/koroad.md`: bilingual tool doc for `koroad_accident_search` covering endpoint, auth, input/output schema, code table references, and usage example
- [ ] T043 [P] Write `docs/tools/kma.md`: bilingual tool doc covering both `kma_weather_alert_status` and `kma_current_observation`, including grid coordinate lookup and quirks (RN1="-", base_time retry, empty items)
- [ ] T044 [P] Run `uv run pytest tests/tools/` and confirm all non-`@pytest.mark.live` tests pass with zero live API calls; document fixture recording procedure in `tests/fixtures/README.md`

**Checkpoint**: Epic #7 complete. All 4 tools registered, tested, and documented. CI passes without API keys.

---

## Dependencies & Execution Order

### Phase dependency chain

```
Phase 1 (T001–T008)        — no deps; start immediately; all parallel
        ↓
Phase 2 (T009–T013)        — depends on Phase 1; T009→T010→T011 serial; T012/T013 parallel
        ↓
┌───────────────────────────────────┐
│  Phase 3: US1 (T014–T021)        │  ← parallel with Phase 4 and Phase 5
│  Phase 4: US2 (T022–T027)        │  ← parallel with Phase 3 and Phase 5
│  Phase 5: US3 (T028–T033)        │  ← parallel with Phase 3 and Phase 4
└───────────────────────────────────┘
        ↓  (all three must complete)
Phase 6: US4 (T034–T038)   — composite; depends on Phase 3 + 4 + 5
        ↓
Phase 7: Polish (T039–T044) — depends on Phase 6
```

### Within-phase ordering

**Phase 2**:
- T009 must precede T010 (errors.py is imported by code_tables.py)
- T010 is required before T012 (tests require the enum)
- T011 is required before T013 (tests require the dict)

**Phase 3 (US1)**:
- T014 → T015 → T016 → T017 (sequential; each layer builds on the previous)
- T018 is parallel-safe (fixture file; no code dependency)
- T019 requires T014, T016, T018
- T020 and T021 require T019 (extend the same test module)

**Phase 4 (US2)**:
- T022 → T023 → T024 → T025 (sequential)
- T026 is parallel-safe (fixture file)
- T027 requires T022, T024, T026

**Phase 5 (US3)**:
- T028 → T029 → T030 → T031 (sequential)
- T032 is parallel-safe (fixture file)
- T033 requires T028, T030, T032

**Phase 6 (US4)**:
- T034 → T035 → T036 → T037 (sequential)
- T038 requires T034 and T036

**Phase 7**:
- T039 must precede T040 (registration required for search test)
- T041, T042, T043, T044 are parallel-safe after T039

---

## Parallel Execution Examples

### Agent Teams: 3 Teammates after Phase 2

Once Phase 2 completes, dispatch three Teammates simultaneously:

```
Teammate A (Backend/Sonnet):
  T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021
  (Phase 3: US1 KOROAD adapter)

Teammate B (Backend/Sonnet):
  T022 → T023 → T024 → T025 → T026 → T027
  (Phase 4: US2 KMA WeatherAlert adapter)

Teammate C (Backend/Sonnet):
  T028 → T029 → T030 → T031 → T032 → T033
  (Phase 5: US3 KMA CurrentObservation adapter)
```

All three Teammates work on different subpackages (`koroad/`, `kma/` alert, `kma/` obs) with zero
file-level conflicts. They can all be dispatched in the same Agent Teams turn.

After all three complete, a single Teammate handles Phase 6 (US4) sequentially, then Phase 7.

### Fixture creation (parallel within each phase)

```
T018 (koroad fixture)       ← can be done any time after T001, T004
T026 (kma alert fixture)    ← can be done any time after T002, T005
T032 (kma obs fixture)      ← can be done any time after T002, T005
```

All three fixtures can be created concurrently by one person with live API keys, then committed.
If live keys are unavailable, synthetic fixtures are constructed manually and committed directly.

---

## Task Count Summary

| Phase | Tasks | Parallel-safe [P] | Sequential | Blocking? |
|---|---|---|---|---|
| Phase 1: Package setup | 8 | 8 | 0 | No |
| Phase 2: Foundational | 5 | 2 | 3 | YES — blocks all US |
| Phase 3: US1 KOROAD | 8 | 2 | 6 | No |
| Phase 4: US2 KMA Alert | 6 | 2 | 4 | No |
| Phase 5: US3 KMA Obs | 6 | 2 | 4 | No |
| Phase 6: US4 Composite | 5 | 0 | 5 | Yes — blocks Phase 7 |
| Phase 7: Polish | 6 | 5 | 1 | No |
| **Total** | **44** | **21** | **23** | — |

> Note: T044 (`uv run pytest` validation) is counted as a task but may be run as a verification
> step rather than assigned to a Teammate.

### User story traceability

| User Story | Spec Reference | Tasks |
|---|---|---|
| US-001: KOROAD hotspot query | spec § US-001 | T014–T021 |
| US-002: KMA weather alert status | spec § US-002 | T022–T027 |
| US-003: KMA current observation | spec § US-003 | T028–T033 |
| US-004: Road risk composite | spec § US-004 | T034–T038 |
| US-005: Fixture-based CI | spec § US-005 | T018, T026, T032, T039, T044 |
| US-006: Code-table enum validation | spec § US-006 | T010, T012, T020 |

### New files created by these tasks

```
src/kosmos/tools/koroad/__init__.py                     (T001)
src/kosmos/tools/kma/__init__.py                        (T002)
src/kosmos/tools/composite/__init__.py                  (T003)
tests/tools/koroad/__init__.py                          (T004)
tests/tools/kma/__init__.py                             (T005)
tests/tools/composite/__init__.py                       (T006)
tests/fixtures/koroad/.gitkeep                          (T007)
tests/fixtures/kma/.gitkeep                             (T008)
src/kosmos/tools/errors.py                              (T009, update existing)
src/kosmos/tools/koroad/code_tables.py                  (T010)
src/kosmos/tools/kma/grid_coords.py                     (T011)
tests/tools/koroad/test_code_tables.py                  (T012)
tests/tools/kma/test_grid_coords.py                     (T013)
src/kosmos/tools/koroad/koroad_accident_search.py       (T014–T017)
tests/fixtures/koroad/koroad_accident_search.json       (T018)
tests/tools/koroad/test_koroad_accident_search.py       (T019–T021)
src/kosmos/tools/kma/kma_weather_alert_status.py        (T022–T025)
tests/fixtures/kma/kma_weather_alert_status.json        (T026)
tests/tools/kma/test_kma_weather_alert_status.py        (T027)
src/kosmos/tools/kma/kma_current_observation.py         (T028–T031)
tests/fixtures/kma/kma_current_observation.json         (T032)
tests/tools/kma/test_kma_current_observation.py         (T033)
src/kosmos/tools/composite/road_risk_score.py           (T034–T037)
tests/tools/composite/test_road_risk_score.py           (T038)
tests/tools/test_registration.py                        (T039)
tests/tools/test_search_integration.py                  (T040–T041)
docs/tools/koroad.md                                    (T042)
docs/tools/kma.md                                       (T043)
tests/fixtures/README.md                                (T044)
```

**Total new files**: 30 (29 new + 1 update to `errors.py`)
