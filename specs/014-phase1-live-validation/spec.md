# Feature Specification: Phase 1 Final Validation & Stabilization (Live)

**Feature Branch**: `014-phase1-live-validation`  
**Created**: 2026-04-13  
**Status**: Draft  
**Epic**: #291  
**Input**: User description: "Phase 1 Final Validation & Stabilization (Live) — run the entire system against real Live APIs (data.go.kr + FriendliAI K-EXAONE) to surface cross-layer integration defects and fix them."

## Clarifications

### Session 2026-04-13

- Q: When a live API endpoint is unreachable during test execution, should the test skip or fail? → A: Hard fail. Live tests exist to verify real API behavior; skipping on unavailability creates false green results that defeat the epic's purpose.
- Q: Should the E2E Scenario 1 validation be fully automated, fully manual, or hybrid? → A: Hybrid. Automated pytest tests validate pipeline structure (tool calls fire, response contains expected data fields, no errors). Manual CLI sessions validate subjective quality (coherent Korean response from K-EXAONE). Both are required for SC-02.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live API Test Suite Execution (Priority: P1)

A developer runs the live test suite to validate that all Phase 1 adapters, the LLM client, and the composite tool work correctly against real external APIs (data.go.kr, KOROAD portal, FriendliAI K-EXAONE).

**Why this priority**: Without live test coverage, the system has zero verified behavior against real APIs. Mock-based tests cannot catch SSE chunk boundary mismatches, response schema drift, XML-in-JSON gateway errors, or real Korean tool call argument quality from K-EXAONE. This is the foundational deliverable that makes all other validation possible.

**Independent Test**: Can be fully tested by running `uv run pytest -m live` with valid API credentials and verifying all tests pass. Delivers confidence that each adapter and the LLM client work with real APIs.

**Acceptance Scenarios**:

1. **Given** valid `KOSMOS_FRIENDLI_TOKEN`, `KOSMOS_DATA_GO_KR_API_KEY`, and `KOSMOS_KOROAD_API_KEY` environment variables are set, **When** the developer runs `uv run pytest -m live`, **Then** all live-marked tests pass with real API responses. If any external API is unreachable, tests fail (not skip) to prevent false green results.
2. **Given** the KOROAD adapter is tested against the live API, **When** a valid `sido_code` and `accident_type` are provided, **Then** the adapter returns structured accident hotspot data matching the Pydantic output schema.
3. **Given** the KMA weather alert adapter is tested against the live API, **When** a request is made, **Then** the adapter returns structured alert data (or an empty list if no active alerts) without errors.
4. **Given** the KMA current observation adapter is tested against the live API with valid grid coordinates, **When** a request is made for recent data, **Then** the adapter returns observation data with expected field structure.
5. **Given** the FriendliAI LLM client is tested against the live API, **When** a Korean-language prompt with tool definitions is sent, **Then** the client receives and parses SSE streaming chunks correctly, including tool call arguments.

---

### User Story 2 - End-to-End CLI Scenario 1 Conversation (Priority: P1)

A user launches the KOSMOS CLI and conducts a Scenario 1 conversation ("safe route recommendation") using real K-EXAONE for reasoning and real data.go.kr/KOROAD APIs for data, verifying the full pipeline from user input through tool execution to Korean-language response.

**Why this priority**: Individual adapter tests confirm component-level correctness, but only a full end-to-end flow verifies that the QueryEngine, ToolExecutor, RecoveryExecutor, ContextBuilder, and LLM client orchestrate correctly together with real external services.

**Independent Test**: Validated in two complementary ways: (1) Automated live pytest validates pipeline structure — tool calls fire, response contains expected data fields, no errors. (2) Manual CLI session validates subjective response quality — coherent Korean route recommendation from real K-EXAONE.

**Acceptance Scenarios**:

1. **Given** the KOSMOS CLI is started with valid credentials, **When** the user sends "내일 부산에서 서울 가는데, 안전한 경로 추천해줘", **Then** the system issues tool calls to KOROAD and KMA adapters, computes a road risk score, and returns a Korean route recommendation based on real data. Automated validation confirms tool calls and data fields; manual review confirms response coherence.
2. **Given** the user has received an initial route recommendation, **When** the user sends a follow-up "대전-천안 구간 사고 이력 더 자세히 알려줘", **Then** the system maintains conversation context and issues additional tool calls to provide detailed accident history.
3. **Given** the system is streaming a response, **When** the user presses Ctrl+C, **Then** the streaming cancels cleanly and the terminal state is restored without corruption.

