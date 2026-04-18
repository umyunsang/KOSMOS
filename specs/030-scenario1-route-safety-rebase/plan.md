# Implementation Plan: Scenario 1 E2E — Route Safety (Re-baseline)

**Branch**: `feat/17-scenario1-route-safety` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/030-scenario1-route-safety-rebase/spec.md`
**Supersedes**: `specs/012-scenario1-e2e-route-safety/plan.md` (2026-04-13 — pre-022 facade freeze)

## Summary

Re-baseline the Scenario 1 (route safety) end-to-end test onto the post-Epic 022 MVP main-tool surface. The citizen trigger query now flows exclusively through the two LLM-visible tools `resolve_location` + `lookup(mode=search|fetch)`; the deprecated `road_risk_score` composite and standalone geocoding tools are not called. Two adapters are invoked behind `lookup(mode="fetch")`: `koroad_accident_hazard_search` and `kma_forecast_fetch`. All providers are replayed from recorded fixtures; the LLM is a deterministic `MockLLMClient` scripted to the 6-turn sequence in `spec.md §Overview`. The test module is purely new — no production code changes are required for happy/degraded/quirk paths. Two small, scoped production touches are required for the observability assertions: wiring `kosmos.tool.outcome` + `kosmos.tool.adapter` attributes on the existing `execute_tool` span inside `ToolExecutor.dispatch()` / `invoke()` (FR-017/018), which is a missing part of the spec 021 contract that this scenario is the first to assert end-to-end.

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no version bump).
**Primary Dependencies**: `pydantic >= 2.13` (existing), `httpx >= 0.27` (existing, mock target), `pytest` + `pytest-asyncio` (existing), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (existing from spec 021, used via `kosmos.observability.semconv`). **No new runtime dependencies** (AGENTS.md hard rule).
**Storage**: N/A — in-memory test state + in-memory OTel `InMemorySpanExporter`. Recorded HTTP fixtures live under `tests/fixtures/{kakao,koroad,kma}/` as JSON.
**Testing**: `pytest` + `pytest-asyncio`; `unittest.mock.AsyncMock` patching `httpx.AsyncClient.get`; `opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter` for span assertions; `monkeypatch.setenv` for startup-guard neutralization.
**Target Platform**: macOS/Linux CI — the existing GitHub Actions matrix.
**Project Type**: Integration test suite (single-project layout). New files live only under `tests/e2e/`; minimal production edits confined to `src/kosmos/tools/executor.py` and `src/kosmos/tools/lookup.py` for FR-017/018.
**Performance Goals**: Full scenario suite (happy + degraded + quirk + span + edge) completes in **< 5 s wall-clock** (SC-8) and < 1.5 s CPU on a modern developer machine. No network I/O.
**Constraints**:
  - Zero live API calls in CI (Constitution §IV; FR-004).
  - Zero new runtime dependencies (AGENTS.md).
  - Fail-closed defaults preserved; `ToolRegistry.register()` V1–V6 backstop MUST run for both adapters (FR-009/010).
  - No raw citizen query strings in any exported OTel span attribute (FR-019; spec 021 PII masking).
**Scale/Scope**: 1 new `conftest.py` helper module + 5 new test files (happy / degraded / quirk / span / edge) + 1 new span-attribute emission site on the `lookup(fetch)` path. Estimated ~900–1,200 LOC of test code; ≤ 40 LOC of production instrumentation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | Every design decision in `research.md` maps to a source from `docs/vision.md § Reference materials`. |
| II. Fail-Closed Security | PASS | Test fixtures neutralize the startup guard via `monkeypatch.setenv` (FR-012) — they do **not** bypass it. Adapters register through `ToolRegistry.register()` so V1–V6 backstop runs. |
| III. Pydantic v2 Strict Typing | PASS | No `Any` in new I/O; assertions use the frozen `LookupCollection` / `LookupTimeseries` / `LookupError` discriminated union from `kosmos.tools.models`. |
| IV. Government API Compliance | PASS | All HTTP intercepted by recorded fixtures; live variants gated behind `@pytest.mark.live` (FR-004). `rate_limit_per_minute` and `usage_tracker` are exercised once per adapter (FR-016). |
| V. Policy Alignment | N/A | No policy change; KOROAD + KMA are `is_personal_data=False` so the full 7-step permission gauntlet is intentionally not exercised (spec §Overview, Epic #16). |
| VI. Deferred Work Accountability | PASS | All six deferred items in `spec.md § Deferred to Future Work` have a tracking destination. The three `NEEDS TRACKING` rows are resolved below in the Deferred-Item Dispositions table; `/speckit-taskstoissues` will create the placeholder issues and back-fill. |

**Post-Phase 1 re-check**: PASS — no new violations introduced by design artifacts. The two small production edits (span attributes `kosmos.tool.outcome` / `kosmos.tool.adapter`) satisfy a pre-existing spec 021 contract obligation and do not require their own ADR.

## Deferred-Item Dispositions (Phase 0 resolution)

The parent dispatch brief explicitly asks Phase 0 to decide or defer three items. All three belong to the `NEEDS TRACKING` rows in spec.md and are resolved here:

| Item (from spec §Deferred) | Phase 0 disposition | Rationale |
|---|---|---|
| Multi-turn follow-up E2E | **DEFER to Context Assembly v2 epic.** This spec asserts the 6-turn scripted sequence only; no new multi-turn test lands under this spec. | Single-turn is the P1 acceptance bar; multi-turn requires the Context Assembly v2 compression policy (vision.md §Layer 5), which is not a scope for scenario 1. `/speckit-taskstoissues` opens a placeholder. |
| DeepEval eval harness integration | **DEFER to observability/eval epic; no harness hook lands here.** `tests/eval/` path is reserved but unused by this spec. | Pipeline correctness ≠ LLM quality. DeepEval is Apache-2.0 and can be added inside a later spec-driven PR without breaking this scenario. `/speckit-taskstoissues` opens a placeholder. |
| Prompt-cache instrumentation for repeated `resolve_location` | **DEFER to cache epic; no cache counters emitted by this spec.** `cache_ttl_seconds=0` fail-closed default remains for both adapters (FR-009). | Cache strategy is a cross-cutting concern tied to the Anthropic "Don't Break the Cache" study (vision.md §References); instrumenting it here would smuggle a policy decision past the spec cycle. The observability assertion in this spec asserts span attributes only. `/speckit-taskstoissues` opens a placeholder. |

## Project Structure

### Documentation (this feature)

```text
specs/030-scenario1-route-safety-rebase/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions with reference mapping
├── data-model.md        # Phase 1 — ScenarioFixture, ObservabilitySnapshot, RunReport
├── contracts/
│   ├── scenario-runner-cli.md   # CLI contract for the scenario runner entry point
│   └── eval-output.schema.json  # JSON schema for the run report artifact
├── quickstart.md        # How to run and extend the scenario locally
└── tasks.md             # Phase 2 output (from /speckit-tasks — NOT created here)
```

### Source Code (repository root — existing layout; no new top-level dirs)

```text
src/kosmos/
├── tools/
│   ├── executor.py              # EDIT — add kosmos.tool.outcome span attr (FR-017)
│   ├── lookup.py                # EDIT — add kosmos.tool.adapter span attr on fetch (FR-018)
│   ├── resolve_location.py      # UNCHANGED — already span-instrumented by executor
│   ├── koroad/
│   │   ├── accident_hazard_search.py  # UNCHANGED — year-quirk logic already in place
│   │   └── code_tables.py             # UNCHANGED — 42→51, 45→52 mappings present
│   └── kma/
│       └── forecast_fetch.py    # UNCHANGED
└── observability/
    └── semconv.py               # UNCHANGED — add string constants only if needed in tests

