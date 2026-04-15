---
description: "Task breakdown for MVP Main-Tool (lookup + resolve_location + 4 seed adapters + BM25 gate + #288 refactor)"
---

# Tasks: MVP Main-Tool — `lookup` + `resolve_location`

**Input**: Design documents from `/specs/022-mvp-main-tool/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓
**Tests**: REQUIRED — FR-023 mandates happy + error-path tests with recorded fixtures for every seed adapter; Constitution §IV forbids live `data.go.kr` calls in CI.
**Organization**: Tasks grouped by User Story (US1–US5) from `spec.md` with frozen discriminator names from `docs/design/mvp-tools.md §5.4`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: `US1`–`US5` — maps to spec.md user stories
- File paths are absolute from repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new runtime dependencies and scaffold the feature source/test tree. Does not yet touch production logic.

- [ ] T001 Add `rank_bm25>=0.2.2` and `kiwipiepy>=0.17` to `[project.dependencies]` in `pyproject.toml` and run `uv sync` to refresh `uv.lock`.
- [ ] T002 [P] Create empty package scaffolds `src/kosmos/tools/hira/__init__.py` and `src/kosmos/tools/nmc/__init__.py` (NMC gets an `__init__.py` docstring flagging `is_personal_data=True` wiring).
- [ ] T003 [P] Create empty test scaffolds `tests/tools/hira/__init__.py`, `tests/tools/nmc/__init__.py`, `tests/fixtures/hira/.gitkeep`, `tests/fixtures/nmc/.gitkeep`.
- [ ] T004 [P] Create `eval/` directory with a stub `eval/retrieval_queries.yaml` containing the YAML schema header comment (`query: ... / expected_tool_id: ... / notes?: ...`) — populated in T037.

**Checkpoint**: Dependencies resolved; new package trees exist empty.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two-tool surface contract, BM25 retrieval core, envelope normalizer, and Layer 3 auth-gate short-circuit. **All five user stories depend on this phase.** Do not start any US-phase before Phase 2 completes.

**⚠️ CRITICAL**: No user story work begins until Phase 2 is green.

### Schemas (frozen discriminators)

- [ ] T005 [P] Extend `src/kosmos/tools/models.py` with `ResolveLocationInput` (fields: `query: str (1..200)`, `want: Literal["coords","adm_cd","coords_and_admcd","road_address","jibun_address","poi","all"]=coords_and_admcd`, `near: tuple[float,float]|None`).
- [ ] T006 [P] Extend `src/kosmos/tools/models.py` with the 6-variant `ResolveLocationOutput` discriminated union on `kind` (`CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError`) per `contracts/resolve_location.output.schema.json`. `AdmCodeResult.code` uses `pattern=r"^[0-9]{10}$"`.
- [ ] T007 [P] Extend `src/kosmos/tools/models.py` with `LookupInput` discriminated union on `mode` (`LookupSearchInput | LookupFetchInput`). `tool_id` uses `pattern=r"^[a-z][a-z0-9_]*$"`. `params: dict[str, object]` is the only loose field (validated at fetch time against the target adapter schema).
- [ ] T008 [P] Extend `src/kosmos/tools/models.py` with the 5-variant `LookupOutput` discriminated union on `kind` (`LookupSearchResult | LookupRecord | LookupCollection | LookupTimeseries | LookupError`) per `contracts/lookup.output.schema.json`, including `LookupMeta` and `AdapterCandidate` nested models.
- [ ] T009 Extend `src/kosmos/tools/errors.py` with the closed `LookupErrorReason` enum (`auth_required | stale_data | timeout | upstream_unavailable | unknown_tool | invalid_params | out_of_domain | empty_registry`) and the `ResolveErrorReason` enum (`not_found | ambiguous | upstream_unavailable | invalid_query | empty_query | out_of_domain`). Depends on T005–T008 for import wiring.

### Retrieval core

- [ ] T010 [P] Create `src/kosmos/tools/tokenizer.py` — thin `kiwipiepy` wrapper with module-level lazy singleton, deterministic output, and fallback `whitespace_tokenize` for non-Korean strings.
- [ ] T011 [P] Create `src/kosmos/tools/bm25_index.py` — `rank_bm25` wrapper with `rebuild(corpus: list[str])`, `score(query: str) -> list[tuple[tool_id, score]]`, and deterministic tie-break by `tool_id` ascending (FR-013).
- [ ] T012 Replace the body of `src/kosmos/tools/search.py`: remove token-overlap scoring, delegate to `bm25_index`, expose `search(query: str, registry: ToolRegistry, top_k: int) -> list[AdapterCandidate]`. Adaptive clamp `top_k = max(1, min(top_k, len(registry), 20))`. Depends on T010, T011.
- [ ] T013 Extend `src/kosmos/tools/registry.py` — in `register()`, rebuild the BM25 index from the concatenated `search_hint` of every registered tool. Add a startup invariant: `is_personal_data=True and not requires_auth` raises `RegistrationError` (FR-038). Depends on T012.

### Envelope + Layer 3 gate

- [ ] T014 [P] Create `src/kosmos/tools/envelope.py` — `normalize(output: object, tool: GovAPITool) -> LookupOutput` that validates every handler return against the frozen 5-variant union and raises `EnvelopeNormalizationError` for discriminator mismatch (FR-015). Catches handler exceptions and converts to `LookupError` (FR-017). Injects `meta.source`, `fetched_at`, `request_id`, `elapsed_ms` (FR-014).
- [ ] T015 Extend `src/kosmos/tools/executor.py` — add the unconditional Layer 3 short-circuit: before invoking any handler, if `tool.requires_auth and no_session_identity`, return `LookupError(reason="auth_required", retryable=False)` with zero upstream calls (FR-025, FR-026). Depends on T014.

### Configuration

- [ ] T016 [P] Add env settings fields to `src/kosmos/settings.py` (pydantic-settings): `kosmos_lookup_topk: int = Field(default=5, ge=1, le=20)`, `kosmos_nmc_freshness_minutes: int = Field(default=30, ge=1, le=1440)`, `kosmos_kakao_rest_key`, `kosmos_juso_confm_key`, `kosmos_sgis_key`, `kosmos_sgis_secret`, `kosmos_data_go_kr_api_key` (FR-032, FR-033, FR-034).

**Checkpoint**: Two-tool schemas, BM25 core, envelope normalizer, Layer 3 gate, and env config all exist and import clean. User story phases can begin in parallel.

---

## Phase 3: User Story 1 — End-to-end citizen query through the two-tool surface (Priority: P1) 🎯 MVP

**Goal**: Deliver the `resolve_location` + `lookup` facade driving a full `resolve → search → fetch` cycle against the KOROAD seed adapter, returning a typed `LookupCollection` envelope.

**Independent Test**: Drive a scripted conversation against a stub LLM calling `resolve_location(query="종로구", want="adm_cd")` → `lookup(mode="search", query="교통사고 위험지역")` → `lookup(mode="fetch", tool_id="koroad_accident_hazard_search", params=...)` and verify the final `LookupCollection` contains hazard records against a recorded fixture. No live `data.go.kr` call.

### Tests for User Story 1 ⚠️

- [ ] T017 [P] [US1] Contract test `tests/tools/contracts/test_resolve_location_schema.py` — import `ResolveLocationInput/Output` and round-trip the sample payloads from `specs/022-mvp-main-tool/contracts/resolve_location.*.schema.json`.
- [ ] T018 [P] [US1] Contract test `tests/tools/contracts/test_lookup_schema.py` — round-trip every variant in `contracts/lookup.output.schema.json` including `LookupSearchResult` and all 4 fetch variants.
- [ ] T019 [P] [US1] Integration test `tests/tools/test_resolve_location.py` — `resolve_location(query="서울 종로구", want="adm_cd")` returns an `AdmCodeResult` with `code=pattern ^[0-9]{10}$`, `level="sigungu"`, `source ∈ {sgis, juso}` (uses recorded `tests/fixtures/geocoding/`).
- [ ] T020 [P] [US1] Integration test `tests/tools/test_lookup_search.py` — `lookup(mode="search", query="교통사고 위험지역", domain="traffic")` returns `LookupSearchResult` with `koroad_accident_hazard_search` as the top candidate.
- [ ] T021 [P] [US1] Integration test `tests/tools/test_lookup_fetch.py` — `lookup(mode="fetch", tool_id="koroad_accident_hazard_search", params={"adm_cd":"1111000000","year":2025})` returns `LookupCollection` with `items[].spot_nm`, `tot_dth_cnt`, `geom_json` populated from the recorded KOROAD fixture.
- [ ] T022 [P] [US1] Unit test `tests/tools/test_envelope_normalization.py` — injecting a handler output with wrong `kind` raises `EnvelopeNormalizationError`; missing `meta` fields rejected; exceptions converted to `LookupError`.

### Implementation for User Story 1

- [ ] T023 [US1] Create `src/kosmos/tools/resolve_location.py` — the facade coroutine. Deterministic resolver chain `kakao → juso → sgis` from `src/kosmos/tools/geocoding/`, short-circuit on first non-error, map backend output to the correct `kind` variant (`coords | adm_cd | address | poi | bundle`). `want="coords_and_admcd"` returns a `ResolveBundle`. Depends on T005–T009, T016.
- [ ] T024 [US1] Create `src/kosmos/tools/lookup.py` — the facade coroutine dispatching on `LookupInput.mode`. `search` delegates to `tools.search.search(...)`; `fetch` calls `executor.invoke(tool_id, params)` passing through Layer 3 gate + envelope normalizer. Unknown `tool_id` returns `LookupError(reason="unknown_tool")` with no side effect (edge case). Depends on T012, T014, T015.
- [ ] T025 [P] [US1] Create `src/kosmos/tools/koroad/accident_hazard_search.py` — `koroad_accident_hazard_search` adapter handler. Input schema: `{adm_cd: str pattern=^[0-9]{10}$, year: int}`. Internal codebook maps `adm_cd` → KOROAD `siDo`+`guGun` with 2023 quirks (강원 42→51, 전북 45→52, 부천시 split) encapsulated here (FR-018, FR-019). Returns `LookupCollection`.
- [ ] T026 [P] [US1] Capture recorded fixture `tests/fixtures/koroad/accident_hazard_search_happy.json` via a `@pytest.mark.live` helper (run once, committed). Add `_error_invalid_params.json` fixture.
- [ ] T027 [US1] Register `koroad_accident_hazard_search` in `src/kosmos/tools/register_all.py` with bilingual `search_hint` (Korean: "교통사고 다발지역 · 위험구간 · 사망자수"; English: "accident hazard spot high-fatality zone"), `requires_auth=False`, `is_personal_data=False`, `is_concurrency_safe=True`, `cache_ttl_seconds=0`. Depends on T025.
- [ ] T028 [US1] Expose `resolve_location` and `lookup` as the LLM-visible tool set in the registry bootstrap — ensure introspection returns exactly these two plus pre-existing non-MVP tools (FR-001, SC-003). Depends on T023, T024.

**Checkpoint**: US1 acceptance scenarios 1–4 pass; SC-001 satisfied for KOROAD leg of the seed matrix.

---

## Phase 4: User Story 2 — PII-flagged adapter gated by Layer 3 auth_required (Priority: P2)

**Goal**: Register `nmc_emergency_search` with `is_personal_data=True` so Layer 3 gate short-circuits every fetch to `LookupError(reason="auth_required")` — zero upstream NMC HTTP calls in the full CI suite (SC-006).

**Independent Test**: `lookup(mode="fetch", tool_id="nmc_emergency_search", params={...})` returns `LookupError(reason="auth_required", retryable=False)`. Assert the httpx mock tape records zero NMC calls.

### Tests for User Story 2 ⚠️

- [ ] T029 [P] [US2] Integration test `tests/tools/nmc/test_emergency_search_auth_gate.py` — fetch returns `LookupError(reason="auth_required")` and a `respx` mock asserts `call_count == 0` for any `nmc.go.kr` URL pattern.
- [ ] T030 [P] [US2] Unit test `tests/tools/test_registry_invariant.py` — registering an adapter with `is_personal_data=True` and `requires_auth=False` raises `RegistrationError` at startup (FR-038, SC-005).
- [ ] T031 [P] [US2] Integration test `tests/tools/test_lookup_search.py::test_nmc_discoverable` — NMC MAY appear in `lookup(mode="search", query="응급실")` results with `required_params` reflecting the `auth_required` contract (US2 AS #2).

### Implementation for User Story 2

- [ ] T032 [P] [US2] Create `src/kosmos/tools/nmc/emergency_search.py` — `nmc_emergency_search` adapter handler. Input schema: `{lat: float, lon: float, limit: int}`. Handler body is a stub that raises `Layer3GateViolation` if ever invoked (should never reach it). Documented freshness SLO check (`hvidate > KOSMOS_NMC_FRESHNESS_MINUTES`) is NOT implemented in this epic — comment-only per spec FR-034.
- [ ] T033 [US2] Register `nmc_emergency_search` in `register_all.py` with `requires_auth=True`, `is_personal_data=True`, `is_concurrency_safe=False`, `cache_ttl_seconds=0`. Bilingual `search_hint` (Korean: "응급실 실시간 병상 · 응급의료센터"; English: "emergency room bed availability nearest ER"). Depends on T032.
- [ ] T034 [US2] Add fixture placeholder `tests/fixtures/nmc/auth_required_error.json` documenting the expected `LookupError` envelope shape (no HTTP tape required since zero calls are made).

**Checkpoint**: US2 acceptance scenarios 1–3 pass; SC-006 verified in CI; Layer 3 interface exercised end-to-end.

---

## Phase 5: User Story 3 — BM25 retrieval gate with eval quality guarantee (Priority: P2)

**Goal**: The 30-query evaluation set runs in CI, gating merges on `recall@5 ≥ 80%` (pass), `[60%, 80%)` (warn), `< 60%` (fail). Machine-readable report for PR comment action.

**Independent Test**: `uv run python -m kosmos.eval.retrieval eval/retrieval_queries.yaml` against the 4 seed adapters, assert `recall@5 ≥ 0.80` and `recall@1 ≥ 0.50` on the committed eval set; verify JSON report written to `.eval-artifacts/retrieval.json`.

### Tests for User Story 3 ⚠️

- [ ] T035 [P] [US3] Unit test `tests/tools/test_bm25_retrieval.py` — BM25 scores are strictly positive for matching terms, zero for disjoint terms, deterministic across 10 repeated runs (FR-013).
- [ ] T036 [P] [US3] Unit test `tests/tools/test_lookup_topk_clamp.py` — `top_k=None → 5`, `top_k=0 → 1`, `top_k=99 → min(20, len(registry))`, registry size 4 → `effective_top_k=4` (FR-009, US3 AS #2, AS #4).
- [ ] T037 [P] [US3] Integration test `tests/eval/test_retrieval_gate.py` — runs the eval harness on the 30-query set; asserts `recall@5 ≥ 0.80` on the seed adapter registry.

### Implementation for User Story 3

- [ ] T038 [US3] Populate `eval/retrieval_queries.yaml` with 30 queries — coverage per research.md §5: 10 KOROAD, 7 KMA, 7 HIRA, 6 NMC. Each entry: `{query: str, expected_tool_id: str, notes?: str}`.
- [ ] T039 [US3] Create `src/kosmos/eval/__init__.py` and `src/kosmos/eval/retrieval.py` — CLI entry point `python -m kosmos.eval.retrieval <queries.yaml>` that loads the seed registry, runs `lookup(mode="search")` per query, computes `recall@1` and `recall@5`, writes JSON report to `.eval-artifacts/retrieval.json`, exits with code 0 (pass ≥ 0.80), code 1 (warn [0.60, 0.80)), code 2 (fail < 0.60) (FR-011, FR-012).
- [ ] T040 [US3] Add CI job in `.github/workflows/eval.yml` — runs `uv run python -m kosmos.eval.retrieval eval/retrieval_queries.yaml` on every PR; uploads `.eval-artifacts/retrieval.json` as artifact; posts summary via job annotation.

**Checkpoint**: US3 acceptance scenarios 1–4 pass; SC-002 satisfied; CI retrieval gate active.

---

## Phase 6: User Story 4 — #288 geocoding refactor behavioral equivalence (Priority: P3)

**Goal**: Remove `address_to_region` and `address_to_grid` from the LLM-visible surface without a compat shim. Preserve adm-code resolution equivalence; fold LCC grid projection into a KMA-adapter-internal helper.

**Independent Test**: Record pre-refactor fixture tape; post-refactor assertions: (a) `address_to_region` / `address_to_grid` absent from registry and both return `LookupError(unknown_tool)` on `lookup.fetch`; (b) `resolve_location(want="adm_cd")` produces exact `adm_cd` match on N pre-refactor inputs; (c) KMA adapter LCC grid `(nx, ny)` matches pre-refactor within ±1 cell.

### Tests for User Story 4 ⚠️

- [ ] T041 [P] [US4] Regression test `tests/tools/test_legacy_geocoding_removed.py` — asserts `address_to_region` and `address_to_grid` are not in `registry.all_tools()`; `lookup(mode="fetch", tool_id="address_to_region")` → `LookupError(reason="unknown_tool")` (FR-027, FR-030, FR-031, US4 AS #3).
- [ ] T042 [P] [US4] Behavioral parity test `tests/tools/test_resolve_admcd_parity.py` — for each entry in `tests/fixtures/legacy/address_to_region_baseline.json`, `resolve_location(query=..., want="adm_cd")` returns the exact `adm_cd` from the baseline (US4 AS #1, SC-007).
- [ ] T043 [P] [US4] LCC projection parity test `tests/tools/kma/test_lcc_projection_parity.py` — for each entry in `tests/fixtures/legacy/address_to_grid_baseline.json`, the KMA adapter's internal projection produces `(nx, ny)` within ±1 cell of baseline (US4 AS #2, SC-008).

### Implementation for User Story 4

- [ ] T044 [US4] Create the pre-refactor baseline fixtures `tests/fixtures/legacy/address_to_region_baseline.json` and `address_to_grid_baseline.json` by running the legacy tools one last time with `@pytest.mark.live` (commit before removal).
- [ ] T045 [US4] Create `src/kosmos/tools/kma/projection.py` with `latlon_to_lcc(lat: float, lon: float) -> tuple[int, int]` (Lambert Conformal Conic with KMA's canonical constants). `out_of_domain` → raise typed exception caught by envelope (FR-029).
- [ ] T046 [US4] Create `src/kosmos/tools/kma/forecast_fetch.py` — `kma_forecast_fetch` adapter. Input: `{lat: float, lon: float, base_date: str, base_time: str}`. Internally calls `latlon_to_lcc` then the KMA endpoint. Returns `LookupTimeseries` with semantic field names (`temperature_c`, `pop_pct`, `precipitation_mm`, `interval="hour"`). `invalid_params` on unsupported `base_time`.
- [ ] T047 [P] [US4] Capture `tests/fixtures/kma/forecast_fetch_happy.json` and `_error_invalid_base_time.json` fixtures.
- [ ] T048 [US4] Register `kma_forecast_fetch` in `register_all.py` with `requires_auth=False`, `is_personal_data=False`, `is_concurrency_safe=True`, bilingual `search_hint` ("단기예보 날씨 기온 강수 · short-term weather forecast temperature precipitation"). Depends on T046.
- [ ] T049 [US4] Delete `address_to_region` and `address_to_grid` from the registry — remove any `register_all.py` calls, remove the source modules under `src/kosmos/tools/geocoding/legacy/` (if present), delete their test files. Depends on T044 (fixtures captured first).
- [ ] T050 [US4] Move the adm-code lookup logic (formerly in `address_to_region`) into `src/kosmos/tools/geocoding/sgis.py` and/or `juso.py` as a backend method consumed by `resolve_location` — no public tool surface (FR-028).

**Checkpoint**: US4 acceptance scenarios 1–3 pass; SC-007, SC-008 verified; no compat shim remains.

---

## Phase 7: User Story 5 — Adapter registration stability under registry growth (Priority: P3)

**Goal**: Prove `lookup` / `resolve_location` source code does not change when new adapters are added. A synthetic fifth adapter registered in a test-only fixture appears in search results without touching production code.

**Independent Test**: In-test adapter registration + `lookup(mode="search", query="<matching hint>")` returns it; also registers `hira_hospital_search` as the 4th real seed to round out the `collection`+`coord+radius` quadrant.

### Tests for User Story 5 ⚠️

- [ ] T051 [P] [US5] Integration test `tests/tools/test_registry_extensibility.py` — registers a synthetic `test_only_synthetic_adapter` with a unique `search_hint`, calls `lookup(mode="search", query=<matching>)`, asserts it appears as a candidate. No production file outside test fixtures touched (US5 AS #1).
- [ ] T052 [P] [US5] Integration test `tests/tools/test_bm25_tie_break.py` — two adapters with identical scores produce stable ordering across 100 repeated calls (US5 AS #2, FR-013).
- [ ] T053 [P] [US5] Integration test `tests/tools/hira/test_hospital_search.py` — `lookup(mode="fetch", tool_id="hira_hospital_search", params={"xPos":127.028,"yPos":37.498,"radius":2000})` returns `LookupCollection` with `ykiho`, `yadmNm`, distance fields from recorded fixture.

### Implementation for User Story 5

- [ ] T054 [P] [US5] Create `src/kosmos/tools/hira/hospital_search.py` — `hira_hospital_search` adapter. Input schema: `{xPos: float, yPos: float, radius: int (max 10000)}`. Returns `LookupCollection` with HIRA hospital records.
- [ ] T055 [P] [US5] Capture `tests/fixtures/hira/hospital_search_happy.json` and `_error_invalid_radius.json` fixtures.
- [ ] T056 [US5] Register `hira_hospital_search` in `register_all.py` with `requires_auth=False`, `is_personal_data=False`, `is_concurrency_safe=True`, bilingual `search_hint` ("병원 병상 · 의료기관 위치 반경 검색 · hospital locator within radius"). Depends on T054.
- [ ] T057 [US5] Add a test-only registration helper `tests/tools/_synthetic_adapter.py` providing `build_synthetic_tool(hint: str)` factory used by T051 without touching `register_all.py`.

**Checkpoint**: US5 acceptance scenarios 1–3 pass; extensibility proven; all 4 seed adapters now registered.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and quickstart validation across all stories.

- [ ] T058 [P] Update `docs/tool-adapters.md` — add the NMC `is_personal_data=True` interface-only pattern and the Layer 3 gate contract to the adapter author checklist.
- [ ] T059 [P] Add `docs/adr/ADR-NNN-bm25-retrieval-gate.md` documenting the `rank_bm25 + kiwipiepy` choice, Q1 rejection of mecab-ko, and the 30-query eval gate.
- [ ] T060 [P] Extend `CLAUDE.md` Active Technologies section to note the two new tools (`resolve_location`, `lookup`) as the LLM-facing surface.
- [ ] T061 [P] Add `ruff`/`mypy` passes for the new modules (`resolve_location.py`, `lookup.py`, `envelope.py`, `tokenizer.py`, `bm25_index.py`, `eval/retrieval.py`) with no new warnings.
- [ ] T062 Run `uv run pytest -q` full suite — all tests pass, zero live-API calls (verify with `pytest --collect-only -m live` count matches fixture-capture tasks only).
- [ ] T063 Run quickstart.md §2 walkthrough end-to-end against the stub LLM harness — verify every envelope in `quickstart.md` matches actual output byte-for-byte on the `kind` + `reason` + `source` discriminators.
- [ ] T064 Verify `pyproject.toml` dependencies match the spec manifest exactly (`httpx`, `pydantic`, `pydantic-settings`, `rank_bm25`, `kiwipiepy`) — no unlisted additions slipped in (SC-009).

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** — no dependencies.
- **Phase 2 (Foundational)** — depends on Phase 1; **blocks** Phases 3–7.
- **Phases 3–7 (User Stories)** — each depends on Phase 2; can run in parallel across teams.
- **Phase 8 (Polish)** — depends on Phases 3–7.

### Cross-story dependencies

- US1 is the MVP floor — US2–US5 are additive increments but assume US1's `resolve_location` + `lookup` facade from T023, T024, T028.
- US3 eval gate (T037–T040) assumes US1+US2+US5 adapters are registered (registry of 4 needed for realistic recall numbers). If US5 slips, US3 runs against 3 adapters with a warning annotation.
- US4 (`kma_forecast_fetch`) shares `register_all.py` with US1 (KOROAD), US2 (NMC), US5 (HIRA) — serialize the register_all edits or resolve conflicts at rebase time.

### Within each story

- Tests (Txx–Txx under "Tests for User Story N") MUST be written and failing before the corresponding implementation tasks.
- Schemas → adapters → registration → envelope wiring.
- Fixture capture (`@pytest.mark.live`) happens once, results committed; subsequent runs are offline.

### Parallel opportunities

- **Phase 1**: T002–T004 in parallel.
- **Phase 2**: T005–T008 in parallel (models), T010–T011 in parallel (tokenizer + index), T014 in parallel with T016.
- **Phase 3 (US1)**: T017–T022 (tests) fully parallel; T025–T026 parallel with T023–T024.
- **Phase 4 (US2)**: T029–T031 parallel; T032 parallel with anything else.
- **Phase 5 (US3)**: T035–T037 parallel; T038 standalone.
- **Phase 6 (US4)**: T041–T043 parallel; T045 + T047 parallel with T044.
- **Phase 7 (US5)**: T051–T055 parallel.
- **Phase 8**: T058–T061 fully parallel; T062–T064 serial.

---

## Parallel Example: User Story 1 tests

```bash
# All six US1 tests can run simultaneously — different files, different fixtures:
pytest tests/tools/contracts/test_resolve_location_schema.py \
       tests/tools/contracts/test_lookup_schema.py \
       tests/tools/test_resolve_location.py \
       tests/tools/test_lookup_search.py \
       tests/tools/test_lookup_fetch.py \
       tests/tools/test_envelope_normalization.py -n auto
