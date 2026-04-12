# SPDX-License-Identifier: Apache-2.0
"""Budget enforcement tests for QueryEngine (turn budget and token budget).

Covers:
- Turn budget: engine blocks additional turns once max_turns is reached.
- Token budget: engine blocks processing once the UsageTracker is exhausted.
- SessionBudget snapshot: turns_used, turns_remaining, tokens_used, etc.
- Mid-session exhaustion: token budget runs out before turn budget.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, SessionBudget
from kosmos.llm.client import LLMClient  # noqa: F401 — needed for QueryContext.model_rebuild()
from kosmos.llm.models import ChatMessage, StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

# Re-resolve forward references in QueryContext so mock objects are accepted.
QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def collect_events(engine: QueryEngine, msg: str) -> list[QueryEvent]:
    """Run engine.run(msg) and collect all yielded events into a list."""
    return [e async for e in engine.run(msg)]


def _stop_event(events: list[QueryEvent]) -> QueryEvent:
    """Return the stop event from a collected event list."""
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found in events"
    return stop_events[-1]


# ---------------------------------------------------------------------------
# MockLLMClientAdapter
#
# QueryContext validates llm_client as isinstance(LLMClient) after model_rebuild.
# We subclass LLMClient but bypass its __init__ to avoid needing real API tokens.
# ---------------------------------------------------------------------------

_SIMPLE_TEXT_RESPONSE: list[StreamEvent] = [
    StreamEvent(type="content_delta", content="Hello, I am KOSMOS."),
    StreamEvent(type="usage", usage=TokenUsage(input_tokens=10, output_tokens=5)),
    StreamEvent(type="done"),
]


class _MockLLMClientAdapter(LLMClient):
    """Minimal LLMClient subclass used only in budget tests.

    Delegates usage tracking and stream responses to a caller-supplied
    UsageTracker and a fixed list of StreamEvent sequences.
    """

    def __new__(cls, *args: object, **kwargs: object) -> _MockLLMClientAdapter:
        return object.__new__(cls)  # type: ignore[return-value]

    def __init__(
        self,
        usage_tracker: UsageTracker,
        responses: list[list[StreamEvent]] | None = None,
    ) -> None:
        self._usage = usage_tracker
        self._responses = responses or [_SIMPLE_TEXT_RESPONSE]
        self._call_index = 0

    @property
    def usage(self) -> UsageTracker:  # type: ignore[override]
        return self._usage

    async def stream(  # type: ignore[override]
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        events = self._responses[min(self._call_index, len(self._responses) - 1)]
        self._call_index += 1
        for event in events:
            yield event


def _make_engine(
    *,
    max_turns: int = 10,
    token_budget: int = 100_000,
    responses: list[list[StreamEvent]] | None = None,
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> tuple[QueryEngine, UsageTracker]:
    """Construct a QueryEngine with a fresh UsageTracker and adapter.

    Returns both the engine and the UsageTracker so tests can manipulate
    the tracker directly (e.g. debit() to simulate token exhaustion).
    """
    tracker = UsageTracker(budget=token_budget)
    client = _MockLLMClientAdapter(
        usage_tracker=tracker,
        responses=responses or [_SIMPLE_TEXT_RESPONSE],
    )
    config = QueryEngineConfig(max_turns=max_turns)
    engine = QueryEngine(
        llm_client=client,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=config,
    )
    return engine, tracker


# ===========================================================================
# Turn budget enforcement
# ===========================================================================


@pytest.mark.asyncio
async def test_turn_budget_blocks_after_max_turns(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Third turn is blocked when max_turns=2 and two turns have already run."""
    engine, _ = _make_engine(
        max_turns=2,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    # Run two successful turns to exhaust the turn budget
    await collect_events(engine, "first message")
    await collect_events(engine, "second message")
    assert engine.budget.turns_used == 2

    # Third turn must be immediately blocked
    events = await collect_events(engine, "third message — should be blocked")

    stop = _stop_event(events)
    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert "Turn budget exhausted" in (stop.stop_message or "")
    # turn_count must not increment because the turn was rejected before processing
    assert engine.budget.turns_used == 2


@pytest.mark.asyncio
async def test_turn_budget_blocks_second_turn_when_max_turns_is_one(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Second turn is blocked when max_turns=1."""
    engine, _ = _make_engine(
        max_turns=1,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "first message")
    assert engine.budget.turns_used == 1

    events = await collect_events(engine, "second message — should be blocked")

    stop = _stop_event(events)
    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert "Turn budget exhausted" in (stop.stop_message or "")
    assert engine.budget.turns_used == 1


@pytest.mark.asyncio
async def test_turn_budget_stop_message_contains_turn_counts(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """The stop_message for a turn-budget violation includes both used and total turns."""
    max_turns = 3
    engine, _ = _make_engine(
        max_turns=max_turns,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    for i in range(max_turns):
        await collect_events(engine, f"message {i}")

    events = await collect_events(engine, "over-budget message")
    stop = _stop_event(events)

    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert stop.stop_message is not None
    # Must mention used count (3) and budget (3)
    assert str(max_turns) in stop.stop_message
    assert "Turn budget exhausted" in stop.stop_message


@pytest.mark.asyncio
async def test_turn_budget_yields_only_stop_event(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """A budget-exceeded turn yields exactly one event: the stop event."""
    engine, _ = _make_engine(
        max_turns=1,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "first turn")
    events = await collect_events(engine, "blocked turn")

    # Only the stop event is emitted; nothing else should precede it
    assert len(events) == 1
    assert events[0].type == "stop"
    assert events[0].stop_reason == StopReason.api_budget_exceeded


# ===========================================================================
# Token budget enforcement
# ===========================================================================


@pytest.mark.asyncio
async def test_token_budget_blocks_run_when_exhausted(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """run() yields api_budget_exceeded stop when the token budget is exhausted."""
    engine, tracker = _make_engine(
        token_budget=1000,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    # Exhaust the token budget manually before calling run()
    tracker.debit(TokenUsage(input_tokens=500, output_tokens=500))
    assert tracker.is_exhausted

    events = await collect_events(engine, "this call should be blocked by token budget")

    stop = _stop_event(events)
    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert "Token budget exhausted" in (stop.stop_message or "")


@pytest.mark.asyncio
async def test_token_budget_stop_message_contains_token_counts(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """The stop_message for a token-budget violation includes used and budget counts."""
    budget = 500
    engine, tracker = _make_engine(
        token_budget=budget,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    # Exhaust all tokens
    tracker.debit(TokenUsage(input_tokens=250, output_tokens=250))
    assert tracker.is_exhausted

    events = await collect_events(engine, "blocked by token budget")
    stop = _stop_event(events)

    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert stop.stop_message is not None
    assert "Token budget exhausted" in stop.stop_message
    # Message should mention the used and budget values
    assert str(budget) in stop.stop_message


@pytest.mark.asyncio
async def test_token_budget_yields_only_stop_event(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """A token-budget-exceeded run yields exactly one event: the stop event."""
    engine, tracker = _make_engine(
        token_budget=100,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    tracker.debit(TokenUsage(input_tokens=50, output_tokens=50))
    assert tracker.is_exhausted

    events = await collect_events(engine, "blocked")

    assert len(events) == 1
    assert events[0].type == "stop"
    assert events[0].stop_reason == StopReason.api_budget_exceeded


@pytest.mark.asyncio
async def test_token_budget_turn_count_does_not_increment_on_block(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Blocked turns (token budget) do not increment the turn counter."""
    engine, tracker = _make_engine(
        token_budget=1000,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    tracker.debit(TokenUsage(input_tokens=500, output_tokens=500))
    assert tracker.is_exhausted

    assert engine.budget.turns_used == 0
    await collect_events(engine, "blocked turn 1")
    await collect_events(engine, "blocked turn 2")
    # Turn count must remain zero; blocked turns are not counted
    assert engine.budget.turns_used == 0


# ===========================================================================
# SessionBudget snapshot
# ===========================================================================


def test_budget_snapshot_initial_state(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Fresh engine budget snapshot reflects zero usage and configured limits."""
    max_turns = 5
    token_budget = 10_000
    engine, _ = _make_engine(
        max_turns=max_turns,
        token_budget=token_budget,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    budget = engine.budget
    assert isinstance(budget, SessionBudget)
    assert budget.turns_used == 0
    assert budget.turns_budget == max_turns
    assert budget.turns_remaining == max_turns
    assert budget.tokens_used == 0
    assert budget.tokens_budget == token_budget
    assert budget.tokens_remaining == token_budget
    assert budget.is_exhausted is False


@pytest.mark.asyncio
async def test_budget_snapshot_after_completed_turns(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Budget snapshot reflects turn increments after each successful run()."""
    engine, _ = _make_engine(
        max_turns=5,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "turn one")
    b1 = engine.budget
    assert b1.turns_used == 1
    assert b1.turns_remaining == 4

    await collect_events(engine, "turn two")
    b2 = engine.budget
    assert b2.turns_used == 2
    assert b2.turns_remaining == 3


@pytest.mark.asyncio
async def test_budget_snapshot_turns_remaining_reaches_zero(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """turns_remaining reaches zero and is_exhausted becomes True after max_turns."""
    max_turns = 2
    engine, _ = _make_engine(
        max_turns=max_turns,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    for i in range(max_turns):
        await collect_events(engine, f"turn {i}")

    budget = engine.budget
    assert budget.turns_used == max_turns
    assert budget.turns_remaining == 0
    assert budget.is_exhausted is True


def test_budget_snapshot_reflects_manual_token_debit(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Budget snapshot reflects token consumption after a manual debit() call."""
    engine, tracker = _make_engine(
        token_budget=1000,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    tracker.debit(TokenUsage(input_tokens=300, output_tokens=200))

    budget = engine.budget
    assert budget.tokens_used == 500
    assert budget.tokens_remaining == 500
    assert budget.tokens_budget == 1000
    assert budget.is_exhausted is False


def test_budget_snapshot_is_exhausted_after_full_token_debit(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """is_exhausted is True when tokens_remaining reaches zero."""
    engine, tracker = _make_engine(
        token_budget=200,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    tracker.debit(TokenUsage(input_tokens=100, output_tokens=100))

    budget = engine.budget
    assert budget.tokens_used == 200
    assert budget.tokens_remaining == 0
    assert budget.is_exhausted is True


# ===========================================================================
# Mid-session token exhaustion (token budget hit before turn budget)
# ===========================================================================


@pytest.mark.asyncio
async def test_mid_session_token_exhaustion_blocks_before_turn_budget(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """After 2 successful turns, manually exhaust tokens; third run is blocked by token budget."""
    engine, tracker = _make_engine(
        max_turns=10,  # Turn budget is generous — should not be hit first
        token_budget=100_000,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "first turn")
    await collect_events(engine, "second turn")
    assert engine.budget.turns_used == 2

    # Exhaust the token budget manually between turns
    remaining = tracker.remaining
    tracker.debit(TokenUsage(input_tokens=remaining, output_tokens=0))
    assert tracker.is_exhausted

    # Third call: token budget is exhausted, turn budget (10) is still available
    events = await collect_events(engine, "third turn — token budget exhausted")

    stop = _stop_event(events)
    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert "Token budget exhausted" in (stop.stop_message or "")
    # Turn count must not have incremented for the blocked turn
    assert engine.budget.turns_used == 2


@pytest.mark.asyncio
async def test_mid_session_token_exhaustion_message_correct(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """stop_message for mid-session token exhaustion references token counts."""
    token_budget = 5000
    engine, tracker = _make_engine(
        max_turns=10,
        token_budget=token_budget,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "first turn")

    # Drain remaining tokens
    remaining = tracker.remaining
    tracker.debit(TokenUsage(input_tokens=remaining, output_tokens=0))
    assert tracker.is_exhausted

    events = await collect_events(engine, "blocked by token exhaustion")
    stop = _stop_event(events)

    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert stop.stop_message is not None
    assert "Token budget exhausted" in stop.stop_message
    # The budget ceiling should appear in the message
    assert str(token_budget) in stop.stop_message


@pytest.mark.asyncio
async def test_turn_budget_takes_priority_over_token_budget_when_both_exhausted(
    populated_registry: ToolRegistry,
    tool_executor_with_mocks: ToolExecutor,
) -> None:
    """Turn budget check runs first in engine.run(); when turns are exhausted first, the
    stop message cites 'Turn budget exhausted' even if the token budget is also exhausted."""
    engine, tracker = _make_engine(
        max_turns=1,
        token_budget=1000,
        populated_registry=populated_registry,
        tool_executor_with_mocks=tool_executor_with_mocks,
    )

    await collect_events(engine, "first and only turn")
    assert engine.budget.turns_used == 1

    # Also exhaust the token budget
    remaining = tracker.remaining
    tracker.debit(TokenUsage(input_tokens=remaining, output_tokens=0))
    assert tracker.is_exhausted

    events = await collect_events(engine, "this turn is blocked")
    stop = _stop_event(events)

    # engine.py checks turn budget BEFORE token budget
    assert stop.stop_reason == StopReason.api_budget_exceeded
    assert "Turn budget exhausted" in (stop.stop_message or "")
