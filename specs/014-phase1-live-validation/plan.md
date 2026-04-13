# Implementation Plan: Phase 1 Final Validation & Stabilization (Live)

**Branch**: `014-phase1-live-validation` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/014-phase1-live-validation/spec.md`

## Summary

Create a `@pytest.mark.live` test suite that validates all Phase 1 components (KOROAD, KMA adapters, FriendliAI LLM client, composite road_risk_score, QueryEngine pipeline) against real external APIs. Fix cross-layer defects exposed by live testing, wire PermissionPipeline into QueryEngine, resolve env-var naming inconsistencies, and synchronize test fixtures with current live API responses.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx >=0.27, pydantic >=2.0, pydantic-settings >=2.0
**Storage**: N/A (in-memory session state only)
**Testing**: pytest + pytest-asyncio, `@pytest.mark.live` for real API tests
**Target Platform**: macOS/Linux CLI
**Project Type**: CLI application (conversational agent)
**Performance Goals**: N/A — functional correctness validation, not benchmarking
**Constraints**: data.go.kr 1,000 calls/day per API key; live tests must hard-fail on API unavailability
**Scale/Scope**: 4 API adapters, 1 composite tool, 1 LLM client, 1 query engine

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | Validation epic — tests existing architecture. No new architectural decisions requiring reference mapping. |
| II. Fail-Closed Security | PASS | No new adapters. PermissionPipeline wiring preserves existing fail-closed defaults (steps 2-5 are pass-through stubs). |
| III. Pydantic v2 Strict Typing | PASS | No new I/O schemas. Existing schemas validated against live API responses. |
| IV. Government API Compliance | PASS | FR-003: `@pytest.mark.live` tests skipped in CI by default. Existing `pyproject.toml` marker config already supports this. No hardcoded keys. |
| V. Policy Alignment | PASS | No policy changes. |
| VI. Deferred Work Accountability | PASS | 3 deferred items tracked in spec's Deferred Items table with NEEDS TRACKING markers. |

## Project Structure

### Documentation (this feature)

```text
specs/014-phase1-live-validation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
# Existing source code — NO new modules created
src/kosmos/
├── cli/app.py                           # Fix: env var naming
├── engine/engine.py                     # Fix: wire PermissionPipeline into QueryContext
├── engine/models.py                     # Already has permission_pipeline field (unused)
├── llm/config.py                        # Fix: base_url default vs .env.example
├── tools/kma/kma_current_observation.py # Validate against live response
├── tools/kma/kma_weather_alert_status.py# Validate against live response
├── tools/koroad/koroad_accident_search.py# Validate against live response
└── tools/composite/road_risk_score.py   # Validate full orchestration

# New test files — all under tests/
tests/
├── conftest.py                          # NEW: root conftest with live marker skip logic
├── live/                                # NEW: live test package
│   ├── __init__.py
│   ├── conftest.py                      # Shared live test fixtures (API clients, credentials)
│   ├── test_live_koroad.py              # KOROAD adapter live validation
│   ├── test_live_kma.py                 # KMA adapters live validation
│   ├── test_live_llm.py                 # FriendliAI LLM client live validation
│   ├── test_live_composite.py           # road_risk_score composite live validation
│   └── test_live_e2e.py                 # Full Scenario 1 pipeline structural validation
├── fixtures/
│   ├── kma/                             # UPDATE: sync with live responses
│   │   ├── weather_alert_status.json    # NEW: captured from live API
│   │   └── current_observation.json     # NEW: captured from live API
│   └── koroad/
│       └── koroad_accident_search.json  # UPDATE: verify against live response

