# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.llm.system_prompt_builder.build_system_prompt_with_tools.

Coverage table (contracts/system-prompt-builder.md § Test coverage):
  T1  test_empty_tools_returns_base_unchanged
  T2  test_single_tool_appends_section
  T3  test_byte_stable_for_same_input
  T4  test_korean_description_preserved
  T5  test_sort_keys_invariant
  T6  test_caller_order_preserved
  T7  test_no_timestamp_or_env_leakage
"""

from __future__ import annotations

from kosmos.llm.models import FunctionSchema, ToolDefinition
from kosmos.llm.system_prompt_builder import build_system_prompt_with_tools

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

BASE_PROMPT = (
    "You are a Korean public service AI assistant. "
    "Use available tools to answer citizen queries accurately."
)


def _make_tool(
    name: str,
    description: str,
    parameters: dict | None = None,
) -> ToolDefinition:
    """Build a ToolDefinition fixture without importing from registry."""
    return ToolDefinition(
        type="function",
        function=FunctionSchema(
            name=name,
            description=description,
            parameters=parameters if parameters is not None else {},
        ),
    )


LOOKUP_TOOL = _make_tool(
    name="lookup",
    description="Look up a public service by tool_id.",
    parameters={
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["search", "fetch"]},
            "tool_id": {"type": "string"},
        },
        "required": ["mode", "tool_id"],
    },
)

WEATHER_TOOL = _make_tool(
    name="kma_forecast_fetch",
    description="Fetch a KMA weather forecast for a given location.",
    parameters={
        "type": "object",
        "properties": {
            "nx": {"type": "integer"},
            "ny": {"type": "integer"},
        },
        "required": ["nx", "ny"],
    },
)


# ---------------------------------------------------------------------------
# T1 — empty tools list returns base unchanged
# ---------------------------------------------------------------------------


def test_empty_tools_returns_base_unchanged() -> None:
    """Output must be byte-identical to base when tools list is empty."""
    result = build_system_prompt_with_tools(BASE_PROMPT, [])
    assert result == BASE_PROMPT
    assert result is BASE_PROMPT  # same object — no copy made


# ---------------------------------------------------------------------------
# T2 — single tool appends section
# ---------------------------------------------------------------------------


def test_single_tool_appends_section() -> None:
    """Output must start with base and end with the per-tool Markdown block."""
    result = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL])

    # Base is preserved at the start
    assert result.startswith(BASE_PROMPT)

    # Section header is present
    assert "\n\n## Available tools\n\n" in result

    # Tool heading
    assert "### lookup\n" in result

    # Description
    assert "Look up a public service by tool_id." in result

    # Parameters block with JSON fences
    assert "**Parameters**:" in result
    assert "```json\n" in result
    assert "```" in result

    # Output ends with closing fence
    assert result.endswith("```")


# ---------------------------------------------------------------------------
# T3 — byte stability
# ---------------------------------------------------------------------------


def test_byte_stable_for_same_input() -> None:
    """Two calls with identical inputs must return identical strings."""
    result_a = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL])
    result_b = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL])
    assert result_a == result_b


# ---------------------------------------------------------------------------
# T4 — Korean characters round-trip (ensure_ascii=False)
# ---------------------------------------------------------------------------


def test_korean_description_preserved() -> None:
    """Korean characters in description must not be escaped as \\u… sequences."""
    korean_tool = _make_tool(
        name="hira_hospital_search",
        description="병원 정보를 검색합니다. 지역명과 진료과목으로 조회 가능합니다.",
        parameters={"type": "object", "properties": {"region": {"type": "string"}}},
    )
    result = build_system_prompt_with_tools(BASE_PROMPT, [korean_tool])

    # Korean text must appear literally — not as \uXXXX escapes
    assert "병원 정보를 검색합니다" in result
    assert "\\u" not in result


# ---------------------------------------------------------------------------
# T5 — sort_keys invariant
# ---------------------------------------------------------------------------


def test_sort_keys_invariant() -> None:
    """Same tool with different dict insertion order must produce identical output."""
    params_alpha = {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "date": {"type": "string"},
            "mode": {"type": "string"},
        },
    }
    # Same keys, different insertion order
    params_reversed = {
        "type": "object",
        "properties": {
            "mode": {"type": "string"},
            "date": {"type": "string"},
            "city": {"type": "string"},
        },
    }

    tool_a = _make_tool("weather", "Weather forecast.", params_alpha)
    tool_b = _make_tool("weather", "Weather forecast.", params_reversed)

    result_a = build_system_prompt_with_tools(BASE_PROMPT, [tool_a])
    result_b = build_system_prompt_with_tools(BASE_PROMPT, [tool_b])
    assert result_a == result_b


# ---------------------------------------------------------------------------
# T6 — caller order preserved (helper does NOT sort internally)
# ---------------------------------------------------------------------------


def test_caller_order_preserved() -> None:
    """Outputs for [LOOKUP, WEATHER] and [WEATHER, LOOKUP] must differ."""
    result_lw = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL, WEATHER_TOOL])
    result_wl = build_system_prompt_with_tools(BASE_PROMPT, [WEATHER_TOOL, LOOKUP_TOOL])

    assert result_lw != result_wl

    # Positional check: lookup appears before kma_forecast_fetch in first result
    assert result_lw.index("### lookup") < result_lw.index("### kma_forecast_fetch")
    # And reversed in the second result
    assert result_wl.index("### kma_forecast_fetch") < result_wl.index("### lookup")


# ---------------------------------------------------------------------------
# T7 — no timestamp or env variable leakage
# ---------------------------------------------------------------------------


def test_no_timestamp_or_env_leakage() -> None:
    """The function must not inject current-year strings or KOSMOS_ env var names."""
    result = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL, WEATHER_TOOL])

    # No year strings (determinism check — no datetime.now() calls)
    assert "2026" not in result
    assert "2025" not in result

    # No env var names (no os.environ lookups inside the helper)
    assert "KOSMOS_" not in result
