---
tool_id: koroad_accident_hazard_search
primitive: lookup
tier: live
permission_tier: 1
---

# koroad_accident_hazard_search

## Overview

Queries the KOROAD accident hazard spot dataset for a Korean municipality by 10-digit administrative code (`adm_cd`) and calendar year, returning a ranked collection of hazard locations with occurrence counts, casualty counts, and GeoJSON geometry.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | KOROAD (도로교통공단) — B552061/frequentzoneLg |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/koroad/accident_hazard_search.py` |

## Envelope

**Input model**: `AccidentHazardSearchInput` defined at `src/kosmos/tools/koroad/accident_hazard_search.py:40-65`.

| Field | Type | Required | Description |
|---|---|---|---|
| `adm_cd` | `str` | yes | 10-digit 행정동 administrative code. Must match pattern `^[0-9]{10}$`. Obtain via `resolve_location(want='adm_cd')`. Example: `'1111000000'` for 서울특별시 종로구. |
| `year` | `int` | yes | Calendar year for the accident dataset (2019–2100). The adapter maps the year to the correct KOROAD `searchYearCd` internally, including 2023+ code changes for 강원/전북. Example: `2024`. |

**Output model**: LookupCollection-shaped dict returned by `handle()` at `src/kosmos/tools/koroad/accident_hazard_search.py:731-846`.

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `str` | yes | Always `"collection"`. |
| `items` | `list[dict]` | yes | Ranked hazard spots. Each item contains `spot_nm`, `tot_dth_cnt`, `geom_json`, `spot_cd`, `sido_sgg_nm`, `occrrnc_cnt`, `caslt_cnt`, `la_crd`, `lo_crd`. |
| `total_count` | `int` | yes | Total matching hazard records from the upstream API. |

## Search hints

- 한국어: `교통사고 위험지점`, `사고다발구역`, `행정동코드`, `연도별 위험지역`, `도로 위험구역 조회`
- English: `accident hazard spot`, `dangerous zone`, `adm_cd year`, `traffic safety Korea`, `road hazard by administrative code`

## Endpoint

- **data.go.kr endpoint**: `B552061/frequentzoneLg/getRestFrequentzoneLg`
- **Source URL**: https://www.data.go.kr/data/15063424/openapi.do
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

## Permission tier rationale

This adapter is classified as Permission tier 1 (green) per Spec 033 (`specs/033-permission-v2-spectrum/spec.md`). The underlying endpoint is identical to `koroad_accident_search` — aggregated public road safety statistics with no individual personal data. `pipa_class` is `non_personal`, `auth_level` is `AAL1`, and `is_irreversible=False`. The distinguishing characteristic of this adapter is its simplified input interface (10-digit `adm_cd` + integer `year`), which makes it easier to call directly after a `resolve_location` step. No consent prompt is required; the adapter may execute automatically within a citizen lookup session.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "koroad_accident_hazard_search",
  "params": {
    "adm_cd": "1168000000",
    "year": 2024
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "koroad_accident_hazard_search",
  "result": {
    "kind": "collection",
    "total_count": 8,
    "items": [
      {
        "spot_nm": "강남구 테헤란로 사거리 일원",
        "tot_dth_cnt": 1,
        "geom_json": null,
        "spot_cd": "119001234",
        "sido_sgg_nm": "서울특별시 강남구",
        "occrrnc_cnt": 14,
        "caslt_cnt": 17,
        "la_crd": 37.5035,
        "lo_crd": 127.0490
      }
    ]
  }
}
```

### Conversation snippet

```text
Citizen: 강남구에서 작년에 교통사고가 많이 난 위험한 곳을 알려주세요.
KOSMOS: 2024년 강남구(행정동 코드 1168000000) 교통사고 위험지점 조회 결과, 총 8개 지점이 확인되었습니다. 가장 사고가 잦은 곳은 '강남구 테헤란로 사거리 일원'으로 연간 14건의 사고(사망 1명, 총 17명 사상)가 발생했습니다. 위치는 위도 37.5035, 경도 127.0490 근방입니다.
```

## Constraints

- **Rate limit**: data.go.kr daily quota: 1,000 requests per API key. In-adapter rate limit: 10 requests/minute (`rate_limit_per_minute=10`).
- **Freshness window**: Annual dataset; 2024 data uses `searchYearCd=2025119`. New datasets publish each spring. `cache_ttl_seconds=3600`.
- **Fixture coverage gaps**: The internal `_PREFIX5_TO_SIDO` / `_PREFIX5_TO_GUGUN` codebook covers all 17 metropolitan/provincial units but does not include every sub-district code exhaustively — unknown prefixes fall back to a two-digit sido heuristic. Year codes before 2019 are not supported; years after 2024 map to the latest available dataset. 부천시 split (pre/post-2023 `41191`/`41192`/`41193`/`41195`) is handled but not covered by recorded fixtures.
- **Error envelope examples**:
  - Tier-1 fail: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "koroad_accident_hazard_search", "message": "KOROAD API error: code='99' msg='SERVICE_ERROR'"}}`
  - Tier-2 / Tier-3 (auth) fail: `{"error": {"code": "CONFIGURATION_ERROR", "message": "Missing required environment variable: KOSMOS_DATA_GO_KR_API_KEY"}}`
  - Network timeout: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "koroad_accident_hazard_search", "message": "Network error reaching KOROAD API: timed out after 30s"}}`
