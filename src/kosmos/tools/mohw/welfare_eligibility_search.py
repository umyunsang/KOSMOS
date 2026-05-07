# SPDX-License-Identifier: Apache-2.0
"""MOHW welfare eligibility search adapter — Spec 2522 US4.

Calls the SSIS NationalWelfarelistV001 endpoint to return welfare services
matching life stage, household type, interest theme, age, or keyword.

T025: Real handle() implementation with camelCase wire params + UTF-8 XML parsing.
T026: callTp=L + srchKeyCode=003 auto-injected; never exposed in pydantic input.
T027: build_description_v4 5-section llm_description with MOHW_LIFE_STAGE_SHORT_REFERENCE.

Evidence: /tmp/kosmos-evidence/koroad-mohw-evidence.md (lifeArray=007 → 21 services live).
Wire format: UTF-8 XML per SSIS NationalWelfarelistV001 v2.2 §1.1.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any, Final, Literal, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.tools._description_template import build_description_v4
from kosmos.tools._outbound_trace import traced_async_client
from kosmos.tools.errors import ToolExecutionError, _require_env
from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool
from kosmos.tools.mohw._short_references import (
    MOHW_LIFE_STAGE_SHORT_REFERENCE,
    MOHW_TARGET_HOUSEHOLD_SHORT_REFERENCE,
)
from kosmos.tools.ssis.codes import (
    CallType,
    IntrsThemaCode,
    LifeArrayCode,
    OrderBy,
    SrchKeyCode,
    TrgterIndvdlCode,
)

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001"
)
_SINGLE_PARENT_PRECISION_TERMS: Final[tuple[str, ...]] = (
    "한부모",
    "조손",
    "아동양육비",
)
_SINGLE_PARENT_CHILD_SUPPORT_CANONICAL_SEARCH: Final[str] = "한부모가족 아동양육비"
_SINGLE_PARENT_CHILD_SUPPORT_ALIASES: Final[tuple[str, ...]] = (
    "한부모 아동양육비",
    "한부모아동양육비",
    "한부모가족아동양육비",
)


def _canonical_single_parent_child_support_search(search_wrd: str) -> str:
    compact = "".join(search_wrd.split())
    if search_wrd.strip() in _SINGLE_PARENT_CHILD_SUPPORT_ALIASES:
        return _SINGLE_PARENT_CHILD_SUPPORT_CANONICAL_SEARCH
    if compact in _SINGLE_PARENT_CHILD_SUPPORT_ALIASES:
        return _SINGLE_PARENT_CHILD_SUPPORT_CANONICAL_SEARCH
    return search_wrd


# ---------------------------------------------------------------------------
# Input schema (T025) — snake_case pydantic; camelCase mapping happens in handle()
# ---------------------------------------------------------------------------


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
    life_array: LifeArrayCode | None = Field(
        default=None,
        description=(
            "Life-stage filter. "
            "001=영유아 / 002=아동 / 003=청소년 / 004=청년 / "
            "005=중장년 / 006=노년 / 007=임신·출산. "
            "For 한부모/조손 child-support searches, omit this field and use "
            "trgter_indvdl_array='060'."
        ),
    )
    trgter_indvdl_array: TrgterIndvdlCode | None = Field(
        default=None,
        description=(
            "Target individual / household-type filter "
            "(010 다문화·탈북민, 020 다자녀, 030 보훈, 040 장애인, "
            "050 저소득, 060 한부모·조손). "
            "For 한부모/조손, use '060' here; do not put household type in life_array."
        ),
    )
    intrs_thema_array: IntrsThemaCode | None = Field(
        default=None,
        description=(
            "Interest-theme filter. Authoritative 임신·출산 code: '080'. '010' = 신체건강."
        ),
    )
    age: int | None = Field(
        default=None,
        ge=0,
        le=150,
        description=(
            "Citizen age in years for age-eligibility filtering. "
            "Do NOT request from the citizen without consent."
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
        default=1,
        ge=1,
        le=1000,
        description="Page number (1-indexed). SSIS caps at 1000.",
    )
    num_of_rows: int = Field(
        default=10,
        ge=1,
        le=500,
        description="Records per page. Default 10, maximum 500 per SSIS API contract.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_single_parent_child_support_search(cls, data: object) -> object:
        """Map common user-facing abbreviations to the SSIS-matching service term."""
        if not isinstance(data, dict):
            return data
        if str(data.get("trgter_indvdl_array") or "") != str(TrgterIndvdlCode.single_parent):
            return data
        search_wrd = data.get("search_wrd")
        if not isinstance(search_wrd, str):
            return data

        canonical = _canonical_single_parent_child_support_search(search_wrd)
        if canonical == search_wrd:
            return data
        normalized = dict(data)
        normalized["search_wrd"] = canonical
        return normalized

    @model_validator(mode="after")
    def reject_single_parent_life_stage_collision(self) -> Self:
        """Reject the SSIS filter combination proven to suppress valid records."""
        if (
            self.life_array is not None
            and self.trgter_indvdl_array == TrgterIndvdlCode.single_parent
            and self.search_wrd is not None
            and any(term in self.search_wrd for term in _SINGLE_PARENT_PRECISION_TERMS)
        ):
            raise ValueError(
                "For 한부모/조손 child-support searches, omit life_array; use "
                "trgter_indvdl_array='060' with search_wrd='아동양육비'. "
                "Direct curl evidence 2026-05-06: adding lifeArray=002 returns "
                "resultCode=40 NO DATA, while omitting lifeArray returns WLF00001068."
            )
        return self


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class SsisWelfareServiceItem(BaseModel):
    """Single welfare service record from NationalWelfarelistV001."""

    model_config = ConfigDict(extra="allow", frozen=True)

    servId: str = Field(description="서비스ID (e.g. 'WLF00000056')")  # noqa: N815
    servNm: str = Field(description="서비스명")  # noqa: N815
    jurMnofNm: str = Field(description="소관부처명 (ministry)")  # noqa: N815
    jurOrgNm: str | None = Field(default=None, description="소관조직명 (bureau)")  # noqa: N815
    inqNum: str | None = Field(default=None, description="조회수 (raw string)")  # noqa: N815
    servDgst: str | None = Field(default=None, description="서비스 요약")  # noqa: N815
    servDtlLink: str | None = Field(  # noqa: N815
        default=None, description="서비스 상세링크 (bokjiro.go.kr)"
    )
    svcfrstRegTs: str | None = Field(default=None, description="서비스등록일")  # noqa: N815
    lifeArray: str | None = Field(  # noqa: N815
        default=None, description="생애주기 (comma-separated names)"
    )
    intrsThemaArray: str | None = Field(default=None, description="관심주제")  # noqa: N815
    trgterIndvdlArray: str | None = Field(default=None, description="가구유형")  # noqa: N815
    sprtCycNm: str | None = Field(  # noqa: N815
        default=None, description="지원주기 (e.g. '1회성')"
    )
    srvPvsnNm: str | None = Field(  # noqa: N815
        default=None, description="제공유형 (e.g. '전자바우처')"
    )
    rprsCtadr: str | None = Field(default=None, description="문의처")  # noqa: N815
    onapPsbltYn: Literal["Y", "N"] | None = Field(  # noqa: N815
        default=None, description="온라인신청가능여부"
    )


class MohwWelfareEligibilitySearchOutput(BaseModel):
    """Documentation contract for the SSIS welfare-list response shape.

    Note: this strict schema is no longer the wire surface — the handler emits
    an envelope-ready ``{"kind": "collection", "items": [...], ...}`` dict so
    ``envelope.normalize()`` can wrap it as ``LookupCollection``. See module
    docstring + ``MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL.output_schema``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_code: str = Field(description="결과코드 ('0' = SUCCESS in SSIS v2.0)")
    result_message: str = Field(description="결과메세지")
    page_no: int
    num_of_rows: int
    total_count: int
    items: list[SsisWelfareServiceItem] = Field(
        description="List of welfare services matching the query."
    )


