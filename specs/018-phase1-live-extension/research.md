# Phase 0 Research: Phase 1 Live Validation Coverage Extension

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-04-14

## 0. Reference Mapping (Constitution Principle I)

Every design decision traces to a concrete reference from `docs/vision.md § Reference materials` or established KOSMOS precedent.

| Design Area | Primary Reference | Rationale |
|---|---|---|
| Live-test architecture (event-based assertions) | Claude Agent SDK (async generator loop) | Matches #291 E2E test pattern; assert on event shape, not LLM text. |
| Telemetry assertions (counter/event diff) | OpenAI Agents SDK (guardrail/telemetry pipeline) | Inject collector + logger, snapshot before/after, diff the deltas. |
| Structural schema assertions | Pydantic AI (schema-driven registry) | Assert response conforms to existing Pydantic models; never assert specific values. |
| Rate-limit / hard-fail fixture pattern | Existing `tests/live/conftest.py` (from #291) | Inherit `_require_env` + `_live_rate_limit_pause` pattern; add Kakao-specific equivalents. |
| Fail-closed validation (unmapped region) | KOSMOS adapter contract (`address_to_region` docstring) | AS-7 asserts the documented fail-closed behavior — tests strengthen, never loosen. |

No architectural changes. This is a test-coverage extension that inherits #291's reference set.

---

## 1. Decisions

### D1: Test file layout — per-Epic grouping

**Decision**: Create `tests/live/test_live_geocoding.py` for Epic #288 coverage and `tests/live/test_live_observability.py` for Epic #290 coverage. Extend (not replace) `tests/live/test_live_e2e.py` with the Scenario 1 natural-address test.

**Rationale**:
- Per-epic file grouping matches the existing #291 layout (`test_live_koroad.py`, `test_live_kma.py`, `test_live_llm.py`, `test_live_composite.py`, `test_live_e2e.py`).
- Keeps failure diagnostics easy: a failing `test_live_geocoding.py::test_*` points operators directly at Kakao / #288.
- The E2E natural-address case is a composite Scenario 1 flow, which already has a home in `test_live_e2e.py`.

**Alternatives rejected**:
- Single `test_live_phase1_extension.py` — would mix Kakao-only failures with KOROAD/FriendliAI-only failures, obscuring root cause.
- Separate `test_live_natural_address.py` — fragments Scenario 1 coverage across files.

### D2: Env var naming for Kakao — `KOSMOS_KAKAO_API_KEY`

**Decision**: Use `KOSMOS_KAKAO_API_KEY` as the env var for the Kakao REST API key.

**Rationale**:
- Matches the `KOSMOS_` prefix hard rule (AGENTS.md).
- Matches the local `.env` precedent already in place (verified during the prior session — file contains `KOSMOS_KAKAO_API_KEY=...`).
- Spec FR-004 mandates the exact failure message `set KOSMOS_KAKAO_API_KEY to run live geocoding tests`; the env var name and the message must stay in sync.

**Alternatives rejected**:
- `KOSMOS_KAKAO_REST_API_KEY` — more verbose, doesn't match `.env` precedent, would require renaming the existing local secret.
- `KAKAO_API_KEY` (no prefix) — violates AGENTS.md hard rule.

### D3: Kakao rate-limit fixture — 200 ms default delay

**Decision**: Implement `kakao_rate_limit_delay` as an explicit (non-autouse) async helper that sleeps 200 ms between Kakao calls.

**Rationale**:
- Free-tier quota is 100,000 calls/day. A 200 ms floor is orders of magnitude under the quota and prevents burst-pattern throttling during a single test-suite run.
- Non-autouse design: the existing `_live_rate_limit_pause` autouse fixture already adds 10 s of post-test cooldown for FriendliAI. Making the Kakao delay autouse would double-delay observability/E2E tests that don't call Kakao at all.
- 200 ms is the same rate-limit order used by data.go.kr fixtures and FriendliAI cooldown logic — consistent developer experience.

**Alternatives rejected**:
- Autouse 200 ms pause — applies overhead to non-Kakao tests for no benefit.
- 1-second delay — unnecessarily slows the geocoding suite (~7 tests × 3 calls each = ~21 s of avoidable wait).
- No rate-limit fixture — violates FR-014 and risks quota breach on iterative local runs.

### D4: Hard-fail message — exact string from spec

**Decision**: `pytest.fail("set KOSMOS_KAKAO_API_KEY to run live geocoding tests")` — no formatting, no trailing period, no prefix.

**Rationale**:
- Spec Story 1 AS-8 and FR-004 pin this string verbatim. SC-004 verifies by running without the env var and checking the exact output.
- Keeping the string literal rather than f-string parameterization makes the assertion test (SC-004) simple: `grep` for the literal.

### D5: Observability test instrumentation approach

**Decision**: In each observability test, instantiate a fresh `MetricsCollector()` and `ObservabilityEventLogger()` and inject them into the tool executor / LLM client via the same seam production code uses. Snapshot `counters`/`events` state, run the real call, snapshot again, diff.

**Rationale**:
- Mirrors OpenAI Agents SDK telemetry-integration pattern (wire the real collector, exercise the real code path, observe side effects).
- Tests validate the wiring itself — not just the collector API. A silent regression where the executor stops calling the collector would be caught.
- Avoids the trap of mock-based assertions that "pass" because the mock is also called, but the real side effect never happens.

**Alternatives rejected**:
- Singleton/global collector inspection — fragile across parallel test runs and hides wiring bugs.
- Mock-backed collector — defeats the entire point of a live test.

### D6: Assertion policy — structural only

**Decision**: All geocoding assertions are structural (key presence, type, numeric range). All observability assertions are counter/histogram deltas and event-schema presence.

**Rationale**:
- Kakao, KOROAD, and FriendliAI all return non-deterministic data. Asserting specific values guarantees flaky tests.
- Structural assertions still catch every class of defect the spec enumerates: schema drift, empty-document contracts, grid-reference shifts, region-code mapping breakage, event-schema regressions.
- Matches the #291 precedent: all existing live tests use structural assertions.

**Alternatives rejected**:
- Snapshot assertions on response bodies — high noise, low signal.
- Specific-value assertions (e.g., exact nx/ny) — false failures on Kakao routing updates, district-boundary re-draws, etc.

### D7: E2E natural-address — event-chain structural assertion

**Decision**: Assert tool-call sequence ordering (geocoding strictly before KOROAD), non-empty Hangul-containing final response, and presence of the three event pairs (LLM stream, geocoding tool, KOROAD tool) in the observability log.

**Rationale**:
- The premise of KOSMOS Scenario 1 is that the LLM *chooses* to call geocoding from a natural Korean prompt. This test is the single checkpoint that verifies the choice actually happens in production wiring.
- Ordering assertion (geocoding before KOROAD) catches a latent regression where the LLM skips geocoding and calls KOROAD directly with a hallucinated region code — a silent quality failure.
- Hangul check avoids asserting on LLM-generated text content while still confirming the response is in Korean.

**Alternatives rejected**:
- Assert on specific LLM response text — unstable; violates D6.
- Only assert final response non-empty — would miss the geocoding-skip regression.

### D8: CI safety — inherit #291 skip logic

**Decision**: Do not modify `tests/conftest.py` root skip logic. Verify by running `uv run pytest` (no `-m live`) locally and confirming the new tests are collected but skipped.

**Rationale**:
- FR-007 and SC-005 forbid new CI cost. The root conftest from #291 already enforces `-m live` opt-in. Our new tests inherit this via their `@pytest.mark.live` decoration.
- Testing the skip behavior is part of acceptance (SC-005), not a plan decision.

---

## 2. Deferred Items Validation (Constitution Principle VI)

**Spec declaration**: "No items deferred — all requirements are addressed in this epic."

**Validation**:

| Check | Result |
|---|---|
| Deferred Items table present in spec? | Yes — Out of Scope (Permanent) + Deferred to Future Work (empty) |
| Any `NEEDS TRACKING` markers? | None |
| Unregistered `future epic` / `v2` / `later release` / `separate epic` prose? | None — verified by grep over `spec.md` |
| Sole `Phase 2` reference | Scope boundary (TUI layer does not exist in repo yet) — not a deferral |

**Status**: PASS. No additional tracking required.

---

## 3. Research Tasks (None remaining)

All `NEEDS CLARIFICATION` markers from `/speckit-specify` are resolved in the spec's Assumptions section. No open research tasks remain for Phase 1.

---

## 4. Open Questions (None)

No open questions. Plan may proceed to Phase 1 Design.
