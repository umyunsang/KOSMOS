# Feature Specification: MVP Main-Tool — `lookup` + `resolve_location`

**Feature Branch**: `022-mvp-main-tool`
**Created**: 2026-04-16
**Status**: Draft
**Input**: Epic #507 — MVP Main-Tool: `lookup` + `resolve_location` + 4 seed adapters (KOROAD/KMA/HIRA/NMC) + BM25 retrieval gate + #288 geocoding 흡수 refactor. Canonical design frozen at `docs/design/mvp-tools.md` (2026-04-16). All 12 design decisions (D1–D7, Q1–Q5) are closed and MUST NOT be re-opened in this spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End-to-end citizen query through the two-tool surface (Priority: P1)

A citizen asks the assistant a natural-language question that spans location resolution and a public-data lookup (e.g., "어제 종로구 교통사고 위험지역 알려줘"). The model sees exactly **two** tools — `resolve_location` for any place-to-identifier conversion and `lookup` for retrieving/fetching public data — and must orchestrate the full turn through them without the model ever seeing adapter-specific tool names.

**Why this priority**: This is the core MVP contract. If the two-tool surface cannot complete a realistic citizen query end-to-end, nothing else in the epic delivers value. Every deferred capability (scenario graph, swarm orchestration, TUI) depends on this surface being stable first.

**Independent Test**: Drive a scripted conversation against a stub LLM that (a) calls `resolve_location(query="종로구", want=["adm_code","point"])`, (b) calls `lookup(mode="search", query="교통사고 위험지역", top_k=3)`, (c) calls `lookup(mode="fetch", tool_id="koroad_accident_hazard_search", params={...})`, and verify the final `LookupCollection` envelope contains hazard records. Runs fully against recorded fixtures — no live `data.go.kr` calls, no LLM provider calls in CI.

**Acceptance Scenarios**:

1. **Given** an empty tool-loop session, **When** the LLM introspects its tool list, **Then** it sees exactly `resolve_location` and `lookup` (plus any pre-existing non-MVP tools already in the registry) and none of the four seed adapters appear as top-level tools.
2. **Given** a citizen query requiring location resolution, **When** the model calls `resolve_location(query="종로구", want=["adm_code","point"])`, **Then** it receives a `ResolveBundle` containing both an `AdmCodeResult` and a `CoordResult` drawn from the appropriate resolver backends, with matching `source` provenance.
3. **Given** a resolved location, **When** the model calls `lookup(mode="search", query="교통사고 위험지역", top_k=3)`, **Then** it receives a ranked list of `AdapterCandidate` entries with `tool_id`, `score`, `required_params`, `search_hint` echo, and `why_matched` rationale — and no adapter is invoked.
4. **Given** a selected candidate, **When** the model calls `lookup(mode="fetch", tool_id="koroad_accident_hazard_search", params={...})`, **Then** the response is a `LookupCollection` (the frozen discriminator from §5.4 of the design doc) containing typed records plus a `meta` block with `source`, `fetched_at`, `request_id`, and `elapsed_ms`.

---

### User Story 2 - PII-flagged adapter gated by Layer 3 auth_required (Priority: P2)

A citizen asks for the nearest open emergency room (`nmc_emergency_search`). The adapter is flagged `is_personal_data=True` and `requires_auth=True`. The Layer 3 permission gauntlet is not fully implemented yet in this epic, so the adapter MUST refuse with a structured `LookupError(reason="auth_required")` envelope rather than silently returning data or crashing.

**Why this priority**: The canonical design freezes NMC as the interface-only harness that proves the permission-pipeline contract before the pipeline itself ships (Q4 decision). Shipping the four-adapter matrix without this gate would mean NMC either leaks PII or cannot be listed at all — both block the MVP release.

**Independent Test**: Call `lookup(mode="fetch", tool_id="nmc_emergency_search", params={lat:…, lon:…, radius_m:3000})` against the stub; assert the response is a `LookupError` with `reason="auth_required"`, a human-readable `message`, and NO upstream NMC HTTP call is recorded in the fixture tape.

**Acceptance Scenarios**:

1. **Given** `nmc_emergency_search` is registered, **When** any `lookup(mode="fetch")` call targets it, **Then** the response is `LookupError(reason="auth_required")` with no HTTP call made to the NMC endpoint.
2. **Given** `lookup(mode="search", query="응급실")` is called, **When** the BM25 gate scores adapters, **Then** `nmc_emergency_search` MAY appear as a candidate (it is discoverable) and each candidate's `required_params` signals that `auth_required` will be enforced at fetch time.
3. **Given** NMC's TTL SLO of 30 minutes on `hvidate`, **When** the Layer 3 gate is later lifted by a future epic, **Then** freshness-stale responses MUST return `LookupError(reason="stale_data")` rather than flowing through (this epic only wires the gate interface; the SLO is documented for the follow-on).