class _MohwPlaceholderOutput(BaseModel):
    """Placeholder GovAPITool.output_schema — handler returns envelope-ready dict.

    Permits any dict to flow through GovAPITool.output_schema validation; the
    real envelope check happens inside ``envelope.normalize`` against the
    discriminated ``LookupOutput`` union (FR-015).
    """

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# T025 / T026 — XML parser helpers
# ---------------------------------------------------------------------------

_TEXT_FIELDS = {
    "servId",
    "servNm",
    "jurMnofNm",
    "jurOrgNm",
    "inqNum",
    "servDgst",
    "servDtlLink",
    "svcfrstRegTs",
    "lifeArray",
    "intrsThemaArray",
    "trgterIndvdlArray",
    "sprtCycNm",
    "srvPvsnNm",
    "rprsCtadr",
    "onapPsbltYn",
}


def _clean_ssis_text(value: str) -> str:
    """Normalize government XML text before it reaches terminal captures."""
    return value.replace("\ufffd", "").strip()


def _parse_xml_response(xml_bytes: bytes) -> dict[str, Any]:
    """Parse SSIS NationalWelfarelistV001 UTF-8 XML response.

    Live SSIS envelope (verified 2026-05-04 with KOSMOS_DATA_GO_KR_API_KEY):
        <wantedList>
          <totalCount>15</totalCount>
          <pageNo>1</pageNo>
          <numOfRows>3</numOfRows>
          <resultCode>0</resultCode>
          <resultMessage>SUCCESS</resultMessage>
          <servList>            <!-- one per record, sibling of metadata -->
            <servId>WLF00000061</servId>
            <servNm>의료급여임신.출산진료비지원</servNm>
            ...
          </servList>
          <servList>...</servList>
        </wantedList>

    Historical envelope (older docs / NIA-IFT v2.2 §1.1, kept as fallback):
        <response>
          <servList>
            <servList>  <!-- nested wrapper -->
              <servId>…</servId>
            </servList>
          </servList>
        </response>

    Critical: the wrong-envelope assumption was the documented C-class root
    cause for citizen welfare mis-info on 2026-05-04 — the parser found
    ``totalCount=15`` but extracted zero items, the empty list flowed through
    output validation, the executor masked the resulting envelope mismatch as
    "Response processing failed.", and the LLM fabricated a 12-service welfare
    catalog including bokjiro.go.kr URLs that pointed at the wrong service IDs.
    """
    root = ET.fromstring(xml_bytes)  # noqa: S314 — SSIS is a trusted government source

    def _text_in(parent: ET.Element, tag: str) -> str:
        el = parent.find(tag)
        return _clean_ssis_text(el.text or "") if el is not None and el.text else ""

    result_code = _text_in(root, "resultCode")
    result_message = _text_in(root, "resultMessage")

    try:
        total_count = int(_text_in(root, "totalCount") or "0")
    except ValueError:
        total_count = 0
    try:
        page_no = int(_text_in(root, "pageNo") or "1")
    except ValueError:
        page_no = 1
    try:
        num_of_rows = int(_text_in(root, "numOfRows") or "10")
    except ValueError:
        num_of_rows = 10

    # Item discovery: support both the live live-envelope (servList siblings of
    # metadata under <wantedList>) and the legacy nested envelope where each
    # outer <servList> wraps an inner <servList>. The condition is "outer
    # contains an inner servList" → drill in; otherwise treat each direct
    # <servList> child of root as an item record.
    direct_serv_lists = root.findall("servList")
    item_elements: list[ET.Element]
    if direct_serv_lists and direct_serv_lists[0].find("servList") is not None:
        # Legacy nested shape — first outer wraps inner items.
        outer = direct_serv_lists[0]
        item_elements = outer.findall("servList")
    else:
        # Live flat shape — each direct <servList> is one record.
        item_elements = direct_serv_lists

    items: list[dict[str, Any]] = []
    for item_el in item_elements:
        item: dict[str, Any] = {}
        for field in _TEXT_FIELDS:
            el = item_el.find(field)
            if el is not None and el.text:
                item[field] = _clean_ssis_text(el.text)
            else:
                item[field] = None
        # servId and servNm are required — skip malformed items
        if item.get("servId") and item.get("servNm"):
            # Ensure required fields are non-None strings
            item["jurMnofNm"] = item.get("jurMnofNm") or ""
            items.append(item)

    return {
        "result_code": result_code,
        "result_message": result_message,
        "total_count": total_count,
        "page_no": page_no,
        "num_of_rows": num_of_rows,
        "items": items,
    }


