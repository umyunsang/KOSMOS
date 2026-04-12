# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import time
from collections import deque


class RateLimiter:
    """Sliding-window rate limiter for per-tool call throttling.

    Uses a deque of call timestamps. On each check/record, expired
    timestamps (older than window_seconds) are pruned.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        """Initialize rate limiter.

        Args:
            limit: Maximum calls allowed within the window. Must be > 0.
            window_seconds: Size of the sliding window in seconds.
        """
        self._limit = limit
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque()

    def _prune(self) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = time.monotonic() - self._window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def check(self) -> bool:
        """Can a call be made right now?

        Returns True if the current number of calls in the window is
        less than the limit.
        """
        self._prune()
        return len(self._timestamps) < self._limit

    def record(self) -> None:
        """Record a call timestamp."""
        self._timestamps.append(time.monotonic())

    @property
    def remaining(self) -> int:
        """Remaining calls allowed in the current window."""
        self._prune()
        return max(0, self._limit - len(self._timestamps))

    def reset(self) -> None:
        """Clear all timestamps."""
        self._timestamps.clear()

    @property
    def limit(self) -> int:
        """The configured rate limit."""
        return self._limit

    @property
    def window_seconds(self) -> float:
        """The configured window size."""
        return self._window_seconds
