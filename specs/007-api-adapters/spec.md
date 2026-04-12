# Feature Specification: Phase 1 API Adapters (KOROAD, KMA, Road Risk)

**Epic**: #7
**Created**: 2026-04-13
**Status**: Draft
**Layer**: Layer 2 — Tool System
**Input**: Three government API adapters (KOROAD AccidentHazard, KMA WeatherAlert, KMA ShortTermForecast) and one composite adapter (Road Risk Index) that fuses KOROAD and KMA data to power Scenario 1: Route Safety.

---

## Overview and Context

Scenario 1 is the primary acceptance test for Phase 1 of KOSMOS:

> Citizen: "오늘 서울 가는 길 안전해?" (Is the road to Seoul safe today?)
> KOSMOS: fuses KOROAD accident data + KMA weather alerts + road risk index
>          → actionable route safety recommendation

This epic implements the first three live government API adapters and one composite fusion adapter. These tools are the first concrete data sources loaded into the tool registry from Epic #6 (Tool System). They exercise the `GovAPITool` contract, demonstrate fail-closed defaults in practice, and prove Scenario 1 end-to-end.

### Endpoint inventory and classification

| Endpoint | Provider | Decision | Justification |
|---|---|---|---|
| `getRestFrequentzoneLg` | KOROAD / `B552061/frequentzoneLg/` | **include** | Returns accident hotspot polygons by municipality; directly answers "dangerous zone near me" |
| `getWMSFrequentzoneLg` | KOROAD / `B552061/frequentzoneLg/` | **exclude** | Returns a WMS PNG tile (image/png), not machine-readable data; not useful for a conversational AI |
| `getPwnStatus` | KMA / `1360000/WthrWrnInfoService/` | **include** | Returns current weather warning status across all warning zones; best single call for "any active alerts in my region" |
| `getWthrWrnList` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Returns warning list with pagination by time range; useful for history queries but not needed for real-time Scenario 1 |
| `getWthrWrnMsg` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Full warning bulletin text; verbose, better as a follow-up after `getPwnStatus` confirms an active alert |
| `getWthrInfoList` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Weather information (non-alert) list; useful for Scenario 5 (disaster) but not Scenario 1 |
| `getWthrInfo` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Full weather info text; defer for same reason as `getWthrWrnMsg` |
| `getWthrBrkNewsList` | KMA / `1360000/WthrWrnInfoService/` | **exclude** | Weather flash news list; low relevance for transport safety |
| `getWthrBrkNews` | KMA / `1360000/WthrWrnInfoService/` | **exclude** | Flash news full text; exclude for same reason |
| `getWthrPwnList` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Pre-warning list; useful later for predictive safety alerts but out of scope Phase 1 |
| `getWthrPwn` | KMA / `1360000/WthrWrnInfoService/` | **defer** | Pre-warning full text; defer for same reason |
| `getPwnCd` | KMA / `1360000/WthrWrnInfoService/` | **exclude** | Warning code lookup table; static metadata, better served by a built-in Enum than a live API call |
| `getUltraSrtNcst` | KMA / `1360000/VilageFcstInfoService_2.0/` | **include** | Ultra-short-term current observation (updated every 10 min); provides T1H (temperature), RN1 (1-hour precipitation), WSD (wind speed) — essential for current road condition assessment |
| `getUltraSrtFcst` | KMA / `1360000/VilageFcstInfoService_2.0/` | **defer** | 6-hour ahead forecast; useful for "road conditions in 3 hours" but not Scenario 1 current-state focus |
| `getVilageFcst` | KMA / `1360000/VilageFcstInfoService_2.0/` | **defer** | Short-term (up to ~72h) forecast; valuable for trip planning but deferred to Phase 2 |
| `getFcstVersion` | KMA / `1360000/VilageFcstInfoService_2.0/` | **exclude** | Forecast version metadata; internal API utility, not citizen-facing |
| Road Risk Index (composite) | KOROAD + KMA | **include** | Derived score fusing accident hotspot density and current weather hazard; the highest-value output for Scenario 1 |

### Tools included in this epic

| Tool ID | Source | Description |
|---|---|---|
| `koroad_accident_search` | KOROAD `getRestFrequentzoneLg` | Accident hotspot zones by municipality and year category |
| `kma_weather_alert_status` | KMA `getPwnStatus` | Current weather warning status by warning zone |
| `kma_current_observation` | KMA `getUltraSrtNcst` | Current weather observation at a 5 km grid point (precipitation, temperature, wind) |
| `road_risk_score` | Composite (KOROAD + KMA) | Road segment risk score derived from accident density and current weather hazards |

---

## User Stories

### US-001 — Query accident hotspot zones by municipality (P1)

A citizen asks "서울 강남구 사고 많은 곳 알려줘" (Tell me the accident-prone areas in Gangnam-gu, Seoul). KOSMOS calls `koroad_accident_search` with `sido=11` (Seoul) and `gugun=680` (Gangnam-gu) and returns a list of accident hotspot locations with coordinates, accident counts, casualties, and road geometry.

**Why P1**: This is the primary data source for Scenario 1. Without accident hotspot data, the road risk answer is unfounded.

**Independent Test**: Can be tested with a recorded fixture for sido=11, gugun=680 without any live API call.

**Acceptance Scenarios**:

