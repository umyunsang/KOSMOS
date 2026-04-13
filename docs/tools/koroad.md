# KOROAD Tool Adapter — `koroad_accident_search`

교통사고 위험지역 조회 (Traffic Accident Hotspot Search)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `koroad_accident_search` |
| Korean Name (`name_ko`) | 교통사고 위험지역 조회 |
| Provider | 도로교통공단 (KOROAD) |
| Endpoint | `https://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 3600 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns accident-prone zones (사고다발지역) by municipality and dataset year category.
Each result includes the location name, administrative codes, accident and casualty
counts, and decimal-degree coordinates. Results are paginated.

## Input Schema (`KoroadAccidentSearchInput`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `search_year_cd` | `SearchYearCd` | Yes | — | Dataset year/category code (see Code Tables) |
| `si_do` | `SidoCode` | Yes | — | Province/city code (see Code Tables) |
| `gu_gun` | `GugunCode` | Yes | — | District code. Required by the KOROAD wire API |
| `num_of_rows` | `int` (1–100) | No | 10 | Rows per page |
| `page_no` | `int` (≥1) | No | 1 | Page number, 1-indexed |

### Cross-validation rules

The model validator `_validate_legacy_sido` rejects legacy sido codes when paired
with 2023+ datasets. The year is extracted from the `SearchYearCd` enum name suffix
(e.g., `GENERAL_2024 → 2024`) — callers do not need to compute year boundaries manually.

- `si_do=42` (`GANGWON_LEGACY`, 강원도) is only valid for datasets with year < 2023.
  Use `si_do=51` (`GANGWON`, 강원특별자치도) for `SearchYearCd` values from 2023+.
- `si_do=45` (`JEONBUK_LEGACY`, 전라북도) is only valid for datasets with year < 2023.
  Use `si_do=52` (`JEONBUK`, 전북특별자치도) for `SearchYearCd` values from 2023+.

## Output Schema (`KoroadAccidentSearchOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `total_count` | `int` | Total matching hotspot records |
| `page_no` | `int` | Current page number |
| `num_of_rows` | `int` | Rows per page requested |
| `hotspots` | `list[AccidentHotspot]` | Accident hotspot zones (empty list when no results) |

### `AccidentHotspot` fields

| Field | Type | Description |
|-------|------|-------------|
| `spot_cd` | `str` | Unique spot code |
| `spot_nm` | `str` | Location name (Korean) |
| `sido_sgg_nm` | `str` | Province + district combined name (Korean) |
| `bjd_cd` | `str` | Administrative district (법정동) code |
| `occrrnc_cnt` | `int` | Accident occurrence count |
| `caslt_cnt` | `int` | Total casualty count |
| `dth_dnv_cnt` | `int` | Death count |
| `se_dnv_cnt` | `int` | Serious injury count |
| `sl_dnv_cnt` | `int` | Minor injury count |
| `wnd_dnv_cnt` | `int` | Injury count |
| `la_crd` | `float` | Latitude (decimal degrees) |
| `lo_crd` | `float` | Longitude (decimal degrees) |
| `geom_json` | `str \| None` | GeoJSON polygon string; absent in some wire responses |
| `afos_id` | `str` | Year-dataset identifier (e.g., `"2025119"` for GENERAL_2024) |
| `afos_fid` | `str` | Feature ID within the dataset |

## Code Tables

### `SidoCode` — province/city codes

| Code | Korean Name | Enum Constant | Notes |
|------|-------------|---------------|-------|
| 11 | 서울특별시 | `SEOUL` | |
| 26 | 부산광역시 | `BUSAN` | |
| 27 | 대구광역시 | `DAEGU` | |
| 28 | 인천광역시 | `INCHEON` | |
| 29 | 광주광역시 | `GWANGJU` | |
| 30 | 대전광역시 | `DAEJEON` | |
| 31 | 울산광역시 | `ULSAN` | |
| 36 | 세종특별자치시 | `SEJONG` | |
| 41 | 경기도 | `GYEONGGI` | |
| 42 | 강원도 | `GANGWON_LEGACY` | Pre-2023 datasets only |
| 43 | 충청북도 | `CHUNGBUK` | |
| 44 | 충청남도 | `CHUNGNAM` | |
| 45 | 전라북도 | `JEONBUK_LEGACY` | Pre-2023 datasets only |
| 46 | 전라남도 | `JEONNAM` | |
| 47 | 경상북도 | `GYEONGBUK` | |
| 48 | 경상남도 | `GYEONGNAM` | |
| 50 | 제주특별자치도 | `JEJU` | |
| 51 | 강원특별자치도 | `GANGWON` | 2023+ datasets |
| 52 | 전북특별자치도 | `JEONBUK` | 2023+ datasets |

### `SearchYearCd` — dataset year/category codes

