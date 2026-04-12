# SPDX-License-Identifier: Apache-2.0
"""Concurrent tool dispatch tests for the KOSMOS Query Engine.

Tests cover:
- dispatch_tool_calls() directly (unit tests)
- Timing assertions to verify parallel execution via asyncio.TaskGroup
- Partition-sort algorithm correctness
- Integration through QueryEngine via mock_llm_client_two_tools

All tests use mocks only — no live API calls, no environment variables required.
asyncio_mode = "auto" is configured in pyproject.toml; @pytest.mark.asyncio is
added for documentation clarity.
"""

from __future__ import annotations

import time

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import StopReason
from kosmos.engine.models import QueryContext, QueryState
from kosmos.engine.query import dispatch_tool_calls, query

# LLMClient must be imported (not just under TYPE_CHECKING) so that
# QueryContext.model_rebuild() can resolve the forward reference.
from kosmos.llm.client import LLMClient  # noqa: F401
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Local helpers: build ToolCall objects for unit tests
# ---------------------------------------------------------------------------


def _tc(call_id: str, tool_name: str, args: str = '{"query": "test"}') -> ToolCall:
    """Shorthand to build a ToolCall."""
    return ToolCall(id=call_id, function=FunctionCall(name=tool_name, arguments=args))


# ---------------------------------------------------------------------------
# Helper: build a QueryContext from fixture objects
# ---------------------------------------------------------------------------


def _make_ctx(
    llm_client: object,
    tool_executor: ToolExecutor,
    tool_registry: ToolRegistry,
    config: QueryEngineConfig | None = None,
) -> QueryContext:
    """Construct a minimal QueryContext for integration tests."""
    if config is None:
        config = QueryEngineConfig()
    state = QueryState(
        usage=UsageTracker(budget=100_000),
        messages=[
            ChatMessage(role="system", content="You are KOSMOS."),
            ChatMessage(role="user", content="test"),
        ],
    )
    return QueryContext.model_construct(
        state=state,
        llm_client=llm_client,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
        config=config,
        iteration=0,
    )


# ===========================================================================
# Section 1: Unit tests for dispatch_tool_calls() directly
# ===========================================================================


