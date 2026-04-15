# Implementation Plan: MVP Main-Tool — `lookup` + `resolve_location`

**Branch**: `022-mvp-main-tool` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-mvp-main-tool/spec.md`
**Design source (frozen)**: `docs/design/mvp-tools.md` (frozen 2026-04-16). All 12 decisions (D1–D7, Q1–Q5) are closed.

## Summary

Collapse the KOSMOS LLM-facing tool surface to exactly **two tools** — `resolve_location` (any place → typed identifier) and `lookup` (`mode="search"` BM25 gate over adapters + `mode="fetch"` typed invocation) — and register **four seed adapters** (KOROAD / KMA / HIRA / NMC) as cold-path entries visible only through `lookup.search`. The two-tool facade follows the frozen `docs/design/mvp-tools.md` verbatim: discriminated outputs `LookupRecord | LookupCollection | LookupTimeseries | LookupError` (§5.4) and `CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError`; BM25 retrieval via `rank_bm25` + `kiwipiepy>=0.17`; adaptive `top_k = min(KOSMOS_LOOKUP_TOPK, len(registry))` clamped to `[1, 20]`. NMC is interface-only (PII-flagged) to exercise the Layer 3 auth-gate short-circuit end-to-end without shipping a real Provider. The refactor absorbs #288's `address_to_region` / `address_to_grid` into `resolve_location` and the KMA adapter's internal LCC projection helper — both tools are removed from the LLM surface with no compat shim.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `httpx>=0.27` (async HTTP, existing), `pydantic>=2.13` (schemas, existing), `pydantic-settings>=2.0` (env config, existing), `rank_bm25>=0.2.2` (NEW — Apache-2.0, BM25 retrieval), `kiwipiepy>=0.17` (NEW — MIT, Korean morpheme tokenizer)
**Storage**: N/A — in-memory registry; BM25 index rebuilt at registry boot and on registration; no persistent state
**Testing**: `pytest`, `pytest-asyncio`, recorded fixtures for all four adapters; `@pytest.mark.live` for the one-time fixture capture (skipped in CI)
**Target Platform**: Linux / macOS server (CPython 3.12); TUI layer deferred to #287 and not in scope
**Project Type**: Single-project Python library (`src/kosmos/`) — not a web service; the LLM tool-loop harness consumes the two tools via the existing `kosmos.tools` module tree
**Performance Goals**: BM25 `search` p95 < 50 ms on a 10–50-adapter registry (well below any LLM tool-call overhead); `resolve_location` p95 < 1.5 s per chain step (network-bound on Kakao/JUSO/SGIS)
**Constraints**: Fail-closed defaults (Constitution §II) — `is_concurrency_safe=False`, `is_personal_data=True`, `requires_auth=True`, `cache_ttl_seconds=0` unless explicitly relaxed per adapter. `Any` forbidden in all schemas. `KOSMOS_` env-prefix enforced. No live `data.go.kr` calls in CI (§IV). No `print()` outside the CLI layer.
**Scale/Scope**: 4 seed adapters; 30-query BM25 eval set (`eval/retrieval_queries.yaml`); two LLM-facing tools; envelope-normalization layer shared by both; Layer 3 auth-gate short-circuit as interface-only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.1.0.

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I  | Reference-Driven | PASS | Every design decision in `docs/design/mvp-tools.md` traces to a reference (Anthropic Tool Search Tool, AnyTool hierarchical router, Claude Code reconstructed `02-tool-system.md`, Pydantic AI registry). Phase 0 research.md builds the layer-to-reference map explicitly. |
| II | Fail-Closed (NON-NEGOTIABLE) | PASS | FR-024 requires every seed adapter to declare the four fail-closed booleans; `GovAPITool` model already defaults the four to their restrictive values (`src/kosmos/tools/models.py:49-59`). NMC (PII) returns `LookupError(reason="auth_required")` with 0 upstream calls (FR-022, SC-006). |
| III | Pydantic v2 Strict (NON-NEGOTIABLE) | PASS | FR-007 forbids `Any` in the schema; the single loose field is `LookupFetchInput.params: dict[str, object]` validated against the target adapter's `input_schema` at fetch time (per frozen §5.2). |
| IV | Government API Compliance | PASS | FR-023 (happy + error-path tests with recorded fixtures for every seed adapter); SC-006 (NMC = 0 live calls); `KOSMOS_`-prefixed env vars enforced (FR-032). |
| V  | Policy Alignment | PASS | Two-tool facade = Principle 8 (single conversational window); `search_hint` bilingual ko+en = Principle 9 (discoverable Open API). Layer 3 auth-gate interface = Principle 5 / PIPA foundation (even without a real Provider, the short-circuit is unconditional per FR-026). |
| VI | Deferred Work Accountability | PASS (deferred to taskstoissues) | 14-row Deferred Items table populated. 1 row carries a verified `#16` ref (Permission Pipeline v2) + 13 rows carry `NEEDS TRACKING`. Pre-remediation mismatches were downgraded per research.md §2. Resolution path: `/speckit-taskstoissues` will materialize placeholder issues for all 13 `NEEDS TRACKING` rows before `/speckit-implement`. |

