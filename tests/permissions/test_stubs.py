# SPDX-License-Identifier: Apache-2.0
"""Tests for stubs.py re-exports.

stubs.py now re-exports the real step implementations rather than pass-through
stubs.  These tests verify that the re-exported names are callable and return
the correct step numbers, using minimal valid inputs so each step allows.
"""

from __future__ import annotations

import pytest

from kosmos.permissions.models import PermissionDecision
from kosmos.permissions.steps.step2_intent import reset_call_tracking
from kosmos.permissions.steps.step5_terms import clear_all_consent, grant_consent
from kosmos.permissions.steps.stubs import (
    check_authn,
    check_intent,
    check_params,
    check_terms,
)


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset stateful modules before and after each test."""
    reset_call_tracking()
    clear_all_consent()
    yield
    reset_call_tracking()
    clear_all_consent()


class TestStubReExports:
    """Verify stubs.py re-exports are callable and return correct step numbers."""

    def test_step2_intent_allows_clean_request(self, make_permission_request):
        """check_intent (step 2) allows a clean request."""
        req = make_permission_request()
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_step3_params_allows_clean_request(self, make_permission_request):
        """check_params (step 3) allows a request with clean arguments."""
        req = make_permission_request(arguments_json='{"query": "test"}')
        result = check_params(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 3

    def test_step4_authn_allows_public_tier(self, make_permission_request):
        """check_authn (step 4) allows a public-tier request."""
        req = make_permission_request()
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 4

    def test_step5_terms_allows_with_consent(self, make_permission_request, make_session_context):
        """check_terms (step 5) allows when consent has been granted for the provider."""
        ctx = make_session_context(session_id="stub-test-session")
        # tool_id="test_tool" → provider "test"
        grant_consent("stub-test-session", "test")
        req = make_permission_request(session_context=ctx)
        result = check_terms(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 5

    def test_all_re_exports_return_correct_step_number(
        self, make_permission_request, make_session_context
    ):
        """Each re-exported function returns its own step number."""
        ctx = make_session_context(session_id="step-num-session")
        grant_consent("step-num-session", "test")

        req = make_permission_request(arguments_json='{"query": "ok"}', session_context=ctx)
        assert check_intent(req).step == 2
        assert check_params(req).step == 3
        assert check_authn(req).step == 4
        assert check_terms(req).step == 5