---

### User Story 3 - Cross-Layer Defect Discovery and Remediation (Priority: P2)

A developer discovers and fixes defects that only manifest when hitting real APIs — including SSE chunk boundary issues, XML-in-JSON gateway errors, response schema drift, environment variable inconsistencies, and unconnected pipeline components.

**Why this priority**: These defects are invisible behind mocks and represent the primary risk to production readiness. However, they are dependent on the live test infrastructure from User Stories 1 and 2 to be discovered systematically.

**Independent Test**: Can be tested by running the full test suite (mock + live) after all fixes are applied and verifying zero failures across both test categories.

**Acceptance Scenarios**:

1. **Given** a defect is discovered during live testing (e.g., XML-in-JSON response from data.go.kr), **When** the developer fixes the adapter or client, **Then** both the live test and all existing mock-based tests pass.
2. **Given** environment variable naming inconsistencies exist (e.g., `.env.example` vs source code), **When** corrections are applied, **Then** a developer following `.env.example` can successfully run the system without errors.
3. **Given** the PermissionPipeline is not wired into QueryEngine, **When** the wiring is completed, **Then** permission checks fire during actual engine execution and audit trail entries are recorded.

---

### User Story 4 - API Response Fixture Synchronization (Priority: P2)

A developer compares live API responses against existing test fixtures and updates any that have drifted, ensuring mock-based tests remain representative of real API behavior.

**Why this priority**: Fixtures that no longer match live responses create a false sense of security — mock tests pass but the system fails with real data. This synchronization is important but depends on live test infrastructure being in place first.

**Independent Test**: Can be tested by comparing fixture files against live API responses and verifying structural consistency (field names, data types, nesting).

**Acceptance Scenarios**:

1. **Given** existing fixtures for KOROAD and KMA responses, **When** compared against live API responses, **Then** any structural mismatches (renamed fields, added/removed fields, changed data types) are identified and documented.
2. **Given** a fixture mismatch is found, **When** the fixture is updated, **Then** all mock-based tests that use the fixture are updated to match and continue to pass.

---

### User Story 5 - Stateful Component Live Behavior Verification (Priority: P3)

A developer verifies that stateful components (RateLimiter, CircuitBreaker, UsageTracker) behave correctly under real API call patterns, including actual network latency, real rate limit responses, and accurate token consumption tracking.

**Why this priority**: These components have been tested with mocks that respond instantly. Real-world timing, latency, and actual rate limit behavior may expose edge cases. However, this is lower priority because the core architecture is sound — this is refinement.

**Independent Test**: Can be tested by running a sequence of live API calls that exercise rate limiting thresholds and observing CircuitBreaker state transitions and UsageTracker token counts against real K-EXAONE responses.

**Acceptance Scenarios**:

1. **Given** multiple rapid live API calls to KOROAD (exceeding `rate_limit_per_minute=10`), **When** the rate limiter activates, **Then** the RecoveryExecutor returns a rate-limit degradation result rather than an API error.
2. **Given** a live K-EXAONE conversation, **When** token usage is tracked, **Then** the UsageTracker records actual token counts (not estimates) from real API responses.

---

### Edge Cases

