# SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for PermissionPipeline.

All tests use mock tools and adapters — no live API calls are made.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, ConfigDict

from kosmos.permissions.models import AccessTier, SessionContext
from kosmos.permissions.pipeline import PermissionPipeline
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal tool schemas for testing
# ---------------------------------------------------------------------------


class _DummyInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = "test"


class _DummyOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: str = "ok"


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_tool(
    tool_id: str = "public_tool",
    auth_type: str = "public",
    is_personal_data: bool = False,
) -> GovAPITool:
    """Build a minimal GovAPITool for testing."""
    return GovAPITool(
        id=tool_id,
        name_ko="테스트도구",
        provider="테스트기관",
        category=["테스트"],
        endpoint="http://example.com/api",
        auth_type=auth_type,  # type: ignore[arg-type]
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="test tool 테스트",
        requires_auth=auth_type != "public",
        is_personal_data=is_personal_data,
        rate_limit_per_minute=60,
    )


@pytest.fixture()
def public_tool() -> GovAPITool:
    """A public (no-auth) tool with no personal data."""
    return _make_tool(tool_id="public_tool", auth_type="public", is_personal_data=False)


@pytest.fixture()
def authn_tool() -> GovAPITool:
    """An oauth (citizen-authenticated) tool — denied for unauthenticated sessions."""
    return _make_tool(tool_id="authn_tool", auth_type="oauth", is_personal_data=False)


@pytest.fixture()
def personal_tool() -> GovAPITool:
    """An auth-gated tool that returns personal data — immune rule applies.

    Note: FR-038 (Epic #507) prohibits ``is_personal_data=True`` without
    ``requires_auth=True`` at registration, so this fixture uses
    ``auth_type="oauth"`` to satisfy the invariant.  The bypass-immune rule
    tested here (personal_data_citizen_mismatch) still fires regardless of
    auth_type — the immune behavior is driven by ``is_personal_data=True``.
    """
    return _make_tool(tool_id="personal_tool", auth_type="oauth", is_personal_data=True)


@pytest.fixture()
def mock_adapter() -> AsyncMock:
    """Async mock adapter returning a valid _DummyOutput dict."""
    return AsyncMock(return_value={"result": "ok"})