class TestDispatchToolCallsEmpty:
    """dispatch_tool_calls() with an empty list must return an empty list."""

    @pytest.mark.asyncio
    async def test_empty_tool_calls_returns_empty_list(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        results = await dispatch_tool_calls([], populated_registry, tool_executor_with_mocks)
        assert results == []


class TestDispatchToolCallsSingleSafe:
    """A single concurrency-safe tool must still be dispatched sequentially.

    The partition-sort optimization: single-element groups skip TaskGroup
    (not worth the overhead).
    """

    @pytest.mark.asyncio
    async def test_single_safe_tool_dispatched_sequentially(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [_tc("call_1", "traffic_accident_search")]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 1
        assert results[0].tool_id == "traffic_accident_search"
        assert results[0].success is True


class TestDispatchToolCallsTwoSafe:
    """Two consecutive concurrency-safe tools must be dispatched concurrently via TaskGroup."""

    @pytest.mark.asyncio
    async def test_two_safe_tools_both_succeed(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),
            _tc("call_2", "weather_info"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 2
        assert results[0].tool_id == "traffic_accident_search"
        assert results[1].tool_id == "weather_info"
        assert results[0].success is True
        assert results[1].success is True

    @pytest.mark.asyncio
    async def test_two_safe_tools_result_order_preserved(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Results must be in the same order as input tool_calls, regardless of concurrency."""
        tool_calls = [
            _tc("call_a", "weather_info"),
            _tc("call_b", "traffic_accident_search"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 2
        assert results[0].tool_id == "weather_info"
        assert results[1].tool_id == "traffic_accident_search"


class TestDispatchToolCallsSingleNonSafe:
    """A single non-concurrency-safe tool must be dispatched sequentially."""

    @pytest.mark.asyncio
    async def test_single_non_safe_tool_dispatched_sequentially(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [_tc("call_1", "civil_petition_status")]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 1
        assert results[0].tool_id == "civil_petition_status"
        assert results[0].success is True


class TestDispatchToolCallsMixed:
    """Mixed safe/non-safe sequence: [safe, safe, non-safe, safe].

    Expected dispatch strategy:
    - Group 1: [traffic_accident_search, weather_info] → concurrent (TaskGroup)
    - Group 2: [civil_petition_status] → sequential (single non-safe)
    - Group 3: [traffic_accident_search] → sequential (single safe, solo group)
    """

    @pytest.mark.asyncio
    async def test_mixed_safe_non_safe_all_succeed(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),
            _tc("call_2", "weather_info"),
            _tc("call_3", "civil_petition_status"),
            _tc("call_4", "traffic_accident_search"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 4
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_mixed_result_order_matches_input(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),
            _tc("call_2", "weather_info"),
            _tc("call_3", "civil_petition_status"),
            _tc("call_4", "traffic_accident_search"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert results[0].tool_id == "traffic_accident_search"
        assert results[1].tool_id == "weather_info"
        assert results[2].tool_id == "civil_petition_status"
        assert results[3].tool_id == "traffic_accident_search"


class TestDispatchToolCallsUnknownTool:
    """An unknown tool must be treated as non-safe (fail-closed) and dispatched sequentially.

    The executor returns success=False for an unknown tool; dispatch_tool_calls
    must not raise and must still include the failed result in the output.
    """

    @pytest.mark.asyncio
    async def test_unknown_tool_treated_as_non_safe_fail_closed(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [_tc("call_unk", "nonexistent_tool_xyz")]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 1
        assert results[0].tool_id == "nonexistent_tool_xyz"
        assert results[0].success is False
        assert results[0].error_type == "not_found"

    @pytest.mark.asyncio
    async def test_unknown_tool_does_not_raise(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """dispatch_tool_calls must never raise even when a tool is not found."""
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),
            _tc("call_unk", "completely_unknown_tool"),
            _tc("call_2", "weather_info"),
        ]
        # Must not raise
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error_type == "not_found"
        assert results[2].success is True


class TestDispatchToolCallsResultOrdering:
    """Results must always match input order regardless of dispatch strategy."""

    @pytest.mark.asyncio
    async def test_result_order_for_all_safe(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Two concurrency-safe tools: result[0] → first tool, result[1] → second tool."""
        tool_calls = [
            _tc("id_first", "traffic_accident_search"),
            _tc("id_second", "weather_info"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 2
        assert results[0].tool_id == "traffic_accident_search"
        assert results[1].tool_id == "weather_info"

    @pytest.mark.asyncio
    async def test_result_order_mixed_safe_and_non_safe(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Non-safe tool between two safe groups must appear at the correct index."""
        tool_calls = [
            _tc("id_1", "weather_info"),
            _tc("id_2", "civil_petition_status"),
            _tc("id_3", "traffic_accident_search"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 3
        assert results[0].tool_id == "weather_info"
        assert results[1].tool_id == "civil_petition_status"
        assert results[2].tool_id == "traffic_accident_search"


# ===========================================================================
# Section 2: Timing assertions (concurrent vs sequential)
# ===========================================================================


class TestTimingConcurrentDispatch:
    """Verify that two slow concurrency-safe tools complete in ~0.5s, not ~1.0s."""

    @pytest.mark.asyncio
    async def test_two_slow_safe_tools_complete_concurrently(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_slow_mocks: ToolExecutor,
    ) -> None:
        """Two 0.5s tools dispatched concurrently must finish in < 0.8s.

        If dispatched sequentially they would take ~1.0s total.
        The 0.8s upper bound provides generous tolerance for CI scheduling jitter.
        """
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),
            _tc("call_2", "weather_info"),
        ]

        start = time.monotonic()
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_slow_mocks
        )
        elapsed = time.monotonic() - start

        assert len(results) == 2
        assert all(r.success for r in results)
        # Concurrent: should finish near 0.5s, not 1.0s
        assert elapsed < 0.8, (
            f"Two concurrent 0.5s tools took {elapsed:.3f}s — expected < 0.8s. "
            "Dispatch may have fallen back to sequential."
        )

    @pytest.mark.asyncio
    async def test_single_slow_safe_tool_dispatched_sequentially(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_slow_mocks: ToolExecutor,
    ) -> None:
        """A single safe tool (no group) must run sequentially and finish in ~0.5s.

        This confirms the 'single-tool group → sequential' optimization is preserved.
        """
        tool_calls = [_tc("call_1", "traffic_accident_search")]

        start = time.monotonic()
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_slow_mocks
        )
        elapsed = time.monotonic() - start

        assert len(results) == 1
        assert results[0].success is True
        # Single tool: must complete in roughly one sleep cycle
        assert elapsed >= 0.4, f"Single slow tool completed in only {elapsed:.3f}s — unexpected"
        assert elapsed < 1.2, f"Single slow tool took too long: {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_non_safe_tools_always_sequential(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_slow_mocks: ToolExecutor,
    ) -> None:
        """Non-safe tools must never be batched; two such tools take ~1.0s, not ~0.5s.

        civil_petition_status is is_concurrency_safe=False.
        We only have one non-safe tool with a slow adapter, so we call it
        twice via two separate tool calls and verify total time is >= 0.9s.
        """
        # Two consecutive non-safe tool calls (same tool, two calls)
        tool_calls = [
            _tc("call_a", "civil_petition_status"),
            _tc("call_b", "civil_petition_status"),
        ]

        start = time.monotonic()
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_slow_mocks
        )
        elapsed = time.monotonic() - start

        assert len(results) == 2
        assert all(r.success for r in results)
        # Sequential: must take at least 0.9s (two × 0.5s minus scheduling slack)
        assert elapsed >= 0.9, (
            f"Two sequential 0.5s non-safe tools finished in {elapsed:.3f}s — "
            "expected >= 0.9s (sequential execution)."
        )


# ===========================================================================
# Section 3: Partition-sort correctness
# ===========================================================================


class TestPartitionSortCorrectness:
    """Verify the partition-sort grouping algorithm produces correct groups.

    Input:  [safe_A, safe_B, non_safe_C, safe_D, safe_E]
    Groups: [A, B], [C], [D, E]

    All 5 results must be returned in order.
    """

    @pytest.mark.asyncio
    async def test_five_tools_partitioned_into_three_groups(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        tool_calls = [
            _tc("call_a", "traffic_accident_search"),  # safe group 1
            _tc("call_b", "weather_info"),  # safe group 1
            _tc("call_c", "civil_petition_status"),  # non-safe group 2
            _tc("call_d", "traffic_accident_search"),  # safe group 3
            _tc("call_e", "weather_info"),  # safe group 3
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 5
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_five_tools_result_order_matches_input(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Regardless of grouping and concurrent execution, output index == input index."""
        tool_calls = [
            _tc("call_a", "traffic_accident_search"),
            _tc("call_b", "weather_info"),
            _tc("call_c", "civil_petition_status"),
            _tc("call_d", "traffic_accident_search"),
            _tc("call_e", "weather_info"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        tool_ids = [r.tool_id for r in results]
        assert tool_ids == [
            "traffic_accident_search",
            "weather_info",
            "civil_petition_status",
            "traffic_accident_search",
            "weather_info",
        ]

    @pytest.mark.asyncio
    async def test_five_tools_concurrent_groups_faster_than_sequential(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_slow_mocks: ToolExecutor,
    ) -> None:
        """Groups [A,B] and [D,E] each dispatch concurrently (0.5s each group).

        Total expected time: ~1.5s (group1: 0.5s + group2: 0.5s + group3: 0.5s).
        Sequential would be: 5 × 0.5s = 2.5s.

        We assert total_time < 2.0s to confirm parallel execution within groups.
        """
        tool_calls = [
            _tc("call_a", "traffic_accident_search"),
            _tc("call_b", "weather_info"),
            _tc("call_c", "civil_petition_status"),
            _tc("call_d", "traffic_accident_search"),
            _tc("call_e", "weather_info"),
        ]

        start = time.monotonic()
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_slow_mocks
        )
        elapsed = time.monotonic() - start

        assert len(results) == 5
        # Concurrent groups: ~1.5s. Sequential: ~2.5s.
        assert elapsed < 2.0, (
            f"Five-tool partition took {elapsed:.3f}s — expected < 2.0s with concurrent groups."
        )

    @pytest.mark.asyncio
    async def test_consecutive_non_safe_tools_stay_sequential(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Multiple consecutive non-safe tools must each run individually (no batching)."""
        tool_calls = [
            _tc("call_1", "civil_petition_status"),
            _tc("call_2", "civil_petition_status"),
            _tc("call_3", "civil_petition_status"),
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 3
        assert all(r.tool_id == "civil_petition_status" for r in results)
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_alternating_safe_non_safe_creates_many_groups(
        self,
        populated_registry: ToolRegistry,
        tool_executor_with_mocks: ToolExecutor,
    ) -> None:
        """Alternating [safe, non-safe, safe, non-safe] → 4 groups of 1, all succeed."""
        tool_calls = [
            _tc("call_1", "traffic_accident_search"),  # safe, solo
            _tc("call_2", "civil_petition_status"),  # non-safe, solo
            _tc("call_3", "weather_info"),  # safe, solo
            _tc("call_4", "civil_petition_status"),  # non-safe, solo
        ]
        results = await dispatch_tool_calls(
            tool_calls, populated_registry, tool_executor_with_mocks
        )

        assert len(results) == 4
        assert all(r.success for r in results)
        tool_ids = [r.tool_id for r in results]
        assert tool_ids == [
            "traffic_accident_search",
            "civil_petition_status",
            "weather_info",
            "civil_petition_status",
        ]


# ===========================================================================
# Section 4: Integration through QueryEngine (query() generator)
# ===========================================================================


class TestIntegrationThroughQueryEngine:
    """Verify concurrent dispatch is exercised end-to-end through the query() generator."""

    @pytest.mark.asyncio
    async def test_two_concurrent_safe_tools_yield_two_tool_result_events(
        self,
        mock_llm_client_two_tools,
        tool_executor_with_mocks: ToolExecutor,
        populated_registry: ToolRegistry,
    ) -> None:
        """mock_llm_client_two_tools requests traffic_accident_search + weather_info.

        Both are concurrency-safe, so they should be dispatched concurrently.
        The query() generator must yield exactly two tool_result events.
        """
        ctx = _make_ctx(mock_llm_client_two_tools, tool_executor_with_mocks, populated_registry)
        events = []
        async for event in query(ctx):
            events.append(event)

        tool_result_events = [e for e in events if e.type == "tool_result"]
        assert len(tool_result_events) == 2

    @pytest.mark.asyncio
    async def test_two_concurrent_safe_tools_both_succeed(
        self,
        mock_llm_client_two_tools,
        tool_executor_with_mocks: ToolExecutor,
        populated_registry: ToolRegistry,
    ) -> None:
        """Both tool results from concurrent dispatch must report success=True."""
        ctx = _make_ctx(mock_llm_client_two_tools, tool_executor_with_mocks, populated_registry)
        events = []
        async for event in query(ctx):
            events.append(event)

        tool_result_events = [e for e in events if e.type == "tool_result"]
        assert all(e.tool_result is not None for e in tool_result_events)
        assert all(e.tool_result.success for e in tool_result_events)

    @pytest.mark.asyncio
    async def test_two_concurrent_safe_tools_names_correct(
        self,
        mock_llm_client_two_tools,
        tool_executor_with_mocks: ToolExecutor,
        populated_registry: ToolRegistry,
    ) -> None:
        """tool_use events must carry the correct tool names for both dispatched tools."""
        ctx = _make_ctx(mock_llm_client_two_tools, tool_executor_with_mocks, populated_registry)
        events = []
        async for event in query(ctx):
            events.append(event)

        tool_use_events = [e for e in events if e.type == "tool_use"]
        dispatched_names = {e.tool_name for e in tool_use_events}
        assert "traffic_accident_search" in dispatched_names
        assert "weather_info" in dispatched_names

    @pytest.mark.asyncio
    async def test_two_concurrent_safe_tools_final_stop_is_end_turn(
        self,
        mock_llm_client_two_tools,
        tool_executor_with_mocks: ToolExecutor,
        populated_registry: ToolRegistry,
    ) -> None:
        """After concurrent dispatch succeeds, the engine must complete with end_turn."""
        ctx = _make_ctx(mock_llm_client_two_tools, tool_executor_with_mocks, populated_registry)
        events = []
        async for event in query(ctx):
            events.append(event)

        stop_event = events[-1]
        assert stop_event.type == "stop"
        assert stop_event.stop_reason == StopReason.end_turn

    @pytest.mark.asyncio
    async def test_concurrent_dispatch_timing_through_query_engine(
        self,
        mock_llm_client_two_tools,
        tool_executor_with_slow_mocks: ToolExecutor,
        populated_registry: ToolRegistry,
    ) -> None:
        """Two slow (0.5s) concurrent-safe tools through the engine must finish in < 0.8s.

        This test validates that the query() loop invokes dispatch_tool_calls()
        which uses asyncio.TaskGroup for the two-tool group.
        """
        ctx = _make_ctx(
            mock_llm_client_two_tools, tool_executor_with_slow_mocks, populated_registry
        )

        start = time.monotonic()
        events = []
        async for event in query(ctx):
            events.append(event)
        elapsed = time.monotonic() - start

        tool_result_events = [e for e in events if e.type == "tool_result"]
        assert len(tool_result_events) == 2

        # Tool dispatch phase should be concurrent: ~0.5s, not ~1.0s
        # The remaining engine overhead (LLM mock streaming) is negligible.
        # We allow up to 1.3s total to account for the second LLM call (text answer).
        assert elapsed < 1.3, (
            f"Query engine with two slow concurrent tools took {elapsed:.3f}s. "
            "Expected < 1.3s (0.5s concurrent dispatch + text answer overhead)."
        )
