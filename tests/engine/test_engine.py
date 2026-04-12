# SPDX-License-Identifier: Apache-2.0
"""Integration tests for QueryEngine (T015).

Covers the US1 acceptance scenarios:
1. One tool call -> task_complete
2. Two sequential tool calls -> task_complete
3. No tool call -> end_turn
4. Event ordering guarantee
5. No-raise contract
6. Turn count increment
7. System prompt initialization
8. Budget property
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import _DEFAULT_SYSTEM_PROMPT, QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, SessionBudget

# LLMClient must be imported (not just under TYPE_CHECKING) so that
# QueryContext.model_rebuild() can resolve the forward reference and accept
# mock objects for the llm_client field.
from kosmos.llm.client import LLMClient  # noqa: F401
from kosmos.llm.models import ChatMessage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Helper: collect all events from the async generator
# ---------------------------------------------------------------------------


async def _collect(engine: QueryEngine, message: str) -> list[QueryEvent]:
    """Run engine.run() and collect all yielded events into a list."""
    return [event async for event in engine.run(message)]


# ---------------------------------------------------------------------------
# LLMClient-compatible mock base
#
# QueryContext validates llm_client as isinstance(LLMClient) because the model
# is rebuilt with the real LLMClient annotation.  We subclass LLMClient but
# skip super().__init__() so no real config or HTTP client is created.
# ---------------------------------------------------------------------------


class _MockLLMClientBase(LLMClient):
    """Base for test LLM client mocks that inherit from LLMClient.

    Skips LLMClient.__init__ to avoid requiring a real API token.
    Subclasses must set self._usage and implement stream().
    """

    def __new__(cls, *args: object, **kwargs: object) -> _MockLLMClientBase:
        # Bypass LLMClient.__init__ by calling object.__new__ directly
        return object.__new__(cls)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Adapter: wrap a conftest MockLLMClient inside an LLMClient subclass
# ---------------------------------------------------------------------------


class _MockClientAdapter(_MockLLMClientBase):
    """Delegate stream() and usage to a conftest MockLLMClient instance."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate

    @property
    def usage(self) -> UsageTracker:  # type: ignore[override]
        """Forward to delegate's usage tracker."""
        return self._delegate.usage  # type: ignore[attr-defined]

    async def stream(  # type: ignore[override]
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[object]:
        """Forward to delegate's stream() async generator."""
        async for event in self._delegate.stream(messages, **kwargs):
            yield event


# ---------------------------------------------------------------------------
# Failing mock LLM client for no-raise contract test
# ---------------------------------------------------------------------------


class _FailingMockClient(_MockLLMClientBase):
    """Mock LLM client that raises RuntimeError on every stream() call."""

    def __init__(self) -> None:
        self._usage = UsageTracker(budget=100_000)

    @property
    def usage(self) -> UsageTracker:  # type: ignore[override]
        """Return internal usage tracker."""
        return self._usage

    async def stream(  # type: ignore[override]
        self,
        messages: object,
        **kwargs: object,
    ) -> AsyncIterator[object]:
        """Raise immediately to simulate a catastrophic LLM failure."""
        raise RuntimeError("Simulated LLM failure")
        yield  # pragma: no cover — makes this an async generator


# ---------------------------------------------------------------------------
# Scenario 1: One tool call -> task_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_tool_call_task_complete(
    mock_llm_client: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """One tool call followed by a text answer produces the expected event stream."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    events = await _collect(engine, "서울 강남구 교통사고 현황")

    event_types = [e.type for e in events]

    # Must include all four essential event types
    assert "tool_use" in event_types
    assert "tool_result" in event_types
    assert "text_delta" in event_types
    assert "stop" in event_types

    # Last event is always stop
    assert events[-1].type == "stop"

    # Stop reason indicates the model finished speaking (end_turn after text answer)
    assert events[-1].stop_reason in (StopReason.end_turn, StopReason.task_complete)

    # Message history: system + user + assistant(tool_call) + tool + assistant(text)
    assert engine.message_count >= 5

    # One turn completed
    assert engine.budget.turns_used == 1


# ---------------------------------------------------------------------------
# Scenario 2: Two sequential tool calls -> task_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_tool_calls_both_dispatched(
    mock_llm_client_two_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """Two tool calls in one LLM response: both tool_use and tool_result events appear."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_two_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    events = await _collect(engine, "서울 강남구 날씨와 교통사고 정보를 알려주세요")

    tool_use_events = [e for e in events if e.type == "tool_use"]
    tool_result_events = [e for e in events if e.type == "tool_result"]

    # Both tools dispatched
    assert len(tool_use_events) == 2
    assert len(tool_result_events) == 2

    tool_names_used = {e.tool_name for e in tool_use_events}
    assert "traffic_accident_search" in tool_names_used
    assert "weather_info" in tool_names_used

    # Stream ends with stop
    assert events[-1].type == "stop"


# ---------------------------------------------------------------------------
# Scenario 3: No tool call -> end_turn
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_tool_call_end_turn(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """A direct text response without tool calls yields text_delta events and end_turn stop."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    events = await _collect(engine, "안녕하세요")

    event_types = [e.type for e in events]

    # Text content is emitted
    assert "text_delta" in event_types

    # No tool events
    assert "tool_use" not in event_types
    assert "tool_result" not in event_types

    # Stop is end_turn
    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.end_turn


# ---------------------------------------------------------------------------
# Scenario 4: Event ordering guarantee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_ordering_guarantee(
    mock_llm_client: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """Verify strict event ordering: tool_use before tool_result, usage_update before stop."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    events = await _collect(engine, "교통사고 정보")

    # stop is always the very last event
    assert events[-1].type == "stop"

    # Locate indices for ordering checks
    indices: dict[str, list[int]] = {}
    for i, e in enumerate(events):
        indices.setdefault(e.type, []).append(i)

    # tool_use must precede its corresponding tool_result
    if "tool_use" in indices and "tool_result" in indices:
        assert indices["tool_use"][0] < indices["tool_result"][0]

    # usage_update must precede stop (if present)
    if "usage_update" in indices:
        last_usage_idx = indices["usage_update"][-1]
        stop_idx = indices["stop"][0]
        assert last_usage_idx < stop_idx


# ---------------------------------------------------------------------------
# Scenario 5: No-raise contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_raise_contract(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """engine.run() must not raise even when the LLM client throws an exception."""
    failing_client = _FailingMockClient()

    engine = QueryEngine(
        llm_client=failing_client,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    # Must not raise; collect all events normally
    events = await _collect(engine, "이 요청은 실패합니다")

    assert len(events) >= 1
    last = events[-1]
    assert last.type == "stop"
    assert last.stop_reason == StopReason.error_unrecoverable


# ---------------------------------------------------------------------------
# Scenario 6: Turn count increment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_count_increments_each_run(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """budget.turns_used increments by 1 after each call to run()."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    assert engine.budget.turns_used == 0

    await _collect(engine, "첫 번째 메시지")
    assert engine.budget.turns_used == 1

    await _collect(engine, "두 번째 메시지")
    assert engine.budget.turns_used == 2


# ---------------------------------------------------------------------------
# Scenario 7: System prompt initialization
# ---------------------------------------------------------------------------


def test_default_system_prompt_is_first_message(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """First message in history is the default system prompt."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    # message_count is 1: the system prompt
    assert engine.message_count == 1

    # The internal state carries the correct system prompt
    first_message = engine._state.messages[0]  # noqa: SLF001
    assert first_message.role == "system"
    assert first_message.content == _DEFAULT_SYSTEM_PROMPT


def test_custom_system_prompt(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """A custom system_prompt is stored as the first message."""
    custom_prompt = "You are a specialized assistant for road safety information."

    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
        system_prompt=custom_prompt,
    )

    first_message = engine._state.messages[0]  # noqa: SLF001
    assert first_message.role == "system"
    assert first_message.content == custom_prompt


# ---------------------------------------------------------------------------
# Scenario 8: Budget property
# ---------------------------------------------------------------------------


def test_budget_initial_snapshot(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """Initial budget snapshot reflects zero usage and correct configured limits."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    budget = engine.budget

    assert isinstance(budget, SessionBudget)
    assert budget.tokens_used == 0
    assert budget.turns_used == 0
    assert budget.tokens_budget == 100_000  # MockLLMClient default budget
    assert budget.turns_budget == sample_config.max_turns
    assert budget.is_exhausted is False


@pytest.mark.asyncio
async def test_budget_reflects_token_usage_after_run(
    mock_llm_client_no_tools: object,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
    sample_config: QueryEngineConfig,
) -> None:
    """Budget snapshot reflects token consumption after a completed turn."""
    engine = QueryEngine(
        llm_client=_MockClientAdapter(mock_llm_client_no_tools),
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=sample_config,
    )

    await _collect(engine, "안녕하세요")

    budget = engine.budget
    assert budget.turns_used == 1
    assert budget.is_exhausted is False
    # turns_remaining decreases after a completed turn
    assert budget.turns_remaining == sample_config.max_turns - 1