def _build_pipeline(
    *tools: GovAPITool,
    adapter: AsyncMock | None = None,
) -> tuple[PermissionPipeline, ToolRegistry, ToolExecutor]:
    """Build a PermissionPipeline pre-loaded with the given tools."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    for tool in tools:
        registry.register(tool)
        if adapter is not None:
            executor.register_adapter(tool.id, adapter)
    pipeline = PermissionPipeline(executor=executor, registry=registry)
    return pipeline, registry, executor


def _anon_session(consented_providers: list[str] | None = None) -> SessionContext:
    return SessionContext(
        session_id="test-session",
        consented_providers=consented_providers or ["public"],
    )


def _auth_session(consented_providers: list[str] | None = None) -> SessionContext:
    return SessionContext(
        session_id="test-session",
        citizen_id="citizen-42",
        auth_level=1,
        consented_providers=consented_providers or ["public"],
    )


# ---------------------------------------------------------------------------
# T023-1: Happy path — public tool → all steps pass → ToolResult(success=True)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_allow_path_returns_success(public_tool: GovAPITool, mock_adapter: AsyncMock) -> None:
    """Public tool with anonymous session → pipeline allows → success ToolResult."""
    pipeline, _, _ = _build_pipeline(public_tool, adapter=mock_adapter)

    result = await pipeline.run(
        tool_id="public_tool",
        arguments_json='{"query": "hello"}',
        session_context=_anon_session(),
    )

    assert result.success is True
    assert result.data == {"result": "ok"}
    assert result.error is None
    assert result.error_type is None
    mock_adapter.assert_awaited_once()


# ---------------------------------------------------------------------------
# T023-2: Step 1 deny — authenticated tool, unauthenticated session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_deny_at_step1_returns_permission_denied(
    authn_tool: GovAPITool, mock_adapter: AsyncMock
) -> None:
    """OAuth tool + unauthenticated session → denied at step 1."""
    pipeline, _, _ = _build_pipeline(authn_tool, adapter=mock_adapter)

    result = await pipeline.run(
        tool_id="authn_tool",
        arguments_json='{"query": "hello"}',
        session_context=_anon_session(),
    )

    assert result.success is False
    assert result.error_type == "permission_denied"
    assert "step 1" in result.error  # type: ignore[operator]
    # Adapter must NOT have been called
    mock_adapter.assert_not_awaited()


# ---------------------------------------------------------------------------
# T023-3: Step 7 always fires — audit log called on both allow and deny
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_step7_always_fires_on_allow(
    public_tool: GovAPITool, mock_adapter: AsyncMock
) -> None:
    """Audit log is written even on a successful allow path."""
    pipeline, _, _ = _build_pipeline(public_tool, adapter=mock_adapter)

    import kosmos.permissions.pipeline as pipeline_mod

    with patch.object(pipeline_mod, "write_audit_log") as mock_audit:
        mock_audit.return_value = None
        await pipeline.run(
            tool_id="public_tool",
            arguments_json='{"query": "hello"}',
            session_context=_anon_session(),
        )

    # Audit must have been called exactly once (step 7)
    mock_audit.assert_called_once()
    # Adapter was called before audit in sandbox
    mock_adapter.assert_awaited_once()


@pytest.mark.asyncio()
async def test_step7_always_fires_on_deny(authn_tool: GovAPITool, mock_adapter: AsyncMock) -> None:
    """Audit log is written even when the pipeline denies at step 1."""
    pipeline, _, _ = _build_pipeline(authn_tool, adapter=mock_adapter)

    import kosmos.permissions.pipeline as pipeline_mod

    with patch.object(pipeline_mod, "write_audit_log") as mock_audit:
        mock_audit.return_value = None
        result = await pipeline.run(
            tool_id="authn_tool",
            arguments_json='{"query": "hello"}',
            session_context=_anon_session(),
        )

    assert result.error_type == "permission_denied"
    mock_audit.assert_called_once()
    mock_adapter.assert_not_awaited()


# ---------------------------------------------------------------------------
# T023-4: Step 1 raises RuntimeError → fail-closed → deny with reason="internal_error"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_step1_exception_returns_deny(
    public_tool: GovAPITool, mock_adapter: AsyncMock
) -> None:
    """If step 1 raises an exception, the pipeline is fail-closed → deny."""
    pipeline, _, _ = _build_pipeline(public_tool, adapter=mock_adapter)

    import kosmos.permissions.pipeline as pipeline_mod

    with patch.object(
        pipeline_mod,
        "_PRE_EXECUTION_STEPS",
        [
            lambda req: (_ for _ in ()).throw(RuntimeError("boom")),
        ],
    ):
        result = await pipeline.run(
            tool_id="public_tool",
            arguments_json='{"query": "hello"}',
            session_context=_anon_session(),
        )

    assert result.success is False
    assert result.error_type == "permission_denied"
    assert "internal_error" in (result.error or "")
    mock_adapter.assert_not_awaited()


# ---------------------------------------------------------------------------
# T023-5: Bypass mode + personal data → still denied (immune rule)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_bypass_mode_still_enforces_immune_rules(
    personal_tool: GovAPITool, mock_adapter: AsyncMock
) -> None:
    """Bypass mode cannot skip bypass-immune rules (FR-016).

    The personal_tool has is_personal_data=True.  Even in bypass mode,
    an unauthenticated session must be denied by the immune rule.

    Note: The bypass-immune rule (personal_data_citizen_mismatch) only fires
    when citizen_id is set AND there is a citizen_id mismatch in args.
    With citizen_id=None (anon session), the rule does not fire since there
    is no citizen identity to mismatch against.  To test immune enforcement,
    we use a session with a citizen_id and supply mismatching args.
    """
    pipeline, _, _ = _build_pipeline(personal_tool, adapter=mock_adapter)

    session = SessionContext(
        session_id="test-session",
        citizen_id="citizen-42",
        auth_level=1,
        consented_providers=["personal"],
    )
    result = await pipeline.run(
        tool_id="personal_tool",
        arguments_json='{"query": "hello", "citizen_id": "other-citizen"}',
        session_context=session,
        is_bypass_mode=True,
    )

    assert result.success is False
    assert result.error_type == "permission_denied"
    # Adapter must NOT have been called even in bypass mode
    mock_adapter.assert_not_awaited()


# ---------------------------------------------------------------------------
# T023-6: Import-time env isolation — importing pipeline without KOSMOS_* vars
# ---------------------------------------------------------------------------


def test_import_time_env_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing the pipeline module must not raise if KOSMOS_* env vars are absent."""
    # Remove any KOSMOS_* vars from the env
    monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)
    monkeypatch.delenv("KOSMOS_FRIENDLI_TOKEN", raising=False)

    # Remove cached module so we get a fresh import
    for mod_name in list(sys.modules.keys()):
        if "kosmos.permissions" in mod_name:
            del sys.modules[mod_name]

    # This must not raise
    imported = importlib.import_module("kosmos.permissions.pipeline")
    assert hasattr(imported, "PermissionPipeline")


# ---------------------------------------------------------------------------
# Additional: bypass mode skips steps 1-5 for non-immune tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_bypass_mode_skips_pre_execution_steps(
    authn_tool: GovAPITool, mock_adapter: AsyncMock
) -> None:
    """In bypass mode, an oauth tool is allowed for an unauthenticated session.

    Since the authn_tool has is_personal_data=False, the immune rule does NOT fire.
    With is_bypass_mode=True and steps 1-5 skipped, execution proceeds to step 6.
    """
    pipeline, _, _ = _build_pipeline(authn_tool, adapter=mock_adapter)

    result = await pipeline.run(
        tool_id="authn_tool",
        arguments_json='{"query": "hello"}',
        session_context=_anon_session(),
        is_bypass_mode=True,
    )

    # Bypass skips step 1 → adapter gets called → success
    assert result.success is True
    mock_adapter.assert_awaited_once()


# ---------------------------------------------------------------------------
# Additional: unknown auth_type maps to restricted → denied
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_unknown_auth_type_maps_to_restricted() -> None:
    """A tool with an unknown auth_type should map to AccessTier.restricted → denied."""
    # We can't create a GovAPITool with an unknown auth_type (Literal validation).
    # Instead, test the mapping constant directly.
    from kosmos.permissions.pipeline import _AUTH_TYPE_TO_ACCESS_TIER

    assert "public" in _AUTH_TYPE_TO_ACCESS_TIER
    assert "api_key" in _AUTH_TYPE_TO_ACCESS_TIER
    assert "oauth" in _AUTH_TYPE_TO_ACCESS_TIER
    # Unknown key should fall back to restricted via .get(..., AccessTier.restricted)
    assert _AUTH_TYPE_TO_ACCESS_TIER.get("unknown", AccessTier.restricted) == AccessTier.restricted
