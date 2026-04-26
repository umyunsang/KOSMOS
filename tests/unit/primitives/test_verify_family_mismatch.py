# SPDX-License-Identifier: Apache-2.0
"""T065 — Verify primitive family-mismatch dispatcher test.

Asserts that:
- (happy path) a known family_hint routes to its adapter and returns a valid
  AuthContext variant.
- (mismatch path) an unregistered family_hint causes the dispatcher to return
  a VerifyMismatchError without raising an exception.
"""

from __future__ import annotations

import logging

import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_gongdong_injeungseo() -> None:
    """Calling verify() with a registered family returns a valid AuthContext."""
    import kosmos.tools.mock  # noqa: F401 — registers all 6 adapters

    from kosmos.primitives.verify import GongdongInjeungseoContext, verify

    result = await verify("gongdong_injeungseo", {})

    assert isinstance(result, GongdongInjeungseoContext), (
        f"Expected GongdongInjeungseoContext, got {type(result).__name__!r}"
    )
    assert result.family == "gongdong_injeungseo"
    assert result.published_tier == "gongdong_injeungseo_personal_aal3"
    assert result.nist_aal_hint == "AAL3"
    logger.debug("happy path result: %s", result)


# ---------------------------------------------------------------------------
# Mismatch path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unregistered_family_returns_mismatch_error() -> None:
    """verify() with an unknown family must return VerifyMismatchError, not raise."""
    import kosmos.tools.mock  # noqa: F401

    from kosmos.primitives.verify import VerifyMismatchError, verify

    result = await verify("nonexistent_cert_family", {})

    assert isinstance(result, VerifyMismatchError), (
        f"Expected VerifyMismatchError, got {type(result).__name__!r}"
    )
    assert result.family == "mismatch_error"
    assert result.reason == "family_mismatch"
    assert result.expected_family == "nonexistent_cert_family"
    assert result.observed_family == "<no_adapter>"
    logger.debug("mismatch result: %s", result)
