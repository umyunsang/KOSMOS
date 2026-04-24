# SPDX-License-Identifier: Apache-2.0
"""E2E smoke test: observability wiring (T028).

Boots the full stack with MetricsCollector + ObservabilityEventLogger (no live
API calls, using mock adapters).  Dispatches one tool call through
PermissionPipeline → ToolExecutor → mock adapter.

Asserts:
- tool.call_count non-zero
- permission.decision_count non-zero
- kosmos.events logger received at least one valid JSON line

AC-A12: integration coverage for all four instrumentation areas.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from kosmos.observability import MetricsCollector, ObservabilityEventLogger
from kosmos.permissions.models import SessionContext
from kosmos.permissions.pipeline import PermissionPipeline
from kosmos.permissions.steps.refusal_circuit_breaker import reset_all
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal mock tool
# ---------------------------------------------------------------------------


class _MockInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = "test"


class _MockOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: str = "ok"


def _make_tool(tool_id: str = "mock_tool") -> GovAPITool:
    return GovAPITool(
        id=tool_id,
        name_ko="모의도구",
        ministry="OTHER",
        category=["테스트"],
        endpoint="http://example.com/api",
        auth_type="public",
        input_schema=_MockInput,
        output_schema=_MockOutput,
        search_hint="mock tool 테스트",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_personal_data=False,
        rate_limit_per_minute=60,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_refusal_cb() -> None:
    reset_all()


# ---------------------------------------------------------------------------
# Logging capture helper
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# ---------------------------------------------------------------------------
# E2E smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_observability_wiring_full_stack() -> None:
    """Full stack: PermissionPipeline → ToolExecutor → mock adapter.

    Verifies that metrics accumulate and events are emitted as JSON.
    """
    mc = MetricsCollector()
    el = ObservabilityEventLogger()

    # Capture kosmos.events logger output
    handler = _CapturingHandler()
    events_logger = logging.getLogger("kosmos.events")
    original_level = events_logger.level
    events_logger.setLevel(logging.DEBUG)
    events_logger.addHandler(handler)

    try:
        # --- Set up tool registry and executor ---
        tool = _make_tool()
        registry = ToolRegistry()
        registry.register(tool)

        executor = ToolExecutor(registry, metrics=mc, event_logger=el)

        async def _mock_adapter(inp: object) -> dict[str, Any]:
            return {"result": "ok"}

        executor.register_adapter(tool.id, _mock_adapter)

        # --- Set up PermissionPipeline with metrics ---
        pipeline = PermissionPipeline(
            executor=executor,
            registry=registry,
            metrics=mc,
            event_logger=el,
        )

        session = SessionContext(
            session_id="e2e-test-session",
            auth_level=0,
            citizen_id=None,
            consented_providers=["mock"],
        )

        # --- Dispatch one tool call through the full pipeline ---
        result = await pipeline.run(tool.id, "{}", session)
        assert result.success, f"Tool call should succeed, got: {result.error}"

        # --- Assert: tool.call_count is non-zero ---
        tool_call_count = mc.get_counter("tool.call_count", labels={"tool_id": tool.id})
        assert tool_call_count >= 1, f"Expected tool.call_count >= 1, got {tool_call_count}"

        # --- Assert: permission.decision_count is non-zero ---
        total_permission_decisions = sum(
            mc.get_counter(
                "permission.decision_count",
                labels={"step": str(s), "decision": "allow"},
            )
            for s in range(1, 8)
        )
        assert total_permission_decisions >= 1, (
            f"Expected permission.decision_count >= 1, got {total_permission_decisions}"
        )

        # --- Assert: at least one valid JSON event in kosmos.events logger ---
        assert len(handler.records) >= 1, "Expected at least one event in kosmos.events logger"

        # Verify all emitted messages are valid JSON
        for record in handler.records:
            msg = record.getMessage()
            try:
                parsed = json.loads(msg)
                assert "event_type" in parsed
            except json.JSONDecodeError as exc:
                pytest.fail(f"kosmos.events log message is not valid JSON: {msg!r} — {exc}")

    finally:
        events_logger.removeHandler(handler)
        events_logger.setLevel(original_level)


@pytest.mark.asyncio
async def test_observability_wiring_no_metrics_no_error() -> None:
    """Full stack runs without error when no MetricsCollector is provided (AC-A11)."""
    tool = _make_tool("mock_no_metrics")
    registry = ToolRegistry()
    registry.register(tool)

    executor = ToolExecutor(registry)  # no metrics

    async def _mock_adapter(inp: object) -> dict[str, Any]:
        return {"result": "ok"}

    executor.register_adapter(tool.id, _mock_adapter)

    pipeline = PermissionPipeline(executor=executor, registry=registry)  # no metrics

    session = SessionContext(
        session_id="e2e-no-metrics-session",
        auth_level=0,
        citizen_id=None,
        consented_providers=["mock"],
    )

    result = await pipeline.run(tool.id, "{}", session)
    assert result.success
