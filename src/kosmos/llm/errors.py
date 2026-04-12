# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSMOS LLM client module."""

from __future__ import annotations


class KosmosLLMError(Exception):
    """Base exception for all LLM client errors."""


class ConfigurationError(KosmosLLMError):
    """Missing or invalid configuration (e.g., missing KOSMOS_FRIENDLI_TOKEN)."""


class BudgetExceededError(KosmosLLMError):
    """Session token budget exhausted."""


class AuthenticationError(KosmosLLMError):
    """API authentication failed (401/403)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMConnectionError(KosmosLLMError):
    """Endpoint unreachable after retry exhaustion."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(KosmosLLMError):
    """Non-retryable API error (400, 404, 500)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class StreamInterruptedError(KosmosLLMError):
    """Streaming response interrupted mid-delivery."""
