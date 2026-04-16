# SPDX-License-Identifier: Apache-2.0
"""Central registry for KOSMOS government API tools."""

from __future__ import annotations

import logging

from kosmos.tools.errors import DuplicateToolError, RegistrationError, ToolNotFoundError
from kosmos.tools.models import GovAPITool, ToolSearchResult
from kosmos.tools.rate_limiter import RateLimiter
from kosmos.tools.search import _registry_bm25_index, search_tools

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for government API tools."""

    def __init__(self) -> None:
        self._tools: dict[str, GovAPITool] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}

    def register(self, tool: GovAPITool) -> None:
        """Register a tool.

        Raises:
            DuplicateToolError: If tool.id is already registered.
            RegistrationError: If ``is_personal_data=True`` without ``requires_auth=True``
                (FR-038 — fail-closed PII invariant).
        """
        if tool.id in self._tools:
            raise DuplicateToolError(tool.id)

        # FR-038: PII-flagged adapters MUST also require authentication.
        if tool.is_personal_data and not tool.requires_auth:
            raise RegistrationError(
                tool.id,
                "is_personal_data=True requires requires_auth=True (Constitution §II / FR-038)",
            )

        self._tools[tool.id] = tool
        self._rate_limiters[tool.id] = RateLimiter(
            limit=tool.rate_limit_per_minute,
        )

        # Rebuild BM25 index from the full current search_hint corpus so that
        # subsequent search() calls reflect the newly registered adapter.
        _registry_bm25_index.rebuild({tid: t.search_hint for tid, t in self._tools.items()})

        logger.info("Registered tool: %s", tool.id)

    def lookup(self, tool_id: str) -> GovAPITool:
        """Look up tool by id. Raises ToolNotFoundError if not found."""
        try:
            return self._tools[tool_id]
        except KeyError:
            raise ToolNotFoundError(tool_id) from None

    def all_tools(self) -> list[GovAPITool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def search(self, query: str, max_results: int = 5) -> list[ToolSearchResult]:
        """Search tools by Korean or English keywords in search_hint."""
        return search_tools(self.all_tools(), query, max_results)

    def core_tools(self) -> list[GovAPITool]:
        """Return core tools sorted by id (deterministic for prompt caching)."""
        return sorted(
            [t for t in self._tools.values() if t.is_core],
            key=lambda t: t.id,
        )

    def situational_tools(self) -> list[GovAPITool]:
        """Return non-core tools."""
        return [t for t in self._tools.values() if not t.is_core]

    def export_core_tools_openai(self) -> list[dict[str, object]]:
        """Export core tools as OpenAI function-calling definitions.

        Output is deterministic (sorted by id) for prompt cache stability.
        """
        return [t.to_openai_tool() for t in self.core_tools()]

    def get_rate_limiter(self, tool_id: str) -> RateLimiter:
        """Get the rate limiter for a tool.

        Raises ToolNotFoundError if tool_id is not registered.
        """
        if tool_id not in self._rate_limiters:
            raise ToolNotFoundError(tool_id)
        return self._rate_limiters[tool_id]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools
