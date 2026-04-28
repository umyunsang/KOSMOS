# SPDX-License-Identifier: Apache-2.0
"""KMA weather pre-warning list adapter (기상예비특보목록 조회).

Wraps the ``getWthrPwnList`` endpoint from the Korea Meteorological Administration
(기상청) via the shared data.go.kr service key.
Returns a list of pre-warning (예비특보) announcements that precede formal
weather warnings, providing early notification of developing weather events.

Wire format quirks handled by this module:
  - Single-item response returns ``item`` as a dict (not array) — normalized to list.
  - XML is the default; JSON is requested via ``_type=json`` and ``dataType=JSON``.
  - ``resultCode != "00"`` is always an error regardless of HTTP 200.
  - ``resultCode == "03"`` means no data — returns empty list, not an error.
  - Wire fields use camelCase; output model fields use snake_case.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.errors import ToolExecutionError, _require_env
from kosmos.tools.executor import ToolExecutor
from datetime import datetime, timezone

from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrPwnList"

# ---------------------------------------------------------------------------
# Input / Output models
# ---------------------------------------------------------------------------


class KmaPreWarningInput(BaseModel):
    """Input parameters for the KMA weather pre-warning list (기상예비특보목록) API."""

    model_config = ConfigDict(frozen=True)

    num_of_rows: int = Field(default=100, ge=1)
    """Number of rows per page (numOfRows wire parameter)."""

    page_no: int = Field(default=1, ge=1)
    """Page number, 1-indexed (pageNo wire parameter)."""

    stn_id: str | None = None
    """Station/region ID filter (optional).

    Filters results to a specific KMA station. See the KMA station code table
    for valid values (e.g., '108' for Seoul, '159' for Busan).
    If omitted, results from all stations are returned.
    """

    data_type: Literal["JSON", "XML"] = "JSON"
    """Response format (dataType wire parameter)."""


class PreWarningItem(BaseModel):
    """A single pre-warning announcement from KMA getWthrPwnList."""

    model_config = ConfigDict(frozen=True)

    stn_id: str
    """Station/region ID that issued the pre-warning."""

    title: str
    """Announcement title (e.g., '[예비] 제06-7호 : 2017.06.07.07:30')."""

    tm_fc: str
    """Announcement time in YYYYMMDDHHMI format."""

    tm_seq: int
    """Monthly sequence number of this announcement."""


class KmaPreWarningOutput(BaseModel):
    """Output from the kma_pre_warning tool."""

    model_config = ConfigDict(frozen=True)

    total_count: int
    """Total number of pre-warning items available."""

    items: list[PreWarningItem]
    """Pre-warning announcement items for the requested page."""


# ---------------------------------------------------------------------------
# Response normalization helpers
# ---------------------------------------------------------------------------


def _normalize_items(raw: object) -> list[dict[str, Any]]:
    """Normalize the ``items.item`` value from the KMA wire response.

    The KMA API returns:
    - A list of dicts when multiple results are found.
    - A single dict (not wrapped in a list) when exactly one result is found.
    - An empty string, None, or missing key when no results are found.

    Args:
        raw: The raw value of ``response.body.items.item``.

    Returns:
        A list of item dicts. Empty list for no-data responses.
    """
    if not raw:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return raw
    logger.warning(
        "Unexpected items type %s from KMA pre-warning API; treating as empty", type(raw)
    )
    return []


def _parse_response(raw: dict[str, Any]) -> KmaPreWarningOutput:
    """Parse the full KMA getWthrPwnList JSON response body into a KmaPreWarningOutput.

    Args:
        raw: Parsed JSON dict from the KMA API.

    Returns:
        Validated KmaPreWarningOutput with announcement items.

    Raises:
        ToolExecutionError: If resultCode is not "00" or "03".
    """
    header = raw.get("response", {}).get("header", {})
    result_code = str(header.get("resultCode", ""))
    result_msg = str(header.get("resultMsg", "Unknown error"))

    # Code "03" means NO_DATA — no active pre-warnings.  This is a
    # legitimate empty result (common when no weather events are developing).
    if result_code == "03":
        logger.info("KMA pre-warning: no pre-warnings available (resultCode=03)")
        return KmaPreWarningOutput(total_count=0, items=[])

    if result_code != "00":
        raise ToolExecutionError(
            "kma_pre_warning",
            f"KMA API returned error: code={result_code!r} msg={result_msg!r}",
        )

    body = raw.get("response", {}).get("body", {})
    total_count = int(str(body.get("totalCount", 0)))

    # items may be {"item": [...]} or {"item": {}} or "" or missing
    raw_items_container = body.get("items", {})
    if isinstance(raw_items_container, str) or not raw_items_container:
        item_list: list[dict[str, Any]] = []
    else:
        raw_item = raw_items_container.get("item", [])
        item_list = _normalize_items(raw_item)

    parsed_items: list[PreWarningItem] = []
    for wire_item in item_list:
        parsed_items.append(
            PreWarningItem(
                stn_id=str(wire_item.get("stnId", "")),
                title=str(wire_item.get("title", "")),
                tm_fc=str(wire_item.get("tmFc", "")),
                tm_seq=int(str(wire_item.get("tmSeq", 0))),
            )
        )

    return KmaPreWarningOutput(total_count=total_count, items=parsed_items)


# ---------------------------------------------------------------------------
# Async adapter function
# ---------------------------------------------------------------------------


async def _call(
    inp: KmaPreWarningInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Async adapter for kma_pre_warning.

    Fetches pre-warning announcement list data from the KMA getWthrPwnList endpoint.
    Handles JSON vs. XML content-type guard, error code mapping, and response parsing.

    Args:
        inp: Validated input parameters.
        client: Optional httpx.AsyncClient for test injection. If None, a new
                client is created for this call.

    Returns:
        A plain dict matching KmaPreWarningOutput schema.

    Raises:
        ConfigurationError: If KOSMOS_DATA_GO_KR_API_KEY is not set.
        ToolExecutionError: If the API returns a non-"00" result code or XML response.
    """
    api_key = _require_env("KOSMOS_DATA_GO_KR_API_KEY")

    params: dict[str, str | int] = {
        "serviceKey": api_key,
        "numOfRows": inp.num_of_rows,
        "pageNo": inp.page_no,
        "dataType": inp.data_type,
        "_type": "json",
    }

    if inp.stn_id is not None:
        params["stnId"] = inp.stn_id

    own_client = client is None
    _client: httpx.AsyncClient = httpx.AsyncClient() if own_client else client  # type: ignore[assignment]
    assert _client is not None  # narrow: either injected or freshly created above

    try:
        logger.debug(
            "Calling KMA getWthrPwnList: numOfRows=%s pageNo=%s stnId=%s",
            inp.num_of_rows,
            inp.page_no,
            inp.stn_id,
        )
        response = await _client.get(_BASE_URL, params=params, timeout=30.0)
        response.raise_for_status()

        # XML fallback guard: some data.go.kr endpoints ignore _type=json
        content_type = response.headers.get("content-type", "")
        if "xml" in content_type.lower() and "json" not in content_type.lower():
            raise ToolExecutionError(
                "kma_pre_warning",
                f"KMA API returned XML instead of JSON (Content-Type: {content_type!r}). "
                "Add Accept: application/json header or check _type parameter.",
            )

        raw = response.json()
        output = _parse_response(raw)
        return output.model_dump()

    finally:
        if own_client:
            await _client.aclose()


