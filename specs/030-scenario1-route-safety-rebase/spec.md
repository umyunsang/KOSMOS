# Feature Specification: Scenario 1 E2E — Route Safety (Re-baseline)

**Feature Branch**: `feat/17-scenario1-route-safety`
**Created**: 2026-04-18
**Status**: Draft
**Input**: Epic #17 — Scenario 1 E2E — Route Safety (KOROAD + KMA via `lookup` facade)
**Supersedes**: `specs/012-scenario1-e2e-route-safety/spec.md` (2026-04-13 draft)
**Related closed specs that changed the baseline**: #507 (022 two-tool facade), #602 (023 NMC SLO), #612/#650s (024/025 security v1/v6), #468 (026-secrets Infisical OIDC + fail-fast guard)

---

## What changed from spec 012 (delta summary)

| Area | Spec 012 (pre-freeze) | Spec 030 (this spec) |
|---|---|---|
| Tool surface | Direct composite adapter `road_risk_score` + three fan-out sub-tools | `resolve_location` + `lookup(mode=search→fetch)` only — no sub-tool calls |
| Geocoding | `address_to_region` / `address_to_grid` (standalone LLM-visible tools) | `resolve_location(want="coords_and_admcd")` internal dispatch |
| Adapters | `road_risk_score` composite (KOROAD + KMA + KMA-obs fused in one call) | Two discrete `lookup(mode="fetch")` calls: `koroad_accident_hazard_search` then `kma_forecast_fetch` |
| NMC involvement | Out of scope (Scenario 2) | Still out of scope, but `nmc_emergency_search` is referenced for adapter-level gating patterns |
| Security contract | None — spec predates 024/025 | All adapters must satisfy V1–V6 invariants (`auth_type`↔`auth_level`, fail-closed defaults) |
| Secrets/config | No startup guard | `KOSMOS_KAKAO_REST_KEY` + `KOSMOS_DATA_GO_KR_API_KEY` validated at boot by guard (#468); scenario tests must NOT boot without these present (or use in-memory fixture fixture override) |
| Observability | `UsageTracker` token counts only | OTel GenAI spans: `gen_ai.tool.execute` per call, `kosmos.tool.adapter` attribute on `fetch` calls, no raw query strings in PII span attributes |
| Return schema | `road_risk_score` custom dict | Frozen discriminated union: `LookupCollection` (KOROAD) + `LookupTimeseries` (KMA) |
| KOROAD code quirks | Not addressed | Year-aware code mapping (2023: 강원 42→51, 전북 45→52) exercised by dedicated fixture path |
| Test structure | `tests/e2e/` against mock LLM + composite fixture | Same location; mock LLM replays exact `resolve→search→fetch→fetch` sequence; all fixtures recorded |

---

## Overview & Context

This is the Phase 1 capstone: an end-to-end test validating the complete KOSMOS pipeline for the route-safety citizen scenario. A citizen asks a natural-language question about travel safety; the system fuses KOROAD accident-hotspot data with KMA weather forecast data — routed entirely through the `resolve_location` + `lookup` two-tool facade — and produces an actionable Korean-language safety recommendation.

The scenario exercises the tool loop (Layer 1), the tool system's facade + BM25 retrieval gate + adapter invocation (Layer 2), the fail-closed auth gate (Layer 3 interface), context assembly (Layer 5), and cost accounting. It does NOT exercise Layer 4 (Agent Swarms), which is Phase 2+ (Epics #13, #14).

KOROAD (`koroad_accident_hazard_search`) and KMA (`kma_forecast_fetch`) are both `is_personal_data=False`, so this scenario intentionally avoids the full Layer 3 permission gauntlet — it targets the KSC 2026 demonstration path where the core `resolve→search→fetch` cycle is proven against recorded fixtures.

Target interaction (from `docs/design/mvp-tools.md` §7 Pattern A + B, and Epic #17 body):

```
Citizen:  "내일 강남구에서 서울역 가는데 날씨랑 사고다발지역 알려줘"

Turn 1 — LLM calls:
  resolve_location(query="강남구", want="coords_and_admcd")
    → ResolveBundle { coords: (37.518, 127.047), adm_cd: "1168000000" }
  resolve_location(query="서울역", want="coords_and_admcd")
    → ResolveBundle { coords: (37.554, 126.970), adm_cd: "1104000000" }

Turn 2 — LLM calls:
  lookup(mode="search", query="사고다발지역 교통사고")
    → LookupSearchOutput { candidates: [koroad_accident_hazard_search, …] }

Turn 3 — LLM calls:
  lookup(mode="fetch", tool_id="koroad_accident_hazard_search",
         args={sido_code: "11", gugun_code: "680", year: "2023"})
    → LookupCollection { items: [...] }

Turn 4 — LLM calls:
  lookup(mode="search", query="날씨 예보 단기예보")
    → LookupSearchOutput { candidates: [kma_forecast_fetch, …] }

Turn 5 — LLM calls:
  lookup(mode="fetch", tool_id="kma_forecast_fetch",
         args={lat: 37.518, lon: 127.047, base_date: "20260419", base_time: "0500"})
    → LookupTimeseries { points: [{ts: "...", temperature_c: ..., pop_pct: ..., ...}], ... }

Turn 6 — LLM synthesizes:
  Korean response combining ≥1 hazard spot name + ≥1 weather field (e.g., temperature or pop_pct)
```

**Minimum turn count**: 6 turns (2 resolve + 2 search + 2 fetch + 1 synthesis). The mock LLM fixture is scripted to this exact sequence for deterministic CI assertion.

---

## User Scenarios & Testing

### User Story 1 — Happy-Path Route Safety Query (Priority: P1)

A citizen asks a natural-language route-safety question. KOSMOS executes the full `resolve→search→fetch×2→synthesize` pipeline using recorded fixtures, then produces a Korean-language recommendation that names at least one KOROAD hazard spot and at least one KMA forecast field.

**Why this priority**: This is the fundamental proof that the Phase 1 pipeline works end-to-end under the frozen two-tool facade. Without this, Phase 1 acceptance is not complete.

**Independent Test**: Send the scripted user message through the QueryEngine with a deterministic mock LLM (pre-loaded with the exact 6-turn `StreamEvent` sequence) against recorded JSON fixtures for all three providers (Kakao geocoding, KOROAD, KMA). Assert tool-call order, output schema conformance, and Korean synthesis content.

**Acceptance Scenarios**:

1. **Given** a configured QueryEngine, recorded fixtures, and a mock LLM scripted to the 6-turn sequence above, **When** the citizen sends the trigger query, **Then** the engine executes all tool calls in the declared order and the final assistant message is in Korean, contains ≥1 KOROAD hazard spot name (from `LookupCollection.items[].location_name` or equivalent), and ≥1 KMA forecast field reference (e.g., temperature, precipitation probability).

2. **Given** the same setup, **When** the query completes, **Then** the conversation history contains `tool_calls` and `tool` result messages in the correct interleaved order — no tool result appears before its corresponding call.

3. **Given** the same setup, **When** the query completes, **Then** `UsageTracker.total_input_tokens` and `UsageTracker.total_output_tokens` each equal the sum of the mock LLM's reported per-call token counts (0% tolerance — deterministic mocks).

4. **Given** the same setup, **When** the query completes, **Then** every `lookup(mode="fetch")` response envelope has a `meta` block containing `source`, `fetched_at` (UTC ISO-8601), `request_id` (UUID4), and `elapsed_ms`.

---

### User Story 2 — Degraded-Path: Single Adapter Failure (Priority: P2)

One of the two lookup adapters (KOROAD or KMA) returns an upstream error. The tool loop retries once, then synthesizes a partial response using whichever data source succeeded, with the failure clearly noted.

**Why this priority**: Government APIs fail during maintenance windows and rate-limit spikes. Graceful degradation is essential for citizen trust and is a direct success criterion in Epic #17.

**Independent Test**: Configure one adapter fixture to return `LookupError(reason="upstream_down", retryable=True)`; the other succeeds. Assert the mock LLM receives a partial result, issues one retry, and the final assistant message contains data from the surviving adapter with a transparent data-gap note.

**Acceptance Scenarios**:

1. **Given** the KMA fixture returns `LookupError(reason="upstream_down", retryable=True)` on the first `fetch` call and succeeds on retry, **When** the tool loop processes the error, **Then** the loop issues exactly one retry and the final response includes KMA data (not just KOROAD).

2. **Given** the KOROAD fixture returns `LookupError(reason="upstream_down", retryable=True)` and the mock LLM does not retry (retryable state consumed), **When** synthesis occurs, **Then** the final Korean response still contains KMA weather data and explicitly notes that accident-hotspot data was unavailable, without raising an unhandled exception to the CLI layer.

3. **Given** both adapters return `LookupError(reason="upstream_down", retryable=False)`, **When** synthesis occurs, **Then** the engine produces a graceful Korean error message (no raw exception traceback surfaces) and the `QueryState.stop_reason` is `error_unrecoverable`.

---

### User Story 3 — KOROAD Year-Code Quirk Path (Priority: P2)

A query targeting a prefecture affected by the 2023 sido/gugun code shift (강원도 42→51, 전북 45→52) produces the same hazard-count result as an unaffected prefecture, proving the adapter's year-aware codebook is applied correctly.

**Why this priority**: This is a data-correctness invariant that is easy to break silently. The 2023 realignment affects real KOROAD API responses and must be fixture-tested at the scenario level, not only at the unit level.

**Independent Test**: Supply a `adm_cd` resolving to 강원도 with `year="2023"`. Assert the adapter maps the incoming `siDo` code to `51` (not `42`) before the outbound HTTP call. The recorded fixture uses `siDo=51` — a mismatch causes the fixture replay to return no results, failing the hazard-count assertion.

**Acceptance Scenarios**:

1. **Given** `resolve_location(query="강원도 춘천시")` returns `adm_cd` whose sido prefix is the legacy value `42`, **When** `lookup(mode="fetch", tool_id="koroad_accident_hazard_search", args={..., year: "2023"})` is called, **Then** the adapter internally substitutes `siDo=51` before constructing the KOROAD HTTP request, and the fixture replay returns a non-empty `LookupCollection`.

2. **Given** the same query with `year="2022"` (pre-shift year), **When** the adapter executes, **Then** the adapter uses `siDo=42` (no substitution), and the corresponding fixture confirms the count.

---

### User Story 4 — Observability Span Assertions (Priority: P3)

Every tool call during the scenario emits an OTel `gen_ai.tool.execute` span with the required attributes, enabling end-to-end trace reconstruction in Langfuse.

**Why this priority**: OTel spans are the acceptance surface for Epic #501 (observability). The scenario test is the natural host for integration-level span assertions, keeping unit and integration concerns separated.

**Independent Test**: After running the happy-path scenario, assert the captured in-memory span list against the span-attribute contract from spec 021/Epic #501.

**Acceptance Scenarios**:

1. **Given** the happy-path scenario completes, **When** the span list is inspected, **Then** every tool call (both `resolve_location` and `lookup`) has produced exactly one `gen_ai.tool.execute` span with `gen_ai.tool.name ∈ {"resolve_location", "lookup"}` and `kosmos.tool.outcome ∈ {"ok", "error"}`.

2. **Given** the two `lookup(mode="fetch")` calls, **When** spans are inspected, **Then** those spans carry a `kosmos.tool.adapter` attribute set to `"koroad_accident_hazard_search"` and `"kma_forecast_fetch"` respectively (this attribute is only present on `fetch` calls, not `search` or `resolve_location` calls).

3. **Given** a `lookup(mode="fetch")` call that fails with `LookupError`, **When** the span is inspected, **Then** `kosmos.tool.outcome = "error"` and `error.type` names the error class; no raw citizen query string appears in any span attribute (PII masking per spec 021).

---

### Edge Cases

- **Unregistered `tool_id` in fetch call**: LLM calls `lookup(mode="fetch", tool_id="nonexistent_adapter", ...)` → `LookupError(reason="not_found")` returned; loop continues.
- **Max-iterations guard**: Mock LLM scripted to never emit `end_turn` — QueryEngine must stop at `max_iterations` and yield `StopReason.error_unrecoverable`.
- **Pydantic validation failure**: Mock LLM passes `args` that fail `koroad_accident_hazard_search`'s `input_schema` → `LookupError(reason="invalid_args")` with Pydantic error detail in `upstream_message`; loop does not raise.
- **Budget exceeded mid-turn**: `BudgetExceededError` raised during a `fetch` call → engine yields `StopReason.api_budget_exceeded` gracefully.
- **`resolve_location` returns `ResolveError(reason="not_found")`**: LLM receives the error variant; mock LLM is scripted to rewrite the query and retry once; test asserts the retry path.
- **`base_time` validation error for KMA**: KMA adapter receives an invalid `base_time` not in `{"0200","0500","0800","1100","1400","1700","2000","2300"}` → `LookupError(reason="invalid_args")`; fixture covers this path.
- **Ambiguous location (`resolve_location` returns `ResolveError(reason="ambiguous")`)**:  `candidates` list is non-empty; mock LLM picks the first candidate and re-calls `resolve_location` with the resolved string; test asserts the disambiguation loop terminates.

---

## Requirements

### Functional Requirements

**E2E test module**

- **FR-001**: The system MUST execute the full query pipeline end-to-end: user message → context assembly → LLM stream → `resolve_location` × 2 → `lookup(search)` × 2 → `lookup(fetch)` × 2 → synthesis → final response.
- **FR-002**: All tool calls MUST be routed through `resolve_location` and `lookup` exclusively. Zero direct adapter imports may appear in the test module. The test module must never reference adapter classes by fully qualified name.
- **FR-003**: The mock LLM MUST be a deterministic stub (pre-loaded `StreamEvent` sequence) — not a live FriendliAI/K-EXAONE call in CI.
- **FR-004**: ALL HTTP calls to `data.go.kr`, Kakao, juso.go.kr, and SGIS MUST be intercepted by recorded fixtures during CI. No live outbound requests are permitted. Live variants MUST be gated behind `@pytest.mark.live`.

**Return schema conformance**

- **FR-005**: The KOROAD adapter MUST return `LookupCollection` with `kind="collection"` and `items` containing typed hazard records.
- **FR-006**: The KMA adapter MUST return `LookupTimeseries` with `kind="timeseries"`, `interval="hour"`, and `points` using semantic field names (`temperature_c`, `precipitation_mm`, `humidity_pct`, `wind_ms`, `pop_pct`) rather than KMA category codes (`TMP`, `PCP`, etc.).
- **FR-007**: Every `lookup(mode="fetch")` response envelope MUST include a `meta` block with `source`, `fetched_at` (UTC ISO-8601), `request_id` (UUID4), and `elapsed_ms`.
- **FR-008**: `LookupError` values MUST carry `reason` (from the frozen enum in `docs/design/mvp-tools.md` §5.4), `retryable: bool`, and optionally `upstream_code` / `upstream_message`.

**Security invariants (new vs spec 012)**

- **FR-009**: Both `koroad_accident_hazard_search` and `kma_forecast_fetch` MUST satisfy the V1–V6 security invariants: `auth_type="api_key"` and `auth_level` in `{"AAL1","AAL2","AAL3"}` (V6 canonical mapping), `is_personal_data=False`, `requires_auth=False`, fail-closed defaults for `is_concurrency_safe=False` and `cache_ttl_seconds=0`.
- **FR-010**: The test module MUST NOT bypass `ToolRegistry.register()` validation. Adapters are registered through the normal path so V6 backstop checks run.

**Configuration and startup guard (new vs spec 012)**

- **FR-011**: Test fixtures MUST either populate `KOSMOS_DATA_GO_KR_API_KEY` and `KOSMOS_KAKAO_REST_KEY` via in-memory override (using `pydantic-settings` test injection) or configure the startup guard to no-op in unit mode. Tests MUST NOT expose real key values.
- **FR-012**: The startup guard (spec 026-secrets / Epic #468) MUST NOT be bypassed in the scenario test harness — instead, the test fixture MUST provide the required env vars via `monkeypatch.setenv` or a `pytest` fixture that sets dummy values for CI.

**KOROAD year-code quirks**

- **FR-013**: The KOROAD adapter MUST apply year-aware sido/gugun code mapping before constructing any outbound HTTP request. The mapping table MUST cover at minimum: 강원 42→51 (2023+), 전북 45→52 (2023+).
- **FR-014**: The scenario test MUST include at least one fixture exercising the 2023 quirk path (강원도 query with `year="2023"`), and the fixture MUST use the post-shift code `siDo=51` in the recorded request URL.

**Token and cost accounting**

- **FR-015**: `UsageTracker.total_input_tokens` and `UsageTracker.total_output_tokens` MUST equal the sum of mock LLM per-call reported counts across all loop iterations (0% tolerance).
- **FR-016**: The rate limiter MUST record exactly one call per adapter endpoint invoked (KOROAD and KMA each appear once in the happy-path fixture set).

**Observability spans (new vs spec 012)**

- **FR-017**: Every tool call (both `resolve_location` and `lookup`) MUST emit one `gen_ai.tool.execute` span with `gen_ai.tool.name` and `kosmos.tool.outcome`.
- **FR-018**: `lookup(mode="fetch")` spans MUST additionally carry `kosmos.tool.adapter` set to the resolved adapter id.
- **FR-019**: Span assertions MUST verify that no raw Korean query strings from citizen input appear in exported span attributes. Citizen-originating strings MUST be absent from span attributes or represented only by a hash (per spec 021 PII masking rules).
- **FR-020**: The span assertion test MUST be skipped gracefully (not fail) when `OTEL_SDK_DISABLED=true` is set, to preserve CI compatibility with spec 021's no-op path.

**Degraded-path behavior**

- **FR-021**: When exactly one adapter returns `LookupError(retryable=True)`, the engine MUST retry that call exactly once before proceeding.
- **FR-022**: When both adapters fail, the engine MUST produce a graceful Korean error message and set `stop_reason=error_unrecoverable` without propagating an unhandled exception to the CLI layer.

**Synthesis content**

- **FR-023**: The final synthesized Korean response MUST contain ≥1 KOROAD hazard spot location reference and ≥1 KMA forecast field reference in the happy-path test assertion. The assertion is a string-presence check on mock LLM output — it does not evaluate LLM quality.

### Key Entities

- **ScenarioFixture**: A self-contained test bundle — mock LLM `StreamEvent` sequence + recorded HTTP fixture tapes for Kakao, KOROAD, and KMA — for a specific trigger query.
- **RecordedHTTPTape**: A JSON file (or `respx` tape) capturing a real outbound HTTP request/response pair for replay in CI, stored under `tests/fixtures/{provider}/`.
- **MockLLMClient**: Existing deterministic stub from `tests/engine/conftest.py`, extended to script the 6-turn tool-call sequence for this scenario.

---

## Success Criteria

| ID | Criterion | Measurable bar |
|---|---|---|
| SC-1 | Happy-path test green | Final Korean response contains ≥1 hazard spot name AND ≥1 weather field; all assertions pass |
| SC-2 | Schema conformance | 100% of `lookup(fetch)` responses are `LookupCollection` or `LookupTimeseries` or `LookupError`; no ad-hoc dict escapes the envelope |
| SC-3 | Single-adapter failure | Partial-data response produced without unhandled exception; surviving adapter's data present in response |
| SC-4 | Both-adapters failure | Graceful Korean error message; `stop_reason=error_unrecoverable`; no exception to CLI |
| SC-5 | KOROAD 2023 quirk path | Quirk fixture produces same non-zero hazard-count assertion as non-quirk path |
| SC-6 | Token accounting | `UsageTracker` totals match mock LLM reports; 0% deviation |
| SC-7 | Span assertions | Every tool call produces exactly one `gen_ai.tool.execute` span; `fetch` spans carry `kosmos.tool.adapter`; no citizen query strings in span attributes |
| SC-8 | CI runtime | Full scenario test suite (happy + degraded + quirk + span paths) completes in < 5 s with no live HTTP calls |
| SC-9 | Security invariants | `ToolRegistry.register()` passes V1–V6 checks for both adapters; test fails if a misconfigured adapter is introduced |
| SC-10 | No hardcoding | No static keyword lists, no hardcoded adapter IDs in the mock LLM fixture beyond the scripted sequence; no salvage logic; no `Any` in I/O schemas |

---

## Assumptions

1. `resolve_location`, `lookup`, `koroad_accident_hazard_search`, and `kma_forecast_fetch` are implemented and passing their own unit tests (spec 022 / Epic #507 closed before this spec lands).
2. The `MockLLMClient` with pre-loaded `StreamEvent` sequences is the established testing pattern from `tests/engine/conftest.py`.
3. Recorded HTTP fixtures follow the existing pattern: JSON (or `respx` tape) files under `tests/fixtures/{provider}/` loaded via path resolution.
4. The startup guard (spec 026-secrets) is implemented; test fixtures neutralize it via `monkeypatch.setenv`.
5. OTel spans are captured in-process via an in-memory `SpanExporter` in tests (no real OTLP endpoint needed for CI assertions).
6. `KOSMOS_DATA_GO_KR_API_KEY` is the shared key for both KOROAD and KMA endpoints; `KOSMOS_KAKAO_REST_KEY` covers Kakao Local geocoding.

---

## Scope Boundaries & Deferred Items

### Out of Scope (Permanent)

- Live `data.go.kr` / Kakao API calls in CI — recorded fixtures only (Constitution §IV).
- CLI/TUI rendering tests — this spec tests the engine pipeline, not terminal output formatting.
- LLM response quality evaluation (semantic similarity, DeepEval) — pipeline mechanics only.
- HIRA / NMC adapter invocation — NMC is `auth_required` interface-only in this scenario; HIRA belongs to Scenario 2 (#18).
- Full 7-step Layer 3 permission gauntlet — KOROAD and KMA are `is_personal_data=False`; this scenario intentionally avoids the full gauntlet (see Epic #16).
- Multi-turn follow-up conversation (≥3 distinct citizen turns) — deferred to Context Assembly v2.
- `road_risk_score` composite adapter — permanently removed per `docs/design/mvp-tools.md` §8.2.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Multi-turn follow-up E2E (e.g., citizen asks a follow-up in the same session) | Context Assembly v2; single-turn is P1 scope | Context Assembly v2 epic | NEEDS TRACKING |
| Agent Swarm participation (parallel KOROAD + KMA fan-out via mailbox IPC) | Requires Layer 4 (#13, #14); single-agent loop proves the adapter surface first | Epic #13 / #14 | #13, #14 |
| LLM output quality metrics (DeepEval) | Evaluation framework setup is orthogonal to pipeline correctness | Observability/eval epic | NEEDS TRACKING |
| Scenario 2–5 E2E tests | Different adapters (HIRA, NMC, MOHW, Gov24) | Epics #18, #19, and successors | #18, #19 |
| Dense-embedding retrieval upgrade for `lookup(mode="search")` | BM25 is MVP baseline; dense retrieval is tracked under #585 | Epic #585 | #585 |
| Prompt-cache instrumentation for repeated `resolve_location` calls | Cache strategy deferred; `cache_ttl_seconds=0` fail-closed default remains | Context Assembly / cache epic | NEEDS TRACKING |

---

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-001 | `tool_id` is the canonical identifier field (per spec 022). `adapter_id` in Epic #17 body is deprecated. | Aligns with the `lookup` facade parameter contract established in spec 022; all `adapter_id` references in this spec have been replaced with `tool_id`. |

---

## References

- **Design**: `docs/design/mvp-tools.md` §4 (`resolve_location`), §5 (`lookup`), §5.4 (frozen envelope discriminators), §5.8 (seed adapter set), §7 (Pattern A + B walkthroughs)
- **Constitution**: `.specify/memory/constitution.md` §II (fail-closed), §III (Pydantic v2), §IV (no live CI calls), §VI (deferred item tracking)
- **Vision**: `docs/vision.md` §Layer 1 (query engine), §Layer 2 (tool system), §Citizen scenarios #1
- **Security invariants**: `specs/024-tool-security-v1/spec.md` (FR-001 to FR-038), `specs/025-tool-security-v6/spec.md` (FR-039 to FR-048)
- **NMC freshness**: `specs/023-nmc-freshness-slo/spec.md` (referenced for `stale_data` reason pattern; NMC not exercised in this scenario)
- **Observability**: `specs/021-observability-otel-genai/spec.md` (span schema, PII masking, OTEL_SDK_DISABLED no-op)
- **Secrets guard**: `specs/026-secrets-infisical-oidc/spec.md` (startup guard integration, env var names)
- **Prior draft**: `specs/012-scenario1-e2e-route-safety/spec.md` (2026-04-13 — superseded by this spec)
- **Reconstructed sources**: `claude-code-sourcemap/query.ts` (streaming tool-loop reference), `claude-reviews-claude/architecture/01-query-engine.md` (full pipeline analysis)
