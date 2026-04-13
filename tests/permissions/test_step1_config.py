# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 1: Configuration-based access tier enforcement."""

from __future__ import annotations

from kosmos.permissions.models import AccessTier, PermissionDecision
from kosmos.permissions.steps.step1_config import check_config


class TestStep1Config:
    """Step 1 configuration-based access tier enforcement."""

    def test_public_tier_allows(self, make_permission_request):
        """AccessTier.public should always allow regardless of env vars."""
        req = make_permission_request(access_tier=AccessTier.public)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 1

    def test_api_key_tier_allows_when_data_go_kr_key_set(
        self, make_permission_request, monkeypatch
    ):
        """AccessTier.api_key should allow when KOSMOS_DATA_GO_KR_API_KEY is set."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-api-key-value")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 1

    def test_api_key_tier_allows_when_other_kosmos_key_set(
        self, make_permission_request, monkeypatch
    ):
        """AccessTier.api_key should allow when any KOSMOS_*_API_KEY env var is set."""
        monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)
        monkeypatch.setenv("KOSMOS_KOROAD_API_KEY", "other-service-key")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 1

    def test_api_key_tier_denies_when_no_kosmos_key_set(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when no KOSMOS_*_API_KEY env var is set."""
        import os

        # Remove all KOSMOS_*_API_KEY vars that might exist in the environment
        kosmos_api_keys = [
            k for k in os.environ if k.startswith("KOSMOS_") and k.endswith("_API_KEY")
        ]
        for key in kosmos_api_keys:
            monkeypatch.delenv(key, raising=False)
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_api_key_tier_denies_when_missing(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when no KOSMOS_*_API_KEY is set."""
        import os

        for k in [k for k in os.environ if k.startswith("KOSMOS_") and k.endswith("_API_KEY")]:
            monkeypatch.delenv(k, raising=False)
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_api_key_tier_denies_when_empty(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when all KOSMOS_*_API_KEY vars are empty."""
        import os

        for k in [k for k in os.environ if k.startswith("KOSMOS_") and k.endswith("_API_KEY")]:
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_api_key_tier_denies_when_whitespace(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when all KOSMOS_*_API_KEY vars are whitespace."""
        import os

        for k in [k for k in os.environ if k.startswith("KOSMOS_") and k.endswith("_API_KEY")]:
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "   ")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_authenticated_tier_denies(self, make_permission_request):
        """AccessTier.authenticated should deny with reason citizen_auth_not_implemented."""
        req = make_permission_request(access_tier=AccessTier.authenticated)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "citizen_auth_not_implemented"

    def test_restricted_tier_denies(self, make_permission_request):
        """AccessTier.restricted should deny with reason tier_restricted_not_implemented."""
        req = make_permission_request(access_tier=AccessTier.restricted)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "tier_restricted_not_implemented"
