# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Permission Pipeline (Layer 3).

Public API for the 7-step permission gauntlet that gates all tool executions.

Quick start::

    from kosmos.permissions import PermissionPipeline, SessionContext

    pipeline = PermissionPipeline(executor=executor, registry=registry)
    result = await pipeline.run(
        tool_id="my_tool",
        arguments_json='{"query": "test"}',
        session_context=SessionContext(session_id="s1"),
    )
"""

from __future__ import annotations

from kosmos.permissions.bypass import BYPASS_IMMUNE_RULES, check_bypass_immune
from kosmos.permissions.models import (
    AccessTier,
    AuditLogEntry,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
    SessionContext,
)
from kosmos.permissions.pipeline import PermissionPipeline

__all__ = [
    "AccessTier",
    "AuditLogEntry",
    "BYPASS_IMMUNE_RULES",
    "PermissionCheckRequest",
    "PermissionDecision",
    "PermissionPipeline",
    "PermissionStepResult",
    "SessionContext",
    "check_bypass_immune",
]
