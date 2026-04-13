# Data Model: Phase 1 API Adapters (KOROAD, KMA, Road Risk)

**Epic**: #7
**Spec**: `specs/007-api-adapters/spec.md`
**Created**: 2026-04-13

All models are Pydantic v2 `BaseModel`. No `Any` types. Per constitution § III.

---

## KOROAD Adapter Models

### `KoroadAccidentSearchInput`

Location: `src/kosmos/tools/koroad/koroad_accident_search.py`

| Field | Python Type | Required | Default | Validation |
|---|---|---|---|---|
| `search_year_cd` | `SearchYearCd` | Yes | — | Must be a valid `SearchYearCd` enum member |
| `si_do` | `SidoCode` | Yes | — | Must be a valid `SidoCode` enum member |
| `gu_gun` | `GugunCode \| None` | No | `None` | Optional district code |
| `num_of_rows` | `int` | No | `10` | `ge=1, le=100` |
| `page_no` | `int` | No | `1` | `ge=1` |

**Cross-validator** (`@model_validator(mode="after")`):
- If `si_do` is `SidoCode.GANGWON_LEGACY` (42) and `search_year_cd` encodes a year >= 2023: raise `ValidationError` with message `"sido=42 (강원도) is only valid for pre-2023 datasets. Use sido=51 (강원특별자치도) for 2023+ data."`
- If `si_do` is `SidoCode.JEONBUK_LEGACY` (45) and `search_year_cd` encodes a year >= 2023: raise `ValidationError` with message `"sido=45 (전라북도) is only valid for pre-2023 datasets. Use sido=52 (전북특별자치도) for 2023+ data."`

Wire parameter name mapping (field → query param):
- `search_year_cd` → `searchYearCd`
- `si_do` → `siDo`
- `gu_gun` → `guGun`
- `num_of_rows` → `numOfRows`
- `page_no` → `pageNo`

---

### `AccidentHotspot`

Location: `src/kosmos/tools/koroad/koroad_accident_search.py`

| Field | Python Type | Required | Wire Field | Notes |
|---|---|---|---|---|
| `spot_cd` | `str` | Yes | `spot_cd` | Unique spot code |
| `spot_nm` | `str` | Yes | `spot_nm` | Location name |
| `sido_sgg_nm` | `str` | Yes | `sido_sgg_nm` | Province + district name |
| `bjd_cd` | `str` | Yes | `bjd_cd` | Administrative district code |
| `occrrnc_cnt` | `int` | Yes | `occrrnc_cnt` | Accident occurrence count |
| `caslt_cnt` | `int` | Yes | `caslt_cnt` | Total casualty count |
| `dth_dnv_cnt` | `int` | Yes | `dth_dnv_cnt` | Death count |
| `se_dnv_cnt` | `int` | Yes | `se_dnv_cnt` | Serious injury count |
| `sl_dnv_cnt` | `int` | Yes | `sl_dnv_cnt` | Minor injury count |
| `wnd_dnv_cnt` | `int` | Yes | `wnd_dnv_cnt` | Injury count |
| `la_crd` | `float` | Yes | `la_crd` | Latitude |
| `lo_crd` | `float` | Yes | `lo_crd` | Longitude |
| `geom_json` | `str \| None` | No | `geom_json` | GeoJSON polygon string; may be absent |
| `afos_id` | `str` | Yes | `afos_id` | Year-dataset identifier |
| `afos_fid` | `str` | Yes | `afos_fid` | Feature ID within dataset |

---

### `KoroadAccidentSearchOutput`

Location: `src/kosmos/tools/koroad/koroad_accident_search.py`

| Field | Python Type | Notes |
|---|---|---|
| `total_count` | `int` | `totalCount` from `response.body` |
| `page_no` | `int` | `pageNo` from `response.body` |
| `num_of_rows` | `int` | `numOfRows` from `response.body` |
| `hotspots` | `list[AccidentHotspot]` | Empty list when no results; never null |

---

## KMA WeatherAlert Adapter Models

### `KmaWeatherAlertStatusInput`

Location: `src/kosmos/tools/kma/kma_weather_alert_status.py`

| Field | Python Type | Required | Default | Notes |
|---|---|---|---|---|
| `num_of_rows` | `int` | No | `2000` | `ge=1`; 2000 returns all active alerts in one page |
| `page_no` | `int` | No | `1` | `ge=1` |
| `data_type` | `Literal["JSON", "XML"]` | No | `"JSON"` | Always send `"JSON"` |