```

## Parallel Example: Phase 2 foundational models

```bash
# T005, T006, T007, T008 all touch src/kosmos/tools/models.py — ⚠️ SERIALIZE these.
# But T010 (tokenizer.py), T011 (bm25_index.py), T014 (envelope.py), T016 (settings.py) are independent files → parallel.
```

---

## Implementation Strategy

### MVP scope (User Story 1 only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational) — **blocking**.
3. Complete Phase 3 (US1) — KOROAD end-to-end.
4. STOP and validate against quickstart.md Pattern A.
5. Demo-ready MVP.

### Incremental delivery

- MVP (US1) → `koroad_accident_hazard_search` working end-to-end → demoable.
- +US2 → NMC Layer 3 gate proof → constitutional §II fully exercised.
- +US3 → BM25 eval gate live in CI → quality guarantee locked.
- +US4 → #288 refactor + KMA adapter → seed matrix half-done.
- +US5 → HIRA adapter + extensibility proof → all 4 seed adapters + Pattern D quickstart green.

### Parallel team strategy

- Dev A: Phase 2 foundational (T005–T016) then US1.
- Dev B (starts after Phase 2): US2 (auth gate) + US3 (eval gate) — both small, both use Phase 2 primitives.
- Dev C (starts after Phase 2): US4 (KMA + #288 refactor) — the refactor surface.
- Dev D (starts after US1 Phase 3 lands): US5 (HIRA + extensibility) — depends on the registration pattern from US1.

---

## Notes

- [P] markers = different files, no incomplete-task dependencies.
- [Story] labels map tasks to `spec.md` user stories for traceability and checkpoint gating.
- Frozen discriminator names from `docs/design/mvp-tools.md §5.4` are binding — any variant rename requires an ADR.
- Every `LookupError` reason value is drawn from the closed enum in T009 — no ad-hoc strings.
- Commit after each task or logical group; PR boundary is per user story (5 PRs total + Phase 1/2 setup PR + Phase 8 polish PR).
- `@pytest.mark.live` tests are run once per fixture refresh and skipped in CI (`pytest -m "not live"`).
- Do NOT reintroduce `address_to_region` / `address_to_grid` as compat shims (FR-031, spec §Out of Scope Permanent).
