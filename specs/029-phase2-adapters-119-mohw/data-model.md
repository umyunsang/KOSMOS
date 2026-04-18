# Phase 1 — Data Model: 029 Phase 2 Adapters (NFA 119 + MOHW)

**Spec**: [`spec.md`](./spec.md) · **Research**: [`research.md`](./research.md)
**Date**: 2026-04-18

This file fixes the Pydantic v2 schemas (input + output for every operation),
the security-metadata declarations, the `TOOL_MIN_AAL` diff, and the shared
SSIS code-table enums. Every schema in this document is normative for
`/speckit-tasks` and implementation.

All models share:

```python
model_config = ConfigDict(extra="forbid", frozen=True)
```

unless explicitly noted. No `Any` types anywhere (Constitution §III).

---

## 1. Shared module — SSIS code tables (`src/kosmos/tools/ssis/codes.py`)

```python
from __future__ import annotations

import enum


class SrchKeyCode(str, enum.Enum):
    """Service-list keyword search field code (SSIS 검색분류)."""
    name = "001"          # 서비스명
    summary = "002"       # 서비스내용
    all_fields = "003"    # 서비스명 + 서비스내용


class CallType(str, enum.Enum):
    """SSIS callTp — 호출페이지 타입."""
    list_ = "L"           # 목록 (list)
    detail = "D"          # 상세 (detail) — reserved for NationalWelfaredetailedV001


class OrderBy(str, enum.Enum):
    """SSIS orderBy — 정렬순서."""
    date = "date"         # 등록순
    popular = "popular"   # 인기순 (조회 수 기준)


class LifeArrayCode(str, enum.Enum):
    """Life-stage code (생애주기). Source: 지자체복지서비스_코드표(v1.0).doc."""
    infant = "001"              # 영유아
    child = "002"               # 아동
    teen = "003"                # 청소년
    young_adult = "004"         # 청년
    middle_aged = "005"         # 중장년
    elderly = "006"             # 노년
    pregnancy_birth = "007"     # 임신·출산


class TrgterIndvdlCode(str, enum.Enum):
    """Target-individual / household-type code (가구상황)."""
    multicultural = "010"       # 다문화·탈북민
    multichild = "020"          # 다자녀
    veteran = "030"             # 보훈대상자
    disabled = "040"            # 장애인
    low_income = "050"          # 저소득
    single_parent = "060"       # 한부모·조손


class IntrsThemaCode(str, enum.Enum):
    """Interest-theme code (관심주제)."""
    physical_health = "010"     # 신체건강
    mental_health = "020"       # 정신건강
    livelihood = "030"          # 생활지원
    housing = "040"             # 주거
    employment = "050"          # 일자리
    culture_leisure = "060"     # 문화·여가
    safety_crisis = "070"       # 안전·위기
    pregnancy_birth = "080"     # 임신·출산
    childcare = "090"           # 보육
    education = "100"           # 교육
    adoption_foster = "110"     # 입양·위탁
    care_support = "120"        # 보호·돌봄
    small_finance = "130"       # 서민금융
    legal = "140"               # 법률
```

These enums are **shared** across the MOHW adapter (this spec) and the future
`ssis_welfare_detail_fetch` adapter (spec §9.2).

---

## 2. NFA 119 — Input schema (`src/kosmos/tools/nfa119/emergency_info_service.py`)

