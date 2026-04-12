# SPDX-License-Identifier: Apache-2.0
"""Tests for bypass-immune permission rules."""
from __future__ import annotations

import json
import logging

import pytest

from kosmos.permissions.bypass import check_bypass_immune
from kosmos.permissions.models import PermissionDecision


class TestBypassImmune:
    """Bypass-immune rule enforcement."""

    def test_no_personal_data_passes(self, make_permission_request):
        """is_personal_data=False should pass all bypass-immune checks."""
        req = make_permission_request(is_personal_data=False)
        result = check_bypass_immune(req)
        assert result is None

    def test_citizen_mismatch_denies(self, make_session_context, make_permission_request):
        """Different citizen_id in args vs session should deny."""
        ctx = make_session_context(citizen_id="citizen-A")
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            arguments_json=json.dumps({"citizen_id": "citizen-B"}),
        )
        result = check_bypass_immune(req)
        assert result is not None
        assert result.decision == PermissionDecision.deny
        assert result.step == 0
        assert result.reason == "personal_data_citizen_mismatch"

    def test_citizen_match_passes(self, make_session_context, make_permission_request):
        """Same citizen_id in args and session should pass."""
        ctx = make_session_context(citizen_id="citizen-A")
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            arguments_json=json.dumps({"citizen_id": "citizen-A"}),
        )
        result = check_bypass_immune(req)
        assert result is None

    def test_bypass_mode_logs_warning(
        self, make_permission_request, caplog
    ):
        """is_bypass_mode=True should log a WARNING but still enforce rules."""
        req = make_permission_request(is_bypass_mode=True, is_personal_data=False)

        with caplog.at_level(logging.WARNING, logger="kosmos.permissions.bypass"):
            result = check_bypass_immune(req)

        assert result is None  # No rule fires for non-personal data
        # Verify the bypass warning was emitted
        bypass_records = [
            r for r in caplog.records if "bypass" in r.message.lower() or "bypass" in r.name
        ]
        assert any("bypass" in r.message.lower() for r in caplog.records)

    def test_no_citizen_id_in_session_passes(self, make_session_context, make_permission_request):
        """citizen_id=None in session should skip the mismatch check."""
        ctx = make_session_context(citizen_id=None)
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            arguments_json=json.dumps({"citizen_id": "some-citizen"}),
        )
        result = check_bypass_immune(req)
        assert result is None

    def test_invalid_json_fails_closed(self, make_session_context, make_permission_request):
        """Malformed arguments_json should fail closed (deny)."""
        ctx = make_session_context(citizen_id="citizen-A")
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            arguments_json="not-valid-json{{{",
        )
        result = check_bypass_immune(req)
        assert result is not None
        assert result.decision == PermissionDecision.deny
        assert result.reason == "internal_error"

    def test_bypass_mode_still_denies_on_mismatch(
        self, make_session_context, make_permission_request
    ):
        """Bypass mode should still enforce citizen_id mismatch rule."""
        ctx = make_session_context(citizen_id="citizen-A")
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            is_bypass_mode=True,
            arguments_json=json.dumps({"citizen_id": "citizen-B"}),
        )
        result = check_bypass_immune(req)
        assert result is not None
        assert result.decision == PermissionDecision.deny
        assert result.reason == "personal_data_citizen_mismatch"

    def test_no_citizen_id_in_args_passes(self, make_session_context, make_permission_request):
        """No citizen_id in args (None from .get()) should pass the mismatch check."""
        ctx = make_session_context(citizen_id="citizen-A")
        req = make_permission_request(
            session_context=ctx,
            is_personal_data=True,
            arguments_json=json.dumps({"other_param": "value"}),
        )
        result = check_bypass_immune(req)
        assert result is None
