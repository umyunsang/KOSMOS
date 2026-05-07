# SPDX-License-Identifier: Apache-2.0
"""KOSAX Layer 6 — Error Recovery package.

Public API for the error-recovery sub-system that wraps data.go.kr tool
adapter calls with retry, circuit-breaker, and cache-fallback logic.
"""

from kosax.recovery.auth_refresh import attempt_auth_refresh, get_credential
from kosax.recovery.cache import CacheEntry, ResponseCache
from kosax.recovery.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)
from kosax.recovery.classifier import (
    ClassifiedError,
    DataGoKrErrorClassifier,
    DataGoKrErrorCode,
    ErrorClass,
)
from kosax.recovery.executor import ErrorContext, RecoveryExecutor, RecoveryResult
from kosax.recovery.messages import build_degradation_message
from kosax.recovery.persistent_cache import PersistentCacheEntry, PersistentResponseCache
from kosax.recovery.policies import RetryPolicy, RetryPolicyRegistry
from kosax.recovery.retry import ToolRetryPolicy, retry_tool_call

__all__ = [
    # auth_refresh
    "attempt_auth_refresh",
    "get_credential",
    # cache
    "CacheEntry",
    "ResponseCache",
    # circuit_breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerRegistry",
    "CircuitState",
    # classifier
    "ClassifiedError",
    "DataGoKrErrorClassifier",
    "DataGoKrErrorCode",
    "ErrorClass",
    # executor
    "ErrorContext",
    "RecoveryExecutor",
    "RecoveryResult",
    # messages
    "build_degradation_message",
    # persistent_cache
    "PersistentCacheEntry",
    "PersistentResponseCache",
    # policies
    "RetryPolicy",
    "RetryPolicyRegistry",
    # retry
    "ToolRetryPolicy",
    "retry_tool_call",
]
