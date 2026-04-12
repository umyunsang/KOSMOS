# SPDX-License-Identifier: Apache-2.0
"""Unit tests for permission pipeline foundational models (T006)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kosmos.permissions.models import (
    AccessTier,
    AuditLogEntry,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
    SessionContext,
)


# ---------------------------------------------------------------------------
# AccessTier enum
# ---------------------------------------------------------------------------


class TestAccessTier:
    """AccessTier enum values and string representation."""

    def test_values(self):
        assert AccessTier.public == "public"
        assert AccessTier.api_key == "api_key"
        assert AccessTier.authenticated == "authenticated"
        assert AccessTier.restricted == "restricted"

    def test_membership(self):
        assert len(AccessTier) == 4

    def test_is_str_enum(self):
        assert isinstance(AccessTier.public, str)


# ---------------------------------------------------------------------------
# PermissionDecision enum
# ---------------------------------------------------------------------------


class TestPermissionDecision:
    """PermissionDecision enum values."""

    def test_values(self):
        assert PermissionDecision.allow == "allow"
        assert PermissionDecision.deny == "deny"
        assert PermissionDecision.escalate == "escalate"

    def test_membership(self):
        assert len(PermissionDecision) == 3


# ---------------------------------------------------------------------------
# SessionContext
# ---------------------------------------------------------------------------


class TestSessionContext:
    """SessionContext frozen model tests."""

    def test_minimal_construction(self):
        ctx = SessionContext(session_id="s1")
        assert ctx.session_id == "s1"
        assert ctx.citizen_id is None
        assert ctx.auth_level == 0
        assert ctx.consented_providers == []

    def test_full_construction(self):
        ctx = SessionContext(
            session_id="s2",
            citizen_id="cid-123",
            auth_level=2,
            consented_providers=["koroad", "kma"],
        )
        assert ctx.citizen_id == "cid-123"
        assert ctx.auth_level == 2
        assert ctx.consented_providers == ["koroad", "kma"]

    def test_frozen(self):
        ctx = SessionContext(session_id="s1")
        with pytest.raises(ValidationError):
            ctx.session_id = "mutated"

    def test_session_id_required(self):
        with pytest.raises(ValidationError):
            SessionContext()


# ---------------------------------------------------------------------------
# PermissionCheckRequest
# ---------------------------------------------------------------------------


class TestPermissionCheckRequest:
    """PermissionCheckRequest frozen model tests."""

    def test_minimal_construction(self):
        req = PermissionCheckRequest(
            tool_id="test_tool",
            access_tier=AccessTier.public,
            arguments_json="{}",
            session_context=SessionContext(session_id="s1"),
            is_personal_data=False,
        )
        assert req.tool_id == "test_tool"
        assert req.access_tier == AccessTier.public
        assert req.is_bypass_mode is False

    def test_frozen(self):
        req = PermissionCheckRequest(
            tool_id="test_tool",
            access_tier=AccessTier.public,
            arguments_json="{}",
            session_context=SessionContext(session_id="s1"),
            is_personal_data=False,
        )
        with pytest.raises(ValidationError):
            req.tool_id = "mutated"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PermissionCheckRequest(
                tool_id="test_tool",
                # missing access_tier, arguments_json, session_context, is_personal_data
            )

    def test_bypass_mode_default_false(self):
        req = PermissionCheckRequest(
            tool_id="t",
            access_tier=AccessTier.api_key,
            arguments_json="{}",
            session_context=SessionContext(session_id="s1"),
            is_personal_data=True,
            # is_bypass_mode not provided
        )
        assert req.is_bypass_mode is False

    def test_bypass_mode_explicit_true(self):
        req = PermissionCheckRequest(
            tool_id="t",
            access_tier=AccessTier.api_key,
            arguments_json="{}",
            session_context=SessionContext(session_id="s1"),
            is_personal_data=True,
            is_bypass_mode=True,
        )
        assert req.is_bypass_mode is True


# ---------------------------------------------------------------------------
# PermissionStepResult
# ---------------------------------------------------------------------------


class TestPermissionStepResult:
    """PermissionStepResult frozen model tests."""

    def test_allow_result(self):
        result = PermissionStepResult(
            decision=PermissionDecision.allow,
            step=1,
        )
        assert result.decision == PermissionDecision.allow
        assert result.step == 1
        assert result.reason is None

    def test_deny_result_with_reason(self):
        result = PermissionStepResult(
            decision=PermissionDecision.deny,
            step=1,
            reason="api_key_not_configured",
        )
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_frozen(self):
        result = PermissionStepResult(
            decision=PermissionDecision.allow,
            step=1,
        )
        with pytest.raises(ValidationError):
            result.step = 2

    def test_escalate_result(self):
        result = PermissionStepResult(
            decision=PermissionDecision.escalate,
            step=3,
            reason="needs_review",
        )
        assert result.decision == PermissionDecision.escalate


# ---------------------------------------------------------------------------
# AuditLogEntry
# ---------------------------------------------------------------------------


class TestAuditLogEntry:
    """AuditLogEntry frozen model tests — no ``arguments_json`` field."""

    def test_full_construction(self):
        now = datetime.now(UTC)
        entry = AuditLogEntry(
            timestamp=now,
            tool_id="koroad_accident_search",
            access_tier=AccessTier.api_key,
            decision=PermissionDecision.allow,
            step_that_decided=5,
            outcome="success",
            session_id="s1",
        )
        assert entry.tool_id == "koroad_accident_search"
        assert entry.outcome == "success"
        assert entry.error_type is None
        assert entry.deny_reason is None

    def test_denied_entry(self):
        now = datetime.now(UTC)
        entry = AuditLogEntry(
            timestamp=now,
            tool_id="restricted_tool",
            access_tier=AccessTier.restricted,
            decision=PermissionDecision.deny,
            step_that_decided=1,
            outcome="denied",
            deny_reason="tier_restricted_not_implemented",
            session_id="s1",
        )
        assert entry.outcome == "denied"
        assert entry.deny_reason == "tier_restricted_not_implemented"

    def test_frozen(self):
        now = datetime.now(UTC)
        entry = AuditLogEntry(
            timestamp=now,
            tool_id="t",
            access_tier=AccessTier.public,
            decision=PermissionDecision.allow,
            step_that_decided=1,
            outcome="success",
            session_id="s1",
        )
        with pytest.raises(ValidationError):
            entry.tool_id = "mutated"

    def test_no_arguments_json_field(self):
        """AuditLogEntry must NOT have an ``arguments_json`` field (PII safety)."""
        assert not hasattr(AuditLogEntry.model_fields, "arguments_json")
        assert "arguments_json" not in AuditLogEntry.model_fields

    def test_no_any_types(self):
        """No field in AuditLogEntry should use ``Any`` type."""
        for name, field_info in AuditLogEntry.model_fields.items():
            annotation = field_info.annotation
            # Check string representation for 'Any' as a simple heuristic
            assert "Any" not in str(annotation), (
                f"Field {name!r} uses Any type: {annotation}"
            )

    def test_outcome_literal(self):
        """outcome must be one of 'success', 'failure', 'denied'."""
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            AuditLogEntry(
                timestamp=now,
                tool_id="t",
                access_tier=AccessTier.public,
                decision=PermissionDecision.allow,
                step_that_decided=1,
                outcome="invalid_outcome",
                session_id="s1",
            )


# ---------------------------------------------------------------------------
# Import-time env isolation (SC-010)
# ---------------------------------------------------------------------------


class TestImportIsolation:
    """Importing models must not read env vars or cause side effects."""

    def test_import_does_not_fail_without_env(self, monkeypatch):
        """Models import successfully even without any KOSMOS_* env vars."""
        monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)
        # Re-import the module to verify no import-time env reads
        import importlib

        import kosmos.permissions.models as mod

        importlib.reload(mod)
        # If we get here, import succeeded
        assert mod.AccessTier.public == "public"
