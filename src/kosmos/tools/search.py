# SPDX-License-Identifier: Apache-2.0
"""BM25-based search for the KOSMOS Tool System.

Public API (for external callers):
- ``search(query, registry, top_k)`` — new BM25 facade returning ``AdapterCandidate`` objects.
- ``search_tools(tools, query, max_results)`` — legacy token-overlap function kept for
  backward compatibility with ``ToolRegistry.search()``; will be removed in a follow-on epic.
- ``create_search_meta_tool()`` — factory for the ``search_tools`` meta-tool definition.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from kosmos.tools.bm25_index import BM25Index
from kosmos.tools.models import (
    AdapterCandidate,
    GovAPITool,
    SearchToolsInput,
    SearchToolsOutput,
    ToolSearchResult,
)

if TYPE_CHECKING:
    from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Module-level BM25 index shared with the registry rebuild path.
# The registry calls ``_registry_bm25_index.rebuild(corpus)`` on every
# ``register()`` call; ``search()`` reads from it.
_registry_bm25_index: BM25Index = BM25Index({})


def search(
    query: str,
    registry: ToolRegistry,
    top_k: int | None = None,
) -> list[AdapterCandidate]:
    """BM25-ranked adapter search over the tool registry.

    Replaces the legacy token-overlap scoring.  Delegates scoring to the
    shared module-level ``BM25Index`` (kept in sync by ``registry.register()``).

    Adaptive top_k clamp (FR-009):
        effective_top_k = max(1, min(top_k if top_k else 5, len(registry), 20))

    Args:
        query: Free-text query in Korean or English.
        registry: The live ToolRegistry to search.
        top_k: Per-call override.  None → use default (5).

    Returns:
        Ranked list of AdapterCandidate entries.
    """
    registry_size = len(registry)
    default_k = 5
    raw_k = top_k if top_k is not None else default_k
    effective_top_k = max(1, min(raw_k, registry_size, 20))

    if registry_size == 0:
        return []

    scored = _registry_bm25_index.score(query)
    results: list[AdapterCandidate] = []

    for tool_id, score in scored[:effective_top_k]:
        try:
            tool = registry.lookup(tool_id)
        except Exception:  # pragma: no cover
            logger.warning("search: tool %r in BM25 index but not in registry", tool_id)
            continue

        required_params = _required_params(tool)
        candidate = AdapterCandidate(
            tool_id=tool_id,
            score=max(0.0, float(score)),
            required_params=required_params,
            search_hint=tool.search_hint,
            why_matched=f"BM25 score {score:.4f} on search_hint",
            requires_auth=tool.requires_auth,
            is_personal_data=tool.is_personal_data,
        )
        results.append(candidate)

    return results


def _required_params(tool: GovAPITool) -> list[str]:
    """Extract required parameter names from a tool's input_schema."""
    try:
        schema = tool.input_schema.model_json_schema()
        return list(schema.get("required", []))
    except Exception:  # pragma: no cover
        return []


# ---------------------------------------------------------------------------
# Legacy token-overlap function — kept for ToolRegistry.search() backward compat
# ---------------------------------------------------------------------------


def search_tools(
    tools: list[GovAPITool],
    query: str,
    max_results: int = 5,
) -> list[ToolSearchResult]:
    """Search tools by Korean or English keywords in search_hint.

    Legacy token-overlap algorithm retained for ToolRegistry.search() backward
    compatibility.  New code should use ``search()`` instead.

    Algorithm:
    1. Tokenize query into lowercase tokens (split by whitespace).
    2. If query is empty or only whitespace, return empty list.
    3. For each tool, tokenize its search_hint into lowercase tokens.
    4. Score = number of query tokens that are bidirectionally substring-matched
       against any search_hint token (case-insensitive, either token may contain
       the other).
    5. If score > 0, include in results.
    6. Sort by score descending.
    7. Return top max_results.

    Args:
        tools: All registered tool definitions to search over.
        query: Freeform Korean or English search string.
        max_results: Maximum number of results to return.

    Returns:
        Ranked list of :class:`ToolSearchResult` with score > 0,
        capped at *max_results* entries.
    """
    if max_results <= 0:
        return []

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
            # Bidirectional substring match: either token contains the other.
            if any(q_token in h_token or h_token in q_token for h_token in hint_tokens):
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

    results.sort(key=lambda r: (-r.score, r.tool.id))
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
