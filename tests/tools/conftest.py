"""Shared pytest fixtures for the KOSMOS Tool System module.

All tests use mock tools — no live API calls are made here.
Imports from kosmos.tools resolve once Phase 3 implementation is complete.
"""

import pytest
from pydantic import BaseModel

from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Schema stubs used across tool tests
# ---------------------------------------------------------------------------


class MockInput(BaseModel):
    """Minimal input schema for weather-style tool tests."""

    city: str
    date: str | None = None


class MockOutput(BaseModel):
    """Minimal output schema for weather-style tool tests."""

    temperature: float
    condition: str
    humidity: int


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_tool_factory():
    """Return a factory that creates GovAPITool instances with sensible defaults.

    Callers may override any field by passing keyword arguments.
    Korean values (name_ko, provider, category, search_hint) are domain data
    and are intentionally kept in Korean.
    """

    def _factory(
        id: str = "kma_weather_forecast",  # noqa: A002
        name_ko: str = "날씨예보",
        provider: str = "기상청",
        category: list[str] | None = None,
        endpoint: str = "http://apis.data.go.kr/test",
        auth_type: str = "api_key",
        search_hint: str = "날씨 예보 weather forecast 기상청",
        **overrides,
    ) -> GovAPITool:
        return GovAPITool(
            id=id,
            name_ko=name_ko,
            provider=provider,
            category=category or ["날씨", "기상"],
            endpoint=endpoint,
            auth_type=auth_type,
            input_schema=MockInput,
            output_schema=MockOutput,
            search_hint=search_hint,
            **overrides,
        )

    return _factory


@pytest.fixture
def sample_tool(sample_tool_factory) -> GovAPITool:
    """A single pre-built GovAPITool instance using factory defaults."""
    return sample_tool_factory()


@pytest.fixture
def mock_tool_adapter():
    """A mock async adapter function that returns a fixed weather payload.

    Returned dict mirrors MockOutput field names so callers can validate
    output_schema parsing in integration tests.
    """

    async def _adapter(validated_input):
        return {"temperature": 22.5, "condition": "맑음", "humidity": 45}

    return _adapter


@pytest.fixture
def populated_registry(sample_tool_factory) -> ToolRegistry:
    """A ToolRegistry pre-loaded with 4 diverse tools for search/filter tests.

    Tools cover weather, traffic, health, and business domains so that
    category-based and keyword-based search tests can exercise distinct results.
    """
    registry = ToolRegistry()

    # 1. Weather forecast — core tool, marked as core=True
    weather = sample_tool_factory(
        id="kma_weather_forecast",
        name_ko="날씨예보",
        provider="기상청",
        category=["날씨", "기상"],
        search_hint="날씨 예보 weather forecast 기상청",
        core=True,
    )

    # 2. Traffic accident statistics
    traffic = sample_tool_factory(
        id="koroad_accident_stats",
        name_ko="교통사고통계",
        provider="도로교통공단",
        category=["교통", "사고"],
        endpoint="http://apis.data.go.kr/koroad/accident",
        search_hint="교통사고 통계 traffic accident road safety",
    )

    # 3. Hospital information lookup
    hospital = sample_tool_factory(
        id="hira_hospital_info",
        name_ko="병원정보조회",
        provider="건강보험심사평가원",
        category=["의료", "병원"],
        endpoint="http://apis.data.go.kr/hira/hospital",
        search_hint="병원 의원 의료기관 hospital clinic HIRA",
    )

    # 4. Business registration lookup
    business = sample_tool_factory(
        id="nts_business_registration",
        name_ko="사업자등록정보조회",
        provider="국세청",
        category=["사업자", "세금"],
        endpoint="http://apis.data.go.kr/nts/business",
        search_hint="사업자등록 법인 business registration NTS tax",
    )

    for tool in (weather, traffic, hospital, business):
        registry.register(tool)

    return registry
