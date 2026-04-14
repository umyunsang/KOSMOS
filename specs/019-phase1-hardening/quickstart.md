# Quickstart — Phase 1 Hardening Live Validation

**Feature**: 019-phase1-hardening
**Audience**: KOSMOS maintainer validating Phase 1 release-readiness locally.

## Prerequisites

- `uv` installed and synced (`uv sync`).
- Environment variables set: `KOSMOS_FRIENDLI_API_KEY`, `KOSMOS_DATA_GO_KR_API_KEY`, `KOSMOS_KAKAO_REST_API_KEY`, `KOSMOS_KMA_API_KEY` (never commit `.env`).
- FriendliAI account on Tier 1 (100 RPM / 100 TPM). No higher tier required.
- No CI involvement — the live suite runs locally only.

## Mocked-suite sanity check (no live quota consumed)

```bash
uv run pytest tests/llm/ tests/tools/ tests/context/ -v
```

Expected: 100% green (SC-005). No assertion rewrites beyond the new default-parameter payload expectations.

## Live validation suite

```bash
uv run pytest -m live -v
```

Expected outcome:
- 30 passed / 0 xfailed / 0 failed (SC-001).
- Zero test failures attributable to HTTP 429 (SC-003).
- `test_live_scenario1_from_natural_address` passes with the first `koroad_accident_search` tool invocation carrying Seoul / Gangnam administrative codes (SC-002).
- `test_live_e2e_multi_turn_context` wall-clock ≤ the pre-change baseline (which included the 60s blind cooldown) (SC-004).

## How to inspect a live run for the "강남역" assertion

```bash
uv run pytest -m live -v -k test_live_scenario1_from_natural_address
```

Check the captured tool-use events: the first `koroad_accident_search` invocation must carry `si_do` and `gu_gun` matching Seoul / Gangnam per the project's enumerated codes. The final Korean-language answer must reference Gangnam (강남), not any other district.

## How to observe retry behavior

Retry activity is logged via stdlib `logging` at `INFO` level in `src/kosmos/llm/client.py`. Grep for the categorized rate-limit log line during a live run to see:

- Whether `Retry-After` was present and honored, or the fallback backoff was used.
- How many attempts elapsed before success.
- Whether the failure was pre-stream or mid-stream.

## Definition of done for Phase 1 release

1. Mocked suite green.
2. Live suite 30/30 across three consecutive runs (SC-002 stability clause).
3. Public discussion thread carries the retraction comment (SC-006).
4. Epic #404 PR merged with `Closes #404` and CI green.

When all four hold, the maintainer can declare Phase 1 release-ready (SC-007) and proceed to Phase 2.
