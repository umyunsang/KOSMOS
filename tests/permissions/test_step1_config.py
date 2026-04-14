# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 1: Configuration-based access tier enforcement.

Step 1 is provider-aware: a Kakao-backed tool requires ``KOSMOS_KAKAO_API_KEY``
(or an override / legacy global), while a data.go.kr-backed tool requires
``KOSMOS_DATA_GO_KR_API_KEY``.  An unrelated KOSMOS_* env var must **not**
satisfy an api_key tier check for a tool whose provider is different.
"""

from __future__ import annotations

import os

import pytest

from kosmos.permissions.models import AccessTier, PermissionDecision
from kosmos.permissions.steps.step1_config import check_config


def _clear_all_kosmos_api_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every ``KOSMOS_*_API_KEY`` and ``KOSMOS_API_KEY`` from the env."""
    for k in [k for k in os.environ if k.startswith("KOSMOS_") and k.endswith("_API_KEY")]:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("KOSMOS_API_KEY", raising=False)


class TestStep1TierDecisions:
    """Public / authenticated / restricted tier decisions."""

    def test_public_tier_allows(self, make_permission_request):
        req = make_permission_request(access_tier=AccessTier.public)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 1

    def test_authenticated_tier_denies(self, make_permission_request):
        req = make_permission_request(access_tier=AccessTier.authenticated)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "citizen_auth_not_implemented"

    def test_restricted_tier_denies(self, make_permission_request):
        req = make_permission_request(access_tier=AccessTier.restricted)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.step == 1
        assert result.reason == "tier_restricted_not_implemented"


class TestStep1ProviderAwareCredentialCheck:
    """api_key tier: credential must belong to the tool's actual provider."""

    def test_kakao_tool_allows_with_kakao_key(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "kakao-value")
        req = make_permission_request(tool_id="address_to_region", access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow

    def test_kakao_tool_denied_with_only_data_go_kr_key(self, make_permission_request, monkeypatch):
        """Regression: Kakao tool must not be satisfied by a data.go.kr key."""
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "data-only-value")
        req = make_permission_request(tool_id="address_to_region", access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_data_go_kr_tool_allows_with_data_go_kr_key(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "data-value")
        req = make_permission_request(
            tool_id="koroad_accident_search", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.allow

    def test_data_go_kr_tool_denied_with_only_kakao_key(self, make_permission_request, monkeypatch):
        """Regression: data.go.kr tool must not be satisfied by a Kakao key."""
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "kakao-only-value")
        req = make_permission_request(
            tool_id="koroad_accident_search", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_kma_tool_requires_data_go_kr_key(self, make_permission_request, monkeypatch):
        """KMA tools share data.go.kr credentials, not Kakao."""
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "irrelevant")
        req = make_permission_request(
            tool_id="kma_short_term_forecast", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_per_tool_override_satisfies(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_ADDRESS_TO_REGION_API_KEY", "tool-override")
        req = make_permission_request(tool_id="address_to_region", access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow

    def test_legacy_global_key_satisfies(self, make_permission_request, monkeypatch):
        """Legacy ``KOSMOS_API_KEY`` is still accepted for any registered tool."""
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_API_KEY", "legacy-global")
        req = make_permission_request(tool_id="address_to_region", access_tier=AccessTier.api_key)
        result = check_config(req)
        assert result.decision == PermissionDecision.allow


class TestStep1CredentialAbsenceFailClosed:
    """Missing / empty / whitespace credentials must deny."""

    def test_denies_when_nothing_set(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        req = make_permission_request(
            tool_id="koroad_accident_search", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_denies_when_credential_empty_string(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "")
        req = make_permission_request(
            tool_id="koroad_accident_search", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"

    def test_denies_when_credential_whitespace(self, make_permission_request, monkeypatch):
        _clear_all_kosmos_api_keys(monkeypatch)
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "    ")
        req = make_permission_request(
            tool_id="koroad_accident_search", access_tier=AccessTier.api_key
        )
        result = check_config(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "api_key_not_configured"
