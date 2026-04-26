# Feature Specification: Phase 1 Hardening — LLM Rate-Limit Resilience & KOROAD Tool Input Discipline

**Feature Branch**: `019-phase1-hardening`
**Created**: 2026-04-14
**Status**: Draft
**Input**: Epic #404 — Phase 1 live validation (#291, #380) surfaced two defects that mocked tests could not catch: (1) EXAONE producing incorrect district-level admin codes when the natural-language query targets a specific Seoul district ("강남역" → the assistant filled `gu_gun=110` / Jongno instead of `gu_gun=680` / Gangnam), and (2) HTTP 429 rate-limit failures mid-stream against FriendliAI Serverless. This feature hardens the Phase 1 MVP so it can be released and Phase 2 can start.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Correct district returned for a district-named natural-language query (Priority: P1)

A citizen opens the KOSMOS CLI and asks, in natural Korean, about traffic accidents near a well-known Seoul landmark (e.g., "강남역 근처 사고 정보 알려줘"). The assistant must consult an authoritative geocoding source for the administrative region instead of guessing from model memory, and return accident data for the correct district.

**Why this priority**: The current assistant can confidently return data for the *wrong* district (Jongno instead of Gangnam) while sounding correct. This is a trust-breaking failure mode that makes the whole Phase 1 MVP unsafe to ship: a citizen believes they got accident statistics for Gangnam when the numbers actually describe Jongno. This outranks every other hardening item.

**Independent Test**: Run the live end-to-end scenario "강남역 근처 사고 정보 알려줘" and inspect the recorded tool-use events. The first authoritative accident-search tool invocation must carry the administrative codes that correspond to Seoul/Gangnam, not to any other district. The final Korean-language answer must reference Gangnam, not Jongno.

**Acceptance Scenarios**:

1. **Given** a citizen asks "강남역 근처 사고 정보 알려줘", **When** the assistant invokes the accident-search tool, **Then** the first invocation's administrative codes match Seoul/Gangnam and a geocoding tool was invoked before the accident-search tool.
2. **Given** the same question is asked multiple times across independent sessions, **When** the accident-search tool is invoked, **Then** the administrative codes are Seoul/Gangnam on every session (no probabilistic drift).
3. **Given** a citizen asks about a landmark in a different city (e.g., Busan), **When** the assistant invokes the accident-search tool, **Then** the first invocation's administrative codes correspond to that city, not to any Seoul district.

---

### User Story 2 — Live validation suite completes without rate-limit failures (Priority: P1)

A KOSMOS maintainer runs the full live validation suite locally before declaring Phase 1 complete. The suite must complete without any test failing because of upstream rate limiting, and must complete at least as fast as the current suite that relies on a blind 60-second cooldown between multi-turn steps.

**Why this priority**: Without a dependable suite, the maintainer cannot certify Phase 1 closure, and Phase 2 cannot start. The current mitigation (blind 60-second sleep) is brittle — it has already failed in practice after the upstream free tier ended — and it also inflates suite runtime.

**Independent Test**: Run the full live validation suite (all live-marked tests) in a single session. Count how many tests failed because of a rate-limit error. Record the wall-clock time of the multi-turn scenario and compare it to the previous baseline.

**Acceptance Scenarios**:

1. **Given** the full live suite is executed, **When** every live-marked test finishes, **Then** zero tests fail because of a rate-limit error from the LLM provider.
2. **Given** the LLM provider responds with a rate-limit error that carries a provider-specified retry delay, **When** the assistant retries, **Then** the assistant waits at least that delay before retrying and ultimately succeeds within a bounded retry budget.
3. **Given** two LLM calls are initiated concurrently within the same session, **When** both execute, **Then** they do not execute in parallel at the provider — they are serialized so the per-minute bucket is not spiked.
4. **Given** the multi-turn scenario is run, **When** it completes, **Then** its wall-clock time is less than or equal to the baseline that included the fixed 60-second cooldown.

