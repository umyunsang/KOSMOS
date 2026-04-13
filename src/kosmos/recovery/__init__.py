# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Layer 6 — Error Recovery package.

Public API for the error-recovery sub-system that wraps data.go.kr tool
adapter calls with retry, circuit-breaker, and cache-fallback logic.
"""

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
from kosmos.recovery.retry import ToolRetryPolicy, retry_tool_call

__all__ = [
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
    # retry
    "ToolRetryPolicy",
    "retry_tool_call",
]
