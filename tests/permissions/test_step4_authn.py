# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 4: Citizen authentication level enforcement."""

from __future__ import annotations

import pytest

from kosmos.permissions.models import AccessTier, PermissionDecision
from kosmos.permissions.steps.step4_authn import (
    AUTH_LEVEL_ANONYMOUS,
    AUTH_LEVEL_BASIC,
    AUTH_LEVEL_VERIFIED,
    check_authn,
)


class TestStep4PublicTier:
    """Public tier should allow at any auth level."""

    @pytest.mark.parametrize("auth_level", [0, 1, 2, 99])
    def test_public_tier_any_auth_level_allows(
        self, make_permission_request, make_session_context, auth_level
    ):
        """Public tier allows regardless of auth_level."""
        ctx = make_session_context(auth_level=auth_level)
        req = make_permission_request(access_tier=AccessTier.public, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 4


class TestStep4ApiKeyTier:
    """API key tier should allow at any auth level."""

    @pytest.mark.parametrize("auth_level", [0, 1, 2])
    def test_api_key_tier_any_auth_level_allows(
        self, make_permission_request, make_session_context, auth_level
    ):
        """API key tier allows at all auth levels (key presence = step 1)."""
        ctx = make_session_context(auth_level=auth_level)
        req = make_permission_request(access_tier=AccessTier.api_key, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow


class TestStep4AuthenticatedTier:
    """Authenticated tier requires auth_level >= AUTH_LEVEL_VERIFIED."""

    def test_anonymous_denies(self, make_permission_request, make_session_context):
        """auth_level=0 (anonymous) should be denied for authenticated tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_ANONYMOUS)
        req = make_permission_request(access_tier=AccessTier.authenticated, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "insufficient_auth_level"
        assert result.step == 4

    def test_basic_auth_denies(self, make_permission_request, make_session_context):
        """auth_level=1 (basic) should be denied for authenticated tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_BASIC)
        req = make_permission_request(access_tier=AccessTier.authenticated, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "insufficient_auth_level"

    def test_verified_allows(self, make_permission_request, make_session_context):
        """auth_level=2 (verified) should be allowed for authenticated tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_VERIFIED, citizen_id="citizen-abc")
        req = make_permission_request(access_tier=AccessTier.authenticated, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow

    def test_verified_without_citizen_id_still_allows(
        self, make_permission_request, make_session_context
    ):
        """Authenticated tier does NOT require citizen_id (only restricted does)."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_VERIFIED, citizen_id=None)
        req = make_permission_request(access_tier=AccessTier.authenticated, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow


class TestStep4RestrictedTier:
    """Restricted tier requires auth_level >= AUTH_LEVEL_VERIFIED AND citizen_id."""

    def test_anonymous_without_citizen_id_denies(
        self, make_permission_request, make_session_context
    ):
        """Anonymous with no citizen_id should be denied for restricted tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_ANONYMOUS, citizen_id=None)
        req = make_permission_request(access_tier=AccessTier.restricted, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "insufficient_auth_level"

    def test_verified_without_citizen_id_denies(
        self, make_permission_request, make_session_context
    ):
        """Verified auth but no citizen_id should be denied for restricted tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_VERIFIED, citizen_id=None)
        req = make_permission_request(access_tier=AccessTier.restricted, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "citizen_id_required"

    def test_verified_with_citizen_id_allows(self, make_permission_request, make_session_context):
        """Verified auth with citizen_id should be allowed for restricted tier."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_VERIFIED, citizen_id="citizen-xyz")
        req = make_permission_request(access_tier=AccessTier.restricted, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.allow

    def test_basic_auth_with_citizen_id_denies(self, make_permission_request, make_session_context):
        """Basic auth (level 1) with citizen_id still denied — auth level too low."""
        ctx = make_session_context(auth_level=AUTH_LEVEL_BASIC, citizen_id="citizen-xyz")
        req = make_permission_request(access_tier=AccessTier.restricted, session_context=ctx)
        result = check_authn(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "insufficient_auth_level"


class TestStep4StepNumber:
    """Step result must always carry step=4."""

    @pytest.mark.parametrize(
        "tier",
        [AccessTier.public, AccessTier.api_key, AccessTier.authenticated, AccessTier.restricted],
    )
    def test_step_number_is_4(self, make_permission_request, make_session_context, tier):
        ctx = make_session_context(auth_level=AUTH_LEVEL_VERIFIED, citizen_id="cid")
        req = make_permission_request(access_tier=tier, session_context=ctx)
        result = check_authn(req)
        assert result.step == 4
