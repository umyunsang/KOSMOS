# SPDX-License-Identifier: Apache-2.0
"""Integration tests: QueryEngine + ContextBuilder wiring (T025).

Covers:
- Engine uses ContextBuilder.build_system_message() for the initial system prompt.
- Default ContextBuilder (no explicit arg) produces a valid system message.
- Custom ContextBuilder with custom SystemPromptConfig is reflected in state.
- build_turn_attachment() returning None does not insert an extra message.
- build_assembled_context() budget check does not block when budget is healthy.
- build_assembled_context() budget check blocks when token budget is exhausted.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from kosmos.context.builder import ContextBuilder
from kosmos.context.models import SystemPromptConfig
from kosmos.context.system_prompt import SystemPromptAssembler
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext
from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage, StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# Force QueryContext to resolve the LLMClient forward reference so that
# mock subclasses pass the isinstance check inside QueryContext validation.
QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Minimal mock infrastructure (self-contained; no conftest imports needed)
# ---------------------------------------------------------------------------

_SIMPLE_TEXT_RESPONSE: list[StreamEvent] = [
    StreamEvent(type="content_delta", content="Hello from KOSMOS."),
    StreamEvent(type="usage", usage=TokenUsage(input_tokens=10, output_tokens=5)),
    StreamEvent(type="done"),
]


class _MockLLMClientBase(LLMClient):
    """Subclass of LLMClient that skips __init__ to avoid needing a real API token."""

    def __new__(cls, *args: object, **kwargs: object) -> _MockLLMClientBase:
        return object.__new__(cls)  # type: ignore[return-value]


class _SimpleMockClient(_MockLLMClientBase):
    """Minimal mock LLM client that always returns a single text response."""

    def __init__(self, budget: int = 100_000) -> None:
        self._usage = UsageTracker(budget=budget)

    @property
    def usage(self) -> UsageTracker:  # type: ignore[override]
        return self._usage

    async def stream(  # type: ignore[override]
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        for event in _SIMPLE_TEXT_RESPONSE:
            yield event


def _make_registry() -> ToolRegistry:
    """Return a ToolRegistry with one minimal mock tool."""
    from pydantic import BaseModel

    class _In(BaseModel):
        query: str

    class _Out(BaseModel):
        result: str

    registry = ToolRegistry()
    registry.register(
        GovAPITool(
            id="test_tool",
            name_ko="테스트 도구",
            provider="mock",
            category=["mock"],
            endpoint="https://mock.example.com/api",
            auth_type="public",
            input_schema=_In,
            output_schema=_Out,
            search_hint="test tool mock",
            is_core=True,
            requires_auth=False,
            is_personal_data=False,
            is_concurrency_safe=True,
            cache_ttl_seconds=0,
            rate_limit_per_minute=60,
        )
    )
    return registry


def _make_executor(registry: ToolRegistry) -> ToolExecutor:
    """Return a ToolExecutor with a no-op adapter for the mock tool."""
    executor = ToolExecutor(registry)

    async def _adapter(validated_input: object) -> dict[str, object]:
        return {"result": "mock"}

    executor.register_adapter("test_tool", _adapter)
    return executor


async def _collect(engine: QueryEngine, message: str) -> list[QueryEvent]:
    """Drain engine.run(message) and return all events."""
    return [event async for event in engine.run(message)]


# ---------------------------------------------------------------------------
# Test 1: Engine uses ContextBuilder.build_system_message() for system prompt
# ---------------------------------------------------------------------------


def test_engine_uses_context_builder_system_message() -> None:
    """QueryEngine with explicit ContextBuilder reflects that builder's system message."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    builder = ContextBuilder()
    expected_content = builder.build_system_message().content

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
        context_builder=builder,
    )

    first_msg = engine._state.messages[0]  # noqa: SLF001
    assert first_msg.role == "system"
    assert first_msg.content == expected_content


# ---------------------------------------------------------------------------
# Test 2: Default engine (no context_builder arg) still produces a system message
# ---------------------------------------------------------------------------


