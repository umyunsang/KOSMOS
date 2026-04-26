---
tool_id: nfa_emergency_info_service
primitive: lookup
tier: live
permission_tier: 1
---

# nfa_emergency_info_service

## Overview

Queries the NFA (소방청, National Fire Agency) emergency activity statistics service for historical, anonymized EMS records by region, fire station, and report year-month, covering dispatch activity, patient transport, patient condition, first-aid treatment, and vehicle information.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | National Fire Agency (NFA / 소방청) / data.go.kr |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/nfa119/emergency_info_service.py` |

## Envelope

**Input model**: `NfaEmergencyInfoServiceInput` defined at `src/kosmos/tools/nfa119/emergency_info_service.py:45–105`.

| Field | Type | Required | Description |
|---|---|---|---|
| `operation` | `NfaEmgOperation` (default `"getEmgencyActivityInfo"`) | no | Sub-endpoint selector. See operation table below. |
| `sido_hq_ogid_nm` | `str \| None` (max 22 chars) | no | Regional fire HQ name (시도본부). Example: `서울소방재난본부`. Omit to query all regions. |
| `rsac_gut_fstt_ogid_nm` | `str` (max 7 chars) | yes | Fire station name (출동소방서). Example: `공주소방서`. Must be a valid NFA station name — do not guess. |
| `stmt_ym` | `str` (pattern `^\d{6}$`) | yes | Report year-month in YYYYMM format. Example: `202101` for January 2021. Do not use future dates. |
| `page_no` | `int` (≥1, default 1) | no | Page number (1-indexed). |
| `num_of_rows` | `int` (1–100, default 10) | no | Records per page. Maximum 100 per NFA API contract. |
| `result_type` | `Literal["json"]` (fixed) | no | Fixed to `"json"`. Do not override. |

**`NfaEmgOperation` values**:

| Value | Wire sub-endpoint | Description |
|---|---|---|
| `activity` | `getEmgencyActivityInfo` | Dispatch distance, patient symptoms, crew qualifications (default) |
| `transfer` | `getEmgPatientTransferInfo` | Patient transport information |
| `condition` | `getEmgPatientConditionInfo` | Patient vital signs |
| `firstaid` | `getEmgPatientFirstaidInfo` | Emergency treatment codes |
| `vehicle_dispatch` | `getEmgVehicleDispatchInfo` | Vehicle dispatch information |
| `vehicle_info` | `getEmgVehicleInfo` | Vehicle fleet information |

**Output model**: `NfaEmergencyInfoServiceOutput` defined at `src/kosmos/tools/nfa119/emergency_info_service.py:243–260`.

| Field | Type | Required | Description |
|---|---|---|---|
| `operation` | `str` | yes | The queried operation path (e.g., `getEmgencyActivityInfo`). |
| `result_code` | `str` | yes | API `resultCode` (`"00"` = NORMAL SERVICE). |
| `result_msg` | `str` | yes | API `resultMsg`. |
| `page_no` | `int` | yes | Requested page number. |
| `num_of_rows` | `int` | yes | Rows per page. |
| `total_count` | `int` | yes | Total matching records. |
| `items` | `list[NfaItem]` | yes | Records matching the operation discriminator. Empty list when no records match. |

`NfaItem` is a union of six operation-specific models (lines 233–240): `NfaActivityItem`, `NfaTransferItem`, `NfaConditionItem`, `NfaFirstaidItem`, `NfaVehicleDispatchItem`, `NfaVehicleInfoItem`. All models use `extra="allow"` to tolerate undocumented wire fields.

## Search hints

- 한국어: `119 구급`, `출동`, `소방청`, `구급정보`, `구급활동`, `구급차`, `통계`, `현황`, `소방서`, `긴급구조`
- English: `119 NFA emergency`, `ambulance dispatch`, `EMS activity statistics`, `fire station`, `Korea emergency services`, `first aid records`

## Endpoint

- **data.go.kr endpoint**: `1661000/EmergencyInformationService`
- **Source URL**: https://apis.data.go.kr/1661000/EmergencyInformationService
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

> **Implementation status**: The HTTP handler is an interface-only stub pending Layer 3 auth gate provisioning (Epic #16/#20). The `handle()` function raises `Layer3GateViolation` as a defence-in-depth backstop, which should never be reached because the Layer 3 auth-gate in `executor.invoke()` short-circuits unauthenticated calls first. The `GovAPITool` registration, all six Pydantic output models, and the `NfaEmgOperation` enum are complete and ready for the live handler.

## Permission tier rationale

This adapter is classified as Permission tier 1 despite having `requires_auth=True` because the underlying data is historical and anonymized (`pipa_class="non_personal"`, `is_personal_data=False`, `auth_level="AAL1"`). No individual citizen's health or identity data is exposed — records contain aggregate dispatch statistics by region, station, and month. The `requires_auth=True` flag enforces service access control (preventing unauthenticated bulk scraping), not citizen privacy protection. Under Spec 033, tier 1 applies when the data class is non-personal, even when auth is required for access-control purposes. Unauthenticated calls receive `LookupError(reason="auth_required")` from the Layer 3 gate before `handle()` is reached.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "nfa_emergency_info_service",
  "params": {
    "operation": "getEmgencyActivityInfo",
    "rsac_gut_fstt_ogid_nm": "공주소방서",
    "stmt_ym": "202101",
    "page_no": 1,
    "num_of_rows": 5
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "nfa_emergency_info_service",
  "result": {
    "operation": "getEmgencyActivityInfo",
    "result_code": "00",
    "result_msg": "NORMAL SERVICE.",
    "page_no": 1,
    "num_of_rows": 5,
    "total_count": 42,
    "items": [
      {
        "sidoHqOgidNm": "충청남도소방본부",
        "rsacGutFsttOgidNm": "공주소방서",
        "gutYm": "202101",
        "gutHh": "14",
        "sptMvmnDtc": "1200",
        "ptntAge": "60~69세",
        "ptntSdtSeCdNm": "남",
        "ruptSptmCdNm": "호흡곤란",
        "emtpQlcClCd1Nm": "1급 응급구조사"
      }
    ]
  }
}
```

### Conversation snippet

```text
Citizen: 2021년 1월에 공주소방서에서 구급 출동이 얼마나 있었는지 알고 싶어요.
KOSMOS: 2021년 1월 공주소방서 구급활동 정보를 조회했습니다. 해당 기간 총 42건의 출동 기록이 있으며, 예시로 1건을 살펴보면 60~69세 남성 환자가 호흡곤란 증세로 현장과 1,200m 거리에서 이송되었고 1급 응급구조사가 대응했습니다. 더 자세한 내용이나 다른 기간의 통계도 조회해 드릴 수 있습니다.
```

## Constraints

- **Rate limit**: `rate_limit_per_minute=10`; data.go.kr daily quota applies per API key.
- **Freshness window**: `cache_ttl_seconds=86400` (24 hours). This is historical statistics data; upstream updates are monthly or quarterly.
- **Fixture coverage gaps**: Live handler is not yet implemented — the current stub raises `Layer3GateViolation`. CI tests must use recorded fixtures or mock the executor. All six output item models are authored and ready for live handler wiring.
- **Error envelope examples**:
  - Unauthenticated call (Layer 3 gate): `LookupError(reason="auth_required")` before `handle()` is reached.
  - Defence-in-depth (handle() reached without auth): `Layer3GateViolation` raised.
  - Future `stmt_ym`: Pydantic validation rejects the input at the `pattern=r"^\d{6}$"` level if malformed; the adapter does not validate against future dates at the model layer — the LLM description instructs the model not to use future dates.
