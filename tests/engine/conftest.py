# SPDX-License-Identifier: Apache-2.0
"""Shared test fixtures for the KOSMOS Query Engine test suite.

All fixtures use mocks only — no live API calls, no environment variables required.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from pydantic import BaseModel

from kosmos.engine.config import QueryEngineConfig
from kosmos.llm.models import ChatMessage, StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal Pydantic schemas shared across mock tool definitions
# ---------------------------------------------------------------------------


class MockInput(BaseModel):
    """Minimal input schema for mock government API tools."""

    query: str


class MockOutput(BaseModel):
    """Minimal output schema for mock government API tools."""

    result: str


# ---------------------------------------------------------------------------
# Helper: build a GovAPITool with sensible mock defaults
# ---------------------------------------------------------------------------


def _make_tool(
    tool_id: str,
    name_ko: str,
    *,
    is_core: bool = False,
    requires_auth: bool = False,
    is_personal_data: bool = False,
    is_concurrency_safe: bool = False,
) -> GovAPITool:
    """Return a GovAPITool instance with MockInput/MockOutput schemas.

    Maintains spec-024 V5 biconditional ``auth_level=='public' ⇔ requires_auth==False``
    and FR-038 PII ⇒ auth by deriving ``auth_level`` + ``pipa_class`` from the
    ``requires_auth`` / ``is_personal_data`` flags.
    """
    # V6 (FR-039/FR-040): auth_type must be consistent with auth_level.
    #   public   → {public, AAL1}
    #   api_key  → {AAL1, AAL2, AAL3}
    if is_personal_data:
        auth_level = "AAL2"
        pipa_class = "personal"
        dpa_reference = "dpa-mock-engine-conftest"
        auth_type = "api_key"
    elif requires_auth:
        auth_level = "AAL1"
        pipa_class = "non_personal"
        dpa_reference = None
        auth_type = "public"
    else:
        auth_level = "public"
        pipa_class = "non_personal"
        dpa_reference = None
        auth_type = "public"
    return GovAPITool(
        id=tool_id,
        name_ko=name_ko,
        provider="mock_provider",
        category=["mock"],
        endpoint="https://mock.example.com/api",
        auth_type=auth_type,
        input_schema=MockInput,
        output_schema=MockOutput,
        search_hint=f"{name_ko} mock tool for testing",
        auth_level=auth_level,
        pipa_class=pipa_class,
        is_irreversible=False,
        dpa_reference=dpa_reference,
        is_core=is_core,
        requires_auth=requires_auth,
        is_personal_data=is_personal_data,
        is_concurrency_safe=is_concurrency_safe,
        cache_ttl_seconds=0,
        rate_limit_per_minute=60,
    )


# Pre-built mock tool instances reused across fixtures.
_TRAFFIC_ACCIDENT_TOOL = _make_tool(
    "traffic_accident_search",
    "교통사고 검색",
    is_core=True,
    is_concurrency_safe=True,
)
_WEATHER_INFO_TOOL = _make_tool(
    "weather_info",
    "날씨 정보",
    is_core=True,
    is_concurrency_safe=True,
)
_CIVIL_PETITION_TOOL = _make_tool(
    "civil_petition_status",
    "민원 처리 현황",
    is_core=True,
    is_concurrency_safe=False,  # not concurrency-safe
)
_RESIDENT_REGISTRATION_TOOL = _make_tool(
    "resident_registration",
    "주민등록 정보",
    is_core=False,
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
)

_ALL_MOCK_TOOLS = [
    _TRAFFIC_ACCIDENT_TOOL,
    _WEATHER_INFO_TOOL,
    _CIVIL_PETITION_TOOL,
    _RESIDENT_REGISTRATION_TOOL,
]

# ---------------------------------------------------------------------------
# MockLLMClient — mimics LLMClient interface using pre-configured StreamEvent
# sequences.  Each call consumes the next response in the list; once exhausted
# the last response is repeated (safe for "infinite-tools" scenarios).
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Drop-in mock for LLMClient that replays pre-configured StreamEvent lists.

    Args:
        responses: Ordered list of StreamEvent sequences.  Each stream() call
                   consumes the next list; the last list is repeated when all
                   have been consumed.
        budget: Token budget forwarded to an internal UsageTracker.
    """

    def __init__(
        self,
        responses: list[list[StreamEvent]],
        budget: int = 100_000,
    ) -> None:
        self._responses = responses
        self._call_index = 0
        self._usage = UsageTracker(budget=budget)
        self.last_messages: list[ChatMessage] | None = None
        self.call_count: int = 0

    @property
    def usage(self) -> UsageTracker:
        """Current session usage tracker."""
        return self._usage

    async def stream(
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        """Yield pre-configured StreamEvent objects for the current call index."""
        self.last_messages = list(messages)
        self.call_count += 1
        events = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        for event in events:
            yield event


# ---------------------------------------------------------------------------
# Pre-built StreamEvent sequences
# ---------------------------------------------------------------------------

# --- Call 1: single tool call for traffic_accident_search ---
_TOOL_CALL_EVENTS: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_001",
        function_name="traffic_accident_search",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta='{"query": "서울 강남구 교통사고"}',
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=100, output_tokens=50),
    ),
    StreamEvent(type="done"),
]

