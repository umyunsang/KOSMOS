# SPDX-License-Identifier: Apache-2.0
"""NFA (소방청) 구급정보서비스 adapter — interface-only stub.

Calls the NFA EmergencyInformationService endpoint for historical, anonymized
EMS statistics by region, fire station, and report year-month.

Epic δ #2295: citizen-facing gate = read-only (public emergency data).
The Layer 3 auth-gate in ``executor.invoke()`` short-circuits unauthenticated
calls to ``LookupError(reason="auth_required")`` before handle() is reached
(FR-025, FR-026, SC-006). handle() raises Layer3GateViolation as defence-in-depth.

# TODO: implement live HTTP handler after Layer 3 auth gate is provisioned
# (Epic #16 / #20).
"""

from __future__ import annotations

from datetime import datetime, timezone

import logging
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from kosmos.tools.errors import Layer3GateViolation
from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# T010 — NFA operation enum + input schema
# ---------------------------------------------------------------------------


class NfaEmgOperation(StrEnum):
    """Sub-endpoint selector for EmergencyInformationService."""

    activity = "getEmgencyActivityInfo"  # 구급활동정보 (default)
    transfer = "getEmgPatientTransferInfo"  # 구급환자이송정보
    condition = "getEmgPatientConditionInfo"  # 구급환자상태정보
    firstaid = "getEmgPatientFirstaidInfo"  # 구급환자응급처치정보
    vehicle_dispatch = "getEmgVehicleDispatchInfo"  # 구급차량출동정보
    vehicle_info = "getEmgVehicleInfo"  # 구급차량정보


class NfaEmergencyInfoServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: NfaEmgOperation = Field(
        default=NfaEmgOperation.activity,
        description=(
            "Which emergency-info sub-endpoint to query. "
            "Pass the NfaEmgOperation enum value string directly. "
            "Default 'getEmgencyActivityInfo' returns dispatch distance, patient "
            "symptoms, and crew qualifications — the most citizen-relevant view. "
            "Use 'getEmgPatientTransferInfo' for patient transport, "
            "'getEmgPatientConditionInfo' for vitals, "
            "'getEmgPatientFirstaidInfo' for treatment codes, "
            "'getEmgVehicleDispatchInfo' or 'getEmgVehicleInfo' for fleet data."
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
        default=1,
        ge=1,
        description="Page number (1-indexed). Default 1.",
    )
    num_of_rows: int = Field(
        default=10,
        ge=1,
        le=100,
        description=("Number of records per page. Default 10, maximum 100 per NFA API contract."),
    )
    result_type: Literal["json"] = Field(
        default="json",
        description=(
            "Response format. Fixed to 'json' — the adapter's Content-Type guard "
            "requires JSON to be requested. Do not override."
        ),
    )


# ---------------------------------------------------------------------------
# T011 — Per-operation output item models + envelope
# ---------------------------------------------------------------------------


class NfaActivityItem(BaseModel):
    """Single 구급활동정보 record (getEmgencyActivityInfo)."""

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


class NfaTransferItem(BaseModel):
    """Single 구급환자이송정보 record (getEmgPatientTransferInfo)."""

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


class NfaConditionItem(BaseModel):
    """Single 구급환자상태정보 record (getEmgPatientConditionInfo)."""

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


class NfaFirstaidItem(BaseModel):
    """Single 구급환자응급처치정보 record (getEmgPatientFirstaidInfo)."""

    model_config = ConfigDict(extra="allow", frozen=True)

    sidoHqOgidNm: str  # noqa: N815
    rsacGutFsttOgidNm: str  # noqa: N815
    stmtYm: str  # noqa: N815
    stmtHh: str | None = None  # noqa: N815
    ptntAge: str | None = None  # noqa: N815
    ptntSdtSeCdNm: str | None = None  # noqa: N815
    fstaCdNm: str | None = Field(default=None, description="응급처치코드")  # noqa: N815


class NfaVehicleDispatchItem(BaseModel):
    """Single 구급차량출동정보 record (getEmgVehicleDispatchInfo)."""

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


class NfaVehicleInfoItem(BaseModel):
    """Single 구급차량정보 record (getEmgVehicleInfo)."""

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


NfaItem = (
    NfaActivityItem
    | NfaTransferItem
    | NfaConditionItem
    | NfaFirstaidItem
    | NfaVehicleDispatchItem
    | NfaVehicleInfoItem
)


class NfaEmergencyInfoServiceOutput(BaseModel):
    """Normalized upstream response wrapper for EmergencyInformationService."""

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


# ---------------------------------------------------------------------------
# T012 — Interface-only stub, GovAPITool registration, and handle()
# ---------------------------------------------------------------------------


class _NfaEmergencyInfoServiceOutputStub(RootModel[dict[str, Any]]):
    """Placeholder output schema for GovAPITool registration.

    Real output shape is deferred until Layer 3 auth is provisioned (Epic #16/#20).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


NFA_EMERGENCY_INFO_SERVICE_TOOL = GovAPITool(
    id="nfa_emergency_info_service",
    name_ko="소방청 구급정보서비스 (구급활동 통계 조회)",
    ministry="NFA",
    category=["안전", "응급", "소방", "119", "구급통계"],
    endpoint="https://apis.data.go.kr/1661000/EmergencyInformationService",
    auth_type="api_key",
    input_schema=NfaEmergencyInfoServiceInput,
    output_schema=_NfaEmergencyInfoServiceOutputStub,  # RootModel[dict] stub
    llm_description=(
        "Query the NFA (소방청) emergency-activity records service for historical, "
        "anonymized EMS statistics by region, fire station, and report year-month. "
        "Returns dispatch distance, patient symptoms, and crew qualifications when "
        "operation='getEmgencyActivityInfo' (default). This is NOT a real-time 119 dispatch tool "
        "and does NOT return current-incident or facility-locator data. "
        "IMPORTANT: This is a read-only emergency info service — public data access."
    ),
    search_hint=(
        "119 구급 출동 소방청 구급정보 구급활동 구급차 통계 현황 소방서 긴급구조 "
        "119 NFA emergency ambulance dispatch activity statistics fire station Korea"
    ),
    policy=AdapterRealDomainPolicy(
        real_classification_url="https://www.nfa.go.kr/nfa/main/contents.do?menuKey=66",
        real_classification_text="소방청 공공데이터 이용약관 — 119 응급서비스 데이터 비상업적 공공 이용 허가",  # TODO: verify URL
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    ),
    is_concurrency_safe=True,
    cache_ttl_seconds=86400,
    rate_limit_per_minute=10,
    is_core=False,
    primitive="lookup",
    trigger_examples=[
        "심정지 응급 처치",
        "AED 위치 알려줘",
    ],
)


async def handle(inp: NfaEmergencyInfoServiceInput) -> dict[str, object]:
    """Defence-in-depth backstop — should never be reached.

    The Layer 3 auth-gate in executor.invoke() short-circuits on
    Epic δ #2295: auth gate based on policy.citizen_facing_gate (FR-025, FR-026, SC-006).

    # TODO: implement live HTTP handler after Layer 3 auth gate is provisioned
    # (Epic #16 / #20).

    Raises:
        Layer3GateViolation: Always — signals a programming error if reached.
    """
    raise Layer3GateViolation("nfa_emergency_info_service")


def register(registry: object, executor: object) -> None:
    """Register the NFA emergency info service tool and its adapter.

    Called by ``register_all.py`` at application startup.

    Args:
        registry: A ToolRegistry instance.
        executor: A ToolExecutor instance.
    """
    from kosmos.tools.executor import ToolExecutor  # noqa: PLC0415
    from kosmos.tools.registry import ToolRegistry  # noqa: PLC0415

    assert isinstance(registry, ToolRegistry)
    assert isinstance(executor, ToolExecutor)

    async def _adapter(inp: BaseModel) -> dict[str, Any]:
        assert isinstance(inp, NfaEmergencyInfoServiceInput)
        return await handle(inp)

    registry.register(NFA_EMERGENCY_INFO_SERVICE_TOOL)
    executor.register_adapter("nfa_emergency_info_service", _adapter)
    logger.info(
        "Registered tool: nfa_emergency_info_service (auth_required gate — interface-only stub)"
    )
