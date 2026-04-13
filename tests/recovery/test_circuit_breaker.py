# SPDX-License-Identifier: Apache-2.0
"""Tests for the CircuitBreaker and CircuitBreakerRegistry."""

from __future__ import annotations

import time

import pytest

from kosmos.recovery.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)


@pytest.fixture()
def config() -> CircuitBreakerConfig:
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=0.05,  # 50 ms for fast tests
        half_open_max_calls=1,
    )


@pytest.fixture()
def cb(config: CircuitBreakerConfig) -> CircuitBreaker:
    return CircuitBreaker("test_tool", config)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_starts_closed(self, cb: CircuitBreaker) -> None:
        assert cb.state == CircuitState.CLOSED

    def test_allows_requests_when_closed(self, cb: CircuitBreaker) -> None:
        assert cb.allow_request() is True


# ---------------------------------------------------------------------------
# CLOSED → OPEN transition
# ---------------------------------------------------------------------------


class TestClosedToOpen:
    def test_opens_after_failure_threshold(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_after_open(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        assert cb.allow_request() is False

    def test_does_not_open_before_threshold(self, cb: CircuitBreaker) -> None:
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_success_resets_failure_count(self, cb: CircuitBreaker) -> None:
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # resets to 0
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED  # only 2 failures since reset


# ---------------------------------------------------------------------------
# OPEN → HALF_OPEN transition
# ---------------------------------------------------------------------------


class TestOpenToHalfOpen:
    def test_transitions_to_half_open_after_timeout(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.06)  # exceed 50 ms recovery timeout
        assert cb.state == CircuitState.HALF_OPEN

    def test_allows_probe_call_in_half_open(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        assert cb.allow_request() is True

    def test_blocks_extra_calls_in_half_open(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()  # consumes the one allowed probe call
        assert cb.allow_request() is False


# ---------------------------------------------------------------------------
# HALF_OPEN → CLOSED on success
# ---------------------------------------------------------------------------


class TestHalfOpenToClosedOnSuccess:
    def test_closes_on_probe_success(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_allows_requests_after_close(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()
        cb.record_success()
        assert cb.allow_request() is True


# ---------------------------------------------------------------------------
# HALF_OPEN → OPEN on failure
# ---------------------------------------------------------------------------


class TestHalfOpenToOpenOnFailure:
    def test_reopens_on_probe_failure(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_immediately_after_reopen(self, cb: CircuitBreaker) -> None:
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()
        cb.record_failure()
        assert cb.allow_request() is False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestCircuitBreakerRegistry:
    def test_lazy_creation(self) -> None:
        registry = CircuitBreakerRegistry()
        cb = registry.get("tool_a")
        assert isinstance(cb, CircuitBreaker)
        assert cb.state == CircuitState.CLOSED

    def test_same_instance_on_second_call(self) -> None:
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("tool_a")
        cb2 = registry.get("tool_a")
        assert cb1 is cb2

    def test_separate_instances_for_different_tools(self) -> None:
        registry = CircuitBreakerRegistry()
        cb1 = registry.get("tool_a")
        cb2 = registry.get("tool_b")
        assert cb1 is not cb2

    def test_default_config_applied(self) -> None:
        config = CircuitBreakerConfig(failure_threshold=7)
        registry = CircuitBreakerRegistry(default_config=config)
        cb = registry.get("tool_x")
        assert cb._config.failure_threshold == 7  # noqa: SLF001


# ---------------------------------------------------------------------------
# Concurrent HALF_OPEN: second probe is blocked
# ---------------------------------------------------------------------------


class TestConcurrentHalfOpen:
    def test_second_probe_blocked_in_half_open(self, cb: CircuitBreaker) -> None:
        """With half_open_max_calls=1, only one probe is allowed at a time."""
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.06)
        # First call transitions to HALF_OPEN and allows the probe
        first = cb.allow_request()
        second = cb.allow_request()
        assert first is True
        assert second is False
