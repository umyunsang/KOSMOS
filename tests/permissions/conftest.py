# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for permission pipeline tests."""

from __future__ import annotations

import pytest

from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    SessionContext,
)


@pytest.fixture()
def make_session_context():
    """Factory fixture for creating SessionContext instances."""

    def _make(
        *,
        session_id: str = "test-session-001",
        citizen_id: str | None = None,
        auth_level: int = 0,
        consented_providers: list[str] | None = None,
    ) -> SessionContext:
        return SessionContext(
            session_id=session_id,
            citizen_id=citizen_id,
            auth_level=auth_level,
            consented_providers=consented_providers or [],
        )

    return _make


@pytest.fixture()
def make_permission_request(make_session_context):
    """Factory fixture for creating PermissionCheckRequest instances."""

    def _make(
        *,
        tool_id: str = "test_tool",
        access_tier: AccessTier = AccessTier.public,
        arguments_json: str = "{}",
        session_context: SessionContext | None = None,
        is_personal_data: bool = False,
        is_bypass_mode: bool = False,
    ) -> PermissionCheckRequest:
        return PermissionCheckRequest(
            tool_id=tool_id,
            access_tier=access_tier,
            arguments_json=arguments_json,
            session_context=session_context or make_session_context(),
            is_personal_data=is_personal_data,
            is_bypass_mode=is_bypass_mode,
        )

    return _make