# --- Call 2: text answer ---
_TEXT_ANSWER_EVENTS: list[StreamEvent] = [
    StreamEvent(
        type="content_delta",
        content="서울 강남구 교통사고 현황입니다.",
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=200, output_tokens=100),
    ),
    StreamEvent(type="done"),
]

# --- No-tool: direct greeting response ---
_NO_TOOL_EVENTS: list[StreamEvent] = [
    StreamEvent(
        type="content_delta",
        content="안녕하세요! 무엇을 도와드릴까요?",
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=50, output_tokens=20),
    ),
    StreamEvent(type="done"),
]

# --- Infinite-tools: repeating tool call (each call returns same tool) ---
_INFINITE_TOOL_EVENTS: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_inf",
        function_name="traffic_accident_search",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta='{"query": "loop"}',
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=80, output_tokens=30),
    ),
    StreamEvent(type="done"),
]

# --- Unknown tool: requests a tool that is not registered ---
_UNKNOWN_TOOL_EVENTS: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_unk",
        function_name="nonexistent_tool_xyz",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta='{"query": "test"}',
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=90, output_tokens=40),
    ),
    StreamEvent(type="done"),
]

# --- Two simultaneous tool calls in one response ---
_TWO_TOOL_EVENTS: list[StreamEvent] = [
    # First tool: traffic_accident_search
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_t1",
        function_name="traffic_accident_search",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta='{"query": "서울 강남구 교통사고"}',
    ),
    # Second tool: weather_info
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=1,
        tool_call_id="call_t2",
        function_name="weather_info",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=1,
        tool_call_id=None,
        function_name=None,
        function_args_delta='{"query": "서울 날씨"}',
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=120, output_tokens=60),
    ),
    StreamEvent(type="done"),
]

# ---------------------------------------------------------------------------
# LLM client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """MockLLMClient: first call requests a tool, second call returns text answer."""
    return MockLLMClient(
        responses=[_TOOL_CALL_EVENTS, _TEXT_ANSWER_EVENTS],
    )


@pytest.fixture
def mock_llm_client_no_tools() -> MockLLMClient:
    """MockLLMClient: single call returns a direct text answer (no tool use)."""
    return MockLLMClient(
        responses=[_NO_TOOL_EVENTS],
    )


@pytest.fixture
def mock_llm_client_inspectable() -> MockLLMClient:
    """MockLLMClient configured for snapshot verification of last_messages.

    Behaves identically to mock_llm_client; returned as a separate fixture so
    tests can rely on a fresh instance with call_count=0.
    """
    return MockLLMClient(
        responses=[_TOOL_CALL_EVENTS, _TEXT_ANSWER_EVENTS],
    )


@pytest.fixture
def mock_llm_client_infinite_tools() -> MockLLMClient:
    """MockLLMClient: every call requests the same tool indefinitely.

    The engine's max_iterations guard must terminate the loop.
    """
    # Single response list is repeated forever (last element reused).
    return MockLLMClient(
        responses=[_INFINITE_TOOL_EVENTS],
    )


@pytest.fixture
def mock_llm_client_unknown_tool() -> MockLLMClient:
    """MockLLMClient: first call requests a non-existent tool, second returns text."""
    return MockLLMClient(
        responses=[_UNKNOWN_TOOL_EVENTS, _TEXT_ANSWER_EVENTS],
    )


