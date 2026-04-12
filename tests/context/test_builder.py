# SPDX-License-Identifier: Apache-2.0
"""Tests for ContextBuilder (US1-US4 integration).

Covers:
- build_system_message() returns ChatMessage with role=system
- build_system_message() caches result (same object on second call)
- Custom SystemPromptConfig is reflected in system message content
- build_turn_attachment() returns None for empty sessions
- build_turn_attachment() returns ContextLayer when resolved tasks exist
- Returned attachment has correct layer_name and role
- _build_tool_definitions() returns empty list when registry=None
- Core tools appear in definitions list
- Situational tools appear when activated in state
- build_assembled_context() returns AssembledContext with budget populated
- system_layer is always present in AssembledContext
"""

from __future__ import annotations

from pydantic import BaseModel

from kosmos.context.builder import ContextBuilder
from kosmos.context.models import SystemPromptConfig
from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.models import QueryState
from kosmos.llm.usage import UsageTracker
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockInput(BaseModel):
    query: str


class _MockOutput(BaseModel):
    result: str


def _make_tool(tool_id: str = "test_tool", is_core: bool = False) -> GovAPITool:
    """Create a minimal GovAPITool for test use."""
    return GovAPITool(
        id=tool_id,
        name_ko="테스트",
        provider="테스트기관",
        category=["테스트"],
        endpoint="http://test.example.com",
        auth_type="public",
        input_schema=_MockInput,
        output_schema=_MockOutput,
        search_hint="test search hint",
        is_core=is_core,
    )


def _make_state(**kwargs) -> QueryState:
    """Create a QueryState with default UsageTracker for testing."""
    config = QueryEngineConfig()
    usage = UsageTracker(budget=config.context_window)
    return QueryState(usage=usage, **kwargs)


# ---------------------------------------------------------------------------
# Tests: build_system_message()
# ---------------------------------------------------------------------------


class TestContextBuilderSystemMessage:
    """build_system_message() caches and returns ChatMessage."""

    def test_returns_chat_message(self) -> None:
        """Returns a ChatMessage with role='system' and non-empty content."""
        from kosmos.llm.models import ChatMessage

        builder = ContextBuilder()
        msg = builder.build_system_message()
        assert isinstance(msg, ChatMessage)
        assert msg.role == "system"
        assert msg.content is not None
        assert len(msg.content.strip()) > 0

    def test_cached_on_second_call(self) -> None:
        """Second call returns the exact same object (is-identity)."""
        builder = ContextBuilder()
        first = builder.build_system_message()
        second = builder.build_system_message()
        assert first is second

    def test_custom_config(self) -> None:
        """Custom platform_name appears in the assembled system message."""
        config = SystemPromptConfig(platform_name="TEST")
        builder = ContextBuilder(config=config)
        msg = builder.build_system_message()
        assert "TEST" in (msg.content or "")


# ---------------------------------------------------------------------------
# Tests: build_turn_attachment()
# ---------------------------------------------------------------------------


class TestContextBuilderAttachment:
    """build_turn_attachment() produces ContextLayer or None."""

    def test_empty_session_returns_none(self) -> None:
        """Fresh QueryState with no tasks → None."""
        builder = ContextBuilder()
        state = _make_state(turn_count=0)
        result = builder.build_turn_attachment(state=state)
        assert result is None

    def test_with_resolved_tasks(self) -> None:
        """State with resolved tasks → returns a ContextLayer."""
        from kosmos.context.models import ContextLayer

        builder = ContextBuilder()
        state = _make_state(turn_count=0, resolved_tasks=["Task completed"])
        result = builder.build_turn_attachment(state=state)
        assert result is not None
        assert isinstance(result, ContextLayer)
        assert "Task completed" in result.content

    def test_layer_name(self) -> None:
        """Returned ContextLayer has layer_name='turn_attachment'."""
        builder = ContextBuilder()
        state = _make_state(turn_count=0, resolved_tasks=["Some task"])
        result = builder.build_turn_attachment(state=state)
        assert result is not None
        assert result.layer_name == "turn_attachment"

    def test_role_is_user(self) -> None:
        """Returned ContextLayer has role='user'."""
        builder = ContextBuilder()
        state = _make_state(turn_count=0, resolved_tasks=["Another task"])
        result = builder.build_turn_attachment(state=state)
        assert result is not None
        assert result.role == "user"


# ---------------------------------------------------------------------------
# Tests: _build_tool_definitions()
# ---------------------------------------------------------------------------


class TestContextBuilderToolDefinitions:
    """_build_tool_definitions() partitions core and situational tools."""

    def test_no_registry_returns_empty(self) -> None:
        """ContextBuilder(registry=None) → empty tool definitions list."""
        builder = ContextBuilder(registry=None)
        state = _make_state()
        defs = builder._build_tool_definitions(state)
        assert defs == []

    def test_core_tools_included(self) -> None:
        """A registered core tool appears in the definitions."""
        registry = ToolRegistry()
        core_tool = _make_tool(tool_id="core_tool", is_core=True)
        registry.register(core_tool)
        builder = ContextBuilder(registry=registry)
        state = _make_state()
        defs = builder._build_tool_definitions(state)
        assert len(defs) == 1
        # OpenAI function-calling format: {"type": "function", "function": {...}}
        tool_names = [d["function"]["name"] for d in defs]  # type: ignore[index]
        assert "core_tool" in tool_names

    def test_situational_tools_included(self) -> None:
        """Situational tool activated in state.active_situational_tools appears in defs."""
        registry = ToolRegistry()
        sit_tool = _make_tool(tool_id="sit_tool", is_core=False)
        registry.register(sit_tool)
        builder = ContextBuilder(registry=registry)
        state = _make_state(active_situational_tools={"sit_tool"})
        defs = builder._build_tool_definitions(state)
        assert len(defs) == 1
        tool_names = [d["function"]["name"] for d in defs]  # type: ignore[index]
        assert "sit_tool" in tool_names


# ---------------------------------------------------------------------------
# Tests: build_assembled_context()
# ---------------------------------------------------------------------------


class TestContextBuilderAssembledContext:
    """build_assembled_context() returns full AssembledContext with budget."""

    def test_returns_assembled_context(self) -> None:
        """build_assembled_context() returns an AssembledContext instance."""
        from kosmos.context.models import AssembledContext

        builder = ContextBuilder()
        state = _make_state()
        ctx = builder.build_assembled_context(state=state)
        assert isinstance(ctx, AssembledContext)

    def test_budget_is_populated(self) -> None:
        """Returned AssembledContext has a non-None budget with estimated_tokens >= 0."""
        builder = ContextBuilder()
        state = _make_state()
        ctx = builder.build_assembled_context(state=state)
        assert ctx.budget is not None
        assert ctx.budget.estimated_tokens >= 0
        assert ctx.budget.hard_limit_tokens > 0
        assert ctx.budget.soft_limit_tokens > 0

    def test_system_layer_present(self) -> None:
        """system_layer is always present and has role='system'."""
        builder = ContextBuilder()
        state = _make_state()
        ctx = builder.build_assembled_context(state=state)
        assert ctx.system_layer is not None
        assert ctx.system_layer.role == "system"
        assert ctx.system_layer.layer_name == "system_prompt"
        assert len(ctx.system_layer.content.strip()) > 0
