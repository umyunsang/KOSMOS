# SPDX-License-Identifier: Apache-2.0
"""Circuit breaker pattern for tool adapter protection.

Implements the standard three-state circuit breaker:
CLOSED → (failure threshold) → OPEN → (recovery timeout) → HALF_OPEN
HALF_OPEN → (success) → CLOSED
HALF_OPEN → (failure) → OPEN
"""

from __future__ import annotations

import logging
import time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    """State of a circuit breaker."""

    CLOSED = "closed"
    """Normal operation; all requests pass through."""

    OPEN = "open"
    """Circuit tripped; all requests are blocked immediately."""

    HALF_OPEN = "half_open"
    """Probe mode; a limited number of requests are allowed through."""


class CircuitBreakerConfig(BaseModel):
    """Configuration for a single circuit breaker instance."""

    model_config = ConfigDict(frozen=True)

    failure_threshold: int = 5
    """Number of consecutive failures before the circuit opens."""

    recovery_timeout: float = 30.0
    """Seconds after opening before transitioning to HALF_OPEN."""

    half_open_max_calls: int = 1
    """Maximum probe calls allowed while in HALF_OPEN state."""


class CircuitBreaker:
    """Stateful circuit breaker for a single tool.

    Thread/coroutine safety: Python's GIL makes simple attribute updates atomic
    for CPython, but callers running multiple coroutines concurrently should be
    aware that ``allow_request`` / ``record_*`` are not atomic as a pair.
    """

    def __init__(self, tool_id: str, config: CircuitBreakerConfig | None = None) -> None:
        self._tool_id = tool_id
        self._config = config or CircuitBreakerConfig()
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: float = 0.0
        self._half_open_calls: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition OPEN→HALF_OPEN on read)."""
        self._check_recovery()
        return self._state

    def allow_request(self) -> bool:
        """Return ``True`` if a new request should be allowed through.

        Side-effects:
        - Transitions OPEN → HALF_OPEN when recovery_timeout has elapsed.
        - Increments the half-open call counter.
        """
        self._check_recovery()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            logger.debug("Circuit OPEN for tool %s — request blocked", self._tool_id)
            return False

        # HALF_OPEN
        if self._half_open_calls < self._config.half_open_max_calls:
            self._half_open_calls += 1
            logger.debug(
                "Circuit HALF_OPEN for tool %s — probe call %d/%d",
                self._tool_id,
                self._half_open_calls,
                self._config.half_open_max_calls,
            )
            return True

        logger.debug(
            "Circuit HALF_OPEN for tool %s — max probe calls reached, blocking",
            self._tool_id,
        )
        return False

    def record_success(self) -> None:
        """Record a successful call; resets failure count and closes circuit if HALF_OPEN."""
        if self._state == CircuitState.HALF_OPEN:
            logger.info("Circuit HALF_OPEN → CLOSED for tool %s (probe succeeded)", self._tool_id)
            self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call; opens the circuit when the threshold is reached."""
        if self._state == CircuitState.HALF_OPEN:
            logger.warning("Circuit HALF_OPEN → OPEN for tool %s (probe failed)", self._tool_id)
            self._transition_to_open()
            return

        if self._state == CircuitState.OPEN:
            return  # already open

        # CLOSED
        self._failure_count += 1
        if self._failure_count >= self._config.failure_threshold:
            logger.warning(
                "Circuit CLOSED → OPEN for tool %s after %d failures",
                self._tool_id,
                self._failure_count,
            )
            self._transition_to_open()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_recovery(self) -> None:
        """Transition OPEN → HALF_OPEN if the recovery timeout has elapsed."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._config.recovery_timeout:
                logger.info(
                    "Circuit OPEN → HALF_OPEN for tool %s after %.1fs",
                    self._tool_id,
                    elapsed,
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

    def _transition_to_open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._failure_count = 0
        self._half_open_calls = 0

    def _transition_to_closed(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0


class CircuitBreakerRegistry:
    """Lazy per-tool CircuitBreaker registry.

    Creates a new ``CircuitBreaker`` on first access for each *tool_id*.
    The default config is used unless a specific config is provided at
    construction time.
    """

    def __init__(self, default_config: CircuitBreakerConfig | None = None) -> None:
        self._default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, tool_id: str) -> CircuitBreaker:
        """Return the ``CircuitBreaker`` for *tool_id*, creating it if needed."""
        if tool_id not in self._breakers:
            self._breakers[tool_id] = CircuitBreaker(tool_id, self._default_config)
            logger.debug("Created circuit breaker for tool %s", tool_id)
        return self._breakers[tool_id]
