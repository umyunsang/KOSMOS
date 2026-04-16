# Tasks: NMC Freshness SLO Enforcement

**Input**: Design documents from `specs/023-nmc-freshness-slo/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Included — spec explicitly requires "fixture 기반 unit + stale/fresh 경계값" tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test fixtures and foundational test infrastructure for freshness validation

- [X] T001 [P] Create fresh NMC response fixture in tests/fixtures/nmc/fresh_response.json — include `hvidate` set to 10 minutes ago in `YYYY-MM-DD HH:MM:SS` KST format, with realistic NMC bed availability fields (`hvec`, `hvoc`, `hvs1`, `dutyName`, `dutyAddr`, `dutyTel3`, `wgs84Lat`, `wgs84Lon`)
- [X] T002 [P] Create stale NMC response fixture in tests/fixtures/nmc/stale_response.json — include `hvidate` set to 60 minutes ago in `YYYY-MM-DD HH:MM:SS` KST format, with same realistic NMC field structure as fresh_response.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model changes and freshness utility that MUST be complete before user story implementation

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `freshness_status: Literal["fresh"] | None = None` field to `LookupMeta` in src/kosmos/tools/models.py — add after `rate_limit_remaining` field, include docstring: "Set to 'fresh' when adapter freshness check passes. None for adapters without freshness semantics."
- [X] T004 Create freshness check utility module at src/kosmos/tools/nmc/freshness.py — implement `FreshnessResult` dataclass (fields: `is_fresh: bool`, `data_age_minutes: float`, `threshold_minutes: int`, `hvidate_raw: str | None`) and `check_freshness(hvidate_str: str | None, threshold_minutes: int | None = None) -> FreshnessResult` function. When `threshold_minutes` is `None`, read `settings.nmc_freshness_minutes` from `kosmos.settings.settings` as default. Parse `hvidate` with `datetime.strptime("%Y-%m-%d %H:%M:%S")`, localize to `ZoneInfo("Asia/Seoul")`, compare age against threshold. Missing/empty/unparseable `hvidate` → `FreshnessResult(is_fresh=False, ...)` (fail-closed per Constitution § II).

**Checkpoint**: Foundation ready — freshness utility and model extension in place

---

## Phase 3: User Story 1 + 2 — Fresh Delivery & Stale Rejection (Priority: P1) MVP

**Goal**: Every NMC response is validated for freshness: fresh data passes through with `freshness_status: "fresh"` metadata, stale data is rejected with `LookupError(reason="stale_data")`

**Independent Test**: Call `check_freshness()` with fixture data and verify correct fresh/stale classification; call NMC adapter handler with mock responses and verify envelope shape

### Tests for User Stories 1 & 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation in T007**

- [X] T005 [P] [US1] Write unit tests for fresh path in tests/tools/nmc/test_freshness_validation.py — mock `datetime.now(tz=ZoneInfo("Asia/Seoul"))` to a fixed time matching fixture hvidate + expected age for deterministic results. Test `check_freshness()` with hvidate 10 min old (threshold 30) returns `FreshnessResult(is_fresh=True, data_age_minutes≈10, threshold_minutes=30)`; test hvidate exactly at threshold (30 min old, threshold 30) returns `is_fresh=True` (boundary: equal-to-threshold is fresh per spec AC); load tests/fixtures/nmc/fresh_response.json as input
- [X] T006 [P] [US2] Write unit tests for stale path in tests/tools/nmc/test_freshness_validation.py — mock `datetime.now(tz=ZoneInfo("Asia/Seoul"))` to a fixed time for deterministic age calculations. Test `check_freshness()` with hvidate 31 min old (threshold 30) returns `FreshnessResult(is_fresh=False)`; test hvidate 1440 min old returns `is_fresh=False`; test missing hvidate (None) returns `is_fresh=False`; test empty string hvidate returns `is_fresh=False`; test unparseable hvidate (`"invalid-date"`) returns `is_fresh=False`; load tests/fixtures/nmc/stale_response.json as input

### Implementation for User Stories 1 & 2

- [X] T007 [US1] [US2] Integrate freshness validation into NMC adapter handler in src/kosmos/tools/nmc/emergency_search.py — replace `Layer3GateViolation` raise with real handler logic: (1) call upstream NMC API via httpx, (2) extract `hvidate` from response items, (3) call `check_freshness()` from `kosmos.tools.nmc.freshness`, (4) if fresh: return response dict with items + inject `freshness_status: "fresh"` key for envelope meta enrichment, (5) if stale: return dict matching `LookupError` shape with `kind="error"`, `reason="stale_data"`, `message` including data age and threshold, `retryable=False`. Update module docstring to remove "freshness deferred" comment (FR-034 is now implemented).
- [X] T008 [US1] [US2] Write integration test in tests/tools/nmc/test_freshness_validation.py — test full `executor.invoke()` flow with mocked httpx response (respx): (1) mock NMC API to return fresh fixture → verify result is LookupCollection/LookupRecord with `meta.freshness_status == "fresh"`, (2) mock NMC API to return stale fixture → verify result is LookupError with `reason == "stale_data"` and message contains age and threshold info, (3) mock NMC API to return response with missing `hvidate` → verify result is LookupError with `reason == "stale_data"`

**Checkpoint**: US1 + US2 complete — fresh data delivered with status, stale data rejected with error

---

## Phase 4: User Story 3 — Configurable Freshness Threshold (Priority: P2)

**Goal**: Freshness threshold is configurable via `KOSMOS_NMC_FRESHNESS_MINUTES` env var with default 30, clamped [1, 1440]

**Independent Test**: Set env var to different values and verify freshness check uses the configured threshold

### Tests for User Story 3

- [X] T009 [P] [US3] Write threshold configuration tests in tests/tools/nmc/test_freshness_validation.py — (1) test `check_freshness()` with explicit `threshold_minutes=60` and hvidate 59 min old → `is_fresh=True`, (2) test with `threshold_minutes=60` and hvidate 61 min old → `is_fresh=False`, (3) test default threshold from `settings.nmc_freshness_minutes` is used when no explicit threshold passed, (4) verify `KosmosSettings.nmc_freshness_minutes` Field constraint `ge=1, le=1440` rejects out-of-range values via `pydantic.ValidationError`

### Implementation for User Story 3

- [X] T010 [US3] Verify threshold integration in src/kosmos/tools/nmc/freshness.py — confirm `check_freshness()` correctly reads `settings.nmc_freshness_minutes` as default when `threshold_minutes=None` (signature already defined in T004). Write a focused integration test: call `check_freshness(hvidate_str, threshold_minutes=None)` and verify it uses the settings default. No changes needed to src/kosmos/settings.py (field already exists with correct constraints).

**Checkpoint**: US3 complete — threshold configurable via env var, defaults and clamp validated

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, documentation, and regression verification

- [X] T011 Update NMC adapter module docstring in src/kosmos/tools/nmc/emergency_search.py — remove all "FR-034: Freshness check deferred" comments and replace with "FR-034: Freshness enforcement via check_freshness() — see freshness.py"
- [X] T012 Run full test suite via `uv run pytest` and verify zero regressions — existing tests in tests/tools/nmc/test_emergency_search_auth_gate.py must still pass (auth gate behavior unchanged), existing envelope normalization tests must still pass (LookupMeta backward-compatible with new optional field)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: T003 and T004 can run in parallel; BLOCKS all user stories
- **US1+US2 (Phase 3)**: Depends on Phase 2 completion. T005 and T006 (tests) can run in parallel. T007 depends on T004. T008 depends on T007.
- **US3 (Phase 4)**: Depends on Phase 2 completion. Can run in parallel with Phase 3 (different test cases, shared utility).
- **Polish (Phase 5)**: Depends on Phase 3 and Phase 4 completion

### User Story Dependencies

- **US1 + US2 (P1)**: Can start after Foundational (Phase 2) — core feature, MVP
- **US3 (P2)**: Can start after Foundational (Phase 2) — independent of US1/US2 implementation but tests may share the same file

### Within Each User Story

- Tests written FIRST, must FAIL before implementation
- Utility module (freshness.py) before adapter integration
- Unit tests before integration tests

### Parallel Opportunities

- T001 and T002 (fixtures) can run in parallel
- T003 and T004 (model + utility) can run in parallel
- T005 and T006 (unit tests) can run in parallel
- T009 (US3 tests) can run in parallel with T005/T006
- Phase 3 and Phase 4 can run in parallel after Phase 2

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch both foundational tasks together:
Task: "Add freshness_status to LookupMeta in src/kosmos/tools/models.py"
Task: "Create freshness utility in src/kosmos/tools/nmc/freshness.py"
```

## Parallel Example: Phase 3 (Tests)

```bash
# Launch US1 and US2 tests together:
Task: "Write fresh path tests in tests/tools/nmc/test_freshness_validation.py"
Task: "Write stale path tests in tests/tools/nmc/test_freshness_validation.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (fixtures)
2. Complete Phase 2: Foundational (LookupMeta + freshness utility)
3. Complete Phase 3: US1 + US2 (fresh/stale validation)
4. **STOP and VALIDATE**: Run `uv run pytest tests/tools/nmc/ -v`
5. Core safety guarantee is in place

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Phase 3 → US1 + US2 complete → MVP (fresh/stale enforcement works)
3. Phase 4 → US3 complete → Threshold configurability validated
4. Phase 5 → Polish → Full test suite passes, docs updated

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All tests use fixture data — NEVER call live data.go.kr APIs (Constitution § IV)
- `freshness_status` field is backward-compatible (None default) — existing tests unaffected
- Auth gate behavior is unchanged — freshness check only applies after successful upstream fetch
