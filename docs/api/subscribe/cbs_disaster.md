---
tool_id: mock_cbs_disaster_v1
primitive: subscribe
tier: mock
permission_tier: 1
---

# mock_cbs_disaster_v1

## Overview

Subscribes to Korean government Cell Broadcasting Service (CBS) disaster alert messages and streams `CbsBroadcastEvent` fixtures covering message IDs 4370–4385 (3GPP TS 23.041 range adopted by the Korean CBS profile).

| Field | Value |
|---|---|
| Classification | Mock · Permission tier 1 |
| Source | 행정안전부 재난문자방송 (CBS — Cell Broadcasting Service), SafeKorea (https://www.safekorea.go.kr/) |
| Primitive | `subscribe` |
| Module | `src/kosmos/tools/mock/cbs/disaster_feed.py` |

## Envelope

**Input model**: `SubscribeInput` (from `kosmos.primitives.subscribe`) with the following adapter-specific `params` keys.

| Field | Type | Required | Description |
|---|---|---|---|
| `tool_id` | `str` | yes | Must be `"mock_cbs_disaster_v1"` |
| `params.burst_count` | `int` | no | Total number of events to emit (default `3`) |
| `params.burst_delay_seconds` | `float` | no | Delay in seconds between events (default `0.1`); set to `0.0` to enable back-pressure stress mode |

**Output model**: `CbsBroadcastEvent` (from `kosmos.primitives.subscribe`) — one event per streamed item.

| Field | Type | Required | Description |
|---|---|---|---|
| `cbs_message_id` | `Literal[4370..4385]` | yes | CBS message ID per 3GPP TS 23.041; Korean CMAS categories |
| `received_at` | `datetime` (UTC) | yes | Wall-clock time when the broadcast was received |
| `payload_hash` | `str` | yes | SHA-256 of `body + received_at ISO string` for integrity verification |
| `language` | `Literal["ko", "en"]` | yes | Language of the alert body |
| `body` | `str` | yes | Alert text (Korean `[긴급재난문자]` or English `[EMERGENCY ALERT]`) |

## Search hints

- 한국어: `재난문자`, `긴급재난알림`, `CBS`, `지진`, `홍수`, `폭염`
- English: `disaster alert`, `CBS broadcast`, `emergency notification`, `cell broadcast`

## Endpoint

- **Mode**: Fixture-replay only
- **Public spec source**: 행정안전부 재난문자방송 공식 안내 및 SafeKorea 표준 (https://www.safekorea.go.kr/), 3GPP TS 23.041 "Technical realization of Cell Broadcast Service (CBS)" — Korean CBS message ID profile (IDs 4370–4385) aligned with ATIS-0700007 CMAS categories.
- **Fixture path**: `tests/fixtures/cbs/disaster_feed/` (6 static fixtures cycling through message IDs 4370–4375)

## Permission tier rationale

This adapter sits at permission tier 1 (green ⓵) because disaster alerts are public safety broadcasts that do not involve personal data and do not require citizen authentication. Spec 033 defines tier 1 for read-only, non-personal data streams. CBS messages are broadcast to all devices in a geographic cell without authentication; mirroring this in KOSMOS as a no-auth subscription is consistent with the real-world service model. The adapter uses `MODALITY_CBS` (3GPP byte-mirror modality) and is registered with `register_subscribe_adapter`, which applies no auth gate at tier 1.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "mock_cbs_disaster_v1",
  "params": {
    "burst_count": 2,
    "burst_delay_seconds": 0.1
  }
}
```

### Output envelope (success)

```json
{
  "events": [
    {
      "cbs_message_id": 4370,
      "received_at": "2026-04-26T08:00:00.123456+00:00",
      "payload_hash": "a3f2d1e9b84c7a560d3e12f89e4c2b17a0f5c6d8e1b293a4f7d68502e1c93b4",
      "language": "ko",
      "body": "[긴급재난문자] 지진 발생 경보: 규모 4.5, 경상북도 일대. 즉시 대피하십시오."
    },
    {
      "cbs_message_id": 4371,
      "received_at": "2026-04-26T08:00:00.234567+00:00",
      "payload_hash": "b4e3c2f0a95d8b671e4f23g90f5d3c28b1g6d7e9f2c304b5g8e79613f2d04c5",
      "language": "ko",
      "body": "[긴급재난문자] 호우 경보: 서울 전 지역. 강우량 80mm/h 이상 예상."
    }
  ]
}
```

### Conversation snippet

```text
Citizen: 지금 재난문자 알림을 받고 싶어요.
KOSMOS: 최근 재난문자 2건을 수신했습니다. 경상북도 일대에 규모 4.5 지진 경보가, 서울 전 지역에 시간당 80mm 이상의 호우 경보가 발령되었습니다.
```

## Constraints

- **Rate limit**: N/A (fixture mode, no upstream call). In live CBS integration the system operates at the cell-broadcast layer — there is no API rate limit, but fixture burst is bounded by `burst_count`.
- **Freshness window**: N/A — fixtures are static. Real CBS alerts are issued on-demand by 행정안전부; there is no polling interval.
- **Fixture coverage gaps**: Only 6 fixture bodies (IDs 4370–4375) are defined; IDs 4376–4385 (additional CMAS categories including AMBER alerts and national security) are not populated. Duplicate-ID de-duplication is not exercised by the default fixture set; set `burst_count` > 6 to cycle through IDs and trigger de-dup in downstream consumers.
- **Error envelope examples**:
  - Tier-1 fail (handle expired): subscription silently terminates when `handle.closes_at` is exceeded; no error event is emitted — the async generator returns cleanly.
  - Tier-2 / Tier-3 (auth) fail: N/A — CBS adapter is tier 1, no authentication required.
  - Network timeout: N/A in fixture mode. In a live CBS integration, a radio-layer dropout would manifest as a gap in the event stream, not an error envelope.
