# KOROAD Tool Adapter — koroad_accident_search

교통사고 위험지역 조회 (Traffic Accident Hotspot Search)

## Overview

| Field         | Value                                                                                          |
|---------------|-----------------------------------------------------------------------------------------------|
| Tool ID       | `koroad_accident_search`                                                                       |
| Provider      | 도로교통공단 (KOROAD)                                                                          |
| Endpoint      | `https://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg`                        |
| Auth Type     | `api_key` — env var `KOSMOS_KOROAD_API_KEY`                                                   |
| Rate limit    | 10 calls / minute (client-side)                                                                |
| Cache TTL     | 3600 seconds                                                                                   |
| Personal data | No                                                                                             |

Returns accident-prone zones (사고다발지역) by municipality and dataset year category,
including location coordinates and casualty statistics.

## Input Schema (`KoroadAccidentSearchInput`)

| Field           | Type                  | Required | Description                                      |
|-----------------|-----------------------|----------|--------------------------------------------------|
| `search_year_cd`| `SearchYearCd`        | Yes      | Dataset year/category code (see Code Tables)     |
| `si_do`         | `SidoCode`            | Yes      | Province/city code (see Code Tables)             |
| `gu_gun`        | `GugunCode \| None`   | No       | District code; omit to query entire province     |
| `num_of_rows`   | `int` (1–100)         | No       | Rows per page, default 10                        |
| `page_no`       | `int` (≥1)            | No       | Page number, 1-indexed, default 1                |

### Cross-validation rules

- `si_do=42` (GANGWON_LEGACY) is only valid for datasets with year < 2023.
  Use `si_do=51` (GANGWON) for 2023+ datasets.
- `si_do=45` (JEONBUK_LEGACY) is only valid for datasets with year < 2023.
  Use `si_do=52` (JEONBUK) for 2023+ datasets.

## Output Schema (`KoroadAccidentSearchOutput`)

| Field         | Type                    | Description                                  |
|---------------|-------------------------|----------------------------------------------|
| `total_count` | `int`                   | Total matching hotspot records               |
| `page_no`     | `int`                   | Current page number                          |
| `num_of_rows` | `int`                   | Rows per page requested                      |
| `hotspots`    | `list[AccidentHotspot]` | Accident hotspot zones (empty if no results) |

### `AccidentHotspot` fields

| Field         | Type          | Description                                            |
|---------------|---------------|--------------------------------------------------------|
| `spot_cd`     | `str`         | Unique spot code                                       |
| `spot_nm`     | `str`         | Location name (Korean)                                 |
| `sido_sgg_nm` | `str`         | Province + district combined name (Korean)             |
| `bjd_cd`      | `str`         | Administrative district (법정동) code                  |
| `occrrnc_cnt` | `int`         | Accident occurrence count                              |
| `caslt_cnt`   | `int`         | Total casualty count                                   |
| `dth_dnv_cnt` | `int`         | Death count                                            |
| `se_dnv_cnt`  | `int`         | Serious injury count                                   |
| `sl_dnv_cnt`  | `int`         | Minor injury count                                     |
| `wnd_dnv_cnt` | `int`         | Injury count                                           |
| `la_crd`      | `float`       | Latitude (decimal degrees)                             |
| `lo_crd`      | `float`       | Longitude (decimal degrees)                            |
| `geom_json`   | `str \| None` | GeoJSON polygon string; absent in some wire responses  |
| `afos_id`     | `str`         | Year-dataset identifier (e.g. `"2025119"` for GENERAL_2024) |
| `afos_fid`    | `str`         | Feature ID within the dataset                          |

## Code Table References

### `SidoCode` (province/city codes)

