# Data Model: Scenario 1 E2E — Route Safety

**Date**: 2026-04-13
**Spec**: [spec.md](./spec.md)

---

## Entities

This epic produces **test code only** — no new production data models. The entities below describe the test fixture structures used to drive E2E tests.

### E2EScenarioFixture

A self-contained bundle that configures a complete E2E test run.

| Field | Type | Description |
|-------|------|-------------|
| scenario_name | str | Human-readable scenario identifier (e.g., "route_safety_happy_path") |
| user_message | str | The citizen's Korean-language query |
| llm_responses | list[list[StreamEvent]] | Ordered LLM response sequences for MockLLMClient |
| api_fixtures | dict[str, dict] | Map of API endpoint pattern → recorded JSON response |
| expected_tool_calls | list[str] | Tool IDs expected to be dispatched (assertion target) |
| expected_stop_reason | StopReason | Expected query termination reason |
| expected_token_usage | TokenUsage | Expected cumulative token counts |

### RecordedAPIResponse

Represents a single recorded `data.go.kr` API response for fixture replay.

| Field | Type | Description |
|-------|------|-------------|
| endpoint_pattern | str | URL pattern used to match incoming httpx requests |
| status_code | int | HTTP status code (200, 500, etc.) |
| headers | dict[str, str] | Response headers (Content-Type, etc.) |
| body | dict | Parsed JSON response body |
| fixture_file | str | Path to the JSON fixture file relative to tests/ |

### DegradedScenarioConfig

Configuration for degraded-path test variants.

| Field | Type | Description |
|-------|------|-------------|
| failing_adapters | list[str] | Adapter IDs that should fail (e.g., ["koroad_accident_search"]) |
| failure_mode | str | Type of failure: "timeout", "http_500", "invalid_json", "rate_limited" |
| expected_data_gaps | list[str] | Expected entries in road_risk_score result's data_gaps field |
| should_raise | bool | Whether ToolExecutionError is expected (True when all 3 fail) |

---

## Relationships

```
E2EScenarioFixture
  ├── contains → list[RecordedAPIResponse] (via api_fixtures)
  ├── contains → MockLLMClient config (via llm_responses)
  └── references → DegradedScenarioConfig (for degraded-path variants)

QueryEngine (production)
  ├── uses → MockLLMClient (test substitute for LLMClient)
  ├── uses → ToolRegistry (real, with real tool registrations)
  ├── uses → ToolExecutor + RecoveryExecutor (real)
  ├── uses → PermissionPipeline (real, optional)
  └── uses → ContextBuilder (real)
```

---

## Existing Fixtures to Reuse

| Fixture File | Adapter | Content |
|-------------|---------|---------|
| `tests/tools/koroad/fixtures/koroad_success.json` | koroad_accident_search | Happy-path accident hotspot data |
| `tests/tools/koroad/fixtures/koroad_error.json` | koroad_accident_search | Error response |
| `tests/tools/koroad/fixtures/koroad_empty.json` | koroad_accident_search | Empty result set |
| `tests/tools/kma/fixtures/kma_alert_success.json` | kma_weather_alert_status | Active weather warnings |
| `tests/tools/kma/fixtures/kma_alert_error.json` | kma_weather_alert_status | Error response |
| `tests/tools/kma/fixtures/kma_obs_success.json` | kma_current_observation | Current weather observation |
| `tests/tools/kma/fixtures/kma_obs_error.json` | kma_current_observation | Error response |
