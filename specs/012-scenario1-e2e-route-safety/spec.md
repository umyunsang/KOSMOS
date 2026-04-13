# Feature Specification: Scenario 1 E2E — Route Safety

**Feature Branch**: `013-scenario1-e2e-route-safety`
**Created**: 2026-04-13
**Status**: Draft
**Input**: Epic #12 — Scenario 1 E2E — Route Safety

---

## Overview & Context

This epic is the Phase 1 capstone — an end-to-end integration test that validates the complete KOSMOS pipeline for the route safety citizen scenario. A citizen asks a natural-language question about travel safety, and the system fuses data from three government API sources (KOROAD accident hotspots, KMA weather alerts, KMA current observation) via the composite road risk score tool to produce an actionable Korean-language safety recommendation.

All upstream dependencies (Epics #4–#11) are completed: LLM client, query engine, tool system, API adapters, permission pipeline, context assembly, error recovery, and CLI. This epic proves that all layers work together as an integrated whole.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Happy-Path Route Safety Query (Priority: P1)

A citizen types a natural-language question about route safety. KOSMOS discovers and invokes the relevant tools (KOROAD accident search, KMA weather alert, KMA current observation), fuses results through the road risk composite adapter, and returns a coherent Korean-language safety recommendation.

**Why this priority**: This is the fundamental proof that the entire Phase 1 pipeline works end-to-end. Without this, Phase 1 cannot be considered complete.

**Independent Test**: Can be fully tested by sending a pre-defined user message through the QueryEngine with recorded API fixtures and a deterministic mock LLM, then asserting that all expected tool calls were made and a synthesized response was produced.

**Acceptance Scenarios**:

1. **Given** a configured QueryEngine with recorded API fixtures and a mock LLM that requests the road_risk_score tool, **When** the citizen sends "내일 부산에서 서울 가는데, 안전한 경로 추천해줘", **Then** the engine dispatches the road_risk_score composite tool which fans out to KOROAD + KMA endpoints, and the final response contains route safety information in Korean.
2. **Given** the same setup, **When** the query completes, **Then** the conversation history contains assistant messages with tool_calls and tool results in the correct order.
3. **Given** the same setup, **When** the query completes, **Then** the UsageTracker reflects accurate token counts for all LLM calls made during the turn.

---

### User Story 2 - Degraded-Path: Single API Failure (Priority: P2)

One of the three underlying APIs (KOROAD or KMA) is unavailable. The road risk composite adapter tolerates partial failures and returns a degraded but still useful response with data gaps clearly noted.

**Why this priority**: Government APIs are unreliable by nature (maintenance windows, rate limits, timeouts). Graceful degradation is essential for citizen trust.

**Independent Test**: Can be tested by configuring one API fixture to return an error response while others succeed, then asserting the composite adapter produces a result with `data_gaps` populated and the final response still contains useful safety information.

**Acceptance Scenarios**:

1. **Given** KOROAD returns a 500 error while KMA endpoints succeed, **When** the road risk composite tool executes, **Then** the result includes weather data with a `data_gaps` entry for accident data, and the risk score uses fallback defaults.
2. **Given** KMA weather alert returns a timeout while KOROAD and KMA observation succeed, **When** the composite tool executes, **Then** the result includes accident and observation data with a `data_gaps` entry for weather alerts.
3. **Given** all three inner adapters fail, **When** the composite tool executes, **Then** a ToolExecutionError is raised and the engine produces a graceful error message to the citizen.

---

### User Story 3 - Cost Accounting Verification (Priority: P3)

Every LLM call and API invocation during the E2E flow is accurately tracked in the session budget. Token usage matches expected values from the mock LLM, and API call counts are recorded.

**Why this priority**: Cost accountability is a first-class concern — taxpayer-funded services must track every API call and token spent.

**Independent Test**: Can be tested by running the full E2E flow with known mock LLM token counts, then asserting the UsageTracker totals match expected input/output token sums.

**Acceptance Scenarios**:

1. **Given** a mock LLM configured to report specific token counts per call, **When** the E2E flow completes with two LLM iterations (tool call + final answer), **Then** the UsageTracker total equals the sum of all reported token usages.
2. **Given** the same setup, **When** the flow completes, **Then** the rate limiter records show exactly one call per API endpoint invoked.

---

### User Story 4 - Permission Pipeline Integration (Priority: P3)

Tool calls pass through the 7-step permission gauntlet when a session context is provided. The audit step records all tool invocations for compliance.

**Why this priority**: Permission enforcement is mandatory for PIPA compliance, but P1 scope uses API-key auth only (no citizen PII), making this lower priority than core pipeline validation.

**Independent Test**: Can be tested by running the E2E flow with a PermissionPipeline and SessionContext attached, then asserting audit log entries are created for each tool call.

**Acceptance Scenarios**:

1. **Given** a QueryEngine configured with a PermissionPipeline and a public-auth SessionContext, **When** a route safety query completes, **Then** audit log entries exist for each tool invocation with tool_id, timestamp, and result status.
2. **Given** the same setup, **When** a tool call targets a requires_auth=True tool without proper credentials, **Then** the permission pipeline denies the call and the engine includes a denial message in the response.

---

### Edge Cases

- What happens when the LLM requests a tool that is not registered in the registry?
- What happens when the LLM enters an infinite tool-call loop (max_iterations guard)?
- What happens when the LLM stream is interrupted mid-response (StreamInterruptedError retry)?
- What happens when the token budget is exceeded mid-turn (BudgetExceededError)?
- What happens when the mock LLM returns tool call arguments that fail Pydantic validation?
- What happens when the circuit breaker is open for an API endpoint?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute the full query pipeline end-to-end: user message → context assembly → LLM stream → tool dispatch → result injection → LLM synthesis → final response.
- **FR-002**: System MUST dispatch the road_risk_score composite tool, which fans out to koroad_accident_search, kma_weather_alert_status, and kma_current_observation in parallel.
- **FR-003**: System MUST use recorded JSON fixtures for all API responses — no live `data.go.kr` calls in CI tests.
- **FR-004**: System MUST produce a final assistant message containing route safety information in Korean after tool results are injected.
- **FR-005**: System MUST accurately track token usage across all LLM calls in the UsageTracker.
- **FR-006**: System MUST tolerate partial API failures in the composite adapter, returning degraded results with `data_gaps` populated.
- **FR-007**: System MUST raise ToolExecutionError when all three inner adapters of the composite tool fail.
- **FR-008**: System MUST record audit entries for each tool invocation when a PermissionPipeline is active.
- **FR-009**: System MUST terminate the query loop when max_iterations is reached.
- **FR-010**: System MUST handle StreamInterruptedError with a single retry before yielding an unrecoverable stop.
- **FR-011**: System MUST handle BudgetExceededError by yielding a stop event with api_budget_exceeded reason.
- **FR-012**: System MUST handle invalid tool arguments from the LLM by returning a ToolResult with success=False and validation error details.
- **FR-013**: System MUST verify that the preprocessing pipeline compresses context when token count exceeds the configured threshold.

### Key Entities

- **E2EScenarioFixture**: A self-contained test fixture bundle containing mock LLM response sequences and recorded API response JSON files for a specific citizen scenario.
- **RecordedAPIResponse**: A JSON file capturing a real `data.go.kr` API response for replay in tests — includes headers, status code, and body.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The happy-path E2E test completes successfully with all assertions passing — tool calls dispatched, results fused, Korean response synthesized.
- **SC-002**: The degraded-path test demonstrates graceful degradation when 1 or 2 of 3 APIs fail — partial results returned with data gaps noted.
- **SC-003**: Token usage reported by the UsageTracker after an E2E run matches the sum of mock LLM token counts within 0% deviation (deterministic mocks).
- **SC-004**: All E2E tests run without any live API calls — verified by absence of real HTTP requests (all intercepted by mocks/fixtures).
- **SC-005**: The test suite completes in under 10 seconds (no network I/O, no sleep, deterministic mocks).
- **SC-006**: Edge case tests cover at minimum: unknown tool, infinite loop guard, stream interruption retry, budget exceeded, invalid tool arguments, and circuit breaker open.

## Assumptions

- All Layer 1–6 modules and CLI are implemented and passing their unit tests (Epics #4–#11 closed).
- The mock LLM client pattern from `tests/engine/conftest.py` (MockLLMClient with pre-configured StreamEvent sequences) is the established testing approach and will be reused.
- Recorded API fixtures follow the existing pattern: JSON files under `tests/tools/*/fixtures/` loaded via `json.loads(Path.read_text())`.
- The road_risk_score composite adapter's partial-failure tolerance (asyncio.gather with return_exceptions=True) is already implemented and unit-tested.
- The E2E tests test the integration of existing modules — no new production source code is required, only test code and fixtures.
- The existing `@pytest.mark.live` convention is used to separate recorded-fixture tests (run in CI) from live-API tests (skipped in CI).

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Live API testing against `data.go.kr` — E2E tests use recorded fixtures only (constitution rule IV)
- CLI/TUI rendering tests — this epic tests the engine pipeline, not terminal output formatting
- LLM response quality evaluation (DeepEval, semantic similarity) — E2E tests verify pipeline mechanics, not AI output quality
- Performance benchmarking or load testing — this epic validates correctness, not throughput

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Multi-turn conversation E2E (follow-up questions) | Single-turn validation is the P1 scope; multi-turn requires context assembly v2 | Epic #17 — Context Assembly v2 | #317 |
| Geocoding integration in E2E (free-text address → coordinates) | Geocoding adapter not yet implemented | Epic #288 — Geocoding Adapter | #288 |
| LLM output quality metrics (DeepEval, semantic evaluation) | Requires evaluation framework setup; orthogonal to pipeline correctness | Epic #290 — Observability & Telemetry | #290 |
| Scenario 2–5 E2E tests | Different API adapters required (HIRA, 119, MOHW, Gov24) | Epics #18, #19, #23, #24 | #18, #19, #23, #24 |
