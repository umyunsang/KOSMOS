# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the UMMAYA LLM client module."""

from __future__ import annotations


class UmmayaLLMError(Exception):
    """Base exception for all LLM client errors."""


class ConfigurationError(UmmayaLLMError):
    """Missing or invalid configuration (e.g., missing UMMAYA_FRIENDLI_TOKEN)."""


class BudgetExceededError(UmmayaLLMError):
    """Session token budget exhausted."""


class AuthenticationError(UmmayaLLMError):
    """API authentication failed (401/403)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMConnectionError(UmmayaLLMError):
    """Endpoint unreachable after retry exhaustion."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(UmmayaLLMError):
    """Non-retryable API error (400, 404, 500)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class StreamInterruptedError(UmmayaLLMError):
    """Streaming response interrupted mid-delivery."""
