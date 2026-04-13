---
feature: Tool API Documentation
epic: "#289"
status: draft
---

# Tasks: Tool API Documentation

**Input**: Design documents from `/specs/016-tool-api-documentation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Not applicable — this is a docs-only epic. Verification tasks replace test tasks.

**Organization**: Tasks grouped by plan phase and user story for independent authoring.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup — Template & Index

**Purpose**: Establish the index page and document the shared page template so all per-adapter pages can follow it consistently.

- [ ] T001 Write `docs/tools/README.md` index — table of all 7 tools (tool ID, Korean name, provider, one-line description), links to each adapter page, Authentication section (`KOSMOS_DATA_GO_KR_API_KEY`), shared error code summary referencing `koroad.md`
- [ ] T002 [P] Verify `docs/tools/kma.md` has no inbound links in the codebase before deprecating (`grep -r "kma.md" docs/ src/ tests/`)

**Checkpoint**: `docs/tools/README.md` exists and lists all 7 tools. Inbound-link audit for `kma.md` complete.

---

## Phase 2: User Story 1 — KOROAD Adapter Documentation (Priority: P1) 🎯 MVP

**Goal**: Correct all errors in `docs/tools/koroad.md`, expand the `GugunCode` table to include Busan Haeundae, and make the full error code table available as the shared reference.

**Independent Test**: Open `koroad.md` and confirm: (1) auth field shows `KOSMOS_DATA_GO_KR_API_KEY`, (2) `gu_gun` Required column shows `Yes`, (3) `GugunCode` table includes `BUSAN_HAEUNDAE = 350`, (4) full error code table present.

### Implementation for User Story 1

- [ ] T003 [US1] Fix auth field in `docs/tools/koroad.md` Overview table: change `KOSMOS_KOROAD_API_KEY` → `KOSMOS_DATA_GO_KR_API_KEY`
- [ ] T004 [US1] Fix `gu_gun` optionality in `docs/tools/koroad.md` Input Schema table: change Required column from `No` → `Yes`; remove incorrect "omit to query entire province" note
- [ ] T005 [US1] Add `resultCode="03"` → empty hotspots list (not error) note to Wire Format Quirks section in `docs/tools/koroad.md`
- [ ] T006 [US1] Expand `GugunCode` table in `docs/tools/koroad.md`: add all 25 Seoul gu entries, all 16 Busan gu entries (must include `BUSAN_HAEUNDAE = 350`), all 5 Daejeon entries, and one anchor entry per remaining sido; add note linking to `src/kosmos/tools/koroad/code_tables.py` for the complete 250+ entry list
- [ ] T007 [US1] Add full shared error code table to `docs/tools/koroad.md` Error Codes section — resultCodes `"00"` through `"32"` matching spec Technical Design § Error code table
- [ ] T008 [US1] Add cross-validation rules note to `docs/tools/koroad.md` Input Schema — clarify that `_validate_legacy_sido` uses `SearchYearCd.year` property (extracted from enum name suffix, e.g., `GENERAL_2024 → 2024`)
- [ ] T009 [US1] Add runnable Python code example to `docs/tools/koroad.md` using `asyncio.run()` that passes with `uv run python` (uses fixture, no live API call)

**Checkpoint**: US-001 acceptance satisfied — developer can find `BUSAN_HAEUNDAE = 350` and the single-item dict normalization quirk in `docs/tools/koroad.md` in under five minutes.

---

## Phase 3: User Story 2 — KMA Ultra-Short-Term Forecast Documentation (Priority: P1)

**Goal**: Create `docs/tools/kma-ultra-short-term-forecast.md` with prominent `base_time` must-end-in-30 constraint so a developer fixing a validation error can identify the correct format immediately.

**Independent Test**: Open `kma-ultra-short-term-forecast.md` and confirm: (1) `base_time` HH30 requirement appears in both the Input Schema table Constraint column and the Wire Format Quirks section, (2) a wrong-value example (`"1400"` → `"1430"`) is shown, (3) Grid Coordinates section links to `kma-observation.md § Grid Coordinates`.

### Implementation for User Story 2

- [ ] T010 [US2] Create `docs/tools/kma-ultra-short-term-forecast.md` — Overview table (endpoint `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst`, rate limit 10/min, cache TTL 600 s, `is_concurrency_safe: Yes`)
- [ ] T011 [US2] Add Input Schema section to `docs/tools/kma-ultra-short-term-forecast.md` — full `KmaUltraShortTermForecastInput` field table; Constraint column for `base_time` must explicitly state "Must end in `30` (HH30 format, e.g. `0630`, `1130`)"
- [ ] T012 [US2] Add Output Schema section to `docs/tools/kma-ultra-short-term-forecast.md` — note that `KmaUltraShortTermForecastOutput` is a type alias for `KmaShortTermForecastOutput`; link to `kma-short-term-forecast.md § Output Schema`
- [ ] T013 [US2] Add Wire Format Quirks section to `docs/tools/kma-ultra-short-term-forecast.md` — prominently document `base_time` must-end-in-30 quirk with wrong-value example (`"1400"` raises ValidationError; correct value is `"1430"`); document `http://` base URL; published every hour at HH:30 KST; `num_of_rows=60` rationale
- [ ] T014 [US2] Add Grid Coordinates section to `docs/tools/kma-ultra-short-term-forecast.md` — link to `kma-observation.md § Grid Coordinates`; inline example: Seoul `nx=61, ny=126`
- [ ] T015 [US2] Add condensed Error Codes section to `docs/tools/kma-ultra-short-term-forecast.md` — `"00"` and `"03"` only; link to `koroad.md § Error Codes` for full table
- [ ] T016 [US2] Add runnable Python code example to `docs/tools/kma-ultra-short-term-forecast.md` using `asyncio.run()`