---

### User Story 3 - BM25 retrieval gate with eval quality guarantee (Priority: P2)

Adapter discovery is not a hard keyword match. The model asks `lookup(mode="search", ...)` with a Korean free-text query and receives the top-k adapters ranked by BM25 over each adapter's bilingual `search_hint` field. A 30-query evaluation set encodes the "acceptable discovery quality" contract: recall@5 ≥ 80% passes, [60%, 80%) emits a warning, <60% fails.

**Why this priority**: The model's only visibility into the adapter registry is via `lookup(mode="search")`. If retrieval quality is untracked, the four-adapter matrix silently degrades as registry grows, and future adapter additions have no quality gate. The eval set is cheap to maintain and catches regressions before merge.

**Independent Test**: Run the 30-query eval harness against the four seed adapters, assert `recall@5 ≥ 80%` for the seed corpus, and verify the CI job produces a machine-readable report with per-query rank and aggregate recall metrics.

**Acceptance Scenarios**:

1. **Given** the registry contains the four seed adapters plus any pre-existing tools, **When** `lookup(mode="search", query="교통사고 위험지역")` runs, **Then** `koroad_accident_hazard_search` appears in the top-5 results with BM25 score > 0.
2. **Given** `KOSMOS_LOOKUP_TOPK=3` is set, **When** `lookup(mode="search", top_k=10)` is called, **Then** the effective `top_k` is clamped to the env-configured default (3) or the explicit per-call `top_k` (whichever applies per §5.2 of the design doc), and the clamp bounds `[1, 20]` are enforced.
3. **Given** the 30-query eval set, **When** CI runs the eval harness, **Then** the report writes machine-readable output to a known path and the job fails if recall@5 falls below 60% or warns if it falls into [60%, 80%).
4. **Given** registry size < 5, **When** `lookup(mode="search")` runs with default top_k, **Then** the effective top_k adapts via `min(default, len(registry))` so empty-candidate responses never occur on under-populated registries.

---

### User Story 4 - #288 geocoding refactor behavioral equivalence (Priority: P3)

Spec #288 previously introduced `address_to_region` and `address_to_grid` as two stand-alone tools visible to the model. This epic removes both from the LLM surface and folds their behavior into `resolve_location` (for the adm-code branch) and into the KMA adapter's internal projection helper (for the grid branch). Existing callers of the old surface MUST continue to receive the same resolved data through the new surface — not identical APIs, but equivalent outcomes.

**Why this priority**: Any regression here breaks already-shipped citizen flows that depend on address-to-region resolution. This is a refactor with a clear correctness bar, not a new capability, so it sits below the new-surface stories but above stability polish.

**Independent Test**: Record a fixture tape from the pre-refactor `address_to_region` / `address_to_grid` calls; after refactor, drive the same user inputs through `resolve_location(query=..., want=["adm_code"])` and through the KMA adapter respectively, and assert the resolved outputs (adm_code, sido, gugun / LCC grid x,y) match within documented tolerance.

**Acceptance Scenarios**:

1. **Given** a fixture of N historical address inputs, **When** each is routed through `resolve_location(want=["adm_code"])`, **Then** the resolved adm_code, sido, and gugun match the #288 baseline for every case (tolerance: exact equality on adm_code).
2. **Given** a fixture of grid-requiring weather queries, **When** the KMA adapter is invoked with a resolved `CoordResult`, **Then** its internal LCC projection produces `(nx, ny)` values matching the #288 baseline within ±1 grid cell tolerance.
3. **Given** the old registry manifest, **When** this epic is merged, **Then** `address_to_region` and `address_to_grid` are absent from the LLM-visible tool list and any attempt to invoke them by id returns `LookupError(reason="unknown_tool")` with no backward-compat shim.

---

### User Story 5 - Adapter registration stability under registry growth (Priority: P3)

The `GovAPITool` registration contract is frozen for this epic: every adapter declares typed `input_schema`, `output_schema`, bilingual `search_hint`, fail-closed defaults (`requires_auth`, `is_personal_data`, `is_concurrency_safe`, `cache_ttl_seconds`), and a `handler` coroutine. Adding a new adapter in a future epic must not require changing `lookup` or `resolve_location` themselves — only registry entries.

