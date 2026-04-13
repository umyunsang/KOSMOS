# KMA Short-Term Forecast — `kma_short_term_forecast`

단기예보 조회 (Short-Term Forecast)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `kma_short_term_forecast` |
| Korean Name (`name_ko`) | 단기예보 조회 |
| Provider | 기상청 (KMA) |
| Endpoint | `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 1800 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns forecast items covering approximately 3 days ahead at a KMA 5 km grid point.
Data is published 8 times per day at `0200`, `0500`, `0800`, `1100`, `1400`, `1700`,
`2000`, and `2300` KST. Each publication produces roughly 290 rows per grid point.

> **Note on URL**: This endpoint uses `http://` (not `https://`). Ensure outbound
> plain HTTP is allowed in your network policy.

## Input Schema (`KmaShortTermForecastInput`)

| Field | Type | Required | Default | Constraint |
|-------|------|----------|---------|------------|
| `base_date` | `str` | Yes | — | `YYYYMMDD` format; 8-digit regex enforced |
| `base_time` | `str` | Yes | — | Must be one of `0200/0500/0800/1100/1400/1700/2000/2300` |
| `nx` | `int` | Yes | — | 1–149 (KMA grid X) |
| `ny` | `int` | Yes | — | 1–253 (KMA grid Y) |
| `num_of_rows` | `int` | No | 290 | Full dataset per grid point is ~290 rows |
| `page_no` | `int` | No | 1 | 1-based |
| `data_type` | `"JSON" \| "XML"` | No | `"JSON"` | XML is rejected |

**`base_time` validation**: Any value outside the 8 valid times raises
`pydantic.ValidationError` before the HTTP call. Valid values: `0200`, `0500`, `0800`,
`1100`, `1400`, `1700`, `2000`, `2300`.

## Output Schema (`KmaShortTermForecastOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `total_count` | `int` | Total number of forecast items available for this query |
| `items` | `list[ForecastItem]` | Forecast items for the requested page |

### `ForecastItem` fields

| Field | Type | Description |
|-------|------|-------------|
| `base_date` | `str` | Base date of the forecast publication (`YYYYMMDD`) |
| `base_time` | `str` | Base time of the forecast publication (`HHMM`) |
| `fcst_date` | `str` | Forecast target date (`YYYYMMDD`) |
| `fcst_time` | `str` | Forecast target time (`HHMM`) |
| `nx` | `int` | Grid X coordinate |
| `ny` | `int` | Grid Y coordinate |
| `category` | `str` | Forecast category code (see table below) |
| `fcst_value` | `str` | Forecast value as a string (numeric or range string like `"30.0~50.0mm"`) |

### Category codes

| Category | Unit | Description |
|----------|------|-------------|
| `TMP` | °C | Temperature |
| `SKY` | code | Sky condition: 1=맑음(Clear), 3=구름많음(Mostly cloudy), 4=흐림(Cloudy) |
| `PTY` | code | Precipitation type: 0=없음, 1=비, 2=비/눈, 3=눈, 4=소나기 |
| `POP` | % | Precipitation probability |
| `REH` | % | Relative humidity |
| `WSD` | m/s | Wind speed |
| `UUU` | m/s | East-west wind component |
| `VVV` | m/s | North-south wind component |
| `VEC` | degrees | Wind direction (0–360) |
| `WAV` | m | Wave height |
| `PCP` | mm | Precipitation amount (may be a range string, e.g., `"30.0~50.0mm"`) |
| `SNO` | cm | Snowfall amount (may be a range string) |
| `TMN` | °C | Minimum temperature for the day |
| `TMX` | °C | Maximum temperature for the day |

## Grid Coordinates

This adapter uses the same `(nx, ny)` Lambert Conformal Conic grid as all KMA adapters.
See [kma-observation.md § Grid Coordinates](kma-observation.md#grid-coordinates) for
the full lookup table.

**Inline examples** (required for common use cases):

| Region | nx | ny |
|--------|----|----|
| 서울 / Seoul | 61 | 126 |
| **대전 / Daejeon** | **67** | **100** |
| 부산 / Busan | 98 | 76 |
| 인천 / Incheon | 55 | 124 |

## Usage Example

```python
import asyncio
from kosmos.tools.kma.kma_short_term_forecast import _call, KmaShortTermForecastInput
from kosmos.tools.kma.grid_coords import REGION_TO_GRID

async def get_daejeon_forecast():
    nx, ny = REGION_TO_GRID["대전"]  # nx=67, ny=100
    inp = KmaShortTermForecastInput(
        base_date="20260414",
        base_time="0800",
        nx=nx,
        ny=ny,
    )
    result = await _call(inp)
    print(f"Total forecast items: {result['total_count']}")
    # Find temperature forecasts
    for item in result['items']:
        if item['category'] == 'TMP':
            print(f"  {item['fcst_date']} {item['fcst_time']}: {item['fcst_value']}°C")

asyncio.run(get_daejeon_forecast())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| Other | Error | Raise `ToolExecutionError` |

See [`koroad.md § Error Codes`](koroad.md#error-codes) for the full shared error code
table.

## Wire Format Quirks

- **`http://` base URL**: This endpoint uses plain `http://`, not `https://`. This
  is a characteristic of the KMA forecast service URLs. Ensure outbound HTTP is
  permitted in your network policy.
- **`base_time` validation**: Any value not in `{0200, 0500, 0800, 1100, 1400, 1700,
  2000, 2300}` raises `pydantic.ValidationError` before the HTTP call is made.
- **"Data not ready" window**: The API publishes data approximately 10 minutes after
  each `base_time`. Early calls (within the first 10 minutes after a `base_time`)
  typically receive `resultCode="10"` (wrong parameter). To recover, retry with the
  previous `base_time` (e.g., if `1400` fails, retry with `1100`).
- **PCP/SNO range strings**: Precipitation and snowfall values may be range strings
  like `"30.0~50.0mm"` or `"5.0cm 이상"` instead of a plain number. These are stored
  as-is in `fcst_value` and are not parsed to a numeric type.
- **`num_of_rows=290` default**: A full 3-day forecast at one grid point is
  approximately 290 rows (8 publications/day × ~3 days × ~12 categories). Increase
  this if your query needs more than the default page.
- **Single-item dict normalization**: When exactly one forecast row is returned,
  `items.item` is a plain dict. The adapter wraps it in a list.
- **XML rejection**: `data_type="XML"` raises `ToolExecutionError` before the HTTP
  call.
- **camelCase-to-snake_case**: Wire fields use camelCase (`baseDate`, `fcstDate`,
  `fcstValue`, etc.); output model fields use snake_case (`base_date`, `fcst_date`,
  `fcst_value`, etc.).

## Related Tools

- [`kma-ultra-short-term-forecast.md`](kma-ultra-short-term-forecast.md) — 6-hour
  forecast with a different `base_time` constraint (HH30 format)
- [`kma-observation.md`](kma-observation.md) — current observations using the same
  grid system
