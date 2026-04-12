# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the RateLimiter sliding-window implementation."""

from __future__ import annotations

import time

from kosmos.tools.rate_limiter import RateLimiter


def test_check_within_limit() -> None:
    """A brand-new limiter with limit=5 should allow calls immediately."""
    limiter = RateLimiter(limit=5)
    assert limiter.check() is True


def test_check_at_limit() -> None:
    """After recording limit calls, check() must return False."""
    limiter = RateLimiter(limit=5)
    for _ in range(5):
        limiter.record()
    assert limiter.check() is False


def test_remaining_count() -> None:
    """After 3 calls with limit=5, remaining should be 2."""
    limiter = RateLimiter(limit=5)
    for _ in range(3):
        limiter.record()
    assert limiter.remaining == 2


def test_remaining_at_limit() -> None:
    """After recording exactly limit calls, remaining should be 0."""
    limiter = RateLimiter(limit=5)
    for _ in range(5):
        limiter.record()
    assert limiter.remaining == 0


def test_record_and_check() -> None:
    """check() should stay True until the limit is reached, then flip to False."""
    limiter = RateLimiter(limit=3)
    for _ in range(2):
        assert limiter.check() is True
        limiter.record()
    assert limiter.check() is True
    limiter.record()
    assert limiter.check() is False


def test_manual_reset() -> None:
    """After filling the limit and calling reset(), check() returns True and remaining == limit."""
    limiter = RateLimiter(limit=4)
    for _ in range(4):
        limiter.record()
    assert limiter.check() is False
    limiter.reset()
    assert limiter.check() is True
    assert limiter.remaining == 4


def test_window_expiry() -> None:
    """Calls recorded before the window expires should no longer count afterward."""
    limiter = RateLimiter(limit=2, window_seconds=0.05)
    limiter.record()
    limiter.record()
    assert not limiter.check()
    time.sleep(0.1)  # Wait past the window
    assert limiter.check()
    assert limiter.remaining == 2  # All old calls expired


def test_limit_property() -> None:
    """The limit property must reflect the value passed to __init__."""
    limiter = RateLimiter(limit=7)
    assert limiter.limit == 7


def test_window_seconds_property() -> None:
    """The window_seconds property must reflect the value passed to __init__."""
    limiter = RateLimiter(limit=1, window_seconds=30.0)
    assert limiter.window_seconds == 30.0


def test_independent_limiters() -> None:
    """Two separate RateLimiter instances must not share state."""
    limiter_a = RateLimiter(limit=3)
    limiter_b = RateLimiter(limit=3)
    for _ in range(3):
        limiter_a.record()
    assert limiter_a.check() is False
    assert limiter_b.check() is True
