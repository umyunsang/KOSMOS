# Quickstart: Query Engine Core

**Feature**: Epic #5 — Query Engine Core
**Date**: 2026-04-13

## Prerequisites

```bash
# Install dependencies
uv sync

# Set environment variable (for integration tests only; unit tests use mocks)
export KOSMOS_FRIENDLI_TOKEN="your-token-here"
```

## Running Tests

```bash
# All query engine tests (unit only, no live API)
uv run pytest tests/engine/ -v

# With coverage
uv run pytest tests/engine/ --cov=kosmos.engine --cov-report=term-missing
```

---

## Test Scenario 1: Single-Turn Query Resolution (US-1, P1)

Validates the fundamental preprocess -> LLM call -> tool dispatch -> answer pipeline.

```python
import pytest
from kosmos.engine import QueryEngine, QueryEngineConfig, QueryEvent, StopReason

@pytest.mark.asyncio
async def test_single_turn_one_tool_call(
    mock_llm_client,          # Fixture: returns tool_call then final answer
    populated_registry,        # Fixture: registry with 4 tools registered
    tool_executor_with_mocks,  # Fixture: executor with mock adapters
):
    """Given a question requiring one tool call,
    the engine should loop twice (tool call + synthesis) and terminate."""
    engine = QueryEngine(
        llm_client=mock_llm_client,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
    )

    events = []
    async for event in engine.run("서울 강남구 교통사고 현황 알려줘"):
        events.append(event)

    # Must end with stop event
    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.task_complete

    # Must have tool_use and tool_result events
    tool_uses = [e for e in events if e.type == "tool_use"]
    tool_results = [e for e in events if e.type == "tool_result"]
    assert len(tool_uses) >= 1
    assert len(tool_results) >= 1


@pytest.mark.asyncio
async def test_single_turn_no_tool_call(
    mock_llm_client_no_tools,  # Fixture: returns direct text answer
    populated_registry,
    tool_executor_with_mocks,
):
    """Given a simple question needing no tools,
    the engine should return the answer directly."""
    engine = QueryEngine(
        llm_client=mock_llm_client_no_tools,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
    )

    events = []
    async for event in engine.run("안녕하세요"):
        events.append(event)

    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.end_turn
    # No tool events
    assert not any(e.type == "tool_use" for e in events)
```

---

## Test Scenario 2: Multi-Turn Conversation (US-2, P2)

Validates history accumulation and preprocessing across turns.

```python
@pytest.mark.asyncio
async def test_multi_turn_history_accumulates(
    mock_llm_client,
    populated_registry,
    tool_executor_with_mocks,
):
    """Given 3 sequential turns, messages accumulate in session state."""
    engine = QueryEngine(
        llm_client=mock_llm_client,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
    )

    for question in [
        "서울 강남구 교통사고 현황",
        "작년 대비 증감율은?",
        "사고 다발 지역 상위 3곳은?",
    ]:
        async for _ in engine.run(question):
            pass

    # History should contain messages from all 3 turns
    assert engine.message_count > 6  # At least 2 messages per turn
    # Turn count should be 3
    assert engine.budget.turns_used == 3


@pytest.mark.asyncio
async def test_immutable_snapshot_per_llm_call(
    mock_llm_client_inspectable,  # Fixture: records messages it receives
    populated_registry,
    tool_executor_with_mocks,
):
    """The LLM receives a snapshot copy, not the mutable list."""
    engine = QueryEngine(
        llm_client=mock_llm_client_inspectable,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
    )

    async for _ in engine.run("테스트"):
        pass

    # Inspect what the LLM received
    snapshot = mock_llm_client_inspectable.last_messages
    # Snapshot should be a different list object than the state's messages
    assert snapshot is not engine._state.messages
```

---

## Test Scenario 3: Budget Enforcement (US-3, P3)

Validates graceful termination when budgets are exceeded.