tests/
├── e2e/
│   ├── __init__.py              # EXISTING
│   ├── conftest.py              # REPLACE — builder for the 030 scenario (NOT the 012 composite)
│   ├── test_route_safety_happy.py      # REPLACE — 6-turn resolve→search→fetch×2→synthesize
│   ├── test_route_safety_degraded.py   # REPLACE — single-adapter + both-adapter failure
│   ├── test_route_safety_quirk.py      # NEW — 강원 42→51 and 전북 45→52 fixture path
│   ├── test_route_safety_spans.py      # NEW — OTel span attribute assertions (FR-017/018/019/020)
│   └── test_route_safety_edge.py       # UPDATE — edge cases from spec.md §Edge Cases
└── fixtures/
    ├── kakao/                   # REUSE / EXTEND — geocoding tape
    ├── koroad/                  # REUSE — accident_hazard_search tapes (add 강원 2023 path)
    └── kma/                     # REUSE — forecast_fetch tape
```

**Structure Decision**: Keep the existing `tests/e2e/` directory but re-author its contents against the two-tool facade. Do not introduce a separate `tests/scenarios/` directory — it would duplicate the `e2e/` contract and fragment scenario ownership. Fixtures continue to live under `tests/fixtures/{provider}/`, consistent with every prior adapter spec.

## Architectural Shape

### Turn-loop shape (what the test actually drives)

```
                 +--------------------------+
                 |  MockLLMClient (scripted)|
                 +-----------+--------------+
                             |
                   StreamEvent[tool_call] x6 in order
                             |
                             v
               +-----------------------------+
  Turn 1:      |  resolve_location("강남구")  |---> ResolveBundle  (Kakao tape)
  Turn 1:      |  resolve_location("서울역")  |---> ResolveBundle  (Kakao tape)
  Turn 2:      |  lookup(mode=search,         |---> LookupSearchOutput
               |    query="사고다발지역 …")    |     (BM25 over in-memory index)
  Turn 3:      |  lookup(mode=fetch,          |---> LookupCollection
               |    tool_id="koroad_…")       |     (KOROAD tape; siDo=51 for 2023)
  Turn 4:      |  lookup(mode=search,         |---> LookupSearchOutput
               |    query="날씨 예보 …")       |
  Turn 5:      |  lookup(mode=fetch,          |---> LookupTimeseries
               |    tool_id="kma_…")          |     (KMA tape)
  Turn 6:      |  StreamEvent[text_delta]     |---> Korean synthesis string
               +-----------------------------+
