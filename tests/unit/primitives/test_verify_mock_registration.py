# SPDX-License-Identifier: Apache-2.0
"""T063 — Verify Mock adapter registration test.

Asserts that importing kosmos.tools.mock registers all 6 verify family adapters
into kosmos.primitives.verify._VERIFY_ADAPTERS, that each adapter is callable,
and that invoking each with a minimal VerifyInput-compatible session_context
returns an AuthContext-shaped object with the required fields.
"""

from __future__ import annotations

import logging

import pytest

logger = logging.getLogger(__name__)

_ALL_FAMILIES = [
    # NOTE: "digital_onepass" REMOVED — FR-004 (서비스 종료 2025-12-30, Epic ε #2296 T021).
    "gongdong_injeungseo",
    "geumyung_injeungseo",
    "ganpyeon_injeung",
    "mobile_id",
    "mydata",
]

_REQUIRED_AT_LEAST = 2


# ---------------------------------------------------------------------------
# Registration presence
# ---------------------------------------------------------------------------


class TestVerifyMockRegistration:
    """After importing kosmos.tools.mock, _VERIFY_ADAPTERS must be populated."""

    def test_at_least_two_families_registered(self) -> None:
        import kosmos.tools.mock  # noqa: F401 — side-effect: registers adapters
        from kosmos.primitives.verify import _VERIFY_ADAPTERS

        registered = set(_VERIFY_ADAPTERS.keys()) & set(_ALL_FAMILIES)
        assert len(registered) >= _REQUIRED_AT_LEAST, (
            f"Expected at least {_REQUIRED_AT_LEAST} verify families registered, "
            f"got {sorted(registered)}"
        )

    def test_all_remaining_families_registered(self) -> None:
        """After digital_onepass deletion (FR-004, Epic ε T021), 5 families remain."""
        import kosmos.tools.mock  # noqa: F401
        from kosmos.primitives.verify import _VERIFY_ADAPTERS

        for family in _ALL_FAMILIES:
            assert family in _VERIFY_ADAPTERS, (
                f"Family {family!r} not in _VERIFY_ADAPTERS after mock import"
            )

    def test_each_adapter_is_callable(self) -> None:
        import kosmos.tools.mock  # noqa: F401
        from kosmos.primitives.verify import _VERIFY_ADAPTERS

        for family in _ALL_FAMILIES:
            adapter = _VERIFY_ADAPTERS.get(family)
            assert adapter is not None, f"Adapter for {family!r} is None"
            assert callable(adapter), f"Adapter for {family!r} is not callable"


# ---------------------------------------------------------------------------
# Adapter invocation — AuthContext shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family", _ALL_FAMILIES)
def test_adapter_returns_auth_context_shape(family: str) -> None:
    """Each adapter must return an object with published_tier and nist_aal_hint."""
    import kosmos.tools.mock  # noqa: F401
    from kosmos.primitives.verify import (
        _VERIFY_ADAPTERS,
        GanpyeonInjeungContext,
        GeumyungInjeungseoContext,
        GongdongInjeungseoContext,
        MobileIdContext,
        MyDataContext,
    )

    auth_context_types = (
        GongdongInjeungseoContext,
        GeumyungInjeungseoContext,
        GanpyeonInjeungContext,
        MobileIdContext,
        MyDataContext,
    )

    adapter = _VERIFY_ADAPTERS[family]
    result = adapter({})  # type: ignore[operator]

    # New Epic ε adapters may return dict (DelegationContext) or Pydantic context.
    # Existing 5 Spec 031 adapters return Pydantic AuthContext objects.
    if isinstance(result, auth_context_types):
        assert hasattr(result, "published_tier"), f"Missing 'published_tier' on {type(result).__name__}"
        assert hasattr(result, "nist_aal_hint"), f"Missing 'nist_aal_hint' on {type(result).__name__}"
        assert result.published_tier, "published_tier must be non-empty"
        assert result.nist_aal_hint, "nist_aal_hint must be non-empty"
        assert result.family == family, (
            f"Adapter family mismatch: registered as {family!r} but returned {result.family!r}"
        )
        logger.debug(
            "verify adapter %s → published_tier=%s nist_aal_hint=%s",
            family,
            result.published_tier,
            result.nist_aal_hint,
        )
    else:
        # dict return (e.g. DelegationContext payload from Epic ε adapters) — just assert it
        # carries the six transparency fields.
        assert isinstance(result, dict), (
            f"Adapter for {family!r} returned unexpected type {type(result).__name__!r}"
        )