# ---------------------------------------------------------------------------
# T025 / T026 — camelCase wire-param builder
# ---------------------------------------------------------------------------

# T026: callTp=L + srchKeyCode=003 are always injected; never in pydantic input.
_FIXED_CALL_TP: str = CallType.list_  # "L"
_FIXED_SRCH_KEY_CODE: str = SrchKeyCode.all_fields  # "003"


def _build_params(inp: MohwWelfareEligibilitySearchInput, api_key: str) -> dict[str, str]:
    """Build camelCase HTTP params from snake_case pydantic input (T025 + T026).

    T026 contract:
      - callTp=L  always added (not in pydantic input)
      - srchKeyCode=003  always added (not in pydantic input)
    """
    params: dict[str, str] = {
        "serviceKey": api_key,
        "callTp": _FIXED_CALL_TP,
        "srchKeyCode": _FIXED_SRCH_KEY_CODE,
        "pageNo": str(inp.page_no),
        "numOfRows": str(inp.num_of_rows),
        "orderBy": str(inp.order_by),
    }

    # Optional filters — only add when pydantic value is set
    if inp.search_wrd is not None:
        params["searchWrd"] = inp.search_wrd
    if inp.life_array is not None:
        params["lifeArray"] = str(inp.life_array)
    if inp.trgter_indvdl_array is not None:
        params["trgterIndvdlArray"] = str(inp.trgter_indvdl_array)
    if inp.intrs_thema_array is not None:
        params["intrsThemaArray"] = str(inp.intrs_thema_array)
    if inp.age is not None:
        params["age"] = str(inp.age)
    if inp.onap_psblt_yn is not None:
        params["onapPsbltYn"] = inp.onap_psblt_yn

    return params


