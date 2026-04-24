# SPDX-License-Identifier: Apache-2.0
"""E2E permission pipeline tests for Scenario 1 Route Safety (030 rebase).

Tests verify:
- T016: The PermissionPipeline allows public-auth tools with an anonymous
  (auth_level=0) session (component-level test).
- T017: When a tool requires authentication (auth_type="oauth" →
  AccessTier.authenticated), the permission pipeline denies the call.

Architecture note:
  The PermissionPipeline is not yet wired into QueryEngine.run() — tool
  execution goes through ToolExecutor directly in the engine loop. These tests
  exercise the pipeline at the component level to confirm correctness. The E2E
  happy-path flow succeeds independently of the pipeline (tested in T011).

These tests do NOT use the E2EFixtureBuilder pattern. They are component-level
tests that exercise the permission pipeline in isolation.
"""

from __future__ import annotations

import json

import pytest

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

# ---------------------------------------------------------------------------
# T016 [US4] Permission pipeline — public tool, anonymous session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t016_permission_pipeline_public_tool_succeeds() -> None:
    """PermissionPipeline allows public tools with an anonymous session.

    The pipeline step1_config check passes for AccessTier.public regardless
    of session auth_level. This is the expected behaviour for all public-auth
    gov APIs in the two-tool facade.
    """
    from pydantic import BaseModel

    class _MockInput(BaseModel):
        query: str

    class _MockOutput(BaseModel):
        result: str

    pub_tool = GovAPITool(
        id="public_test_tool",
        name_ko="공개 테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://test.example.com/api",
        auth_type="public",
        input_schema=_MockInput,
        output_schema=_MockOutput,
        search_hint="public test tool for E2E permission testing",
        auth_level="AAL1",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=True,
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
        session_context=SessionContext(
            session_id="t016-unit",
            auth_level=0,
            consented_providers=["public"],
        ),
    )

    assert result.success, (
        f"PermissionPipeline.run() should succeed for public tool with anonymous session, "
        f"but got: error={result.error}, error_type={result.error_type}"
    )
    assert result.data is not None
    assert result.error_type is None


# ---------------------------------------------------------------------------
# T017 [US4] Permission denial — authenticated/oauth tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t017_permission_pipeline_denies_authenticated_tool() -> None:
    """PermissionPipeline denies tools with auth_type='oauth' (authenticated tier).

    Per pipeline.py step 1 (step1_config.py):
      AccessTier.authenticated → deny with reason "citizen_auth_not_implemented"

    This is tested via a mock GovAPITool with requires_auth=True and
    auth_type="oauth", which maps to AccessTier.authenticated.
    """
    from pydantic import BaseModel

    class _AuthInput(BaseModel):
        citizen_id: str

    class _AuthOutput(BaseModel):
        personal_data: str

    auth_required_tool = GovAPITool(
        id="auth_required_tool",
        name_ko="인증 필요 도구",
        ministry="OTHER",
        category=["personal"],
        endpoint="https://secure.example.com/api",
        auth_type="oauth",
        input_schema=_AuthInput,
        output_schema=_AuthOutput,
        search_hint="authenticated personal data tool requiring citizen login",
        auth_level="AAL1",
        pipa_class="personal",
        is_irreversible=False,
        dpa_reference="dpa-test-v1",
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
        # Must never be reached when pipeline denies the call
        return {"personal_data": "개인정보"}

    executor.register_adapter("auth_required_tool", _mock_auth_adapter)

    pipeline = PermissionPipeline(executor=executor, registry=registry)

    anon_session = SessionContext(session_id="t017-anon", auth_level=0)

    result = await pipeline.run(
        tool_id="auth_required_tool",
        arguments_json=json.dumps({"citizen_id": "test-citizen-001"}),
        session_context=anon_session,
    )

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
async def test_t017b_permission_pipeline_denies_restricted_tool() -> None:
    """PermissionPipeline denies tools with restricted access tier.

    GovAPITool does not support auth_type="restricted" as a Literal value,
    so we exercise the restricted tier by building a PermissionCheckRequest
    directly with AccessTier.restricted and feeding it into step1_config.
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


# ---------------------------------------------------------------------------
# T016b — happy-path E2E with permission pipeline configured (integration check)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t016b_happy_path_unaffected_by_permission_pipeline() -> None:
    """Full E2E happy-path run is not affected by permission pipeline existence.

    The pipeline is NOT yet wired into QueryEngine.run(); tool execution
    goes through ToolExecutor directly. This test confirms that the standard
    happy-path RunReport (stop_reason='end_turn') is produced regardless of
    whether a PermissionPipeline would theoretically deny the call.
    """
    from tests.e2e.conftest import run_scenario

    report = await run_scenario("happy")

    assert report.stop_reason == "end_turn", (
        f"Happy path should produce stop_reason='end_turn', got {report.stop_reason!r}"
    )
    assert report.final_response, "Happy path must have a non-empty final_response"
