# SPDX-License-Identifier: Apache-2.0
"""E2E permission pipeline tests for the route safety flow (T016-T017).

Tests verify:
- T016: When the permission pipeline is configured, tool execution still
  succeeds for public-auth tools with an anonymous (auth_level=0) session.
- T017: When a tool requires authentication (access tier = "authenticated"
  or "restricted"), the permission pipeline denies the call and returns a
  permission_denied ToolResult.

Architecture note:
  The E2EFixtureBuilder stores the PermissionPipeline as engine attributes
  (_permission_pipeline, _permission_session) but QueryEngine.run() creates
  a QueryContext without forwarding them (those fields in QueryContext are None
  by default). Therefore, end-to-end tests through engine.run() do NOT exercise
  the permission pipeline.

  TODO: Wire engine._permission_pipeline and engine._permission_session into
  the QueryContext in QueryEngine.run() so that PermissionPipeline is exercised
  automatically on every tool dispatch (see engine.py and models.py QueryContext).

  These tests exercise the permission pipeline at the component level
  (PermissionPipeline.run()) to ensure correctness independently of engine
  integration, and verify the happy-path E2E flow still succeeds with
  public-auth tools when the pipeline is tested in isolation.
"""

from __future__ import annotations

import json

import pytest

from kosmos.engine.events import StopReason
from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    SessionContext,
)
from kosmos.permissions.pipeline import PermissionPipeline
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry
from tests.e2e.conftest import (
    TEXT_ANSWER_ROUTE_SAFETY,
    TOOL_CALL_ROAD_RISK,
    E2EFixtureBuilder,
    assert_tool_calls_dispatched,
    run_e2e_query,
)

