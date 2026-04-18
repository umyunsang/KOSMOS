# Feature Specification: Phase 2 API Adapters — `nfa_emergency_info_service` + `mohw_welfare_eligibility_search`

**Feature Branch**: `feat/15-phase2-adapters-119-mohw`
**Spec Directory**: `specs/029-phase2-adapters-119-mohw/`
**Created**: 2026-04-18
**Status**: Draft
**Input**: Epic #15 — Phase 2 API Adapters (119, MOHW)

---

## 1. User Scenarios and Testing

### User Story 1 — Citizen asks about emergency activity patterns by region (Priority: P1)

A citizen or researcher asks "충청남도 천안 구급 출동 현황 알려줘" or "지난달 서울 구급차 출동 정보". The
model calls `lookup(mode="search", query="구급 출동 소방청 통계")`, discovers `nfa_emergency_info_service`,
then calls `lookup(mode="fetch", tool_id="nfa_emergency_info_service", params={...})`. The response is a
`LookupCollection` of emergency activity records for the queried station and period.

This is also exercised as the fallback path when `nmc_emergency_search` returns
`LookupError(reason="auth_required")` in Scenario 2 (Epic #18): the model discovers the NFA emergency
info adapter and surfaces historical dispatch context for pre-hospital routing guidance.

> **Scope note**: `nfa_emergency_info_service` maps to the official API
> `소방청_구급정보서비스` (data.go.kr service ID 15099423, provider code `1661000`).
> It is a **statistical records service** — it returns historical anonymized EMS records
> (patient transport, condition, first aid, vehicle dispatch, vehicle info, activity) by
> region + fire station + report year-month. It is NOT a real-time geospatial facility
> locator. For nearest-station lookup, see §9 (`nfa_safety_center_lookup` — deferred).

**Acceptance scenarios**:
1. `lookup(mode="fetch", tool_id="nfa_emergency_info_service", params={sido_hq_ogid_nm, rsac_gut_fstt_ogid_nm, stmt_ym, operation})` against a recorded fixture returns a `LookupCollection` with `items` containing at minimum `sidoHqOgidNm`, `rsacGutFsttOgidNm`, `stmtYm`.
2. With `session_identity=None`, the executor returns `LookupError(reason="auth_required")` — the adapter is fail-closed per `requires_auth=True`.
3. `lookup(mode="search", query="119 구급 출동 소방 통계 현황")` returns `nfa_emergency_info_service` in the top-5 BM25 candidates.

### User Story 2 — Citizen asks about childbirth benefit eligibility (Priority: P1)

A citizen asks "출산 보조금 신청하고 싶어요" or "아이 낳으면 복지 혜택 뭐가 있어요?". The model calls
`lookup(mode="search", query="출산 복지 보조금")`, discovers `mohw_welfare_eligibility_search`, then
calls `lookup(mode="fetch", tool_id="mohw_welfare_eligibility_search", params={...})`. Because
`is_personal_data=True` and `requires_auth=True`, the executor returns `LookupError(reason="auth_required")`
for unauthenticated sessions — matching the same gate contract as `nmc_emergency_search`.

**Acceptance scenarios**:
1. Any `lookup(mode="fetch", tool_id="mohw_welfare_eligibility_search", ...)` with `session_identity=None`
   returns `LookupError(reason="auth_required")` and makes zero HTTP calls to the SSIS endpoint.
2. `lookup(mode="search", query="출산 보조금 복지 혜택")` returns `mohw_welfare_eligibility_search` in
   the top-5 BM25 candidates.
3. The `recall@5` eval set (Epic #507 criterion) does not regress after adding both new adapters.

### User Story 3 — Scenario 3 E2E childbirth benefits flow (Priority: P2)

Epic #19 (Scenario 3 E2E) uses `mohw_welfare_eligibility_search` as the primary data source. The
adapter's `LookupError(reason="auth_required")` return is the expected stub behavior until Layer 3
(Epic #16 / #20) is delivered. The E2E test for Epic #19 replay-asserts this specific error shape
so that the harness route is validated without a live upstream call.

### Edge Cases

- **XML fallback quirk**: `data.go.kr` returns XML when the `Accept` header is missing or the
  `serviceKey` is invalid. Both adapters MUST guard `Content-Type` and return
  `LookupError(reason="upstream_unavailable")` with `retryable=False` on XML response bodies
  when JSON was requested.
- **Single-item normalization**: `data.go.kr` XML/JSON endpoints sometimes wrap a single result
  item as a bare object rather than a list. Both adapters MUST normalize to `list[dict]` before
  constructing the `LookupCollection`.
- **Missing `serviceKey`**: If `KOSMOS_DATA_GO_KR_API_KEY` is not set, return
  `LookupError(reason="upstream_unavailable", retryable=False)` immediately — do not call the API.
- **Upstream 4xx / 5xx**: Wrap in `LookupError(reason="upstream_unavailable", retryable=True)`.
- **Empty result set**: Return `LookupCollection(items=[], total_count=0)` — not an error.
- **data.go.kr error envelope**: The API returns an `<OpenAPI_ServiceResponse>` XML envelope
  for auth errors (e.g., `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`, code 30;
  `LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR`, code 22). The adapter MUST detect this
  envelope and map code 22 to `LookupError(reason="rate_limited", retryable=True)` and all
  other codes to `LookupError(reason="upstream_unavailable", retryable=False)`.

---

## 2. Scope Boundaries and Deferred Items

### In Scope

- `nfa_emergency_info_service` — interface-only adapter (see §4.1)
- `mohw_welfare_eligibility_search` — interface-only adapter (see §4.2)
- Both adapters registered in `register_all.py`
- Fixture stubs under `tests/fixtures/<provider>/<tool_id>.json`
- Happy-path + error-path tests using recorded fixture stubs
- `docs/tools/nfa119.md` and `docs/tools/ssis.md` documentation entries
- TOOL_MIN_AAL additions for both tool IDs in `src/kosmos/security/audit.py`

### Out of Scope (Deferred)

| Item | Tracking issue |
|---|---|
| Live HTTP implementation of `nfa_emergency_info_service.handle()` | Deferred to Phase 2 implementation PR |
| Live HTTP implementation of `mohw_welfare_eligibility_search.handle()` | Blocked on Layer 3 auth gate (Epic #16 / #20) |
| Layer 3 auth gate that lifts `requires_auth` short-circuit | Epic #16, Epic #20 |
| Scenario 2 full E2E (119 fallback path) | Epic #18 |
| Scenario 3 full E2E (childbirth benefits flow) | Epic #19 |
| Gov24 application submission after eligibility lookup | Epic #22 |
| Recall@5 eval set expansion for Phase 2 adapters | Epic #507 follow-on |
| `nfa_safety_center_lookup` (local CSV-backed nearest-station tool) | #934 (deferred placeholder) — See §9 |

---

## 3. SSIS vs MOHW Endpoint Decision

The Epic body raises the question: should `mohw_welfare_eligibility_search` use MOHW's own
endpoint or the SSIS (한국사회보장정보원) endpoint?

**Decision: use the SSIS endpoint** — specifically
`https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001`.

**Justification**:

1. `research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc` is the only welfare API technical
   document available in this repository. The SSIS document describes the `NationalWelfarelistV001`
   endpoint that aggregates both 중앙부처 and 지자체 welfare services — it is the canonical
   cross-ministry welfare service catalog that MOHW feeds into. MOHW does not expose a separate
   `data.go.kr` welfare-service-list API distinct from SSIS.
2. The SSIS endpoint supports filter parameters (`lifeArray`, `trgterIndvdlArray`, `intrsThemaArray`,
   `age`, `searchWrd`) that are directly useful for eligibility-style queries ("임산부 대상 복지
   서비스" / "출산 지원 혜택") without requiring citizen PII in the request.
3. Shipping both the SSIS list endpoint and a hypothetical MOHW-only endpoint would duplicate
   adapter registration against the same upstream data with no differential citizen value.

The SSIS detail endpoint (`NationalWelfaredetailedV001`) is deferred — it is a single-item
fetch-by-`servId` that is useful only after the citizen selects a specific service from the list.
It will be added in a follow-on spec.

---

## 4. Adapter Specifications

### 4.1 `nfa_emergency_info_service`

#### Summary

| Field | Value |
|---|---|
| `tool_id` | `nfa_emergency_info_service` |
| `name_ko` | `소방청 구급정보서비스 (구급활동 통계 조회)` |
| `provider` | `소방청 (National Fire Agency, NFA)` |
| `category` | `["안전", "응급", "소방", "119", "구급통계"]` |
| `auth_type` | `api_key` |
| `auth_level` | `AAL1` |
| `pipa_class` | `non_personal` |
| `is_irreversible` | `False` |
| `dpa_reference` | `None` (non_personal — V2 does not require dpa_reference) |
| `requires_auth` | `True` |
| `is_personal_data` | `False` |
| `is_concurrency_safe` | `True` |
| `cache_ttl_seconds` | `86400` |
| `rate_limit_per_minute` | `10` |
| `is_core` | `False` |

**V1–V6 compliance check**:
- V1: `pipa_class="non_personal"` → no `auth_level` restriction from PII. Compliant.
- V2: `pipa_class="non_personal"` → `dpa_reference` not required; set `None`. Compliant.
- V3: `nfa_emergency_info_service` is NOT in `TOOL_MIN_AAL` at construction — V3 does not fire.
  `auth_level="AAL1"` is chosen because the adapter requires `api_key` auth (serviceKey).
  Per V6 mapping `api_key → {AAL1, AAL2, AAL3}`, `AAL1` is compliant.
- V4: `is_irreversible=False` → no constraint. Compliant.
- V5: `auth_level="AAL1"` → `requires_auth=True` (V5 requires this). Compliant.
- V6: `auth_type="api_key"`, `auth_level="AAL1"` → in allowed set `{AAL1, AAL2, AAL3}`. Compliant.
- FR-038: `is_personal_data=False` → no `requires_auth` pairing constraint from FR-038.

Note: `requires_auth=True` with `is_personal_data=False` is valid — the adapter uses a
`serviceKey` (API key authentication) even though it returns only anonymized statistical data.
This matches the V5 requirement that `auth_level != "public"` must pair with `requires_auth=True`.

**TOOL_MIN_AAL addition required**: add `"nfa_emergency_info_service": "AAL1"` so V3 is
enforced consistently once the implementation lands.

#### Endpoint

```
GET https://apis.data.go.kr/1661000/EmergencyInformationService/{operation}
```

**Confirmed source**: `research/data/nfa119/공공데이터 오픈API 활용가이드(소방청_구급정보).docx`,
TABLE 0 (서비스 URL), data.go.kr catalog ID 15099423.

**Authentication**: `serviceKey` query parameter (URL-encoded). Provider code `1661000`.
Response format: XML or JSON (`resultType` param). Adapter requests JSON.

**Available operations** (TABLE 1 in docx):

| # | operation path | 국문명 |
|---|---|---|
| 1 | `getEmgPatientTransferInfo` | 구급환자이송정보 목록조회 |
| 2 | `getEmgPatientConditionInfo` | 구급환자상태정보 목록조회 |
| 3 | `getEmgPatientFirstaidInfo` | 구급환자응급처치정보 목록조회 |
| 4 | `getEmgVehicleDispatchInfo` | 구급차량출동정보 목록조회 |
| 5 | `getEmgVehicleInfo` | 구급차량정보 목록조회 |
| 6 | `getEmgencyActivityInfo` | 구급활동정보 목록조회 |

MVP scope uses `getEmgencyActivityInfo` as the primary operation (most citizen-relevant:
includes dispatch location type, patient symptoms, crew qualifications, incident-site distance).
Other operations are exposed via the `operation` field for forward compatibility.

**Rate limit**: 30 TPS per operation, daily traffic cap managed by data.go.kr (1,000 calls/day
for development accounts). `cache_ttl_seconds=86400` (1 day) matches the `데이터 갱신주기: 일 1회`
stated in the docx.

#### Input schema

```python
import enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class NfaEmgOperation(str, enum.Enum):
    """Selects which sub-endpoint to query."""
    activity       = "getEmgencyActivityInfo"       # 구급활동정보 (default — most citizen-relevant)
    transfer       = "getEmgPatientTransferInfo"    # 구급환자이송정보
    condition      = "getEmgPatientConditionInfo"   # 구급환자상태정보
    firstaid       = "getEmgPatientFirstaidInfo"    # 구급환자응급처치정보
    vehicle_dispatch = "getEmgVehicleDispatchInfo"  # 구급차량출동정보
    vehicle_info   = "getEmgVehicleInfo"            # 구급차량정보


class NfaEmergencyInfoServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: NfaEmgOperation = Field(
        default=NfaEmgOperation.activity,
        description=(
            "Which emergency info sub-endpoint to query. "
            "Default 'activity' (getEmgencyActivityInfo) returns dispatch distance, "
            "patient symptoms, and crew qualifications. "
            "Choose 'transfer' for patient transport, 'condition' for vitals, "
            "'firstaid' for treatment codes, 'vehicle_dispatch' or 'vehicle_info' for fleet data."
        ),
    )
    sido_hq_ogid_nm: str | None = Field(
        default=None,
        max_length=22,
        description=(
            "Regional fire headquarters name (시도본부). "
            "Example: '서울소방재난본부', '충청남도소방본부', '경기도소방재난본부'. "
            "Optional — omit to query all regions (may return large result set)."
        ),
    )
    rsac_gut_fstt_ogid_nm: str = Field(
        max_length=7,
        description=(
            "Fire station name (출동소방서). Required. "
            "Example: '공주소방서', '파주소방서', '은평소방서'. "
            "Must be a valid NFA station name — do not guess. "
            "Use nfa_safety_center_lookup (when available) or ask the citizen."
        ),
    )
    stmt_ym: str = Field(
        pattern=r"^\d{6}$",
        description=(
            "Report year-month in YYYYMM format (신고년월 or 출동년월). "
            "Example: '202101' for January 2021. "
            "Required for all operations. Do not use future dates."
        ),
    )
    page_no: int = Field(
        default=1, ge=1,
        description="Page number (1-indexed). Default 1.",
    )
    num_of_rows: int = Field(
        default=10, ge=1, le=100,
        description=(
            "Number of records per page. Default 10. Maximum 100 per NFA API contract."
        ),
    )
    result_type: Literal["json"] = Field(
        default="json",
        description=(
            "Response format. Fixed to 'json'. Do not override — "
            "the adapter's XML guard requires JSON to be requested."
        ),
    )
```

#### Output schema — `getEmgencyActivityInfo` (primary operation)

```python
class NfaActivityItem(BaseModel):
    """Single 구급활동정보 record. All fields optional — NFA may omit sparse fields."""
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str = Field(description="시도본부 (regional HQ name)")
    rsacGutFsttOgidNm: str = Field(description="출동소방서 (fire station name)")
    gutYm: str = Field(description="출동년월 YYYYMM")
    gutHh: str | None = Field(default=None, description="출동시 HH (dispatch hour)")
    sptMvmnDtc: str | None = Field(default=None, description="현장과의거리 (distance to scene, meters)")
    ptntAge: str | None = Field(default=None, description="환자연령 bracket (e.g. '60~69세')")
    ptntSdtSeCdNm: str | None = Field(default=None, description="환자성별 (남/여)")
    egrcSidoCdNm: str | None = Field(default=None, description="긴급구조시 (rescue city)")
    egrcSiggCdNm: str | None = Field(default=None, description="긴급구조구 (rescue district)")
    ruptOccrPlcCdNm: str | None = Field(default=None, description="구급사고발생장소 (incident location type)")
    ruptSptmCdNm: str | None = Field(default=None, description="환자증상 (patient symptom)")
    rcptPathCdNm: str | None = Field(default=None, description="접수경로 (call receipt channel)")
    cptcSeCdNm: str | None = Field(default=None, description="관할구분 (jurisdiction type)")
    frnrAt: str | None = Field(default=None, description="외국인여부 Y/N")
    emtpQlcClCd1Nm: str | None = Field(default=None, description="구급대원1 자격 (lead crew qualification)")
    emtpQlcClCd2Nm: str | None = Field(default=None, description="구급대원2 자격")
    emtpQlcClCd3Nm: str | None = Field(default=None, description="운전요원 자격")


class NfaEmergencyInfoServiceOutput(BaseModel):
    """Normalized response from EmergencyInformationService."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str = Field(description="The operation path queried.")
    result_code: str = Field(description="API result code ('00' = NORMAL SERVICE)")
    result_msg: str = Field(description="API result message")
    page_no: int
    num_of_rows: int
    total_count: int
    items: list[NfaActivityItem] = Field(
        description=(
            "List of emergency info records. Empty list when no records match. "
            "Item schema shown for 'activity' operation; "
            "other operations return operation-specific fields."
        ),
    )
```

> Note: `getEmgPatientTransferInfo`, `getEmgPatientConditionInfo`,
> `getEmgPatientFirstaidInfo`, `getEmgVehicleDispatchInfo`, and `getEmgVehicleInfo`
> return different item fields (see docx TABLE 4, 8, 12, 16, 20). Full Pydantic models
> for those operations will be added at `/speckit-plan` time. For the interface-only
> phase, `items: list[NfaActivityItem]` with `extra="allow"` covers all operations.

#### Handler contract (interface-only)

The handler MUST raise `Layer3GateViolation` unconditionally. The executor's Layer 3 gate
short-circuits `requires_auth=True` adapters before `handle()` is reached
(FR-025, FR-026, SC-006). The `handle()` body is the defence-in-depth backstop.

```python
async def handle(inp: NfaEmergencyInfoServiceInput) -> dict[str, object]:
    """Should never reach here — Layer 3 gate short-circuits on requires_auth=True.
    # TODO: implement after Layer 3 auth gate is provisioned (Epic #16 / #20).
    """
    raise Layer3GateViolation("nfa_emergency_info_service")
```

#### search_hint

```
119 구급 출동 소방청 구급정보 구급활동 구급차 통계 현황 소방서 긴급구조
119 NFA emergency ambulance dispatch activity statistics fire station Korea
```

#### Fixture strategy

Since the handler is interface-only, the recorded fixture asserts the executor returns
`LookupError(reason="auth_required")` with no upstream HTTP call. A synthetic fixture
representing the expected upstream JSON response shape MUST be created at
`tests/fixtures/nfa119/nfa_emergency_info_service.json`. Synthetic data drawn from docx
sample: `sidoHqOgidNm="충청남도소방본부"`, `rsacGutFsttOgidNm="천안동남소방서"`,
`gutYm="202112"`, `ruptSptmCdNm="기침"`, `ptntAge="60~69세"`.

#### Module path

```
src/kosmos/tools/nfa119/__init__.py
src/kosmos/tools/nfa119/emergency_info_service.py
tests/tools/nfa119/test_nfa_emergency_info_service.py
tests/fixtures/nfa119/nfa_emergency_info_service.json
docs/tools/nfa119.md
```

---

### 4.2 `mohw_welfare_eligibility_search`

#### Summary

| Field | Value |
|---|---|
| `tool_id` | `mohw_welfare_eligibility_search` |
| `name_ko` | `복지서비스 목록 조회 (한국사회보장정보원 SSIS)` |
| `provider` | `한국사회보장정보원 (SSIS) / 보건복지부 (MOHW)` |
| `category` | `["복지", "출산", "의료비", "보조금", "사회보장"]` |
| `auth_type` | `api_key` |
| `auth_level` | `AAL2` |
| `pipa_class` | `personal` |
| `is_irreversible` | `False` |
| `dpa_reference` | `dpa-ssis-welfare-v1` |
| `requires_auth` | `True` |
| `is_personal_data` | `True` |
| `is_concurrency_safe` | `True` |
| `cache_ttl_seconds` | `0` |
| `rate_limit_per_minute` | `10` |
| `is_core` | `False` |

**V1–V6 compliance check**:
- V1: `pipa_class="personal"` → `auth_level` must not be `"public"`. `AAL2` compliant.
- V2: `pipa_class="personal"` → `dpa_reference` must be non-null and well-formed.
  `dpa-ssis-welfare-v1` satisfies the pattern `^[A-Za-z][A-Za-z0-9_-]{5,63}$`. Compliant.
- V3: `mohw_welfare_eligibility_search` is NOT in `TOOL_MIN_AAL` yet — V3 does not fire at
  construction time. **`TOOL_MIN_AAL` must be extended with
  `"mohw_welfare_eligibility_search": "AAL2"` before or in the same PR as registration.**
- V4: `is_irreversible=False` → no constraint.
- V5: `auth_level="AAL2"` → `requires_auth=True`. Compliant.
- V6: `auth_type="api_key"`, `auth_level="AAL2"` → in allowed set `{AAL1, AAL2, AAL3}`. Compliant.
- FR-038: `is_personal_data=True` and `requires_auth=True`. Compliant.

**auth_level rationale**: The query parameters (`age`, `lifeArray`, `trgterIndvdlArray`) can
encode personal demographic signals (age bracket, household type) even if no name or ID is
submitted. AAL2 aligns with the `check_eligibility` canonical tool pattern from `TOOL_MIN_AAL`
and with the Layer 3 design intent for PII-adjacent queries.

**TOOL_MIN_AAL addition required**: add `"mohw_welfare_eligibility_search": "AAL2"`.

#### Endpoint

```
GET https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001
```

**Source**: SSIS welfare service list from `research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc`.
The URL and parameter table are confirmed from the technical document (§1.1 API URL, §2 request
parameter table). Response format is XML; JSON is not listed as a supported output format in v2.2.
The adapter MUST use the XML parser path.

#### Input schema

```python
import enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class SrchKeyCode(str, enum.Enum):
    """Service name keyword search field code."""
    name = "001"         # 서비스명
    summary = "002"      # 서비스요약
    all_fields = "003"   # 전체 (name + summary)

class OrderBy(str, enum.Enum):
    popular = "popular"   # 조회 수 기준
    date = "date"         # 등록일 기준


class MohwWelfareEligibilitySearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    search_wrd: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Free-text keyword to search welfare service names/summaries. "
            "Korean preferred. Example: '출산' for childbirth benefits. "
            "If None, returns services filtered by other parameters."
        ),
    )
    srch_key_code: SrchKeyCode = Field(
        default=SrchKeyCode.all_fields,
        description="Which fields to search (name=001, summary=002, all=003).",
    )
    life_array: str | None = Field(
        default=None,
        max_length=3,
        description=(
            "Life stage code (3 digits). Example: '007' for 임산부·출산. "
            "See SSIS life stage code table for full list."
        ),
    )
    trgter_indvdl_array: str | None = Field(
        default=None,
        max_length=3,
        description=(
            "Target individual type code (3 digits). Example: '050' for 임산부. "
            "See SSIS target individual code table."
        ),
    )
    intrs_thema_array: str | None = Field(
        default=None,
        max_length=3,
        description=(
            "Interest theme code (3 digits). Example: '010' for 임신·출산. "
            "See SSIS interest theme code table."
        ),
    )
    age: int | None = Field(
        default=None, ge=0, le=150,
        description=(
            "Citizen age in years. Used to filter age-eligible services. "
            "Do NOT request this from the citizen unless they have consented — "
            "this field triggers is_personal_data=True."
        ),
    )
    onap_psblt_yn: Literal["Y", "N"] | None = Field(
        default=None,
        description=(
            "Filter to only online-applicable services when 'Y'. "
            "Omit to return both online and offline services."
        ),
    )
    order_by: OrderBy = Field(
        default=OrderBy.popular,
        description="Sort order: 'popular' (inquiry count) or 'date' (registration date).",
    )
    page_no: int = Field(
        default=1, ge=1,
        description="Page number (1-indexed). Default 1.",
    )
    num_of_rows: int = Field(
        default=10, ge=1, le=500,
        description=(
            "Number of results per page. Default 10. Maximum 500 per SSIS API contract."
        ),
    )
    call_tp: Literal["L"] = Field(
        default="L",
        description=(
            "Call type: 'L' (list). Fixed to 'L' for this endpoint. "
            "Do not override."
        ),
    )
```

#### Output schema (placeholder — interface-only pattern)

```python
class _MohwWelfareEligibilitySearchOutput(RootModel[dict[str, object]]):
    """Placeholder output schema.

    Real shape from SSIS technical document v2.2 §3 (response parameters):
    - wantedList.totalCount (int)
    - wantedList.servList[] containing:
        servId, servNm, jurMnofNm, jurOrgNm, inqNum,
        servDgst, servDtlLink, svcfrstRegTs,
        lifeArray, intrsThemaArray, trgterIndvdlArray,
        onaPPsbltYn, sprtCycNm, srvPvsnNm.
    Schema will be finalized at /speckit-plan time with full Pydantic models.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
```

#### Handler contract (interface-only)

```python
async def handle(inp: MohwWelfareEligibilitySearchInput) -> dict[str, object]:
    """Should never reach here — Layer 3 gate short-circuits on requires_auth=True.
    # TODO: implement full XML parsing and response normalization once
    # Layer 3 auth gate is provisioned (Epic #16 / #20).
    """
    raise Layer3GateViolation("mohw_welfare_eligibility_search")
```

#### search_hint

```
복지서비스 출산 보조금 복지혜택 신청 사회보장정보원 보건복지부 임산부 지원
welfare benefit eligibility childbirth subsidy MOHW SSIS social security Korea
```

#### Fixture strategy

Synthetic fixture at `tests/fixtures/ssis/mohw_welfare_eligibility_search.json` with representative
SSIS XML response shape converted to a Python dict. Synthetic data: `servNm="출산가정 방문서비스"`,
`servId="WLF0000001188"`, `jurMnofNm="보건복지부"`. Primary test asserts executor returns
`LookupError(reason="auth_required")` with no upstream HTTP call.

#### Module path

```
src/kosmos/tools/ssis/__init__.py
src/kosmos/tools/ssis/welfare_eligibility_search.py
tests/tools/ssis/test_mohw_welfare_eligibility_search.py
tests/fixtures/ssis/mohw_welfare_eligibility_search.json
docs/tools/ssis.md
```

---

## 5. Security Metadata Summary

| Adapter | auth_type | auth_level | pipa_class | is_irreversible | dpa_reference | requires_auth | is_personal_data |
|---|---|---|---|---|---|---|---|
| `nfa_emergency_info_service` | `api_key` | `AAL1` | `non_personal` | `False` | `None` | `True` | `False` |
| `mohw_welfare_eligibility_search` | `api_key` | `AAL2` | `personal` | `False` | `dpa-ssis-welfare-v1` | `True` | `True` |

Both adapters are read-only (`is_irreversible=False`) and share `KOSMOS_DATA_GO_KR_API_KEY`.
Neither fires FR-007 live-introspection, as `is_irreversible=False`.

Output sanitization declaration (security PR checklist §224):
- `nfa_emergency_info_service`: `pipa_class="non_personal"` → `sanitized_output_hash=None`,
  `merkle_covered_hash="output_hash"`.
- `mohw_welfare_eligibility_search`: `pipa_class="personal"` → sanitized output variant required,
  `sanitized_output_hash` set, `merkle_covered_hash="sanitized_output_hash"`. LLM synthesis gated
  by `synthesis_consent=True` in originating consent record (FR-015).

---

## 6. TOOL_MIN_AAL Changes Required

The `src/kosmos/security/audit.py` `TOOL_MIN_AAL` table must be extended in the same PR:

```python
TOOL_MIN_AAL: Final[dict[str, AALLevel]] = {
    # ... existing entries ...
    "nfa_emergency_info_service": "AAL1",       # NFA EMS stats — anonymized, serviceKey auth
    "mohw_welfare_eligibility_search": "AAL2",  # SSIS welfare — personal demographic inputs
}
```

This ensures V3 fires from first registration and prevents auth_level drift in future PRs.

---

## 7. Clarifications

### C1 — NFA 119 API scope confirmed [RESOLVED 2026-04-18]

The NFA technical document has been retrieved and parsed. The `EmergencyInformationService`
(provider `1661000`) is a **statistical records service** exposing 6 operations over anonymized
EMS data. It is NOT a real-time geospatial 119 facility locator.

- **Document**: `research/data/nfa119/공공데이터 오픈API 활용가이드(소방청_구급정보).docx`
  (data.go.kr catalog ID 15099423, KOGL Type 1)
- **Confirmed endpoint**: `https://apis.data.go.kr/1661000/EmergencyInformationService/{operation}`
- **Confirmed auth**: `serviceKey` query parameter (URL-encoded), REST GET
- **Confirmed format**: XML and JSON both supported via `resultType` param; adapter requests JSON
- **Rate**: 30 TPS per operation, daily 1,000 call cap on development accounts (`데이터 갱신주기: 일 1회`)
- **Operations confirmed**: 6 — see §4.1 endpoint table

The adapter name has been changed from the draft name `emergency_119_facility_search` to
`nfa_emergency_info_service` to accurately reflect the API's official name
"소방청 구급정보서비스" and its statistical (not facility-search) nature.

The geospatial nearest-station use case originally scoped under this item is now addressed
via the CSV-backed `nfa_safety_center_lookup` extension path documented in §9.

### C2 — SSIS life-stage / target-individual code tables

The technical document `활용가이드_중앙부처복지서비스(v2.2).doc` references code tables for
`lifeArray`, `trgterIndvdlArray`, and `intrsThemaArray`. The code table document
`지자체복지서비스_코드표(v1.0).doc` is present in `research/data/ssis/` but applies to 지자체
(local government) services. It is not confirmed whether this code table also covers 중앙부처
services. The `/speckit-plan` stage should confirm whether the same code table applies and
produce Python `Enum` definitions from it. This is a non-blocking clarification — the adapter
can use raw `str | None` fields for code parameters and upgrade to `Enum` after confirmation.

### C3 — DPA template `dpa-ssis-welfare-v1`

The `dpa_reference` value `dpa-ssis-welfare-v1` is a placeholder identifier. A DPA template
document governing KOSMOS's §26 processor relationship with SSIS does not yet exist. Per the
security PR checklist, this identifier must be traceable to an actual DPA template before the
adapter is deployed to production. For Phase 2 development purposes, the placeholder is
sufficient — but Epic #15 should include a task to draft the DPA template outline.

---

## 8. References Consulted

| Source | How used |
|---|---|
| Epic #15 issue body (`gh issue view 15 --repo umyunsang/KOSMOS`) | Primary scope definition, adapter field tables, SSIS/MOHW decision prompt |
| `specs/022-mvp-main-tool/spec.md` | `lookup` mode=fetch registration pattern, interface-only adapter pattern |
| `src/kosmos/tools/nmc/emergency_search.py` | Canonical interface-only adapter implementation (NMC reference pattern) |
| `src/kosmos/tools/hira/hospital_search.py` | Full HTTP adapter pattern reference |
| `src/kosmos/tools/models.py` | `GovAPITool` field contract, V1–V6 validators, `_AUTH_TYPE_LEVEL_MAPPING` |
| `src/kosmos/security/audit.py` | `TOOL_MIN_AAL` table, `AALLevel` type |
| `specs/024-tool-security-v1/spec.md` | `ToolCallAuditRecord`, PIPA role, DPA reference contract |
| `specs/025-tool-security-v6/spec.md` | `auth_type ↔ auth_level` invariant canonical mapping |
| `docs/tool-adapters.md` | Adapter shape, PR checklist, interface-only pattern rules |
| `docs/vision.md` | Scenario 2 (응급), Scenario 3 (출산보조금), Layer 2 tool shape |
| `.specify/memory/constitution.md` | §II fail-closed defaults, §III Pydantic v2 strict typing, §IV government API compliance |
| `research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc` | SSIS endpoint URL, request/response parameter tables, XML format confirmation |
| `research/data/nfa119/공공데이터 오픈API 활용가이드(소방청_구급정보).docx` | **Confirmed** NFA endpoint, auth method, 6 operations, request/response schemas, rate limit, error codes |
| `research/data/nfa119/README.md` | File provenance, KOGL license, endpoint summary |
| `research/data/nfa119/소방청_119안전센터 현황_20250701.csv` | Nationwide 119 safety center directory — columns: 순번, 시도본부, 소방서명, 119안전센터명, 주소, 전화번호, 팩스번호 — see §9 for extension path |

---

## 9. Extension Path

Future Phase 2 work can add the following adapters without modifying `lookup` or
`resolve_location`:

1. **`nfa_safety_center_lookup`** — LOCAL CSV-backed nearest 119 safety-center lookup.
   Source: `research/data/nfa119/소방청_119안전센터 현황_20250701.csv`
   (columns: `순번`, `시도본부`, `소방서명`, `119안전센터명`, `주소`, `전화번호`, `팩스번호`).
   This file has no GPS coordinates in the current export. The extension path requires either:
   (a) a geocoding pass over `주소` via `resolve_location`, or
   (b) a refreshed CSV export with latitude/longitude columns from NFA.
   This adapter covers the geospatial "find nearest 119 station" use case that was originally
   scoped under this spec's primary adapter but is NOT served by `EmergencyInformationService`.
   MVP scope: NOT included in this spec.

2. **`ssis_welfare_detail_fetch`** — `NationalWelfaredetailedV001` single-service detail by `servId`.
   Prerequisite: citizen selects a service from `mohw_welfare_eligibility_search` results.

3. **`nfa_emg_statistics_service`** — `EmergencyStatisticsService` (provider `1661000`,
   data.go.kr ID 15099428) for aggregate statistical queries. Reference docx:
   `research/data/nfa119/공공데이터 오픈API 활용가이드(소방청_구급통계).docx`.

4. **`gov24_application_guide`** — Gov24 service application guide for welfare services
   discovered through `mohw_welfare_eligibility_search` (Epic #22).

Each can be added as a drop-in `GovAPITool` registration in `register_all.py` following the
same interface-only pattern established here.
