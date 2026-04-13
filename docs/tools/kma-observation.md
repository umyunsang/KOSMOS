# KMA Current Observation — `kma_current_observation`

초단기실황 관측 조회 (Ultra-Short-Term Current Observation)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `kma_current_observation` |
| Korean Name (`name_ko`) | 초단기실황 관측 조회 |
| Provider | 기상청 (KMA) |
| Endpoint | `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 600 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns current weather observations (temperature, precipitation, humidity, wind) at a
KMA 5 km grid point. The upstream API uses a **pivot row** format: each observation
category is a separate `{category, obsrValue}` row rather than a flat response object.
The adapter flattens these rows into a single `KmaCurrentObservationOutput` model.

## Input Schema (`KmaCurrentObservationInput`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `base_date` | `str` | Yes | — | Observation date in `YYYYMMDD` format |
| `base_time` | `str` | Yes | — | Observation time in `HHMM` format; **rounded down to `HH00`** |
| `nx` | `int` (1–149) | Yes | — | KMA grid X coordinate |
| `ny` | `int` (1–253) | Yes | — | KMA grid Y coordinate |
| `num_of_rows` | `int` (≥1) | No | 10 | Rows per page |
| `page_no` | `int` (≥1) | No | 1 | Page number, 1-indexed |
| `data_type` | `"JSON" \| "XML"` | No | `"JSON"` | Response format; **XML is rejected** before the HTTP call |

**`base_time` rounding**: The field validator normalizes any `HHMM` value to `HH00`.
For example, `"1430"` becomes `"1400"` and `"0915"` becomes `"0900"`. This prevents
"data not ready" errors caused by calling for a time that has not yet been published.

## Output Schema (`KmaCurrentObservationOutput`)

The pivot rows are flattened into a single output object:

| Field | Type | Description |
|-------|------|-------------|
| `base_date` | `str` | Observation date `YYYYMMDD` |
| `base_time` | `str` | Observation time `HHMM` (after rounding) |
| `nx` | `int` | Grid X coordinate |
| `ny` | `int` | Grid Y coordinate |
| `t1h` | `float \| None` | Temperature in degrees Celsius |
| `rn1` | `float` | 1-hour accumulated precipitation in mm (0.0 when absent or sentinel `"-"`) |
| `uuu` | `float \| None` | East-west wind component in m/s (positive = eastward) |
| `vvv` | `float \| None` | North-south wind component in m/s (positive = northward) |
| `wsd` | `float \| None` | Wind speed in m/s |
| `reh` | `float \| None` | Relative humidity in percent |
| `pty` | `int` | Precipitation type code (see table below) |
| `vec` | `float \| None` | Wind direction in degrees (0–360, meteorological convention) |

#### Precipitation type codes (`pty`)

| Code | Meaning |
|------|---------|
| 0 | None |
| 1 | Rain |
| 2 | Rain + Snow |
| 3 | Snow |
| 5 | Drizzle |
| 6 | Drizzle + Snow |
| 7 | Snow Flurry |

### Category-to-field pivot mapping

The wire response contains rows with `category` and `obsrValue` keys. The adapter
maps them as follows:

| Wire `category` | Output field | Notes |
|-----------------|-------------|-------|
| `T1H` | `t1h` | Temperature °C |
| `RN1` | `rn1` | Precipitation mm; `"-"` normalized to `0.0` |
| `UUU` | `uuu` | East-west wind m/s |
| `VVV` | `vvv` | North-south wind m/s |
| `WSD` | `wsd` | Wind speed m/s |
| `REH` | `reh` | Relative humidity % |
| `PTY` | `pty` | Precipitation type code |
| `VEC` | `vec` | Wind direction degrees |

Unknown categories are silently ignored.

## Grid Coordinates

KMA uses a Lambert Conformal Conic projection grid with 5 km resolution. Grid
coordinates `(nx, ny)` are region-specific and do not correspond to
latitude/longitude.

The `kosmos.tools.kma.grid_coords.REGION_TO_GRID` dict maps Korean and Romanized
region names to `(nx, ny)` tuples. Use `lookup_grid("서울")` or `lookup_grid("Busan")`
for a direct lookup. Raises `ValueError` if the region is not found.

<details>
<summary>Full grid coordinate table (click to expand)</summary>

| Region (Korean) | Region (English) | nx | ny |
|-----------------|-----------------|-----|-----|
| 서울특별시 | Seoul | 61 | 126 |
| 부산광역시 | Busan | 98 | 76 |
| 대구광역시 | Daegu | 89 | 90 |
| 인천광역시 | Incheon | 55 | 124 |
| 광주광역시 | Gwangju | 58 | 74 |
| 대전광역시 | **Daejeon** | **67** | **100** |
| 울산광역시 | Ulsan | 102 | 84 |
| 세종특별자치시 | Sejong | 66 | 103 |
| 경기도 | Gyeonggi | 60 | 120 |
| 강원특별자치도 | Gangwon | 73 | 134 |
| 충청북도 | Chungbuk | 69 | 107 |
| 충청남도 | Chungnam | 68 | 100 |
| 전라북도 / 전북특별자치도 | Jeonbuk | 63 | 89 |
| 전라남도 | Jeonnam | 51 | 67 |
| 경상북도 | Gyeongbuk | 89 | 106 |
| 경상남도 | Gyeongnam | 91 | 77 |
| 제주특별자치도 | Jeju | 52 | 38 |
| 강남구 | Gangnam | 61 | 125 |
| 서초구 | Seocho | 61 | 124 |
| 송파구 | Songpa | 62 | 124 |
| 마포구 | Mapo | 59 | 127 |
| 종로구 | Jongno | 60 | 127 |
| 용산구 | Yongsan | 60 | 126 |
| 노원구 | Nowon | 61 | 130 |
| 수원 | Suwon | 60 | 121 |
| 성남 | Seongnam | 63 | 124 |
| 고양 | Goyang | 57 | 128 |
| 용인 | Yongin | 64 | 119 |
| 창원 | Changwon | 90 | 77 |
| 전주 | Jeonju | 63 | 89 |
| 청주 | Cheongju | 69 | 106 |
| 춘천 | Chuncheon | 73 | 134 |
| 포항 | Pohang | 102 | 94 |
| 천안 | Cheonan | 63 | 110 |

</details>

**Frequently used coordinates:**

| Region | nx | ny |
|--------|----|----|
| 서울 / Seoul | 61 | 126 |
| 부산 / Busan | 98 | 76 |
| 대전 / Daejeon | 67 | 100 |
| 인천 / Incheon | 55 | 124 |
| 제주 / Jeju | 52 | 38 |

## Usage Example

```python
import asyncio
from datetime import UTC, datetime
from kosmos.tools.kma.kma_current_observation import _call, KmaCurrentObservationInput
from kosmos.tools.kma.grid_coords import REGION_TO_GRID

