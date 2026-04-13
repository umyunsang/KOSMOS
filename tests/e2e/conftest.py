# SPDX-License-Identifier: Apache-2.0
"""E2E test infrastructure for the KOSMOS pipeline.

Provides:
- ``E2EFixtureBuilder`` — builder pattern assembling a fully-wired QueryEngine
  with MockLLMClient, real ToolRegistry (all Phase 1 tools), real ToolExecutor
  with RecoveryExecutor, real ContextBuilder, and optional PermissionPipeline.
- httpx mock fixture — patches ``httpx.AsyncClient.get`` to return recorded
  JSON fixtures based on URL pattern matching.
- MockLLMClient response sequences — pre-built StreamEvent sequences for
  road_risk_score happy-path and degraded-path scenarios.
- Assertion helpers — reusable asserts for E2E test verification.

All tests use recorded fixtures only; zero live API calls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from kosmos.context.builder import ContextBuilder
from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage, StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.permissions.models import SessionContext
from kosmos.permissions.pipeline import PermissionPipeline
from kosmos.recovery.executor import RecoveryExecutor
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

# Re-export MockLLMClient from engine test fixtures for reuse
from tests.engine.conftest import MockLLMClient

# ---------------------------------------------------------------------------
# LLMClient-compatible adapter for MockLLMClient
#
# QueryContext validates llm_client as isinstance(LLMClient); MockLLMClient is
# a plain class that duck-types the interface.  _MockLLMClientAdapter subclasses
# LLMClient (bypassing __init__) so Pydantic's isinstance check passes, while
# delegating all behaviour to the underlying MockLLMClient instance.
# ---------------------------------------------------------------------------


class _MockLLMClientAdapter(LLMClient):
    """Wrap a MockLLMClient so it satisfies Pydantic's isinstance(LLMClient) check.

    Bypasses LLMClient.__init__ via __new__ to avoid requiring a real API token
    or HTTP client.  All stream() calls and the usage property are delegated to
    the underlying MockLLMClient instance.
    """

    def __new__(cls, *args: object, **kwargs: object) -> _MockLLMClientAdapter:
        return object.__new__(cls)  # type: ignore[return-value]

    def __init__(self, delegate: MockLLMClient) -> None:
        self._delegate = delegate

    @property
    def usage(self) -> UsageTracker:  # type: ignore[override]
        """Forward to delegate's usage tracker."""
        return self._delegate.usage

    async def stream(  # type: ignore[override]
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        """Delegate to MockLLMClient.stream()."""
        async for event in self._delegate.stream(messages, **kwargs):
            yield event


# ---------------------------------------------------------------------------
# Fixture file paths
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).resolve().parent.parent
_KOROAD_FIXTURE_DIR = _FIXTURE_DIR / "tools" / "koroad" / "fixtures"
_KMA_FIXTURE_DIR = _FIXTURE_DIR / "tools" / "kma" / "fixtures"

# URL patterns for httpx mock routing
_URL_PATTERNS: dict[str, str] = {
    "koroad_accident_search": "getRestFrequentzoneLg",
    "kma_weather_alert_status": "getWthrWrnList",
    "kma_current_observation": "getUltraSrtNcst",
}

# Fixture file mapping: adapter_id → default fixture filename
_DEFAULT_FIXTURES: dict[str, tuple[Path, str]] = {
    "koroad_accident_search": (_KOROAD_FIXTURE_DIR, "koroad_success.json"),
    "kma_weather_alert_status": (_KMA_FIXTURE_DIR, "kma_alert_success.json"),
    "kma_current_observation": (_KMA_FIXTURE_DIR, "kma_obs_success.json"),
}

# ---------------------------------------------------------------------------
# Environment variables required by adapters
# ---------------------------------------------------------------------------

_REQUIRED_ENV_VARS: dict[str, str] = {
    "KOSMOS_KOROAD_API_KEY": "test-koroad-key-e2e",
    "KOSMOS_DATA_GO_KR_API_KEY": "test-data-go-kr-key-e2e",
}


# ---------------------------------------------------------------------------
# T004: Pre-built StreamEvent sequences for road_risk_score E2E
# ---------------------------------------------------------------------------

# RoadRiskScoreInput JSON: si_do=11 (Seoul), nx=61, ny=126
_ROAD_RISK_SCORE_ARGS = json.dumps({"si_do": 11, "nx": 61, "ny": 126})

# --- Happy-path: Iteration 1 — LLM requests road_risk_score tool ---
TOOL_CALL_ROAD_RISK: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_e2e_001",
        function_name="road_risk_score",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta=_ROAD_RISK_SCORE_ARGS,
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=500, output_tokens=80),
    ),
    StreamEvent(type="done"),
]

