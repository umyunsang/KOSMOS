---
tool_id: kma_short_term_forecast
primitive: find
tier: live
permission_tier: 1
---

# kma_short_term_forecast

## Overview

Fetches the KMA short-term forecast (단기예보) for a grid point, covering approximately 3 days ahead at hourly resolution. Returns a paginated list of raw pivot-row forecast items covering temperature, precipitation probability, sky condition, humidity, wind, and more.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | KMA (기상청) — VilageFcstInfoService_2.0/getVilageFcst |
| Primitive | `find` |
| Module | `src/ummaya/tools/kma/kma_short_term_forecast.py` |

## Envelope

**Input model**: `KmaShortTermForecastInput` defined at `src/ummaya/tools/kma/kma_short_term_forecast.py:43-91`.

| Field | Type | Required | Description |
|---|---|---|---|
| `base_date` | `str` | yes | Forecast base date in `YYYYMMDD` format. |
| `base_time` | `str` | yes | Forecast base time. Must be one of: `0200`, `0500`, `0800`, `1100`, `1400`, `1700`, `2000`, `2300` (KST). Data is published ~10 minutes after each base time. |
| `nx` | `int` | yes | KMA Lambert grid X coordinate (1–149). |
| `ny` | `int` | yes | KMA Lambert grid Y coordinate (1–253). |
| `num_of_rows` | `int` | no | Rows per page. Default `290` (covers a full 3-day forecast for one grid point). |
| `page_no` | `int` | no | 1-indexed page number. Default `1`. |
| `data_type` | `Literal["JSON", "XML"]` | no | Response format. Default `"XML"` to match the KMA technical guide and public examples. JSON remains available when explicitly requested. |

**Output model**: `KmaShortTermForecastOutput` defined at `src/ummaya/tools/kma/kma_short_term_forecast.py:130-140`.

| Field | Type | Required | Description |
|---|---|---|---|
| `total_count` | `int` | yes | Total forecast items available for this query. |
| `items` | `list[ForecastItem]` | yes | Forecast pivot rows for the requested page. Each `ForecastItem` carries `base_date`, `base_time`, `fcst_date`, `fcst_time`, `nx`, `ny`, `category`, `fcst_value`. |

`ForecastItem` category codes include: `TMP` (temperature °C), `SKY` (sky: 1=clear/3=cloudy/4=overcast), `PTY` (precipitation type), `POP` (precipitation probability %), `REH` (humidity %), `WSD` (wind speed m/s), `UUU`, `VVV`, `VEC` (wind components/direction), `WAV` (wave height), `PCP` (precipitation amount string), `SNO` (snowfall), `TMN`/`TMX` (min/max temperature).

## Search hints

- 한국어: `단기예보`, `날씨예보`, `기온`, `강수확률`, `하늘상태`, `습도`, `풍속`, `풍향`
- English: `short-term forecast`, `weather temperature`, `precipitation probability`, `sky condition`, `humidity`, `wind speed`

## Endpoint

- **KMA API Hub endpoint**: `https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst`
- **Source URL**: https://apihub.kma.go.kr/apiList.do?seqApi=10
- **Authentication**: KMA API Hub key via `UMMAYA_KMA_API_HUB_AUTH_KEY` as `authKey`.

## Permission tier rationale

This adapter is classified as Permission tier 1 (green) per Spec 033 (`specs/033-permission-v2-spectrum/spec.md`). Short-term forecast data is publicly available meteorological information with no personal data content (`pipa_class=non_personal`, `auth_level=AAL1`). The query is read-only, idempotent, and concurrency-safe. `cache_ttl_seconds=1800` (30 minutes) reflects the KMA publication schedule (8 base times/day, roughly every 3 hours). No citizen consent prompt is needed; automatic execution within a lookup session is appropriate.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "kma_short_term_forecast",
  "params": {
    "base_date": "20260426",
    "base_time": "1100",
    "nx": 61,
    "ny": 125,
    "num_of_rows": 10,
    "page_no": 1
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "kma_short_term_forecast",
  "result": {
    "total_count": 290,
    "items": [
      {
        "base_date": "20260426",
        "base_time": "1100",
        "fcst_date": "20260426",
        "fcst_time": "1200",
        "nx": 61,
        "ny": 125,
        "category": "TMP",
        "fcst_value": "19"
      },
      {
        "base_date": "20260426",
        "base_time": "1100",
        "fcst_date": "20260426",
        "fcst_time": "1200",
        "nx": 61,
        "ny": 125,
        "category": "POP",
        "fcst_value": "10"
      }
    ]
  }
}
```

### Conversation snippet

```text
Citizen: 오늘 오후 서울 날씨 어때요? 비가 올 가능성이 있나요?
UMMAYA: 2026년 4월 26일 오전 11시 기준 서울(격자 61, 125) 단기예보입니다. 오후 12시 기온은 19°C로 예상되며 강수확률은 10%입니다. 비 올 가능성은 낮습니다. 전체 3일 예보는 총 290개 항목이 있으며 페이지를 늘려 조회할 수 있습니다.
```

## Constraints

- **Rate limit**: KMA API Hub applies the approved API usage quota for this service. In-adapter rate limit: 10 requests/minute (`rate_limit_per_minute=10`).
- **Freshness window**: KMA publishes short-term forecasts 8 times/day. `cache_ttl_seconds=1800`. Requesting a `base_time` that has not yet been published (within 10 minutes of issue time) may return a `NO_DATA` error.
- **Endpoint caveat**: This adapter uses the KMA API Hub `authKey` surface. The data.go.kr `serviceKey` credential is not accepted for this adapter.
- **Fixture coverage gaps**: PCP and SNO values are range strings (e.g. `"30.0~50.0mm"`, `"강수없음"`) stored as-is in `fcst_value`; numeric parsing is the caller's responsibility. TMN/TMX items appear only once per day, not every hour.
- **Error envelope examples**:
  - Tier-1 fail: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "kma_short_term_forecast", "message": "KMA API error: resultCode='03' resultMsg='NO_DATA'"}}`
  - Tier-2 / Tier-3 (auth) fail: `{"error": {"code": "CONFIGURATION_ERROR", "message": "Missing required environment variable: UMMAYA_KMA_API_HUB_AUTH_KEY"}}`
  - Network timeout: `{"error": {"code": "TOOL_EXECUTION_ERROR", "tool_id": "kma_short_term_forecast", "message": "HTTP error from KMA short-term forecast API: 503"}}`