# ---------------------------------------------------------------------------
# Tool definition and registration helper
# ---------------------------------------------------------------------------

KMA_PRE_WARNING_TOOL = GovAPITool(
    id="kma_pre_warning",
    name_ko="기상예비특보목록 조회",
    ministry="KMA",
    category=["기상", "예비특보", "특보"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=KmaPreWarningInput,
    output_schema=KmaPreWarningOutput,
    search_hint=(
        "기상예비특보 예비특보 태풍예고 호우예고 대설예고 한파예고 폭염예고 강풍예고 "
        "weather pre-warning preliminary alert typhoon heavy-rain snow cold-wave heat wind"
    ),
    policy=AdapterRealDomainPolicy(
        real_classification_url="https://www.kma.go.kr/data/policy.html",
        real_classification_text="기상청 공공데이터 이용약관 — 기상특보 데이터 비상업적 공공 이용 허가",  # TODO: verify URL
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    ),
    is_concurrency_safe=True,
    cache_ttl_seconds=300,
    rate_limit_per_minute=10,
    is_core=True,
    primitive="lookup",
    trigger_examples=[
        "오늘 서울 호우주의 예비특보",
        "태풍 예비특보",
    ],
)


def register(registry: ToolRegistry, executor: ToolExecutor) -> None:
    """Register KMA pre-warning tool and its adapter.

    Args:
        registry: A ToolRegistry instance.
        executor: A ToolExecutor instance.
    """
    from typing import cast

    from kosmos.tools.executor import AdapterFn

    registry.register(KMA_PRE_WARNING_TOOL)
    executor.register_adapter("kma_pre_warning", cast(AdapterFn, _call))
    logger.info("Registered tool: kma_pre_warning")
