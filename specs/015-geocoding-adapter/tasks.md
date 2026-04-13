---
feature: Geocoding Adapter
epic: "#288"
status: draft
---

# Tasks: Geocoding Adapter

**Input**: Design documents from `/specs/015-geocoding-adapter/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Included — spec US-004 explicitly requires recorded-fixture CI tests.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeleton, shared Kakao HTTP client, region mapping, and grid conversion.

- [ ] T001 Create module directory and `__init__.py` at `src/kosmos/tools/geocoding/__init__.py`
- [ ] T002 [P] Implement Kakao HTTP client with Pydantic models in `src/kosmos/tools/geocoding/kakao_client.py`
- [ ] T003 [P] Implement region-name-to-code mapping in `src/kosmos/tools/geocoding/region_mapping.py`
- [ ] T004 [P] Add Lambert Conformal Conic `latlon_to_grid()` to `src/kosmos/tools/kma/grid_coords.py`
- [ ] T005 [P] Create test fixture directory and 5 recorded Kakao JSON fixtures under `tests/tools/geocoding/fixtures/`
- [ ] T006 Create `tests/tools/geocoding/__init__.py` (empty, pytest discovery)

**Checkpoint**: Foundation ready — Kakao client callable, region mapping importable, grid conversion testable.

---

## Phase 2: User Story 1 — Address to Region Codes (Priority: P1) MVP

**Goal**: Free-text Korean address → KOROAD `(SidoCode, GugunCode)` via `address_to_region` tool.

**Independent Test**: `uv run pytest tests/tools/geocoding/test_address_to_region.py` passes with fixtures only (no API key).

### Tests for User Story 1

- [ ] T007 [P] [US1] Implement Kakao client unit tests in `tests/tools/geocoding/test_kakao_client.py`
- [ ] T008 [P] [US1] Implement region mapping unit tests in `tests/tools/geocoding/test_region_mapping.py`
- [ ] T009 [P] [US1] Implement `address_to_region` adapter tests in `tests/tools/geocoding/test_address_to_region.py`

### Implementation for User Story 1

- [ ] T010 [US1] Implement `address_to_region` adapter (Input/Output models, `_resolve`, `_call`, `GovAPITool`, `register()`) in `src/kosmos/tools/geocoding/address_to_region.py`

**Checkpoint**: `address_to_region("서울 강남구")` returns `sido=11, gugun=680` using fixture. SC-002, SC-003, SC-005, SC-006 validated.

---

## Phase 3: User Story 2 — Address to KMA Grid Coordinates (Priority: P1)

**Goal**: Free-text Korean address → KMA `(nx, ny)` grid coordinates via `address_to_grid` tool, with local-lookup fallback.

**Independent Test**: `uv run pytest tests/tools/geocoding/test_address_to_grid.py` passes with fixtures only.

### Tests for User Story 2

- [ ] T011 [P] [US2] Implement grid conversion unit tests in `tests/tools/geocoding/test_grid_conversion.py`
- [ ] T012 [P] [US2] Implement `address_to_grid` adapter tests in `tests/tools/geocoding/test_address_to_grid.py`

### Implementation for User Story 2

- [ ] T013 [US2] Implement `address_to_grid` adapter (Input/Output models, `_resolve_from_kakao`, `_fallback_local_lookup`, `_call`, `GovAPITool`, `register()`) in `src/kosmos/tools/geocoding/address_to_grid.py`

**Checkpoint**: `address_to_grid("서초구")` returns `nx=61, ny=124` using fixture. Fallback to `REGION_TO_GRID` tested. SC-004, SC-007 validated.

---

## Phase 4: User Story 3 — Integration with road_risk_score (Priority: P2)

**Goal**: Both geocoding tools registered in `ToolRegistry`, discoverable by LLM, and chainable with `road_risk_score`.

**Independent Test**: `uv run pytest tests/tools/test_registration.py` asserts 9 registered tools.

### Implementation for User Story 3

- [ ] T014 [US3] Register both tools in `src/kosmos/tools/register_all.py` (import + call, update docstring count to 9)
- [ ] T015 [US3] Update `tests/tools/test_registration.py` assertions (registry size → 9, add tool IDs to expected sets)
- [ ] T016 [US3] Verify search integration — run `tests/tools/test_search_integration.py` to confirm geocoding tools surface on Korean address queries

**Checkpoint**: `register_all_tools()` returns 9 tools. SC-001, SC-010 validated.

---

## Phase 5: User Story 4 — CI Fixture Tests (Priority: P1)

**Goal**: All tests pass in CI without any live API keys.

**Independent Test**: `KOSMOS_KAKAO_API_KEY= uv run pytest tests/tools/geocoding/` passes with zero failures.

### Implementation for User Story 4

- [ ] T017 [US4] Run `uv run pytest tests/` and confirm all tests pass with no live API calls (SC-009)
- [ ] T018 [US4] Run `uv run ruff check src/ tests/` and fix all lint issues
- [ ] T019 [US4] Run `uv run ruff format --check src/ tests/` and fix all format issues

**Checkpoint**: Full green CI. No `type: ignore` needed. SC-009 validated.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: ADR, documentation, type safety.

- [ ] T020 [P] Create `docs/adr/` directory and write `docs/adr/ADR-001-geocoding-provider.md`
- [ ] T021 [P] Update `src/kosmos/tools/geocoding/__init__.py` with re-exports and module docstring
- [ ] T022 Validate all spec acceptance criteria (SC-001 through SC-010) in a final sweep

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on T001, T002, T003, T005 from Setup
- **US2 (Phase 3)**: Depends on T001, T002, T004, T005 from Setup. Independent of US1.
- **US3 (Phase 4)**: Depends on T010 (US1) and T013 (US2) — both adapters must exist
- **US4 (Phase 5)**: Depends on US1, US2, US3 all complete
- **Polish (Phase 6)**: Depends on Phase 5

### User Story Dependencies

- **US1 (address_to_region)**: Requires `kakao_client.py` + `region_mapping.py` — no dependency on US2
- **US2 (address_to_grid)**: Requires `kakao_client.py` + `latlon_to_grid()` — no dependency on US1
- **US3 (integration)**: Requires both US1 and US2 complete
- **US4 (CI validation)**: Requires US1, US2, US3 complete

### Parallel Opportunities

- T002, T003, T004, T005: All Setup tasks on different files — fully parallel
- T007, T008, T009: All US1 tests on different files — fully parallel
- T011, T012: Both US2 tests on different files — fully parallel
- **US1 and US2 implementation can run in parallel** (different files, shared only via `kakao_client.py` which is in Setup)
- T014, T015: Integration tasks must be sequential (registration before test assertion update)
- T020, T021: Polish tasks on different files — fully parallel

---

## Parallel Example: Setup Phase

```bash
# All four foundation tasks in parallel (different files):
Task: "Implement Kakao HTTP client in src/kosmos/tools/geocoding/kakao_client.py"
Task: "Implement region mapping in src/kosmos/tools/geocoding/region_mapping.py"
Task: "Add latlon_to_grid() to src/kosmos/tools/kma/grid_coords.py"
Task: "Create fixture files under tests/tools/geocoding/fixtures/"
```

## Parallel Example: US1 + US2 Implementation

```bash
# After Setup complete, US1 and US2 can proceed simultaneously:
Agent A: "Implement address_to_region adapter + tests"
Agent B: "Implement address_to_grid adapter + tests"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (T001–T006)
2. Complete Phase 2: US1 — address_to_region (T007–T010)
3. Complete Phase 3: US2 — address_to_grid (T011–T013)
4. **STOP and VALIDATE**: Both tools work independently with fixtures
5. Complete Phase 4: Integration (T014–T016)

### Parallel Team Strategy

With Agent Teams:
1. **Lead**: Completes Setup (Phase 1) — shared foundation
2. **Agent A (Sonnet)**: US1 — `address_to_region` + `kakao_client` tests + `region_mapping` tests
3. **Agent B (Sonnet)**: US2 — `address_to_grid` + `grid_conversion` tests
4. **Lead**: Integration (Phase 4) + Polish (Phase 6)

---

## Notes

- Total tasks: **22**
- US1 tasks: 4 (T007–T010)
- US2 tasks: 3 (T011–T013)
- US3 tasks: 3 (T014–T016)
- US4 tasks: 3 (T017–T019)
- Setup tasks: 6 (T001–T006)
- Polish tasks: 3 (T020–T022)
- Parallel opportunities: 8 groups of [P] tasks across phases
- MVP scope: Phase 1 + Phase 2 + Phase 3 (Setup + US1 + US2 = 13 tasks)
- All tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` format
