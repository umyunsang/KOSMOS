# SPDX-License-Identifier: Apache-2.0
"""Async LLM client for the KOSMOS project (FriendliAI Serverless endpoint)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx
from pydantic import ValidationError

from kosmos.llm.config import LLMClientConfig
from kosmos.llm.errors import (
    AuthenticationError,
    BudgetExceededError,
    ConfigurationError,
    LLMResponseError,
    StreamInterruptedError,
)
from kosmos.llm.models import (
    ChatCompletionResponse,
    ChatMessage,
    FunctionCall,
    StreamEvent,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from kosmos.llm.retry import RetryPolicy, retry_with_backoff
from kosmos.llm.usage import UsageTracker

logger = logging.getLogger(__name__)


class LLMClient:
    """Async LLM client for FriendliAI Serverless endpoint."""

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        """Initialize with config. Loads from env vars if config is None.

        Raises:
            ConfigurationError: If KOSMOS_FRIENDLI_TOKEN is missing or invalid.
        """
        if config is None:
            try:
                config = LLMClientConfig()
            except ValidationError as exc:
                raise ConfigurationError(
                    f"Failed to load LLM client configuration from environment: {exc}"
                ) from exc

        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.token.get_secret_value()}"},
            timeout=httpx.Timeout(config.timeout),
        )
        self._usage = UsageTracker(budget=self._config.session_budget)
        self._retry_policy = RetryPolicy(max_retries=self._config.max_retries)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def usage(self) -> UsageTracker:
        """Current session usage tracker."""
        return self._usage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolDefinition | dict[str, object]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
    ) -> ChatCompletionResponse:
        """Send a non-streaming chat completion request.

        Args:
            messages: Ordered list of conversation messages.
            tools: Optional tool definitions (ToolDefinition models or raw dicts).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the completion.
            top_p: Nucleus sampling parameter.
            stop: Stop sequences.

        Returns:
            Parsed ChatCompletionResponse.

        Raises:
            BudgetExceededError: If the session token budget is exhausted.
            AuthenticationError: On 401 or 403 responses.
            LLMResponseError: On 400, 404, or other non-retryable HTTP errors.
            LLMConnectionError: On network / transport failures after all retries.
        """
        if not self._usage.can_afford(max_tokens or 1):
            raise BudgetExceededError("Session token budget exhausted")

        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            tools=tools,
            stream=False,
        )

        logger.debug(
            "LLM complete request: model=%s messages=%d",
            self._config.model,
            len(messages),
        )

        async def _do_request() -> ChatCompletionResponse:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return self._parse_completion_response(response.json())

        result = await retry_with_backoff(_do_request, self._retry_policy)
        self._usage.debit(result.usage)
        logger.info(
            "Token usage: %d input, %d output",
            result.usage.input_tokens,
            result.usage.output_tokens,
        )
        return result

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolDefinition | dict[str, object]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Send a streaming chat completion request.

        Yields StreamEvent objects as they arrive from the SSE stream.

        Args:
            messages: Ordered list of conversation messages.
            tools: Optional tool definitions (ToolDefinition models or raw dicts).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the completion.
            top_p: Nucleus sampling parameter.
            stop: Stop sequences.

        Yields:
            StreamEvent for each SSE event received.

        Raises:
            BudgetExceededError: If the session token budget is exhausted.
            StreamInterruptedError: If the connection is lost mid-stream.
            AuthenticationError: On 401 or 403 responses.
            LLMResponseError: On non-retryable HTTP errors.
        """
        if not self._usage.can_afford(max_tokens or 1):
            raise BudgetExceededError("Session token budget exhausted")

        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            tools=tools,
            stream=True,
        )

        logger.debug(
            "LLM stream request: model=%s messages=%d",
            self._config.model,
            len(messages),
        )

        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                self._raise_for_status(response)

                async for line in response.aiter_lines():
                    async for event in self._parse_sse_line(line):
                        yield event
                        if event.type == "done":
                            return

        except httpx.ConnectError as exc:
            raise StreamInterruptedError(f"Connection lost during streaming: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise StreamInterruptedError(f"Stream timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise StreamInterruptedError(f"Stream request failed: {exc}") from exc

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> LLMClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _parse_sse_line(self, line: str) -> AsyncIterator[StreamEvent]:
        """Parse a single SSE line and yield corresponding StreamEvent(s)."""
        if not line or not line.startswith("data: "):
            return

        payload_text = line[len("data: ") :]

        if payload_text == "[DONE]":
            yield StreamEvent(type="done")
            return

        try:
            chunk = json.loads(payload_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse SSE chunk: %r", payload_text)
            return

        if "usage" in chunk and chunk["usage"] is not None:
            raw_usage = chunk["usage"]
            usage = TokenUsage(
                input_tokens=raw_usage.get("prompt_tokens", 0),
                output_tokens=raw_usage.get("completion_tokens", 0),
            )
            logger.info(
                "LLM stream usage: input=%d output=%d",
                usage.input_tokens,
                usage.output_tokens,
            )
            self._usage.debit(usage)
            yield StreamEvent(type="usage", usage=usage)

        choices = chunk.get("choices")
        if not choices:
            return

        choice = choices[0]
        delta = choice.get("delta", {})

        if "content" in delta and delta["content"] is not None:
            yield StreamEvent(type="content_delta", content=delta["content"])

        if "tool_calls" in delta and delta["tool_calls"]:
            for tc_delta in delta["tool_calls"]:
                func = tc_delta.get("function", {})
                yield StreamEvent(
                    type="tool_call_delta",
                    tool_call_index=tc_delta.get("index"),
                    tool_call_id=tc_delta.get("id"),
                    function_name=func.get("name"),
                    function_args_delta=func.get("arguments"),
                )

    def _build_payload(
        self,
        *,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int | None,
        top_p: float | None,
        stop: list[str] | None,
        tools: list[ToolDefinition | dict[str, object]] | None = None,
        stream: bool,
    ) -> dict[str, object]:
        """Construct the JSON payload for a chat completions request."""
        payload: dict[str, object] = {
            "model": self._config.model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        if tools is not None:
            payload["tools"] = [
                t.model_dump() if isinstance(t, ToolDefinition) else t for t in tools
            ]
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Map HTTP error status codes to typed KOSMOS exceptions."""
        status = response.status_code
        if status in (401, 403):
            raise AuthenticationError(
                f"Authentication failed (HTTP {status})",
                status_code=status,
            )
        if status == 429:
            raise LLMResponseError(
                f"Rate limited by LLM API (HTTP 429): {response.text}",
                status_code=status,
            )
        if status >= 500:
            raise LLMResponseError(
                f"LLM API server error (HTTP {status}): {response.text}",
                status_code=status,
            )
        if status >= 400:
            raise LLMResponseError(
                f"LLM API returned error (HTTP {status}): {response.text}",
                status_code=status,
            )

    @staticmethod
    def _parse_completion_response(data: dict[str, object]) -> ChatCompletionResponse:
        """Parse a raw /chat/completions JSON response into ChatCompletionResponse."""
        choice = data["choices"][0]  # type: ignore[index]
        message = choice["message"]

        # Parse tool calls if present
        tool_calls: list[ToolCall] = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc["function"]
                tool_calls.append(
                    ToolCall(
                        id=tc["id"],
                        type=tc.get("type", "function"),
                        function=FunctionCall(
                            name=func["name"],
                            arguments=func["arguments"],
                        ),
                    )
                )

        # Parse token usage
        raw_usage = data.get("usage") or {}
        usage = TokenUsage(
            input_tokens=raw_usage.get("prompt_tokens", 0),  # type: ignore[attr-defined]
            output_tokens=raw_usage.get("completion_tokens", 0),  # type: ignore[attr-defined]
        )

        logger.info(
            "LLM complete usage: model=%s input=%d output=%d",
            data.get("model"),
            usage.input_tokens,
            usage.output_tokens,
        )

        return ChatCompletionResponse(
            id=data["id"],  # type: ignore[arg-type]
            content=message.get("content"),
            tool_calls=tool_calls,
            usage=usage,
            model=data["model"],  # type: ignore[arg-type]
            finish_reason=choice["finish_reason"],
        )
