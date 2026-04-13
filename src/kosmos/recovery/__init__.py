# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Layer 6 — Error Recovery package.

Public API for the error-recovery sub-system that wraps data.go.kr tool
adapter calls with retry, circuit-breaker, and cache-fallback logic.
"""

from kosmos.recovery.auth_refresh import attempt_auth_refresh, get_credential
from kosmos.recovery.cache import CacheEntry, ResponseCache
from kosmos.recovery.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)
from kosmos.recovery.classifier import (
    ClassifiedError,
    DataGoKrErrorClassifier,
    DataGoKrErrorCode,
    ErrorClass,
)
from kosmos.recovery.executor import ErrorContext, RecoveryExecutor, RecoveryResult
from kosmos.recovery.messages import build_degradation_message
from kosmos.recovery.persistent_cache import PersistentCacheEntry, PersistentResponseCache
from kosmos.recovery.policies import RetryPolicy, RetryPolicyRegistry
from kosmos.recovery.retry import ToolRetryPolicy, retry_tool_call

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
