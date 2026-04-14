# Implementation Plan: Phase 1 Live Validation Coverage Extension — Post #291 Modules

**Branch**: `018-phase1-live-extension` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-phase1-live-extension/spec.md`
**Epic**: #380 (extension of #291 live validation)

## Summary

Extend the Phase 1 live-API test suite (merged in #291) to cover two post-merge modules that currently have no live coverage: the Geocoding adapters (Epic #288, Kakao Local API-backed) and the Observability/Telemetry layer (Epic #290). Add two new live test files (`test_live_geocoding.py`, `test_live_observability.py`), one new E2E natural-address scenario in the existing `test_live_e2e.py`, and two new fixtures in `tests/live/conftest.py` (`kakao_api_key`, `kakao_rate_limit_delay`). This is a test-only, additive epic — no production source changes. Every test hard-fails via `pytest.fail()` on missing env vars; none are skipped silently. All live tests remain opt-in via `-m live` and never run in CI.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx >=0.27, pydantic >=2.0, pytest, pytest-asyncio
**Storage**: N/A (test-only; observability snapshots are in-memory test state)
**Testing**: pytest + pytest-asyncio, `@pytest.mark.live` (skipped by default; opt-in via `-m live`)
**Target Platform**: macOS/Linux CLI (local developer workstation)
**Project Type**: CLI application (conversational agent) — test coverage extension
**Performance Goals**: N/A — correctness-only validation, not benchmarking
**Constraints**: Kakao Local API 100k calls/day free-tier quota; data.go.kr 1,000 calls/day per API key; FriendliAI per-minute rate limits; hard-fail on missing env vars
**Scale/Scope**: +7 geocoding tests, +4 observability tests, +1 E2E natural-address test, +2 conftest fixtures (12 new test functions, 0 new source files)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | Additive live-test coverage for existing modules. Test architecture inherits the Claude Agent SDK event-pattern precedent set by #291. No new architectural decisions. |
| II. Fail-Closed Security | PASS | No new adapters, no new production code paths. Tests read existing fail-closed contracts (e.g., `address_to_region` unmapped response) as assertions — they validate fail-closed behavior, never weaken it. |
| III. Pydantic v2 Strict Typing | PASS | No new I/O schemas. Tests assert structural conformance of existing Pydantic models against real Kakao/KOROAD responses. |
| IV. Government API Compliance | PASS | `@pytest.mark.live` keeps tests out of CI (inherited root conftest skip logic from #291). No hardcoded keys. Rate-limit fixtures (`kakao_rate_limit_delay`, existing `_live_rate_limit_pause`) respect daily quotas. |
| V. Policy Alignment | PASS | No policy-relevant code changes. Geocoding + observability are supporting layers, not citizen-data flows. |
| VI. Deferred Work Accountability | PASS | Spec explicitly states "No items deferred — all requirements are addressed in this epic." No unregistered `future/v2/Phase 2+` references in prose. |

## Project Structure

### Documentation (this feature)

```text
specs/018-phase1-live-extension/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (fixture + test-interface contracts)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already written)
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
# NO production source changes — test-only epic.

