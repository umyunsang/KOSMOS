# SPDX-License-Identifier: Apache-2.0
"""Tests for Step 3: Parameter inspection and Korean PII detection."""

from __future__ import annotations

import json

import pytest

from kosmos.permissions.models import PermissionDecision
from kosmos.permissions.steps.step3_params import (
    check_params,
)


class TestStep3CleanParams:
    """Clean parameter payloads should be allowed."""

    def test_empty_args_allows(self, make_permission_request):
        """Empty JSON object has nothing to scan — should allow."""
        req = make_permission_request(arguments_json="{}")
        result = check_params(req)
        assert result.decision == PermissionDecision.allow
        assert result.step == 3

    def test_normal_query_allows(self, make_permission_request):
        """A normal keyword query contains no PII."""
        req = make_permission_request(
            arguments_json=json.dumps({"query": "Seoul traffic accident 2024"})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_numeric_params_allow(self, make_permission_request):
        """Numeric parameters (int/float) contain no PII."""
        req = make_permission_request(
            arguments_json=json.dumps({"year": 2024, "limit": 10, "offset": 0})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_boolean_params_allow(self, make_permission_request):
        """Boolean parameters contain no PII."""
        req = make_permission_request(arguments_json=json.dumps({"include_archived": True}))
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_null_params_allow(self, make_permission_request):
        """Null values contain no PII."""
        req = make_permission_request(arguments_json=json.dumps({"cursor": None}))
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_list_of_strings_clean_allows(self, make_permission_request):
        """A list of clean strings should be allowed."""
        req = make_permission_request(
            arguments_json=json.dumps({"tags": ["accident", "highway", "2024"]})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_nested_clean_object_allows(self, make_permission_request):
        """Nested clean object should be allowed."""
        req = make_permission_request(
            arguments_json=json.dumps({"filter": {"region": "Gyeonggi", "type": "pedestrian"}})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.allow

    def test_returns_step_3(self, make_permission_request):
        """Allow result must carry step=3."""
        req = make_permission_request()
        result = check_params(req)
        assert result.step == 3


class TestStep3RRNDetection:
    """주민등록번호 (Resident Registration Number) detection."""

    @pytest.mark.parametrize(
        "rrn",
        [
            "900101-1234567",  # male born 1990
            "901231-2345678",  # female born 1990
            "000101-3234567",  # male born 2000
            "000101-4234567",  # female born 2000
        ],
    )
    def test_rrn_in_param_denies(self, make_permission_request, rrn):
        """RRN embedded in a query string should be denied."""
        req = make_permission_request(
            arguments_json=json.dumps({"query": f"resident {rrn} lookup"})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "rrn" in result.reason

    def test_rrn_exact_value_denies(self, make_permission_request):
        """RRN as the exact parameter value should be denied."""
        req = make_permission_request(arguments_json=json.dumps({"id_number": "900101-1234567"}))
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "rrn" in result.reason

    def test_rrn_in_pii_accepting_param_allowed(self, make_permission_request):
        """RRN in a PII-accepting parameter should NOT be flagged."""
        req = make_permission_request(
            arguments_json=json.dumps({"resident_number": "900101-1234567"})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.allow


class TestStep3PhoneDetection:
    """전화번호 (Korean mobile phone number) detection."""

    @pytest.mark.parametrize(
        "phone",
        [
            "010-1234-5678",
            "0101234-5678",  # missing first hyphen
            "010-12345678",  # missing second hyphen
            "01012345678",  # no hyphens
            "011-123-4567",  # old SKT prefix
            "016-123-4567",  # old KT prefix
            "017-123-4567",
            "018-123-4567",
            "019-123-4567",
        ],
    )
    def test_phone_in_param_denies(self, make_permission_request, phone):
        """Korean mobile phone number should be denied."""
        req = make_permission_request(arguments_json=json.dumps({"contact": phone}))
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "phone_kr" in result.reason

    def test_phone_in_pii_accepting_param_allowed(self, make_permission_request):
        """Phone number in phone_number param should NOT be flagged."""
        req = make_permission_request(arguments_json=json.dumps({"phone_number": "010-1234-5678"}))
        result = check_params(req)
        assert result.decision == PermissionDecision.allow


class TestStep3EmailDetection:
    """이메일 (email address) detection."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "test.user+tag@sub.domain.co.kr",
            "admin@gov.kr",
        ],
    )
    def test_email_in_param_denies(self, make_permission_request, email):
        """Email address in parameters should be denied."""
        req = make_permission_request(arguments_json=json.dumps({"contact_info": email}))
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "email" in result.reason


class TestStep3PassportDetection:
    """여권번호 (passport number) detection."""

    @pytest.mark.parametrize(
        "passport",
        [
            "M12345678",
            "A98765432",
            "Z00000001",
        ],
    )
    def test_passport_in_param_denies(self, make_permission_request, passport):
        """Korean passport number should be denied."""
        req = make_permission_request(arguments_json=json.dumps({"document": passport}))
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "passport_kr" in result.reason

    def test_passport_in_pii_accepting_param_allowed(self, make_permission_request):
        """Passport number in passport_number param should NOT be flagged."""
        req = make_permission_request(arguments_json=json.dumps({"passport_number": "M12345678"}))
        result = check_params(req)
        assert result.decision == PermissionDecision.allow


class TestStep3CreditCardDetection:
    """신용카드 번호 (credit card number) detection."""

    @pytest.mark.parametrize(
        "card",
        [
            "1234-5678-9012-3456",
            "1234 5678 9012 3456",
            "1234567890123456",
        ],
    )
    def test_credit_card_in_param_denies(self, make_permission_request, card):
        """Credit card number in parameters should be denied."""
        req = make_permission_request(arguments_json=json.dumps({"payment": card}))
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "credit_card" in result.reason


class TestStep3NestedPII:
    """PII embedded inside nested or list structures."""

    def test_pii_in_nested_object_denies(self, make_permission_request):
        """PII inside a nested dict should be detected."""
        req = make_permission_request(
            arguments_json=json.dumps({"filter": {"owner": {"id_number": "900101-1234567"}}})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "rrn" in result.reason

    def test_pii_in_list_denies(self, make_permission_request):
        """PII inside a list element should be detected."""
        req = make_permission_request(
            arguments_json=json.dumps({"ids": ["clean", "900101-1234567", "also-clean"]})
        )
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert "rrn" in result.reason


class TestStep3InvalidJSON:
    """Malformed argument payloads should be denied."""

    def test_invalid_json_denies(self, make_permission_request):
        """Non-parseable JSON should be denied."""
        req = make_permission_request(arguments_json="not-json{")
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "invalid_arguments_json"

    def test_json_array_root_denies(self, make_permission_request):
        """Root-level JSON array (not object) should be denied."""
        req = make_permission_request(arguments_json="[1, 2, 3]")
        result = check_params(req)
        assert result.decision == PermissionDecision.deny
        assert result.reason == "arguments_not_object"
