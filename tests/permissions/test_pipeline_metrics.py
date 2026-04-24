# SPDX-License-Identifier: Apache-2.0
"""Tests for PermissionPipeline metrics instrumentation (T009).

Validates AC-A1, AC-A2, AC-A3 (refusal circuit), AC-A9.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from kosmos.observability.metrics import MetricsCollector
from kosmos.permissions.models import SessionContext
from kosmos.permissions.pipeline import PermissionPipeline
from kosmos.permissions.steps.refusal_circuit_breaker import reset_all
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal test schemas
# ---------------------------------------------------------------------------


class _DummyInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = "test"


class _DummyOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: str = "ok"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tool(
    tool_id: str = "public_tool",
    auth_type: str = "public",
    is_personal_data: bool = False,
) -> GovAPITool:
    pipa_class = "personal" if is_personal_data else "non_personal"
    # Spec-024 V5: auth_level=='public' ⇔ requires_auth==False. Any non-public
    # auth_type (e.g. "oauth") implies authentication is required, which means
    # auth_level must be at least AAL1.
    requires_auth = auth_type != "public"
    auth_level = "AAL1" if is_personal_data or requires_auth else "public"
    dpa_reference = "dpa-test-v1" if is_personal_data else None
    return GovAPITool(
        id=tool_id,
        name_ko="테스트도구",
        ministry="OTHER",
        category=["테스트"],
        endpoint="http://example.com/api",
        auth_type=auth_type,  # type: ignore[arg-type]
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="test 테스트",
        auth_level=auth_level,  # type: ignore[arg-type]
        pipa_class=pipa_class,  # type: ignore[arg-type]
        is_irreversible=False,
        dpa_reference=dpa_reference,
        requires_auth=requires_auth,
        is_personal_data=is_personal_data,
        rate_limit_per_minute=60,
    )


def _make_session(
    session_id: str = "sess-001",
    auth_level: int = 0,
    consented_providers: list[str] | None = None,
) -> SessionContext:
    return SessionContext(
        session_id=session_id,
        auth_level=auth_level,
        citizen_id=None,
        consented_providers=consented_providers if consented_providers is not None else ["public"],
    )


def _make_stack(
    tool: GovAPITool,
    metrics: MetricsCollector | None = None,
) -> PermissionPipeline:
    """Create a PermissionPipeline with a mock adapter returning success."""
    registry = ToolRegistry()
    registry.register(tool)
    executor = ToolExecutor(registry)

    async def _adapter(inp: object) -> dict:
        return {"result": "ok"}

    executor.register_adapter(tool.id, _adapter)
    return PermissionPipeline(executor=executor, registry=registry, metrics=metrics)


@pytest.fixture(autouse=True)
def _reset_circuit_breaker() -> None:
    """Reset the global refusal circuit breaker state before each test."""
    reset_all()


# ---------------------------------------------------------------------------
# T009: test_decision_count_incremented_per_step_allow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_count_incremented_per_step_allow() -> None:
    """On a full allow path, decision_count is incremented for each step."""
    mc = MetricsCollector()
    tool = _make_tool(auth_type="public")
    pipeline = _make_stack(tool, metrics=mc)

    await pipeline.run(tool.id, "{}", _make_session())

    # Steps 1-5 should all have "allow" decisions
    total_allow = sum(
        mc.get_counter("permission.decision_count", labels={"step": str(s), "decision": "allow"})
        for s in range(1, 6)
    )
    assert total_allow >= 5, f"Expected 5+ allow decisions, got {total_allow}"


# ---------------------------------------------------------------------------
# T009: test_decision_count_incremented_on_deny_step3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_count_incremented_on_deny_step3() -> None:
    """When step 4 (authn) denies (oauth tool + unauthenticated), decision_count is incremented."""
    mc = MetricsCollector()
    # auth_type="oauth" with auth_level=0 → step4 (authn) denies
    tool = _make_tool(auth_type="oauth", is_personal_data=False)
    pipeline = _make_stack(tool, metrics=mc)

    result = await pipeline.run(tool.id, "{}", _make_session(auth_level=0))
    assert not result.success  # should be denied

    # At least one deny decision should be recorded
    total_deny = sum(
        mc.get_counter("permission.decision_count", labels={"step": str(s), "decision": "deny"})
        for s in range(1, 6)
    )
    assert total_deny >= 1


# ---------------------------------------------------------------------------
# T009: test_refusal_circuit_trips_incremented
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refusal_circuit_trips_incremented() -> None:
    """When consecutive denials reach threshold, refusal_circuit_trips is incremented."""
    from kosmos.permissions.steps.refusal_circuit_breaker import (
        CONSECUTIVE_DENIAL_THRESHOLD,  # noqa: PLC0415
    )

    mc = MetricsCollector()
    # oauth tool + unauthenticated session → step4 denies consistently
    tool = _make_tool(auth_type="oauth", is_personal_data=False)
    pipeline = _make_stack(tool, metrics=mc)
    session = _make_session(auth_level=0)

    # Trigger enough denials to cross the threshold
    for _ in range(CONSECUTIVE_DENIAL_THRESHOLD):
        await pipeline.run(tool.id, "{}", session)

    trips = mc.get_counter("permission.refusal_circuit_trips", labels={"tool_id": tool.id})
    assert trips >= 1


# ---------------------------------------------------------------------------
# T009: test_pipeline_duration_recorded_on_deny
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_duration_recorded_on_deny() -> None:
    """Duration histogram is recorded even when the pipeline exits early via deny."""
    mc = MetricsCollector()
    # oauth + unauthenticated → step4 denies
    tool = _make_tool(auth_type="oauth", is_personal_data=False)
    pipeline = _make_stack(tool, metrics=mc)

    result = await pipeline.run(tool.id, "{}", _make_session(auth_level=0))
    assert not result.success

    stats = mc.get_histogram_stats("permission.pipeline_duration_ms")
    assert stats["count"] == 1.0
    assert stats["avg"] >= 0.0


# ---------------------------------------------------------------------------
# T009: test_pipeline_duration_recorded_on_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_duration_recorded_on_success() -> None:
    """Duration histogram is recorded on a successful pipeline run."""
    mc = MetricsCollector()
    tool = _make_tool(auth_type="public")
    pipeline = _make_stack(tool, metrics=mc)

    result = await pipeline.run(tool.id, "{}", _make_session())
    assert result.success

    stats = mc.get_histogram_stats("permission.pipeline_duration_ms")
    assert stats["count"] == 1.0
    assert stats["avg"] >= 0.0


# ---------------------------------------------------------------------------
# T009: test_no_metrics_no_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_metrics_no_error() -> None:
    """When no MetricsCollector is provided, pipeline.run() works without error."""
    tool = _make_tool(auth_type="public")
    pipeline = _make_stack(tool, metrics=None)

    result = await pipeline.run(tool.id, "{}", _make_session())
    assert result.success