```

- **Runner layer**: Existing `QueryEngine` (`src/kosmos/engine/engine.py`) — no wrapper, no new runner class. The scenario is a normal `pytest` test that drives `QueryEngine.run()` with the scripted mock client. This is deliberately smaller surface than spec 012's `E2EFixtureBuilder` because the two-tool facade removes the fan-out composite.
- **Turn-loop shape**: The Claude-Code-style async-generator tool loop (Layer 1) is unmodified. The tool loop "just works" once `MockLLMClient` replays the scripted `StreamEvent` sequence against a `ToolRegistry` that has both adapters registered and the two facade tools (`resolve_location`, `lookup`) exposed.
- **Fixture-driven HTTP seam**: `httpx.AsyncClient.get` is patched at the test boundary. URL-pattern matching selects the right tape (Kakao vs KOROAD vs KMA). No `respx`, no `vcrpy` — existing in-repo pattern continues (RQ-1 in research.md).
- **Observability**: OTel `TracerProvider` is configured in the test fixture with an `InMemorySpanExporter`. After `QueryEngine.run()` completes, the test inspects the exported span list. `OTEL_SDK_DISABLED=true` is set for FR-020's graceful-skip variant.

### Eval integration (how the scenario surfaces evidence)

- **Run report**: Every scenario run produces an in-memory `RunReport` (new Pydantic v2 model in `tests/e2e/conftest.py`) holding: trigger query, tool-call order, stop reason, UsageTracker totals, span snapshot, final Korean response. The happy-path test asserts on this structured artifact, not on loose locals.
- **JSON export (optional, for manual debugging)**: When `KOSMOS_E2E_DUMP_DIR` is set, the scenario writes the `RunReport` as JSON to `$KOSMOS_E2E_DUMP_DIR/030-<timestamp>.json` per the `contracts/eval-output.schema.json` contract. Unset by default — CI writes nothing to disk.
- **DeepEval hook point**: `RunReport.final_response` is the canonical surface that a future DeepEval harness would read. We document the shape; we do **not** integrate DeepEval under this spec (deferred — see disposition above).
- **Span extraction**: `RunReport.spans` is a typed snapshot of exported OTel spans filtered by name prefix `execute_tool`. This is the input to FR-017/018/019 assertions.

## Implementation Approach

### Layer integration map

```
tests/e2e/conftest.py (ScenarioFixtureBuilder)
    │
    ├── MockLLMClient (from tests/engine/conftest.py)
    │   └── 6-turn StreamEvent sequence (+ alt sequences for degraded/retry)
    │
    ├── ContextBuilder (real — kosmos.context.builder)
    │   └── System prompt includes resolve_location + lookup only
    │
    ├── ToolRegistry (real — kosmos.tools.registry)
    │   ├── resolve_location        (facade; LLM-visible)
    │   ├── lookup                  (facade; LLM-visible)
    │   ├── koroad_accident_hazard_search  (adapter; lookup-fetch target only)
    │   └── kma_forecast_fetch              (adapter; lookup-fetch target only)
    │
    ├── ToolExecutor (real — kosmos.tools.executor)
    │   └── RecoveryExecutor (real — retry + circuit breaker)
    │
    ├── OTel TracerProvider
    │   └── InMemorySpanExporter  (test-only)
    │
    └── httpx.AsyncClient.get ← PATCHED seam
        └── URL-matched tape replay (Kakao / KOROAD / KMA)
