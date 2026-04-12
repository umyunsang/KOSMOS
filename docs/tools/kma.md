# KMA Tool Adapters

기상청 (Korea Meteorological Administration) adapters for weather alerts and current observations.

---

## Tool 1: kma_weather_alert_status

기상특보 현황 조회 (Weather Alert Status)

### Overview

| Field         | Value                                                                               |
|---------------|-------------------------------------------------------------------------------------|
| Tool ID       | `kma_weather_alert_status`                                                          |
| Provider      | 기상청 (KMA)                                                                        |
| Endpoint      | `https://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList`                |
| Auth Type     | `api_key` — env var `KOSMOS_DATA_GO_KR_API_KEY`                                    |
| Rate limit    | 10 calls / minute (client-side)                                                     |
| Cache TTL     | 300 seconds                                                                         |
| Personal data | No                                                                                  |

Returns the current list of active weather warnings and watches (경보/주의보) for
all regions nationwide. Cancelled alerts (`cancel=1`) are automatically filtered out.

### Input Schema (`KmaWeatherAlertStatusInput`)

| Field         | Type                    | Required | Description                                    |
|---------------|-------------------------|----------|------------------------------------------------|
| `num_of_rows` | `int` (≥1)              | No       | Rows per page, default 2000 (returns all alerts) |
| `page_no`     | `int` (≥1)              | No       | Page number, 1-indexed, default 1              |
| `data_type`   | `"JSON" \| "XML"`       | No       | Response format, default `"JSON"`              |

### Output Schema (`KmaWeatherAlertStatusOutput`)

| Field         | Type                     | Description                                      |
|---------------|--------------------------|--------------------------------------------------|
| `total_count` | `int`                    | Count of active (non-cancelled) warnings         |
| `warnings`    | `list[WeatherWarning]`   | Active warnings only (cancel=0)                  |

### `WeatherWarning` fields

| Field          | Type  | Description                                                         |
|----------------|-------|---------------------------------------------------------------------|
| `stn_id`       | `str` | Station/region ID                                                   |
| `tm_fc`        | `str` | Announcement time in `YYYYMMDDHHMI` format                         |
| `tm_ef`        | `str` | Effective time in `YYYYMMDDHHMI` format                            |
| `tm_seq`       | `int` | Sequence number within the announcement                             |
| `area_code`    | `str` | Warning zone code (e.g., `"S1151300"`)                              |
| `area_name`    | `str` | Korean warning zone name (e.g., `"서울"`)                           |
| `warn_var`     | `int` | Warning type: 1=강풍, 2=호우, 3=한파, 4=건조, 5=해일, 6=태풍, 7=대설, 8=황사, 11=폭염 |
| `warn_stress`  | `int` | Severity: 0=주의보 (watch), 1=경보 (warning)                        |
| `cancel`       | `int` | Cancellation flag: 0=active, 1=cancelled (active only in output)    |
| `command`      | `int` | Command code from KMA                                               |
| `warn_fc`      | `int` | Warning forecast flag                                               |

### Usage Example

```python
from kosmos.tools.kma.kma_weather_alert_status import _call, KmaWeatherAlertStatusInput
import asyncio

async def check_alerts():
    inp = KmaWeatherAlertStatusInput()  # defaults fetch all active alerts
    result = await _call(inp)
    print(f"Active alerts: {result['total_count']}")
    for w in result['warnings']:
        stress = "경보" if w['warn_stress'] == 1 else "주의보"
        print(f"  {w['area_name']}: {stress} (type {w['warn_var']})")

asyncio.run(check_alerts())
```

### Wire Format Quirks

- **Single-item dict normalization**: When exactly one alert is active, the API
  returns `items.item` as a plain dict. The adapter wraps it in a list.
- **XML default**: Requests must include `_type=json` and `dataType=JSON`. If the
  response `Content-Type` contains `xml`, a `ToolExecutionError` is raised.
- **resultCode check**: The API always returns HTTP 200. `resultCode != "00"` is
  always an error.
- **Cancelled alerts**: Items with `cancel=1` are silently filtered out before the
  output is returned. `total_count` reflects only non-cancelled warnings.
- **Empty items**: An empty/missing `items` field yields `total_count=0` and an
  empty `warnings` list.
- **camelCase-to-snake_case mapping**: Wire fields use camelCase (`stnId`, `tmFc`,
  etc.); output model fields use snake_case (`stn_id`, `tm_fc`, etc.). The mapping
  is performed by `_FIELD_MAP` in the module.

---

## Tool 2: kma_current_observation

초단기실황 관측 조회 (Ultra-Short-Term Current Observation)

### Overview

| Field         | Value                                                                                     |
|---------------|-------------------------------------------------------------------------------------------|
| Tool ID       | `kma_current_observation`                                                                 |
| Provider      | 기상청 (KMA)                                                                              |
| Endpoint      | `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst`              |
| Auth Type     | `api_key` — env var `KOSMOS_DATA_GO_KR_API_KEY`                                          |
| Rate limit    | 10 calls / minute (client-side)                                                           |
| Cache TTL     | 600 seconds                                                                               |
| Personal data | No                                                                                        |

