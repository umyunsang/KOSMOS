# KMA Ultra-Short-Term Forecast — `kma_ultra_short_term_forecast`

초단기예보 조회 (Ultra-Short-Term Forecast)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `kma_ultra_short_term_forecast` |
| Korean Name (`name_ko`) | 초단기예보 조회 |
| Provider | 기상청 (KMA) |
| Endpoint | `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 600 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns forecast items covering the next 6 hours at a KMA 5 km grid point. Data is
published every hour at HH:30 KST. Each call returns approximately 60 rows (6 hours
× ~10 categories per grid point).

> **Note on URL**: This endpoint uses `http://` (not `https://`). Ensure outbound
> plain HTTP is allowed in your network policy.

## Input Schema (`KmaUltraShortTermForecastInput`)

| Field | Type | Required | Default | Constraint |
|-------|------|----------|---------|------------|
| `base_date` | `str` | Yes | — | `YYYYMMDD` format; 8-digit regex enforced |
| `base_time` | `str` | Yes | — | **Must end in `"30"` (HH30 format)** |
| `nx` | `int` | Yes | — | 1–149 (KMA grid X) |
| `ny` | `int` | Yes | — | 1–253 (KMA grid Y) |
| `num_of_rows` | `int` | No | 60 | 6 hours × ~10 categories |
| `page_no` | `int` | No | 1 | 1-based |
| `data_type` | `"JSON" \| "XML"` | No | `"JSON"` | XML is rejected |

> **`base_time` constraint**: The minutes part **must be `"30"`**. Valid examples:
> `"0030"`, `"0130"`, `"0630"`, `"1130"`, `"2330"`. Any value where MM ≠ 30 raises
> `pydantic.ValidationError` before the HTTP call.

## Output Schema

`KmaUltraShortTermForecastOutput` is a **type alias** for `KmaShortTermForecastOutput`.
The output schema is identical to the short-term forecast adapter.

See [kma-short-term-forecast.md § Output Schema](kma-short-term-forecast.md#output-schema-kmashortermforecastoutput) for the full field table.

## Grid Coordinates

This adapter uses the same `(nx, ny)` Lambert Conformal Conic grid as all other KMA
adapters. See [kma-observation.md § Grid Coordinates](kma-observation.md#grid-coordinates)
for the full lookup table.

**Inline examples:**

| Region | nx | ny |
|--------|----|----|
| 서울 / Seoul | 61 | 126 |
| 부산 / Busan | 98 | 76 |

## Usage Example

```python
import asyncio
from datetime import UTC, datetime
from kosmos.tools.kma.kma_ultra_short_term_forecast import (
    _call,
    KmaUltraShortTermForecastInput,
)
from kosmos.tools.kma.grid_coords import REGION_TO_GRID

async def get_seoul_ultra_short_forecast():
    now = datetime.now(UTC)
    nx, ny = REGION_TO_GRID["서울"]
    # base_time must end in "30" — use the most recent HH:30 publication
    base_time = now.strftime("%H") + "30"
    inp = KmaUltraShortTermForecastInput(
        base_date=now.strftime("%Y%m%d"),
        base_time=base_time,
        nx=nx,
        ny=ny,
    )
    result = await _call(inp)
    print(f"Forecast items: {result['total_count']}")
    for item in result['items'][:5]:
        print(f"  {item['fcst_date']} {item['fcst_time']} {item['category']}: {item['fcst_value']}")

asyncio.run(get_seoul_ultra_short_forecast())
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

- **`base_time` must end in `"30"` (HH30 format)**: This is the most common mistake
  when calling this adapter. The ultra-short-term forecast is published at every
  half-hour mark (HH:30 KST), not at the top of the hour.

  | Wrong | Correct | What happens |
  |-------|---------|--------------|
  | `"1400"` | `"1430"` | `pydantic.ValidationError`: "Ultra-short-term forecast base_time must end in '30' (e.g. 0630)" |
  | `"0900"` | `"0930"` | Same error |

  The validator message is: `"Ultra-short-term forecast base_time must end in '30' (e.g. 0630), got '1400'"`.

- **Published hourly at HH:30 KST**: Each publication covers the next 6 hours
  starting from `base_time`. After `HH:30` passes, the next publication is at
  `(HH+1):30`. If you call before the HH:30 publication, use `(HH-1):30`.

- **`http://` base URL**: Unlike KOROAD and KMA alert/observation adapters which use
  `https://`, this endpoint uses plain `http://`. Ensure outbound HTTP is permitted
  in your network policy.

- **`num_of_rows=60` default**: 6 hours × ~10 categories per grid point = ~60 rows.
  Increase this only if you need more than the default 6-hour window.

- **Type alias output**: `KmaUltraShortTermForecastOutput` is defined as
  `KmaUltraShortTermForecastOutput = KmaShortTermForecastOutput` — it is not a
  distinct model class. The field structure is identical.

- **XML rejection**: `data_type="XML"` raises `ToolExecutionError` before the HTTP
  call (not via content-type detection).

- **Single-item dict normalization**: When exactly one forecast row is returned,
  `items.item` is a plain dict. The adapter wraps it in a list.

## Related Tools

- [`kma-observation.md`](kma-observation.md) — current observations (same grid system)
- [`kma-short-term-forecast.md`](kma-short-term-forecast.md) — 3-day forecast
  (different `base_time` constraint, longer coverage window)