Wire parameter name mapping:
- `num_of_rows` → `numOfRows`
- `page_no` → `pageNo`
- `data_type` → `dataType`

---

### `WeatherWarning`

Location: `src/kosmos/tools/kma/kma_weather_alert_status.py`

| Field | Python Type | Wire Field | Notes |
|---|---|---|---|
| `stn_id` | `str` | `stnId` | Station/region ID |
| `tm_fc` | `str` | `tmFc` | Announcement time `YYYYMMDDHHMI` |
| `tm_ef` | `str` | `tmEf` | Effective time `YYYYMMDDHHMI` |
| `tm_seq` | `int` | `tmSeq` | Sequence number |
| `area_code` | `str` | `areaCode` | Warning zone code (e.g., `"S1151300"`) |
| `area_name` | `str` | `areaName` | Korean warning zone name |
| `warn_var` | `int` | `warnVar` | Warning type: 1=강풍, 2=호우, 3=한파, 4=건조, 5=해일, 6=태풍, 7=대설, 8=황사, 11=폭염 |
| `warn_stress` | `int` | `warnStress` | Severity: 0=주의보, 1=경보 |
| `cancel` | `int` | `cancel` | 0=active, 1=cancelled |
| `command` | `int` | `command` | Command code |
| `warn_fc` | `int` | `warFc` | Warning forecast flag |

---

### `KmaWeatherAlertStatusOutput`

Location: `src/kosmos/tools/kma/kma_weather_alert_status.py`

| Field | Python Type | Notes |
|---|---|---|
| `total_count` | `int` | Count of active (non-cancelled) warnings returned |
| `warnings` | `list[WeatherWarning]` | Active warnings only (`cancel=0`); empty list when no active warnings |

---

## KMA Current Observation Adapter Models

### `KmaCurrentObservationInput`

Location: `src/kosmos/tools/kma/kma_current_observation.py`

| Field | Python Type | Required | Default | Validation |
|---|---|---|---|---|
| `base_date` | `str` | Yes | — | Pattern `YYYYMMDD`; validated with `@field_validator` |
| `base_time` | `str` | Yes | — | Pattern `HHMM` (exact hour, minutes always `"00"`); normalized by validator |
| `nx` | `int` | Yes | — | `ge=1, le=149`; KMA grid X |
| `ny` | `int` | Yes | — | `ge=1, le=253`; KMA grid Y |
| `num_of_rows` | `int` | No | `10` | `ge=1` |
| `page_no` | `int` | No | `1` | `ge=1` |
| `data_type` | `Literal["JSON", "XML"]` | No | `"JSON"` | Always send `"JSON"` |

**`base_time` validator**: strips the minutes component and rounds down to the nearest hour. Input `"0610"` → stored as `"0600"`. This prevents the "data not ready in first 10 min" error at the input layer.

Wire parameter name mapping:
- `base_date` → `base_date`
- `base_time` → `base_time`
- `nx` → `nx`
- `ny` → `ny`
- `num_of_rows` → `numOfRows`
- `page_no` → `pageNo`
- `data_type` → `dataType`

---

### `KmaCurrentObservationOutput`

Location: `src/kosmos/tools/kma/kma_current_observation.py`

The wire format returns a list of `{baseDate, baseTime, nx, ny, category, obsrValue}` rows. The adapter pivots these rows into this flat model.

| Field | Python Type | KMA Category | Notes |
|---|---|---|---|
| `base_date` | `str` | `baseDate` | Observation date `YYYYMMDD` |
| `base_time` | `str` | `baseTime` | Observation time `HHMM` |
| `nx` | `int` | `nx` | Grid X |
| `ny` | `int` | `ny` | Grid Y |
| `t1h` | `float \| None` | `T1H` | Temperature °C |
| `rn1` | `float` | `RN1` | 1-hour precipitation mm; `@field_validator` normalizes `"-"`, `None`, `""` to `0.0` |
| `uuu` | `float \| None` | `UUU` | East-west wind component m/s (east=positive) |
| `vvv` | `float \| None` | `VVV` | North-south wind component m/s (north=positive) |
| `wsd` | `float \| None` | `WSD` | Wind speed m/s |
| `reh` | `float \| None` | `REH` | Relative humidity % |
| `pty` | `int` | `PTY` | Precipitation type: 0=none, 1=rain, 2=rain+snow, 3=snow, 5=drizzle, 6=drizzle+snow, 7=snow flurry |
| `vec` | `float \| None` | `VEC` | Wind direction (degrees 0–360) |

