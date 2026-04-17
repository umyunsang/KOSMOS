# SPDX-License-Identifier: Apache-2.0
"""Round-trip tests for the two new LookupErrorReason members added by T004.

Tests:
- ``LookupErrorReason.content_blocked`` and ``LookupErrorReason.injection_detected``
  round-trip through enum construction, ``make_error_envelope()``, ``model_dump()``,
  and ``model_validate()``.

No live API calls are made. No mocking.
"""

from __future__ import annotations

import uuid

import pytest

from kosmos.tools.envelope import make_error_envelope
from kosmos.tools.errors import LookupErrorReason
from kosmos.tools.models import LookupError  # noqa: A004

_REQUEST_ID = str(uuid.uuid4())

_NEW_MEMBERS = [
    LookupErrorReason.content_blocked,
    LookupErrorReason.injection_detected,
]


class TestNewLookupErrorReasonRoundTrip:
    """Parametric round-trip coverage for content_blocked and injection_detected."""

    @pytest.mark.parametrize("member", _NEW_MEMBERS, ids=lambda m: m.value)
    def test_string_value_round_trips(self, member: LookupErrorReason) -> None:
        """Constructing enum from its string value returns the canonical member."""
        reconstructed = LookupErrorReason(member.value)
        assert reconstructed == member

    @pytest.mark.parametrize("member", _NEW_MEMBERS, ids=lambda m: m.value)
    def test_make_error_envelope_reason_attribute(self, member: LookupErrorReason) -> None:
        """make_error_envelope() returns an envelope whose .reason equals the enum member."""
        envelope = make_error_envelope(
            tool_id="safety_gate",
            reason=member,
            message=f"Blocked by safety rail: {member.value}",
            request_id=_REQUEST_ID,
            elapsed_ms=1,
        )
        assert isinstance(envelope, LookupError)
        assert envelope.reason == member

    @pytest.mark.parametrize("member", _NEW_MEMBERS, ids=lambda m: m.value)
    def test_model_dump_reason_is_string(self, member: LookupErrorReason) -> None:
        """model_dump() serialises reason as the plain string value."""
        envelope = make_error_envelope(
            tool_id="safety_gate",
            reason=member,
            message=f"Blocked by safety rail: {member.value}",
            request_id=_REQUEST_ID,
            elapsed_ms=1,
        )
        dumped = envelope.model_dump()
        assert dumped["reason"] == member.value

    @pytest.mark.parametrize("member", _NEW_MEMBERS, ids=lambda m: m.value)
    def test_model_validate_reason_is_enum(self, member: LookupErrorReason) -> None:
        """model_validate() deserialises the string back to the exact enum member."""
        payload = {
            "kind": "error",
            "reason": member.value,
            "message": f"Blocked by safety rail: {member.value}",
            "retryable": False,
        }
        validated = LookupError.model_validate(payload)
        assert validated.reason is member
