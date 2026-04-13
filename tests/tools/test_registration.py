# SPDX-License-Identifier: Apache-2.0
"""Tests for central tool registration entry point (T039)."""

import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry


class TestToolRegistration:
    """Verify register_all_tools() wires all adapters correctly."""

    def test_registers_all_tools(self) -> None:
        """All tools are registered after calling register_all_tools."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register_all_tools(registry, executor)
        assert len(registry) == 9

    def test_tool_ids_present(self) -> None:
        """Each expected tool_id is in the registry."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register_all_tools(registry, executor)
        expected = {
            "koroad_accident_search",
            "kma_weather_alert_status",
            "kma_current_observation",
            "road_risk_score",
            "address_to_region",
            "address_to_grid",
        }
        for tool_id in expected:
            assert tool_id in registry, f"{tool_id} not found in registry"

    def test_adapters_bound(self) -> None:
        """Each tool has a corresponding adapter in the executor."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register_all_tools(registry, executor)
        expected = {
            "koroad_accident_search",
            "kma_weather_alert_status",
            "kma_current_observation",
            "road_risk_score",
            "address_to_region",
            "address_to_grid",
        }
        for tool_id in expected:
            assert tool_id in executor._adapters, f"No adapter for {tool_id}"

    def test_no_import_errors(self) -> None:
        """register_all_tools completes without import errors."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        # Should not raise
        register_all_tools(registry, executor)

    def test_idempotent_fails_on_duplicate(self) -> None:
        """Calling register_all_tools twice raises DuplicateToolError."""
        from kosmos.tools.errors import DuplicateToolError

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register_all_tools(registry, executor)
        with pytest.raises(DuplicateToolError):
            register_all_tools(registry, executor)