async def get_seoul_weather():
    now = datetime.now(UTC)
    nx, ny = REGION_TO_GRID["서울"]
    inp = KmaCurrentObservationInput(
        base_date=now.strftime("%Y%m%d"),
        base_time=now.strftime("%H") + "00",
        nx=nx,
        ny=ny,
    )
    result = await _call(inp)
    print(f"Temperature: {result['t1h']}°C")
    print(f"Precipitation (1h): {result['rn1']} mm")
    print(f"Humidity: {result['reh']}%")
    print(f"Wind speed: {result['wsd']} m/s")

asyncio.run(get_seoul_weather())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| Other | Error | Raise `ToolExecutionError` |

> **Note**: Unlike the alert adapter, `resultCode="03"` does NOT apply here — the
> observation endpoint raises `ToolExecutionError` when items are empty (data not
> ready yet), not an empty result.

See [`koroad.md § Error Codes`](koroad.md#error-codes) for the full shared error code
table.

## Wire Format Quirks

- **XML rejection**: If `data_type="XML"` is requested, `ToolExecutionError` is raised
  *before* the HTTP call (at the adapter level, not via a response content-type check).
  XML parsing is not implemented for this adapter.
- **RN1 sentinel value**: The KMA API reports no-precipitation as the string `"-"`
  instead of `0` or `null`. The `rn1` field validator normalizes `"-"`, `None`, and
  `""` to `0.0` so all consumers always receive a numeric value.
- **base_time rounding**: Any `HHMM` value is rounded down to `HH00` by the input
  model validator before the API call is made. This is intentional — it prevents
  "data not ready" errors from passing a time that falls within the current hour but
  before the data has been published.
- **Empty items = ToolExecutionError**: Unlike the alert status adapter which returns
  an empty list for no results, this adapter raises `ToolExecutionError` when the
  items list is empty. An empty observation means data for that hour has not been
  published yet. To recover, retry with `base_time` set to the previous hour.
- **Pivot row format**: Each observation category (T1H, RN1, WSD, etc.) is a separate
  row in `items.item`. `_pivot_rows_to_output()` flattens these into a single
  `KmaCurrentObservationOutput`.
- **Single-item dict normalization**: When only one category row is present, `items.item`
  is a plain dict. `_normalize_items()` wraps it in a list.

## Related Tools

- [`kma-short-term-forecast.md`](kma-short-term-forecast.md) — 3-day forecast using
  the same `(nx, ny)` grid system; references this page for grid coordinates
- [`kma-ultra-short-term-forecast.md`](kma-ultra-short-term-forecast.md) — 6-hour
  forecast; references this page for grid coordinates
- [`road_risk_score`](road-risk-score.md) — composite tool that calls this adapter
  internally