---

### User Story 3 — Public record corrected (Priority: P2)

A future reader of the project's public discussion thread about Phase 1 live validation must not be misled into believing that the Korean LLM reliably memorizes Korean district administrative codes. The record must state the empirical counter-example and the adopted mitigation.

**Why this priority**: The earlier discussion thread is now the de facto architectural rationale for choosing the Korean LLM. Leaving the unretracted claim in place risks a future contributor building new features on a false premise.

**Independent Test**: Open the referenced public discussion thread. Verify that a retraction comment exists, that it cites the counter-example, and that it names the adopted mitigation.

**Acceptance Scenarios**:

1. **Given** a reader opens the public discussion thread referenced by this epic, **When** they read to the end, **Then** they see a dated retraction comment identifying the empirical counter-example and linking to this epic.
2. **Given** the retraction comment exists, **When** a contributor searches the thread for the phrase the epic retracts, **Then** it is clear that the earlier claim no longer stands.

---

### Edge Cases

- The LLM provider returns a rate-limit error **without** a provider-specified retry delay. The system must still back off on its own with increasing waits and a bounded retry count, and must still fail loudly once the budget is exhausted.
- The LLM provider returns a rate-limit error **during** an already-started streaming response (not only at the start). The system must treat this the same as a pre-stream rate-limit error and must not surface a half-streamed response to the user as if it were complete.
- The LLM provider returns a rate-limit error on **every** retry within the budget. The system must raise an explicit, categorized error so the test suite can surface it rather than returning an empty or partial answer.
- The citizen's natural-language query names a **region outside Seoul** (e.g., a Busan landmark). The system must still consult geocoding first and must not mix in a Seoul district code by accident.
- The citizen's natural-language query names an **unmapped remote region** (e.g., Ulleung-do). The geocoding step must return a structured "unmapped" response, and the assistant must not fabricate an administrative code to fill the accident-search tool input.
- The citizen's query names **no region at all**. The geocoding-first rule does not apply, and the accident-search tool should not be invoked speculatively with memorized codes.
- Two live test runs are triggered close together (rerun after a flaky network). The second run must not be penalized by per-minute bucket exhaustion from the first run beyond the bucket's natural refill time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST consult an authoritative geocoding source for a district/region whenever the citizen's natural-language query names a district, neighborhood, landmark, or address, before invoking any tool that requires administrative codes.
- **FR-002**: The system MUST NOT fill administrative region codes into authoritative-data tool inputs from LLM memory; codes MUST be traceable to a prior geocoding tool invocation in the same session.
- **FR-003**: Documentation surfaced to the LLM for administrative-region tool inputs MUST explicitly forbid memory-fill, state the required source of the codes, and reference the enumerated valid-code sets.
- **FR-004**: The session-level guidance shown to the LLM MUST include an ordering rule that geocoding comes before any location-coded authoritative query.
- **FR-005**: When the LLM provider returns a rate-limit error and a provider-specified retry delay is available, the system MUST respect that delay before retrying.
- **FR-006**: When the LLM provider returns a rate-limit error with no provider-specified retry delay, the system MUST apply increasing waits between retries with randomized jitter, capped per-attempt and in total number of attempts.
- **FR-007**: Rate-limit handling MUST apply both before the response has started streaming and after streaming has already started.
- **FR-008**: When the retry budget is exhausted, the system MUST surface a categorized failure to the caller rather than silently succeed with a partial or empty response.
- **FR-009**: Within a single session, concurrent calls to the LLM MUST be serialized so they do not compound the per-minute bucket pressure.
- **FR-010**: Default LLM sampling and generation parameters MUST align with the current published recommendations for the model the system uses; callers MUST still be able to override any default explicitly.
- **FR-011**: The live end-to-end scenario that asks about a named Seoul district MUST include an automated check that the first authoritative accident-search invocation carries the administrative codes for that district, and MUST fail if it does not.
- **FR-012**: The live multi-turn scenario MUST no longer rely on a fixed cooldown between turns; its success MUST come from rate-limit handling and concurrency control, not from a timed wait.
- **FR-013**: Existing non-live tests (LLM client, tools, context assembly) MUST continue to pass without change in assertions, with only the default-parameter change accepted as a routine update.
- **FR-014**: The project's public discussion thread about Phase 1 live validation MUST receive a retraction entry that cites the empirical counter-example and links to this epic.