1. **Given** a valid `sido` code (11) and `gugun` code (680), **When** `koroad_accident_search` is called, **Then** the response includes one or more hotspot records each with `spot_cd`, `spot_nm`, `occrrnc_cnt`, `caslt_cnt`, `la_crd`, `lo_crd`, and optionally `geom_json`.
2. **Given** an invalid `sido` code (e.g., 99), **When** `koroad_accident_search` is called, **Then** the tool returns a structured error with `error_type="execution"` and does not raise an unhandled exception.
3. **Given** a valid `searchYearCd` for the latest year (2025119 for 2024 municipality data), **When** the request is made, **Then** the `afos_id` in the response matches the expected year category code.
4. **Given** no results found for a rural municipality, **When** `koroad_accident_search` is called, **Then** the tool returns an empty `hotspots` list and `total_count=0` rather than an error.

---

### US-002 — Query current weather warning status by region (P1)

A citizen asks "오늘 경부고속도로 가는데 기상 경보 있어?" (Any weather warnings on the Gyeongbu Expressway today?). KOSMOS calls `kma_weather_alert_status` to retrieve all currently active weather warnings. The system then filters by relevant `areaCode` values for the route.

**Why P1**: Weather warnings are the fastest-changing safety signal. Stale data is worse than no data for this use case.

**Independent Test**: Can be tested with a recorded fixture from a past date with known active warnings (e.g., a recorded typhoon alert day).

**Acceptance Scenarios**:

1. **Given** a call to `kma_weather_alert_status` with no filters, **When** warnings are active nationwide, **Then** the response includes a list of warning items each with `areaCode`, `areaName`, `warnVar` (warning type code), `warnStress` (severity level), `tmFc` (announcement time), and `tmEf` (effective time).
2. **Given** a call to `kma_weather_alert_status` on a day with no active warnings, **When** the API returns an empty items list, **Then** the tool returns `warnings=[]` and `total_count=0` — not an error.
3. **Given** the API returns `resultCode != "00"`, **When** the tool receives the response, **Then** it returns `error_type="execution"` with the `resultMsg` included in the error message.
4. **Given** a filter for `stnId` (station ID), **When** passed as an optional parameter, **Then** only warnings for that station are returned.

---

### US-003 — Query current weather observation at a grid point (P1)

A citizen provides a location (e.g., 서울 서초구). KOSMOS resolves it to KMA grid coordinates (nx, ny) and calls `kma_current_observation` to get current precipitation, temperature, and wind speed.

**Why P1**: Current precipitation and wind are the leading indicators of road hazard. The `getUltraSrtNcst` endpoint updates every 10 minutes — the freshest available data source.

**Independent Test**: Can be tested with a recorded fixture for a known grid point (e.g., nx=61, ny=125 for central Seoul).

**Acceptance Scenarios**:

1. **Given** valid grid coordinates (`nx=61`, `ny=125`), **When** `kma_current_observation` is called, **Then** the response includes `T1H` (temperature °C), `RN1` (1-hour precipitation mm), `WSD` (wind speed m/s), `UUU` (east-west wind), `VVV` (north-south wind), `REH` (humidity %), and the observation timestamp.
2. **Given** grid coordinates outside the South Korea coverage area, **When** `kma_current_observation` is called, **Then** the API returns a non-zero `resultCode` and the tool surfaces a structured error.
3. **Given** a `base_time` that is less than 10 minutes after the current hour (i.e., data not yet available), **When** the tool is called, **Then** it automatically retries with the previous hour's `base_time` rather than failing.
4. **Given** `RN1 = 0` or `RN1 = "-"`, **When** the tool parses the response, **Then** it normalizes the value to `0.0` (float) rather than raising a validation error.

---

### US-004 — Compute road risk score by fusing KOROAD and KMA data (P1)

A citizen asks "오늘 서울 강남 가는 길 안전해?" (Is the road to Gangnam, Seoul safe today?). KOSMOS calls `road_risk_score` with the origin/destination and date. The composite adapter internally calls `koroad_accident_search` (accident density) and `kma_current_observation` (current weather hazard) and returns a single risk score with justification.

**Why P1**: This is the Scenario 1 acceptance test. The composite fusion is what turns two raw API calls into a citizen-facing answer.

**Independent Test**: Can be tested with mocked inner tool responses to verify scoring logic independently of live APIs.

**Acceptance Scenarios**:

1. **Given** a target municipality (`sido=11`, `gugun=680`) and current grid point (`nx=61`, `ny=125`), **When** `road_risk_score` is called, **Then** the response includes a `risk_level` (`low`/`moderate`/`high`/`severe`), a numeric `risk_score` (0.0–1.0), `accident_hotspot_count`, `active_weather_warnings`, `precipitation_mm`, and a `summary` string in Korean.
2. **Given** the KOROAD adapter returns 0 hotspots and KMA returns no precipitation, **When** `road_risk_score` is computed, **Then** `risk_level="low"` and `risk_score` is in [0.0, 0.3).
3. **Given** the KOROAD adapter returns 5+ hotspots AND KMA returns precipitation > 5 mm/h, **When** `road_risk_score` is computed, **Then** `risk_level="high"` or `"severe"` and the summary mentions both accident risk and weather hazard.
4. **Given** one inner adapter (e.g., KMA) fails with a transient error, **When** `road_risk_score` is called, **Then** it returns a partial result with `risk_level` computed from available data only, and `summary` notes the data gap (e.g., "weather data unavailable").
5. **Given** all inner adapters fail, **When** `road_risk_score` is called, **Then** it returns `error_type="execution"` rather than a partial result, since the score cannot be computed at all.