**Checkpoint**: US-002 acceptance satisfied — `base_time` HH30 requirement is prominent in both the Input Schema table and Wire Format Quirks section; wrong-value example (`"1400"` → `"1430"`) is present.

---

## Phase 4: User Story 3 — Composite Tool Documentation (Priority: P1)

**Goal**: Create `docs/tools/road-risk-score.md` with Partial Failure Semantics section, scoring formula, and Architecture fan-out explanation so a developer can understand `data_gaps` fallback values without reading source.

**Independent Test**: Open `road-risk-score.md` and confirm: (1) Partial Failure Semantics table lists `precipitation_mm=0.0` and `temperature_c=None` as fallbacks for `kma_current_observation` failure, (2) scoring formula matches source exactly, (3) total-failure condition (all three fail → ToolExecutionError) stated.

### Implementation for User Story 3

- [ ] T017 [US3] Create `docs/tools/road-risk-score.md` — Overview table (endpoint `(none — composite)`, provider `KOSMOS (composite)`, rate limit 10/min, cache TTL 300 s, Personal Data No, `is_concurrency_safe: Yes`)
- [ ] T018 [US3] Add Architecture section to `docs/tools/road-risk-score.md` — fan-out via `asyncio.gather(return_exceptions=True)` calling `koroad_accident_search`, `kma_weather_alert_status`, `kma_current_observation` in parallel; note that date/time for KMA observation is derived internally from `datetime.now(UTC)` — callers cannot specify them; links to inner adapter docs
- [ ] T019 [US3] Add Input Schema section to `docs/tools/road-risk-score.md` — full `RoadRiskScoreInput` field table (`si_do`, `gu_gun`, `search_year_cd`, `nx`, `ny`)
- [ ] T020 [US3] Add Output Schema section to `docs/tools/road-risk-score.md` — full `RoadRiskScoreOutput` field table; note `temperature_c: float | None` is `None` when observation fails; note `summary` is Korean-language prose for citizen display, not for programmatic parsing
- [ ] T021 [US3] Add Scoring Formula section to `docs/tools/road-risk-score.md` — exact formula from source (`hotspot_score`, `weather_score`, `risk_score`); risk level threshold table (`[0.0, 0.3)=low`, `[0.3, 0.6)=moderate`, `[0.6, 0.8)=high`, `[0.8, 1.0]=severe`) with Korean labels
- [ ] T022 [US3] Add Partial Failure Semantics section to `docs/tools/road-risk-score.md` — table of failed adapter → fallback values → noted in `data_gaps`; total failure condition (all three fail → `ToolExecutionError`)
- [ ] T023 [US3] Add cross-references in `docs/tools/road-risk-score.md` — links to `koroad.md`, `kma-alert.md`, `kma-observation.md` for inner adapter details
- [ ] T024 [US3] Add runnable Python code example to `docs/tools/road-risk-score.md` using `asyncio.run()`