**Why this priority**: The MVP lives or dies by "drop-in adapter" mechanics. If future adapter work touches `lookup`'s core code path, the architecture leaks. This story codifies the closed-for-modification contract.

**Independent Test**: Write a synthetic fifth adapter in a test-only fixture, register it, call `lookup(mode="search", query="<matching hint>")`, and assert it appears as a candidate without any change to production source files under the `lookup`/`resolve_location` module tree.

**Acceptance Scenarios**:

1. **Given** a test-only synthetic adapter whose `search_hint` matches a test query, **When** the test registers it and calls `lookup(mode="search", query=...)`, **Then** it appears in the ranked candidates with the correct `tool_id` and `required_params`.
2. **Given** two adapters with identical BM25 scores, **When** they tie, **Then** the ranking is stable and deterministic across repeated calls in the same process.
3. **Given** an adapter declares `is_personal_data=True`, **When** it is registered, **Then** `requires_auth` MUST also be true (fail-closed pairing) or registration fails at startup with a clear error.

---

### Edge Cases

- **Ambiguous location**: `resolve_location(query="강남")` matches both 서울 강남구 and 인천 남동구 강남동 — resolver MUST return a `ResolveBundle` with ranked candidates and surface the ambiguity rather than silently picking the highest-scoring match.
- **Empty registry (test environment)**: `lookup(mode="search")` with 0 adapters registered MUST return an empty `candidates` list and `meta.reason="empty_registry"`, not a crash.
- **Adapter handler timeout**: Any adapter coroutine exceeding the per-call budget (default 10s, configurable later) MUST return `LookupError(reason="timeout")` with the partial `meta` block intact.
- **Upstream 5xx**: The adapter wraps the error into `LookupError(reason="upstream_unavailable")`; the retry matrix is deferred (tracked below) and this epic only requires wrapping, not retry.
- **Invalid `tool_id` on fetch**: `lookup(mode="fetch", tool_id="nonexistent")` returns `LookupError(reason="unknown_tool")` with no side effects.
- **Param validation failure**: Fetch-mode `params` that fail the adapter's Pydantic `input_schema` return `LookupError(reason="invalid_params")` with the validation detail in `meta.errors`.
- **KMA grid off-domain**: Coordinates outside the Korean LCC grid domain return `LookupError(reason="out_of_domain")`.
- **NMC freshness SLO (post-gate)**: Documented now, enforced when the Layer 3 gate is lifted — `hvidate` older than `KOSMOS_NMC_FRESHNESS_MINUTES` minutes returns `LookupError(reason="stale_data")`.
- **Discriminator mismatch**: An adapter handler returning a response whose `kind` field does not match a member of the frozen `LookupRecord | LookupCollection | LookupTimeseries | LookupError` union MUST be rejected at the envelope-normalization boundary with a typed error rather than surfaced to the model.

## Requirements *(mandatory)*

### Functional Requirements

#### Tool surface (LLM-visible)

- **FR-001**: The system MUST expose exactly two MVP tools to the LLM: `resolve_location` and `lookup`. No seed adapter may be registered as an LLM-visible top-level tool.
- **FR-002**: `resolve_location` MUST accept `query: str` and a scalar `want: Literal["coords","adm_cd","coords_and_admcd","road_address","jibun_address","poi","all"]` (default `"coords_and_admcd"`) plus an optional `near: tuple[float, float]` tiebreaker, and return a discriminated union `CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError` on a `kind` discriminator. Field shape and enum values are binding per `contracts/resolve_location.input.schema.json`.
- **FR-003**: `resolve_location` MUST never expose Kakao, JUSO, or SGIS as separate tools — the resolver backends are selected internally and reported via the `source` field of each result.
- **FR-004**: `lookup` MUST accept a `mode: Literal["search","fetch"]` discriminator and route to the retrieval gate (search) or the adapter invoker (fetch).
- **FR-005**: `lookup(mode="search")` MUST accept `query: str` and optional `top_k: int` and return `LookupSearchResult` containing a ranked list of `AdapterCandidate` entries (`tool_id`, `score`, `required_params`, `search_hint`, `why_matched`).
- **FR-006**: `lookup(mode="fetch")` MUST accept `tool_id: str` and `params: dict` and return a discriminated union `LookupRecord | LookupCollection | LookupTimeseries | LookupError` on a `kind` discriminator — these four frozen names from §5.4 of the design doc are binding; the Epic body's `Point/List/Detail` paraphrase is NOT authoritative.
- **FR-007**: Both tools MUST use Pydantic v2 models exclusively for I/O; `Any` is forbidden in the schema.

