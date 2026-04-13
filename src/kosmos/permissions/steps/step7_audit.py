# SPDX-License-Identifier: Apache-2.0
"""Step 7: Audit log writer.

Writes a structured AuditLogEntry to a dedicated logger after every tool
invocation, whether approved or denied, succeeded or failed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Literal

from kosmos.permissions.models import (
    AuditLogEntry,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)
from kosmos.tools.models import ToolResult

_STEP = 7

# Dedicated audit logger — can be routed to a separate handler
audit_logger = logging.getLogger("kosmos.permissions.audit")


def write_audit_log(
    request: PermissionCheckRequest,
    deciding_result: PermissionStepResult,
    tool_result: ToolResult | None,
) -> AuditLogEntry:
    """Write an audit log entry for a pipeline invocation.

    Args:
        request: The original permission check request.
        deciding_result: The step result that determined the final decision.
        tool_result: The tool execution result (None if denied before execution).

    Returns:
        The AuditLogEntry that was logged.
    """
    # Determine outcome
    outcome: Literal["success", "failure", "denied"]
    if deciding_result.decision == PermissionDecision.deny:
        outcome = "denied"
    elif tool_result is not None and tool_result.success:
        outcome = "success"
    elif tool_result is not None and not tool_result.success:
        outcome = "failure"
    else:
        outcome = "denied"

    entry = AuditLogEntry(
        timestamp=datetime.now(UTC),
        tool_id=request.tool_id,
        access_tier=request.access_tier,
        decision=deciding_result.decision,
        step_that_decided=deciding_result.step,
        outcome=outcome,
        error_type=tool_result.error_type if tool_result and not tool_result.success else None,
        deny_reason=(
            deciding_result.reason if deciding_result.decision != PermissionDecision.allow else None
        ),
        session_id=request.session_context.session_id,
    )

    # Log at WARNING for denied, INFO for all others
    if outcome == "denied":
        audit_logger.warning(
            "Permission audit: tool=%s tier=%s decision=%s step=%d outcome=%s reason=%s",
            entry.tool_id,
            entry.access_tier,
            entry.decision,
            entry.step_that_decided,
            entry.outcome,
            entry.deny_reason,
        )
    else:
        audit_logger.info(
            "Permission audit: tool=%s tier=%s decision=%s step=%d outcome=%s",
            entry.tool_id,
            entry.access_tier,
            entry.decision,
            entry.step_that_decided,
            entry.outcome,
        )

    return entry