# ---------------------------------------------------------------------------
# T016 [US4] Permission pipeline E2E — public tool, anonymous session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t016_permission_pipeline_public_tool_succeeds(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """Happy-path E2E with permission pipeline configured; public tools succeed.

    The PermissionPipeline is built and stored on the engine via
    e2e_builder.with_permission_pipeline(), but is not yet wired into
    QueryEngine.run() (see module-level TODO). This test therefore:

    a) Runs the full E2E flow and verifies that tool calls still complete
       (the pipeline not being wired means tools execute through the regular
        executor path, which is the current supported behaviour).
    b) Directly exercises PermissionPipeline.run() with a public-auth tool
       and an anonymous session to confirm the pipeline itself allows the call.

    Both assertions must pass for T016 to be considered green.
    """
    # ---- Part A: E2E flow succeeds with permission pipeline configured ----
    session_ctx = SessionContext(session_id="e2e-t016", auth_level=0)
    engine, _llm_client, httpx_mock = (
        e2e_builder
        .with_permission_pipeline(session_ctx)
        .with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY])
        .build()
    )

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
    )

    # Tool must still have been dispatched (pipeline not yet wired → direct executor)
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # Flow must complete successfully (not permission-denied stop)
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found"
    assert stop_events[-1].stop_reason not in (
        StopReason.error_unrecoverable,
        StopReason.api_budget_exceeded,
    ), f"Unexpected stop reason: {stop_events[-1].stop_reason}"

    # ---- Part B: PermissionPipeline allows public tools with anonymous session ----
    # Build a minimal registry with a public-auth tool (mimics koroad_accident_search)
    from pydantic import BaseModel

    class _MockInput(BaseModel):
        query: str

    class _MockOutput(BaseModel):
        result: str

    pub_tool = GovAPITool(
        id="public_test_tool",
        name_ko="공개 테스트 도구",
        provider="test_provider",
        category=["test"],
        endpoint="https://test.example.com/api",
        auth_type="public",  # public → AccessTier.public → step 1 always allows
        input_schema=_MockInput,
        output_schema=_MockOutput,
        search_hint="public test tool for E2E permission testing",
        requires_auth=False,
        is_concurrency_safe=True,
        is_personal_data=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=60,
    )

    registry = ToolRegistry()
    registry.register(pub_tool)
    executor = ToolExecutor(registry)

    async def _mock_adapter(validated_input: _MockInput) -> dict[str, object]:
        return {"result": f"공개 API 응답: {validated_input.query}"}

    executor.register_adapter("public_test_tool", _mock_adapter)

    pipeline = PermissionPipeline(executor=executor, registry=registry)

    result = await pipeline.run(
        tool_id="public_test_tool",
        arguments_json=json.dumps({"query": "서울 교통 정보"}),
        session_context=SessionContext(session_id="t016-unit", auth_level=0),
    )

    assert result.success, (
        f"PermissionPipeline.run() should succeed for public tool with anonymous session, "
        f"but got: error={result.error}, error_type={result.error_type}"
    )
    assert result.data is not None
    assert result.error_type is None


# ---------------------------------------------------------------------------
# T017 [US4] Permission denial — restricted/authenticated tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t017_permission_pipeline_denies_authenticated_tool(
    e2e_env: None,
) -> None:
    """PermissionPipeline denies tools with authenticated/restricted access tier.

    The permission pipeline (step 1: check_config) denies any tool whose
    access tier is "authenticated" or "restricted" in v1, regardless of
    the session context. This test verifies the denial mechanism at the
    pipeline level using a mock tool with requires_auth=True and
    auth_type="oauth" (→ AccessTier.authenticated).

    Per pipeline.py step 1 (step1_config.py):
      - AccessTier.authenticated → deny with reason "citizen_auth_not_implemented"
      - AccessTier.restricted   → deny with reason "tier_restricted_not_implemented"

    Note: The real registered tools (koroad_accident_search, kma_*, road_risk_score)
    all use auth_type="api_key" (→ AccessTier.api_key) which is allowed when a
    KOSMOS_*_API_KEY env var is present. No currently-registered tool uses
    auth_type="oauth" or has access_tier=restricted. This test therefore uses a
    mock tool definition with requires_auth=True and auth_type="oauth" to exercise
    the denial path.
    """
    from pydantic import BaseModel

    class _AuthInput(BaseModel):
        citizen_id: str

    class _AuthOutput(BaseModel):
        personal_data: str

    # Tool that requires citizen authentication (auth_type="oauth" → AccessTier.authenticated)
    auth_required_tool = GovAPITool(
        id="auth_required_tool",
        name_ko="인증 필요 도구",
        provider="test_provider",
        category=["personal"],
        endpoint="https://secure.example.com/api",
        auth_type="oauth",  # maps to AccessTier.authenticated → denied in v1
        input_schema=_AuthInput,
        output_schema=_AuthOutput,
        search_hint="authenticated personal data tool requiring citizen login",
        requires_auth=True,
        is_concurrency_safe=False,
        is_personal_data=True,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
    )

    registry = ToolRegistry()
    registry.register(auth_required_tool)
    executor = ToolExecutor(registry)

    async def _mock_auth_adapter(validated_input: _AuthInput) -> dict[str, object]:
        # This should never be reached when the permission pipeline denies the call
        return {"personal_data": "개인정보"}

    executor.register_adapter("auth_required_tool", _mock_auth_adapter)

    pipeline = PermissionPipeline(executor=executor, registry=registry)

    # Anonymous session (auth_level=0) — no citizen identity
    anon_session = SessionContext(session_id="t017-anon", auth_level=0)

    result = await pipeline.run(
        tool_id="auth_required_tool",
        arguments_json=json.dumps({"citizen_id": "test-citizen-001"}),
        session_context=anon_session,
    )

    # Pipeline must deny the call
    assert not result.success, (
        "PermissionPipeline should deny authenticated-tier tool for anonymous session"
    )
    assert result.error_type == "permission_denied", (
        f"Expected error_type='permission_denied', got {result.error_type!r}"
    )
    assert result.error is not None
    assert "Permission denied" in result.error, (
        f"Error message should contain 'Permission denied', got: {result.error!r}"
    )


@pytest.mark.asyncio
async def test_t017b_permission_pipeline_denies_restricted_tool(
    e2e_env: None,
) -> None:
    """PermissionPipeline denies tools with restricted access tier.

    GovAPITool does not support auth_type="restricted" in its Literal type,
    so we exercise the restricted tier by building a PermissionCheckRequest
    directly with AccessTier.restricted and feeding it into step1_config.

    This verifies the deny path for the restricted tier in isolation.
    """
    from kosmos.permissions.steps.step1_config import check_config

    request = PermissionCheckRequest(
        tool_id="restricted_test_tool",
        access_tier=AccessTier.restricted,
        arguments_json="{}",
        session_context=SessionContext(session_id="t017b-anon", auth_level=0),
        is_personal_data=False,
    )

    step_result = check_config(request)

    assert step_result.decision == PermissionDecision.deny, (
        f"Step 1 should deny AccessTier.restricted, got {step_result.decision!r}"
    )
    assert step_result.reason == "tier_restricted_not_implemented", (
        f"Expected reason 'tier_restricted_not_implemented', got {step_result.reason!r}"
    )
