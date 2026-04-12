# SPDX-License-Identifier: Apache-2.0
"""Exponential backoff retry logic for the KOSMOS LLM client module."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

import httpx
from pydantic import BaseModel, ConfigDict, Field

from kosmos.llm.errors import AuthenticationError, LLMConnectionError, LLMResponseError

logger = logging.getLogger(__name__)


class RetryPolicy(BaseModel):
    """Configuration for retry behavior."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, ge=0)
    base_delay: float = Field(default=1.0, gt=0)
    multiplier: float = Field(default=2.0, ge=1.0)
    max_delay: float = Field(default=60.0, gt=0)
    retryable_status_codes: frozenset[int] = Field(default_factory=lambda: frozenset({429, 503}))


async def retry_with_backoff[T](
    func: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
) -> T:
    """Execute an async function with exponential backoff retry.

    Args:
        func: Async callable to execute (no arguments — use a closure).
        policy: Retry configuration.

    Returns:
        The result of the successful function call.

    Raises:
        AuthenticationError: On 401/403 (immediate, no retry).
        LLMResponseError: On non-retryable HTTP errors (immediate, no retry).
        LLMConnectionError: After all retries exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await func()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            # Non-retryable: 401, 403 → AuthenticationError (immediate)
            if status in {401, 403}:
                raise AuthenticationError(
                    f"Authentication failed: HTTP {status}",
                    status_code=status,
                ) from exc

            # Non-retryable: other non-retryable codes → LLMResponseError (immediate)
            if status not in policy.retryable_status_codes:
                raise LLMResponseError(
                    f"API error: HTTP {status}",
                    status_code=status,
                ) from exc

            # Retryable: 429, 503
            last_exception = exc
            if attempt < policy.max_retries:
                delay = _compute_delay(attempt, policy)
                logger.warning(
                    "Retryable error (HTTP %d), attempt %d/%d, retrying in %.2fs",
                    status,
                    attempt + 1,
                    policy.max_retries,
                    delay,
                )
                await asyncio.sleep(delay)

        except httpx.RequestError as exc:
            last_exception = exc
            if attempt < policy.max_retries:
                delay = _compute_delay(attempt, policy)
                logger.warning(
                    "Transport error (%s), attempt %d/%d, retrying in %.2fs",
                    type(exc).__name__,
                    attempt + 1,
                    policy.max_retries,
                    delay,
                )
                await asyncio.sleep(delay)

    # All retries exhausted
    raise LLMConnectionError(
        f"All {policy.max_retries} retries exhausted",
    ) from last_exception


def _compute_delay(attempt: int, policy: RetryPolicy) -> float:
    """Compute delay with exponential backoff and full jitter.

    Formula: min(max_delay, base_delay * multiplier^attempt) * random(0, 1)
    """
    exp_delay = min(policy.max_delay, policy.base_delay * (policy.multiplier**attempt))
    return random.uniform(0, exp_delay)  # noqa: S311 — not cryptographic
