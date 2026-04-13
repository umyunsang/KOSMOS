# Road Risk Score — `road_risk_score`

도로 위험도 종합 평가 (Composite Road Risk Assessment)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `road_risk_score` |
| Korean Name (`name_ko`) | 도로 위험도 종합 평가 |
| Provider | KOSMOS (composite) |
| Endpoint | (none — composite, no direct upstream endpoint) |
| Auth Type | `api_key` — delegates to `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 300 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Computes a normalized road risk score (0.0–1.0) by fanning out to three inner adapters
in parallel, then combining their results into a single score and citizen-facing summary.

## Architecture

This adapter has no direct upstream endpoint. It orchestrates three inner adapters:

```
road_risk_score
├── koroad_accident_search   (accident hotspots)
├── kma_weather_alert_status (active weather warnings)
└── kma_current_observation  (current precipitation + temperature)
```

The three inner calls run in parallel via
`asyncio.gather(return_exceptions=True)`. The date and time for the KMA observation
are derived internally from `datetime.now(UTC)` — **callers cannot specify them**.
This is intentional: the composite tool is designed for real-time risk assessment.

For endpoint URLs, rate limits, and quota details of each inner adapter, see:
- [koroad.md](koroad.md) — KOROAD accident hotspot search
- [kma-alert.md](kma-alert.md) — KMA weather alert status
- [kma-observation.md](kma-observation.md) — KMA current observation

## Input Schema (`RoadRiskScoreInput`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `si_do` | `SidoCode` | Yes | — | Province/city code for the KOROAD query |
| `gu_gun` | `GugunCode` | Yes | — | District code for the KOROAD query |
| `search_year_cd` | `SearchYearCd \| None` | No | `GENERAL_2024` | Dataset year code; set to `GENERAL_2024` by model validator when `None` |
| `nx` | `int` (1–149) | Yes | — | KMA grid X coordinate for the observation |
| `ny` | `int` (1–253) | Yes | — | KMA grid Y coordinate for the observation |

See [koroad.md § Code Tables](koroad.md#code-tables) for `SidoCode`, `SearchYearCd`,
and `GugunCode` values. See [kma-observation.md § Grid Coordinates](kma-observation.md#grid-coordinates)
for `(nx, ny)` values.

## Output Schema (`RoadRiskScoreOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `risk_score` | `float` (0.0–1.0) | Normalized composite risk score |
| `risk_level` | `"low" \| "moderate" \| "high" \| "severe"` | Human-readable risk tier |
| `hotspot_count` | `int` | Accident hotspot count from KOROAD |
| `active_warnings` | `int` | Active weather warning count from KMA |
| `precipitation_mm` | `float` | 1-hour precipitation in mm from KMA observation |
| `temperature_c` | `float \| None` | Current temperature in °C; `None` when the observation adapter failed |
| `data_gaps` | `list[str]` | Names of inner adapters that failed and used fallback values |
| `summary` | `str` | Korean-language prose for citizen display (do not parse programmatically) |

**`summary` format**: The summary is generated as citizen-facing Korean-language prose:
```
위험도 {level_ko}: 사고다발지역 {hotspot_count}건, 기상특보 {active_warnings}건, 강수량 {precipitation_mm}mm
```
Use the typed fields (`risk_score`, `risk_level`, `hotspot_count`, etc.) for
programmatic consumption. Do not parse the `summary` string.

## Scoring Formula

The risk score is computed in two steps:

```python
hotspot_score  = min(1.0, hotspot_count / 10.0)
weather_score  = min(1.0, active_warnings * 0.3 + precipitation_mm / 50.0)
risk_score     = hotspot_score * 0.5 + weather_score * 0.5   # clamped to [0.0, 1.0]
```

**Weight interpretation**:
- `hotspot_score`: normalizes accident hotspot count against a ceiling of 10. A
  district with 10+ hotspots scores 1.0 on this dimension.
- `weather_score`: combines active warning count (each warning adds 0.3) and
  precipitation rate (50 mm/h = 1.0). Both factors are clamped before summation.