The wire value is a numeric string (e.g., `"2025119"`). The `year` property extracts
the four-digit year from the enum name suffix (e.g., `GENERAL_2024.year == 2024`).

| Category | 2024 code | 2023 code |
|----------|-----------|-----------|
| 지자체별 General | `"2025119"` | `"2024056"` |
| 결빙 Ice | `"2025113"` | `"2024055"` |
| 어린이보호구역 Child zone | `"2025066"` | `"2024041"` |
| 보행어린이 Pedestrian child | `"2025108"` | `"2024042"` |
| 보행노인 Pedestrian elderly | `"2025076"` | `"2024044"` |
| 자전거 Bicycle | `"2025081"` | `"2024046"` |
| 신호위반 Signal violation | `"2025111"` | — |
| 중앙선침범 Centerline violation | `"2025110"` | — |
| 연휴기간별 Holiday | `"2025112"` | — |
| 이륜차 Motorcycle | `"2025091"` | — |
| 보행자 Pedestrian general | `"2025083"` | — |
| 음주운전 Drunk driving | `"2025085"` | — |
| 화물차 Freight | `"2025089"` | — |

### `GugunCode` — district codes

District code integers overlap across sido (multiple cities share code `110` for
their Jung-gu). Always pair `gu_gun` with the correct `si_do`.

For the complete 250+ entry list, see
[`src/kosmos/tools/koroad/code_tables.py`](../../src/kosmos/tools/koroad/code_tables.py).

#### Seoul (시도코드 11) — 25 districts

| Code | Korean Name | Enum Constant |
|------|-------------|---------------|
| 110 | 종로구 | `SEOUL_JONGNO` |
| 140 | 중구 | `SEOUL_JUNGGU` |
| 170 | 용산구 | `SEOUL_YONGSAN` |
| 200 | 성동구 | `SEOUL_SEONGDONG` |
| 215 | 광진구 | `SEOUL_GWANGJIN` |
| 230 | 동대문구 | `SEOUL_DONGDAEMUN` |
| 260 | 중랑구 | `SEOUL_JUNGRANG` |
| 290 | 성북구 | `SEOUL_SEONGBUK` |
| 305 | 강북구 | `SEOUL_GANGBUK` |
| 320 | 도봉구 | `SEOUL_DOBONG` |
| 350 | 노원구 | `SEOUL_NOWON` |
| 380 | 은평구 | `SEOUL_EUNPYEONG` |
| 410 | 서대문구 | `SEOUL_SEODAEMUN` |
| 440 | 마포구 | `SEOUL_MAPO` |
| 470 | 양천구 | `SEOUL_YANGCHEON` |
| 500 | 강서구 | `SEOUL_GANGSEO` |
| 530 | 구로구 | `SEOUL_GURO` |
| 545 | 금천구 | `SEOUL_GEUMCHEON` |
| 560 | 영등포구 | `SEOUL_YEONGDEUNGPO` |
| 590 | 동작구 | `SEOUL_DONGJAK` |
| 620 | 관악구 | `SEOUL_GWANAK` |
| 650 | 서초구 | `SEOUL_SEOCHO` |
| 680 | 강남구 | `SEOUL_GANGNAM` |
| 710 | 송파구 | `SEOUL_SONGPA` |
| 740 | 강동구 | `SEOUL_GANGDONG` |

#### Busan (시도코드 26) — 16 districts

| Code | Korean Name | Enum Constant |
|------|-------------|---------------|
| 110 | 중구 | `BUSAN_JUNGGU` |
| 140 | 서구 | `BUSAN_SEO` |
| 170 | 동구 | `BUSAN_DONG` |
| 200 | 영도구 | `BUSAN_YEONGDO` |
| 230 | 부산진구 | `BUSAN_BUSANJIN` |
| 260 | 동래구 | `BUSAN_DONGNAE` |
| 290 | 남구 | `BUSAN_NAM` |
| 320 | 북구 | `BUSAN_BUK` |
| **350** | **해운대구** | **`BUSAN_HAEUNDAE`** |
| 380 | 사하구 | `BUSAN_SAHA` |
| 410 | 금정구 | `BUSAN_GEUMJEONG` |
| 440 | 강서구 | `BUSAN_GANGSEO` |
| 470 | 연제구 | `BUSAN_YEONJE` |
| 500 | 수영구 | `BUSAN_SUYEONG` |
| 530 | 사상구 | `BUSAN_SASANG` |
| 710 | 기장군 | `BUSAN_GIJANG` |

#### Daejeon (시도코드 30) — 5 districts

| Code | Korean Name | Enum Constant |
|------|-------------|---------------|
| 110 | 동구 | `DAEJEON_DONG` |
| 140 | 중구 | `DAEJEON_JUNGGU` |
| 170 | 서구 | `DAEJEON_SEO` |
| 200 | 유성구 | `DAEJEON_YUSEONG` |
| 230 | 대덕구 | `DAEJEON_DAEDEOK` |

