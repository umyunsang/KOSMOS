# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 2: Rule-based intent analysis."""

from __future__ import annotations

import json

import pytest

from kosmos.permissions.models import AccessTier, PermissionDecision
from kosmos.permissions.steps.step2_intent import (
    MAX_ARGS_BYTES,
    RAPID_CALL_THRESHOLD,
    check_intent,
    reset_call_tracking,
)


@pytest.fixture(autouse=True)
def clear_tracking():
    """Reset rapid-call tracking state before each test."""
    reset_call_tracking()
    yield
    reset_call_tracking()


class TestStep2IntentNormalPatterns:
    """Normal usage patterns that should be allowed."""

    def test_simple_query_allows(self, make_permission_request):
        """A straightforward query should pass intent analysis."""
        req = make_permission_request(arguments_json='{"query": "traffic accident Seoul"}')
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_empty_args_allows(self, make_permission_request):
        """Empty JSON object is a valid argument payload."""
        req = make_permission_request(arguments_json="{}")
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_nested_object_args_allows(self, make_permission_request):
        """Nested but reasonably-sized arguments should be allowed."""
        args = json.dumps({"filter": {"region": "Seoul", "year": 2024}})
        req = make_permission_request(arguments_json=args)
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_unicode_args_allows(self, make_permission_request):
        """Unicode (Korean) values in arguments should be allowed."""
        args = json.dumps({"query": "서울 교통사고"})
        req = make_permission_request(arguments_json=args)
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 2

    def test_returns_step_2(self, make_permission_request):
        """Allow result must carry step=2."""
        req = make_permission_request()
        result = check_intent(req)
        assert result.step == 2


class TestStep2RapidCallDetection:
    """Tests for rapid-call burst detection."""

    def test_below_threshold_allows(self, make_permission_request, make_session_context):
        """Calls below threshold should all be allowed."""
        ctx = make_session_context(session_id="burst-session")
        req = make_permission_request(tool_id="test_tool", session_context=ctx, arguments_json="{}")
        for _ in range(RAPID_CALL_THRESHOLD - 1):
            result = check_intent(req)
            assert result.decision == PermissionDecision.allow

    def test_exactly_at_threshold_denies(self, make_permission_request, make_session_context):
        """Exactly RAPID_CALL_THRESHOLD calls in the window triggers denial."""
        ctx = make_session_context(session_id="burst-session-exact")
        req = make_permission_request(
            tool_id="burst_tool", session_context=ctx, arguments_json="{}"
        )
        for _ in range(RAPID_CALL_THRESHOLD - 1):
            check_intent(req)
        # The Nth call should be denied
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "rapid_call_burst"
        assert result.step == 2

    def test_different_tools_independent_counters(
        self, make_permission_request, make_session_context
    ):
        """Burst on tool_a should not affect tool_b."""
        ctx = make_session_context(session_id="multi-tool-session")

        req_a = make_permission_request(tool_id="tool_a", session_context=ctx, arguments_json="{}")
        req_b = make_permission_request(tool_id="tool_b", session_context=ctx, arguments_json="{}")

        # Trigger burst on tool_a
        for _ in range(RAPID_CALL_THRESHOLD):
            check_intent(req_a)

        # tool_b should still be allowed on first call
        result = check_intent(req_b)
        assert result.decision == PermissionDecision.allow

    def test_different_sessions_independent_counters(
        self, make_permission_request, make_session_context
    ):
        """Burst in session_a should not affect session_b."""
        ctx_a = make_session_context(session_id="session-a")
        ctx_b = make_session_context(session_id="session-b")

        req_a = make_permission_request(
            tool_id="same_tool", session_context=ctx_a, arguments_json="{}"
        )
        req_b = make_permission_request(
            tool_id="same_tool", session_context=ctx_b, arguments_json="{}"
        )

        for _ in range(RAPID_CALL_THRESHOLD):
            check_intent(req_a)

        result = check_intent(req_b)
        assert result.decision == PermissionDecision.allow


class TestStep2ArgumentSizeDetection:
    """Tests for large argument payload detection."""

    def test_payload_at_limit_allows(self, make_permission_request):
        """Payload exactly at MAX_ARGS_BYTES should be allowed."""
        # Build a payload that is exactly MAX_ARGS_BYTES bytes
        padding = "x" * (MAX_ARGS_BYTES - len('{"k": ""}'))
        args = json.dumps({"k": padding})
        assert len(args.encode("utf-8")) <= MAX_ARGS_BYTES
        req = make_permission_request(arguments_json=args)
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow

    def test_payload_over_limit_denies(self, make_permission_request):
        """Payload exceeding MAX_ARGS_BYTES should be denied."""
        padding = "x" * (MAX_ARGS_BYTES + 100)
        args = json.dumps({"k": padding})
        assert len(args.encode("utf-8")) > MAX_ARGS_BYTES
        req = make_permission_request(arguments_json=args)
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "argument_payload_too_large"
        assert result.step == 2


class TestStep2InvalidJSON:
    """Tests for malformed arguments_json detection."""

    def test_invalid_json_denies(self, make_permission_request):
        """Non-JSON arguments_json should be denied."""
        req = make_permission_request(arguments_json="not-json")
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "invalid_arguments_json"

    def test_json_array_denies(self, make_permission_request):
        """JSON array (not object) should be denied."""
        req = make_permission_request(arguments_json="[1, 2, 3]")
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "arguments_not_object"

    def test_json_string_denies(self, make_permission_request):
        """Bare JSON string should be denied."""
        req = make_permission_request(arguments_json='"hello"')
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "arguments_not_object"


class TestStep2PersonalDataTierMismatch:
    """Tests for personal-data tool on public tier mismatch."""

    def test_personal_data_public_tier_denies(self, make_permission_request):
        """is_personal_data=True with public tier should be denied."""
        req = make_permission_request(
            access_tier=AccessTier.public,
            is_personal_data=True,
            arguments_json="{}",
        )
        result = check_intent(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "personal_data_public_tier_mismatch"

    def test_personal_data_api_key_tier_allows(self, make_permission_request):
        """is_personal_data=True with api_key tier should pass this step."""
        req = make_permission_request(
            access_tier=AccessTier.api_key,
            is_personal_data=True,
            arguments_json="{}",
        )
        result = check_intent(req)
        assert result.decision == PermissionDecision.allow
