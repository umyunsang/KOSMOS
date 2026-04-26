# Feature Specification: Phase 1 Live Validation Coverage Extension — Post #291 Modules

**Feature Branch**: `feat/018-phase1-live-extension`
**Created**: 2026-04-14
**Status**: Draft
**Input**: Extend Phase 1 live validation coverage to modules merged after #291 — specifically the Geocoding adapters (Epic #288, Kakao Local API-backed) and the Observability/Telemetry layer (Epic #290). Epic issue: #380.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Live Geocoding Safety Net Before Merge (Priority: P1)

As the KOSMOS student maintainer, before merging any change that touches the geocoding adapter layer (`src/kosmos/tools/geocoding/`, `src/kosmos/tools/kakao/`, or the region/grid resolution helpers), I run `uv run pytest -m live -k geocoding` against the real Kakao Local API to confirm that the adapter still produces usable coordinates, KMA grid cells, and sido/gugun codes for canonical Korean addresses. Mock-based unit tests under `tests/tools/geocoding/` cannot detect Kakao response schema drift, service activation regressions, quota/rate-limit contract changes, or real-world edge cases such as unmapped remote regions — only live traffic can.

**Why this priority**: Geocoding sits at the front of every location-aware Scenario 1 flow. If Kakao silently changes its response shape or the adapter's fallback contract breaks, *every* downstream KOROAD/KMA call inherits the defect. A dedicated live test suite is the earliest cross-layer checkpoint where upstream drift becomes visible.

**Independent Test**: Run `uv run pytest tests/live/test_live_geocoding.py -m live -v` with `KOSMOS_KAKAO_API_KEY` set. Suite delivers value on its own — it is the first live coverage for Epic #288 and surfaces Kakao-side regressions without requiring any other live suite to run.

**Acceptance Scenarios**:

1. **Given** a valid Korean road address "서울특별시 강남구 테헤란로 152" and a set `KOSMOS_KAKAO_API_KEY`, **When** the test calls `search_address` against the real Kakao Local API, **Then** the adapter returns at least one document whose `address_name`, `x`, `y` fields are present and `x`/`y` parse to floats inside the Korea bounding box (longitude 124–132, latitude 33–39).
2. **Given** a clearly invalid query string (e.g., random noise), **When** `search_address` is called live, **Then** the adapter returns an empty documents list without raising — confirming the adapter's empty-result contract matches Kakao's real behavior.
3. **Given** a Seoul landmark address, **When** `address_to_grid` is called live, **Then** the returned KMA grid matches the known Seoul grid reference (nx=60, ny=127) within ±3 tolerance for district-level variance.
4. **Given** a Busan landmark address, **When** `address_to_grid` is called live, **Then** the returned grid falls in the Busan grid band (nx ∈ [95..100], ny ∈ [73..78]).
5. **Given** a Gangnam address, **When** `address_to_region` is called live, **Then** the resolved sido/gugun codes equal SEOUL / SEOUL_GANGNAM.
6. **Given** a Busan address, **When** `address_to_region` is called live, **Then** the resolved sido code equals BUSAN.
7. **Given** a remote / unmapped area query (e.g., "울릉도"), **When** `address_to_region` is called live, **Then** the tool returns a structured "unmapped" response consistent with its documented fail-closed contract — never a crash, exception, or silent None.
8. **Given** `KOSMOS_KAKAO_API_KEY` is unset, **When** any live geocoding test starts, **Then** the suite hard-fails via `pytest.fail()` with the exact message `set KOSMOS_KAKAO_API_KEY to run live geocoding tests` — never xfail, never skip.

---

### User Story 2 — Live Observability Pipeline Verification (Priority: P1)

As the KOSMOS maintainer, before merging any change that touches the observability layer (`src/kosmos/observability/`), the tool executor, or the LLM client, I run live observability tests that exercise the real metrics collector and event logger under real tool and LLM traffic. This verifies that counters actually increment, histograms actually record positive latencies/token counts, and the event schema (`tool.call.started/completed`, `llm.stream.started/completed`) is actually emitted under live pressure — not just under mock conditions that cannot simulate async-boundary races, real token-counting paths, or streaming-chunk timing.