tests/
├── live/
│   ├── conftest.py                       # EDIT: add kakao_api_key + kakao_rate_limit_delay fixtures
│   ├── test_live_geocoding.py            # NEW: 7 live geocoding tests (Story 1)
│   ├── test_live_observability.py        # NEW: 4 live observability tests (Story 2)
│   └── test_live_e2e.py                  # EDIT: add test_live_scenario1_from_natural_address (Story 3)
```

**Structure Decision**: All changes confined to `tests/live/`. Two new test modules group tests per Epic (#288 → geocoding, #290 → observability); the natural-address E2E case extends the existing E2E module to keep Scenario 1 coverage in one place. Conftest edits add Kakao-specific fixtures alongside the existing KOROAD/FriendliAI fixtures from #291.

## Complexity Tracking

> No constitution violations. No complexity tracking required.

---

## Phase 0: Research

See [research.md](./research.md) for full details.

### Key Decisions

1. **Test file layout**: Per-epic module grouping (`test_live_geocoding.py` for #288, `test_live_observability.py` for #290). E2E natural-address test lives in the existing `test_live_e2e.py` to keep full-scenario coverage co-located.
2. **Kakao env var**: `KOSMOS_KAKAO_API_KEY` (matches `.env` precedent; resolves to the Kakao REST API key).
3. **Kakao rate-limit fixture**: Default 200 ms inter-call delay (`kakao_rate_limit_delay`), adjustable via a private constant. 200 ms × ~20 real calls per test run = well under 100k/day quota.
4. **Hard-fail semantics**: `pytest.fail()` with the exact message `set KOSMOS_KAKAO_API_KEY to run live geocoding tests`, mirroring the `_require_env` pattern already used in `conftest.py`.
5. **Assertion style**: Structural only — key presence, type, numeric ranges (Korea bbox, KMA grid bands). No specific document IDs or accident counts.
6. **Observability test wiring**: Construct a real `MetricsCollector` + `ObservabilityEventLogger` in-test, pass them through the tool executor / LLM client, snapshot counters and event logs pre/post the real call.

### Deferred Items Validation

Spec declares "No items deferred — all requirements are addressed in this epic." Validation confirmed:

- No free-text occurrences of `future epic`, `v2`, `Phase 2+`, `later release`, `separate epic` as deferrals in `spec.md`.
- Single reference to Phase 2 is a scope boundary (TUI out of scope — the Phase 2 layer does not exist yet in this repo), not a deferral.

No `NEEDS TRACKING` markers.

---

## Phase 1: Design

See [data-model.md](./data-model.md) for entity details and [contracts/](./contracts/) for test/fixture contracts.

### Design Decisions

#### D1: Fixture architecture (extend, don't replace)

Existing `tests/live/conftest.py` already exposes `friendli_token`, `data_go_kr_api_key`, `koroad_api_key`, `live_http_client`, and the autouse `_live_rate_limit_pause` (10 s autouse post-test cooldown; primarily motivated by FriendliAI per-minute limits but applies to every live test regardless of backend). We add two new fixtures without touching the existing ones:

- `kakao_api_key` (session-scoped) — reads `KOSMOS_KAKAO_API_KEY`, calls `pytest.fail(f"set KOSMOS_KAKAO_API_KEY to run live geocoding tests")` when unset. Mirrors the `_require_env` helper but with the exact message string required by FR-004.
- `kakao_rate_limit_delay` (function-scoped async) — yields a callable or context manager that sleeps 200 ms between Kakao calls. Implemented via a small async helper invoked explicitly from geocoding tests (autouse would double-delay since `_live_rate_limit_pause` already adds 10 s post-test).

Reference: existing `conftest.py` `_require_env` pattern (tests/live/conftest.py:29) — same hard-fail semantics, different env var name.

#### D2: Geocoding test assertions

| Test | Structural Assertion | Explicitly NOT Asserted |
|------|----------------------|-------------------------|
| `test_live_kakao_search_address_happy` | ≥1 document; `address_name`, `x`, `y` present; `float(x) ∈ [124, 132]`, `float(y) ∈ [33, 39]` | Specific building name, zone_no, road_address |
| `test_live_kakao_search_address_nonsense` | `documents == []`, no exception raised | Which exception would have been raised |
| `test_live_address_to_grid_seoul_landmark` | `nx ∈ [57, 63]`, `ny ∈ [124, 130]` (center 60/127 ±3) | Exact nx/ny value |
| `test_live_address_to_grid_busan_landmark` | `nx ∈ [95, 100]`, `ny ∈ [73, 78]` | Exact nx/ny value |
| `test_live_address_to_region_gangnam` | `sido == "SEOUL"`, `gugun == "SEOUL_GANGNAM"` | Other fields present in response |
| `test_live_address_to_region_busan` | `sido == "BUSAN"` | Specific gugun code (varies by landmark) |
| `test_live_address_to_region_unmapped_region` | Tool returns a structured `ToolResult` where the output indicates unmapped status without raising; `success` and payload shape match the adapter's documented contract | Specific wording of unmapped message |

Reference: Pydantic AI (schema-driven assertions against real responses).

#### D3: Observability test wiring

Each observability test follows a common three-step pattern:

1. **Setup** — Instantiate a fresh `MetricsCollector()` and `ObservabilityEventLogger()`. Wire them into the tool executor / LLM client under test via the same injection surface used in production (the real `engine.run()` pathway). Snapshot `collector.counters` and `logger.events` (or equivalent accessors) immediately before the live call.
2. **Act** — Execute one real tool call (KOROAD accident search for tool/event tests) or one real LLM streaming completion (FriendliAI for LLM tests).
3. **Assert** — Snapshot again post-call; diff the counters and event log. Assertions check counter deltas and event-schema presence only.

Reference: OpenAI Agents SDK telemetry pattern (counter/event assertions in integration tests).

#### D4: Observability test assertions

| Test | Counter Delta | Histogram Delta | Event Assertions |
|------|---------------|-----------------|------------------|
| `test_live_metrics_collector_under_live_tool_call` | `tool.calls.total` += 1 | `tool.latency_ms` has ≥1 sample > 0 | — |
| `test_live_metrics_collector_under_live_llm_stream` | `llm.requests.total` += 1 | `llm.tokens.prompt`, `llm.tokens.completion` each ≥1 sample > 0 | — |
| `test_live_event_logger_emits_tool_events` | — | — | ≥1 `tool.call.started`, ≥1 `tool.call.completed`; each event has `tool_id`, `latency_ms`, `outcome` populated |
| `test_live_event_logger_emits_llm_events` | — | — | ≥1 `llm.stream.started`, ≥1 `llm.stream.completed` with valid schema |

#### D5: E2E natural-address test

Extends `test_live_e2e.py` with `test_live_scenario1_from_natural_address`. The test drives the full QueryEngine pipeline with the user message `"강남역 근처 사고 정보 알려줘"`. Success criteria:

- Recorded tool-call sequence: a geocoding invocation (`address_to_region` or `address_to_grid`) strictly precedes a KOROAD accident-search invocation.
- Final response is a non-empty string containing Hangul characters (`\uac00-\ud7af`).
- Observability event chain includes ≥1 LLM stream pair, ≥1 geocoding tool pair, ≥1 KOROAD tool pair.

No assertions on LLM-generated text content. Reference: Claude Agent SDK event-based assertion pattern (inherited from #291 E2E test).

#### D6: Hard-fail policy (reuse existing primitive)

The existing `_require_env(var_name)` helper in `tests/live/conftest.py:29` already performs `pytest.fail()` with a standard message. For the new Kakao fixture we need a **different** message format (the spec's FR-004 and Story 1 AS-8 demand the exact string `set KOSMOS_KAKAO_API_KEY to run live geocoding tests`). Implementation: write a dedicated `kakao_api_key` fixture with a hardcoded message string rather than parameterizing `_require_env`. Keeps the existing helper unchanged, avoids over-generalization.

#### D7: CI safety (inherited)

Root `tests/conftest.py` from #291 already skips `live`-marked tests unless `-m live` is passed. No changes needed. Verified by SC-005 ("CI continues to pass with identical runtime").

### Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | D3 → OpenAI Agents SDK telemetry. D5 → Claude Agent SDK event pattern. D2 → Pydantic AI schema assertions. |
| II. Fail-Closed Security | PASS | D2 AS-7 explicitly asserts the fail-closed contract (unmapped region → structured response, never crash). Tests strengthen fail-closed guarantees. |
| III. Pydantic v2 Strict Typing | PASS | Tests validate existing Pydantic schemas. No new models. |
| IV. Government API Compliance | PASS | D7 inherits skip logic. No hardcoded keys. Rate-limit fixtures in place for both Kakao and KOROAD. |
| V. Policy Alignment | PASS | No policy-surface changes. |
| VI. Deferred Work Accountability | PASS | Zero deferred items; all requirements addressed in-epic. |
