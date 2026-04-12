# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 7: Audit log writer."""

from __future__ import annotations

import logging

from kosmos.permissions.models import (
    AccessTier,
    PermissionDecision,
    PermissionStepResult,
)
from kosmos.permissions.steps.step7_audit import write_audit_log
from kosmos.tools.models import ToolResult


def _make_allow_result(step: int = 6) -> PermissionStepResult:
    return PermissionStepResult(decision=PermissionDecision.allow, step=step)


def _make_deny_result(
    step: int = 1,
    reason: str = "api_key_not_configured",
) -> PermissionStepResult:
    return PermissionStepResult(decision=PermissionDecision.deny, step=step, reason=reason)


def _make_success_tool_result(tool_id: str = "test_tool") -> ToolResult:
    return ToolResult(tool_id=tool_id, success=True, data={"ok": True})


def _make_failed_tool_result(tool_id: str = "test_tool") -> ToolResult:
    return ToolResult(
        tool_id=tool_id,
        success=False,
        error="Something went wrong",
        error_type="execution",
    )


class TestStep7Audit:
    """Audit log writer."""

    def test_success_audit(self, make_permission_request, caplog):
        """allow + success ToolResult should produce outcome=success logged at INFO."""
        req = make_permission_request(access_tier=AccessTier.api_key)
        deciding = _make_allow_result(step=6)
        tool_result = _make_success_tool_result(req.tool_id)

        with caplog.at_level(logging.INFO, logger="kosmos.permissions.audit"):
            entry = write_audit_log(req, deciding, tool_result)

        assert entry.outcome == "success"
        assert entry.decision == PermissionDecision.allow
        assert entry.step_that_decided == 6
        assert entry.deny_reason is None
        assert entry.session_id == req.session_context.session_id

    def test_denied_audit(self, make_permission_request, caplog):
        """deny result should produce outcome=denied logged at WARNING."""
        req = make_permission_request(access_tier=AccessTier.api_key)
        deciding = _make_deny_result(step=1, reason="api_key_not_configured")

        with caplog.at_level(logging.WARNING, logger="kosmos.permissions.audit"):
            entry = write_audit_log(req, deciding, None)

        assert entry.outcome == "denied"
        assert entry.decision == PermissionDecision.deny
        assert entry.deny_reason == "api_key_not_configured"
        # Check that a WARNING was emitted
        audit_records = [r for r in caplog.records if r.name == "kosmos.permissions.audit"]
        assert any(r.levelno == logging.WARNING for r in audit_records)

    def test_failure_audit(self, make_permission_request):
        """allow + failed ToolResult should produce outcome=failure."""
        req = make_permission_request(access_tier=AccessTier.api_key)
        deciding = _make_allow_result(step=6)
        tool_result = _make_failed_tool_result(req.tool_id)

        entry = write_audit_log(req, deciding, tool_result)

        assert entry.outcome == "failure"
        assert entry.error_type == "execution"
        assert entry.decision == PermissionDecision.allow

    def test_no_arguments_json_in_entry(self, make_permission_request):
        """AuditLogEntry should not include arguments_json (sensitive data)."""
        req = make_permission_request()
        deciding = _make_allow_result()
        tool_result = _make_success_tool_result()

        entry = write_audit_log(req, deciding, tool_result)

        # AuditLogEntry model does not have arguments_json field
        assert not hasattr(entry, "arguments_json")

    def test_session_id_captured(self, make_session_context, make_permission_request):
        """entry.session_id should match the session_context.session_id."""
        ctx = make_session_context(session_id="unique-session-abc")
        req = make_permission_request(session_context=ctx)
        deciding = _make_allow_result()
        tool_result = _make_success_tool_result(req.tool_id)

        entry = write_audit_log(req, deciding, tool_result)

        assert entry.session_id == "unique-session-abc"

    def test_deny_reason_none_on_allow(self, make_permission_request):
        """deny_reason should be None when the decision is allow."""
        req = make_permission_request()
        deciding = _make_allow_result()
        tool_result = _make_success_tool_result()

        entry = write_audit_log(req, deciding, tool_result)

        assert entry.deny_reason is None

    def test_error_type_none_on_success(self, make_permission_request):
        """error_type should be None when the tool_result is successful."""
        req = make_permission_request()
        deciding = _make_allow_result()
        tool_result = _make_success_tool_result()

        entry = write_audit_log(req, deciding, tool_result)

        assert entry.error_type is None

    def test_success_audit_logged_at_info_not_warning(self, make_permission_request, caplog):
        """Successful audit entries should be logged at INFO, not WARNING."""
        req = make_permission_request()
        deciding = _make_allow_result()
        tool_result = _make_success_tool_result()

        with caplog.at_level(logging.DEBUG, logger="kosmos.permissions.audit"):
            write_audit_log(req, deciding, tool_result)

        audit_records = [r for r in caplog.records if r.name == "kosmos.permissions.audit"]
        assert audit_records, "Expected at least one audit log record"
        assert all(r.levelno == logging.INFO for r in audit_records)

    def test_denied_audit_logged_at_warning(self, make_permission_request, caplog):
        """Denied audit entries should be logged at WARNING."""
        req = make_permission_request()
        deciding = _make_deny_result()

        with caplog.at_level(logging.DEBUG, logger="kosmos.permissions.audit"):
            write_audit_log(req, deciding, None)

        audit_records = [r for r in caplog.records if r.name == "kosmos.permissions.audit"]
        assert audit_records, "Expected at least one audit log record"
        assert all(r.levelno == logging.WARNING for r in audit_records)