Returns current weather observations (temperature, precipitation, humidity, wind) at
a KMA 5 km grid point. The API uses a pivot row format: each field is a separate row
with `{category, obsrValue}` rather than a flat response object.

### Input Schema (`KmaCurrentObservationInput`)

| Field         | Type                 | Required | Description                                            |
|---------------|----------------------|----------|--------------------------------------------------------|
| `base_date`   | `str`                | Yes      | Observation date in `YYYYMMDD` format                  |
| `base_time`   | `str`                | Yes      | Observation time in `HHMM` format (rounded to hour)    |
| `nx`          | `int` (1–149)        | Yes      | KMA grid X coordinate                                  |
| `ny`          | `int` (1–253)        | Yes      | KMA grid Y coordinate                                  |
| `num_of_rows` | `int` (≥1)           | No       | Rows per page, default 10                              |
| `page_no`     | `int` (≥1)           | No       | Page number, 1-indexed, default 1                      |
| `data_type`   | `"JSON" \| "XML"`    | No       | Response format, default `"JSON"` (XML is rejected)    |

The `base_time` field validator automatically rounds the minutes down to `"HH00"`.
For example, `"1430"` is stored as `"1400"`.

### Output Schema (`KmaCurrentObservationOutput`)

The API's pivot rows are flattened into a single output object:

| Field       | Type            | Description                                               |
|-------------|-----------------|-----------------------------------------------------------|
| `base_date` | `str`           | Observation date `YYYYMMDD`                               |
| `base_time` | `str`           | Observation time `HHMM`                                   |
| `nx`        | `int`           | Grid X coordinate                                         |
| `ny`        | `int`           | Grid Y coordinate                                         |
| `t1h`       | `float \| None` | Temperature in degrees Celsius                            |
| `rn1`       | `float`         | 1-hour accumulated precipitation in mm (0.0 when absent)  |
| `uuu`       | `float \| None` | East-west wind component in m/s (positive = eastward)     |
| `vvv`       | `float \| None` | North-south wind component in m/s (positive = northward)  |
| `wsd`       | `float \| None` | Wind speed in m/s                                         |
| `reh`       | `float \| None` | Relative humidity in percent                              |
| `pty`       | `int`           | Precipitation type (see table below)                      |
| `vec`       | `float \| None` | Wind direction in degrees (0–360, meteorological)         |

#### Precipitation type codes (`pty`)

| Code | Meaning          |
|------|------------------|
| 0    | None             |
| 1    | Rain             |
| 2    | Rain + Snow      |
| 3    | Snow             |
| 5    | Drizzle          |
| 6    | Drizzle + Snow   |
| 7    | Snow Flurry      |

### Grid Coordinate Lookup

KMA uses a Lambert Conformal Conic projection grid with 5 km resolution. Grid
coordinates `(nx, ny)` are region-specific and do not correspond to latitude/longitude.

The `kosmos.tools.kma.grid_coords.REGION_TO_GRID` dict maps Korean and Romanized
region names to `(nx, ny)` tuples. Selected examples:

| Region        | nx  | ny  |
|---------------|-----|-----|
| 서울 / Seoul  | 61  | 126 |
| 부산 / Busan  | 98  | 76  |
| 대구 / Daegu  | 89  | 90  |
| 인천 / Incheon| 55  | 124 |
| 광주 / Gwangju| 58  | 74  |
| 대전 / Daejeon| 67  | 100 |
| 제주 / Jeju   | 52  | 38  |

### Usage Example

```python
from datetime import UTC, datetime
from kosmos.tools.kma.kma_current_observation import _call, KmaCurrentObservationInput
from kosmos.tools.kma.grid_coords import REGION_TO_GRID
import asyncio

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

### Wire Format Quirks

- **RN1 sentinel value**: The KMA API reports no-precipitation as the string `"-"`
  rather than `0` or `null`. The `rn1` field validator normalises `"-"`, `None`,
  and `""` to `0.0` so all consumers always receive a numeric value.
- **base_time retry logic**: Data for the current hour may not be available
  immediately after the hour boundary. If you receive a `ToolExecutionError` with
  an empty items list, retry with `base_time` set to the previous hour (`HH-100`).
- **Pivot row format**: Each observation category (T1H, RN1, WSD, etc.) is a
  separate row in `items.item`. The adapter's `_pivot_rows_to_output()` function
  flattens these into a single `KmaCurrentObservationOutput`.
- **XML rejection**: Unlike other adapters that log a warning on XML responses,
  this adapter raises `ToolExecutionError` immediately if `data_type="XML"` is
  requested, since XML parsing is not implemented.
- **Empty items error**: Unlike the alert status adapter which returns an empty
  list, the observation adapter raises `ToolExecutionError` when `items` is empty,
  because an empty observation means the data is not ready yet.
