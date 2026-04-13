# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 5: Ministry Terms-of-Use consent enforcement."""

from __future__ import annotations

import pytest

from kosmos.permissions.models import PermissionDecision
from kosmos.permissions.steps.step5_terms import (
    check_terms,
    clear_all_consent,
    grant_consent,
    revoke_consent,
)


@pytest.fixture(autouse=True)
def reset_consent_registry():
    """Wipe the in-memory consent registry before and after each test."""
    clear_all_consent()
    yield
    clear_all_consent()


class TestStep5ConsentMissing:
    """When consent is not recorded the call should be denied."""

    def test_no_consent_denies(self, make_permission_request):
        """No consent recorded → deny with provider in reason."""
        req = make_permission_request(tool_id="koroad_accident_search")
        result = check_terms(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 5
        assert "koroad" in result.reason

    def test_deny_reason_format(self, make_permission_request):
        """Deny reason should be 'terms_not_accepted:<provider>'."""
        req = make_permission_request(tool_id="weather_forecast_daily")
        result = check_terms(req)
        assert result.reason == "terms_not_accepted:weather"

    def test_no_underscore_tool_id_uses_full_name(self, make_permission_request):
        """Tool IDs without underscores use the full name as provider."""
        req = make_permission_request(tool_id="publicdata")
        result = check_terms(req)
        assert "publicdata" in result.reason

    def test_returns_step_5(self, make_permission_request):
        """Deny result must carry step=5."""
        req = make_permission_request(tool_id="koroad_search")
        result = check_terms(req)
        assert result.step == 5


class TestStep5GrantConsent:
    """grant_consent() should unlock subsequent calls."""

    def test_grant_consent_allows(self, make_permission_request, make_session_context):
        """After grant_consent, the same request should be allowed."""
        ctx = make_session_context(session_id="session-grant-test")
        req = make_permission_request(tool_id="koroad_accident_search", session_context=ctx)
        grant_consent("session-grant-test", "koroad")
        result = check_terms(req)
        assert result.decision == PermissionDecision.allow

    def test_consent_scoped_to_session(self, make_permission_request, make_session_context):
        """Consent for session A should not apply to session B."""
        _ctx_a = make_session_context(session_id="session-a")
        ctx_b = make_session_context(session_id="session-b")

        req_b = make_permission_request(tool_id="koroad_accident_search", session_context=ctx_b)

        grant_consent("session-a", "koroad")  # Only session-a is consented
        result = check_terms(req_b)
        assert result.decision == PermissionDecision.deny

    def test_consent_scoped_to_provider(self, make_permission_request, make_session_context):
        """Consent for provider X should not allow provider Y."""
        ctx = make_session_context(session_id="scoped-provider-session")
        req = make_permission_request(tool_id="weather_forecast", session_context=ctx)
        grant_consent("scoped-provider-session", "koroad")  # wrong provider
        result = check_terms(req)
        assert result.decision == PermissionDecision.deny

    def test_consent_allows_any_tool_with_same_provider(
        self, make_permission_request, make_session_context
    ):
        """Consent for 'koroad' applies to any koroad_* tool."""
        ctx = make_session_context(session_id="provider-scope-session")
        grant_consent("provider-scope-session", "koroad")

        for tool_id in [
            "koroad_accident_search",
            "koroad_road_condition",
            "koroad_driver_license",
        ]:
            req = make_permission_request(tool_id=tool_id, session_context=ctx)
            result = check_terms(req)
            assert result.decision == PermissionDecision.allow, f"Expected allow for tool {tool_id}"


class TestStep5RevokeConsent:
    """revoke_consent() should re-block access after granting."""

    def test_revoke_after_grant_denies(self, make_permission_request, make_session_context):
        """After revoking consent, subsequent call should be denied again."""
        ctx = make_session_context(session_id="revoke-test-session")
        req = make_permission_request(tool_id="koroad_accident_search", session_context=ctx)
        grant_consent("revoke-test-session", "koroad")
        assert check_terms(req).decision == PermissionDecision.allow

        revoke_consent("revoke-test-session", "koroad")
        assert check_terms(req).decision == PermissionDecision.deny

    def test_revoke_nonexistent_is_noop(self):
        """Revoking consent that was never granted should not raise."""
        revoke_consent("ghost-session", "ghost-provider")  # must not raise


class TestStep5SessionContextConsentedProviders:
    """SessionContext.consented_providers should also be honoured."""

    def test_session_context_consented_provider_allows(
        self, make_permission_request, make_session_context
    ):
        """Consent stored in SessionContext.consented_providers should be recognised."""
        ctx = make_session_context(
            session_id="ctx-consent-session",
            consented_providers=["koroad"],
        )
        req = make_permission_request(tool_id="koroad_accident_search", session_context=ctx)
        # No grant_consent() call — relies solely on SessionContext
        result = check_terms(req)
        assert result.decision == PermissionDecision.allow

    def test_session_context_wrong_provider_denies(
        self, make_permission_request, make_session_context
    ):
        """SessionContext.consented_providers for other provider does not help."""
        ctx = make_session_context(
            session_id="ctx-wrong-provider",
            consented_providers=["weather"],
        )
        req = make_permission_request(tool_id="koroad_accident_search", session_context=ctx)
        result = check_terms(req)
        assert result.decision == PermissionDecision.deny
