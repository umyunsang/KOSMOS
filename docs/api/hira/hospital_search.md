---
tool_id: hira_hospital_search
primitive: lookup
tier: live
permission_tier: 1
---

# hira_hospital_search

## Overview

Searches HIRA's (건강보험심사평가원) hospital registry for medical facilities within a specified radius of a WGS84 coordinate, returning ranked results with name, address, phone number, and institution type.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | Health Insurance Review and Assessment Service (HIRA) / data.go.kr |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/hira/hospital_search.py` |

## Envelope

**Input model**: `HiraHospitalSearchInput` defined at `src/kosmos/tools/hira/hospital_search.py:39–87`.

| Field | Type | Required | Description |
|---|---|---|---|
| `xPos` | `float` (124.0–132.0) | yes | Longitude in WGS84 decimal degrees. Korean peninsula range: 124–132. Obtain from `resolve_location(want='coords')` — never guess. |
| `yPos` | `float` (33.0–39.0) | yes | Latitude in WGS84 decimal degrees. Korean peninsula range: 33–39. Obtain from `resolve_location(want='coords')` — never guess. |
| `radius` | `int` (1–10000, default 2000) | no | Search radius in meters. Maximum 10,000 m. Increase only if initial results are empty. |
| `pageNo` | `int` (≥1, default 1) | no | Page number for pagination (1-based). |
| `numOfRows` | `int` (1–100, default 20) | no | Number of rows per page. |

**Output model**: `LookupCollection` dict returned by `handle()` at `src/kosmos/tools/hira/hospital_search.py:94–212`.

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `str` ("collection") | yes | Envelope type discriminator. |
| `items` | `list[dict]` | yes | List of hospital records. Empty list when no results or `resultCode="03"`. |
| `total_count` | `int` | yes | Total matching records on the upstream (may exceed `numOfRows`). |

Each item in `items` carries:

| Field | Type | Required | Description |
|---|---|---|---|
| `ykiho` | `str` | yes | HIRA unique institution identifier for follow-up detail queries. |
| `yadmNm` | `str` | yes | Hospital/clinic name. |
| `addr` | `str` | yes | Street address. |
| `telno` | `str` | yes | Phone number. |
| `clCd` | `str` | yes | Institution type code. |
| `clCdNm` | `str` | yes | Institution type name (e.g., `의원`, `병원`, `종합병원`). |
| `xPos` | `float \| None` | no | Institution longitude. |
| `yPos` | `float \| None` | no | Institution latitude. |
| `distance` | `float \| None` | no | Distance from search origin in meters. |
| `sidoCdNm` | `str` | no | City/province name. |
| `sgguCdNm` | `str` | no | District name. |

## Search hints

- 한국어: `병원 검색`, `진료과목`, `의료기관 정보`, `근처 병원`, `내과`, `외과`, `소아과`, `치과`, `한의원`
- English: `hospital search`, `medical specialty`, `clinic nearby`, `healthcare provider`, `HIRA`, `Korea hospital`, `nearby medical facility`

## Endpoint

- **data.go.kr endpoint**: `B551182/hospInfoServicev2/getHospBasisList`
- **Source URL**: https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

## Permission tier rationale

This adapter is classified as Permission tier 1 because it returns publicly searchable institutional information about registered medical facilities (`pipa_class="non_personal"`, `is_personal_data=False`). The HIRA hospital registry is published for public benefit. The input contains only geographic coordinates and a radius — no citizen identity is transmitted. The coordinates themselves are lookup parameters, not citizen profile data. Spec 033 defines tier 1 as the baseline for read-only, non-personal government data.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "hira_hospital_search",
  "params": {
    "xPos": 126.9780,
    "yPos": 37.5665,
    "radius": 2000,
    "pageNo": 1,
    "numOfRows": 5
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "hira_hospital_search",
  "result": {
    "kind": "collection",
    "items": [
      {
        "ykiho": "JDQ4MDg=",
        "yadmNm": "서울중구내과의원",
        "addr": "서울특별시 중구 세종대로 110",
        "telno": "02-1234-5678",
        "clCd": "11",
        "clCdNm": "의원",
        "xPos": 126.9775,
        "yPos": 37.5668,
        "distance": 350.2,
        "sidoCdNm": "서울특별시",
        "sgguCdNm": "중구"
      }
    ],
    "total_count": 12
  }
}
```

### Conversation snippet

```text
Citizen: 지금 있는 곳 근처 2km 이내 병원을 알려주세요.
KOSMOS: 현재 위치(서울 중구) 반경 2km 이내 병원 12곳을 찾았습니다. 가장 가까운 곳은 '서울중구내과의원'으로 약 350m 거리에 있으며, 전화번호는 02-1234-5678입니다. 더 많은 목록이 필요하시면 말씀해 주세요.
```

## Constraints

- **Rate limit**: `rate_limit_per_minute=10`; data.go.kr daily quota applies per API key.
- **Freshness window**: `cache_ttl_seconds=0` — no client-side caching. HIRA registry updates occur at irregular intervals; always fetch fresh.
- **Fixture coverage gaps**: The wire response may return a single dict instead of a list when exactly one hospital is found — the adapter normalizes this. `xPos`/`yPos`/`distance` may be `None` for some facility records.
- **Error envelope examples**:
  - Tier-1 fail (no results): `resultCode="03"` → `{"kind": "collection", "items": [], "total_count": 0}`.
  - API error: `resultCode` other than `"00"` or `"03"` → `ToolExecutionError` with code and message.
  - XML response guard: If the upstream returns XML, a `ToolExecutionError` is raised advising to append `&type=json`.
  - Network timeout: `httpx.TimeoutException` propagates after 30 s.