**`rn1` field validator** (handles three null forms):
```python
@field_validator("rn1", mode="before")
@classmethod
def normalize_rn1(cls, v: object) -> float:
    if v is None or v == "" or v == "-":
        return 0.0
    return float(v)
```

---

## Road Risk Composite Model

### `RoadRiskScoreInput`

Location: `src/kosmos/tools/composite/road_risk_score.py`

| Field | Python Type | Required | Default | Notes |
|---|---|---|---|---|
| `sido` | `SidoCode` | Yes | — | Province/city code |
| `gugun` | `GugunCode \| None` | No | `None` | Optional district code |
| `search_year_cd` | `SearchYearCd \| None` | No | `None` | Defaults to most recent `general` year code |
| `nx` | `int` | Yes | — | `ge=1, le=149`; KMA grid X for weather lookup |
| `ny` | `int` | Yes | — | `ge=1, le=253`; KMA grid Y for weather lookup |
| `hazard_type` | `Literal["general","ice","pedestrian","child_zone"]` | No | `"general"` | Maps to accident dataset category |

**Default `search_year_cd` logic**: if `None`, the adapter selects `SearchYearCd.GENERAL_2024` (value `"2025119"`). This is the most recent annual municipality dataset per the code table.

---

### `RoadRiskScoreOutput`

Location: `src/kosmos/tools/composite/road_risk_score.py`

| Field | Python Type | Notes |
|---|---|---|
| `risk_score` | `float` | Composite score `[0.0, 1.0]`; `ge=0.0, le=1.0` |
| `risk_level` | `Literal["low","moderate","high","severe"]` | `[0,0.3)=low`; `[0.3,0.6)=moderate`; `[0.6,0.8)=high`; `[0.8,1.0]=severe` |
| `accident_hotspot_count` | `int` | Hotspot zones found; `0` if KOROAD data unavailable |
| `active_weather_warnings` | `int` | Active KMA warnings; `0` if KMA alert data unavailable |
| `precipitation_mm` | `float` | Current 1-hour precipitation; `0.0` if KMA obs data unavailable |
| `precipitation_type` | `int` | KMA `pty` code; `0` (none) if KMA obs data unavailable |
| `summary` | `str` | Korean-language sentence summarizing the risk assessment |
| `data_sources` | `list[str]` | Which inner adapters contributed: subset of `["koroad","kma_alert","kma_obs"]` |
| `data_gaps` | `list[str]` | Which inner adapters failed: subset of `["koroad","kma_alert","kma_obs"]` |

---

## Enum Definitions

### `SidoCode`

Location: `src/kosmos/tools/koroad/code_tables.py`

```
11 = Seoul (서울특별시)
26 = Busan (부산광역시)
27 = Daegu (대구광역시)
28 = Incheon (인천광역시)
29 = Gwangju (광주광역시)
30 = Daejeon (대전광역시)
31 = Ulsan (울산광역시)
36 = Sejong (세종특별자치시)
41 = Gyeonggi (경기도)
42 = Gangwon_Legacy (강원도 — pre-2023 datasets only)
43 = Chungbuk (충청북도)
44 = Chungnam (충청남도)
45 = Jeonbuk_Legacy (전라북도 — pre-2023 datasets only)
46 = Jeonnam (전라남도)
47 = Gyeongbuk (경상북도)
48 = Gyeongnam (경상남도)
50 = Jeju (제주특별자치도)
51 = Gangwon (강원특별자치도 — 2023+ datasets)
52 = Jeonbuk (전북특별자치도 — 2023+ datasets)
```

Source: `research/data/_converted/koroad_AccidentHazard_CodeList.md § Sheet: Sido 요청값`

---

### `SearchYearCd` (representative subset; full list in code_tables.py)

Location: `src/kosmos/tools/koroad/code_tables.py`

Category: 지자체별 (General municipality)
```
GENERAL_2024 = "2025119"   (24년 지자체별)
GENERAL_2023 = "2024056"   (23년 지자체별)
GENERAL_2022 = "2023026"   (22년 지자체별)
GENERAL_2021 = "2022046"   (21년 지자체별)
```

Category: 결빙 (Ice)
```
ICE_2024 = "2025113"       (20-24년 결빙)
ICE_2023 = "2024055"       (19-23년 결빙)
```