- What happens when the data.go.kr API returns an XML gateway error wrapped in an HTTP 200 response?
- How does the system handle API key daily quota exhaustion (data.go.kr 1000-call/day limit)?
- What happens when the FriendliAI SSE stream has unexpected chunk boundaries or partial JSON?
- How does the system behave when K-EXAONE generates malformed tool call arguments in Korean?
- What happens when KMA current observation is called for a time period with no available data?
- How does the circuit breaker behave under real network timeout conditions (not instant mock failures)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `@pytest.mark.live` test suite that validates each Phase 1 API adapter (KOROAD accident search, KMA weather alerts, KMA current observation) against real API endpoints. Tests MUST fail (not skip) when an API endpoint is unreachable.
- **FR-002**: System MUST provide a live end-to-end test that validates the full Scenario 1 pipeline structure (tool calls fire, response contains expected data fields, no errors) via automated pytest. Subjective response quality (coherent Korean output) is validated via manual CLI session.
- **FR-003**: System MUST skip all `@pytest.mark.live` tests by default in CI, executing only when explicitly selected via `uv run pytest -m live`.
- **FR-004**: System MUST handle the data.go.kr XML-in-JSON gateway error pattern (HTTP 200 with `<OpenAPI_ServiceResponse>` body) gracefully, returning a structured error rather than crashing.
- **FR-005**: System MUST correctly parse FriendliAI SSE streaming responses including tool call chunks with varying boundary positions.
- **FR-006**: System MUST wire the PermissionPipeline into the QueryEngine execution path so that permission checks and audit trail recording fire during actual engine runs.
- **FR-007**: System MUST maintain consistent environment variable naming between `.env.example` documentation and source code configuration classes.
- **FR-008**: System MUST update test fixtures to match current live API response structures when drift is detected.
- **FR-009**: System MUST validate that the composite `road_risk_score` tool correctly orchestrates multiple live adapter calls and produces a valid risk assessment.
- **FR-010**: System MUST ensure the full existing test suite (unit + integration + E2E mock-based) continues to pass after all live validation fixes are applied.

### Key Entities

- **Live Test Configuration**: Environment variables, API credentials, test markers, and skip conditions that control live test execution.
- **API Response Fixture**: Recorded JSON snapshots of real API responses used as reference for mock-based tests, requiring synchronization with live API behavior.
- **Defect Record**: A cross-layer integration issue discovered during live testing, including root cause analysis, affected layers, and remediation applied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-01**: All `@pytest.mark.live` tests pass when run with valid API credentials (`uv run pytest -m live` exits with code 0).
- **SC-02**: A complete Scenario 1 pipeline is validated via (a) automated live pytest confirming tool calls fire and response structure is correct, and (b) manual CLI session confirming coherent Korean route safety recommendation from real K-EXAONE + real data.go.kr.
- **SC-03**: Multi-turn conversation context retention is confirmed — a follow-up question receives a contextually consistent response referencing prior conversation content.
- **SC-04**: All cross-layer defects discovered during live testing are fixed and documented.
- **SC-05**: API response fixtures match current live API response structures (field names, data types, nesting) or are updated to match.
- **SC-06**: The complete test suite (`uv run pytest` — unit + integration + E2E + live) achieves zero failures.
- **SC-07**: The PermissionPipeline is wired into the QueryEngine execution path, with audit trail entries confirmed during live CLI sessions.

## Assumptions

- Valid API credentials (KOSMOS_FRIENDLI_TOKEN, KOSMOS_DATA_GO_KR_API_KEY, KOSMOS_KOROAD_API_KEY) are available and have sufficient quota for testing.
- The FriendliAI K-EXAONE serverless endpoint is operational and accepts the configured model ID.
- data.go.kr and KOROAD portal APIs are available and responding within normal latency ranges during test execution.
- The existing mock-based test suite (847+ tests) passes as a precondition before any live validation work begins.
- Live tests are run manually by a developer, not in CI — CI continues to run only mock-based tests.
- The data.go.kr daily API call limit (1000 calls/day) is sufficient for the live test suite execution.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Mock-based test additions — covered by Epic #12; this epic focuses exclusively on live API validation.
- TUI development — Phase 2 (Epic #287); CLI is the only user interface validated here.
- New API adapter development — only existing Phase 1 adapters (KOROAD, KMA weather alerts, KMA current observation) are validated.
- Performance benchmarking or load testing — this epic validates functional correctness, not performance characteristics.
- PermissionPipeline steps 2-5 implementation — these are intentional stubs in Phase 1; only the wiring of the pipeline into QueryEngine and audit trail (steps 0, 1, 6, 7) is verified.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Automated live test scheduling in CI | Requires secrets management and dedicated API quota; not feasible in student portfolio CI | Phase 2 — CI Infrastructure | #344 |
| PermissionPipeline steps 2-5 full implementation | Intentionally stubbed in Phase 1 design; full implementation planned for Phase 2 | Phase 2 — Permission Pipeline v2 | #345 |
| Additional scenario live validation (Scenarios 2-6) | Phase 1 only covers Scenario 1; other scenarios are Phase 2+ | Phase 2+ — Additional Scenarios | #346 |