**Checkpoint**: US-003 acceptance satisfied — developer can look up `data_gaps: ["kma_current_observation"]`, find Partial Failure Semantics section, and confirm `precipitation_mm=0.0` and `temperature_c=None` are the fallback values.

---

## Phase 5: User Story 4 — KMA Forecast Cross-Reference Documentation (Priority: P2)

**Goal**: Create `docs/tools/kma-short-term-forecast.md` with a Grid Coordinates section that includes Daejeon `nx=67, ny=100` and links to `kma-observation.md` for the full lookup table.

**Independent Test**: Open `kma-short-term-forecast.md` and confirm: (1) Grid Coordinates section contains inline example `Daejeon nx=67, ny=100`, (2) section links to `kma-observation.md § Grid Coordinates` for the full table, (3) `base_time` valid values (`0200/0500/0800/1100/1400/1700/2000/2300`) are in the Input Schema Constraint column.

### Implementation for User Story 4

- [ ] T025 [P] [US4] Create `docs/tools/kma-short-term-forecast.md` — Overview table (endpoint `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst`, rate limit 10/min, cache TTL 1800 s, `is_concurrency_safe: Yes`; note `http://` not `https://`)
- [ ] T026 [P] [US4] Add Input Schema section to `docs/tools/kma-short-term-forecast.md` — full `KmaShortTermForecastInput` field table; Constraint column for `base_time` must list all 8 valid values (`0200/0500/0800/1100/1400/1700/2000/2300`)
- [ ] T027 [P] [US4] Add Output Schema and Category Codes table to `docs/tools/kma-short-term-forecast.md` — `KmaShortTermForecastOutput`/`ForecastItem` field tables; category codes table (TMP, SKY, PTY, POP, REH, WSD, UUU, VVV, VEC, WAV, PCP, SNO, TMN, TMX) with unit and description
- [ ] T028 [US4] Add Grid Coordinates section to `docs/tools/kma-short-term-forecast.md` — link to `kma-observation.md § Grid Coordinates`; inline examples: Seoul `nx=61, ny=126`, Daejeon `nx=67, ny=100`
- [ ] T029 [US4] Add Wire Format Quirks section to `docs/tools/kma-short-term-forecast.md` — `http://` base URL; `base_time` validation (non-valid value raises `pydantic.ValidationError` before HTTP call); "data not ready" window (~10 min after base_time, retry with previous base_time); PCP/SNO range strings stored as-is; `num_of_rows=290` rationale
- [ ] T030 [US4] Add condensed Error Codes section and runnable Python example to `docs/tools/kma-short-term-forecast.md`

**Checkpoint**: US-004 acceptance satisfied — `kma-short-term-forecast.md § Grid Coordinates` contains inline Daejeon example `nx=67, ny=100` and links to `kma-observation.md`.

---

## Phase 6: User Story 5 — Overview Tables Accuracy Across All Tools (Priority: P2)

**Goal**: Every doc page has an Overview table whose values (endpoint URL, rate limit, cache TTL, auth type) exactly match the `GovAPITool` definitions in source code.

**Independent Test**: Spot-check each tool's `GovAPITool` definition in source against the doc Overview table — all values match.

### Implementation for User Story 5

