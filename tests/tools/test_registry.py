# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ToolRegistry registration and lookup."""

from __future__ import annotations

import pytest

from kosmos.tools.errors import DuplicateToolError, ToolNotFoundError
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_success(sample_tool_factory):
    """Registering a tool should make it retrievable from the registry."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id="tool_a")
    registry.register(tool)
    assert "tool_a" in registry


def test_register_multiple_tools(sample_tool_factory):
    """Registering three distinct tools should result in a registry of length 3."""
    registry = ToolRegistry()
    for tool_id in ("tool_x", "tool_y", "tool_z"):
        registry.register(sample_tool_factory(id=tool_id))
    assert len(registry) == 3


def test_duplicate_registration_raises(sample_tool_factory):
    """Registering the same tool id twice must raise DuplicateToolError."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id="dup_tool")
    registry.register(tool)
    with pytest.raises(DuplicateToolError):
        registry.register(sample_tool_factory(id="dup_tool"))


def test_duplicate_error_contains_tool_id(sample_tool_factory):
    """DuplicateToolError must carry the offending tool_id as an attribute."""
    registry = ToolRegistry()
    tool_id = "dup_id_check"
    registry.register(sample_tool_factory(id=tool_id))
    with pytest.raises(DuplicateToolError) as exc_info:
        registry.register(sample_tool_factory(id=tool_id))
    assert exc_info.value.tool_id == tool_id


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def test_lookup_success(sample_tool_factory):
    """Looking up a registered tool by id should return the exact same object."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id="lookup_target")
    registry.register(tool)
    result = registry.lookup("lookup_target")
    assert result is tool


def test_lookup_not_found(sample_tool_factory):
    """Looking up an id that was never registered must raise ToolNotFoundError."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="existing_tool"))
    with pytest.raises(ToolNotFoundError):
        registry.lookup("nonexistent_tool")


def test_not_found_error_contains_tool_id(sample_tool_factory):
    """ToolNotFoundError must carry the missing tool_id as an attribute."""
    registry = ToolRegistry()
    missing_id = "ghost_tool"
    with pytest.raises(ToolNotFoundError) as exc_info:
        registry.lookup(missing_id)
    assert exc_info.value.tool_id == missing_id


# ---------------------------------------------------------------------------
# Collection methods
# ---------------------------------------------------------------------------


def test_all_tools(sample_tool_factory):
    """all_tools() must return every registered tool."""
    registry = ToolRegistry()
    ids = {"alpha", "beta", "gamma"}
    for tool_id in ids:
        registry.register(sample_tool_factory(id=tool_id))
    returned_ids = {t.id for t in registry.all_tools()}
    assert returned_ids == ids


def test_all_tools_empty():
    """all_tools() on a fresh registry must return an empty list."""
    registry = ToolRegistry()
    assert registry.all_tools() == []


# ---------------------------------------------------------------------------
# Dunder methods
# ---------------------------------------------------------------------------


def test_len_empty():
    """A freshly created registry must report length 0."""
    registry = ToolRegistry()
    assert len(registry) == 0


def test_len_with_tools(sample_tool_factory):
    """A registry with two registered tools must report length 2."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="t1"))
    registry.register(sample_tool_factory(id="t2"))
    assert len(registry) == 2


def test_contains_registered(sample_tool_factory):
    """The `in` operator must return True for a registered tool id."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="present_tool"))
    assert "present_tool" in registry


def test_contains_not_registered():
    """The `in` operator must return False for an unknown tool id."""
    registry = ToolRegistry()
    assert "unknown_id" not in registry


# ---------------------------------------------------------------------------
# Prompt cache partitioning — core_tools / situational_tools
# ---------------------------------------------------------------------------


def test_core_tools_returns_only_core(sample_tool_factory):
    """core_tools() must return exactly the tools registered with is_core=True."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="core_a", is_core=True))
    registry.register(sample_tool_factory(id="core_b", is_core=True))
    registry.register(sample_tool_factory(id="sit_c", is_core=False))
    core = registry.core_tools()
    assert len(core) == 2
    assert {t.id for t in core} == {"core_a", "core_b"}


def test_situational_tools_returns_only_non_core(sample_tool_factory):
    """situational_tools() must return exactly the tools registered with is_core=False."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="core_a", is_core=True))
    registry.register(sample_tool_factory(id="sit_b", is_core=False))
    registry.register(sample_tool_factory(id="sit_c", is_core=False))
    situational = registry.situational_tools()
    assert len(situational) == 2
    assert {t.id for t in situational} == {"sit_b", "sit_c"}


def test_core_and_situational_disjoint(sample_tool_factory):
    """core_tools() and situational_tools() must be disjoint and together cover all tools."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="core_a", is_core=True))
    registry.register(sample_tool_factory(id="core_b", is_core=True))
    registry.register(sample_tool_factory(id="sit_c", is_core=False))
    registry.register(sample_tool_factory(id="sit_d", is_core=False))
    core_ids = {t.id for t in registry.core_tools()}
    sit_ids = {t.id for t in registry.situational_tools()}
    assert core_ids & sit_ids == set()
    assert len(core_ids) + len(sit_ids) == len(registry)


def test_core_tools_sorted_by_id(sample_tool_factory):
    """core_tools() must return tools sorted alphabetically by id."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="z_tool", is_core=True))
    registry.register(sample_tool_factory(id="a_tool", is_core=True))
    registry.register(sample_tool_factory(id="m_tool", is_core=True))
    returned_ids = [t.id for t in registry.core_tools()]
    assert returned_ids == ["a_tool", "m_tool", "z_tool"]


def test_export_core_tools_openai_deterministic(sample_tool_factory):
    """export_core_tools_openai() must return identical results on successive calls."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="c_tool", is_core=True))
    registry.register(sample_tool_factory(id="a_tool", is_core=True))
    registry.register(sample_tool_factory(id="b_tool", is_core=True))
    first = registry.export_core_tools_openai()
    second = registry.export_core_tools_openai()
    assert first == second
    assert [item["function"]["name"] for item in first] == [  # type: ignore[index]
        item["function"]["name"] for item in second  # type: ignore[index]
    ]


def test_export_core_tools_openai_format(sample_tool_factory):
    """export_core_tools_openai() must produce valid OpenAI function-calling definitions."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="fmt_tool", is_core=True))
    result = registry.export_core_tools_openai()
    assert len(result) == 1
    item = result[0]
    assert item["type"] == "function"
    func = item["function"]
    assert "name" in func
    assert "parameters" in func


def test_empty_core_tools(sample_tool_factory):
    """core_tools() and export_core_tools_openai() return empty lists when no core tools exist."""
    registry = ToolRegistry()
    registry.register(sample_tool_factory(id="sit_a", is_core=False))
    registry.register(sample_tool_factory(id="sit_b", is_core=False))
    assert registry.core_tools() == []
    assert registry.export_core_tools_openai() == []


# ---------------------------------------------------------------------------
# Rate limiter access
# ---------------------------------------------------------------------------


def test_get_rate_limiter_registered(sample_tool_factory):
    """get_rate_limiter() must return a RateLimiter with the correct limit for a registered tool."""
    from kosmos.tools.rate_limiter import RateLimiter

    registry = ToolRegistry()
    tool = sample_tool_factory(id="rl_tool", rate_limit_per_minute=30)
    registry.register(tool)
    limiter = registry.get_rate_limiter("rl_tool")
    assert isinstance(limiter, RateLimiter)
    assert limiter.limit == 30


def test_get_rate_limiter_not_found():
    """get_rate_limiter() must raise ToolNotFoundError for an unregistered tool id."""
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get_rate_limiter("nonexistent")