**Why this priority**: Observability is the primary operator-facing signal for Phase 1+. A silent regression where counters stop incrementing or events stop emitting would destroy debuggability without any test failure under the mocked unit suite. Live wiring must be validated cross-layer.

**Independent Test**: Run `uv run pytest tests/live/test_live_observability.py -m live -v` with KOROAD and FriendliAI credentials set. Passes verify the full metrics+events pipeline end-to-end under real backends without requiring the geocoding or E2E suites.

**Acceptance Scenarios**:

1. **Given** a real KOROAD accident-search call routed through the tool executor with observability wired in, **When** the call completes successfully, **Then** `tool.calls.total` counter increments by exactly 1 and `tool.latency_ms` histogram records at least 1 sample with a strictly positive value.
2. **Given** a real FriendliAI K-EXAONE streaming completion routed through `LLMClient` with observability wired in, **When** the stream completes, **Then** `llm.requests.total` counter increments and `llm.tokens.prompt` / `llm.tokens.completion` histograms each record at least one sample with positive value.
3. **Given** a real tool call with the event logger attached, **When** the call completes, **Then** the event logger captured at least one `tool.call.started` event and at least one `tool.call.completed` event, each with valid schema fields (`tool_id`, `latency_ms`, `outcome`) populated.
4. **Given** a real LLM streaming request with the event logger attached, **When** streaming completes, **Then** at least one `llm.stream.started` and one `llm.stream.completed` event are captured with valid schemas.
5. **Given** required env vars (FriendliAI token, KOROAD key) are unset, **When** the observability suite starts, **Then** it hard-fails via `pytest.fail()` naming the missing variable — never xfail, never skip.

---

### User Story 3 — End-to-End Natural-Address Scenario 1 (Priority: P2)

As the KOSMOS maintainer, I need one E2E test that proves the full Scenario 1 chain works from a natural Korean user prompt ("강남역 근처 사고 정보 알려줘") — not a pre-resolved grid/region code. The test must exercise LLM → geocoding (`address_to_region`) → KOROAD accident search → final response, verifying the tool loop invokes geocoding **and** KOROAD in the correct order, produces a non-empty Korean final response, and emits the full observability event chain. This is the single live-integration checkpoint that links Epic #288, Epic #290, and the existing Phase 1 E2E coverage.

**Why this priority**: P2 because Stories 1 and 2 must pass first — this is a composite sanity check. But without it, there is no test that proves the LLM actually *chooses* to call geocoding from a natural Korean prompt, which is the whole product premise.

**Independent Test**: Run `uv run pytest tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address -m live -v`. Passes if the full chain executes end-to-end against real backends.

**Acceptance Scenarios**:

1. **Given** user prompt "강남역 근처 사고 정보 알려줘" and all live credentials set, **When** the CLI/runtime processes the message through the tool loop, **Then** the recorded tool call sequence contains a geocoding tool invocation followed by a KOROAD accident-search invocation (geocoding strictly before KOROAD).
2. **Given** the same prompt, **When** the final response is returned, **Then** the response is a non-empty string containing Korean characters (Hangul range).
3. **Given** the same prompt, **When** the observability recorder is inspected after the run, **Then** the event chain contains at least one LLM stream event, one geocoding tool event pair, and one KOROAD tool event pair — proving cross-layer observability coverage.

---

### Edge Cases