Category: 어린이보호구역내 어린이 (Child zone)
```
CHILD_ZONE_2024 = "2025066"
CHILD_ZONE_2023 = "2024041"
```

Category: 보행어린이 (Pedestrian child)
```
PEDESTRIAN_CHILD_2024 = "2025108"
PEDESTRIAN_CHILD_2023 = "2024042"
```

Category: 보행노인 (Pedestrian elderly)
```
PEDESTRIAN_ELDERLY_2024 = "2025076"
PEDESTRIAN_ELDERLY_2023 = "2024044"
```

Category: 자전거 (Bicycle)
```
BICYCLE_2024 = "2025081"
BICYCLE_2023 = "2024046"
```

Category: 법규위반별 (Law violation)
```
LAW_SIGNAL_2024 = "2025111"   (신호위반)
LAW_CENTER_2024 = "2025110"   (중앙선침범)
```

Category: 연휴기간별 (Holiday)
```
HOLIDAY_2024 = "2025112"   (22-24년 연휴기간별)
```

Category: 이륜차 (Motorcycle)
```
MOTORCYCLE_2024 = "2025091"   (22-24년 이륜차)
```

Category: 보행자 (Pedestrian general)
```
PEDESTRIAN_2024 = "2025083"   (22-24년 보행자)
```

Category: 음주운전 (Drunk driving)
```
DRUNK_DRIVING_2024 = "2025085"   (22-24년 음주운전)
```

Category: 화물차 (Freight)
```
FREIGHT_2024 = "2025089"   (22-24년 화물차)
```

Source: `research/data/_converted/koroad_AccidentHazard_CodeList.md § Sheet: serachYearCd 요청값`

---

### `HazardType`

Location: `src/kosmos/tools/koroad/code_tables.py`

Maps the `hazard_type` field in `RoadRiskScoreInput` to a default `SearchYearCd`.

```
general          → SearchYearCd.GENERAL_2024
ice              → SearchYearCd.ICE_2024
pedestrian_child → SearchYearCd.PEDESTRIAN_CHILD_2024
child_zone       → SearchYearCd.CHILD_ZONE_2024
pedestrian_elderly → SearchYearCd.PEDESTRIAN_ELDERLY_2024
bicycle          → SearchYearCd.BICYCLE_2024
law_violation    → SearchYearCd.LAW_SIGNAL_2024   (signal violation as default)
holiday          → SearchYearCd.HOLIDAY_2024
motorcycle       → SearchYearCd.MOTORCYCLE_2024
pedestrian       → SearchYearCd.PEDESTRIAN_2024
drunk_driving    → SearchYearCd.DRUNK_DRIVING_2024
freight          → SearchYearCd.FREIGHT_2024
```

---

### `GugunCode`

Location: `src/kosmos/tools/koroad/code_tables.py`

The `GugunCode` enum uses integer values matching the API code table. Because district code integers overlap across sido (multiple sido use code `110` for their respective Jung-gu), the enum member names are qualified:

```
SEOUL_JONGNO     = 110    # 서울 종로구
SEOUL_JUNGGU     = 140    # 서울 중구
SEOUL_YONGSAN    = 170    # 서울 용산구
SEOUL_SEONGDONG  = 200    # 서울 성동구
SEOUL_GWANGJIN   = 215    # 서울 광진구
SEOUL_DONGDAEMUN = 230    # 서울 동대문구
SEOUL_JUNGRANG   = 260    # 서울 중랑구
SEOUL_SEONGBUK   = 290    # 서울 성북구
SEOUL_GANGBUK    = 305    # 서울 강북구
SEOUL_DOBONG     = 320    # 서울 도봉구
SEOUL_NOWON      = 350    # 서울 노원구
SEOUL_EUNPYEONG  = 380    # 서울 은평구
SEOUL_SEODAEMUN  = 410    # 서울 서대문구
SEOUL_MAPO       = 440    # 서울 마포구
SEOUL_YANGCHEON  = 470    # 서울 양천구
SEOUL_GANGSEO    = 500    # 서울 강서구
SEOUL_GURO       = 530    # 서울 구로구
SEOUL_GEUMCHEON  = 545    # 서울 금천구
SEOUL_YEONGDEUNGPO = 560  # 서울 영등포구
SEOUL_DONGJAK    = 590    # 서울 동작구
SEOUL_GWANAK     = 620    # 서울 관악구
SEOUL_SEOCHO     = 650    # 서울 서초구
SEOUL_GANGNAM    = 680    # 서울 강남구
SEOUL_SONGPA     = 710    # 서울 송파구
SEOUL_GANGDONG   = 740    # 서울 강동구
# ... full list for all sido in code_tables.py
```

