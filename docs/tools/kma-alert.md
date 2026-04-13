# KMA Weather Alert Status — `kma_weather_alert_status`

기상특보 현황 조회 (Weather Alert Status)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `kma_weather_alert_status` |
| Korean Name (`name_ko`) | 기상특보 현황 조회 |
| Provider | 기상청 (KMA) |
| Endpoint | `https://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 300 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns the current list of active weather warnings (경보) and watches (주의보) for
all regions nationwide. Cancelled alerts (`cancel=1`) are automatically filtered out
of the response before the output is returned.

## Input Schema (`KmaWeatherAlertStatusInput`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `num_of_rows` | `int` (≥1) | No | 2000 | Rows per page. Default 2000 returns all alerts in one page |
| `page_no` | `int` (≥1) | No | 1 | Page number, 1-indexed |
| `data_type` | `"JSON" \| "XML"` | No | `"JSON"` | Response format |

## Output Schema (`KmaWeatherAlertStatusOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `total_count` | `int` | Count of active (non-cancelled) warnings |
| `warnings` | `list[WeatherWarning]` | Active warnings only (`cancel=0`) |

### `WeatherWarning` fields

| Field | Type | Description |
|-------|------|-------------|
| `stn_id` | `str` | Station/region ID |
| `tm_fc` | `str` | Announcement time in `YYYYMMDDHHMI` format |
| `tm_ef` | `str` | Effective time in `YYYYMMDDHHMI` format |
| `tm_seq` | `int` | Sequence number within the announcement |
| `area_code` | `str` | Warning zone code (e.g., `"S1151300"`) |
| `area_name` | `str` | Korean warning zone name (e.g., `"서울"`) |
| `warn_var` | `int` | Warning type code (see table below) |
| `warn_stress` | `int` | Severity code (see table below) |
| `cancel` | `int` | Cancellation flag: 0=active, 1=cancelled (only active in output) |
| `command` | `int` | Command code from KMA |
| `warn_fc` | `int` | Warning forecast flag |

#### `warn_var` — warning type codes

| Code | Korean | English |
|------|--------|---------|
| 1 | 강풍 | Strong wind |
| 2 | 호우 | Heavy rain |
| 3 | 한파 | Cold wave |
| 4 | 건조 | Dry conditions |
| 5 | 해일 | Storm surge |
| 6 | 태풍 | Typhoon |
| 7 | 대설 | Heavy snow |
| 8 | 황사 | Yellow dust |
| 11 | 폭염 | Heat wave |

#### `warn_stress` — severity codes

| Code | Korean | English |
|------|--------|---------|
| 0 | 주의보 | Watch |
| 1 | 경보 | Warning |

## Usage Example

```python
import asyncio
from kosmos.tools.kma.kma_weather_alert_status import _call, KmaWeatherAlertStatusInput

async def check_alerts():
    inp = KmaWeatherAlertStatusInput()  # defaults fetch all active alerts
    result = await _call(inp)
    print(f"Active alerts: {result['total_count']}")
    for w in result['warnings']:
        stress = "경보" if w['warn_stress'] == 1 else "주의보"
        print(f"  {w['area_name']}: {stress} (type {w['warn_var']})")

asyncio.run(check_alerts())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| `"03"` | No data | Return `total_count=0` and `warnings=[]` — **not** an error |
| Other | Error | Raise `ToolExecutionError` |

See [`koroad.md § Error Codes`](koroad.md#error-codes) for the full shared error code
table.

> **resultCode="03" is normal**: During calm weather, no active alerts exist and
> the API returns `resultCode="03"`. The adapter returns an empty `warnings` list
> instead of raising an exception.

## Wire Format Quirks

- **Single-item dict normalization**: When exactly one alert is active, `items.item`
  in the wire response is a plain dict, not a list. `_normalize_items()` wraps it in
  a list so `warnings` is always a `list`.
- **XML default**: Requests must include `_type=json` and `dataType=JSON`. If the
  response `Content-Type` contains `xml` without `json`, `ToolExecutionError` is
  raised.
- **resultCode="03" is not an error**: This code means no active weather alerts exist
  at query time. The adapter returns `total_count=0` and an empty `warnings` list.
- **Cancelled alert filtering**: Items with `cancel=1` are silently filtered out
  before the output is returned. `total_count` reflects only non-cancelled (active)
  warnings.
- **camelCase-to-snake_case mapping**: Wire fields use camelCase (`stnId`, `tmFc`,
  `areaCode`, `warnVar`, etc.); output model fields use snake_case (`stn_id`, `tm_fc`,
  `area_code`, `warn_var`, etc.). The mapping is performed by `_FIELD_MAP` in the
  module.
- **Nested response structure**: Unlike KOROAD, this endpoint wraps results in
  `response.header` and `response.body.items.item` (not a flat top-level structure).
- **num_of_rows=2000 default**: The default value of 2000 is intentionally large to
  ensure all active alerts fit in a single page, avoiding the need for pagination.

## Related Tools

- [`road_risk_score`](road-risk-score.md) — composite tool that calls this adapter
  internally as one of its three inner adapters
- [`kma-pre-warning.md`](kma-pre-warning.md) — pre-warning announcements that precede
  formal alerts issued by this adapter
