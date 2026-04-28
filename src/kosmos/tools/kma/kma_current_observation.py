# SPDX-License-Identifier: Apache-2.0
"""KMA ultra-short-term current observation adapter (초단기실황 관측).

The KMA getUltraSrtNcst endpoint returns observations as a list of pivot rows,
where each row has a ``{category, obsrValue}`` pair rather than returning a flat
object.  This module flattens those rows into a single ``KmaCurrentObservationOutput``
model via ``_pivot_rows_to_output``.

Special case: RN1 (1-hour precipitation) can arrive as the string ``"-"`` when
no precipitation has been measured.  The ``rn1`` field validator normalises that
sentinel — along with ``None`` and ``""`` — to ``0.0`` so downstream consumers
always receive a numeric value.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from kosmos.tools.errors import ConfigurationError, ToolExecutionError, _require_env
from kosmos.tools.executor import ToolExecutor
from datetime import datetime, timezone

from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"

# ---------------------------------------------------------------------------
# Input / Output models
# ---------------------------------------------------------------------------


class KmaCurrentObservationInput(BaseModel):
    """Input parameters for the KMA ultra-short-term current observation API."""

    model_config = ConfigDict(frozen=True)

    base_date: str
    """Observation base date in YYYYMMDD format."""

    base_time: str
    """Observation base time in HHMM format; rounded down to the nearest hour."""

    nx: int = Field(..., ge=1, le=149)
    """KMA grid X coordinate (1–149)."""

    ny: int = Field(..., ge=1, le=253)
    """KMA grid Y coordinate (1–253)."""

    num_of_rows: int = Field(default=10, ge=1)
    """Number of rows to return per page."""

    page_no: int = Field(default=1, ge=1)
    """Page number (1-based)."""

    data_type: Literal["JSON", "XML"] = "JSON"
    """Response format; JSON is strongly preferred."""

    @field_validator("base_date")
    @classmethod
    def _validate_base_date(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError(f"base_date must be YYYYMMDD, got {v!r}")
        return v

    @field_validator("base_time")
    @classmethod
    def _normalize_base_time(cls, v: str) -> str:
        """Round down to the nearest hour to avoid 'data not ready' errors."""
        if not re.fullmatch(r"\d{4}", v):
            raise ValueError(f"base_time must be HHMM, got {v!r}")
        return v[:2] + "00"


class KmaCurrentObservationOutput(BaseModel):
    """Flat observation record produced by pivoting KMA category rows."""

    model_config = ConfigDict(frozen=True)

    base_date: str
    """Observation date YYYYMMDD."""

    base_time: str
    """Observation time HHMM."""

    nx: int
    """Grid X coordinate."""

    ny: int
    """Grid Y coordinate."""

    t1h: float | None = None
    """Temperature in degrees Celsius."""

    rn1: float = 0.0
    """1-hour accumulated precipitation in millimetres (0.0 when no precipitation)."""

    uuu: float | None = None
    """East-west wind component in m/s (positive = eastward)."""

    vvv: float | None = None
    """North-south wind component in m/s (positive = northward)."""

    wsd: float | None = None
    """Wind speed in m/s."""

    reh: float | None = None
    """Relative humidity in percent."""

    pty: int = 0
    """Precipitation type code.

    0=none, 1=rain, 2=rain+snow, 3=snow, 5=drizzle, 6=drizzle+snow, 7=snow flurry.
    """

    vec: float | None = None
    """Wind direction in degrees (0–360, meteorological convention)."""

    @field_validator("rn1", mode="before")
    @classmethod
    def _normalize_rn1(cls, v: object) -> float:
        """Normalise sentinel precipitation values to 0.0.

        The KMA API uses ``"-"`` to indicate that no precipitation was observed.
        This validator converts ``"-"``, ``None``, and ``""`` to ``0.0`` so that
        all consumers receive a numeric value.
        """
        if v is None or v == "" or v == "-":
            return 0.0
        return float(v)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_items(raw: object) -> list[dict[str, object]]:
    """Coerce the KMA items payload into a plain list of dicts.

    The KMA API returns ``items.item`` as either a list (multiple rows) or a
    single dict (one row).  An empty / missing value yields an empty list.
    """
    if not raw:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    return []


def _pivot_rows_to_output(items: list[dict[str, object]]) -> KmaCurrentObservationOutput:
    """Pivot a list of KMA observation rows into a flat output model.

    Each row in *items* is expected to contain:
    ``baseDate``, ``baseTime``, ``nx``, ``ny``, ``category``, ``obsrValue``.

    Recognised categories: T1H, RN1, UUU, VVV, WSD, REH, PTY, VEC.
    Unknown categories are silently ignored.

    Args:
        items: List of raw row dicts from the API ``items.item`` field.

    Returns:
        A fully populated ``KmaCurrentObservationOutput`` instance.
    """
    first = items[0]
    base_date = str(first["baseDate"])
    base_time = str(first["baseTime"])
    nx = int(str(first["nx"]))
    ny = int(str(first["ny"]))

    category_map: dict[str, object] = {}
    for row in items:
        cat = str(row["category"]).upper()
        val = row["obsrValue"]
        category_map[cat] = val

    def _opt_float(key: str) -> float | None:
        raw = category_map.get(key)
        if raw is None or raw == "" or raw == "-":
            return None
        return float(str(raw))

    return KmaCurrentObservationOutput(
        base_date=base_date,
        base_time=base_time,
        nx=nx,
        ny=ny,
        t1h=_opt_float("T1H"),
        rn1=category_map.get("RN1", 0.0),  # type: ignore[arg-type]  # field_validator normalises
        uuu=_opt_float("UUU"),
        vvv=_opt_float("VVV"),
        wsd=_opt_float("WSD"),
        reh=_opt_float("REH"),
        pty=int(str(category_map.get("PTY", 0))),
        vec=_opt_float("VEC"),
    )


def _parse_response(payload: dict[str, object]) -> KmaCurrentObservationOutput:
    """Parse a full KMA getUltraSrtNcst JSON response.

    Args:
        payload: Decoded JSON dict from the API.

    Returns:
        A validated ``KmaCurrentObservationOutput``.

    Raises:
        ToolExecutionError: If the API returned a non-zero result code or the
            response structure is unexpected.
    """
    try:
        response = cast(dict[str, object], payload["response"])
        header = cast(dict[str, object], response["header"])
        result_code: str = str(header["resultCode"])
        result_msg: str = str(header.get("resultMsg", ""))

        if result_code != "00":
            raise ToolExecutionError(
                tool_id="kma_current_observation",
                message=(f"KMA API error: resultCode={result_code!r} resultMsg={result_msg!r}"),
            )

        body = cast(dict[str, object], response["body"])
        items_container = cast(dict[str, object], body["items"])
        raw_items = items_container["item"]
        items = _normalize_items(raw_items)

        if not items:
            raise ToolExecutionError(
                tool_id="kma_current_observation",
                message="KMA API returned an empty items list.",
            )

        return _pivot_rows_to_output(items)

    except ToolExecutionError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ToolExecutionError(
            tool_id="kma_current_observation",
            message=f"Unexpected KMA response structure: {exc}",
            cause=exc,
        ) from exc


# ---------------------------------------------------------------------------
# Adapter callable
# ---------------------------------------------------------------------------


async def _call(
    params: KmaCurrentObservationInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Fetch ultra-short-term current observations from the KMA API.

    Args:
        params: Validated input parameters.
        client: Optional injected ``httpx.AsyncClient`` (for testing).

    Returns:
        A plain dict matching ``KmaCurrentObservationOutput`` field names.

    Raises:
        ConfigurationError: If ``KOSMOS_DATA_GO_KR_API_KEY`` is not set.
        ToolExecutionError: On HTTP errors or unexpected API response shapes.
    """
    api_key = _require_env("KOSMOS_DATA_GO_KR_API_KEY")

    if params.data_type == "XML":
        raise ToolExecutionError(
            tool_id="kma_current_observation",
            message="XML data_type is not supported; use JSON.",
        )

    query_params: dict[str, str | int] = {
        "serviceKey": api_key,
        "base_date": params.base_date,
        "base_time": params.base_time,
        "nx": params.nx,
        "ny": params.ny,
        "numOfRows": params.num_of_rows,
        "pageNo": params.page_no,
        "dataType": params.data_type,
        "_type": "json",
    }

    logger.debug(
        "KMA observation request: base_date=%s base_time=%s nx=%d ny=%d",
        params.base_date,
        params.base_time,
        params.nx,
        params.ny,
    )

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        assert client is not None  # noqa: S101 — guaranteed by branch above
        response = await client.get(
            _BASE_URL,
            params=query_params,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "xml" in content_type.lower():
            raise ToolExecutionError(
                tool_id="kma_current_observation",
                message=(
                    f"Unexpected XML response from KMA API "
                    f"(content-type={content_type!r}). "
                    "Check serviceKey validity."
                ),
            )

        payload: dict[str, object] = response.json()
        output = _parse_response(payload)

        logger.info(
            "KMA observation retrieved: base_date=%s base_time=%s nx=%d ny=%d t1h=%s",
            output.base_date,
            output.base_time,
            output.nx,
            output.ny,
            output.t1h,
        )
        return output.model_dump()

    except (ToolExecutionError, ConfigurationError):
        raise
    except httpx.HTTPStatusError as exc:
        raise ToolExecutionError(
            tool_id="kma_current_observation",
            message=f"HTTP error from KMA API: {exc.response.status_code}",
            cause=exc,
        ) from exc
    except httpx.RequestError as exc:
        raise ToolExecutionError(
            tool_id="kma_current_observation",
            message=f"Network error reaching KMA API: {exc}",
            cause=exc,
        ) from exc
    finally:
        if own_client and client is not None:
            await client.aclose()


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

KMA_CURRENT_OBSERVATION_TOOL = GovAPITool(
    id="kma_current_observation",
    name_ko="초단기실황 관측 조회",
    ministry="KMA",
    category=["기상", "실황", "관측"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=KmaCurrentObservationInput,
    output_schema=KmaCurrentObservationOutput,
    search_hint=(
        "현재 날씨 기온 강수 습도 풍속 초단기실황 관측 "
        "current weather temperature precipitation humidity wind observation"
    ),
    policy=AdapterRealDomainPolicy(
        real_classification_url="https://www.kma.go.kr/data/policy.html",
        real_classification_text="기상청 공공데이터 이용약관 — 현재 날씨 관측 데이터 비상업적 공공 이용 허가",  # TODO: verify URL
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    ),
    is_concurrency_safe=True,
    cache_ttl_seconds=600,
    rate_limit_per_minute=10,
    is_core=True,
    primitive="lookup",
    trigger_examples=[
        "지금 서울 기온",
        "현재 풍속",
    ],
)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register(registry: ToolRegistry, executor: ToolExecutor) -> None:
    """Register the KMA current observation tool and its adapter.

    Args:
        registry: The central ``ToolRegistry`` to add the tool to.
        executor: The ``ToolExecutor`` to bind the adapter function to.
    """
    from kosmos.tools.executor import AdapterFn

    registry.register(KMA_CURRENT_OBSERVATION_TOOL)
    executor.register_adapter("kma_current_observation", cast(AdapterFn, _call))
    logger.info("Registered tool: kma_current_observation")