- **Kakao service disabled / 403**: Adapter must bubble the error in a way the live test can distinguish from "no match" (so the test can hard-fail with a clear diagnostic, not silently "pass" an empty result).
- **Kakao quota exhausted (429)**: Test suite must surface the rate-limit error clearly, not flake as a test failure. Use `kakao_rate_limit_delay` fixture between calls to stay under the 100k/day quota.
- **Remote Korean region with no sido/gugun mapping** (e.g., 울릉도, 독도): `address_to_region` must return a structured unmapped response — covered explicitly in AS-7 of Story 1.
- **Partial network failure mid-stream**: LLM streaming tests should not mask silent early-termination; event schema `llm.stream.completed` must only be emitted on clean completion.
- **Korean address with spaces / special characters**: Kakao handles these natively; the adapter must pass them through without mangling URL encoding.
- **Missing optional Kakao fields**: Some results omit `road_address` or `address` variants; structural assertions must check only fields documented as always-present.

## Requirements *(mandatory)*

### Functional Requirements

**Test files to create / modify**

- **FR-001**: System MUST add a new live test file `tests/live/test_live_geocoding.py` implementing all seven geocoding acceptance scenarios from Story 1.
- **FR-002**: System MUST add a new live test file `tests/live/test_live_observability.py` implementing Story 2 acceptance scenarios AS-1 through AS-4 as four test functions. AS-5 (hard-fail on missing env vars) is enforced by the existing session-scoped `friendli_token` and `koroad_api_key` fixtures inherited from #291 (which already call `pytest.fail()` via `_require_env` when unset), not by a dedicated test function.
- **FR-003**: System MUST extend `tests/live/test_live_e2e.py` with a new test `test_live_scenario1_from_natural_address` implementing the three acceptance scenarios from Story 3.
- **FR-004**: System MUST add a `kakao_api_key` fixture to `tests/live/conftest.py` that reads `KOSMOS_KAKAO_API_KEY` and calls `pytest.fail()` with the message `set KOSMOS_KAKAO_API_KEY to run live geocoding tests` if the variable is unset (hard-fail; no `pytest.skip`, no `xfail`).
- **FR-005**: System MUST add a `kakao_rate_limit_delay` fixture to `tests/live/conftest.py` that enforces a minimum delay (configurable, default 200 ms) between successive real Kakao calls within a single test session, to stay under the Kakao Local API free-tier quota.

**Test markers and CI behavior**

- **FR-006**: Every new live test MUST carry the `@pytest.mark.live` marker (and `@pytest.mark.asyncio` where async).
- **FR-007**: New live tests MUST remain skipped by default in CI — no new CI minutes, no new CI secrets required beyond those already documented for Epic #291.
- **FR-008**: New live tests MUST NOT hardcode any API key, token, or other secret in source. All secrets load from environment variables (`KOSMOS_*` prefix per AGENTS.md hard rules).

**Assertion strategy**

- **FR-009**: Assertions MUST be structural (presence of keys, type checks, numeric ranges for well-known geographic bounds) — never specific Kakao document IDs, accident counts, or other values that shift with real-world data.
- **FR-010**: Assertions MUST NOT hide live-only defects. If Kakao returns empty documents for a canonical address, the adapter's fallback behavior must be asserted explicitly; the test must not pass simply because "empty response is permitted."

**Hard-fail policy**

- **FR-011**: Missing env vars MUST trigger `pytest.fail()` with a clear, actionable message (naming the exact env var) — never `pytest.skip`, `xfail`, or silent collection-time bypass.
- **FR-012**: Live-only defects discovered by the new suite (e.g., adapter fallback that masks Kakao 403 as "unmapped") MUST be surfaced as test failures, never suppressed by permissive assertion matchers.

**Rate-limit respect**

