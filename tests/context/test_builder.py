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
- SC-006: build_assembled_context() benchmark — 50 tasks / 20 tools (T027)
- SC-007: No @pytest.mark.live markers in tests/context/ (T030)
- WARNING log when all registered tools are situational (T031)
"""

from __future__ import annotations

import logging
import pathlib

from pydantic import BaseModel, ConfigDict

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
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
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


# ---------------------------------------------------------------------------
# T027: SC-006 build_assembled_context() performance benchmark
# ---------------------------------------------------------------------------


class _BenchInput(BaseModel):
    """Minimal benchmark input schema."""

    model_config = ConfigDict(frozen=True)
    q: str = ""


class _BenchOutput(BaseModel):
    """Minimal benchmark output schema."""

    model_config = ConfigDict(frozen=True)
    r: str = ""


def test_build_assembled_context_performance(benchmark) -> None:  # type: ignore[no-untyped-def]
    """SC-006: build_assembled_context() completes in under 10ms with 50 tasks and 20 tools."""
    # Setup: create registry with 20 tools
    registry = ToolRegistry()
    for i in range(20):
        tool = GovAPITool(
            id=f"bench_tool_{i:03d}",
            name_ko=f"벤치마크 도구 {i}",
            provider="test",
            category=["test"],
            endpoint="https://example.com",
            auth_type="public",
            input_schema=_BenchInput,
            output_schema=_BenchOutput,
            search_hint=f"benchmark test tool {i}",
            auth_level="public",
            pipa_class="non_personal",
            is_irreversible=False,
            dpa_reference=None,
            is_core=True,
        )
        registry.register(tool)

    # Setup: state with 50 resolved tasks
    state = QueryState(
        usage=UsageTracker(budget=1_000_000),
        resolved_tasks=[f"Task {i} completed" for i in range(50)],
        turn_count=10,
    )

    builder = ContextBuilder(registry=registry)

    # Benchmark: real-world pattern — first call caches system message, subsequent calls reuse it
    result = benchmark(builder.build_assembled_context, state)
    assert result is not None
    assert result.budget is not None

    # Soft assertion: mean latency should be under 10ms
    # pytest-benchmark reports stats.mean in seconds
    # stats is None when benchmarks are disabled (e.g. under xdist)
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 0.010, (
            f"build_assembled_context mean latency "
            f"{benchmark.stats['mean'] * 1000:.2f}ms "
            "exceeds 10ms budget (SC-006)"
        )


# ---------------------------------------------------------------------------
# T030: SC-007 No @pytest.mark.live markers in tests/context/
# ---------------------------------------------------------------------------


def test_no_live_markers_in_context_tests() -> None:
    """SC-007: No @pytest.mark.live decorator usages in tests/context/."""
    import ast as _ast

    context_test_dir = pathlib.Path(__file__).parent
    for py_file in sorted(context_test_dir.glob("*.py")):
        source = py_file.read_text()
        # Use AST to find actual decorator nodes, avoiding false positives
        # in docstrings, comments, or test assertions that mention the marker name.
        try:
            tree = _ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                for deco in node.decorator_list:
                    deco_src = _ast.unparse(deco)
                    assert "pytest.mark.live" not in deco_src, (
                        f"{py_file.name}: found @pytest.mark.live decorator on line {deco.lineno}"
                    )


# ---------------------------------------------------------------------------
# T031: WARNING log when all registered tools are situational (no core tools)
# ---------------------------------------------------------------------------


def test_all_tools_situational_warning(caplog) -> None:  # type: ignore[no-untyped-def]
    """Verify WARNING log fires when no core tools are registered."""
    # Create registry with only situational (non-core) tools

    class _Input(BaseModel):
        model_config = ConfigDict(frozen=True)
        q: str = ""

    class _Output(BaseModel):
        model_config = ConfigDict(frozen=True)
        r: str = ""

    registry = ToolRegistry()
    tool = GovAPITool(
        id="situational_only",
        name_ko="상황 도구",
        provider="test",
        category=["test"],
        endpoint="https://example.com",
        auth_type="public",
        input_schema=_Input,
        output_schema=_Output,
        search_hint="situational test",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        is_core=False,  # NOT core
    )
    registry.register(tool)

    builder = ContextBuilder(registry=registry)
    state = QueryState(
        usage=UsageTracker(budget=1_000_000),
        active_situational_tools={"situational_only"},
    )

    with caplog.at_level(logging.WARNING, logger="kosmos.context.builder"):
        builder.build_assembled_context(state)

    assert any("No core tools registered" in r.message for r in caplog.records), (
        "Expected WARNING about no core tools being registered"
    )
