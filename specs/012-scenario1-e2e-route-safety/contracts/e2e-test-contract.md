# E2E Test Contract: Route Safety Scenario

**Date**: 2026-04-13

---

## Test Module Interface

### tests/e2e/conftest.py — E2EFixtureBuilder

Assembles a fully-wired QueryEngine for E2E testing.

```
E2EFixtureBuilder:
    build() → QueryEngine
        - MockLLMClient with configured response sequences
        - Real ToolRegistry with all Phase 1 tools registered
        - Real ToolExecutor with real adapters + RecoveryExecutor
        - Real ContextBuilder with real ToolRegistry
        - Optional PermissionPipeline with SessionContext

    with_llm_responses(responses: list[list[StreamEvent]]) → self
    with_api_fixture(adapter_id: str, fixture_name: str) → self
    with_api_failure(adapter_id: str, failure_mode: str) → self
    with_permission_pipeline(session_context: SessionContext) → self
    with_budget(token_budget: int) → self
```

### Test Execution Pattern

```
async def test_e2e_scenario():
    # 1. Build engine with fixtures
    engine = E2EFixtureBuilder()
        .with_llm_responses([tool_call_events, text_answer_events])
        .with_api_fixture("koroad_accident_search", "koroad_success.json")
        .with_api_fixture("kma_weather_alert_status", "kma_alert_success.json")
        .with_api_fixture("kma_current_observation", "kma_obs_success.json")
        .build()

    # 2. Run query
    events = [e async for e in engine.run("citizen query")]

    # 3. Assert pipeline behavior
    assert_tool_calls_dispatched(events, ["road_risk_score"])
    assert_final_response_contains(events, expected_keywords)
    assert_usage_matches(engine, expected_tokens)
```

### httpx Mock Seam

API adapters call `httpx.AsyncClient.get(url, params=...)`. E2E tests patch this method to return recorded fixture responses based on URL pattern matching.

```
Patch target: httpx.AsyncClient.get
Match strategy: URL contains adapter-specific path segment
    - "/getOldRoadTrficAccidentDeath" → koroad fixture
    - "/getWthrWrnList" → kma_alert fixture
    - "/getUltraSrtNcst" → kma_obs fixture
Return: httpx.Response(status_code, json=fixture_data)
```

### Assertion Helpers

```
assert_tool_calls_dispatched(events, expected_tool_ids: list[str])
    - Filter events for type="tool_use"
    - Verify each expected tool_id appears in dispatched calls

assert_final_response_contains(events, keywords: list[str])
    - Concatenate all type="text_delta" events
    - Assert each keyword appears in the final text

assert_usage_matches(engine, expected: TokenUsage)
    - Compare engine._state.usage totals against expected values

assert_stop_reason(events, expected: StopReason)
    - Find the type="stop" event
    - Verify stop_reason matches expected

assert_data_gaps(events, expected_gaps: list[str])
    - Parse tool_result events for road_risk_score
    - Verify data_gaps field contains expected entries
```