### Risk level thresholds

| Range | Level | Korean |
|-------|-------|--------|
| [0.0, 0.3) | `"low"` | 낮음 |
| [0.3, 0.6) | `"moderate"` | 보통 |
| [0.6, 0.8) | `"high"` | 높음 |
| [0.8, 1.0] | `"severe"` | 매우 높음 |

## Partial Failure Semantics

The composite adapter tolerates partial failures. When one or two inner adapters fail,
fallback values are used and the failed adapter names are listed in `data_gaps`.

| Failed adapter | Fallback value(s) | Listed in `data_gaps` |
|---|---|---|
| `koroad_accident_search` | `hotspot_count = 0` | Yes |
| `kma_weather_alert_status` | `active_warnings = 0` | Yes |
| `kma_current_observation` | `precipitation_mm = 0.0`, `temperature_c = None` | Yes |

**Total failure**: If all three inner adapters fail, `ToolExecutionError` is raised
with a message including the repr of all three exceptions. There is no partial output
in this case.

**Example**: If `data_gaps: ["kma_current_observation"]` appears in the output, the
`precipitation_mm` field holds `0.0` (fallback) and `temperature_c` is `None`. The
risk score was computed using `precipitation_mm=0.0`, which may under-estimate weather
risk. Check `data_gaps` before acting on the score in reliability-sensitive contexts.

## Usage Example

```python
import asyncio
from kosmos.tools.composite.road_risk_score import _call, RoadRiskScoreInput
from kosmos.tools.koroad.code_tables import SidoCode, GugunCode
from kosmos.tools.kma.grid_coords import REGION_TO_GRID

async def assess_busan_haeundae_risk():
    nx, ny = REGION_TO_GRID["부산"]  # nx=98, ny=76
    inp = RoadRiskScoreInput(
        si_do=SidoCode.BUSAN,
        gu_gun=GugunCode.BUSAN_HAEUNDAE,
        nx=nx,
        ny=ny,
    )
    result = await _call(inp)
    print(f"Risk score: {result['risk_score']:.3f} ({result['risk_level']})")
    print(f"Hotspots: {result['hotspot_count']}")
    print(f"Active warnings: {result['active_warnings']}")
    print(f"Precipitation: {result['precipitation_mm']} mm")
    if result['data_gaps']:
        print(f"Warning: data gaps from {result['data_gaps']}")
    print(result['summary'])

asyncio.run(assess_busan_haeundae_risk())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

This adapter delegates HTTP calls to its three inner adapters. Error codes from those
adapters apply individually. See:

- [`koroad.md § Error Codes`](koroad.md#error-codes) — full shared error code table
- [`kma-alert.md § Error Codes`](kma-alert.md#error-codes)
- [`kma-observation.md § Error Codes`](kma-observation.md#error-codes)

Inner adapter errors are caught and handled as partial failures (see above). The
composite only raises `ToolExecutionError` when all three inner adapters fail.

## Wire Format Quirks

- **No direct endpoint**: This is a composite adapter with no upstream HTTP call of
  its own. Rate limiting and error handling apply to each inner adapter independently.
- **Internally derived date/time**: The KMA observation call uses `datetime.now(UTC)`
  to derive `base_date` and `base_time`. The `base_time` is set to `HH:00` (top of
  current hour). Callers cannot override this.
- **Parallel fan-out**: `asyncio.gather(return_exceptions=True)` means all three inner
  calls start concurrently. If one call takes longer (e.g., KOROAD is slow), the other
  two can complete while it is still pending. The total latency is bounded by the
  slowest inner adapter.
- **`search_year_cd` default**: The model validator sets `search_year_cd` to
  `SearchYearCd.GENERAL_2024` when `None` is passed. The default cannot be changed
  without explicitly passing a `SearchYearCd` value.

## Related Tools

- [`koroad.md`](koroad.md) — inner adapter: accident hotspot search
- [`kma-alert.md`](kma-alert.md) — inner adapter: weather alert status
- [`kma-observation.md`](kma-observation.md) — inner adapter: current observation
