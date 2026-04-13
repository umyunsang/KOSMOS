# SPDX-License-Identifier: Apache-2.0
"""Retry policy and retry loop for tool adapter calls.

Implements exponential back-off with full jitter per AWS guidance:
    delay = random.uniform(0, min(max_delay, base_delay * multiplier ** attempt))
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ConfigDict

from kosmos.recovery.classifier import ClassifiedError, DataGoKrErrorClassifier, ErrorClass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

AdapterFn = Callable[..., Awaitable[dict[str, object]]]


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class ToolRetryPolicy(BaseModel):
    """Configuration for the retry behaviour of a single tool call."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = 3
    """Maximum number of retry attempts (not counting the initial attempt)."""

    base_delay: float = 1.0
    """Initial back-off delay in seconds before the first retry."""

    multiplier: float = 2.0
    """Back-off multiplier applied on each successive retry."""

    max_delay: float = 30.0
    """Upper bound on back-off delay in seconds."""

    retryable_classes: frozenset[ErrorClass] = frozenset(
        {ErrorClass.TRANSIENT, ErrorClass.RATE_LIMIT, ErrorClass.TIMEOUT}
    )
    """Set of error classes that are eligible for retry."""


# ---------------------------------------------------------------------------
# Retry loop
# ---------------------------------------------------------------------------


async def retry_tool_call(
    adapter: AdapterFn,
    args: object,
    classifier: DataGoKrErrorClassifier,
    policy: ToolRetryPolicy,
    *,
    is_foreground: bool = True,
) -> tuple[dict[str, object] | None, ClassifiedError | None, int]:
    """Call *adapter* with *args*, retrying on classified retryable errors.

    Back-off formula (full jitter):
        delay = random.uniform(0, min(max_delay, base_delay * multiplier ** attempt))

    For foreground calls the full ``max_retries`` budget is used.  For
    background calls the budget is capped at ``min(1, max_retries)`` to
    avoid holding background resources for extended periods.

    Args:
        adapter: Async callable that performs the actual API call.
        args: Input argument passed verbatim to *adapter*.
        classifier: Classifier instance for translating exceptions.
        policy: Retry configuration.
        is_foreground: ``True`` (default) for user-facing calls; ``False`` for
            background / batch calls where a tighter retry cap applies.

    Returns:
        A 3-tuple ``(result_dict, last_classified_error, attempt_count)`` where:
        - ``result_dict`` is the successful adapter output, or ``None`` on failure.
        - ``last_classified_error`` is the last error seen, or ``None`` on success.
        - ``attempt_count`` is the total number of attempts made (1 = no retry).
    """
    effective_max = policy.max_retries if is_foreground else min(1, policy.max_retries)

    last_error: ClassifiedError | None = None
    attempt = 0

    while attempt <= effective_max:
        try:
            result = await adapter(args)
            return result, None, attempt + 1
        except Exception as exc:  # noqa: BLE001
            classified = classifier.classify_exception(exc)
            last_error = classified

            not_retryable = (
                not classified.is_retryable
                or classified.error_class not in policy.retryable_classes
            )
            if not_retryable:
                logger.warning(
                    "Non-retryable error on attempt %d: class=%s message=%s",
                    attempt + 1,
                    classified.error_class,
                    classified.raw_message,
                )
                return None, last_error, attempt + 1

            if attempt >= effective_max:
                logger.warning(
                    "Retry budget exhausted after %d attempt(s): class=%s message=%s",
                    attempt + 1,
                    classified.error_class,
                    classified.raw_message,
                )
                return None, last_error, attempt + 1

            delay = random.uniform(  # noqa: S311
                0,
                min(policy.max_delay, policy.base_delay * (policy.multiplier**attempt)),
            )
            logger.warning(
                "Retryable error on attempt %d, retrying in %.2fs: class=%s message=%s",
                attempt + 1,
                delay,
                classified.error_class,
                classified.raw_message,
            )
            await asyncio.sleep(delay)
            attempt += 1

    # Should be unreachable but satisfies the type checker
    return None, last_error, attempt + 1  # pragma: no cover
