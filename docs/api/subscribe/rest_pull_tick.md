---
tool_id: mock_rest_pull_tick_v1
primitive: subscribe
tier: mock
permission_tier: 1
---

# mock_rest_pull_tick_v1

## Overview

Subscribes to a REST-pull tick feed that polls a data.go.kr-style REST endpoint on a configurable interval and streams `RestPullTickEvent` objects carrying the raw response payload and its SHA-256 hash.

| Field | Value |
|---|---|
| Classification | Mock · Permission tier 1 |
| Source | Any data.go.kr REST endpoint with documented polling cadence; adapter conforms to RFC 7231 HTTP semantics (https://datatracker.ietf.org/doc/html/rfc7231) |
| Primitive | `subscribe` |
| Module | `src/kosmos/tools/mock/data_go_kr/rest_pull_tick.py` |

## Envelope

**Input model**: `SubscribeInput` (from `kosmos.primitives.subscribe`) with the following adapter-specific `params` keys.

| Field | Type | Required | Description |
|---|---|---|---|
| `tool_id` | `str` | yes | Must be `"mock_rest_pull_tick_v1"` |
| `params.polling_interval_seconds` | `float` | no | Requested polling interval; harness enforces a minimum of 10s (default `30.0`) |
| `params.tick_count` | `int` | no | Total number of ticks to emit (default `1`) |
| `params.tick_delay_seconds` | `float` | no | Override of the actual sleep duration between ticks in tests; also clamped to >= 10s |

**Output model**: `RestPullTickEvent` (from `kosmos.primitives.subscribe`) — one event per polling tick.

| Field | Type | Required | Description |
|---|---|---|---|
| `tool_id` | `str` | yes | Echo of the subscription `tool_id` |
| `tick_at` | `datetime` (UTC) | yes | Wall-clock time when the tick was generated |
| `response_hash` | `str` | yes | SHA-256 of the JSON-serialized response payload (sort_keys, utf-8) |
| `payload` | `dict[str, object]` | yes | Raw upstream REST response (mock: static data.go.kr-format envelope with `resultCode`, `resultMsg`, and `items`) |

## Search hints

- 한국어: `REST폴링`, `주기적조회`, `공공데이터갱신`, `데이터갱신알림`
- English: `REST poll`, `polling subscription`, `periodic fetch`, `data refresh tick`

## Endpoint

- **Mode**: Fixture-replay only
- **Public spec source**: RFC 7231 "Hypertext Transfer Protocol (HTTP/1.1): Semantics and Content" (https://datatracker.ietf.org/doc/html/rfc7231) defines the HTTP GET semantics this adapter mirrors. Upstream data.go.kr endpoints follow the standard `resultCode` / `resultMsg` / `body.items` envelope documented in the 공공데이터포털 OpenAPI 가이드 (https://www.data.go.kr/ugs/selectPublicDataUseGuide.do). The adapter fires against any data.go.kr REST endpoint with documented polling cadence; the mock payload reproduces the MOLIT 공고 endpoint shape.
- **Fixture path**: `tests/fixtures/data_go_kr/rest_pull_tick/` (single static payload with `resultCode: "00"`)

## Permission tier rationale

This adapter sits at permission tier 1 (green ⓵) because it polls public data.go.kr REST endpoints that return non-personal, open government data without authentication. Spec 033 defines tier 1 for read-only, non-personal data streams. The adapter does not carry citizen identity, does not write any state, and does not invoke any PII-bearing endpoint; it models the general-purpose polling subscription surface. The harness enforces a 10-second minimum polling interval (`_MIN_POLLING_INTERVAL_SECONDS`) to prevent abusive upstream request rates regardless of what the caller declares.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "mock_rest_pull_tick_v1",
  "params": {
    "polling_interval_seconds": 30,
    "tick_count": 1
  }
}
```

### Output envelope (success)

```json
{
  "events": [
    {
      "tool_id": "mock_rest_pull_tick_v1",
      "tick_at": "2026-04-26T08:30:00.000000+00:00",
      "response_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "payload": {
        "response": {
          "header": {
            "resultCode": "00",
            "resultMsg": "NORMAL_SERVICE"
          },
          "body": {
            "items": {
              "item": [
                {
                  "noticeNo": "20260419-001",
                  "title": "2026년도 국토교통부 공고 제001호",
                  "pubDate": "2026-04-19T09:00:00+09:00",
                  "category": "국토교통"
                }
              ]
            },
            "numOfRows": 1,
            "pageNo": 1,
            "totalCount": 1
          }
        }
      }
    }
  ]
}
```

### Conversation snippet

```text
Citizen: 국토교통부 공고가 새로 올라오면 알려줘.
KOSMOS: 국토교통부 공고를 30초 간격으로 확인하겠습니다. 새 공고 "2026년도 국토교통부 공고 제001호"가 2026-04-19에 등록되었습니다.
```

## Constraints

- **Rate limit**: N/A in fixture mode. In live mode: data.go.kr free-tier service keys allow approximately 1,000 calls/day per key (~12s minimum between calls). The harness enforces a 10s polling floor (`_MIN_POLLING_INTERVAL_SECONDS`); the adapter default of 30s provides comfortable headroom.
- **Freshness window**: N/A for fixture. In live mode, upstream data.go.kr endpoints vary; MOLIT公고 is typically refreshed daily. Check the specific endpoint's `returnReasonCode` and `totalCount` fields to detect stale results.
- **Fixture coverage gaps**: Only `resultCode: "00"` (success) is represented. Error codes `03` (no data), `10` (wrong key), `12` (traffic exceeded), and `20` (service error) are not in fixtures. Multiple ticks produce identical payloads (same static fixture) — downstream consumers should compare `response_hash` across ticks to detect genuine updates in live mode.
- **Error envelope examples**:
  - Tier-1 fail (handle expired): the generator returns cleanly when `handle.closes_at` is exceeded.
  - Tier-2 / Tier-3 (auth) fail: N/A — REST-pull tick adapter is tier 1, no authentication required.
  - Network timeout: N/A in fixture mode. In live mode: `{"kind": "error", "reason": "upstream_unavailable", "message": "data.go.kr REST endpoint did not respond within 10s"}` — the harness surfaces this as a missed tick; the subscription continues on the next polling interval.
