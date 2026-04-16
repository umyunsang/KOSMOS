# SPDX-License-Identifier: Apache-2.0
"""LLM-visible core tool definitions for the MVP two-tool surface — T028.

Defines ``GovAPITool`` registrations for ``resolve_location`` and ``lookup``.
Both tools carry ``is_core=True`` so they appear in the core prompt partition
and are exported via ``registry.export_core_tools_openai()``.

FR-001: The LLM sees exactly two tools: resolve_location and lookup.
SC-003: All adapter details are hidden; the LLM only interacts with this surface.
"""

from __future__ import annotations

from pydantic import RootModel

from kosmos.tools.models import (
    GovAPITool,
    LookupSearchInput,
    ResolveLocationInput,
)

# ---------------------------------------------------------------------------
# Minimal output schema placeholders
# ---------------------------------------------------------------------------
# The actual output types are discriminated unions defined in models.py.
# GovAPITool.output_schema must be a type[BaseModel]; we use RootModel wrappers
# so we can pass the full union output as-is without breaking the registry.


class _ResolveLocationOutput(RootModel[object]):
    """Placeholder output schema for resolve_location tool registration."""


class _LookupOutput(RootModel[object]):
    """Placeholder output schema for lookup tool registration."""


# ---------------------------------------------------------------------------
# resolve_location core tool definition (T028)
# ---------------------------------------------------------------------------

RESOLVE_LOCATION_TOOL = GovAPITool(
    id="resolve_location",
    name_ko="위치 정보 조회",
    provider="KOSMOS",
    category=["위치", "지오코딩", "행정구역"],
    endpoint="internal://resolve_location",
    auth_type="public",
    input_schema=ResolveLocationInput,
    output_schema=_ResolveLocationOutput,
    llm_description=(
        "Convert a free-text Korean place name, address, or landmark into structured "
        "location identifiers (coordinates, 10-digit 행정동 code, road address, POI).\n\n"
        "ALWAYS call this tool first before calling lookup(mode='fetch') on any "
        "location-dependent adapter such as koroad_accident_hazard_search.\n\n"
        "want options:\n"
        "  - 'coords_and_admcd' (default): returns lat/lon + 10-digit adm_cd bundle\n"
        "  - 'adm_cd': returns only the 10-digit 행정동 administrative code\n"
        "  - 'coords': returns lat/lon with confidence level\n"
        "  - 'road_address' / 'jibun_address': returns structured address\n"
        "  - 'poi': returns the nearest point-of-interest match\n"
        "  - 'all': returns all of the above in a ResolveBundle\n\n"
        "Examples: query='서울 강남구', want='adm_cd' → '1168000000'"
    ),
    search_hint=(
        "위치 조회 주소 변환 행정동 코드 좌표 지오코딩 POI 장소 검색 "
        "resolve location address geocode coordinates adm_cd administrative code place"
    ),
    requires_auth=False,
    is_personal_data=False,
    is_concurrency_safe=True,
    cache_ttl_seconds=300,
    rate_limit_per_minute=60,
    is_core=True,
)


# ---------------------------------------------------------------------------
# lookup core tool definition (T028)
# ---------------------------------------------------------------------------

LOOKUP_SEARCH_TOOL = GovAPITool(
    id="lookup",
    name_ko="데이터 조회",
    provider="KOSMOS",
    category=["시스템", "도구검색", "데이터조회"],
    endpoint="internal://lookup",
    auth_type="public",
    input_schema=LookupSearchInput,
    output_schema=_LookupOutput,
    llm_description=(
        "Two-mode tool for discovering and invoking KOSMOS data adapters.\n\n"
        "MODE 1 — search (mode='search'):\n"
        "  BM25-ranked discovery over the adapter registry. Returns ranked candidates "
        "  with tool_id, required_params, and search_hint.\n"
        "  Use this FIRST to discover what tools are available for the user's request.\n"
        '  Example: {"mode": "search", "query": "교통사고 위험지역"}\n\n'
        "MODE 2 — fetch (mode='fetch'):\n"
        "  Invokes a specific adapter by tool_id. The params dict must match the "
        "  adapter's input_schema exactly. tool_id MUST come from a prior search result.\n"
        "  Example: {\n"
        '    "mode": "fetch",\n'
        '    "tool_id": "koroad_accident_hazard_search",\n'
        '    "params": {"adm_cd": "1168000000", "year": 2024}\n'
        "  }\n\n"
        "ORDERING RULE: search → fetch. Never guess a tool_id; always search first."
    ),
    search_hint=(
        "데이터 조회 도구 호출 검색 패치 lookup search fetch invoke tool adapter data query"
    ),
    requires_auth=False,
    is_personal_data=False,
    is_concurrency_safe=True,
    cache_ttl_seconds=0,
    rate_limit_per_minute=60,
    is_core=True,
)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_mvp_surface(registry: object) -> None:
    """Register the MVP LLM-visible core tools (resolve_location + lookup).

    These tools are NOT bound to executor adapters because their invocation
    is handled directly by the KOSMOS orchestrator loop, not via
    ToolExecutor.invoke(). Registration here ensures they appear in
    registry.core_tools() and registry.export_core_tools_openai().

    Args:
        registry: A ToolRegistry instance.
    """
    from kosmos.tools.registry import ToolRegistry

    assert isinstance(registry, ToolRegistry)

    registry.register(RESOLVE_LOCATION_TOOL)
    registry.register(LOOKUP_SEARCH_TOOL)