```

### Reference Mapping (Constitution Principle I)

| Design decision | Primary reference | Secondary reference |
|---|---|---|
| Async-generator tool loop driven by `MockLLMClient` | Claude Agent SDK (tool loop) | `claude-code-sourcemap/query.ts` — tool_use / tool_result interleave |
| `resolve → search → fetch` facade sequence | `docs/design/mvp-tools.md §7 Pattern A + B` | Pydantic AI (schema-driven registry) |
| BM25 search gate between model and adapter | `docs/design/mvp-tools.md §5` | Claude Agent SDK (tool definitions) |
| Degraded-path retry (one-shot, retryable=True) | OpenAI Agents SDK (retry matrix) | LangGraph `ToolNode(handle_tool_errors=True)` |
| Circuit-breaker-aware fail-closed on both-adapter outage | `aiobreaker` | `stamina` (bounded backoff) |
| Year-aware KOROAD siDo quirk (2023: 42→51, 45→52) | `PublicDataReader` (data.go.kr wire format ground truth) | `research/data/_converted/koroad_AccidentHazard_CodeList.md` |
| In-memory OTel span capture for assertions | OTel SDK `InMemorySpanExporter` docs | `specs/021-observability-otel-genai/spec.md` (span schema, PII masking) |
| PII masking of citizen query in span attrs | `specs/021-observability-otel-genai/spec.md §FR-* PII` | Claude Code reconstructed (permission model — info-leak guardrails) |
| Recorded-fixture replay via `AsyncMock(httpx.AsyncClient.get)` | `specs/012-scenario1-e2e-route-safety/research.md §RQ-1` | PublicDataReader (wire format ground truth) |
| RunReport as Pydantic v2 aggregate | `docs/vision.md §Layer 1` (immutable per-call snapshots) | Pydantic AI (graph-based state) |

### Production edits (minimal, scoped)

1. **`src/kosmos/tools/executor.py`**
   - On the `execute_tool` span, add `span.set_attribute("kosmos.tool.outcome", "ok" | "error")` exactly once in the `finally` block, derived from `_final_result.success`. This closes FR-017 for all callers (resolve_location, lookup, and any future facade).
2. **`src/kosmos/tools/lookup.py`**
   - When `LookupInput.mode == "fetch"`, attach `span.set_attribute("kosmos.tool.adapter", input.tool_id)` on the current span **only on the fetch path**. `search` and `resolve_location` calls MUST NOT carry this attribute (FR-018 gate).
   - Use the current span (via `trace.get_current_span()`); do not create a second span.
3. **No other production edits.** The `koroad_accident_hazard_search` year-quirk mapping, fail-closed defaults, and V1–V6 invariants are already in place (spec 025 landed in #676).

### Test authoring plan (detail deferred to `/speckit-tasks`)

- **T-happy**: 6-turn scripted sequence; assertions from spec FR-001, FR-005/006/007, FR-015, FR-023.
- **T-degraded**: two sub-cases — KMA-down + retry, KOROAD-down no-retry; assertions from FR-021/022.
- **T-quirk**: 강원 + `year=2023` drives `siDo=51` in outbound URL; mirror fixture for 전북; sanity `year=2022` stays on `siDo=42/45`.
- **T-spans**: in-memory exporter; FR-017 (attribute presence on every tool call); FR-018 (attribute only on fetch spans); FR-019 (no Korean citizen string in exported attrs); FR-020 (graceful skip when `OTEL_SDK_DISABLED=true`).
- **T-edge**: the seven edge cases enumerated in spec.md §Edge Cases; each maps 1:1 to a `pytest.param` case.

## Complexity Tracking

No constitution violations to justify. The two production edits are instrumentation-only, confined to lines already inside spans, and carry no new dependencies.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