| Code | Name                   | Notes                            |
|------|------------------------|----------------------------------|
| 11   | 서울특별시              | SEOUL                            |
| 26   | 부산광역시              | BUSAN                            |
| 27   | 대구광역시              | DAEGU                            |
| 28   | 인천광역시              | INCHEON                          |
| 29   | 광주광역시              | GWANGJU                          |
| 30   | 대전광역시              | DAEJEON                          |
| 31   | 울산광역시              | ULSAN                            |
| 36   | 세종특별자치시          | SEJONG                           |
| 41   | 경기도                  | GYEONGGI                         |
| 42   | 강원도                  | GANGWON_LEGACY — pre-2023 only   |
| 43   | 충청북도                | CHUNGBUK                         |
| 44   | 충청남도                | CHUNGNAM                         |
| 45   | 전라북도                | JEONBUK_LEGACY — pre-2023 only   |
| 46   | 전라남도                | JEONNAM                          |
| 47   | 경상북도                | GYEONGBUK                        |
| 48   | 경상남도                | GYEONGNAM                        |
| 50   | 제주특별자치도          | JEJU                             |
| 51   | 강원특별자치도          | GANGWON — 2023+                  |
| 52   | 전북특별자치도          | JEONBUK — 2023+                  |

### `SearchYearCd` (dataset year/category codes)

The wire value is a numeric string (e.g., `"2025119"`). Categories include:

| Category           | 2024 code   | 2023 code   |
|--------------------|-------------|-------------|
| 지자체별 (General) | `"2025119"` | `"2024056"` |
| 결빙 (Ice)         | `"2025113"` | `"2024055"` |
| 어린이보호구역     | `"2025066"` | `"2024041"` |
| 보행어린이         | `"2025108"` | `"2024042"` |
| 보행노인           | `"2025076"` | `"2024044"` |
| 자전거             | `"2025081"` | `"2024046"` |
| 신호위반           | `"2025111"` | —           |
| 중앙선침범         | `"2025110"` | —           |
| 연휴기간별         | `"2025112"` | —           |
| 이륜차             | `"2025091"` | —           |
| 보행자             | `"2025083"` | —           |
| 음주운전           | `"2025085"` | —           |
| 화물차             | `"2025089"` | —           |

### `GugunCode` (district codes, selected Seoul examples)

| Code | Name               | Sido |
|------|--------------------|------|
| 110  | 서울 종로구        | 11   |
| 140  | 서울 중구          | 11   |
| 680  | 서울 강남구        | 11   |
| 710  | 서울 송파구        | 11   |

Note: district codes overlap across sido (e.g., code 110 is Jung-gu in multiple cities).
Always pair `gu_gun` with the correct `si_do`.

### `HazardType`

Convenience enum mapping hazard categories to their default `SearchYearCd`.
Values: `general`, `ice`, `pedestrian_child`, `child_zone`, `pedestrian_elderly`,
`bicycle`, `law_violation`, `holiday`, `motorcycle`, `pedestrian`, `drunk_driving`, `freight`.

## Usage Example

```python
from kosmos.tools.koroad.koroad_accident_search import _call, KoroadAccidentSearchInput
from kosmos.tools.koroad.code_tables import SidoCode, SearchYearCd, GugunCode
import asyncio

async def query_seoul_gangnam_hotspots():
    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.SEOUL,
        gu_gun=GugunCode.SEOUL_GANGNAM,
        num_of_rows=10,
    )
    result = await _call(inp)
    print(f"Total hotspots: {result['total_count']}")
    for spot in result['hotspots']:
        print(f"  {spot['spot_nm']}: {spot['occrrnc_cnt']} accidents")

asyncio.run(query_seoul_gangnam_hotspots())
```

## Wire Format Quirks

### Single-item dict normalization

When exactly one hotspot matches, the KOROAD API returns `items.item` as a plain
dict instead of a list of dicts. The adapter's `_normalize_items()` detects this and
wraps it in a list, so `hotspots` is always a `list`.

### XML default

The data.go.kr gateway serves XML by default. The adapter appends `_type=json` to
all requests. If the response `Content-Type` still contains `xml` without `json`, a
`ToolExecutionError` is raised immediately (rather than silently parsing broken XML).

### resultCode check

The KOROAD API always returns HTTP 200, even for business-layer errors. The adapter
checks `response.header.resultCode`; any value other than `"00"` raises a
`ToolExecutionError` with the original error message.

### Empty results

When no hotspots match the query, `items` in the wire response may be an empty
string `""`, `null`, or a missing key. All three cases are normalized to an empty
`hotspots` list with `total_count=0`.