def test_engine_default_context_builder_produces_system_message() -> None:
    """QueryEngine without context_builder creates a default one internally."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
    )

    first_msg = engine._state.messages[0]  # noqa: SLF001
    assert first_msg.role == "system"
    assert first_msg.content  # must be non-empty
    assert len(engine._state.messages) == 1  # noqa: SLF001


# ---------------------------------------------------------------------------
# Test 3: Custom SystemPromptConfig platform_name is reflected in the system message
# ---------------------------------------------------------------------------


def test_engine_custom_platform_name_via_context_builder() -> None:
    """ContextBuilder built with a custom SystemPromptConfig uses that platform name."""
    custom_name = "RoadSafetyAssistant"
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    builder = ContextBuilder(config=SystemPromptConfig(platform_name=custom_name))
    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
        context_builder=builder,
    )

    first_msg = engine._state.messages[0]  # noqa: SLF001
    assert first_msg.role == "system"
    assert custom_name in first_msg.content


# ---------------------------------------------------------------------------
# Test 4: No extra message appended when turn attachment returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_extra_message_when_turn_attachment_is_none() -> None:
    """build_turn_attachment() returning None must not add any extra messages."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
    )

    initial_count = engine.message_count  # 1 (system only)

    await _collect(engine, "Hello!")

    # After one no-tool turn: system + user + assistant = 3 messages.
    # No extra attachment message must have been injected.
    assert engine.message_count == initial_count + 2


# ---------------------------------------------------------------------------
# Test 5: Healthy budget does not block engine.run()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthy_budget_does_not_block_run() -> None:
    """Engine proceeds normally when token budget is not exhausted."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient(budget=100_000)

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
    )

    events = await _collect(engine, "Test message")

    assert events[-1].type == "stop"
    assert events[-1].stop_reason == StopReason.end_turn


# ---------------------------------------------------------------------------
# Test 6: Exhausted token budget triggers api_budget_exceeded via context builder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exhausted_budget_triggers_api_budget_exceeded() -> None:
    """When the token budget is exhausted, engine.run() yields api_budget_exceeded.

    This verifies the context-builder budget-check path (assembled.budget.is_over_limit)
    in addition to the existing direct UsageTracker check in engine.run().
    """
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient(budget=100)

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
    )

    # Manually exhaust the token budget via the usage tracker
    client.usage.debit(TokenUsage(input_tokens=50, output_tokens=50))
    assert client.usage.is_exhausted

    events = await _collect(engine, "This should be blocked")

    assert len(events) == 1
    assert events[0].type == "stop"
    assert events[0].stop_reason == StopReason.api_budget_exceeded


# ---------------------------------------------------------------------------
# Test 7: build_system_message output matches ContextBuilder defaults
# ---------------------------------------------------------------------------


def test_context_builder_system_message_matches_default_config() -> None:
    """ContextBuilder().build_system_message() returns the default SystemPromptConfig content."""
    builder = ContextBuilder()
    msg = builder.build_system_message()

    expected = SystemPromptAssembler().assemble(SystemPromptConfig())
    assert msg.role == "system"
    assert msg.content == expected


# ---------------------------------------------------------------------------
# Test 8: Engine _context_builder attribute is set correctly
# ---------------------------------------------------------------------------


def test_engine_context_builder_attribute() -> None:
    """engine._context_builder references the injected or default ContextBuilder."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    builder = ContextBuilder()
    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
        context_builder=builder,
    )

    assert engine._context_builder is builder  # noqa: SLF001


def test_engine_creates_default_context_builder_when_none() -> None:
    """Engine creates a ContextBuilder internally when context_builder=None."""
    registry = _make_registry()
    executor = _make_executor(registry)
    client = _SimpleMockClient()

    engine = QueryEngine(
        llm_client=client,
        tool_registry=registry,
        tool_executor=executor,
    )

    assert isinstance(engine._context_builder, ContextBuilder)  # noqa: SLF001
