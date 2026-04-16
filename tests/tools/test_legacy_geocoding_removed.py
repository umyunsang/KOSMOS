# SPDX-License-Identifier: Apache-2.0
"""T041 — Verify address_to_region and address_to_grid are NOT in the registry.

These tools were removed from the LLM-visible surface in spec/022-mvp-main-tool US4
(T049). This test guards against accidental re-registration.

After deletion:
  - registry.all_tools() must not contain either tool id.
  - lookup(mode='fetch', tool_id='address_to_region', ...) → LookupError(reason='unknown_tool').
  - lookup(mode='fetch', tool_id='address_to_grid', ...) → LookupError(reason='unknown_tool').
"""

from __future__ import annotations

import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import LookupError, LookupFetchInput  # noqa: A004
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry


@pytest.fixture()
def full_registry_and_executor() -> tuple[ToolRegistry, ToolExecutor]:
    """Full registry populated via register_all_tools."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register_all_tools(registry, executor)
    return registry, executor


class TestLegacyToolsNotInRegistry:
    def test_address_to_region_not_in_all_tools(
        self, full_registry_and_executor: tuple[ToolRegistry, ToolExecutor]
    ) -> None:
        registry, _ = full_registry_and_executor
        tool_ids = {t.id for t in registry.all_tools()}
        assert "address_to_region" not in tool_ids, (
            "address_to_region was found in the registry — it must be deleted (T049)."
        )

    def test_address_to_grid_not_in_all_tools(
        self, full_registry_and_executor: tuple[ToolRegistry, ToolExecutor]
    ) -> None:
        registry, _ = full_registry_and_executor
        tool_ids = {t.id for t in registry.all_tools()}
        assert "address_to_grid" not in tool_ids, (
            "address_to_grid was found in the registry — it must be deleted (T049)."
        )

    def test_address_to_region_module_not_importable(self) -> None:
        """The source module must be deleted — ImportError confirms removal."""
        with pytest.raises(ImportError):
            import kosmos.tools.geocoding.address_to_region  # noqa: F401

    def test_address_to_grid_module_not_importable(self) -> None:
        """The source module must be deleted — ImportError confirms removal."""
        with pytest.raises(ImportError):
            import kosmos.tools.geocoding.address_to_grid  # noqa: F401


class TestLookupFetchReturnsUnknownTool:
    @pytest.mark.asyncio
    async def test_address_to_region_fetch_returns_unknown_tool_error(
        self, full_registry_and_executor: tuple[ToolRegistry, ToolExecutor]
    ) -> None:
        from kosmos.tools.lookup import lookup

        registry, executor = full_registry_and_executor
        inp = LookupFetchInput(mode="fetch", tool_id="address_to_region", params={})
        result = await lookup(inp, registry=registry, executor=executor)
        assert isinstance(result, LookupError), f"Expected LookupError, got {type(result)}"
        assert result.reason == "unknown_tool", f"Expected 'unknown_tool', got {result.reason!r}"

    @pytest.mark.asyncio
    async def test_address_to_grid_fetch_returns_unknown_tool_error(
        self, full_registry_and_executor: tuple[ToolRegistry, ToolExecutor]
    ) -> None:
        from kosmos.tools.lookup import lookup

        registry, executor = full_registry_and_executor
        inp = LookupFetchInput(mode="fetch", tool_id="address_to_grid", params={})
        result = await lookup(inp, registry=registry, executor=executor)
        assert isinstance(result, LookupError), f"Expected LookupError, got {type(result)}"
        assert result.reason == "unknown_tool", f"Expected 'unknown_tool', got {result.reason!r}"
