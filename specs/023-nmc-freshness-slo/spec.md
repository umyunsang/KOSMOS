# Feature Specification: NMC Freshness SLO Enforcement

**Feature Branch**: `023-nmc-freshness-slo`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "NMC Freshness SLO Enforcement: stale_data judgment + hvidate check"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fresh Emergency Room Data Delivery (Priority: P1)

A user asks about nearby emergency rooms. The system fetches real-time bed availability data from the NMC API. The response includes an `hvidate` timestamp indicating when the data was last updated by the upstream source. When this timestamp is recent (within the configured freshness threshold), the system delivers the data to the user with a "fresh" status indicator, giving confidence that the information is current.

**Why this priority**: Emergency room data that appears current but is actually stale can lead to dangerous decisions (e.g., driving to an ER that no longer has beds). Validating freshness on every response is the core safety guarantee.

**Independent Test**: Can be fully tested by providing a response with an `hvidate` value within the threshold and verifying the system returns the data with a "fresh" freshness status.

**Acceptance Scenarios**:

1. **Given** the freshness threshold is configured to 30 minutes, **When** the NMC response contains an `hvidate` that is 10 minutes old, **Then** the system returns the data with `freshness_status: "fresh"`.
2. **Given** the freshness threshold is configured to 30 minutes, **When** the NMC response contains an `hvidate` that is exactly 30 minutes old, **Then** the system returns the data with `freshness_status: "fresh"` (boundary: equal-to-threshold is fresh).

---

### User Story 2 - Stale Data Rejection (Priority: P1)

A user asks about nearby emergency rooms, but the upstream NMC data has not been refreshed recently. The `hvidate` timestamp exceeds the configured freshness threshold. Instead of silently delivering outdated information, the system returns a structured error indicating that the data is stale. The LLM agent can then communicate this to the user transparently rather than presenting potentially dangerous outdated bed counts.

**Why this priority**: Equally critical to Story 1 — the safety guarantee requires that stale data is never silently passed through. This is the enforcement half of the SLO.

**Independent Test**: Can be fully tested by providing a response with an `hvidate` value beyond the threshold and verifying the system returns a stale_data error instead of the data.

**Acceptance Scenarios**:

1. **Given** the freshness threshold is configured to 30 minutes, **When** the NMC response contains an `hvidate` that is 31 minutes old, **Then** the system returns a structured error with reason "stale_data" and does not return the bed availability data.
2. **Given** the freshness threshold is configured to 30 minutes, **When** the NMC response contains an `hvidate` that is 1440 minutes old, **Then** the system returns a structured error with reason "stale_data".

---

### User Story 3 - Configurable Freshness Threshold (Priority: P2)

An operator adjusts the freshness threshold via the `KOSMOS_NMC_FRESHNESS_MINUTES` environment variable to match their deployment's acceptable staleness window. The threshold is clamped to a safe range of 1 to 1440 minutes (1 minute to 24 hours) to prevent misconfiguration.

**Why this priority**: Different deployment environments may have different tolerance for data staleness. Configurability supports production flexibility without code changes.

**Independent Test**: Can be fully tested by setting the environment variable to various values (within range, boundary values, default) and verifying the freshness check uses the configured threshold.

**Acceptance Scenarios**:

1. **Given** `KOSMOS_NMC_FRESHNESS_MINUTES` is set to 60, **When** the NMC response contains an `hvidate` that is 59 minutes old, **Then** the system treats the data as fresh.
2. **Given** `KOSMOS_NMC_FRESHNESS_MINUTES` is not set, **When** the system starts, **Then** the freshness threshold defaults to 30 minutes.
3. **Given** `KOSMOS_NMC_FRESHNESS_MINUTES` is set to 0, **When** the system starts, **Then** the value is rejected with a validation error (pydantic `ge=1` constraint).

---

### Edge Cases

- What happens when the `hvidate` field is missing or empty in the NMC response? The system treats the data as stale (fail-closed per Constitution Section II).
- What happens when the `hvidate` field contains an unparseable value? The system treats the data as stale and returns a stale_data error.
- What happens when the system clock and the NMC server clock are slightly out of sync? The freshness check uses a comparison against the configured threshold, not absolute wall-clock alignment. Minor clock drift within the threshold window is acceptable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compare the `hvidate` timestamp in every NMC emergency room response against the current time to determine data freshness.
- **FR-002**: System MUST classify data as "fresh" when the age of `hvidate` is less than or equal to `KOSMOS_NMC_FRESHNESS_MINUTES`.
- **FR-003**: System MUST classify data as "stale" when the age of `hvidate` exceeds `KOSMOS_NMC_FRESHNESS_MINUTES`.
- **FR-004**: When data is stale, the system MUST return a structured error with reason "stale_data" instead of returning the bed availability data.
- **FR-005**: When data is fresh, the system MUST include `freshness_status: "fresh"` metadata in the response envelope.
- **FR-006**: When data is stale, the stale_data error MUST include a human-readable message stating the data age and the configured threshold.
- **FR-007**: The `KOSMOS_NMC_FRESHNESS_MINUTES` configuration MUST default to 30 minutes and be clamped to the range [1, 1440].
- **FR-008**: When `hvidate` is missing, empty, or unparseable, the system MUST treat the data as stale (fail-closed).

### Key Entities

- **Freshness Status**: A classification of NMC response data as either "fresh" or "stale", determined by comparing the `hvidate` field age against the configured threshold.
- **hvidate**: A timestamp field in the NMC API response representing when the upstream data was last updated by the National Medical Center.
- **Freshness Threshold**: A configurable duration (in minutes) representing the maximum acceptable age of NMC data before it is considered stale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of NMC emergency room responses are validated for freshness before being delivered to users.
- **SC-002**: Stale data (exceeding the configured threshold) is never silently delivered to users; it always results in a structured stale_data error.
- **SC-003**: Fresh data is delivered with an explicit freshness status indicator, enabling the LLM agent to communicate data currency to users.
- **SC-004**: Missing or malformed `hvidate` values are caught and treated as stale in 100% of cases (fail-closed guarantee).
- **SC-005**: The freshness threshold is configurable without code changes, supporting deployment flexibility.

## Assumptions

- The NMC API `hvidate` field uses a parseable Korean datetime format (e.g., `YYYY-MM-DD HH:MM:SS` or similar).
- The system clock on the deployment server is reasonably synchronized (within a few minutes of NMC server time).
- The existing `KOSMOS_NMC_FRESHNESS_MINUTES` setting in the configuration module is the canonical source for the threshold value.
- The existing `stale_data` reason in the error taxonomy is the correct classification for this error type.
- The NMC adapter currently has an auth gate that short-circuits before the handler; freshness enforcement will be added to the response processing path that runs after a successful upstream fetch.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Automatic retry or fallback to cached data when stale data is detected — the system reports staleness; the LLM agent decides how to communicate it to the user.
- NMC server-side freshness monitoring or alerting — KOSMOS only validates at the point of consumption.
- Freshness enforcement for non-NMC adapters — each adapter's freshness semantics differ; this epic covers NMC only.

### Deferred to Future Work

No items deferred — all requirements are addressed in this epic.