@pytest.fixture
def mock_llm_client_two_tools() -> MockLLMClient:
    """MockLLMClient: first call requests two simultaneous tools, second returns text."""
    return MockLLMClient(
        responses=[_TWO_TOOL_EVENTS, _TEXT_ANSWER_EVENTS],
    )


# ---------------------------------------------------------------------------
# Registry fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def populated_registry() -> ToolRegistry:
    """ToolRegistry pre-loaded with all four mock tools."""
    registry = ToolRegistry()
    for tool in _ALL_MOCK_TOOLS:
        registry.register(tool)
    return registry


@pytest.fixture
def populated_registry_concurrent() -> ToolRegistry:
    """ToolRegistry where traffic_accident_search and weather_info are concurrency-safe.

    Both tools already carry is_concurrency_safe=True in the default mock
    definitions, so this fixture is equivalent to populated_registry.  It is
    provided as an explicit named fixture to document intent in tests that
    verify concurrent dispatch behavior.
    """
    registry = ToolRegistry()
    for tool in _ALL_MOCK_TOOLS:
        registry.register(tool)
    return registry


# ---------------------------------------------------------------------------
# Executor fixtures
# ---------------------------------------------------------------------------


def _build_executor_with_adapters(
    registry: ToolRegistry,
    *,
    slow: bool = False,
    traffic_raises: bool = False,
) -> ToolExecutor:
    """Construct a ToolExecutor with mock adapters for all registered tools.

    Args:
        registry: Pre-populated registry to attach adapters to.
        slow: If True, each adapter sleeps 0.5 s before returning (tests
              concurrent dispatch timing).
        traffic_raises: If True, the traffic_accident_search adapter raises
                        RuntimeError to simulate an API failure.
    """
    executor = ToolExecutor(registry)

    async def _traffic_adapter(validated_input: MockInput) -> dict[str, object]:
        if slow:
            await asyncio.sleep(0.5)
        if traffic_raises:
            raise RuntimeError("API unavailable")
        return {"result": f"Mock result for {validated_input.query}"}

    async def _generic_adapter(validated_input: MockInput) -> dict[str, object]:
        if slow:
            await asyncio.sleep(0.5)
        return {"result": f"Mock result for {validated_input.query}"}

    executor.register_adapter("traffic_accident_search", _traffic_adapter)
    executor.register_adapter("weather_info", _generic_adapter)
    executor.register_adapter("civil_petition_status", _generic_adapter)
    executor.register_adapter("resident_registration", _generic_adapter)

    return executor


@pytest.fixture
def tool_executor_with_mocks(populated_registry: ToolRegistry) -> ToolExecutor:
    """ToolExecutor with immediate-success mock adapters for all four tools."""
    return _build_executor_with_adapters(populated_registry, slow=False)


@pytest.fixture
def tool_executor_with_slow_mocks(populated_registry: ToolRegistry) -> ToolExecutor:
    """ToolExecutor where each adapter awaits 0.5 s before returning.

    Used to verify that the engine dispatches concurrency-safe tools in
    parallel rather than sequentially.
    """
    return _build_executor_with_adapters(populated_registry, slow=True)


@pytest.fixture
def tool_executor_one_fails(populated_registry: ToolRegistry) -> ToolExecutor:
    """ToolExecutor where traffic_accident_search raises RuntimeError.

    weather_info and other tools succeed normally.  Used to verify that the
    engine captures per-tool failures without aborting the full turn.
    """
    return _build_executor_with_adapters(populated_registry, traffic_raises=True)


# ---------------------------------------------------------------------------
# Config and message fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_config() -> QueryEngineConfig:
    """Default QueryEngineConfig with all fields at their standard defaults."""
    return QueryEngineConfig()


@pytest.fixture
def sample_messages() -> list[ChatMessage]:
    """Short conversation history for context-management and snapshot tests."""
    return [
        ChatMessage(role="system", content="You are KOSMOS."),
        ChatMessage(role="user", content="서울 강남구 교통사고 현황"),
        ChatMessage(role="assistant", content="교통사고 현황을 조회하겠습니다."),
    ]