**Gate decision**: PASS. Proceeding to Phase 0; the 13 `NEEDS TRACKING` rows are resolved by `/speckit-taskstoissues` prior to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/022-mvp-main-tool/
├── plan.md                 # This file
├── research.md             # Phase 0 output
├── data-model.md           # Phase 1 output
├── quickstart.md           # Phase 1 output
├── contracts/              # Phase 1 output (JSON Schemas + tool contracts)
│   ├── resolve_location.input.schema.json
│   ├── resolve_location.output.schema.json
│   ├── lookup.input.schema.json
│   ├── lookup.output.schema.json
│   └── README.md
├── checklists/
│   └── requirements.md     # Spec-quality checklist (already written)
└── tasks.md                # Created later by /speckit-tasks
```

### Source Code (repository root)

Existing layout — KOSMOS is a single-project Python library under `src/kosmos/`. This feature **adds new modules** to the existing `tools/` subtree rather than introducing a new top-level layout.

```text
src/kosmos/
├── tools/
│   ├── models.py            # EXTEND: add LookupInput/Output discriminated unions + ResolveLocation{Input,Output}
│   ├── search.py            # REPLACE body: swap token-overlap for BM25 + kiwipiepy tokenizer
│   ├── registry.py          # EXTEND: emit BM25 index rebuild on register()
│   ├── executor.py          # EXTEND: wire Layer 3 auth-gate short-circuit + envelope normalization
│   ├── errors.py            # EXTEND: add LookupError reason enum values
│   ├── register_all.py      # EXTEND: register 4 seed adapters
│   ├── resolve_location.py  # NEW: single location-resolution facade
│   ├── lookup.py            # NEW: single data-lookup facade (search|fetch)
│   ├── envelope.py          # NEW: discriminated-union envelope validator
│   ├── tokenizer.py         # NEW: kiwipiepy wrapper with lazy load
│   ├── bm25_index.py        # NEW: rank_bm25 wrapper with deterministic tie-break
│   ├── geocoding/           # EXISTING: Kakao / JUSO / SGIS clients — move #288 logic here
│   ├── koroad/              # EXISTING: extend with koroad_accident_hazard_search adapter
│   ├── kma/                 # EXISTING: add kma_forecast_fetch + internal LCC projection helper
│   ├── hira/                # NEW package: hira_hospital_search adapter
│   └── nmc/                 # NEW package: nmc_emergency_search interface-only adapter
├── permissions/             # EXISTING: Layer 3 plumbing; executor hooks auth-gate here
└── (other layers unchanged)

tests/
├── tools/
│   ├── test_resolve_location.py        # NEW
│   ├── test_lookup_search.py           # NEW
│   ├── test_lookup_fetch.py            # NEW
│   ├── test_envelope_normalization.py  # NEW
│   ├── test_bm25_retrieval.py          # NEW
│   ├── test_auth_gate.py               # NEW: NMC short-circuit = 0 upstream calls
│   ├── koroad/                         # EXISTING + new hazard adapter tests
│   ├── kma/                            # EXISTING + new forecast+LCC tests
│   ├── hira/                           # NEW
│   └── nmc/                            # NEW
├── fixtures/
│   ├── koroad/                         # NEW recorded tapes
│   ├── kma/
│   ├── hira/
│   └── nmc/                            # placeholder — NMC makes 0 upstream calls, no tape beyond error shape
└── (other test subtrees unchanged)

eval/
└── retrieval_queries.yaml  # NEW: 30-query BM25 evaluation set

pyproject.toml              # EDIT: add rank_bm25 + kiwipiepy to [project.dependencies]
```

**Structure Decision**: Single-project Python layout (Option 1) — KOSMOS already uses `src/kosmos/` with per-layer subpackages. The two new facades and four seed adapters drop into the existing `src/kosmos/tools/` subtree; no new top-level package or service boundary is introduced. This matches `docs/vision.md` (six-layer single backend) and avoids the multi-project complexity of Option 2/3.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

**No unjustified violations.** The one WARN (Principle VI: 6 mismatched deferral refs) is a spec-data-quality issue, not a constitutional design violation — it will be resolved in Phase 0 research.md and corrected via spec amendment or `/speckit-taskstoissues` before implementation begins. No new complexity is introduced by the frozen design choices (all 12 decisions D1–D7, Q1–Q5 are pre-resolved; simpler alternatives were rejected in the design doc itself, not here).