- **FR-013**: New KOROAD / KMA live calls in the observability suite are governed by the existing autouse `_live_rate_limit_pause` 10-second post-test cooldown in `tests/live/conftest.py` (inherited from #291), which applies to every live test regardless of backend.
- **FR-014**: New Kakao live calls MUST use the `kakao_rate_limit_delay` fixture (FR-005) to avoid bursting the quota across the geocoding test module.

### Key Entities

- **Live Test Fixture (`kakao_api_key`)**: pytest fixture that resolves the Kakao REST API key from the environment and hard-fails the test if unset. Consumed by every geocoding live test and the E2E natural-address test.
- **Live Test Fixture (`kakao_rate_limit_delay`)**: pytest fixture/autouse hook that enforces a minimum interval between Kakao calls to stay under the daily free-tier quota.
- **Observability Snapshot**: in-test data structure capturing the metrics collector state and the event log before/after a live call, used to assert counter increments and event emission.
- **Recorded Tool-Call Sequence**: ordered list of tool invocations captured during the E2E natural-address test, used to verify geocoding-before-KOROAD ordering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All seven live geocoding tests (`test_live_geocoding.py`) pass against the real Kakao Local API when `KOSMOS_KAKAO_API_KEY` is valid and the Kakao app has the Local API activated (앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON).
- **SC-002**: All four live observability tests (`test_live_observability.py`) pass against real KOROAD + FriendliAI backends, proving counters increment and events emit under real traffic.
- **SC-003**: `test_live_scenario1_from_natural_address` passes end-to-end, with the recorded tool sequence proving `geocoding → KOROAD` ordering from a natural Korean prompt.
- **SC-004**: Missing `KOSMOS_KAKAO_API_KEY` causes `pytest.fail` with the exact expected message — verified by running the suite without the env var set and observing the failure output.
- **SC-005**: `uv run pytest` (without `-m live`) continues to pass with identical runtime and zero new CI minutes — confirmed by comparing CI duration before and after the PR.
- **SC-006**: Running `uv run pytest -m live` locally with all credentials set completes the full extended live suite within a single Kakao free-tier quota envelope (under 100k Kakao calls, under KOROAD daily budget) — i.e., the rate-limit fixtures work.

## Assumptions

- Kakao Developers app has the Local API activated (앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON). Platform registration is NOT required for server-side REST calls — a one-time manual operator step, documented as a prerequisite in the test module docstring.
- FriendliAI and KOROAD credentials remain set under the same env var names used by existing Phase 1 live tests (`KOSMOS_FRIENDLI_TOKEN`, `KOSMOS_KOROAD_API_KEY`, etc.).
- Existing live tests from Epic #291 (`test_live_koroad.py`, `test_live_kma.py`, `test_live_kma_forecast.py`, `test_live_composite.py`, `test_live_llm.py`, `test_live_e2e.py`) continue to pass unchanged — this epic is additive only.
- The geocoding adapter (Epic #288) exposes the three tools referenced here: `search_address`, `address_to_grid`, `address_to_region`. The observability layer (Epic #290) exposes `MetricsCollector` (with counter/histogram APIs) and an event logger accepting the named events.
- The known Seoul-center KMA grid (nx=60, ny=127) and Busan grid band (nx ∈ [95..100], ny ∈ [73..78]) are stable enough to use as structural-range assertions; individual district variance is absorbed by the documented ±3 tolerance.
- The Kakao Local API free-tier quota (100k/day) is large enough for an interactive maintainer run of `-m live` without a rate-limit breach when the 200 ms delay fixture is active.
- CI secrets are NOT updated as part of this epic — live tests remain a local-only workflow per AGENTS.md and Epic #291 precedent.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **New functionality added to geocoding or observability modules** — this epic is test-only. Any change to `src/kosmos/tools/geocoding/` or `src/kosmos/observability/` production code is out of scope and must be routed through its own spec.
- **Mock-based test additions for these modules** — already covered by existing unit tests under `tests/tools/geocoding/` and `tests/observability/`. Re-adding mocks here would duplicate coverage without live value.
- **TUI (Phase 2) live coverage** — the TUI layer does not exist yet in this repo; any live TUI test belongs to Phase 2.
- **Performance benchmarking** — throughput, p99 latency, and load testing are explicitly excluded. Live tests here are correctness-only.
- **Running these tests in CI** — live suite remains local/manual per AGENTS.md precedent. CI continues to skip `-m live`.

### Deferred to Future Work

No items deferred — all requirements are addressed in this epic. This is a narrowly scoped test-only extension; nothing in the description implies follow-up work that belongs to a later epic.
