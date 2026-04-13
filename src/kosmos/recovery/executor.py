# SPDX-License-Identifier: Apache-2.0
"""RecoveryExecutor — orchestrates retry, circuit breaker, and cache fallback.

This module is the single integration point for Layer 6 error recovery.
It wraps a tool adapter call with the full recovery pipeline:

    1. Cache lookup (if hit → return cached data, no side-effects)
    2. Circuit breaker check (if open → degradation message immediately)
    3. Retry loop (exponential back-off with full jitter)
    4. Cache store on success
    5. Cache fallback on final failure (if stale data available)
    6. Degradation message as last resort

The ``RecoveryExecutor`` NEVER raises — all error paths are captured in the
returned ``RecoveryResult``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kosmos.recovery.cache import ResponseCache
from kosmos.recovery.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)
from kosmos.recovery.classifier import (
    ClassifiedError,
    DataGoKrErrorClassifier,
    ErrorClass,
)
from kosmos.recovery.messages import build_degradation_message
from kosmos.recovery.retry import ToolRetryPolicy, retry_tool_call
from kosmos.tools.models import GovAPITool, ToolResult
from kosmos.tools.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AdapterFn = Callable[..., Awaitable[dict[str, object]]]


# ---------------------------------------------------------------------------
# Context models
# ---------------------------------------------------------------------------


class ErrorContext(BaseModel):
    """Diagnostic information about the error recovery attempt."""

    model_config = ConfigDict(frozen=True)

    attempt_count: int
    """Total number of adapter call attempts made."""

    elapsed_seconds: float
    """Wall-clock time spent in the recovery pipeline."""

    error_class: ErrorClass | None
    """Classified error class from the last failure, or ``None`` on success."""

    is_cached_fallback: bool
    """``True`` if the result data came from an expired/stale cache entry."""

    circuit_state: CircuitState
    """State of the circuit breaker at the time of the result."""

    tool_id: str
    """Identifier of the tool that was called."""


class RecoveryResult(BaseModel):
    """Outcome of a ``RecoveryExecutor.execute()`` call."""

    model_config = ConfigDict(frozen=True)

    tool_result: ToolResult
    """The final ``ToolResult`` (may represent a degraded / cached response)."""

    error_context: ErrorContext | None = None
    """Recovery diagnostics; ``None`` on clean success."""


# ---------------------------------------------------------------------------
# RecoveryExecutor
# ---------------------------------------------------------------------------


class RecoveryExecutor:
    """Orchestrate retry, circuit breaker, and cache fallback for tool calls.

    All state (circuit breakers, cache) is held per ``RecoveryExecutor``
    instance.  Typically one instance is shared across the application and
    injected into ``ToolExecutor``.
    """

    def __init__(
        self,
        retry_policy: ToolRetryPolicy | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
        max_cache_entries: int = 256,
    ) -> None:
        self._policy = retry_policy or ToolRetryPolicy()
        self._classifier = DataGoKrErrorClassifier()
        self._registry = CircuitBreakerRegistry(default_config=circuit_config)
        self._cache = ResponseCache(max_entries=max_cache_entries)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def execute(  # noqa: C901
        self,
        tool: GovAPITool,
        adapter: AdapterFn,
        validated_input: object,
        *,
        is_foreground: bool = True,
        rate_limiter: RateLimiter | None = None,
    ) -> RecoveryResult:
        """Execute *adapter* with full error-recovery orchestration.

        Pipeline:
        1. Cache lookup → return cached data if fresh (no side-effects).
        2. Circuit breaker check → immediate degradation if OPEN.
        3. Record rate-limit slot (only before the actual adapter call).
        4. Retry loop with exponential back-off.
        5. On success: update circuit breaker + cache store.
        6. On exhaustion: try stale cache fallback.
        7. Last resort: return degradation message as a failed ToolResult.

        Args:
            tool: The GovAPITool being called (used for cache TTL and messages).
            adapter: Async callable that performs the actual API call.
            validated_input: Pre-validated Pydantic model instance to pass to adapter.
            is_foreground: Whether this is a user-facing call (affects retry cap).
            rate_limiter: Optional rate limiter; ``record()`` is called only
                when the adapter is actually invoked (not on cache hit or
                circuit-open short-circuit).

        Returns:
            A ``RecoveryResult`` that never represents an un-caught exception.
        """
        start = time.monotonic()
        tool_id = tool.id
        breaker = self._registry.get(tool_id)

        # --- 1. Cache lookup (before circuit breaker to avoid wasting a
        #     HALF_OPEN probe allowance on a cache hit) ---
        # _model_to_dict returns None when serialisation fails; in that case
        # we skip all caching to avoid degenerate cache keys.
        input_dict = self._model_to_dict(validated_input)
        args_hash: str | None = None
        if input_dict is not None and tool.cache_ttl_seconds > 0:
            args_hash = self._cache.compute_hash(input_dict)
            cached = self._cache.get(tool_id, args_hash)
            if cached is not None:
                elapsed = time.monotonic() - start
                logger.debug("Cache hit for tool %s", tool_id)
                return RecoveryResult(
                    tool_result=ToolResult(
                        tool_id=tool_id,
                        success=True,
                        data=cached,
                    ),
                    error_context=None,
                )

        # --- 2. Circuit breaker check ---
        if not breaker.allow_request():
            elapsed = time.monotonic() - start
            circuit_open_error = ClassifiedError(
                error_class=ErrorClass.APP_ERROR,
                is_retryable=False,
                raw_code=None,
                raw_message="Circuit breaker is OPEN",
                source="circuit_open",
            )
            degradation = build_degradation_message(tool, circuit_open_error)
            logger.warning("Circuit breaker OPEN for tool %s — returning degradation", tool_id)
            return RecoveryResult(
                tool_result=ToolResult(
                    tool_id=tool_id,
                    success=False,
                    error=degradation,
                    error_type="circuit_open",
                ),
                error_context=ErrorContext(
                    attempt_count=0,
                    elapsed_seconds=elapsed,
                    error_class=ErrorClass.APP_ERROR,
                    is_cached_fallback=False,
                    circuit_state=breaker.state,
                    tool_id=tool_id,
                ),
            )

        # --- 3. Wrap adapter with per-invocation rate-limit recording ---
        # Each adapter call (including retries) records a rate-limit slot so
        # the sliding window accurately reflects actual API call volume.
        if rate_limiter is not None:

            async def _rate_limited_adapter(args: object) -> dict[str, object]:
                rate_limiter.record()
                return await adapter(args)

            effective_adapter: AdapterFn = _rate_limited_adapter
        else:
            effective_adapter = adapter

        # --- 4. Retry loop ---
        result_dict, last_error, attempt_count = await retry_tool_call(
            effective_adapter,
            validated_input,
            self._classifier,
            self._policy,
            is_foreground=is_foreground,
        )

        elapsed = time.monotonic() - start

        # --- 5. Success path ---
        if result_dict is not None:
            breaker.record_success()
            # Only cache data that passes output_schema validation so that
            # invalid adapter responses are never served from the cache.
            # args_hash is None when input serialisation failed — skip caching.
            if args_hash is not None and tool.cache_ttl_seconds > 0:
                try:
                    tool.output_schema.model_validate(result_dict)
                    self._cache.put(tool_id, args_hash, result_dict, tool.cache_ttl_seconds)
                except Exception:
                    logger.debug(
                        "Skipping cache store for tool %s: output_schema validation failed",
                        tool_id,
                        exc_info=True,
                    )
            return RecoveryResult(
                tool_result=ToolResult(
                    tool_id=tool_id,
                    success=True,
                    data=result_dict,
                ),
                error_context=None,
            )

        # --- Failure: record to circuit breaker only for transient/retryable
        #     errors.  Client errors (INVALID_REQUEST, AUTH_FAILURE, etc.) are
        #     the caller's fault and should not count against service health. ---
        if last_error is not None and last_error.is_retryable:
            breaker.record_failure()

        # --- 6. Stale cache fallback (only if cache_ttl_seconds > 0) ---
        if args_hash is not None and tool.cache_ttl_seconds > 0:
            stale = self._get_stale_cache(tool_id, args_hash)
            if stale is not None:
                logger.warning(
                    "Returning stale cache fallback for tool %s after %d attempt(s)",
                    tool_id,
                    attempt_count,
                )
                return RecoveryResult(
                    tool_result=ToolResult(
                        tool_id=tool_id,
                        success=True,
                        data=stale,
                    ),
                    error_context=ErrorContext(
                        attempt_count=attempt_count,
                        elapsed_seconds=elapsed,
                        error_class=last_error.error_class if last_error else None,
                        is_cached_fallback=True,
                        circuit_state=breaker.state,
                        tool_id=tool_id,
                    ),
                )

        # --- 7. Degradation message ---
        assert last_error is not None  # retry_tool_call guarantees this when result is None
        degradation = build_degradation_message(tool, last_error)
        error_type = self._error_class_to_error_type(last_error.error_class)
        logger.error(
            "Tool %s recovery exhausted after %d attempt(s): class=%s",
            tool_id,
            attempt_count,
            last_error.error_class,
        )
        return RecoveryResult(
            tool_result=ToolResult(
                tool_id=tool_id,
                success=False,
                error=degradation,
                error_type=error_type,
            ),
            error_context=ErrorContext(
                attempt_count=attempt_count,
                elapsed_seconds=elapsed,
                error_class=last_error.error_class,
                is_cached_fallback=False,
                circuit_state=breaker.state,
                tool_id=tool_id,
            ),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _model_to_dict(self, model: object) -> dict[str, object] | None:
        """Convert a Pydantic model to a plain dict for cache key computation.

        Uses ``mode="json"`` to ensure all values (Enums, datetimes, etc.)
        are JSON-serialisable primitives.  Returns ``None`` on failure so the
        caller can skip caching rather than produce a degenerate cache key.
        """
        from pydantic import BaseModel as _BaseModel  # local import to avoid circular

        try:
            if isinstance(model, _BaseModel):
                return dict(model.model_dump(mode="json"))
        except Exception:
            logger.debug("model_dump(mode='json') failed; caching will be skipped")
            return None
        if isinstance(model, dict):
            return model
        return None

    def _get_stale_cache(self, tool_id: str, args_hash: str) -> dict[str, object] | None:
        """Look up a stale (possibly expired) cache entry via the public API."""
        return self._cache.get_stale(tool_id, args_hash)

    @staticmethod
    def _error_class_to_error_type(
        error_class: ErrorClass,
    ) -> Literal[
        "validation",
        "rate_limit",
        "not_found",
        "execution",
        "schema_mismatch",
        "permission_denied",
        "timeout",
        "circuit_open",
        "api_error",
        "auth_expired",
    ]:
        """Map ErrorClass to ToolResult.error_type literal string."""
        mapping: dict[
            ErrorClass,
            Literal[
                "validation",
                "rate_limit",
                "not_found",
                "execution",
                "timeout",
                "api_error",
                "auth_expired",
            ],
        ] = {
            ErrorClass.TRANSIENT: "api_error",
            ErrorClass.RATE_LIMIT: "rate_limit",
            ErrorClass.AUTH_FAILURE: "auth_expired",
            ErrorClass.DATA_MISSING: "not_found",
            ErrorClass.INVALID_REQUEST: "validation",
            ErrorClass.TIMEOUT: "timeout",
            ErrorClass.DEPRECATED: "not_found",
            ErrorClass.APP_ERROR: "execution",
            ErrorClass.UNKNOWN: "api_error",
        }
        return mapping.get(error_class, "execution")
