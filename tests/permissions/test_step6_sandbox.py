# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 6: Sandboxed execution context."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

from kosmos.permissions.models import AccessTier, PermissionDecision
from kosmos.permissions.steps.step6_sandbox import execute_sandboxed


class TestStep6Sandbox:
    """Sandboxed execution context."""

    @pytest.mark.asyncio
    async def test_success_execution(self, make_permission_request):
        """A successful adapter call should return allow result and a ToolResult."""
        req = make_permission_request(access_tier=AccessTier.public)
        adapter_fn = AsyncMock(return_value={"data": "result"})
        validated_input = object()

        step_result, tool_result = await execute_sandboxed(req, adapter_fn, validated_input)

        assert step_result.decision == PermissionDecision.allow
        assert step_result.step == 6
        assert tool_result is not None
        assert tool_result.success is True
        assert tool_result.data == {"data": "result"}
        assert tool_result.tool_id == req.tool_id

    @pytest.mark.asyncio
    async def test_exception_in_adapter(self, make_permission_request):
        """An exception in the adapter should return deny with reason execution_error."""
        req = make_permission_request(access_tier=AccessTier.public)
        adapter_fn = AsyncMock(side_effect=RuntimeError("adapter blew up"))
        validated_input = object()

        step_result, tool_result = await execute_sandboxed(req, adapter_fn, validated_input)

        assert step_result.decision == PermissionDecision.deny
        assert step_result.step == 6
        assert step_result.reason == "execution_error"
        assert tool_result is None

    @pytest.mark.asyncio
    async def test_env_isolation(self, make_permission_request, monkeypatch):
        """KOSMOS_OTHER_KEY should NOT be visible inside the sandbox for public tier."""
        monkeypatch.setenv("KOSMOS_OTHER_KEY", "secret-value")
        req = make_permission_request(access_tier=AccessTier.public)

        captured_env: dict[str, str] = {}

        async def capturing_adapter(_input):  # noqa: ANN001
            captured_env.update(os.environ.copy())
            return {"ok": True}

        await execute_sandboxed(req, capturing_adapter, object())

        assert "KOSMOS_OTHER_KEY" not in captured_env

    @pytest.mark.asyncio
    async def test_env_restoration(self, make_permission_request, monkeypatch):
        """All removed env vars should be fully restored after sandbox exits."""
        monkeypatch.setenv("KOSMOS_OTHER_KEY", "restore-me")
        req = make_permission_request(access_tier=AccessTier.public)

        adapter_fn = AsyncMock(return_value={})

        assert os.environ.get("KOSMOS_OTHER_KEY") == "restore-me"
        await execute_sandboxed(req, adapter_fn, object())
        assert os.environ.get("KOSMOS_OTHER_KEY") == "restore-me"

    @pytest.mark.asyncio
    async def test_env_restoration_after_exception(self, make_permission_request, monkeypatch):
        """Removed env vars should be restored even when the adapter raises."""
        monkeypatch.setenv("KOSMOS_OTHER_KEY", "restore-after-error")
        req = make_permission_request(access_tier=AccessTier.public)

        adapter_fn = AsyncMock(side_effect=ValueError("error"))

        await execute_sandboxed(req, adapter_fn, object())
        assert os.environ.get("KOSMOS_OTHER_KEY") == "restore-after-error"

    @pytest.mark.asyncio
    async def test_api_key_visible_in_api_key_tier(self, make_permission_request, monkeypatch):
        """KOSMOS_DATA_GO_KR_API_KEY should be visible for api_key tier."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "my-api-key")
        req = make_permission_request(access_tier=AccessTier.api_key)

        captured_env: dict[str, str] = {}

        async def capturing_adapter(_input):  # noqa: ANN001
            captured_env.update(os.environ.copy())
            return {}

        await execute_sandboxed(req, capturing_adapter, object())

        assert captured_env.get("KOSMOS_DATA_GO_KR_API_KEY") == "my-api-key"

    @pytest.mark.asyncio
    async def test_other_api_key_visible_in_api_key_tier(
        self, make_permission_request, monkeypatch
    ):
        """Any KOSMOS_*_API_KEY var (e.g. KOSMOS_KOROAD_API_KEY) must be visible
        inside the sandbox for api_key tier — the allowlist uses a pattern, not a
        hardcoded list."""
        monkeypatch.setenv("KOSMOS_KOROAD_API_KEY", "koroad-secret")
        req = make_permission_request(access_tier=AccessTier.api_key)

        captured_env: dict[str, str] = {}

        async def capturing_adapter(_input):  # noqa: ANN001
            captured_env.update(os.environ.copy())
            return {}

        await execute_sandboxed(req, capturing_adapter, object())

        assert captured_env.get("KOSMOS_KOROAD_API_KEY") == "koroad-secret"

    @pytest.mark.asyncio
    async def test_non_api_key_var_hidden_in_api_key_tier(
        self, make_permission_request, monkeypatch
    ):
        """A KOSMOS_ var that does NOT match KOSMOS_*_API_KEY must be hidden
        even in api_key tier."""
        monkeypatch.setenv("KOSMOS_SESSION_TOKEN", "hidden-token")
        req = make_permission_request(access_tier=AccessTier.api_key)

        captured_env: dict[str, str] = {}

        async def capturing_adapter(_input):  # noqa: ANN001
            captured_env.update(os.environ.copy())
            return {}

        await execute_sandboxed(req, capturing_adapter, object())

        assert "KOSMOS_SESSION_TOKEN" not in captured_env
