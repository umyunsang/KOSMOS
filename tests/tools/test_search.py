# SPDX-License-Identifier: Apache-2.0
"""Unit tests for bilingual (Korean + English) search in the KOSMOS Tool System.

All tests use mock tools from conftest fixtures — no live API calls are made.
"""

from __future__ import annotations

from kosmos.tools.models import GovAPITool, SearchToolsInput, SearchToolsOutput
from kosmos.tools.search import create_search_meta_tool, search_tools

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_ids(results) -> list[str]:
    """Extract tool IDs from a list of ToolSearchResult objects."""
    return [r.tool.id for r in results]


# ---------------------------------------------------------------------------
# Bilingual keyword matching
# ---------------------------------------------------------------------------


def test_korean_keyword_match(populated_registry):
    """Searching '날씨' should return the weather tool among results."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "날씨")

    assert results, "Expected at least one result for '날씨'"
    assert "kma_weather_forecast" in _tool_ids(results)


def test_english_keyword_match(populated_registry):
    """Searching 'weather' (English) should return the weather tool."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "weather")

    assert results, "Expected at least one result for 'weather'"
    assert "kma_weather_forecast" in _tool_ids(results)


def test_mixed_query(populated_registry):
    """Searching '날씨 weather' (two tokens) should score the weather tool higher
    than a single-token query that also matches one other tool."""
    tools = list(populated_registry._tools.values())

    single_results = search_tools(tools, "날씨")
    mixed_results = search_tools(tools, "날씨 weather")

    # Both queries must find the weather tool.
    assert "kma_weather_forecast" in _tool_ids(single_results)
    assert "kma_weather_forecast" in _tool_ids(mixed_results)

    # Mixed query: weather tool score must be >= single-token score
    # (both tokens match the weather hint, so score = 1.0 vs 1.0 for single token —
    # or mixed provides equal/higher score than any partially-matching rival).
    single_score = next(
        r.score for r in single_results if r.tool.id == "kma_weather_forecast"
    )
    mixed_score = next(
        r.score for r in mixed_results if r.tool.id == "kma_weather_forecast"
    )
    assert mixed_score >= single_score


# ---------------------------------------------------------------------------
# Empty / whitespace / no-match guards
# ---------------------------------------------------------------------------


def test_empty_query_returns_empty(populated_registry):
    """An empty string query must return an empty list."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "")

    assert results == []


def test_whitespace_query_returns_empty(populated_registry):
    """A whitespace-only query must return an empty list."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "   ")

    assert results == []


def test_no_match_returns_empty(populated_registry):
    """A query with no overlap against any hint must return an empty list."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "블록체인 blockchain")

    assert results == []


# ---------------------------------------------------------------------------
# max_results cap
# ---------------------------------------------------------------------------


def test_max_results_limit(populated_registry):
    """max_results=1 must return at most 1 result even if multiple tools match."""
    tools = list(populated_registry._tools.values())
    # "traffic" does not appear in any hint but "accident" appears in koroad hint.
    # Use a broad term present in multiple hints to guarantee multiple matches.
    results = search_tools(tools, "hospital traffic weather business", max_results=1)

    assert len(results) <= 1


# ---------------------------------------------------------------------------
# Score-based ranking
# ---------------------------------------------------------------------------


def test_score_ranking(populated_registry):
    """A query matching two tokens of the weather hint but only one token of
    another hint should rank the weather tool first."""
    tools = list(populated_registry._tools.values())

    # "날씨 weather" both appear only in the weather tool's hint.
    # "hospital" appears only in the hospital tool's hint.
    # Weather tool should have score 2/3, hospital 1/3 → weather ranks first.
    results = search_tools(tools, "날씨 weather hospital")

    assert results, "Expected results"
    assert results[0].tool.id == "kma_weather_forecast", (
        f"Expected weather tool first, got {results[0].tool.id}"
    )
    assert results[0].score >= results[1].score


# ---------------------------------------------------------------------------
# Substring matching
# ---------------------------------------------------------------------------


def test_substring_matching(populated_registry):
    """Query token '교통' should match hint token '교통사고' via substring matching."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "교통")

    assert results, "Expected at least one result for '교통'"
    assert "koroad_accident_stats" in _tool_ids(results)

    matched_result = next(r for r in results if r.tool.id == "koroad_accident_stats")
    assert "교통" in matched_result.matched_tokens


# ---------------------------------------------------------------------------
# Case-insensitive matching
# ---------------------------------------------------------------------------


def test_case_insensitive(populated_registry):
    """Uppercase query 'WEATHER' should still match lowercase 'weather' in hint."""
    tools = list(populated_registry._tools.values())
    results = search_tools(tools, "WEATHER")

    assert results, "Expected at least one result for 'WEATHER'"
    assert "kma_weather_forecast" in _tool_ids(results)


# ---------------------------------------------------------------------------
# create_search_meta_tool factory
# ---------------------------------------------------------------------------


def test_create_search_meta_tool():
    """The meta-tool returned by create_search_meta_tool must meet contract requirements."""
    meta_tool = create_search_meta_tool()

    assert isinstance(meta_tool, GovAPITool)
    assert meta_tool.id == "search_tools"
    assert meta_tool.is_core is True
    assert meta_tool.input_schema is SearchToolsInput
    assert meta_tool.output_schema is SearchToolsOutput
    # Internal tool must not require auth and must be concurrency-safe.
    assert meta_tool.requires_auth is False
    assert meta_tool.is_concurrency_safe is True
    assert meta_tool.is_personal_data is False
