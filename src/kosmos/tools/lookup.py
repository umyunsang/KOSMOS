# SPDX-License-Identifier: Apache-2.0
"""lookup facade coroutine — T024.

Single entry point for adapter discovery (search) and invocation (fetch).

FR-004: Dispatches on ``LookupInput.mode`` discriminator.
FR-005: search → BM25 retrieval gate via ``kosmos.tools.search.search()``.
FR-006: fetch → typed adapter invocation via ``executor.invoke()``.
FR-009: top_k adaptive clamp [1, 20], default from KOSMOS_LOOKUP_TOPK.
"""

from __future__ import annotations

import logging
import uuid

from kosmos.tools.models import (
    LookupCollection,
    LookupError,
    LookupFetchInput,
    LookupRecord,
    LookupSearchInput,
    LookupSearchResult,
    LookupTimeseries,
)

logger = logging.getLogger(__name__)


async def lookup(
    inp: LookupSearchInput | LookupFetchInput,
    *,
    registry: object | None = None,
    executor: object | None = None,
) -> (
    LookupSearchResult
    | LookupRecord
    | LookupCollection
    | LookupTimeseries
    | LookupError
):
    """Dispatch a lookup call by mode.

    Args:
        inp: Validated LookupSearchInput or LookupFetchInput.
        registry: ToolRegistry instance (required for search mode).
        executor: ToolExecutor instance (required for fetch mode).

    Returns:
        One of the 5 LookupOutput variants.
    """
    if isinstance(inp, LookupSearchInput):
        return await _lookup_search(inp, registry=registry)
    else:
        return await _lookup_fetch(inp, executor=executor)


async def _lookup_search(
    inp: LookupSearchInput,
    *,
    registry: object | None = None,
) -> LookupSearchResult:
    """Handle search mode: BM25 retrieval gate over adapter registry.

    FR-005, FR-009.
    """
    from kosmos.tools.registry import ToolRegistry
    from kosmos.tools.search import search

    if registry is None or not isinstance(registry, ToolRegistry):
        logger.warning("lookup search: no valid registry provided, returning empty")
        return LookupSearchResult(
            kind="search",
            candidates=[],
            total_registry_size=0,
            effective_top_k=0,
            reason="empty_registry",
        )

    registry_size = len(registry)

    if registry_size == 0:
        return LookupSearchResult(
            kind="search",
            candidates=[],
            total_registry_size=0,
            effective_top_k=0,
            reason="empty_registry",
        )

    # Compute effective top_k with adaptive clamp (FR-009)
    from kosmos.settings import settings

    default_k = settings.lookup_topk  # from KOSMOS_LOOKUP_TOPK
    raw_k = inp.top_k if inp.top_k is not None else default_k
    effective_top_k = max(1, min(raw_k, registry_size, 20))

    candidates = search(
        query=inp.query,
        registry=registry,
        top_k=effective_top_k,
    )

    # Optional domain filter: filter candidates by category tag
    if inp.domain is not None:
        domain_lower = inp.domain.lower()
        filtered = []
        for candidate in candidates:
            try:
                tool = registry.lookup(candidate.tool_id)
                if any(domain_lower in cat.lower() for cat in tool.category):
                    filtered.append(candidate)
            except Exception:
                filtered.append(candidate)
        candidates = filtered

    return LookupSearchResult(
        kind="search",
        candidates=candidates,
        total_registry_size=registry_size,
        effective_top_k=effective_top_k,
        reason="ok",
    )


async def _lookup_fetch(
    inp: LookupFetchInput,
    *,
    executor: object | None = None,
) -> LookupRecord | LookupCollection | LookupTimeseries | LookupError:
    """Handle fetch mode: typed adapter invocation via executor.

    FR-006, FR-017. Unknown tool_id → LookupError(reason="unknown_tool").
    Layer 3 gate and envelope normalization are handled inside executor.invoke().
    """
    from kosmos.tools.executor import ToolExecutor

    if executor is None or not isinstance(executor, ToolExecutor):
        return LookupError(
            kind="error",
            reason="unknown_tool",
            message=f"No executor available to invoke tool {inp.tool_id!r}.",
            retryable=False,
        )

    request_id = str(uuid.uuid4())

    result = await executor.invoke(
        tool_id=inp.tool_id,
        params=inp.params,
        request_id=request_id,
    )

    # executor.invoke() always returns a LookupOutput variant — pass through
    return result  # type: ignore[return-value]