# --- Happy-path: Iteration 2 — LLM synthesizes Korean safety recommendation ---
TEXT_ANSWER_ROUTE_SAFETY: list[StreamEvent] = [
    StreamEvent(
        type="content_delta",
        content=(
            "부산에서 서울로 가는 경로의 안전 정보를 분석했습니다.\n\n"
            "현재 사고다발지역이 2건 확인되었으며, "
            "기상특보 2건이 발효 중입니다. "
            "강수량은 0mm로 도로 노면 상태는 양호합니다.\n\n"
            "전반적인 도로 위험도는 '보통' 수준으로 평가됩니다. "
            "안전운전에 유의하시기 바랍니다."
        ),
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=800, output_tokens=150),
    ),
    StreamEvent(type="done"),
]

# --- Degraded-path: same tool call, but text acknowledges data gaps ---
TEXT_ANSWER_ROUTE_SAFETY_DEGRADED: list[StreamEvent] = [
    StreamEvent(
        type="content_delta",
        content=(
            "경로 안전 정보를 분석했으나 일부 데이터를 확보하지 못했습니다.\n\n"
            "기상 관측 데이터가 누락되어 정확한 강수 정보를 "
            "제공할 수 없습니다. 가용한 데이터를 기반으로 "
            "위험도를 평가한 결과, 주의가 필요합니다."
        ),
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=900, output_tokens=120),
    ),
    StreamEvent(type="done"),
]


# ---------------------------------------------------------------------------
# T003: httpx mock fixture
# ---------------------------------------------------------------------------


def _raise_failure(adapter_id: str, mode: str, url_str: str) -> httpx.Response:
    """Return an error response or raise an exception for a failed adapter."""
    if mode == "500":
        return httpx.Response(
            status_code=500,
            json={"error": "Internal Server Error"},
            request=httpx.Request("GET", url_str),
        )
    if mode == "timeout":
        raise httpx.TimeoutException(
            f"Timeout for {adapter_id}",
            request=httpx.Request("GET", url_str),
        )
    raise httpx.ConnectError(
        f"Connection refused for {adapter_id}",
        request=httpx.Request("GET", url_str),
    )


