# Phase 0 Research: Phase 1 Final Validation & Stabilization (Live)

**Date**: 2026-04-13
**Branch**: `014-phase1-live-validation`

## Research Questions & Findings

### RQ-1: Current State of Live Test Infrastructure

**Question**: What live test infrastructure currently exists?

**Finding**: Zero `@pytest.mark.live` tests exist anywhere in the codebase. The marker is registered in `pyproject.toml` with `addopts = "--strict-markers"`, but no test files use it. The `tests/` directory contains only mock-based unit, integration, and E2E tests. There is no root-level `tests/conftest.py` to handle marker-based test selection.

**Decision**: Create `tests/live/` package with dedicated conftest and per-component test files.
**Rationale**: Separate directory clearly isolates live tests from mock tests, making it easy to include/exclude by path or marker.
**Alternatives considered**: (1) Co-locate live tests alongside mock tests with marker only — rejected because it mixes concerns and increases risk of accidentally running live tests in CI. (2) Separate top-level `tests_live/` directory — rejected because it breaks pytest's default test discovery and existing `pyproject.toml` config.

### RQ-2: PermissionPipeline Wiring Gap

**Question**: Why is PermissionPipeline not connected to QueryEngine, and what's needed to wire it?

**Finding**: `QueryContext` in `engine/models.py` already declares `permission_pipeline: PermissionPipeline | None = None` (line 108) and `permission_session: SessionContext | None = None` (line 116). However, `QueryEngine.__init__` (engine/engine.py:44-56) does not accept these parameters, and `QueryEngine.run()` creates `QueryContext` without them (engine/engine.py:159-165). The `query()` async generator in `engine/query.py` already checks `ctx.permission_pipeline` and invokes it when non-None — the plumbing downstream is complete.

**Decision**: Add optional `permission_pipeline` and `permission_session` parameters to `QueryEngine.__init__`. Pass to `QueryContext` in `run()`.
**Rationale**: Minimal change — the downstream `query()` function already handles the pipeline. Only the injection point is missing.
**Alternatives considered**: (1) Require PermissionPipeline (non-optional) — rejected because it would break all existing tests and the CLI startup path needs a gradual opt-in. (2) Global registry pattern — rejected per constitution (avoid unnecessary abstractions).

### RQ-3: Environment Variable Inconsistencies

**Question**: What env var naming inconsistencies exist between .env.example and source code?

**Finding**:
1. `.env.example` line 18: `KOSMOS_DATA_GO_KR_KEY=` — but all source code reads `KOSMOS_DATA_GO_KR_API_KEY` (kma_current_observation.py:278, kma_weather_alert_status.py:233, permissions/models.py:27). A developer copying `.env.example` to `.env` and filling in keys will get a `ConfigurationError` when running KMA adapters.
2. `.env.example` line 41 comments: `Base URL: https://api.friendli.ai/serverless/v1` — but `LLMClientConfig.base_url` defaults to `https://api.friendli.ai/v1`. The `/serverless/v1` path is the correct endpoint for FriendliAI Serverless tier. The code's default `/v1` may work if FriendliAI redirects, but the documented endpoint should match.

**Decision**: Fix `.env.example` to use `KOSMOS_DATA_GO_KR_API_KEY`. Add comment documenting the base URL discrepancy and verifying correct endpoint during live testing.
**Rationale**: `.env.example` is the developer onboarding entry point — it must match the code exactly.

### RQ-4: Test Fixture State

**Question**: What test fixtures exist and what gaps need filling?

**Finding**:
- `tests/fixtures/koroad/koroad_accident_search.json` — exists, needs live comparison
- `tests/fixtures/kma/` — directory exists but is EMPTY. No KMA fixtures recorded.
- `tests/fixtures/README.md` — exists, documents fixture recording workflow

**Decision**: During live testing, capture representative responses for KMA adapters. Compare existing KOROAD fixture against live response. Update any drifted fixtures.
**Rationale**: Empty KMA fixtures directory means mock tests for KMA are using inline fixtures or builder patterns rather than file-based fixtures. Live testing will reveal if inline fixtures match real API response structure.

### RQ-5: Live Test Hard-Fail Implementation

**Question**: How to implement hard-fail behavior when APIs are unreachable?

**Finding**: Standard pytest approach would use `pytest.skip()` with `reason`. However, per clarification decision, live tests must fail (not skip) on API unavailability.

**Decision**: No special handling needed — `httpx.ConnectError` and `httpx.TimeoutException` naturally propagate as test failures. The only guard is the root `conftest.py` that skips live tests when `-m live` is not passed.
**Rationale**: The simplest approach: let network errors be test failures. No defensive `try/except/skip` patterns.

### RQ-6: Live E2E Test Design

**Question**: How to structurally validate the E2E pipeline without asserting on LLM-generated content?

**Finding**: The `QueryEngine.run()` yields `QueryEvent` objects with types: `text_delta`, `tool_use`, `tool_result`, `usage_update`, `stop`. For Scenario 1, the expected event sequence is:
1. At least one `tool_use` event (LLM decides to call KOROAD/KMA adapters)
2. Corresponding `tool_result` events with `success=True`
3. `text_delta` events (LLM generates Korean response)
4. `stop` event with `stop_reason=StopReason.task_complete`

**Decision**: Assert on event types and structural fields only. Do not assert on `text_delta` content or specific tool argument values (LLM decides these dynamically).
**Rationale**: LLM output is non-deterministic. Structural assertions verify the pipeline works end-to-end; subjective quality is validated manually per SC-02.
**Reference**: Claude Agent SDK — async generator event-based testing pattern.

## Deferred Items Validation

Scanned `spec.md` for unregistered deferral patterns:

| Pattern | Found In | Tracked? |
|---------|----------|----------|
| "Phase 2" | Scope Boundaries section (3 instances) | Yes — all 3 in Deferred Items table |
| "covered by Epic #12" | Out of Scope section | N/A — permanent exclusion, not deferral |
| "Phase 2+" | Deferred Items table | Yes — tracked |

**Result**: No unregistered deferrals found. All "Phase 2" and "future" references are properly tracked in the Deferred Items table.