#### Retrieval gate

- **FR-008**: The search mode MUST use BM25 ranking (via `rank_bm25`) over each adapter's bilingual `search_hint` string, tokenized by `kiwipiepy>=0.17` (Korean morpheme tokenizer).
- **FR-009**: `top_k` MUST default to `min(KOSMOS_LOOKUP_TOPK, len(registry))`, with `KOSMOS_LOOKUP_TOPK` defaulting to 5 and clamped to `[1, 20]`.
- **FR-010**: The 30-query evaluation set MUST reside at `eval/retrieval_queries.yaml` with a documented schema (query text, expected `tool_id`, optional notes).
- **FR-011**: CI MUST run the eval harness and fail the job when `recall@5 < 60%`, emit a warning annotation when `60% ≤ recall@5 < 80%`, and pass silently when `recall@5 ≥ 80%`.
- **FR-012**: The eval harness MUST emit a machine-readable report (per-query rank, aggregate recall@k) to a known path for the PR comment action.
- **FR-013**: The ranking MUST be stable and deterministic for ties — repeated calls with the same query and registry MUST produce the same ordering.

#### Envelope normalization

- **FR-014**: Every `lookup(mode="fetch")` response envelope MUST include a `meta` block containing `source`, `fetched_at` (UTC ISO-8601), `request_id` (UUID), and `elapsed_ms`.
- **FR-015**: Handler responses that do not match a member of the frozen discriminated union MUST be rejected at the envelope-normalization boundary with a typed error rather than reaching the model.
- **FR-016**: All `LookupError` values MUST carry a `reason` enum (`auth_required | stale_data | timeout | upstream_unavailable | unknown_tool | invalid_params | out_of_domain | empty_registry`) and a human-readable `message`.
- **FR-017**: No adapter may bypass envelope normalization by raising exceptions out of its handler boundary — exceptions MUST be caught and converted to `LookupError` at the invoker layer.

#### Four seed adapters

- **FR-018**: `koroad_accident_hazard_search` MUST be registered with a code-pair `input_schema` (sido_code + gugun_code) and return a `LookupCollection` of hazard records.
- **FR-019**: The KOROAD adapter's internal codebook MUST handle the 2023 사도·구군 code quirks (강원 42→51, 전북 45→52, 부천시 split history) with year-aware resolution logic encapsulated inside the adapter.
- **FR-020**: `kma_forecast_fetch` MUST accept a resolved `CoordResult` (lat/lon) and internally project to LCC grid `(nx, ny)` before calling the KMA endpoint, returning a `LookupTimeseries`.
- **FR-021**: `hira_hospital_search` MUST accept `(lat, lon, radius_m)` and return a `LookupCollection` of hospital records; `radius_m` MUST be validated to a reasonable upper bound at the schema layer.
- **FR-022**: `nmc_emergency_search` MUST be registered with `is_personal_data=True` and `requires_auth=True` and MUST return `LookupError(reason="auth_required")` without making any upstream HTTP call during this epic.
- **FR-023**: Every seed adapter MUST ship happy-path AND error-path tests with recorded fixtures; no test may call live `data.go.kr` endpoints in CI.
- **FR-024**: Every seed adapter MUST declare fail-closed defaults (`requires_auth`, `is_personal_data`, `is_concurrency_safe=False`, `cache_ttl_seconds=0`) in its `GovAPITool` registration.

#### Layer 3 auth gate (interface-only)

- **FR-025**: The envelope-normalization layer MUST check `requires_auth` and `is_personal_data` on the resolved adapter and short-circuit to `LookupError(reason="auth_required")` BEFORE invoking the adapter handler.
- **FR-026**: The auth-gate short-circuit MUST be unconditional in this epic — no mode flag, admin override, or test shortcut may bypass it (per constitution Principle II, bypass-immune checks).

#### #288 refactor

- **FR-027**: `address_to_region` and `address_to_grid` MUST be removed from the LLM-visible tool registry.
- **FR-028**: The adm-code resolution behavior MUST be available through `resolve_location(want=["adm_code"])` with equivalent outputs to the #288 baseline.
- **FR-029**: The LCC grid projection logic MUST be moved into a KMA-adapter-internal helper and MUST NOT be exposed as a tool.
- **FR-030**: Attempting to invoke either removed tool_id via `lookup(mode="fetch", tool_id="address_to_region")` MUST return `LookupError(reason="unknown_tool")`.
- **FR-031**: The refactor MUST NOT introduce a backward-compat shim for the removed tool names.

