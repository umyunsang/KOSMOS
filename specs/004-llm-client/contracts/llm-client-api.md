# Contract: LLM Client API

**Module**: `kosmos.llm`
**Date**: 2026-04-12

## Public Interface

### LLMClient

```python
class LLMClient:
    """Async LLM client for FriendliAI Serverless endpoint."""

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        """Initialize with config. Loads from env vars if config is None.

        Raises:
            ConfigurationError: If KOSMOS_FRIENDLI_TOKEN is missing.
        """

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
    ) -> ChatCompletionResponse:
        """Send a non-streaming chat completion request.

        Raises:
            BudgetExceededError: If session token budget is exhausted.
            AuthenticationError: If API returns 401/403.
            LLMConnectionError: If endpoint is unreachable after retries.
            LLMResponseError: If API returns non-retryable error.
        """

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Send a streaming chat completion request.

        Yields StreamEvent objects as they arrive. Final event contains usage stats.

        Raises:
            BudgetExceededError: If session token budget is exhausted.
            AuthenticationError: If API returns 401/403.
            LLMConnectionError: If endpoint is unreachable after retries.
            StreamInterruptedError: If stream is interrupted mid-response.
        """

    @property
    def usage(self) -> UsageTracker:
        """Current session usage tracker."""

    async def close(self) -> None:
        """Close the underlying HTTP client."""

    async def __aenter__(self) -> "LLMClient": ...
    async def __aexit__(self, *args) -> None: ...
```

### UsageTracker

```python
class UsageTracker:
    """Tracks cumulative token usage against a session budget."""

    def __init__(self, budget: int) -> None: ...

    def can_afford(self, estimated_input_tokens: int) -> bool:
        """Pre-flight check: is there likely enough budget for this call?"""

    def debit(self, usage: TokenUsage) -> None:
        """Record usage from a completed call."""

    @property
    def remaining(self) -> int:
        """Remaining token budget."""

    @property
    def is_exhausted(self) -> bool:
        """Whether the budget is fully consumed."""
```

## Error Hierarchy

```python
class KosmosLLMError(Exception):
    """Base exception for all LLM client errors."""

class ConfigurationError(KosmosLLMError):
    """Missing or invalid configuration (e.g., missing KOSMOS_FRIENDLI_TOKEN)."""

class BudgetExceededError(KosmosLLMError):
    """Session token budget exhausted."""

class AuthenticationError(KosmosLLMError):
    """API authentication failed (401/403)."""

class LLMConnectionError(KosmosLLMError):
    """Endpoint unreachable after retry exhaustion."""

class LLMResponseError(KosmosLLMError):
    """Non-retryable API error (400, 404, 500)."""

class StreamInterruptedError(KosmosLLMError):
    """Streaming response interrupted mid-delivery."""
```

## Module Layout

```
src/kosmos/llm/
├── __init__.py          # Public exports: LLMClient, models, errors
├── client.py            # LLMClient implementation
├── models.py            # Pydantic v2 models (ChatMessage, StreamEvent, etc.)
├── config.py            # LLMClientConfig (pydantic-settings)
├── errors.py            # Error hierarchy
├── retry.py             # RetryPolicy and retry logic
└── usage.py             # UsageTracker
```