.env.example                             # Fix: KOSMOS_DATA_GO_KR_KEY → KOSMOS_DATA_GO_KR_API_KEY
```

**Structure Decision**: All live tests grouped under `tests/live/` to clearly separate from mock-based tests. No new source modules — only test files and defect fixes in existing source.

## Complexity Tracking

> No constitution violations. No complexity tracking required.

---

## Phase 0: Research

See [research.md](./research.md) for full details.

### Key Decisions

1. **Live test directory**: `tests/live/` — separate package for clear isolation from mock tests.
2. **Hard-fail policy**: Tests use direct `httpx` calls with no fallback skip; `ConnectionError` / `TimeoutError` = test failure.
3. **PermissionPipeline wiring**: `QueryEngine.__init__` accepts optional `PermissionPipeline` and `SessionContext`; passes them to `QueryContext`. No behavior change when `None` (backward-compatible).
4. **Env var fix**: `.env.example` corrected to `KOSMOS_DATA_GO_KR_API_KEY`. Base URL documented with note on serverless vs standard endpoint.
5. **Fixture sync strategy**: Live tests capture response structure; developer manually compares and updates fixtures after confirmed drift.

### Deferred Items Validation

| Item | Tracking Issue | Status |
|------|---------------|--------|
| Automated live test scheduling in CI | #344 | Valid deferral — requires secrets management |
| PermissionPipeline steps 2-5 full implementation | #345 | Valid deferral — Phase 2 scope |
| Additional scenario live validation (Scenarios 2-6) | #346 | Valid deferral — Phase 2+ scope |

No unregistered deferral patterns found in spec prose. All "Phase 2" and "future" references are tracked.

---

## Phase 1: Design

See [data-model.md](./data-model.md) for entity details.

### Design Decisions

#### D1: Live Test Architecture

Live tests are organized as a dedicated `tests/live/` package:

- **`conftest.py`**: Shared fixtures providing pre-configured `httpx.AsyncClient`, API keys from env vars, and credential validation helpers. Tests fail immediately if required env vars are missing.
- **Per-adapter tests**: Each adapter gets its own test file validating request/response against the real API.
- **E2E structural test**: Validates the full pipeline (QueryEngine → LLM → ToolExecutor → adapters) produces expected events (tool_use, tool_result, text_delta, stop) without asserting on LLM-generated text content.

Reference: Claude Agent SDK (async generator loop) — event-based assertion pattern.

#### D2: PermissionPipeline QueryEngine Wiring

`QueryContext` already declares `permission_pipeline: PermissionPipeline | None` and `permission_session: SessionContext | None` fields (engine/models.py:108-118). The gap is that `QueryEngine.__init__` and `QueryEngine.run()` never populate these fields.

Fix approach:
1. Add optional `permission_pipeline` and `permission_session` parameters to `QueryEngine.__init__`.
2. Pass them through to `QueryContext` creation in `run()` (engine.py:159-165).
3. No changes to `query()` function — it already reads `ctx.permission_pipeline` and invokes it when non-None.

Reference: OpenAI Agents SDK (guardrail pipeline) — optional pipeline injection pattern.

#### D3: Environment Variable Fixes

Two inconsistencies discovered:

| File | Current | Correct | Action |
|------|---------|---------|--------|
| `.env.example:18` | `KOSMOS_DATA_GO_KR_KEY=` | `KOSMOS_DATA_GO_KR_API_KEY=` | Rename variable |
| `.env.example:41` | `Base URL: https://api.friendli.ai/serverless/v1` | Document both endpoints | Add comment noting `LLMClientConfig` default is `/v1`; `/serverless/v1` is the FriendliAI Serverless tier endpoint |

#### D4: Live Test Assertions Strategy

Live API responses are non-deterministic. Assertion strategy:

| Component | Assert | Do NOT Assert |
|-----------|--------|---------------|
| KOROAD adapter | Response is `ToolResult(success=True)`, output matches `KoroadAccidentOutput` schema, `items` is a list | Specific accident data values |
| KMA weather alert | Response is `ToolResult(success=True)`, output matches schema | Specific alert content (may be empty list) |
| KMA observation | Response is `ToolResult(success=True)`, output has expected field keys | Specific observation values |
| LLM client | SSE stream yields chunks, final message has `role="assistant"` | Content of generated text |
| E2E pipeline | Event sequence includes `tool_use` + `tool_result` + `text_delta` + `stop` | Text content of LLM response |
| Composite tool | Returns `RoadRiskOutput` with valid `risk_level` enum value | Specific risk score values |

#### D5: Root conftest.py for Live Marker

Currently no `tests/conftest.py` exists. Create one to ensure `@pytest.mark.live` tests are properly skipped when not explicitly selected:

```python
# tests/conftest.py
def pytest_collection_modifyitems(config, items):
    if "live" not in config.getoption("-m", default=""):
        skip_live = pytest.mark.skip(reason="live tests require -m live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
```

This ensures CI never accidentally runs live tests even without explicit `-m "not live"`.

### Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | D1 references Claude Agent SDK event pattern. D2 references OpenAI Agents SDK guardrail pipeline. |
| II. Fail-Closed Security | PASS | PermissionPipeline wiring is additive; `None` default preserves existing behavior. |
| III. Pydantic v2 Strict Typing | PASS | Live tests validate existing Pydantic schemas against real data. |
| IV. Government API Compliance | PASS | D5 ensures live tests are never run in CI. No hardcoded keys. |
| V. Policy Alignment | PASS | No changes. |
| VI. Deferred Work Accountability | PASS | All deferrals tracked. |