def _build_httpx_mock(
    fixture_overrides: dict[str, Path],
    failure_modes: dict[str, str],
) -> AsyncMock:
    """Build an AsyncMock for httpx.AsyncClient.get with URL-based routing.

    Args:
        fixture_overrides: adapter_id → Path to JSON fixture file.
        failure_modes: adapter_id → failure mode string ("500", "timeout",
            "connection_error").

    Returns:
        An AsyncMock that returns httpx.Response based on URL patterns.
    """
    # Pre-load fixture data
    fixture_data: dict[str, dict[str, Any]] = {}
    for adapter_id, (fixture_dir, default_name) in _DEFAULT_FIXTURES.items():
        if adapter_id in fixture_overrides:
            fpath = fixture_overrides[adapter_id]
        else:
            fpath = fixture_dir / default_name
        if fpath.exists():
            fixture_data[adapter_id] = json.loads(fpath.read_text())

    async def _mock_get(
        url: str | httpx.URL,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        url_str = str(url)

        for adapter_id, url_pattern in _URL_PATTERNS.items():
            if url_pattern not in url_str:
                continue

            if adapter_id in failure_modes:
                return _raise_failure(
                    adapter_id,
                    failure_modes[adapter_id],
                    url_str,
                )

            # Return fixture data
            data = fixture_data.get(adapter_id, {})
            return httpx.Response(
                status_code=200,
                json=data,
                request=httpx.Request("GET", url_str),
                headers={"content-type": "application/json"},
            )

        # Unmatched URL — fail loud to detect missing fixture coverage
        raise AssertionError(f"Unpatched httpx.get call to URL: {url_str}")

    mock = AsyncMock(side_effect=_mock_get)
    return mock


# ---------------------------------------------------------------------------
# T002: E2EFixtureBuilder
# ---------------------------------------------------------------------------


class E2EFixtureBuilder:
    """Builder pattern for assembling a fully-wired QueryEngine for E2E tests.

    Usage::

        engine, mock_get = (
            E2EFixtureBuilder()
            .with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY])
            .build()
        )
        events = [e async for e in engine.run("citizen query")]
    """

    def __init__(self) -> None:
        self._llm_responses: list[list[StreamEvent]] = [
            TOOL_CALL_ROAD_RISK,
            TEXT_ANSWER_ROUTE_SAFETY,
        ]
        self._budget: int = 100_000
        self._fixture_overrides: dict[str, Path] = {}
        self._failure_modes: dict[str, str] = {}
        self._permission_session: SessionContext | None = None
        self._config: QueryEngineConfig | None = None

    def with_llm_responses(
        self,
        responses: list[list[StreamEvent]],
    ) -> E2EFixtureBuilder:
        """Configure MockLLMClient with custom response sequences."""
        self._llm_responses = responses
        return self

    def with_api_fixture(
        self,
        adapter_id: str,
        fixture_path: str | Path,
    ) -> E2EFixtureBuilder:
        """Override the default fixture file for a specific adapter.

        Args:
            adapter_id: Tool id (e.g. "koroad_accident_search").
            fixture_path: Absolute or relative path to the JSON fixture.
        """
        self._fixture_overrides[adapter_id] = Path(fixture_path)
        return self

    def with_api_failure(
        self,
        adapter_id: str,
        failure_mode: str = "500",
    ) -> E2EFixtureBuilder:
        """Inject a failure for a specific adapter.

        Args:
            adapter_id: Tool id to fail.
            failure_mode: One of "500", "timeout", "connection_error".
        """
        self._failure_modes[adapter_id] = failure_mode
        return self

    def with_permission_pipeline(
        self,
        session_context: SessionContext,
    ) -> E2EFixtureBuilder:
        """Attach a PermissionPipeline with the given SessionContext."""
        self._permission_session = session_context
        return self

    def with_budget(self, token_budget: int) -> E2EFixtureBuilder:
        """Set the token budget for MockLLMClient."""
        self._budget = token_budget
        return self

    def with_config(self, config: QueryEngineConfig) -> E2EFixtureBuilder:
        """Override the QueryEngineConfig."""
        self._config = config
        return self

    def build(self) -> tuple[QueryEngine, MockLLMClient, AsyncMock]:
        """Assemble all components and return a wired QueryEngine.

        Returns:
            A 3-tuple of (QueryEngine, MockLLMClient, httpx_mock_get).
            The httpx mock is returned for call-count verification.
        """
        # 1. MockLLMClient (plain duck-typed mock)
        llm_client = MockLLMClient(
            responses=self._llm_responses,
            budget=self._budget,
        )

        # Wrap in LLMClient subclass so Pydantic's isinstance check in QueryContext passes
        llm_client_adapter = _MockLLMClientAdapter(llm_client)

        # 2. Real ToolRegistry + ToolExecutor with RecoveryExecutor
        registry = ToolRegistry()
        recovery = RecoveryExecutor()
        executor = ToolExecutor(registry, recovery_executor=recovery)

        # 3. Register all Phase 1 tools
        register_all_tools(registry, executor)

        # 4. Real ContextBuilder
        context_builder = ContextBuilder(registry=registry)

        # 5. Build httpx mock
        httpx_mock = _build_httpx_mock(
            self._fixture_overrides,
            self._failure_modes,
        )

        # 6. QueryEngine
        config = self._config or QueryEngineConfig()
        engine = QueryEngine(
            llm_client=llm_client_adapter,
            tool_registry=registry,
            tool_executor=executor,
            config=config,
            context_builder=context_builder,
        )

        # 7. Attach permission pipeline if configured
        # The permission pipeline integration is wired via the engine's query
        # context; store it on the engine for tests to verify.
        if self._permission_session is not None:
            # Store for access in tests
            engine._permission_session = self._permission_session  # type: ignore[attr-defined]
            engine._permission_pipeline = PermissionPipeline(  # type: ignore[attr-defined]
                executor=executor,
                registry=registry,
            )

        return engine, llm_client, httpx_mock


# ---------------------------------------------------------------------------
# T005: Assertion helpers
# ---------------------------------------------------------------------------


def assert_tool_calls_dispatched(
    events: list[QueryEvent],
    expected_tool_ids: list[str],
) -> None:
    """Assert that tool_use events were emitted for all expected tool ids.

    Args:
        events: Collected QueryEvent list from engine.run().
        expected_tool_ids: Tool ids that must appear in tool_use events.
    """
    dispatched = [e.tool_name for e in events if e.type == "tool_use"]
    for tool_id in expected_tool_ids:
        assert tool_id in dispatched, (
            f"Expected tool_use for {tool_id!r}, but only dispatched: {dispatched}"
        )


def assert_final_response_contains(
    events: list[QueryEvent],
    keywords: list[str],
) -> None:
    """Assert that the concatenated text_delta content contains all keywords.

    Args:
        events: Collected QueryEvent list.
        keywords: Korean or English keywords that must appear in the final text.
    """
    text_parts = [e.content for e in events if e.type == "text_delta" and e.content]
    full_text = "".join(text_parts)
    assert full_text, "No text_delta events found in response"
    for kw in keywords:
        assert kw in full_text, (
            f"Keyword {kw!r} not found in final response text: {full_text[:200]}..."
        )


def assert_usage_matches(
    llm_client: MockLLMClient,
    expected_input_tokens: int,
    expected_output_tokens: int,
    events: list[QueryEvent] | None = None,
) -> None:
    """Assert that token usage totals match expected values exactly.

    Args:
        llm_client: The MockLLMClient whose usage tracker may be checked
            as fallback.
        expected_input_tokens: Expected sum of input tokens.
        expected_output_tokens: Expected sum of output tokens.
        events: Optional collected QueryEvent list to read usage_update
            totals from. Preferred over UsageTracker because
            MockLLMClient does not call debit().
    """
    expected_total = expected_input_tokens + expected_output_tokens

    if events is not None:
        # Prefer engine-emitted usage_update events because MockLLMClient
        # yields usage StreamEvents but does not call UsageTracker.debit().
        usage_events = [e for e in events if e.type == "usage_update"]
        if usage_events:
            total_used = 0
            for event in usage_events:
                if event.usage is not None:
                    total_used += (event.usage.input_tokens or 0) + (event.usage.output_tokens or 0)
            assert total_used == expected_total, (
                f"Total tokens used {total_used} != "
                f"expected {expected_total} "
                f"(input={expected_input_tokens}, "
                f"output={expected_output_tokens})"
            )
            return

    tracker = llm_client.usage
    total_used = tracker.total_used
    assert total_used == expected_total, (
        f"Total tokens used {total_used} != expected {expected_total} "
        f"(input={expected_input_tokens}, "
        f"output={expected_output_tokens}); "
        "pass events=... to assert against engine-emitted usage_update "
        "totals when MockLLMClient does not debit UsageTracker"
    )


def assert_stop_reason(
    events: list[QueryEvent],
    expected_reason: StopReason,
) -> None:
    """Assert the stop event has the expected reason.

    Args:
        events: Collected QueryEvent list.
        expected_reason: The StopReason that should appear in the stop event.
    """
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found in response"
    assert stop_events[-1].stop_reason == expected_reason, (
        f"Stop reason {stop_events[-1].stop_reason!r} != expected {expected_reason!r}"
    )


def assert_data_gaps(
    events: list[QueryEvent],
    expected_gaps: list[str],
) -> None:
    """Assert that tool_result events for road_risk_score contain expected data_gaps.

    Args:
        events: Collected QueryEvent list.
        expected_gaps: Adapter names expected in data_gaps (e.g. ["koroad_accident_search"]).
    """
    tool_results = [
        e.tool_result for e in events if e.type == "tool_result" and e.tool_result is not None
    ]
    # Find road_risk_score result
    risk_results = [tr for tr in tool_results if tr.tool_id == "road_risk_score"]
    assert risk_results, "No tool_result for road_risk_score found"

    result = risk_results[0]
    # Fail fast on unsuccessful executions to avoid false positives
    assert result.success, f"road_risk_score failed: {result.error}"
    assert result.data is not None, "road_risk_score returned no data"
    actual_gaps = result.data.get("data_gaps", [])

    for gap in expected_gaps:
        assert gap in actual_gaps, (
            f"Expected data_gap {gap!r} not found in actual gaps: {actual_gaps}"
        )


def assert_no_data_gaps(events: list[QueryEvent]) -> None:
    """Assert that road_risk_score result has no data_gaps."""
    tool_results = [
        e.tool_result for e in events if e.type == "tool_result" and e.tool_result is not None
    ]
    risk_results = [tr for tr in tool_results if tr.tool_id == "road_risk_score"]
    assert risk_results, "No tool_result for road_risk_score found"
    result = risk_results[0]
    assert result.success, f"road_risk_score failed: {result.error}"
    assert result.data is not None
    gaps = result.data.get("data_gaps", [])
    assert gaps == [], f"Unexpected data_gaps: {gaps}"


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def e2e_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for E2E tests."""
    for var, val in _REQUIRED_ENV_VARS.items():
        monkeypatch.setenv(var, val)


@pytest.fixture
def e2e_builder() -> E2EFixtureBuilder:
    """Return a fresh E2EFixtureBuilder instance."""
    return E2EFixtureBuilder()


async def run_e2e_query(
    engine: QueryEngine,
    httpx_mock: AsyncMock,
    user_message: str = "내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
) -> list[QueryEvent]:
    """Run a full E2E query with httpx patched and collect all events.

    Args:
        engine: Wired QueryEngine from E2EFixtureBuilder.
        httpx_mock: The httpx mock to patch with.
        user_message: The citizen's question.

    Returns:
        List of all QueryEvent objects yielded by engine.run().
    """
    with patch.object(httpx.AsyncClient, "get", httpx_mock):
        events: list[QueryEvent] = []
        async for event in engine.run(user_message):
            events.append(event)
        return events