- [ ] T031 [P] [US5] Create `docs/tools/kma-alert.md` — migrate `kma_weather_alert_status` content from `docs/tools/kma.md`; add Overview table (`is_concurrency_safe: Yes`); add `resultCode="03"` → empty list note to Wire Format Quirks; add `warn_var` codes table (1=강풍…11=폭염); add `warn_stress` codes (0=주의보/watch, 1=경보/warning); condensed Error Codes section linking to `koroad.md`
- [ ] T032 [P] [US5] Create `docs/tools/kma-observation.md` — migrate `kma_current_observation` content from `docs/tools/kma.md`; add full Grid Coordinates section from `src/kosmos/tools/kma/grid_coords.py` (use `<details>` block for the full 80+ row table, major cities visible by default); add category-to-field pivot mapping table (T1H→`t1h`, RN1→`rn1`, etc.); note `resultCode="03"` does NOT apply — empty items raises `ToolExecutionError`; note `base_time` rounds down to `HH00`; note `rn1` sentinel `"-"` normalized to `0.0`
- [ ] T033 [P] [US5] Create `docs/tools/kma-pre-warning.md` — Overview table (endpoint `http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrPwnList`, rate limit 10/min, cache TTL 300 s); Input Schema (`KmaPreWarningInput`); Output Schema (`KmaPreWarningOutput` / `PreWarningItem`); camelCase wire mapping (`stnId→stn_id`, `tmFc→tm_fc`, `tmSeq→tm_seq`); Station IDs section (known: `"108"` Seoul, `"159"` Busan; full table deferred — reference tracking issue); Wire Format Quirks (`resultCode="03"` = calm weather, title format example); condensed Error Codes section
- [ ] T034 [US5] Replace `docs/tools/kma.md` contents with deprecation redirect note pointing to `kma-alert.md` and `kma-observation.md`
- [ ] T035 [US5] Spot-check all 7 doc Overview tables against current `GovAPITool` definitions in source (`src/kosmos/tools/`) — verify endpoint URL, rate_limit_per_minute, cache_ttl_seconds, requires_auth, is_personal_data match exactly

**Checkpoint**: US-005 acceptance satisfied — all 7 docs have an Overview table; values verified against source code. `kma.md` contains only a redirect note.

---

## Phase 7: Review & Cross-References

**Purpose**: Final accuracy sweep, cross-reference verification, and code example structural validation.

- [ ] T036 [P] Verify cross-reference: `kma-short-term-forecast.md § Grid Coordinates` links to `kma-observation.md § Grid Coordinates`
- [ ] T037 [P] Verify cross-reference: `kma-ultra-short-term-forecast.md § Grid Coordinates` links to `kma-observation.md § Grid Coordinates`
- [ ] T038 [P] Verify cross-reference: `road-risk-score.md` links to `koroad.md`, `kma-alert.md`, and `kma-observation.md`
- [ ] T039 [P] Verify `docs/tools/README.md` index lists all 7 tools with one-line descriptions
- [ ] T040 Validate all Wire Format Quirks coverage from spec Acceptance Criteria — walk the checklist: KOROAD single-item dict normalization, KMA single-item dict normalization, XML/JSON guard, `resultCode="03"` semantics, `base_time` rounding (observation), `base_time` must-end-in-30 (ultra-short-term), `base_time` valid values (short-term), `rn1` sentinel normalization, KOROAD legacy sido codes, `road_risk_score` fan-out/partial-failure/scoring
- [ ] T041 Structural validation of all code examples — run each `asyncio.run()` snippet with `KOSMOS_DATA_GO_KR_API_KEY` unset; confirm failure mode is `ConfigurationError` (not `ModuleNotFoundError` or `SyntaxError`)
- [ ] T042 Verify `kma-observation.md § Grid Coordinates` contains `nx=67, ny=100` for Daejeon (confirms `grid_coords.py: "대전": (67, 100)`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1 — KOROAD)**: Depends on Phase 1 (index must reference koroad.md)
- **Phase 3 (US2 — Ultra-short-term)**: Depends on Phase 6 T032 (`kma-observation.md` must exist for Grid Coordinates link). Can start in parallel after Phase 1.
- **Phase 4 (US3 — road_risk_score)**: Depends on Phase 2 (koroad.md), Phase 6 T031 (kma-alert.md), Phase 6 T032 (kma-observation.md) for cross-reference links. Core content (T017–T022) can be drafted in parallel.
- **Phase 5 (US4 — Short-term Forecast)**: Can begin after Phase 1. Depends on Phase 6 T032 (`kma-observation.md`) for Grid Coordinates link in T028.
- **Phase 6 (US5 — Overview Accuracy)**: T031, T032, T033 are all new files — fully parallel. T034 depends on T031 + T032. T035 can run after all pages exist.
- **Phase 7 (Review)**: All cross-reference checks depend on all adapter pages existing (Phases 2–6 complete).

### User Story Dependencies