Source: `research/data/_converted/koroad_AccidentHazard_CodeList.md § Sheet: Gugun 요청값`

Note: Because district code integers overlap across sido (e.g., `110` is Jung-gu in both Seoul and Busan), the cross-validator in `KoroadAccidentSearchInput` must verify the `gu_gun` value is present in the legal set for the given `si_do`. The legal set is a dict defined in `code_tables.py`:

```python
SIDO_GUGUN_MAP: dict[SidoCode, frozenset[int]] = {
    SidoCode.SEOUL: frozenset({110, 140, 170, 200, 215, 230, 260, 290, 305,
                                320, 350, 380, 410, 440, 470, 500, 530, 545,
                                560, 590, 620, 650, 680, 710, 740}),
    # ... all sido
}
```

---

## Wire-to-Model Field Name Mapping Summary

### KOROAD `getRestFrequentzoneLg` Response Path

```
response.header.resultCode       → error check ("00" = success)
response.header.resultMsg        → error message on failure
response.body.totalCount         → KoroadAccidentSearchOutput.total_count
response.body.pageNo             → KoroadAccidentSearchOutput.page_no
response.body.numOfRows          → KoroadAccidentSearchOutput.num_of_rows
response.body.items.item[]       → KoroadAccidentSearchOutput.hotspots
  .spot_cd                       → AccidentHotspot.spot_cd
  .spot_nm                       → AccidentHotspot.spot_nm
  .sido_sgg_nm                   → AccidentHotspot.sido_sgg_nm
  .bjd_cd                        → AccidentHotspot.bjd_cd
  .occrrnc_cnt                   → AccidentHotspot.occrrnc_cnt
  .caslt_cnt                     → AccidentHotspot.caslt_cnt
  .dth_dnv_cnt                   → AccidentHotspot.dth_dnv_cnt
  .se_dnv_cnt                    → AccidentHotspot.se_dnv_cnt
  .sl_dnv_cnt                    → AccidentHotspot.sl_dnv_cnt
  .wnd_dnv_cnt                   → AccidentHotspot.wnd_dnv_cnt
  .la_crd                        → AccidentHotspot.la_crd
  .lo_crd                        → AccidentHotspot.lo_crd
  .geom_json                     → AccidentHotspot.geom_json (may be absent)
  .afos_id                       → AccidentHotspot.afos_id
  .afos_fid                      → AccidentHotspot.afos_fid
```

### KMA `getPwnStatus` Response Path

```
response.header.resultCode       → error check
response.body.totalCount         → KmaWeatherAlertStatusOutput.total_count
response.body.items.item[]       → KmaWeatherAlertStatusOutput.warnings
  .stnId                         → WeatherWarning.stn_id
  .tmFc                          → WeatherWarning.tm_fc
  .tmEf                          → WeatherWarning.tm_ef
  .tmSeq                         → WeatherWarning.tm_seq
  .areaCode                      → WeatherWarning.area_code
  .areaName                      → WeatherWarning.area_name
  .warnVar                       → WeatherWarning.warn_var
  .warnStress                    → WeatherWarning.warn_stress
  .cancel                        → WeatherWarning.cancel
  .command                       → WeatherWarning.command
  .warFc                         → WeatherWarning.warn_fc
```

### KMA `getUltraSrtNcst` Response Path (pivot from row format)

```
response.header.resultCode       → error check
response.body.items.item[]       → pivot: category → field
  item where .category == "T1H"  → KmaCurrentObservationOutput.t1h
  item where .category == "RN1"  → KmaCurrentObservationOutput.rn1 (normalized)
  item where .category == "UUU"  → KmaCurrentObservationOutput.uuu
  item where .category == "VVV"  → KmaCurrentObservationOutput.vvv
  item where .category == "WSD"  → KmaCurrentObservationOutput.wsd
  item where .category == "REH"  → KmaCurrentObservationOutput.reh
  item where .category == "PTY"  → KmaCurrentObservationOutput.pty
  item where .category == "VEC"  → KmaCurrentObservationOutput.vec
  item[0].baseDate               → KmaCurrentObservationOutput.base_date
  item[0].baseTime               → KmaCurrentObservationOutput.base_time
  item[0].nx                     → KmaCurrentObservationOutput.nx
  item[0].ny                     → KmaCurrentObservationOutput.ny
```