# ---------------------------------------------------------------------------
# T025 — Real async handle()
# ---------------------------------------------------------------------------


async def handle(
    inp: MohwWelfareEligibilitySearchInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Invoke the SSIS NationalWelfarelistV001 endpoint and parse XML response.

    T025: Replaces the Layer3GateViolation stub with a real HTTP + XML parser.
    T026: callTp=L + srchKeyCode=003 auto-injected via _build_params().

    Args:
        inp: Validated MohwWelfareEligibilitySearchInput.
        client: Optional httpx.AsyncClient for test injection.

    Returns:
        A dict suitable for MohwWelfareEligibilitySearchOutput.model_validate().

    Raises:
        ConfigurationError: If KOSMOS_DATA_GO_KR_API_KEY is not set.
        ToolExecutionError: On upstream API errors or non-'0' resultCode.
    """
    api_key = _require_env("KOSMOS_DATA_GO_KR_API_KEY")
    params = _build_params(inp, api_key)

    logger.debug(
        "mohw_welfare_eligibility_search: life_array=%s page=%d rows=%d",
        inp.life_array,
        inp.page_no,
        inp.num_of_rows,
    )

    own_client = client is None
    _client: httpx.AsyncClient = (
        traced_async_client(timeout=30.0) if own_client else client  # type: ignore[assignment]
    )

    try:
        response = await _client.get(_BASE_URL, params=params)
        response.raise_for_status()
        xml_bytes = response.content
    finally:
        if own_client:
            await _client.aclose()

    try:
        parsed = _parse_xml_response(xml_bytes)
    except ET.ParseError as exc:
        raise ToolExecutionError(
            "mohw_welfare_eligibility_search",
            f"Failed to parse SSIS XML response: {exc}",
        ) from exc

    result_code = parsed.get("result_code", "")
    if result_code not in ("0", "00"):
        result_msg = parsed.get("result_message", "Unknown")
        raise ToolExecutionError(
            "mohw_welfare_eligibility_search",
            f"SSIS API error: resultCode={result_code!r} resultMessage={result_msg!r}",
        )

    # Envelope-ready dict for envelope.normalize() — kind="collection" matches
    # the LookupCollection variant of LookupOutput. Without the discriminator
    # the executor raises EnvelopeNormalizationError, masked as "Response
    # processing failed." to the LLM, triggering the C-class fabrication path
    # documented in the 2026-05-04 mis-info incident.
    return {
        "kind": "collection",
        "items": parsed.get("items", []),
        "total_count": parsed.get("total_count", 0),
    }


# ---------------------------------------------------------------------------
# T027 — 5-section llm_description via build_description_v4
# ---------------------------------------------------------------------------

_MOHW_DESCRIPTION = build_description_v4(
    purpose=(
        "Search the MOHW/SSIS central-ministry welfare-service catalog "
        "(bokjiro.go.kr) for services matching life stage, household type, "
        "interest theme, age, or keyword. "
        "Returns service name, ministry, summary, online-apply flag, and detail link."
    ),
    input_quirk=(
        "Key params (snake_case in LLM input → camelCase on wire): "
        "life_array→lifeArray, trgter_indvdl_array→trgterIndvdlArray, "
        "intrs_thema_array→intrsThemaArray, num_of_rows→numOfRows, page_no→pageNo. "
        "callTp=L and srchKeyCode=003 are auto-injected; do not set them."
    ),
    short_reference=(
        "[LIFE_ARRAY] "
        + MOHW_LIFE_STAGE_SHORT_REFERENCE
        + " [TARGET] "
        + MOHW_TARGET_HOUSEHOLD_SHORT_REFERENCE
    ),
    domain_quirk=(
        "Response is UTF-8 XML only (no JSON option). "
        "resultCode='0' = SUCCESS (SSIS v2.0 convention). "
        "onapPsbltYn='Y' → online application available at bokjiro.go.kr. "
        "No client-side cache (cache_ttl_seconds=0); SSIS catalog updates anytime."
    ),
    self_contained_decl=(
        "This tool is self-contained for catalog queries. "
        "No resolve_location prerequisite. "
        "For '임신·출산' welfare services use life_array='007'. "
        "For '한부모' welfare services use trgter_indvdl_array='060', not life_array; "
        "for child-support precision add search_wrd='아동양육비'. "
        "For online-only results add onap_psblt_yn='Y'. "
        "Combine life_array + intrs_thema_array (080 임신·출산) for best precision."
    ),
)

# ---------------------------------------------------------------------------
# GovAPITool registration object
# ---------------------------------------------------------------------------

MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL = GovAPITool(
    id="mohw_welfare_eligibility_search",
    name_ko="복지서비스 목록 조회 (한국사회보장정보원 SSIS)",
    ministry="MOHW",
    category=["복지", "출산", "의료비", "보조금", "사회보장"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=MohwWelfareEligibilitySearchInput,
    output_schema=_MohwPlaceholderOutput,
    llm_description=_MOHW_DESCRIPTION,
    search_hint=(
        "복지서비스 출산 보조금 복지혜택 신청 사회보장정보원 보건복지부 임산부 지원 "
        "한부모 조손 아동양육비 welfare benefit eligibility childbirth subsidy "
        "single parent child support MOHW SSIS social security Korea"
    ),
    policy=AdapterRealDomainPolicy(
        real_classification_url=(
            "https://www.mohw.go.kr/react/policy/index.jsp?PAR_MENU_ID=06&MENU_ID=06"
        ),
        real_classification_text=(
            "보건복지부 공공데이터 이용약관 — 복지서비스 적격 조회 데이터 비상업적 공공 이용 허가"
        ),
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 5, 2, tzinfo=UTC),
    ),
    is_concurrency_safe=True,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    is_core=False,
    primitive="lookup",
    trigger_examples=[
        "출산 보조금 뭐 있어?",
        "임산부 복지 혜택",
        "기초생활수급 신청",
    ],
)


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


def register(registry: object, executor: object) -> None:
    """Register the MOHW welfare eligibility search tool and its adapter.

    Called by ``register_all.py`` at application startup.
    """
    from kosmos.tools.executor import ToolExecutor  # noqa: PLC0415
    from kosmos.tools.registry import ToolRegistry  # noqa: PLC0415

    assert isinstance(registry, ToolRegistry)
    assert isinstance(executor, ToolExecutor)

    async def _adapter(inp: BaseModel) -> dict[str, Any]:
        assert isinstance(inp, MohwWelfareEligibilitySearchInput)
        return await handle(inp)

    registry.register(MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL)
    executor.register_adapter("mohw_welfare_eligibility_search", _adapter)
    logger.info(
        "Registered tool: mohw_welfare_eligibility_search "
        "(live XML handler; read-only gate; SSIS NationalWelfarelistV001)"
    )
