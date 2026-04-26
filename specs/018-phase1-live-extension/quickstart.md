# Quickstart: Phase 1 Live Validation Extension

**Audience**: KOSMOS maintainer about to merge changes touching geocoding, observability, tool executor, or LLM client.

## Prerequisites

1. Kakao Developers app with the **Local API** activated. Console path: `앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON`. Platform registration is **not** required for server-side REST calls.
2. `data.go.kr` API key with KOROAD Accident Search service activated.
3. FriendliAI Serverless token with access to the EXAONE endpoint.

## Environment Setup

Add the Kakao key to your local `.env` (gitignored):

```bash
# .env (LOCAL ONLY)
KOSMOS_KAKAO_API_KEY=<your Kakao REST API key>
KOSMOS_DATA_GO_KR_API_KEY=<your data.go.kr key>
KOSMOS_FRIENDLI_TOKEN=<your FriendliAI token>
```

Load into your shell before running tests:

```bash
set -a && source .env && set +a
```

## Running the Extended Live Suite

### All new live coverage (geocoding + observability + E2E)

```bash
uv run pytest -m live -v \
  tests/live/test_live_geocoding.py \
  tests/live/test_live_observability.py \
  tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address
```

### Story-by-story

**Story 1 — Geocoding (seven tests)**

```bash
uv run pytest -m live -v tests/live/test_live_geocoding.py
```

**Story 2 — Observability (four tests)**

```bash
uv run pytest -m live -v tests/live/test_live_observability.py
```

**Story 3 — Natural-address E2E**

```bash
uv run pytest -m live -v \
  tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address
```

### Full Phase 1 live suite (this epic + #291)

```bash
uv run pytest -m live -v
```

## Verifying the Hard-Fail Contract (SC-004)

Intentionally unset the Kakao key and run the geocoding suite — it must hard-fail, not skip:

```bash
unset KOSMOS_KAKAO_API_KEY
uv run pytest -m live -v tests/live/test_live_geocoding.py 2>&1 | \
  grep "set KOSMOS_KAKAO_API_KEY to run live geocoding tests"
```

Expect: the exact string is printed in the failure output. If the suite reports `SKIPPED` or `XFAIL`, FR-011 is violated.

## Verifying CI Safety (SC-005)

Without the `-m live` flag, the new tests must be collected but skipped:

```bash
uv run pytest -v --collect-only | grep -E "(test_live_geocoding|test_live_observability|test_live_scenario1_from_natural_address)"
uv run pytest tests/live/ -v  # should report all live tests as SKIPPED
```

## Rate-Limit Envelope (SC-006)

Under the 200 ms `kakao_rate_limit_delay` default, one full run of `test_live_geocoding.py` issues roughly 10–15 Kakao calls. Kakao's free-tier 100k/day quota absorbs **thousands** of iterative runs without breach.

KOROAD calls in the observability suite are governed by the existing `_live_rate_limit_pause` 10 s autouse delay — a single full run uses ≤2 KOROAD calls.

## Expected Duration

| Suite | Approx. wall clock |
|---|---|
| `test_live_geocoding.py` (7 tests) | ~30 s (incl. 10 s post-test cooldown × 7) |
| `test_live_observability.py` (4 tests) | ~50 s |
| `test_live_scenario1_from_natural_address` (1 test) | ~15–30 s |
| **Total new coverage** | **~2 min** |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pytest.fail: set KOSMOS_KAKAO_API_KEY ...` | env var unset | `source .env && set +a` |
| `403 Forbidden` from Kakao | Local API not activated on the Kakao app | Console → 제품 설정 → 카카오맵 → 상태 ON |
| `429 Too Many Requests` from Kakao | Rate-limit fixture bypassed or quota exhausted | Verify `kakao_rate_limit_delay` is invoked between calls; check daily quota |
| `test_live_address_to_region_unmapped_region` raises instead of returning | Adapter regression — no longer fail-closed | Investigate `address_to_region.py` unmapped branch |
| Observability counter delta == 0 | Collector wiring broken — executor no longer calls collector | Investigate tool executor observability injection |
