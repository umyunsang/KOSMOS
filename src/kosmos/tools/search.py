# SPDX-License-Identifier: Apache-2.0
"""Bilingual (Korean + English) token-overlap search for the KOSMOS Tool System."""

from __future__ import annotations

from kosmos.tools.models import (
    GovAPITool,
    SearchToolsInput,
    SearchToolsOutput,
    ToolSearchResult,
)


def search_tools(
    tools: list[GovAPITool],
    query: str,
    max_results: int = 5,
) -> list[ToolSearchResult]:
    """Search tools by Korean or English keywords in search_hint.

    Algorithm:
    1. Tokenize query into lowercase tokens (split by whitespace).
    2. If query is empty or only whitespace, return empty list.
    3. For each tool, tokenize its search_hint into lowercase tokens.
    4. Score = number of query tokens that are substring-matched in any
       search_hint token (case-insensitive substring matching, not exact match).
    5. If score > 0, include in results.
    6. Sort by score descending.
    7. Return top max_results.

    Score normalization: score = matched_count / total_query_tokens
    This gives a 0.0 to 1.0 range.

    Args:
        tools: All registered tool definitions to search over.
        query: Freeform Korean or English search string.
        max_results: Maximum number of results to return.

    Returns:
        Ranked list of :class:`ToolSearchResult` with score > 0,
        capped at *max_results* entries.
    """
    query_stripped = query.strip()
    if not query_stripped:
        return []

    query_tokens = query_stripped.lower().split()
    total_query_tokens = len(query_tokens)

    results: list[ToolSearchResult] = []

    for tool in tools:
        hint_tokens = tool.search_hint.lower().split()

        matched: list[str] = []
        for q_token in query_tokens:
            # Substring match: q_token must appear inside at least one hint token.
            if any(q_token in h_token for h_token in hint_tokens):
                matched.append(q_token)

        if matched:
            score = len(matched) / total_query_tokens
            results.append(
                ToolSearchResult(
                    tool=tool,
                    score=score,
                    matched_tokens=matched,
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:max_results]


def create_search_meta_tool() -> GovAPITool:
    """Create the search_tools meta-tool for LLM discovery.

    This tool is registered in the ToolRegistry so the LLM can discover
    other tools via the search_tools function call.
    """
    return GovAPITool(
        id="search_tools",
        name_ko="도구검색",
        provider="KOSMOS",
        category=["시스템", "검색"],
        endpoint="internal://search_tools",
        auth_type="public",
        input_schema=SearchToolsInput,
        output_schema=SearchToolsOutput,
        search_hint="도구 검색 찾기 search tools find discover 도구목록",
        # Override fail-closed defaults for this internal tool.
        requires_auth=False,
        is_personal_data=False,
        is_concurrency_safe=True,
        cache_ttl_seconds=0,
        rate_limit_per_minute=60,
        is_core=True,
    )