---

### US-005 — All adapters use recorded fixtures in CI (P2)

A developer runs `uv run pytest` without any live API keys. All four adapters pass their happy-path and error-path tests using pre-recorded fixture files under `tests/fixtures/`.

**Why P2**: CI stability. Without fixtures, every CI run would depend on live government API availability and daily quotas.

**Acceptance Scenarios**:

1. **Given** no `KOSMOS_KOROAD_API_KEY` or `KOSMOS_DATA_GO_KR_KEY` env vars, **When** `uv run pytest tests/tools/` is run, **Then** all non-`@pytest.mark.live` tests pass using recorded JSON fixtures.
2. **Given** a recorded fixture is present, **When** the fixture JSON is loaded, **Then** it parses cleanly against the tool's `output_schema` Pydantic model with no validation errors.

---

### US-006 — Shared code-table enums are validated at registration time (P2)

A developer registers the KOROAD adapter. The `searchYearCd`, `sido`, and `gugun` input parameters are validated against the official code table (from `AccidentHazard_CodeList.md`). Passing an unknown `sido` code raises a Pydantic `ValidationError` before the HTTP call is made.

**Why P2**: Fail-fast validation prevents quota waste on guaranteed-to-fail requests against the KOROAD API.

**Acceptance Scenarios**:

1. **Given** a call to `koroad_accident_search` with `sido=99` (not a valid code), **When** the input is validated, **Then** a `ValidationError` is raised listing the valid options.
2. **Given** a call with `sido=42` (old Gangwon-do code) and a `searchYearCd` for 2023 data, **When** the input is validated, **Then** a warning is emitted noting that `sido=51` (강원특별자치도) should be used for 2023+ data — this is a documented quirk.
3. **Given** a call with a valid `sido` but no `gugun`, **When** the request is made, **Then** results for the entire province are returned (gugun is optional per the API spec).

---

## Functional Requirements

### FR-001: KOROAD AccidentHazard adapter

- **Tool ID**: `koroad_accident_search`
- **Module path**: `src/kosmos/tools/koroad/koroad_accident_search.py`
- **Endpoint**: `http://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg`
- **HTTP method**: GET
- **Auth**: `serviceKey` query parameter (URL-encoded); sourced from `KOSMOS_KOROAD_API_KEY`
- **Wire format**: XML by default; request JSON with `_type=json` parameter
- **Auth type** on `GovAPITool`: `api_key`

