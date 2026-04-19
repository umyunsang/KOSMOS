# Mock: data_go_kr

**Mirror axis**: byte
**Source reference**: https://openapi.data.go.kr (공공데이터포털 OpenAPI 게이트웨이)
**License**: Public Domain (공공누리 제1유형, Korean Open Government License Type 1)
**Scope**: Reproduces the HTTP request/response wire format of the data.go.kr REST gateway, including authentication headers, error envelope shape, and pagination fields — limited to the subset of endpoints exercised by KOSMOS adapters.

## What this mock reproduces

- `serviceKey` query-parameter authentication pattern used across all data.go.kr APIs
- Response envelope: `{ response: { header: { resultCode, resultMsg }, body: { items, numOfRows, pageNo, totalCount } } }`
- HTTP 200 with `resultCode != "00"` for application-level errors (e.g., `"03"` = no data, `"10"` = invalid key)
- HTTP 4xx/5xx for transport-level failures
- Rate-limit behaviour: `resultCode = "22"` (service request limit exceeded) with no `Retry-After` header (data.go.kr does not emit one)
- Pagination parameters: `numOfRows`, `pageNo` in both request and response

## What this mock deliberately does NOT reproduce

- Live API key validation (the mock accepts any non-empty `serviceKey`)
- Real geographic or statistical data content — fixtures use synthetic seed values
- HTTPS certificate chain verification (mock runs over plain HTTP on localhost)
- Per-endpoint schema divergences not yet exercised by KOSMOS (e.g., RTMS real-estate API shape)

## Fixture recording approach

Fixtures are recorded from live data.go.kr endpoints using the `tests/fixtures/record_*.py` scripts with a valid `KOSMOS_DATA_GO_KR_API_KEY` set in the environment. Each recorded response is stored as a JSON file under `tests/fixtures/data_go_kr/<endpoint_slug>/`. The mock server replays these files byte-for-byte, including original `Content-Type: application/json; charset=UTF-8` headers.

Steps to re-record:
1. Set `KOSMOS_DATA_GO_KR_API_KEY` in your shell.
2. Run `uv run python tests/fixtures/record_data_go_kr.py --endpoint <slug>`.
3. Commit the updated fixture file. Do not commit the API key.

## Upstream divergence policy

When the upstream response envelope changes (e.g., data.go.kr adds a new top-level field), update the fixture by re-recording and open a PR with label `mock-drift`. The mock must never silently diverge: `tests/test_mock_scenario_split.py` enforces fixture freshness by checking a `recorded_at` timestamp field injected at record time. If `recorded_at` is older than 90 days, the test emits a warning (not a failure) and sets exit code 0 to avoid blocking CI on stale-but-valid fixtures.