```python
from __future__ import annotations

import enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NfaEmgOperation(str, enum.Enum):
    """Sub-endpoint selector for EmergencyInformationService."""
    activity = "getEmgencyActivityInfo"         # 구급활동정보 (default)
    transfer = "getEmgPatientTransferInfo"      # 구급환자이송정보
    condition = "getEmgPatientConditionInfo"    # 구급환자상태정보
    firstaid = "getEmgPatientFirstaidInfo"      # 구급환자응급처치정보
    vehicle_dispatch = "getEmgVehicleDispatchInfo"  # 구급차량출동정보
    vehicle_info = "getEmgVehicleInfo"          # 구급차량정보


class NfaEmergencyInfoServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: NfaEmgOperation = Field(
        default=NfaEmgOperation.activity,
        description=(
            "Which emergency-info sub-endpoint to query. Default 'activity' "
            "(getEmgencyActivityInfo) returns dispatch distance, patient symptoms, "
            "and crew qualifications — the most citizen-relevant view. "
            "Choose 'transfer' for patient transport, 'condition' for vitals, "
            "'firstaid' for treatment codes, 'vehicle_dispatch' or 'vehicle_info' "
            "for fleet data."
        ),
    )
    sido_hq_ogid_nm: str | None = Field(
        default=None,
        max_length=22,
        description=(
            "Regional fire headquarters name (시도본부). Example: "
            "'서울소방재난본부', '충청남도소방본부', '경기도소방재난본부'. "
            "Optional — omit to query all regions (may return a large result set)."
        ),
    )
    rsac_gut_fstt_ogid_nm: str = Field(
        max_length=7,
        description=(
            "Fire station name (출동소방서). Required. "
            "Example: '공주소방서', '파주소방서', '은평소방서'. "
            "Must be a valid NFA station name — do not guess. "
            "Use nfa_safety_center_lookup (future) or ask the citizen."
        ),
    )
    stmt_ym: str = Field(
        pattern=r"^\d{6}$",
        description=(
            "Report year-month in YYYYMM format (신고년월 or 출동년월). "
            "Example: '202101' for January 2021. Required for all operations. "
            "Do not use future dates."
        ),
    )
    page_no: int = Field(
        default=1, ge=1,
        description="Page number (1-indexed). Default 1.",
    )
    num_of_rows: int = Field(
        default=10, ge=1, le=100,
        description=(
            "Number of records per page. Default 10, maximum 100 per NFA API contract."
        ),
    )
    result_type: Literal["json"] = Field(
        default="json",
        description=(
            "Response format. Fixed to 'json' — the adapter's Content-Type guard "
            "requires JSON to be requested. Do not override."
        ),
    )
```

---

## 3. NFA 119 — Output schemas per operation

### 3.1 `getEmgencyActivityInfo` — `NfaActivityItem` (primary)

Sourced from NFA docx sample fields. Citizen-relevant fields only (we do NOT
include every field from the full activity table; we expose the ones a
conversational agent would surface).

```python
class NfaActivityItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str = Field(description="시도본부 (regional HQ name)")  # noqa: N815
    rsacGutFsttOgidNm: str = Field(description="출동소방서 (fire station name)")  # noqa: N815
    gutYm: str = Field(description="출동년월 YYYYMM")  # noqa: N815
    gutHh: str | None = Field(default=None, description="출동시 HH (dispatch hour)")  # noqa: N815
    sptMvmnDtc: str | None = Field(default=None, description="현장과의거리 (metres)")  # noqa: N815
    ptntAge: str | None = Field(default=None, description="환자연령 bracket (e.g. '60~69세')")  # noqa: N815
    ptntSdtSeCdNm: str | None = Field(default=None, description="환자성별 (남/여)")  # noqa: N815
    egrcSidoCdNm: str | None = Field(default=None, description="긴급구조시")  # noqa: N815
    egrcSiggCdNm: str | None = Field(default=None, description="긴급구조구")  # noqa: N815
    ruptOccrPlcCdNm: str | None = Field(default=None, description="구급사고발생장소")  # noqa: N815
    ruptSptmCdNm: str | None = Field(default=None, description="환자증상")  # noqa: N815
    rcptPathCdNm: str | None = Field(default=None, description="접수경로")  # noqa: N815
    cptcSeCdNm: str | None = Field(default=None, description="관할구분")  # noqa: N815
    frnrAt: str | None = Field(default=None, description="외국인여부 Y/N")  # noqa: N815
    emtpQlcClCd1Nm: str | None = Field(default=None, description="구급대원1 자격")  # noqa: N815
    emtpQlcClCd2Nm: str | None = Field(default=None, description="구급대원2 자격")  # noqa: N815
    emtpQlcClCd3Nm: str | None = Field(default=None, description="운전요원 자격")  # noqa: N815
```

### 3.2 `getEmgPatientTransferInfo` — `NfaTransferItem`