#### Other metropolitan cities — anchor entries

| Sido | Code | Enum Constant | Korean Name |
|------|------|---------------|-------------|
| Daegu (27) | 110 | `DAEGU_JUNGGU` | 중구 |
| Incheon (28) | 110 | `INCHEON_JUNGGU` | 중구 |
| Gwangju (29) | 110 | `GWANGJU_DONG` | 동구 |
| Ulsan (31) | 110 | `ULSAN_JUNGGU` | 중구 |
| Gyeonggi (41) | 111 | `GYEONGGI_SUWON_JANGAHN` | 수원시 장안구 |
| Chungbuk (43) | 110 | — | 청주시 상당구 |
| Chungnam (44) | 110 | — | 천안시 동남구 |
| Jeonnam (46) | 110 | — | 목포시 |
| Gyeongbuk (47) | 110 | — | 포항시 남구 |
| Gyeongnam (48) | 110 | — | 창원시 의창구 |
| Jeju (50) | 110 | — | 제주시 |
| Gangwon (51) | 110 | — | 춘천시 |
| Jeonbuk (52) | 110 | — | 전주시 완산구 |

## Usage Example

```python
import asyncio
from kosmos.tools.koroad.koroad_accident_search import _call, KoroadAccidentSearchInput
from kosmos.tools.koroad.code_tables import SidoCode, SearchYearCd, GugunCode

async def query_busan_haeundae_hotspots():
    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.BUSAN,
        gu_gun=GugunCode.BUSAN_HAEUNDAE,
        num_of_rows=10,
    )
    result = await _call(inp)
    print(f"Total hotspots: {result['total_count']}")
    for spot in result['hotspots']:
        print(f"  {spot['spot_nm']}: {spot['occrrnc_cnt']} accidents")

asyncio.run(query_busan_haeundae_hotspots())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

All `data.go.kr` adapters return HTTP 200 even for business-layer errors. The result
is signaled through `resultCode` in the JSON body.

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| `"01"` | Application error | Raise `ToolExecutionError` |
| `"02"` | DB error | Raise `ToolExecutionError` |
| `"03"` | No data (NODATA_ERROR) | Return `hotspots=[]` and `total_count=0` — **not** an error |
| `"04"` | HTTP error | Raise `ToolExecutionError` |
| `"10"` | Wrong parameter | Raise `ToolExecutionError` |
| `"20"` | Service error | Raise `ToolExecutionError` |
| `"21"` | Locked service | Raise `ToolExecutionError` |
| `"22"` | Limit exceeded | Raise `ToolExecutionError` |
| `"30"` | Unregistered key | Raise `ToolExecutionError` |
| `"31"` | Expired key | Raise `ToolExecutionError` |
| `"32"` | IP blocked | Raise `ToolExecutionError` |
| `"33"` | Unregistered domain | Raise `ToolExecutionError` |
| `"99"` | Unknown error | Raise `ToolExecutionError` |

> This is the canonical error code reference for all KOSMOS `data.go.kr` adapters.
> Other adapter docs link here for the full table.

## Wire Format Quirks

- **Single-item dict normalization**: When exactly one hotspot matches, `items.item`
  in the wire response is a plain dict, not a list. `_normalize_items()` detects this
  and wraps it in a list so `hotspots` is always a `list`.
- **JSON parameter name**: This endpoint uses `type=json` (not `_type=json` as KMA
  endpoints do). Both parameters are sent to maximize compatibility.
- **XML default**: The data.go.kr gateway serves XML by default. If the response
  `Content-Type` still contains `xml` without `json`, `ToolExecutionError` is raised
  immediately rather than silently parsing broken XML.
- **resultCode="03" is not an error**: This code means no matching hotspot records
  exist for the given query. The adapter returns an empty `hotspots` list with
  `total_count=0` instead of raising an exception. This is the normal response for
  districts with no accident hotspot designations.
- **Empty items normalization**: When `items` is an empty string `""`, `null`, or
  absent, the adapter normalizes all three cases to an empty list.
- **Legacy sido codes**: `si_do=42` (강원도, `GANGWON_LEGACY`) and `si_do=45`
  (전라북도, `JEONBUK_LEGACY`) are invalid for `search_year_cd` values from 2023 or
  later. The model validator raises `ValueError` before the HTTP call is made.
- **coerce_numbers_to_str**: `AccidentHotspot` uses `coerce_numbers_to_str=True` so
  numeric wire fields like `spotCd` are always coerced to `str` in the output model.

## Related Tools

- [`road_risk_score`](road-risk-score.md) — composite tool that calls this adapter
  internally as one of its three inner adapters
