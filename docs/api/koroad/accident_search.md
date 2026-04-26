---
tool_id: koroad_accident_search
primitive: lookup
tier: live
permission_tier: 1
---

# koroad_accident_search

## Overview

Queries the authoritative KOROAD accident-prone hotspot dataset for a Korean municipality by province/city code, district code, and dataset year category, returning ranked hazard zones with coordinates and casualty statistics.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | KOROAD (도로교통공단) — B552061/frequentzoneLg |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/koroad/koroad_accident_search.py` |

## Envelope

**Input model**: `KoroadAccidentSearchInput` defined at `src/kosmos/tools/koroad/koroad_accident_search.py:96-154`.

| Field | Type | Required | Description |
|---|---|---|---|
| `search_year_cd` | `SearchYearCd` | yes | Dataset year/category code (`searchYearCd` wire parameter). Enum value maps to a specific annual release ID (e.g. `"2025119"` for 2024 general data). |
| `si_do` | `SidoCode` | yes | Province/city code (`siDo` wire parameter). Must be obtained from a prior `resolve_location` call — never filled from model memory. Valid values defined in `SidoCode` enum. |
| `gu_gun` | `GugunCode` | yes | District/county code (`guGun` wire parameter). Must be paired with the corresponding `si_do` value and obtained via `resolve_location`. |
| `num_of_rows` | `int` | no | Rows per page (1–100). Default `10`. |
| `page_no` | `int` | no | 1-indexed page number. Default `1`. |

**Output model**: `KoroadAccidentSearchOutput` defined at `src/kosmos/tools/koroad/koroad_accident_search.py:157-172`.

| Field | Type | Required | Description |
|---|---|---|---|
| `total_count` | `int` | yes | Total hotspot records matching the query. |
| `page_no` | `int` | yes | Current page number returned. |
| `num_of_rows` | `int` | yes | Rows per page as requested. |
| `hotspots` | `list[AccidentHotspot]` | yes | Ranked accident hotspot zones. Empty list when no records exist. Each element contains `spot_cd`, `spot_nm`, `sido_sgg_nm`, `bjd_cd`, `occrrnc_cnt`, `caslt_cnt`, `dth_dnv_cnt`, `se_dnv_cnt`, `sl_dnv_cnt`, `wnd_dnv_cnt`, `la_crd`, `lo_crd`, `geom_json` (nullable), `afos_id`, `afos_fid`. |

## Search hints

- 한국어: `교통사고 위험지역 조회`, `사고다발구역`, `지자체별 위험지점`, `도로 위험구역`
- English: `accident hotspot`, `dangerous zone`, `traffic safety municipality`, `road hazard zone`

## Endpoint

- **data.go.kr endpoint**: `B552061/frequentzoneLg/getRestFrequentzoneLg`
- **Source URL**: https://www.data.go.kr/data/15063424/openapi.do
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

## Permission tier rationale

This adapter is classified as Permission tier 1 (green) per Spec 033 (`specs/033-permission-v2-spectrum/spec.md`). The endpoint returns aggregated, non-personal public safety data — accident zone statistics by administrative boundary with no individual-level personal information. `pipa_class` is `non_personal` and `auth_level` is `AAL1`. Because the data is read-only (`is_irreversible=False`) and does not expose personal data, no citizen consent prompt is required; the system may execute automatically once the user has initiated a lookup session.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "koroad_accident_search",
  "params": {
    "search_year_cd": "2025119",
    "si_do": 11,
    "gu_gun": 680,
    "num_of_rows": 5,
    "page_no": 1
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "koroad_accident_search",
  "result": {
    "total_count": 12,
    "page_no": 1,
    "num_of_rows": 5,
    "hotspots": [
      {
        "spot_cd": "119001234",
        "spot_nm": "강남구 테헤란로 일원",
        "sido_sgg_nm": "서울특별시 강남구",
        "bjd_cd": "1168000000",
        "occrrnc_cnt": 14,
        "caslt_cnt": 17,
        "dth_dnv_cnt": 1,
        "se_dnv_cnt": 3,
        "sl_dnv_cnt": 9,
        "wnd_dnv_cnt": 4,
        "la_crd": 37.5035,
        "lo_crd": 127.0490,
        "geom_json": null,
        "afos_id": "2025119",
        "afos_fid": "7843"
      }
    ]
  }
}
```

### Conversation snippet

```text
Citizen: 강남구에서 교통사고가 자주 발생하는 위험한 곳이 어디인지 알려주세요.
KOSMOS: 강남구(서울특별시)의 2024년 교통사고 사고다발구역 조회 결과입니다. 총 12개 위험지점이 확인되었으며, 가장 사고 빈도가 높은 지점은 '강남구 테헤란로 일원'으로 2024년 한 해 14건의 사고가 발생해 17명의 사상자(사망 1명 포함)가 나왔습니다. 좌표는 위도 37.5035, 경도 127.0490입니다. 해당 구간 이동 시 각별한 주의가 필요합니다.
```

## Constraints

- **Rate limit**: data.go.kr daily quota: 1,000 requests per API key. In-adapter rate limit: 10 requests/minute (`rate_limit_per_minute=10`).
- **Freshness window**: Dataset is updated annually. The 2024 general dataset (`searchYearCd=2025119`) was published in 2025; new datasets typically release each spring. `cache_ttl_seconds=3600`.
- **Fixture coverage gaps**: Single-item response (exactly one hotspot) triggers a dict-not-list wire quirk normalized by `_normalize_items`. NODATA_ERROR (resultCode `"03"`) returns an empty `hotspots` list — no fixture covers the full range of `GugunCode` values.
- **Error envelope examples**:
  - Tier-1 fail: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "koroad_accident_search", "message": "KOROAD API returned error: code='99' msg='SERVICE_ERROR'"}}`
  - Tier-2 / Tier-3 (auth) fail: `{"error": {"code": "CONFIGURATION_ERROR", "message": "Missing required environment variable: KOSMOS_DATA_GO_KR_API_KEY"}}`
  - Network timeout: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "koroad_accident_search", "message": "Network error: timed out after 30s"}}`