```python
class NfaTransferItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str  # noqa: N815
    stmtYm: str  # noqa: N815
    stmtHh: str | None = None  # noqa: N815
    rlifAcdAsmCdNm: str | None = Field(default=None, description="구급사고유형")  # noqa: N815
    ptntAge: str | None = None  # noqa: N815
    ptntSdtSeCdNm: str | None = Field(default=None, description="환자성별")  # noqa: N815
    frnrAt: str | None = Field(default=None, description="내외국인")  # noqa: N815
    ptntTyCdNm: str | None = Field(default=None, description="환자유형")  # noqa: N815
    ruptOccrPlcCdNm: str | None = Field(default=None, description="구급사고발생장소")  # noqa: N815
    rlifOccrTyCdNm: str | None = Field(default=None, description="발생유형")  # noqa: N815
    anmlInctCdNm: str | None = Field(default=None, description="동물곤충원인")  # noqa: N815
    wmhtDamgCdNm: str | None = Field(default=None, description="온열손상")  # noqa: N815
```

### 3.3 `getEmgPatientConditionInfo` — `NfaConditionItem`

```python
class NfaConditionItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    ruptSptmCdNm: str = Field(description="환자증상")  # noqa: N815
    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str  # noqa: N815
    stmtYm: str  # noqa: N815
    stmtHh: str | None = None  # noqa: N815
    ptntAge: str | None = None  # noqa: N815
    lwsBpsr: str | None = Field(default=None, description="최저혈압")  # noqa: N815
    topBpsr: str | None = Field(default=None, description="최고혈압")  # noqa: N815
    ptntHbco: str | None = Field(default=None, description="심박수")  # noqa: N815
    ptntBfco: str | None = Field(default=None, description="호흡수")  # noqa: N815
    ptntOsv: str | None = Field(default=None, description="산소포화도")  # noqa: N815
    ptntBht: str | None = Field(default=None, description="체온")  # noqa: N815
```

### 3.4 `getEmgPatientFirstaidInfo` — `NfaFirstaidItem`

```python
class NfaFirstaidItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str  # noqa: N815
    stmtYm: str  # noqa: N815
    stmtHh: str | None = None  # noqa: N815
    ptntAge: str | None = None  # noqa: N815
    ptntSdtSeCdNm: str | None = None  # noqa: N815
    fstaCdNm: str | None = Field(default=None, description="응급처치코드")  # noqa: N815
```

### 3.5 `getEmgVehicleDispatchInfo` — `NfaVehicleDispatchItem`

```python
class NfaVehicleDispatchItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str  # noqa: N815
    stmtYm: str  # noqa: N815
    stmtHh: str | None = None  # noqa: N815
    vctpCdNm: str = Field(description="차종코드명")  # noqa: N815
    vhclSeCd: str | None = Field(default=None, description="차량구분")  # noqa: N815
    vhclNo: str | None = Field(default=None, description="차량번호")  # noqa: N815
    vhclStatCdNm: str | None = Field(default=None, description="차량상태")  # noqa: N815
    gotFrmtAt: str | None = Field(default=None, description="출동대편성여부 Y/N")  # noqa: N815
    vhcn: str | None = Field(default=None, description="차량명")  # noqa: N815
    vhclGrCdNm: str | None = Field(default=None, description="차량그룹코드명")  # noqa: N815
    mnm: str | None = Field(default=None, description="제작사")
    mdnm: str | None = Field(default=None, description="기종명")
    gutPcnt: str | None = Field(default=None, description="출동인원수")  # noqa: N815
    tnkCpct: str | None = Field(default=None, description="탱크용량")  # noqa: N815
    gutOdr: str | None = Field(default=None, description="출동차수")  # noqa: N815
```

### 3.6 `getEmgVehicleInfo` — `NfaVehicleInfoItem`

```python
class NfaVehicleInfoItem(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str = Field(description="소방서")  # noqa: N815
    vhclSeCd: str | None = Field(default=None, description="차량구분")  # noqa: N815
    vhclNo: str | None = Field(default=None, description="차량번호")  # noqa: N815
    vctpCdNm: str | None = Field(default=None, description="차종코드명")  # noqa: N815
    vhclStatCdNm: str | None = Field(default=None, description="차량상태코드명")  # noqa: N815
    gotFrmtAt: str | None = Field(default=None, description="출동대편성여부")  # noqa: N815
    vhcn: str | None = Field(default=None, description="차량명")  # noqa: N815
    vhclGrCdNm: str | None = Field(default=None, description="차량그룹코드명")  # noqa: N815
    mnm: str | None = Field(default=None, description="제작사")
    mdnm: str | None = Field(default=None, description="기종명")
    bdgPcnt: str | None = Field(default=None, description="탑승인원수")  # noqa: N815
    tnkCpct: str | None = Field(default=None, description="탱크용량")  # noqa: N815
    stde: str | None = Field(default=None, description="기준일자 YYYYMMDD")
```