### Key Entities

- **Administrative region code pair**: A (sido, gugun) pair drawn from the project's enumerated code tables and obtained from a geocoding call; the unit that must NOT be invented from LLM memory.
- **Rate-limit retry policy**: A policy governing how the system reacts to provider rate-limit errors — includes respecting provider-specified delays, a bounded retry count, increasing waits with jitter, and a terminal failure mode.
- **Session-level concurrency gate**: A per-session control that serializes LLM calls so that two calls from the same session never race against the same per-minute bucket.
- **Tool-input guidance block**: The machine-readable text attached to each tool input field that the LLM reads when deciding how to fill that field.
- **Session guidance block**: The session-level instructions given to the LLM at turn start that set ordering rules for tool use.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a single live-suite run, zero tests fail because of an LLM-provider rate-limit error.
- **SC-002**: The live end-to-end test for the "강남역" query passes with the first accident-search invocation carrying the Seoul / Gangnam administrative code pair, on every run across three consecutive runs.
- **SC-003**: When the LLM provider returns a rate-limit error during or before a streaming response, the system recovers in at least 95% of observed occurrences within the retry budget, and surfaces a categorized failure in the remaining occurrences.
- **SC-004**: The live multi-turn scenario's wall-clock time is less than or equal to the current baseline (which includes a 60-second blind cooldown).
- **SC-005**: The existing non-live test suite (LLM client, tools, context) is 100% green after the change, with no assertion rewrites beyond accepting the new default parameter values.
- **SC-006**: The public discussion thread carries a retraction comment dated on or after the merge, and that comment links to this epic.
- **SC-007**: The KOSMOS maintainer can declare Phase 1 release-ready — meaning the live suite passes fully and the discussion record is corrected — within one iteration of this feature.

## Assumptions

- The project's enumerated administrative-code tables are authoritative for the scope of Phase 1 and cover the regions reachable through the geocoding adapter.
- The LLM provider's rate-limit error is surfaced with a standard HTTP status that the client can detect both before and during a streaming response.
- The LLM provider honors its own retry-delay hint when it chooses to send one; when it omits the hint, a bounded exponential-style wait is an acceptable client-side substitute.
- A single session running LLM calls strictly serialized through one gate is enough to stay under the per-minute bucket at the tier this project now occupies; this assumption will be re-examined if the tier changes.
- The published sampling and generation recommendations for the Korean LLM apply to the latency-sensitive, non-reasoning interactive path that Phase 1 uses, and do not need to be overridden for the Phase 1 scenarios.
- The live validation suite runs off-CI, under the maintainer's own provider quota; cost per full run remains bounded within the project's existing allowance.
- The geocoding adapter's behavior for well-known Seoul landmarks (including "강남역") returns Gangnam-level resolution, not only city-level resolution.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Replacing the Korean LLM with a different provider — the point of this feature is to make the current choice safe, not to walk away from it.
- Adding defense-in-depth validation inside the accident-search adapter for arbitrary (sido, gugun) pairs — the upstream authoritative API remains the source of truth and returning its error is the right behavior.
- Any change to the TUI, which belongs to a later phase of the project.
- Extending this work to other citizen scenarios beyond the route-safety scenario already covered.
- Adding new endpoints to the geocoding or weather adapters.
- Moving to a higher LLM provider tier beyond the one this project now occupies.
- Running the live validation suite inside continuous integration — it remains a local, maintainer-run gate.

### Deferred to Future Work

No items deferred — all requirements are addressed in this epic.
