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
    trigger_phrase: str | None = None,
) -> ToolDefinition:
    """Build a ToolDefinition fixture without importing from registry."""
    return ToolDefinition(
        type="function",
        function=FunctionSchema(
            name=name,
            description=description,
            parameters=parameters if parameters is not None else {},
            trigger_phrase=trigger_phrase,
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


# ---------------------------------------------------------------------------
# Epic #2152 R6 — per-tool trigger phrase emission invariants
# (contracts/system-prompt-builder.md I-B1..I-B6)
# ---------------------------------------------------------------------------


def test_trigger_line_present_per_tool() -> None:
    """I-B2 — every per-tool block emits exactly one ``**Trigger**: `` line
    immediately above ``**Parameters**:`` when ``trigger_phrase`` is set."""
    tool_with_trigger = _make_tool(
        name="resolve_location",
        description="Resolve a Korean place name to coordinates.",
        trigger_phrase=(
            '한국 지역의 위치, 주소, 역, 관공서 질문에 호출. — '
            '예: "강남역 어디야?", "서울시청 주소"'
        ),
    )
    result = build_system_prompt_with_tools(BASE_PROMPT, [tool_with_trigger])

    # Trigger line is present, exactly once.
    trigger_lines = [
        line for line in result.splitlines() if line.startswith("**Trigger**: ")
    ]
    assert len(trigger_lines) == 1, (
        f"Expected exactly one **Trigger**: line, got {len(trigger_lines)}"
    )

    # Trigger appears immediately before **Parameters**: with one blank line between.
    trigger_idx = result.index("**Trigger**:")
    params_idx = result.index("**Parameters**:")
    assert trigger_idx < params_idx
    between = result[trigger_idx:params_idx]
    assert between.count("\n") == 2, (
        f"Trigger and Parameters must be separated by exactly one blank line, "
        f"got {between.count(chr(10))} newlines between them"
    )


def test_trigger_line_no_examples() -> None:
    """I-B3 — when ``trigger_examples`` are absent, the trigger line carries
    no ``— 예:`` clause."""
    tool = _make_tool(
        name="lookup",
        description="Look up by tool_id.",
        trigger_phrase="시민의 메타 조회 호출.",
    )
    result = build_system_prompt_with_tools(BASE_PROMPT, [tool])
    assert "**Trigger**: 시민의 메타 조회 호출.\n" in result
    assert "— 예:" not in result


def test_trigger_line_with_examples_quotes() -> None:
    """I-B4 — every example utterance appears verbatim wrapped in double quotes."""
    examples = ["오늘 서울 날씨", "내일 부산 비 와?", "주말 제주 날씨"]
    tool = _make_tool(
        name="kma_forecast_fetch",
        description="KMA forecast.",
        trigger_phrase=(
            "한국 지역의 날씨 질문에 호출. — 예: "
            + ", ".join(f'"{ex}"' for ex in examples)
        ),
    )
    result = build_system_prompt_with_tools(BASE_PROMPT, [tool])
    for ex in examples:
        assert f'"{ex}"' in result


def test_trigger_line_omitted_when_phrase_none() -> None:
    """When ``trigger_phrase`` is None, no ``**Trigger**:`` line is emitted —
    backward-compatible behaviour for tools that have not opted in to R6."""
    result = build_system_prompt_with_tools(BASE_PROMPT, [LOOKUP_TOOL])
    assert "**Trigger**:" not in result


def test_base_unchanged_prefix_with_trigger() -> None:
    """I-B6 — the base prompt remains a strict prefix of the augmented output
    even when trigger phrases are present (augmentation only appends)."""
    tool = _make_tool(
        name="kma_forecast_fetch",
        description="KMA forecast.",
        trigger_phrase="날씨 질문에 호출.",
    )
    result = build_system_prompt_with_tools(BASE_PROMPT, [tool])
    assert result.startswith(BASE_PROMPT)


def test_trigger_line_deterministic() -> None:
    """I-B5 — two calls with the same trigger_phrase produce byte-identical output."""
    tool = _make_tool(
        name="koroad_accident_search",
        description="KOROAD accident hotspot search.",
        trigger_phrase='어린이 보호구역 사고 등 도로 안전 질문에 호출. — 예: "사고 다발"',
    )
    a = build_system_prompt_with_tools(BASE_PROMPT, [tool])
    b = build_system_prompt_with_tools(BASE_PROMPT, [tool])
    assert a == b