```python
@pytest.mark.asyncio
async def test_turn_budget_enforcement(
    mock_llm_client,
    populated_registry,
    tool_executor_with_mocks,
):
    """Given a 2-turn budget, the engine should stop at turn 3."""
    config = QueryEngineConfig(max_turns=2)
    engine = QueryEngine(
        llm_client=mock_llm_client,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=config,
    )

    # Turn 1 — should succeed
    async for _ in engine.run("첫 번째 질문"):
        pass

    # Turn 2 — should succeed
    async for _ in engine.run("두 번째 질문"):
        pass

    # Turn 3 — should be rejected with budget exceeded
    events = []
    async for event in engine.run("세 번째 질문"):
        events.append(event)

    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.api_budget_exceeded


@pytest.mark.asyncio
async def test_max_iterations_guard(
    mock_llm_client_infinite_tools,  # Fixture: always requests tool calls
    populated_registry,
    tool_executor_with_mocks,
):
    """Given an LLM that loops forever, max_iterations stops it."""
    config = QueryEngineConfig(max_iterations=3)
    engine = QueryEngine(
        llm_client=mock_llm_client_infinite_tools,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
        config=config,
    )

    events = []
    async for event in engine.run("무한 루프 테스트"):
        events.append(event)

    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.max_iterations_reached
```

---

## Test Scenario 4: Concurrent Tool Execution (US-4, P3)

Validates parallel dispatch of independent tools.

```python
import time

@pytest.mark.asyncio
async def test_concurrent_dispatch_reduces_latency(
    mock_llm_client_two_tools,  # Fixture: requests 2 tools simultaneously
    populated_registry_concurrent,  # Fixture: both tools are concurrency_safe
    tool_executor_with_slow_mocks,  # Fixture: each adapter sleeps 0.5s
):
    """Two concurrent-safe tools should execute in parallel."""
    config = QueryEngineConfig()
    engine = QueryEngine(
        llm_client=mock_llm_client_two_tools,
        tool_registry=populated_registry_concurrent,
        tool_executor=tool_executor_with_slow_mocks,
        config=config,
    )

    start = time.monotonic()
    async for _ in engine.run("교통사고 현황과 날씨 동시에 알려줘"):
        pass
    elapsed = time.monotonic() - start

    # Sequential would take ~1.0s; concurrent should be ~0.5s
    assert elapsed < 0.8  # 30%+ reduction per SC-004


@pytest.mark.asyncio
async def test_one_tool_fails_other_succeeds(
    mock_llm_client_two_tools,
    populated_registry_concurrent,
    tool_executor_one_fails,  # Fixture: tool A fails, tool B succeeds
):
    """Both results (success + error) are injected into history."""
    engine = QueryEngine(
        llm_client=mock_llm_client_two_tools,
        tool_registry=populated_registry_concurrent,
        tool_executor=tool_executor_one_fails,
    )

    events = []
    async for event in engine.run("두 가지 조회"):
        events.append(event)

    tool_results = [e for e in events if e.type == "tool_result"]
    assert len(tool_results) == 2
    successes = [r for r in tool_results if r.tool_result.success]
    failures = [r for r in tool_results if not r.tool_result.success]
    assert len(successes) == 1
    assert len(failures) == 1
```

---

## Edge Case Tests

```python
@pytest.mark.asyncio
async def test_unknown_tool_returns_error_result(
    mock_llm_client_unknown_tool,  # Fixture: requests non-existent tool
    populated_registry,
    tool_executor_with_mocks,
):
    """Unknown tool call should inject error ToolResult, not crash."""
    engine = QueryEngine(
        llm_client=mock_llm_client_unknown_tool,
        tool_registry=populated_registry,
        tool_executor=tool_executor_with_mocks,
    )

    events = []
    async for event in engine.run("테스트"):
        events.append(event)

    tool_results = [e for e in events if e.type == "tool_result"]
    assert any(not r.tool_result.success for r in tool_results)
    # Engine should NOT crash — must have a stop event
    assert events[-1].type == "stop"


@pytest.mark.asyncio
async def test_cancellation_stops_engine():
    """Breaking out of the async for should cancel in-flight work."""
    engine = QueryEngine(...)  # configured with slow mock tools

    count = 0
    async for event in engine.run("테스트"):
        count += 1
        if count >= 3:
            break  # Cancel mid-stream

    # No assertion — the test passes if no exception is raised
    # and no background tasks leak (verified by pytest-asyncio strict mode)
```