**Input schema** (`KoroadAccidentSearchInput`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `searchYearCd` | `str` | Yes | Opaque year-category code from the code table; validated against `SearchYearCd` Enum |
| `siDo` | `int` | Yes | Province/city code; validated against `SidoCode` Enum |
| `guGun` | `int` | No | District code; validated against `GugunCode` Enum scoped to the given `siDo` |
| `numOfRows` | `int` | No | Default 10; max 100 |
| `pageNo` | `int` | No | Default 1 |

**Output schema** (`KoroadAccidentSearchOutput`):

| Field | Type | Notes |
|---|---|---|
| `total_count` | `int` | `totalCount` from response header |
| `page_no` | `int` | `pageNo` from response header |
| `num_of_rows` | `int` | `numOfRows` from response header |
| `hotspots` | `list[AccidentHotspot]` | List of accident hotspot records |

**`AccidentHotspot` sub-model**:

| Field | Type | Notes |
|---|---|---|
| `spot_cd` | `str` | Unique spot code (`spot_cd`) |
| `spot_nm` | `str` | Location name (`spot_nm`) |
| `sido_sgg_nm` | `str` | Province + district name (`sido_sgg_nm`) |
| `bjd_cd` | `str` | Administrative district code (`bjd_cd`) |
| `occrrnc_cnt` | `int` | Accident occurrence count (`occrrnc_cnt`) |
| `caslt_cnt` | `int` | Total casualty count (`caslt_cnt`) |
| `dth_dnv_cnt` | `int` | Death count (`dth_dnv_cnt`) |
| `se_dnv_cnt` | `int` | Serious injury count (`se_dnv_cnt`) |
| `sl_dnv_cnt` | `int` | Minor injury count (`sl_dnv_cnt`) |
| `wnd_dnv_cnt` | `int` | Injury count (`wnd_dnv_cnt`) |
| `la_crd` | `float` | Latitude (`la_crd`) |
| `lo_crd` | `float` | Longitude (`lo_crd`) |
| `geom_json` | `str \| None` | GeoJSON polygon geometry string (may be absent) |
| `afos_id` | `str` | Year-dataset identifier (`afos_id`) |
| `afos_fid` | `str` | Feature ID within the dataset (`afos_fid`) |

**Fail-closed flags**:

| Flag | Value | Justification |
|---|---|---|
| `requires_auth` | `True` (default) | Requires KOROAD API key |
| `is_personal_data` | `False` | Returns aggregate accident statistics, no individual records |
| `is_concurrency_safe` | `True` | Read-only, idempotent GET |
| `cache_ttl_seconds` | `86400` | Dataset updated annually; 24-hour cache is safe |
| `rate_limit_per_minute` | `30` | Conservative below stated 265 tps; per-key daily quota applies |
| `is_core` | `True` | Always loaded; core to Scenario 1 |

**search_hint**: `"교통사고 다발지역 traffic accident hotspot 사고위험 지역 KOROAD 도로교통공단 지자체별 사고"`

---

### FR-002: KMA WeatherAlert adapter

- **Tool ID**: `kma_weather_alert_status`
- **Module path**: `src/kosmos/tools/kma/kma_weather_alert_status.py`
- **Endpoint**: `http://apis.data.go.kr/1360000/WthrWrnInfoService/getPwnStatus`
- **HTTP method**: GET
- **Auth**: `serviceKey` query parameter; sourced from `KOSMOS_DATA_GO_KR_KEY`
- **Wire format**: XML (default) or JSON; request JSON with `dataType=JSON`
- **Auth type** on `GovAPITool`: `api_key`

**Input schema** (`KmaWeatherAlertStatusInput`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `numOfRows` | `int` | No | Default 2000 (returns all active alerts in one page; max page size) |
| `pageNo` | `int` | No | Default 1 |
| `dataType` | `Literal["JSON", "XML"]` | No | Default `"JSON"` |

Note: `getPwnStatus` returns the current snapshot of all active warnings. No date-range filter. Freshness is governed by the KMA update cadence (on-demand when a warning is issued or lifted).

**Output schema** (`KmaWeatherAlertStatusOutput`):

| Field | Type | Notes |
|---|---|---|
| `total_count` | `int` | Total active warnings |
| `warnings` | `list[WeatherWarning]` | Active warning items |

**`WeatherWarning` sub-model**:

| Field | Type | Notes |
|---|---|---|
| `stn_id` | `str` | Station ID (`stnId`) |
| `tm_fc` | `str` | Announcement time YYYYMMDDHHMI (`tmFc`) |
| `tm_ef` | `str` | Effective time YYYYMMDDHHMI (`tmEf`) |
| `tm_seq` | `int` | Sequence number (`tmSeq`) |
| `area_code` | `str` | Warning zone code (`areaCode`) e.g., `"S1151300"` |
| `area_name` | `str` | Warning zone name in Korean (`areaName`) |
| `warn_var` | `int` | Warning type code (`warnVar`); 1=강풍, 2=호우, 3=한파, 4=건조, 5=해일, 6=태풍, 7=대설, 8=황사, 11=폭염 |
| `warn_stress` | `int` | Severity level (`warnStress`); 0=주의보, 1=경보 |
| `cancel` | `int` | Cancellation flag (`cancel`); 0=active, 1=cancelled |
| `command` | `int` | Command code (`command`) |
| `warn_fc` | `int` | Warning forecast flag (`warFc`) |

**Fail-closed flags**:

| Flag | Value | Justification |
|---|---|---|
| `requires_auth` | `True` (default) | Requires data.go.kr API key |
| `is_personal_data` | `False` | Returns geographic aggregate weather alerts, no personal records |
| `is_concurrency_safe` | `True` | Read-only GET |
| `cache_ttl_seconds` | `300` | Alert status changes on-demand; 5-minute cache is reasonable |
| `rate_limit_per_minute` | `20` | Conservative below 30 tps; alert queries are infrequent |
| `is_core` | `True` | Always loaded; core to Scenario 1 and Scenario 5 |

**search_hint**: `"기상특보 weather alert warning 태풍 폭우 한파 대설 황사 KMA 기상청 재난"`

---

### FR-003: KMA Current Observation adapter

- **Tool ID**: `kma_current_observation`
- **Module path**: `src/kosmos/tools/kma/kma_current_observation.py`
- **Endpoint**: `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst`
- **HTTP method**: GET
- **Auth**: `serviceKey` query parameter; sourced from `KOSMOS_DATA_GO_KR_KEY`
- **Wire format**: XML (default) or JSON; request JSON with `dataType=JSON`
- **Auth type** on `GovAPITool`: `api_key`

**Input schema** (`KmaCurrentObservationInput`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `base_date` | `str` | Yes | Date in `YYYYMMDD` format |
| `base_time` | `str` | Yes | Hour in `HHMM` format (exact hour, e.g., `"0600"`); must be at least 10 min after the hour for data availability |
| `nx` | `int` | Yes | KMA grid X coordinate (1–149) |
| `ny` | `int` | Yes | KMA grid Y coordinate (1–253) |
| `numOfRows` | `int` | No | Default 10 |
| `pageNo` | `int` | No | Default 1 |
| `dataType` | `Literal["JSON", "XML"]` | No | Default `"JSON"` |

**Output schema** (`KmaCurrentObservationOutput`):

| Field | Type | Notes |
|---|---|---|
| `base_date` | `str` | Observation date |
| `base_time` | `str` | Observation time |
| `nx` | `int` | Grid X |
| `ny` | `int` | Grid Y |
| `t1h` | `float \| None` | Temperature in °C (`T1H`) |
| `rn1` | `float` | 1-hour precipitation in mm (`RN1`); 0.0 if none (normalized from null/"-"/0) |
| `uuu` | `float \| None` | East-west wind component m/s (`UUU`; east=positive) |
| `vvv` | `float \| None` | North-south wind component m/s (`VVV`; north=positive) |
| `wsd` | `float \| None` | Wind speed m/s (`WSD`) |
| `reh` | `float \| None` | Relative humidity % (`REH`) |
| `pty` | `int` | Precipitation type code (`PTY`): 0=none, 1=rain, 2=rain+snow, 3=snow, 5=drizzle, 6=drizzle+snow, 7=snow flurry |

**Code values for `pty`** (normalized from raw `obsrValue`):

| Code | Meaning |
|---|---|
| 0 | No precipitation |
| 1 | Rain |
| 2 | Rain/Snow mix |
| 3 | Snow |
| 5 | Drizzle |
| 6 | Drizzle + Snow flurry |
| 7 | Snow flurry |

**Fail-closed flags**:

| Flag | Value | Justification |
|---|---|---|
| `requires_auth` | `True` (default) | Requires data.go.kr API key |
| `is_personal_data` | `False` | Returns grid-level meteorological observations, no personal data |
| `is_concurrency_safe` | `True` | Read-only GET |
| `cache_ttl_seconds` | `600` | Data updates every 10 minutes; cache for one update cycle |
| `rate_limit_per_minute` | `20` | Conservative below 30 tps |
| `is_core` | `True` | Always loaded; core to Scenario 1 |

**search_hint**: `"현재 날씨 current weather observation 기온 강수 precipitation temperature wind 단기예보 KMA 기상청"`

---

### FR-004: Road Risk Score composite adapter

- **Tool ID**: `road_risk_score`
- **Module path**: `src/kosmos/tools/composite/road_risk_score.py`
- **Endpoint**: N/A (no direct HTTP call; orchestrates inner tool calls)
- **Auth type** on `GovAPITool`: `public` (auth handled by inner tools)

**Input schema** (`RoadRiskScoreInput`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `sido` | `int` | Yes | Province/city code (KOROAD `SidoCode` enum) |
| `gugun` | `int` | No | District code (KOROAD `GugunCode` enum) |
| `search_year_cd` | `str` | No | Year-category code; defaults to the most recent available year for the given hazard type |
| `nx` | `int` | Yes | KMA grid X coordinate for current weather |
| `ny` | `int` | Yes | KMA grid Y coordinate for current weather |
| `hazard_type` | `HazardType` | No | Accident dataset type; default `HazardType.GENERAL_2024`. Accepts any `HazardType` enum member (11 values); the composite `road_risk_score` tool restricts input to the 4 most common types via its own validation. |

**Output schema** (`RoadRiskScoreOutput`):

| Field | Type | Notes |
|---|---|---|
| `risk_score` | `float` | Composite score 0.0 (safe) to 1.0 (severe) |
| `risk_level` | `Literal["low", "moderate", "high", "severe"]` | Human label: low=[0,0.3), moderate=[0.3,0.6), high=[0.6,0.8), severe=[0.8,1.0] |
| `accident_hotspot_count` | `int` | Number of accident hotspot zones found in the area |
| `active_weather_warnings` | `int` | Count of active KMA warnings in nearby warning zones |
| `precipitation_mm` | `float` | Current 1-hour precipitation from KMA observation |
| `precipitation_type` | `int` | KMA `pty` code (0=none, 1=rain, 3=snow) |
| `summary` | `str` | Korean-language summary sentence for the citizen |
| `data_sources` | `list[str]` | Which inner adapters contributed: `["koroad", "kma_alert", "kma_obs"]` |
| `data_gaps` | `list[str]` | Which inner adapters failed (empty list if all succeeded) |

**Scoring algorithm** (minimum viable):

```
base_score = 0.0

# Accident density component (weight: 0.5)
if hotspot_count >= 5:
    base_score += 0.5
elif hotspot_count >= 2:
    base_score += 0.3
elif hotspot_count >= 1:
    base_score += 0.15

# Weather component (weight: 0.5)
if active_weather_warnings >= 1:
    base_score += 0.3  # any active warning is significant
if precipitation_mm >= 20:
    base_score += 0.2  # heavy rain
elif precipitation_mm >= 5:
    base_score += 0.15
elif precipitation_mm >= 1:
    base_score += 0.05
if precipitation_type == 3:  # snow
    base_score += 0.1  # bonus for snow on top of precipitation score

risk_score = min(1.0, base_score)
```

**Fail-closed flags**:

| Flag | Value | Justification |
|---|---|---|
| `requires_auth` | `False` | Composite tool; individual inner tools handle auth |
| `is_personal_data` | `False` | Derived aggregate score; no PII |
| `is_concurrency_safe` | `True` | Calls inner tools concurrently (both are concurrency-safe) |
| `cache_ttl_seconds` | `300` | Bounded by the shortest inner cache (weather alerts at 300s) |
| `rate_limit_per_minute` | `10` | Conservative; each call triggers 2 inner tool calls |
| `is_core` | `True` | Always loaded; the primary Scenario 1 tool |

**search_hint**: `"도로 안전 road safety risk 사고위험 weather hazard 운전 안전 경로 route recommendation 교통사고 기상"`

---

### FR-005: Shared code-table module

- **Module path**: `src/kosmos/tools/koroad/code_tables.py`
- **Purpose**: Pydantic-compatible Enum definitions for all KOROAD code table values

**Enums to define**:

| Enum | Values | Source |
|---|---|---|
| `SidoCode` | 11=Seoul, 26=Busan, 27=Daegu, 28=Incheon, 29=Gwangju, 30=Daejeon, 31=Ulsan, 36=Sejong, 41=Gyeonggi, 42=Gangwon(legacy), 43=Chungbuk, 44=Chungnam, 45=Jeonbuk(legacy), 46=Jeonnam, 47=Gyeongbuk, 48=Gyeongnam, 50=Jeju, 51=Gangwon(2023+), 52=Jeonbuk(2023+) | `AccidentHazard_CodeList.md § Sido` |
| `GugunCode` | Per-sido district codes; 3-digit integers | `AccidentHazard_CodeList.md § Gugun` |
| `SearchYearCd` | All valid year-category codes by hazard type | `AccidentHazard_CodeList.md § serachYearCd` |
| `HazardType` | `general`, `ice`, `pedestrian_child`, `pedestrian_elderly`, `bicycle`, `law_violation`, `holiday`, `motorcycle`, `pedestrian`, `drunk_driving`, `freight` | Derived from `serachYearCd` category names |

**Cross-validation rule**: The `KoroadAccidentSearchInput` model validator must verify that when `siDo=42` (old Gangwon) or `siDo=45` (old Jeonbuk), the `searchYearCd` refers to a 2022-or-earlier dataset. If a 2023+ year code is passed with an old sido code, emit a `ValidationError` with a correction hint.

---

### FR-006: KMA grid coordinate utility

- **Module path**: `src/kosmos/tools/kma/grid_coords.py`
- **Purpose**: Lookup table mapping Korean administrative regions to KMA (nx, ny) grid coordinates
- **Source**: KMA short-term forecast guide `별첨` Excel file (`kma_기상청41_단기예보 조회서비스_오픈API활용가이드_241128.md`)
- **Implementation**: Pre-populated dict `REGION_TO_GRID: dict[str, tuple[int, int]]` for the 17 metropolitan cities/provinces and their major districts
- **Coordinate system**: Lambert Conformal Conic projection, 5 km grid, reference point 126°E / 38°N, grid size NX=149 × NY=253

**Minimum coverage required for Phase 1**:

| Region | nx | ny |
|---|---|---|
| Seoul center (서울 중구) | 60 | 127 |
| Busan center (부산 중구) | 98 | 76 |
| Gyeongbu Expressway (대전 구간) | 67 | 100 |
| Gyeongbu Expressway (천안 구간) | 63 | 110 |

Exact coordinates for all major cities are in the KMA-supplied Excel attachment. The implementation reads from a hard-coded dict (not a live API call).

---

### FR-007: Fixture recording and test infrastructure

- **Fixture paths**:
  - `tests/fixtures/koroad/koroad_accident_search.json`
  - `tests/fixtures/kma/kma_weather_alert_status.json`
  - `tests/fixtures/kma/kma_current_observation.json`
- **Fixture format**: Raw JSON responses as returned by the live API after setting `dataType=JSON`
- **Test paths**:
  - `tests/tools/koroad/test_koroad_accident_search.py`
  - `tests/tools/kma/test_kma_weather_alert_status.py`
  - `tests/tools/kma/test_kma_current_observation.py`
  - `tests/tools/composite/test_road_risk_score.py`
- **Live test marker**: `@pytest.mark.live` — skipped by default in CI

Each test module must provide:
- One `test_happy_path_from_fixture()` that loads the fixture and validates against the output schema
- One `test_error_path_bad_input()` that passes an invalid `sido` / invalid grid coordinate and expects a structured `ToolResult` with `success=False`
- One `test_missing_api_key()` that unsets the env var and expects the executor to raise `ToolNotFoundError` or return an auth error before any HTTP call

---

## Non-Functional Requirements

### NFR-001: No hardcoded credentials

All API keys must be sourced from environment variables:
- `KOSMOS_KOROAD_API_KEY` — for KOROAD `B552061/frequentzoneLg/` endpoints
- `KOSMOS_DATA_GO_KR_KEY` — for KMA `1360000/WthrWrnInfoService/` and `1360000/VilageFcstInfoService_2.0/` endpoints

If the relevant env var is not set, the adapter must raise a `ConfigurationError` (or equivalent) before making any HTTP call. Never fall back to a demo key or hardcoded value.

### NFR-002: Pydantic v2 with no Any types

All input and output schemas must use Pydantic v2 `BaseModel`. No field may use `typing.Any`. Where the API may return mixed types (e.g., `obsrValue` is sometimes a float, sometimes a string like `"-"`), the model must use a discriminated union or a `@field_validator` with explicit normalization.

### NFR-003: Wire format handling

Both KMA APIs default to XML. Adapters must request JSON explicitly (`dataType=JSON`). KOROAD returns XML by default; adapters must use the `_type=json` parameter to request JSON. If the API ignores the JSON request and returns XML (observed occasionally on some data.go.kr endpoints), the adapter must fall back to XML parsing via `xml.etree.ElementTree` and log a warning.

The HTTP client is `httpx` (async). Response parsing must handle both the `resultCode="00"` success path and non-zero result codes as structured errors.

### NFR-004: Rate limit compliance

- KOROAD `getRestFrequentzoneLg`: stated 265 tps; adapter declares `rate_limit_per_minute=30`
- KMA `getPwnStatus`: stated 30 tps; adapter declares `rate_limit_per_minute=20`
- KMA `getUltraSrtNcst`: stated 30 tps; adapter declares `rate_limit_per_minute=20`
- `road_risk_score`: adapter declares `rate_limit_per_minute=7` (each call triggers 3 concurrent inner calls: KOROAD + kma_alert + kma_obs; conservative rate prevents quota burst across all three APIs)

The `ToolRegistry.get_rate_limiter(tool_id)` mechanism from Epic #6 is the enforcement point. Adapters do not implement their own throttling.

### NFR-005: Logging

All adapters use `logging.getLogger(__name__)` (stdlib only). No `print()` statements outside of test output. Log levels:
- `DEBUG`: raw request URL (with key redacted), raw response size
- `INFO`: successful call with `tool_id` and response `total_count`
- `WARNING`: JSON parse fallback to XML; KMA grid data missing for requested region
- `ERROR`: non-zero `resultCode`; HTTP 4xx/5xx; timeout

### NFR-006: Performance

- Each adapter call must complete within 5 seconds (httpx timeout setting)
- The `road_risk_score` composite adapter must call `koroad_accident_search` and `kma_current_observation` concurrently using `asyncio.gather`; total latency target is the slower of the two inner calls plus 200ms overhead

---

## Success Criteria

| ID | Criterion | Measurable signal |
|---|---|---|
| SC-001 | All four tools register successfully in the `ToolRegistry` without errors | `pytest tests/tools/test_registration.py` passes |
| SC-002 | `koroad_accident_search` happy-path test passes with recorded fixture | `pytest tests/tools/koroad/test_koroad_accident_search.py::test_happy_path_from_fixture` passes |
| SC-003 | `kma_weather_alert_status` happy-path test passes with recorded fixture | `pytest tests/tools/kma/test_kma_weather_alert_status.py::test_happy_path_from_fixture` passes |
| SC-004 | `kma_current_observation` happy-path test passes with recorded fixture | `pytest tests/tools/kma/test_kma_current_observation.py::test_happy_path_from_fixture` passes |
| SC-005 | `road_risk_score` returns correct `risk_level` for high-accident + heavy-rain inputs using mocked inner tools | `pytest tests/tools/composite/test_road_risk_score.py::test_high_risk_scenario` passes |
| SC-006 | Invalid `sido=99` raises `ValidationError` before any HTTP call is made | `pytest tests/tools/koroad/test_koroad_accident_search.py::test_error_path_bad_input` passes |
| SC-007 | Missing API key raises a `ConfigurationError` before any HTTP call | `pytest tests/tools/koroad/test_koroad_accident_search.py::test_missing_api_key` passes |
| SC-008 | All adapters are `is_personal_data=False` (aggregate data, no PII) | Code review check; confirmed by constitution compliance scan |
| SC-009 | `uv run pytest tests/` passes with zero live API calls (no `KOSMOS_*_KEY` env vars set) | CI green badge |
| SC-010 | The `road_risk_score` tool appears in `search_tools("오늘 서울 가는 길 안전해")` results | `pytest tests/tools/test_search_integration.py::test_scenario_1_discovery` passes |

---

## Edge Cases

### EC-001: KOROAD year-code mismatch with sido code

The `sido` code for Gangwon-do changed from 42 to 51 in 2023, and Jeonbuk from 45 to 52. Passing the old code with a post-2022 `searchYearCd` silently returns empty results from the API (no error). The adapter must detect this via the cross-validation rule in FR-005 and raise `ValidationError` with a correction hint.

### EC-002: KMA observation data not yet available

`getUltraSrtNcst` data is available 10 minutes after each hour. If called within the first 10 minutes of an hour (e.g., 14:07), the current hour's data does not exist. The API returns `resultCode != "00"`. The adapter must retry with `base_time` set to the previous hour exactly once before surfacing an error.

### EC-003: KMA returns `obsrValue = "-"` for no precipitation

For `category=RN1`, the API returns the string `"-"` (not `null`, not `"0"`) when there is no precipitation. The `KmaCurrentObservationOutput.rn1` field normalizes this to `0.0`. The Pydantic validator must handle all three forms: `"-"`, `null`/missing, and a numeric string.

### EC-004: KOROAD API returns XML despite `_type=json` request

Observed on some data.go.kr endpoints that ignore the format parameter. The adapter must detect `Content-Type: application/xml` in the response and fall back to `xml.etree.ElementTree` parsing. This fallback must be logged at `WARNING` level.

### EC-005: KMA warning zone codes contain date-versioned entries

Several `areaCode` values in the warning zone list were deprecated on 2021-07-15 and replaced with new codes. The `WeatherWarning.area_code` field must accept any string value (no enum restriction); the `getPwnStatus` API will only return currently valid codes, but the fixture may contain legacy codes from before the cutover date.

### EC-006: Road risk score with partial data

If `koroad_accident_search` succeeds but `kma_current_observation` fails (or vice versa), `road_risk_score` returns a partial result with `data_gaps` populated. The `risk_level` is computed from available data only. The `summary` string must explicitly note the data gap in Korean (e.g., "기상 데이터를 가져올 수 없어 사고 통계만 반영되었습니다.").

### EC-007: Grid coordinates outside South Korea coverage

`getUltraSrtNcst` only covers South Korea. Grid points outside [1, 149] × [1, 253] return an API error. The input schema must validate `nx` in range [1, 149] and `ny` in range [1, 253]. The `grid_coords.py` utility must return `None` for locations outside Korea and the caller must handle this gracefully.

---

## Out of Scope

The following items are explicitly deferred to future epics:

- **KMA short-term forecast (getVilageFcst)**: 72-hour trip planning; deferred to Phase 2 Epic for full route planning
- **KMA ultra-short-term forecast (getUltraSrtFcst)**: 6-hour forecast; deferred to Phase 2
- **KMA pre-warning (getWthrPwn/getWthrPwnList)**: Predictive alerts; deferred to Phase 2 Scenario 5 (Disaster Response)
- **KOROAD WMS tile endpoint**: Image tiles are not machine-readable; excluded permanently
- **KOROAD non-municipality categories**: Child zone accidents, icy road accidents, bicycle accidents — all use the same `getRestFrequentzoneLg` endpoint but different `searchYearCd` codes. The adapter architecture supports them via code tables, but fixtures and tests are only required for the `general` (municipality) category in this epic.
- **Road risk for highway segments**: Phase 1 scores by municipality (KOROAD's granularity). Segment-level scoring requires a separate road geometry API not yet procured.
- **Geocoding integration**: Converting a citizen's free-text address to (sido, gugun) or (nx, ny) is an independent concern handled by a future geocoding adapter. This epic assumes callers pass valid code values.
- **Permission pipeline integration**: `road_risk_score` is public-access (no PII). Full Layer 3 integration is covered by Epic #8.
- **docs/tools/ documentation**: Tool documentation pages under `docs/tools/koroad.md` and `docs/tools/kma.md` are deferred to a documentation epic.

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| Epic #6 Tool System (`GovAPITool`, `ToolRegistry`, `ToolExecutor`) | Merged (#82) | All adapter fields and registration patterns are defined; this epic adds the first concrete adapter instances |
| `httpx >= 0.27` | Available (`pyproject.toml`) | Async HTTP client for live API calls |
| `pydantic >= 2.0` | Available (`pyproject.toml`) | Input/output schema validation |
| `KOSMOS_KOROAD_API_KEY` env var | Not in repo | Developer must export before recording fixtures; never committed |
| `KOSMOS_DATA_GO_KR_KEY` env var | Not in repo | Developer must export before recording fixtures; never committed |
| KMA grid coordinate Excel attachment | `research/data/kma/` | Used to populate `grid_coords.py`; coordinates for Phase 1 cities hardcoded |
| KOROAD AccidentHazard CodeList | `research/data/_converted/koroad_AccidentHazard_CodeList.md` | Source of truth for all enum values in `code_tables.py` |

---

## Appendix A: Wire Format Examples

### KOROAD getRestFrequentzoneLg — Request

```
GET http://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg
  ?ServiceKey=<URL-encoded-key>
  &searchYearCd=2025119
  &siDo=11
  &guGun=680
  &numOfRows=10
  &pageNo=1
  &_type=json
```

### KOROAD getRestFrequentzoneLg — Response (JSON)

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_CODE"
    },
    "body": {
      "items": {
        "item": [
          {
            "afos_fid": "6467425",
            "afos_id": "2025119",
            "bjd_cd": "11680101",
            "caslt_cnt": 32,
            "dth_dnv_cnt": 0,
            "geom_json": "{\"type\":\"Polygon\",\"coordinates\":[...]}",
            "la_crd": 37.551096761607,
            "lo_crd": 127.034011018795,
            "occrrnc_cnt": 23,
            "se_dnv_cnt": 4,
            "sido_sgg_nm": "서울특별시 성동구",
            "sl_dnv_cnt": 29,
            "spot_cd": "11200001",
            "spot_nm": "서울특별시 성동구 홍익동 일원",
            "wnd_dnv_cnt": 1
          }
        ]
      },
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 3
    }
  }
}
```

### KMA getPwnStatus — Request

```
GET http://apis.data.go.kr/1360000/WthrWrnInfoService/getPwnStatus
  ?serviceKey=<URL-encoded-key>
  &numOfRows=2000
  &pageNo=1
  &dataType=JSON
```

### KMA getPwnStatus — Response (JSON, partial)

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "dataType": "JSON",
      "items": {
        "item": [
          {
            "stnId": "108",
            "tmFc": "201706070730",
            "tmEf": "201706070900",
            "tmSeq": 6,
            "areaCode": "S1322200",
            "areaName": "남해서부동쪽먼바다",
            "warnVar": 6,
            "warnStress": 1,
            "cancel": 0,
            "command": 2,
            "warFc": 1
          }
        ]
      },
      "numOfRows": 2000,
      "pageNo": 1,
      "totalCount": 1
    }
  }
}
```

### KMA getUltraSrtNcst — Request

```
GET http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst
  ?serviceKey=<URL-encoded-key>
  &numOfRows=10
  &pageNo=1
  &base_date=20210628
  &base_time=0600
  &nx=55
  &ny=127
  &dataType=JSON
```

### KMA getUltraSrtNcst — Response (JSON)

```json
{
  "response": {
    "header": {
      "resultCode": "00",
      "resultMsg": "NORMAL_SERVICE"
    },
    "body": {
      "dataType": "JSON",
      "items": {
        "item": [
          {"baseDate": "20210628", "baseTime": "0600", "category": "RN1", "nx": 55, "ny": 127, "obsrValue": "0"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "T1H", "nx": 55, "ny": 127, "obsrValue": "23.4"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "WSD", "nx": 55, "ny": 127, "obsrValue": "2.1"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "REH", "nx": 55, "ny": 127, "obsrValue": "65"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "PTY", "nx": 55, "ny": 127, "obsrValue": "0"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "UUU", "nx": 55, "ny": 127, "obsrValue": "-1.3"},
          {"baseDate": "20210628", "baseTime": "0600", "category": "VVV", "nx": 55, "ny": 127, "obsrValue": "1.8"}
        ]
      },
      "numOfRows": 10,
      "pageNo": 1,
      "totalCount": 8
    }
  }
}
```

Note: The response returns one item per category (pivot-long format). The adapter must pivot the items into a single flat `KmaCurrentObservationOutput` record.
