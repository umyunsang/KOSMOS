# SPDX-License-Identifier: Apache-2.0
"""Tests for per-adapter RetryPolicy and RetryPolicyRegistry."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.recovery.policies import RetryPolicy, RetryPolicyRegistry

# ---------------------------------------------------------------------------
# RetryPolicy defaults
# ---------------------------------------------------------------------------


def test_retry_policy_defaults() -> None:
    """Default RetryPolicy has sane values."""
    policy = RetryPolicy()
    assert policy.max_retries == 3
    assert policy.base_delay == 1.0
    assert policy.max_delay == 30.0
    assert policy.exponential_base == 2.0
    assert 429 in policy.retryable_status_codes
    assert 503 in policy.retryable_status_codes
    assert policy.retry_on_timeout is True


def test_retry_policy_is_frozen() -> None:
    """RetryPolicy instances are immutable."""
    policy = RetryPolicy()
    with pytest.raises(ValidationError):
        policy.max_retries = 99  # type: ignore[misc]


def test_retry_policy_custom_values() -> None:
    """Custom RetryPolicy stores provided values."""
    policy = RetryPolicy(
        max_retries=10,
        base_delay=0.5,
        max_delay=60.0,
        exponential_base=3.0,
        retryable_status_codes=frozenset({429, 503}),
        retry_on_timeout=False,
    )
    assert policy.max_retries == 10
    assert policy.base_delay == 0.5
    assert policy.max_delay == 60.0
    assert policy.exponential_base == 3.0
    assert policy.retryable_status_codes == frozenset({429, 503})
    assert policy.retry_on_timeout is False


# ---------------------------------------------------------------------------
# RetryPolicyRegistry — default behaviour
# ---------------------------------------------------------------------------


def test_registry_returns_default_for_unknown_tool() -> None:
    """Registry returns the default policy for unregistered tool_id."""
    default = RetryPolicy(max_retries=5)
    registry = RetryPolicyRegistry(default=default)
    result = registry.get("unknown_tool")
    assert result is default


def test_registry_default_when_no_default_provided() -> None:
    """Registry creates a RetryPolicy() default when none is supplied."""
    registry = RetryPolicyRegistry()
    result = registry.get("some_tool")
    assert isinstance(result, RetryPolicy)
    assert result.max_retries == 3  # RetryPolicy default


def test_registry_default_property() -> None:
    """Registry.default returns the configured default policy."""
    default = RetryPolicy(max_retries=7)
    registry = RetryPolicyRegistry(default=default)
    assert registry.default is default


# ---------------------------------------------------------------------------
# RetryPolicyRegistry — register and lookup
# ---------------------------------------------------------------------------


def test_registry_register_and_get() -> None:
    """Registered policy is returned for the correct tool_id."""
    registry = RetryPolicyRegistry()
    custom = RetryPolicy(max_retries=1, base_delay=0.0)
    registry.register("my_tool", custom)
    assert registry.get("my_tool") is custom


def test_registry_per_adapter_isolation() -> None:
    """Policies for different tool_ids do not interfere."""
    registry = RetryPolicyRegistry()
    policy_a = RetryPolicy(max_retries=1)
    policy_b = RetryPolicy(max_retries=9)
    registry.register("tool_a", policy_a)
    registry.register("tool_b", policy_b)

    assert registry.get("tool_a") is policy_a
    assert registry.get("tool_b") is policy_b
    # Third tool falls back to default
    assert registry.get("tool_c").max_retries == 3


def test_registry_overwrite_policy() -> None:
    """Re-registering a policy for the same tool_id overwrites the previous."""
    registry = RetryPolicyRegistry()
    first = RetryPolicy(max_retries=2)
    second = RetryPolicy(max_retries=8)
    registry.register("my_tool", first)
    registry.register("my_tool", second)
    assert registry.get("my_tool") is second


def test_registry_registered_tool_does_not_use_default() -> None:
    """Registered tool policy is independent of the registry default."""
    default = RetryPolicy(max_retries=5)
    custom = RetryPolicy(max_retries=1)
    registry = RetryPolicyRegistry(default=default)
    registry.register("specific_tool", custom)

    assert registry.get("specific_tool") is custom
    assert registry.get("other_tool") is default