- **US1 (KOROAD, P1)**: Requires Phase 1 complete. No other user story dependency.
- **US2 (Ultra-short-term, P1)**: Requires `kma-observation.md` (T032) for Grid Coordinates link. T010–T013 (Overview, Input, Output, Quirks) can draft in parallel with Phase 6.
- **US3 (road_risk_score, P1)**: Architecture, Input, Output, Scoring Formula sections (T017–T022) can draft in parallel. Cross-reference tasks (T023) require kma-alert.md and kma-observation.md.
- **US4 (Short-term Forecast, P2)**: T025–T027 fully parallel (different sections). T028 depends on T032 (`kma-observation.md`).
- **US5 (Overview Accuracy, P2)**: T031, T032, T033 fully parallel. T034 depends on T031+T032. T035 depends on all pages.

### Parallel Opportunities

- T002, T025, T026, T027, T031, T032, T033: All on different files — fully parallel
- T003–T009 (US1 corrections to koroad.md): Same file — sequential
- T036–T039 (cross-reference checks): All on different files — fully parallel
- **Phase 6 T031 + T032 + T033**: Three new KMA files — fully parallel with separate agents
- **US1 + Phase 6 T031 + Phase 6 T032 + Phase 6 T033**: Four different doc files — parallel after Phase 1

---

## Parallel Example: Phase 6 KMA Pages

```bash
# All three new KMA adapter pages on different files — fully parallel:
Agent A: "Create docs/tools/kma-alert.md (T031)"
Agent B: "Create docs/tools/kma-observation.md (T032)"
Agent C: "Create docs/tools/kma-pre-warning.md (T033)"
```

## Parallel Example: US1 + US4 Sections

```bash
# After Phase 1 complete — KOROAD corrections and short-term forecast sections in parallel:
Agent A: "Fix koroad.md errors and expand GugunCode table (T003–T009)"
Agent B: "Draft kma-short-term-forecast.md Overview + Input + Output sections (T025–T027)"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 — all P1)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: US1 — KOROAD corrections (T003–T009)
3. Complete Phase 6 T031 + T032 (kma-alert.md + kma-observation.md — prerequisite for US2/US3 cross-references)
4. Complete Phase 3: US2 — Ultra-short-term forecast (T010–T016)
5. Complete Phase 4: US3 — road_risk_score composite (T017–T024)
6. **STOP and VALIDATE**: US-001, US-002, US-003 acceptance criteria met

### Incremental Delivery

1. Phase 1 + Phase 2 → KOROAD doc corrected (US-001 satisfied) → Developer-ready
2. Phase 3 + Phase 6 T031/T032 → Ultra-short-term + KMA alert/observation → US-002 satisfied
3. Phase 4 → road_risk_score composite → US-003 satisfied
4. Phase 5 + Phase 6 T033 → Short-term forecast + pre-warning → US-004 satisfied
5. Phase 6 T034/T035 → Accuracy sweep + kma.md redirect → US-005 satisfied
6. Phase 7 → Full cross-reference and accuracy review

### Parallel Team Strategy

With Agent Teams (3 agents):

1. **Lead**: Completes Phase 1 — index and inbound-link audit
2. Once Phase 1 is done:
   - **Agent A (Sonnet)**: US1 — KOROAD corrections (T003–T009) + US3 — road_risk_score (T017–T024)
   - **Agent B (Sonnet)**: Phase 6 — kma-alert.md (T031) + kma-observation.md (T032)
   - **Agent C (Sonnet)**: Phase 6 — kma-pre-warning.md (T033) + US4 — kma-short-term-forecast.md (T025–T030)
3. **Agent A** completes US2 (kma-ultra-short-term-forecast.md, T010–T016) after Agent B finishes kma-observation.md
4. **Lead**: Phase 7 — cross-reference and accuracy review (T036–T042)

---

## Notes

- Total tasks: **42**
- Phase 1 (Setup) tasks: 2 (T001–T002)
- US1 (KOROAD) tasks: 7 (T003–T009)
- US2 (Ultra-short-term forecast) tasks: 7 (T010–T016)
- US3 (road_risk_score composite) tasks: 8 (T017–T024)
- US4 (Short-term forecast) tasks: 6 (T025–T030)
- US5 (Overview accuracy) tasks: 5 (T031–T035)
- Review tasks: 7 (T036–T042)
- Parallel opportunities: 6 groups of [P] tasks across phases
- MVP scope: Phase 1 + Phase 2 + Phase 3 + Phase 4 + Phase 6 T031/T032 (P1 stories = 31 tasks)
- All tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` format
