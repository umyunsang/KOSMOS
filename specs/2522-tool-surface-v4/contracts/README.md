# Phase 1 Contracts: Tool surface v4

**Date**: 2026-05-03
**Note**: 13 도구 + `resolve_location` 의 input/output schema 는 기존 `src/kosax/tools/<domain>/<tool>.py` 의 pydantic v2 BaseModel 정의 그대로 — v4 는 input schema 변경 X (사용자 디렉티브 "도메인 독립"). v4 의 schema-level 변경은 `resolve_location.output_schema` 4종 필드 표준화 1건만.

## 13 도구 input/output schema 인용

| 도구 | input schema | output schema | docs/api 인용 |
|---|---|---|---|
| `kma_current_observation` | `KmaCurrentObservationInput` (`src/kosax/tools/kma/kma_current_observation.py:38-77`) | `KmaCurrentObservationOutput` (`...:80-135`) | [`docs/api/kma/current_observation.md`](../../../docs/api/kma/current_observation.md) |
| `kma_short_term_forecast` | `KmaShortTermForecastInput` | `LookupTimeseries` | [`docs/api/kma/short_term_forecast.md`](../../../docs/api/kma/short_term_forecast.md) |
| `kma_ultra_short_term_forecast` | `KmaUltraShortTermForecastInput` | `LookupTimeseries` | [`docs/api/kma/ultra_short_term_forecast.md`](../../../docs/api/kma/ultra_short_term_forecast.md) |
| `kma_forecast_fetch` | `KmaForecastFetchInput` (lat/lon) | `LookupTimeseries` | [`docs/api/kma/forecast_fetch.md`](../../../docs/api/kma/forecast_fetch.md) |
| `kma_pre_warning` | `KmaPreWarningInput` | `LookupCollection` | [`docs/api/kma/pre_warning.md`](../../../docs/api/kma/pre_warning.md) |
| `kma_weather_alert_status` | `KmaWeatherAlertStatusInput` (v4: stn_id/tmFc 필수 추가) | `LookupCollection` | [`docs/api/kma/weather_alert_status.md`](../../../docs/api/kma/weather_alert_status.md) |
| `hira_hospital_search` | `HiraHospitalSearchInput` | `LookupCollection` | [`docs/api/hira/hospital_search.md`](../../../docs/api/hira/hospital_search.md) |
| `nmc_emergency_search` | `NmcEmergencySearchInput` | `LookupCollection` | [`docs/api/nmc/emergency_search.md`](../../../docs/api/nmc/emergency_search.md) |
| `nfa_emergency_info_service` | `NfaEmergencyInfoInput` (v4: stub → 진짜 구현, wire param 명세 P4 에서 확정) | `NfaEmergencyInfoOutput` | [`docs/api/nfa119/emergency_info_service.md`](../../../docs/api/nfa119/emergency_info_service.md) |
| `koroad_accident_search` | `KoroadAccidentSearchInput` (v4: siDo `IntEnum` 2-digit, guGun `IntEnum` 3-digit description 정정) | `KoroadAccidentSearchOutput` | [`docs/api/koroad/accident_search.md`](../../../docs/api/koroad/accident_search.md) |
| `koroad_accident_hazard_search` | `KoroadAccidentHazardSearchInput` | `LookupCollection` (v4: `geom_json` strip) | [`docs/api/koroad/accident_hazard_search.md`](../../../docs/api/koroad/accident_hazard_search.md) |
| `mohw_welfare_eligibility_search` | `MohwWelfareEligibilitySearchInput` (v4: stub → 진짜 구현, camelCase serialize) | `MohwWelfareEligibilitySearchOutput` | [`docs/api/mohw/welfare_eligibility_search.md`](../../../docs/api/mohw/welfare_eligibility_search.md) |
| `resolve_location` | `ResolveLocationInput` (`src/kosax/tools/models.py:536-558`) | **`ResolveLocationOutput` v4 표준** (`lat, lon, b_code, address_name`) | [`docs/api/resolve_location/index.md`](../../../docs/api/resolve_location/index.md) |

## v4 schema-level 변경

### `ResolveLocationOutput` 4종 필드 표준 (FR-016)

```python
class ResolveLocationOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    b_code: str = Field(pattern=r"^[0-9]{10}$")
    address_name: str = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]
    source: Literal["kakao", "juso", "sgis"]
```

### `kma_weather_alert_status` 의 stn_id/tmFc 필수화 (FR-009)

```python
class KmaWeatherAlertStatusInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # v4: 둘 중 하나 필수 (현재는 둘 다 optional)
    stn_id: str | None = Field(
        default=None,
        description=(
            "KMA 지점번호 (108=서울, 159=부산, ...). "
            "tmFc 와 둘 중 하나 필수. "
            "kma_pre_warning 응답의 stn_id 그대로 사용 권장."
        ),
    )
    tmFc: str | None = Field(
        default=None,
        description=(
            "특보 발표시각 YYYYMMDDHHMI. "
            "stn_id 와 둘 중 하나 필수. "
            "kma_pre_warning 응답의 tm_fc 그대로 사용 권장."
        ),
    )

    @model_validator(mode="after")
    def _require_at_least_one(self) -> Self:
        if not self.stn_id and not self.tmFc:
            raise ValueError("stn_id 또는 tmFc 둘 중 하나 필수")
        return self
```

### NFA / MOHW stub schema (P4/P5 에서 확정)

P4 (NFA) / P5 (MOHW) 는 진짜 구현 시 wire param 명세 확정 후 input/output schema final. 현재는 placeholder.

## Schema generation

`scripts/build_schemas.py` (Spec 1637) 가 모든 13 도구 + `resolve_location` 의 JSON Schema Draft 2020-12 export 를 `docs/api/schemas/<tool_id>.json` 로 deterministic 생성. v4 implementation 후 `python scripts/build_schemas.py --check` PASS 보장.