### 3.7 Envelope — `NfaEmergencyInfoServiceOutput`

```python
from pydantic import RootModel


NfaItem = (
    NfaActivityItem
    | NfaTransferItem
    | NfaConditionItem
    | NfaFirstaidItem
    | NfaVehicleDispatchItem
    | NfaVehicleInfoItem
)


class NfaEmergencyInfoServiceOutput(BaseModel):
    """Normalized upstream response wrapper."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str = Field(description="Queried operation path (e.g. 'getEmgencyActivityInfo').")
    result_code: str = Field(description="API resultCode ('00' = NORMAL SERVICE).")
    result_msg: str = Field(description="API resultMsg.")
    page_no: int
    num_of_rows: int
    total_count: int
    items: list[NfaItem] = Field(
        description=(
            "List of emergency-info records. Empty list when no records match. "
            "Item schema depends on the 'operation' discriminator."
        ),
    )
```

**Interface-only registration note**: For V1 the adapter registers with
`output_schema = _NfaEmergencyInfoServiceOutputStub = RootModel[dict[str, Any]]`
to match the NMC reference pattern. The per-operation models above are
authored and committed so the switch-over when Layer 3 lands is a one-line
change, not a re-planning cycle.

---

## 4. NFA 119 — `GovAPITool` registration block

```python
NFA_EMERGENCY_INFO_SERVICE_TOOL = GovAPITool(
    id="nfa_emergency_info_service",
    name_ko="소방청 구급정보서비스 (구급활동 통계 조회)",
    provider="소방청 (National Fire Agency, NFA)",
    category=["안전", "응급", "소방", "119", "구급통계"],
    endpoint="https://apis.data.go.kr/1661000/EmergencyInformationService",
    auth_type="api_key",
    input_schema=NfaEmergencyInfoServiceInput,
    output_schema=_NfaEmergencyInfoServiceOutputStub,  # RootModel[dict] stub
    llm_description=(
        "Query the NFA (소방청) emergency-activity records service for historical, "
        "anonymized EMS statistics by region, fire station, and report year-month. "
        "Returns dispatch distance, patient symptoms, and crew qualifications when "
        "operation='activity' (default). This is NOT a real-time 119 dispatch tool "
        "and does NOT return current-incident or facility-locator data. "
        "IMPORTANT: requires_auth=True — unauthenticated sessions receive auth_required."
    ),
    search_hint=(
        "119 구급 출동 소방청 구급정보 구급활동 구급차 통계 현황 소방서 긴급구조 "
        "119 NFA emergency ambulance dispatch activity statistics fire station Korea"
    ),
    auth_level="AAL1",
    pipa_class="non_personal",
    is_irreversible=False,
    dpa_reference=None,
    requires_auth=True,
    is_personal_data=False,
    is_concurrency_safe=True,
    cache_ttl_seconds=86400,
    rate_limit_per_minute=10,
    is_core=False,
)
```

---

## 5. MOHW — Input schema (`src/kosmos/tools/ssis/welfare_eligibility_search.py`)

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.ssis.codes import (
    CallType,
    IntrsThemaCode,
    LifeArrayCode,
    OrderBy,
    SrchKeyCode,
    TrgterIndvdlCode,
)


class MohwWelfareEligibilitySearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    search_wrd: str | None = Field(
        default=None,
        max_length=100,
        description=(
            "Free-text keyword to search welfare-service names/summaries. "
            "Korean preferred. Example: '출산' for childbirth benefits. "
            "Omit to filter by codes only."
        ),
    )
    srch_key_code: SrchKeyCode = Field(
        default=SrchKeyCode.all_fields,
        description="Which fields to search (001 name, 002 summary, 003 both).",
    )
    life_array: LifeArrayCode | None = Field(
        default=None,
        description="Life-stage filter (e.g. '007' for 임신·출산).",
    )
    trgter_indvdl_array: TrgterIndvdlCode | None = Field(
        default=None,
        description="Target individual / household-type filter (e.g. '020' 다자녀).",
    )
    intrs_thema_array: IntrsThemaCode | None = Field(
        default=None,
        description=(
            "Interest-theme filter (e.g. '080' for 임신·출산, '010' for 신체건강). "
            "NOTE: Spec draft used '010' as a placeholder; the authoritative "
            "임신·출산 code for intrsThemaArray is '080'."
        ),
    )
    age: int | None = Field(
        default=None, ge=0, le=150,
        description=(
            "Citizen age in years. Used to filter age-eligible services. "
            "Do NOT request this from the citizen unless they have consented — "
            "this field is part of the is_personal_data=True surface."
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
        description="Sort order: 'popular' (조회 수) or 'date' (등록순).",
    )
    page_no: int = Field(
        default=1, ge=1, le=1000,
        description="Page number (1-indexed). SSIS caps at 1000.",
    )
    num_of_rows: int = Field(
        default=10, ge=1, le=500,
        description="Records per page. Default 10, maximum 500 per SSIS API contract.",
    )
    call_tp: CallType = Field(
        default=CallType.list_,
        description="Call type — fixed to 'L' (list) for this endpoint.",
    )
```

---

## 6. MOHW — Output schema

### 6.1 `SsisWelfareServiceItem`

```python
class SsisWelfareServiceItem(BaseModel):
    """Single welfare service record from NationalWelfarelistV001."""
    model_config = ConfigDict(extra="allow", frozen=True)

    servId: str = Field(description="서비스ID (e.g. 'WLF00001188')")  # noqa: N815
    servNm: str = Field(description="서비스명")  # noqa: N815
    jurMnofNm: str = Field(description="소관부처명 (ministry)")  # noqa: N815
    jurOrgNm: str | None = Field(default=None, description="소관조직명 (bureau)")  # noqa: N815
    inqNum: str | None = Field(default=None, description="조회수 (raw string)")  # noqa: N815
    servDgst: str | None = Field(default=None, description="서비스 요약")  # noqa: N815
    servDtlLink: str | None = Field(default=None, description="서비스 상세링크 (bokjiro.go.kr)")  # noqa: N815
    svcfrstRegTs: str | None = Field(default=None, description="서비스등록일")  # noqa: N815
    lifeArray: str | None = Field(default=None, description="생애주기 (comma-separated names)")  # noqa: N815
    intrsThemaArray: str | None = Field(default=None, description="관심주제")  # noqa: N815
    trgterIndvdlArray: str | None = Field(default=None, description="가구유형")  # noqa: N815
    sprtCycNm: str | None = Field(default=None, description="지원주기 (e.g. '1회성')")  # noqa: N815
    srvPvsnNm: str | None = Field(default=None, description="제공유형 (e.g. '전자바우처')")  # noqa: N815
    rprsCtadr: str | None = Field(default=None, description="문의처")  # noqa: N815
    onapPsbltYn: Literal["Y", "N"] | None = Field(default=None, description="온라인신청가능여부")  # noqa: N815
```

### 6.2 `MohwWelfareEligibilitySearchOutput`

```python
class MohwWelfareEligibilitySearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    result_code: str = Field(description="결과코드 ('0' = SUCCESS in SSIS v2.0)")
    result_message: str = Field(description="결과메세지")
    page_no: int
    num_of_rows: int
    total_count: int
    items: list[SsisWelfareServiceItem] = Field(
        description="List of welfare services matching the query."
    )
```

**Interface-only registration note**: V1 registers with
`output_schema = _MohwWelfareEligibilitySearchOutputStub = RootModel[dict[str, Any]]`
per the NMC reference pattern. The real models are ready for Layer 3 switch-over.

---

## 7. MOHW — `GovAPITool` registration block

```python
MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL = GovAPITool(
    id="mohw_welfare_eligibility_search",
    name_ko="복지서비스 목록 조회 (한국사회보장정보원 SSIS)",
    provider="한국사회보장정보원 (SSIS) / 보건복지부 (MOHW)",
    category=["복지", "출산", "의료비", "보조금", "사회보장"],
    endpoint=(
        "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"
        "/NationalWelfarelistV001"
    ),
    auth_type="api_key",
    input_schema=MohwWelfareEligibilitySearchInput,
    output_schema=_MohwWelfareEligibilitySearchOutputStub,  # RootModel[dict] stub
    llm_description=(
        "Search the SSIS central-ministry welfare-service catalog for services matching "
        "life stage, household type, interest theme, age, or keyword. Returns a ranked "
        "list with serviceId, name, ministry, summary, and bokjiro.go.kr detail link. "
        "Use for 'am I eligible for X?' / '출산 보조금 뭐 있어?' questions. "
        "IMPORTANT: is_personal_data=True and requires_auth=True. "
        "Unauthenticated sessions receive auth_required."
    ),
    search_hint=(
        "복지서비스 출산 보조금 복지혜택 신청 사회보장정보원 보건복지부 임산부 지원 "
        "welfare benefit eligibility childbirth subsidy MOHW SSIS social security Korea"
    ),
    auth_level="AAL2",
    pipa_class="personal",
    is_irreversible=False,
    dpa_reference="dpa-ssis-welfare-v1",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=True,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    is_core=False,
)
```

---

## 8. `TOOL_MIN_AAL` diff (`src/kosmos/security/audit.py`)

```diff
 TOOL_MIN_AAL: Final[dict[str, AALLevel]] = {
     "lookup": "AAL1",
     "resolve_location": "AAL1",
     "check_eligibility": "AAL2",
     "subscribe_alert": "AAL2",
     "reserve_slot": "AAL2",
     "issue_certificate": "AAL3",
     "submit_application": "AAL2",
     "pay": "AAL3",
+    # Phase 2 API adapters (spec 029):
+    "nfa_emergency_info_service": "AAL1",       # NFA EMS stats — anonymized, serviceKey auth
+    "mohw_welfare_eligibility_search": "AAL2",  # SSIS welfare — personal demographic inputs
 }
```

These two rows activate validator V3 (FR-001 / FR-005) drift-protection for
the new adapters from the moment they register. Any future PR that changes
`auth_level` on either adapter without updating this table will fail at
load time — the exact guarantee spec 024 §V3 promises.

---

## 9. DPA placeholder stub (`docs/security/dpa/dpa-ssis-welfare-v1.md`)

```markdown
# DPA Template: dpa-ssis-welfare-v1

**Status**: PLACEHOLDER — real DPA template pending Epic #16 / #20.
This file exists to reserve the identifier for validator V2 traceability.

**Scope (when authored)**: KOSMOS's §26 수탁자 (PIPA) relationship with SSIS
(한국사회보장정보원) governing the `NationalWelfarelistV001` endpoint. The
template covers consent text for welfare-eligibility queries, retention windows
for SSIS responses in KOSMOS session logs, and the synthesis-consent gate for
LLM-generated eligibility guidance.

**Tracked under**: Epic #16 (Layer 3 auth gate) — a dedicated task to draft
the full DPA template must be created alongside the Layer 3 ship.
```

---

## 10. File manifest

### New source files

```
src/kosmos/tools/nfa119/__init__.py
src/kosmos/tools/nfa119/emergency_info_service.py
src/kosmos/tools/ssis/__init__.py
src/kosmos/tools/ssis/codes.py
src/kosmos/tools/ssis/welfare_eligibility_search.py
docs/security/dpa/dpa-ssis-welfare-v1.md
docs/tools/nfa119.md
docs/tools/ssis.md
```

### New test files

```
tests/tools/nfa119/__init__.py
tests/tools/nfa119/test_nfa_emergency_info_service.py
tests/tools/ssis/__init__.py
tests/tools/ssis/test_mohw_welfare_eligibility_search.py
tests/tools/ssis/test_codes.py  # enum coverage
tests/fixtures/nfa119/nfa_emergency_info_service.json
tests/fixtures/ssis/mohw_welfare_eligibility_search.json
```

### Modified source files

```
src/kosmos/security/audit.py            # TOOL_MIN_AAL entries
src/kosmos/tools/register_all.py        # register() calls for both new adapters
```

No other file requires modification. No new runtime dependency. No new
environment variable (the existing `KOSMOS_DATA_GO_KR_API_KEY` is reused).