#### Environment & configuration

- **FR-032**: All external keys MUST be read from `KOSMOS_`-prefixed env vars: `KOSMOS_KAKAO_REST_KEY`, `KOSMOS_JUSO_CONFM_KEY`, `KOSMOS_SGIS_KEY`, `KOSMOS_SGIS_SECRET`, `KOSMOS_DATA_GO_KR_API_KEY`.
- **FR-033**: `KOSMOS_LOOKUP_TOPK` MUST default to 5 and be clamped to `[1, 20]`.
- **FR-034**: `KOSMOS_NMC_FRESHNESS_MINUTES` MUST default to 30 and be clamped to `[1, 1440]` (documented but only enforced once the Layer 3 gate is lifted — see deferred item).

#### Behavioral guarantees

- **FR-035**: `resolve_location` MUST report the resolver backend (`kakao | juso | sgis`) in every successful result's `source` field.
- **FR-036**: When multiple resolver backends agree, the `ResolveBundle` MUST include provenance for each contributing backend.
- **FR-037**: Every adapter handler MUST be an `async` coroutine; the invoker MUST enforce a per-call timeout budget (exceeded → `LookupError(reason="timeout")`).
- **FR-038**: Registry registration MUST fail at startup if an adapter declares `is_personal_data=True` without also declaring `requires_auth=True`.

### Key Entities

- **ResolveLocationInput**: `{query: str, want: list[Literal["point","adm_code","address","poi"]]}` — input to the single location-resolution tool.
- **ResolveLocationOutput**: Discriminated union `CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError` on `kind`. Bundles carry multi-backend provenance.
- **LookupSearchInput / LookupFetchInput**: Two input shapes behind the `mode` discriminator of `lookup`. Search takes `query + top_k`; fetch takes `tool_id + params`.
- **LookupOutput**: `LookupSearchResult | LookupRecord | LookupCollection | LookupTimeseries | LookupError` on `kind`. The four non-search members are the frozen §5.4 discriminator names.
- **AdapterCandidate**: Search-result entry — `tool_id, score, required_params, search_hint, why_matched`.
- **GovAPITool**: The registry record — `tool_id, description, search_hint (bilingual), input_schema, output_schema, requires_auth, is_personal_data, is_concurrency_safe, cache_ttl_seconds, rate_limit_per_minute, handler`.
- **EvalRetrievalSet**: 30-query YAML at `eval/retrieval_queries.yaml`, schema = `{query: str, expected_tool_id: str, notes?: str}`.
- **Layer3AuthGate**: The envelope-layer short-circuit that converts `(requires_auth=True, no session identity)` into `LookupError(reason="auth_required")` before handler invocation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a realistic citizen query, the two-tool surface completes an end-to-end `resolve → search → fetch` cycle and returns a typed envelope for at least 3 of the 4 seed adapters (KOROAD, KMA, HIRA) in CI fixtures. NMC returns `auth_required` as designed.
- **SC-002**: The 30-query eval harness achieves `recall@5 ≥ 80%` on the seed corpus at merge time.
- **SC-003**: No seed adapter is visible as a top-level tool to the LLM — the tool-introspection surface lists exactly `resolve_location` and `lookup` (plus any pre-existing non-MVP tools).
- **SC-004**: 100% of `lookup(mode="fetch")` responses across test fixtures conform to the frozen discriminator names `LookupRecord | LookupCollection | LookupTimeseries | LookupError`.
- **SC-005**: 0 adapter responses in CI bypass envelope normalization (measured by assertion coverage in fixture replays).
- **SC-006**: `nmc_emergency_search` makes 0 upstream HTTP calls in the full CI test suite — verified by fixture tape inspection.
- **SC-007**: The #288 refactor preserves adm-code resolution equivalence on 100% of pre-refactor fixture cases.
- **SC-008**: KMA grid projection matches the #288 baseline within ±1 grid cell on 100% of fixture cases.
- **SC-009**: No `print()` calls, no hardcoded keys, and no new runtime dependencies outside the spec manifest (`httpx`, `pydantic`, `pydantic-settings`, `rank_bm25`, `kiwipiepy`) appear in the merged diff.
- **SC-010**: Every deferred item in the Scope Boundaries section either has a GitHub issue number or is marked `NEEDS TRACKING` for `/speckit-taskstoissues` to resolve; zero free-text "future epic" references appear elsewhere in the spec.

