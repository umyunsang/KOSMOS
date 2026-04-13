# SPDX-License-Identifier: Apache-2.0
"""Tests for Steps 2-5: Pass-through stub implementations."""

from __future__ import annotations

from kosmos.permissions.models import PermissionDecision
from kosmos.permissions.steps.stubs import (
    check_authn,
    check_intent,
    check_params,
    check_terms,
)


class TestStubSteps:
    """Steps 2-5 return allow unconditionally."""

    def test_step2_intent_allows(self, make_permission_request):
        """check_intent (step 2) should return allow unconditionally."""
        req = make_permission_request()
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_step3_params_allows(self, make_permission_request):
        """check_params (step 3) should return allow unconditionally."""
        req = make_permission_request()
        result = check_params(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 3

    def test_step4_authn_allows(self, make_permission_request):
        """check_authn (step 4) should return allow unconditionally."""
        req = make_permission_request()
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 4

    def test_step5_terms_allows(self, make_permission_request):
        """check_terms (step 5) should return allow unconditionally."""
        req = make_permission_request()
        result = check_terms(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 5

    def test_all_stubs_return_correct_step_number(self, make_permission_request):
        """Each stub function should return its correct step number."""
        req = make_permission_request()
        assert check_intent(req).step == 2
        assert check_params(req).step == 3
        assert check_authn(req).step == 4
        assert check_terms(req).step == 5
