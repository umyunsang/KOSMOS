# SPDX-License-Identifier: Apache-2.0
"""T047 [P] — Lifetime ceiling validation: SubscribeInput rejects lifetime_seconds > 365 days.

FR-011: lifetime is bounded; timedelta(days=365) = 31_536_000s is the enforced ceiling.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.primitives.subscribe import SubscribeInput


class TestLifetimeBound:
    """T047 — FR-011 lifetime_seconds ceiling at 365 days (31_536_000s)."""

    def test_lifetime_seconds_at_ceiling_is_valid(self):
        """Exactly 31_536_000s (365 days) must be accepted."""
        inp = SubscribeInput(
            tool_id="some_tool",
            params={},
            lifetime_seconds=31_536_000,
        )
        assert inp.lifetime_seconds == 31_536_000

    def test_lifetime_seconds_above_ceiling_rejected(self):
        """31_536_001s (365 days + 1s) must be rejected with ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SubscribeInput(
                tool_id="some_tool",
                params={},
                lifetime_seconds=31_536_001,
            )
        errors = exc_info.value.errors()
        assert any(
            "lifetime_seconds" in str(e.get("loc", "")) for e in errors
        ), f"Expected error on lifetime_seconds, got: {errors}"

    def test_lifetime_seconds_zero_rejected(self):
        """0s must be rejected (minimum=1)."""
        with pytest.raises(ValidationError):
            SubscribeInput(
                tool_id="some_tool",
                params={},
                lifetime_seconds=0,
            )

    def test_lifetime_seconds_negative_rejected(self):
        """Negative lifetime must be rejected."""
        with pytest.raises(ValidationError):
            SubscribeInput(
                tool_id="some_tool",
                params={},
                lifetime_seconds=-1,
            )

    def test_lifetime_seconds_one_is_valid(self):
        """Minimum valid lifetime = 1s."""
        inp = SubscribeInput(
            tool_id="some_tool",
            params={},
            lifetime_seconds=1,
        )
        assert inp.lifetime_seconds == 1

    def test_lifetime_seconds_typical_values(self):
        """Common test values (60s, 3600s, 86400s) are valid."""
        for seconds in [60, 3600, 86400]:
            inp = SubscribeInput(
                tool_id="some_tool",
                params={},
                lifetime_seconds=seconds,
            )
            assert inp.lifetime_seconds == seconds

    def test_model_is_frozen(self):
        """SubscribeInput must be immutable (frozen=True per data-model.md)."""
        inp = SubscribeInput(
            tool_id="some_tool",
            params={},
            lifetime_seconds=60,
        )
        with pytest.raises((TypeError, ValidationError)):
            inp.lifetime_seconds = 120  # type: ignore[misc]

    def test_model_forbids_extra_fields(self):
        """extra='forbid' — no extra fields allowed (blocks webhook injection)."""
        with pytest.raises(ValidationError):
            SubscribeInput(
                tool_id="some_tool",
                params={},
                lifetime_seconds=60,
                webhook_url="https://evil.example.com/hook",  # FR-013 defense
            )
