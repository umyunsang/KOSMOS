# Tool Adapter Reference

KOSMOS Tool Adapters wrap Korean government APIs (`data.go.kr`) and expose them as
Pydantic v2-typed tools through the KOSMOS tool registry.

## Tool Registry

| Tool ID | Korean Name | Provider | Description |
|---------|-------------|----------|-------------|
| [`koroad_accident_search`](koroad.md) | 교통사고 위험지역 조회 | 도로교통공단 (KOROAD) | Search accident hotspot zones by province, district, and year category |
| [`kma_weather_alert_status`](kma-alert.md) | 기상특보 현황 조회 | 기상청 (KMA) | List active weather warnings and watches nationwide |
| [`kma_current_observation`](kma-observation.md) | 초단기실황 관측 조회 | 기상청 (KMA) | Fetch current weather observations (temperature, precipitation, wind) at a KMA 5 km grid point |
| [`kma_short_term_forecast`](kma-short-term-forecast.md) | 단기예보 조회 | 기상청 (KMA) | Retrieve 3-day forecast published 8 times per day at a KMA grid point |
| [`kma_ultra_short_term_forecast`](kma-ultra-short-term-forecast.md) | 초단기예보 조회 | 기상청 (KMA) | Retrieve next-6-hour forecast published hourly at HH:30 KST |
| [`kma_pre_warning`](kma-pre-warning.md) | 기상예비특보목록 조회 | 기상청 (KMA) | List pre-warning announcements that precede formal weather warnings |
| [`road_risk_score`](road-risk-score.md) | 도로 위험도 종합 평가 | KOSMOS (composite) | Compute a normalized road risk score by fanning out to KOROAD and KMA inner adapters in parallel |

## Authentication

All seven tools share a single environment variable:

```
KOSMOS_DATA_GO_KR_API_KEY
```

This key is the operator-level `serviceKey` parameter required by all `apis.data.go.kr`
endpoints. No per-tool or per-provider separate keys exist. All tools have
`requires_auth=False` — citizen authentication is not required; only the operator API
key is needed.

Set the variable before running any adapter:

```bash
export KOSMOS_DATA_GO_KR_API_KEY="your_service_key_here"
```

Obtain a key by registering at [data.go.kr](https://www.data.go.kr/).

## Shared Error Codes

All `data.go.kr` adapters return HTTP 200 for both success and business-layer errors.
The actual result is in the `resultCode` field of the JSON response body.

| `resultCode` | Meaning | Adapter behavior |
|---|---|---|
| `"00"` | Normal (success) | Parse and return data |
| `"03"` | No data (NODATA_ERROR) | Return empty list or zero count — **not** an error |
| `"10"` | Wrong parameter | Raise `ToolExecutionError` |
| `"12"` | No data (alt) | Raise `ToolExecutionError` |
| `"20"` | Service error | Raise `ToolExecutionError` |
| `"22"` | Limit exceeded | Raise `ToolExecutionError` |
| `"30"` | Unregistered key | Raise `ToolExecutionError` |
| `"31"` | Expired key | Raise `ToolExecutionError` |
| `"32"` | IP blocked | Raise `ToolExecutionError` |
| `"99"` | Unknown error | Raise `ToolExecutionError` |

The full error code reference lives in [`koroad.md § Error Codes`](koroad.md#error-codes).

> **Note on `resultCode="03"`**: This code means "no matching data exists" and is the
> normal response when querying a district with no accidents, or during calm weather
> with no active alerts. The adapters return empty lists, not errors.

## Data Sources

| Adapter | Upstream API | Endpoint pattern |
|---------|-------------|-----------------|
| `koroad_accident_search` | KOROAD getRestFrequentzoneLg | `apis.data.go.kr/B552061/...` |
| `kma_weather_alert_status` | KMA getWthrWrnList | `apis.data.go.kr/1360000/WthrWrnInfoService/...` |
| `kma_current_observation` | KMA getUltraSrtNcst | `apis.data.go.kr/1360000/VilageFcstInfoService_2.0/...` |
| `kma_short_term_forecast` | KMA getVilageFcst | `apis.data.go.kr/1360000/VilageFcstInfoService_2.0/...` |
| `kma_ultra_short_term_forecast` | KMA getUltraSrtFcst | `apis.data.go.kr/1360000/VilageFcstInfoService_2.0/...` |
| `kma_pre_warning` | KMA getWthrPwnList | `apis.data.go.kr/1360000/WthrWrnInfoService/...` |
| `road_risk_score` | Composite (no direct endpoint) | Fans out to KOROAD + KMA |

> **Note on HTTP vs. HTTPS**: KMA forecast endpoints (`getVilageFcst`, `getUltraSrtFcst`,
> `getWthrPwnList`) use `http://` (not `https://`). Ensure outbound HTTP is allowed in
> your network policy. KOROAD and KMA alert/observation endpoints use `https://`.
