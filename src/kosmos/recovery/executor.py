# SPDX-License-Identifier: Apache-2.0
"""RecoveryExecutor — orchestrates retry, circuit breaker, and cache fallback.

This module is the single integration point for Layer 6 error recovery.
It wraps a tool adapter call with the full recovery pipeline:

    1. Cache lookup (if hit → return cached data, no side-effects)
    2. Circuit breaker check (if open → degradation message immediately)
    3. Retry loop (exponential back-off with full jitter)
    4. 401 auth-refresh attempt (once, before final failure)
    5. Cache store on success
    6. Cache fallback on final failure (if stale data available)
    7. Degradation message as last resort

The ``RecoveryExecutor`` NEVER raises — all error paths are captured in the
returned ``RecoveryResult``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from kosmos.recovery.auth_refresh import attempt_auth_refresh
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
from kosmos.recovery.policies import RetryPolicy, RetryPolicyRegistry
from kosmos.recovery.retry import ToolRetryPolicy, retry_tool_call
from kosmos.tools.models import GovAPITool, ToolResult
from kosmos.tools.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from kosmos.observability.event_logger import ObservabilityEventLogger
    from kosmos.observability.metrics import MetricsCollector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AdapterFn = Callable[..., Awaitable[dict[str, object]]]


class _RateLimitExhaustedInRetryError(Exception):
    """Raised inside the rate-limited adapter wrapper when a retry attempt
    would exceed the sliding-window quota.

    Classified as ``APP_ERROR`` / non-retryable by the error classifier,
    which causes the retry loop to stop immediately.
    """

    def __init__(self, tool_id: str) -> None:
        super().__init__(f"Rate limit exhausted during retry for tool {tool_id!r}")


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


def _policy_to_tool_retry_policy(policy: RetryPolicy) -> ToolRetryPolicy:
    """Convert a ``RetryPolicy`` to the ``ToolRetryPolicy`` used by the retry loop."""
    retryable_classes = frozenset({ErrorClass.TRANSIENT, ErrorClass.RATE_LIMIT, ErrorClass.TIMEOUT})
    return ToolRetryPolicy(
        max_retries=policy.max_retries,
        base_delay=policy.base_delay,
        multiplier=policy.exponential_base,
        max_delay=policy.max_delay,
        retryable_classes=retryable_classes,
    )


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
        policy_registry: RetryPolicyRegistry | None = None,
        metrics: MetricsCollector | None = None,
        event_logger: ObservabilityEventLogger | None = None,
    ) -> None:
        # Legacy single-policy is kept for backwards-compatibility.
        # When a policy_registry is supplied it takes precedence for
        # per-tool lookups; the legacy policy becomes the default in a
        # newly created registry when none is provided.
        if policy_registry is not None:
            self._policy_registry = policy_registry
        else:
            default_retry = RetryPolicy(
                max_retries=(retry_policy.max_retries if retry_policy else 3),
                base_delay=(retry_policy.base_delay if retry_policy else 1.0),
                max_delay=(retry_policy.max_delay if retry_policy else 30.0),
                exponential_base=(retry_policy.multiplier if retry_policy else 2.0),
            )
            self._policy_registry = RetryPolicyRegistry(default=default_retry)

        # Keep the legacy _policy attribute for backwards-compatibility with
        # existing code that accesses it directly.
        self._policy = retry_policy or ToolRetryPolicy()
        self._classifier = DataGoKrErrorClassifier()
        self._registry = CircuitBreakerRegistry(default_config=circuit_config)
        self._cache = ResponseCache(max_entries=max_cache_entries)
        self._metrics: MetricsCollector | None = metrics
        self._event_logger: ObservabilityEventLogger | None = event_logger

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
        4. Retry loop with exponential back-off (per-tool RetryPolicy).
        5. 401 handling: attempt auth refresh + one extra retry.
        6. On success: update circuit breaker + cache store.
        7. On exhaustion: try stale cache fallback.
        8. Last resort: return degradation message as a failed ToolResult.

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
        input_dict = self._model_to_dict(validated_input)
        args_hash: str | None = None
        if input_dict is not None and tool.cache_ttl_seconds > 0:
            args_hash = self._cache.compute_hash(input_dict)
            cached = self._cache.get(tool_id, args_hash)
            if cached is not None:
                logger.debug("Cache hit for tool %s", tool_id)
                self._record_metric("recovery.cache_hits", tool_id)
                return RecoveryResult(
                    tool_result=ToolResult(
                        tool_id=tool_id,
                        success=True,
                        data=cached,
                    ),
                    error_context=None,
                )
            self._record_metric("recovery.cache_misses", tool_id)

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
            self._record_metric("recovery.circuit_breaker_trips", tool_id)
            self._event_emit_circuit_break(tool_id, str(breaker.state))
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

        # --- 3. Wrap adapter with per-invocation rate-limit enforcement ---
        if rate_limiter is not None:

            async def _rate_limited_adapter(args: object) -> dict[str, object]:
                if not rate_limiter.check():
                    raise _RateLimitExhaustedInRetryError(tool_id)
                rate_limiter.record()
                return await adapter(args)

            effective_adapter: AdapterFn = _rate_limited_adapter
        else:
            effective_adapter = adapter

        # --- 4. Resolve per-tool retry policy ---
        per_tool_policy = self._policy_registry.get(tool_id)
        tool_retry_policy = _policy_to_tool_retry_policy(per_tool_policy)

        # --- 5. Retry loop ---
        result_dict, last_error, attempt_count = await retry_tool_call(
            effective_adapter,
            validated_input,
            self._classifier,
            tool_retry_policy,
            is_foreground=is_foreground,
        )

        # Record retry metric (attempt_count > 1 means at least one retry happened)
        if attempt_count > 1:
            self._record_metric("recovery.retry_count", tool_id, value=attempt_count - 1)
            self._event_emit_retry(
                tool_id,
                error_class=str(last_error.error_class) if last_error else "",
                success=result_dict is not None,
            )

        # --- 5b. 401 auth-refresh: one extra attempt after credential reload ---
        if (
            result_dict is None
            and last_error is not None
            and last_error.error_class == ErrorClass.AUTH_EXPIRED
        ):
            refreshed = await attempt_auth_refresh(tool_id)
            if refreshed:
                logger.info(
                    "Auth refresh succeeded for tool %s — retrying once",
                    tool_id,
                )
                try:
                    result_dict = await effective_adapter(validated_input)
                    last_error = None
                    attempt_count += 1
                except Exception as exc:  # noqa: BLE001
                    last_error = self._classifier.classify_exception(exc)
                    attempt_count += 1
                    logger.warning(
                        "Post-auth-refresh retry failed for tool %s: %s",
                        tool_id,
                        last_error.raw_message,
                    )
            else:
                logger.warning(
                    "Auth refresh failed for tool %s — no credentials available",
                    tool_id,
                )

        elapsed = time.monotonic() - start

        # Record duration metric
        self._observe_duration("recovery.tool_duration_ms", tool_id, elapsed * 1000)

        # --- 6. Success path ---
        if result_dict is not None:
            breaker.record_success()
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

        # --- Failure: record to circuit breaker for transient/retryable errors ---
        if last_error is not None and last_error.is_retryable:
            breaker.record_failure()

        # Record error metric
        if last_error is not None:
            self._record_error_metric(last_error.error_class, tool_id)

        # --- 7. Stale cache fallback ---
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

        # --- 8. Degradation message ---
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
    # Private metrics helpers (fail-safe: never raise)
    # ------------------------------------------------------------------

    def _record_metric(self, name: str, tool_id: str, value: int = 1) -> None:
        """Increment a counter metric; silently skip if no collector is set."""
        if self._metrics is None:
            return
        try:
            self._metrics.increment(name, value=value, labels={"tool_id": tool_id})
        except Exception:  # noqa: BLE001
            logger.debug("metrics.increment failed for %s", name, exc_info=True)

    def _observe_duration(self, name: str, tool_id: str, duration_ms: float) -> None:
        """Record a duration histogram observation."""
        if self._metrics is None:
            return
        try:
            self._metrics.observe(name, duration_ms, labels={"tool_id": tool_id})
        except Exception:  # noqa: BLE001
            logger.debug("metrics.observe failed for %s", name, exc_info=True)

    def _record_error_metric(self, error_class: ErrorClass, tool_id: str) -> None:
        """Increment the error count metric."""
        if self._metrics is None:
            return
        try:
            self._metrics.increment(
                "recovery.error_count",
                labels={"tool_id": tool_id, "error_class": str(error_class)},
            )
        except Exception:  # noqa: BLE001
            logger.debug("metrics.increment(error_count) failed", exc_info=True)

    def _event_emit_retry(self, tool_id: str, *, error_class: str, success: bool) -> None:
        """Emit a retry event; silently skip if no event_logger (AC-A7)."""
        if self._event_logger is None:
            return
        try:
            from kosmos.observability.events import ObservabilityEvent  # noqa: PLC0415

            self._event_logger.emit(
                ObservabilityEvent(
                    event_type="retry",
                    tool_id=tool_id,
                    success=success,
                    metadata={
                        "tool_id": tool_id,
                        "error_class": error_class,
                    },
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("RecoveryExecutor: event_logger.emit(retry) failed", exc_info=True)

    def _event_emit_circuit_break(self, tool_id: str, circuit_state: str) -> None:
        """Emit a circuit_break event; silently skip if no event_logger (AC-A7)."""
        if self._event_logger is None:
            return
        try:
            from kosmos.observability.events import ObservabilityEvent  # noqa: PLC0415

            self._event_logger.emit(
                ObservabilityEvent(
                    event_type="circuit_break",
                    tool_id=tool_id,
                    success=False,
                    metadata={"tool_id": tool_id, "error_class": circuit_state},
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("RecoveryExecutor: event_logger.emit(circuit_break) failed", exc_info=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _model_to_dict(self, model: object) -> dict[str, object] | None:
        """Convert a Pydantic model to a plain dict for cache key computation."""
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
            ErrorClass.AUTH_EXPIRED: "auth_expired",
            ErrorClass.DATA_MISSING: "not_found",
            ErrorClass.INVALID_REQUEST: "validation",
            ErrorClass.TIMEOUT: "timeout",
            ErrorClass.DEPRECATED: "not_found",
            ErrorClass.APP_ERROR: "execution",
            ErrorClass.UNKNOWN: "api_error",
        }
        return mapping.get(error_class, "execution")
