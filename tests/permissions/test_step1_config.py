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

    def test_api_key_tier_allows_when_set(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should allow when KOSMOS_DATA_GO_KR_API_KEY is set."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-api-key-value")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 1

    def test_api_key_tier_denies_when_missing(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when KOSMOS_DATA_GO_KR_API_KEY is not set."""
        monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_api_key_tier_denies_when_empty(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when KOSMOS_DATA_GO_KR_API_KEY is empty string."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "")
        req = make_permission_request(access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "api_key_not_configured"

    def test_api_key_tier_denies_when_whitespace(self, make_permission_request, monkeypatch):
        """AccessTier.api_key should deny when KOSMOS_DATA_GO_KR_API_KEY is whitespace-only."""
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
