# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSAX LLM client module."""

from __future__ import annotations


class KosaxLLMError(Exception):
    """Base exception for all LLM client errors."""


class ConfigurationError(KosaxLLMError):
    """Missing or invalid configuration (e.g., missing KOSAX_FRIENDLI_TOKEN)."""


class BudgetExceededError(KosaxLLMError):
    """Session token budget exhausted."""


class AuthenticationError(KosaxLLMError):
    """API authentication failed (401/403)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMConnectionError(KosaxLLMError):
    """Endpoint unreachable after retry exhaustion."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(KosaxLLMError):
    """Non-retryable API error (400, 404, 500)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class StreamInterruptedError(KosaxLLMError):
    """Streaming response interrupted mid-delivery."""
