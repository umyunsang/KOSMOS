# Data Model: Phase 1 Final Validation & Stabilization (Live)

**Date**: 2026-04-13

This epic does not introduce new data models. It validates existing models against real API responses. Below documents the entities relevant to live testing.

## Existing Entities Under Validation

### Live Test Configuration

Not a persisted entity — test-time configuration derived from environment.

| Field | Source | Required |
|-------|--------|----------|
| `KOSMOS_FRIENDLI_TOKEN` | Environment variable | Yes |
| `KOSMOS_DATA_GO_KR_API_KEY` | Environment variable | Yes (KMA adapters) |
| `KOSMOS_KOROAD_API_KEY` | Environment variable | Yes (KOROAD adapter) |
| `KOSMOS_FRIENDLI_BASE_URL` | Environment variable | No (defaults to `https://api.friendli.ai/v1`) |
| `KOSMOS_FRIENDLI_MODEL` | Environment variable | No (defaults to `dep89a2fde0e09`) |

### API Response Schemas Under Validation

These Pydantic v2 models are already defined in source code. Live tests validate that real API responses parse correctly into these models.

| Model | Location | Live API |
|-------|----------|----------|
| `KoroadAccidentInput` | `tools/koroad/koroad_accident_search.py` | KOROAD Open Data Portal |
| `KoroadAccidentOutput` | `tools/koroad/koroad_accident_search.py` | KOROAD Open Data Portal |
| `KmaWeatherAlertInput` | `tools/kma/kma_weather_alert_status.py` | data.go.kr KMA |
| `KmaWeatherAlertOutput` | `tools/kma/kma_weather_alert_status.py` | data.go.kr KMA |
| `KmaCurrentObservationInput` | `tools/kma/kma_current_observation.py` | data.go.kr KMA |
| `KmaCurrentObservationOutput` | `tools/kma/kma_current_observation.py` | data.go.kr KMA |
| `RoadRiskInput` | `tools/composite/road_risk_score.py` | Composite (KOROAD + KMA) |
| `RoadRiskOutput` | `tools/composite/road_risk_score.py` | Composite (KOROAD + KMA) |

### QueryEngine Event Model

Live E2E tests assert on `QueryEvent` types emitted by `QueryEngine.run()`:

| Event Type | Expected In Live E2E | Assert On |
|------------|---------------------|-----------|
| `tool_use` | Yes (at least 1) | Event type, tool name is registered |
| `tool_result` | Yes (matching tool_use) | Event type, `success=True` |
| `text_delta` | Yes (at least 1) | Event type, non-empty content |
| `usage_update` | Optional | Token counts > 0 |
| `stop` | Yes (exactly 1, last) | `stop_reason == StopReason.task_complete` |

## State Transitions

No new state transitions introduced. Existing `CircuitBreaker` states (CLOSED → OPEN → HALF_OPEN → CLOSED) are validated under real network conditions but the state machine is unchanged.

## Relationships

```
QueryEngine
  ├── LLMClient (FriendliAI K-EXAONE)
  ├── ToolExecutor
  │   ├── koroad_accident_search → KOROAD API
  │   ├── kma_weather_alert_status → data.go.kr KMA
  │   ├── kma_current_observation → data.go.kr KMA
  │   └── road_risk_score → composite (calls above 3)
  ├── RecoveryExecutor
  │   ├── CircuitBreakerRegistry
  │   └── ResponseCache
  ├── ContextBuilder
  └── PermissionPipeline (NEW wiring — previously None)
      ├── Step 0: bypass-immune checks
      ├── Step 1: config rules
      ├── Steps 2-5: stubs (Phase 1)
      ├── Step 6: sandboxed execution
      └── Step 7: audit log
```
