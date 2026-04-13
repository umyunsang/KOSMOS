# KMA Pre-Warning — `kma_pre_warning`

기상예비특보목록 조회 (Weather Pre-Warning List)

## Overview

| Field | Value |
|-------|-------|
| Tool ID | `kma_pre_warning` |
| Korean Name (`name_ko`) | 기상예비특보목록 조회 |
| Provider | 기상청 (KMA) |
| Endpoint | `http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrPwnList` |
| Auth Type | `api_key` — `KOSMOS_DATA_GO_KR_API_KEY` |
| Rate Limit | 10 calls / minute (client-side) |
| Cache TTL | 300 seconds |
| Personal Data | No |
| Concurrency Safe | Yes |

Returns pre-warning (예비특보) announcements that precede formal weather warnings.
Pre-warnings are issued by KMA when a weather event is developing but has not yet
reached the threshold for a formal watch (주의보) or warning (경보). During calm
weather with no developing events, the API returns no items — this is the normal state.

> **Note on URL**: This endpoint uses `http://` (not `https://`). Ensure outbound
> plain HTTP is allowed in your network policy.

## Input Schema (`KmaPreWarningInput`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `num_of_rows` | `int` (≥1) | No | 100 | Rows per page |
| `page_no` | `int` (≥1) | No | 1 | Page number, 1-indexed |
| `stn_id` | `str \| None` | No | `None` | Station filter; omit for all stations |
| `data_type` | `"JSON" \| "XML"` | No | `"JSON"` | Response format |

**`stn_id` wire behavior**: When `stn_id` is provided, the value is sent as the
`stnId` query parameter. When `stn_id` is `None`, the `stnId` parameter is **not
sent at all** (not sent as an empty string). Omitting it returns results from all
stations.

## Output Schema (`KmaPreWarningOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `total_count` | `int` | Total number of pre-warning items available |
| `items` | `list[PreWarningItem]` | Pre-warning announcement items for the requested page |

### `PreWarningItem` fields

| Field | Type | Description |
|-------|------|-------------|
| `stn_id` | `str` | Station/region ID that issued the pre-warning |
| `title` | `str` | Announcement title (e.g., `"[예비] 제06-7호 : 2017.06.07.07:30"`) |
| `tm_fc` | `str` | Announcement time in `YYYYMMDDHHMI` format |
| `tm_seq` | `int` | Monthly sequence number of this announcement |

### Wire camelCase mapping for `PreWarningItem`

| Wire field | Output field |
|------------|-------------|
| `stnId` | `stn_id` |
| `title` | `title` |
| `tmFc` | `tm_fc` |
| `tmSeq` | `tm_seq` |

## Station IDs

Station IDs filter results to a specific KMA regional station. Known examples:

| `stn_id` | Region |
|----------|--------|
| `"108"` | Seoul (서울) |
| `"159"` | Busan (부산) |

A comprehensive KMA station code table (100+ entries) is deferred to a future issue.
For the full list, consult the KMA API documentation or the upstream
[data.go.kr service page](https://www.data.go.kr/data/15059483/openapi.do).

## Usage Example

```python
import asyncio
from kosmos.tools.kma.kma_pre_warning import _call, KmaPreWarningInput

async def get_pre_warnings():
    # Query all stations (no stn_id filter)
    inp = KmaPreWarningInput()
    result = await _call(inp)
    print(f"Pre-warnings: {result['total_count']}")
    for item in result['items']:
        print(f"  [{item['stn_id']}] {item['title']} @ {item['tm_fc']}")

async def get_seoul_pre_warnings():
    # Filter to Seoul station
    inp = KmaPreWarningInput(stn_id="108")
    result = await _call(inp)
    print(f"Seoul pre-warnings: {result['total_count']}")

asyncio.run(get_pre_warnings())
```

If `KOSMOS_DATA_GO_KR_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_DATA_GO_KR_API_KEY not set`.

## Error Codes

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| `"03"` | No data | Return `total_count=0` and `items=[]` — **not** an error |
| Other | Error | Raise `ToolExecutionError` |

See [`koroad.md § Error Codes`](koroad.md#error-codes) for the full shared error code
table.

## Wire Format Quirks

- **`resultCode="03"` is the normal state**: During calm weather with no developing
  weather events, the API returns `resultCode="03"` (no data). The adapter returns
  an empty `items` list with `total_count=0` instead of raising an exception. This
  is common — do not treat it as an error.
- **Title format**: Pre-warning titles follow the pattern
  `"[예비] 제{NN}-{N}호 : YYYY.MM.DD.HH:MI"`.
  Example: `"[예비] 제06-7호 : 2017.06.07.07:30"`.
- **`http://` base URL**: This endpoint uses plain `http://`. Ensure outbound HTTP
  is permitted in your network policy.
- **`stn_id` omission**: When `stn_id` is `None`, the adapter does not include
  `stnId` in the query parameters. This is distinct from sending an empty string.
- **Single-item dict normalization**: When exactly one pre-warning item is present,
  `items.item` is a plain dict. The adapter wraps it in a list.
- **camelCase-to-snake_case**: Wire fields use camelCase; the adapter maps them to
  snake_case output fields via explicit string lookups in `_parse_response`.

## Related Tools

- [`kma-alert.md`](kma-alert.md) — formal weather warnings (주의보/경보); pre-warnings
  from this adapter typically precede formal warnings issued by the alert adapter