## Assumptions

- Adapter `search_hint` strings are authored bilingually (Korean + English keywords in one field) — this is already required by the tool-adapter checklist in `docs/tool-adapters.md`.
- The session/identity model that Layer 3 will later consume is out of scope for this epic; the gate only reads `requires_auth` / `is_personal_data` from the adapter declaration and short-circuits.
- The BM25 retrieval library (`rank_bm25`) and Korean tokenizer (`kiwipiepy>=0.17`) are acceptable new dependencies and will be added in this spec's PR per the dependency-change rule in `AGENTS.md`.
- The `data.go.kr` shared key (`KOSMOS_DATA_GO_KR_API_KEY`) remains valid across KOROAD, KMA, and HIRA — this matches the KOROAD Portal reference memory.
- Recorded fixtures exist or can be captured once (marked `@pytest.mark.live`) for each adapter's happy and error paths.
- The FriendliAI K-EXAONE provider is Tier 1 (60 RPM) as of 2026-04-15 — sufficient for eval-harness smoke tests, though the eval harness is not expected to call the live LLM in CI.
- The Kakao REST key naming follows the spec `KOSMOS_KAKAO_REST_KEY` (not a prior shorter variant); any existing older naming is migrated in this epic.
- `resolve_location` ambiguity handling returns a ranked bundle rather than erroring — consumers decide how to disambiguate.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **LLM-visible adapter tools**: Individual adapters are NEVER LLM-visible — the two-tool facade is the architectural contract per `docs/vision.md`.
- **Live `data.go.kr` traffic in CI**: Permanently forbidden per constitution IV.
- **Backward-compatibility shim for removed `address_to_*` tools**: No shim is provided; callers migrate to `resolve_location` — per constitution's aversion to dead-code preservation.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Full Layer 3 permission gauntlet (7-step pipeline, session identity, consent ledger) | MVP only needs the `auth_required` short-circuit interface; the full gauntlet is a separate epic per `docs/vision.md § Layer 3` | Layer 3 Permission Pipeline epic | #16 |
| NMC freshness SLO enforcement (`stale_data` reason + `hvidate` check) | Requires the Layer 3 gate to be lifted first; documented now for continuity | NMC live-data enablement epic | #573 |
| Retry matrix for upstream 5xx / transient failures | MVP wraps errors but does not retry; retry policy is part of Error Recovery layer | Layer 6 Error Recovery epic | #574 |
| Scenario graph / multi-turn planning | Scenario-level orchestration is a separate layer above the two-tool surface | Scenario Graph / Agent Swarm epic | #575 |
| Agent Swarm / orchestrator-workers composition | Depends on stable two-tool facade landing first | Layer 4 Agent Swarms epic | #576 |
| Prompt-cache instrumentation for repeated `resolve_location` queries | Caching is intentionally disabled (cache_ttl_seconds=0 fail-closed default); caching strategy is a separate concern | Context Assembly / cache epic | #577 |
| TUI surface for the two-tool flow | TUI (Ink + Bun) is Phase 2+ per `docs/vision.md`; MVP ships headless | TUI Phase 2 epic | #578 |
| Additional adapters beyond the 4 seeds (air quality, public holidays, etc.) | Seed set proves the registration contract; expansion happens after eval gate is green | Adapter expansion epic | #579 |
| OpenTelemetry GenAI spans on the two-tool surface | Spec 021 already observability-ready; integration is additive and non-blocking | Observability integration epic | #580 |
| `parallel_safe` parallelization of candidate adapters in search mode | Current search only returns candidates for the model to pick from; true parallel fan-out is a future optimization | Parallelization epic | #581 |
| Full internationalization of `search_hint` beyond ko+en | Bilingual is sufficient for MVP target users (Korean citizens) | I18n epic | #582 |
| Rate-limit orchestration beyond per-adapter `rate_limit_per_minute` (account-wide budget) | Per-adapter quota is sufficient for MVP; account-wide budget is part of Error Recovery | Layer 6 Error Recovery epic | #583 |
| Write-capable adapters (POST endpoints on `data.go.kr`) | All four seed adapters are read-only; write paths need additional identity-verification wiring | Post-Layer-3 write-path epic | #584 |
| Tokenizer replacement / alternative retrieval backends (dense embeddings) | BM25 + kiwipiepy is the MVP retrieval baseline per Q2 decision; dense retrieval is optimization | Retrieval quality epic | #585 |
