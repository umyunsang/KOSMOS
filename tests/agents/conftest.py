# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for agent integration tests.

Provides:
- tmp_mailbox_root: temp directory for FileMailbox (env patched)
- fixture_tape_llm: stub LLM that replays scripted responses from JSON
- build_test_registry: ToolRegistry restricted to {lookup, resolve_location}
- StubLLMClient: LLMClient subclass that replays scripted text responses
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from kosmos.llm.client import LLMClient
from kosmos.llm.models import StreamEvent, TokenUsage
from kosmos.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Stub LLM client — proper subclass of LLMClient for Pydantic type checking
# ---------------------------------------------------------------------------


class StubLLMClient(LLMClient):
    """LLMClient subclass that replays scripted text responses without real HTTP.

    Bypasses LLMClient.__init__ via object.__new__ so no env vars or httpx
    client are needed. Suitable wherever Pydantic validates `llm_client: LLMClient`.
    """

    def __new__(cls, responses: list[str]) -> "StubLLMClient":  # type: ignore[misc]
        instance = object.__new__(cls)
        return instance

    def __init__(self, responses: list[str]) -> None:
        # Do NOT call super().__init__() — that reads env vars and creates httpx client
        self._stub_responses = list(responses)
        self._stub_index = 0
        self._stub_call_count = 0
        self._stub_tools_args: list[Any] = []

    async def stream(  # type: ignore[override]
        self,
        messages: Any,
        *,
        tools: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        self._stub_call_count += 1
        self._stub_tools_args.append(tools)

        if self._stub_index < len(self._stub_responses):
            text = self._stub_responses[self._stub_index]
            self._stub_index += 1
        else:
            text = ""

        if text:
            yield StreamEvent(type="content_delta", content=text)
        yield StreamEvent(type="usage", usage=TokenUsage(input_tokens=5, output_tokens=5))

    def reset(self) -> None:
        """Reset replay state."""
        self._stub_index = 0
        self._stub_call_count = 0
        self._stub_tools_args = []


# ---------------------------------------------------------------------------
# Mailbox root fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_mailbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a per-test temp directory as the mailbox root.

    Patches KOSMOS_AGENT_MAILBOX_ROOT so FileMailbox uses it.
    """
    mailbox_dir = tmp_path / "mailbox"
    mailbox_dir.mkdir(mode=0o700)
    monkeypatch.setenv("KOSMOS_AGENT_MAILBOX_ROOT", str(mailbox_dir))
    return mailbox_dir


# ---------------------------------------------------------------------------
# Fixture-tape LLM stub
# ---------------------------------------------------------------------------


class FixtureTapeLLMClient(LLMClient):
    """LLMClient subclass that replays scripted LLM responses from JSON files.

    The fixture JSON file has the structure:
    {
      "responses": [
        {
          "content": "optional text",
          "tool_calls": [
            {"id": "tc1", "name": "lookup", "arguments": "{...}"}
          ],
          "usage": {"input_tokens": 10, "output_tokens": 5}
        },
        ...
      ]
    }

    Responses are popped in order. If the queue is exhausted a stop event
    is returned.

    Bypasses LLMClient.__init__ so no env vars or httpx client are needed.
    """

    def __new__(cls, responses: list[dict[str, Any]]) -> "FixtureTapeLLMClient":  # type: ignore[misc]
        instance = object.__new__(cls)
        return instance

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        # Do NOT call super().__init__() — no env vars or httpx client needed
        self._responses = list(responses)
        self._index = 0

    async def stream(  # type: ignore[override]
        self,
        messages: Any,
        *,
        tools: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Yield events matching a scripted response entry."""
        if self._index >= len(self._responses):
            # Exhausted — return a clean stop (no tools)
            yield StreamEvent(type="usage", usage=TokenUsage(input_tokens=0, output_tokens=0))
            return

        entry = self._responses[self._index]
        self._index += 1

        # Emit text content if present
        content: str = entry.get("content", "") or ""
        if content:
            yield StreamEvent(type="content_delta", content=content)

        # Emit tool call deltas
        tool_calls: list[dict[str, Any]] = entry.get("tool_calls", [])
        for idx, tc in enumerate(tool_calls):
            yield StreamEvent(
                type="tool_call_delta",
                tool_call_index=idx,
                tool_call_id=tc.get("id", str(uuid4())),
                function_name=tc.get("name", ""),
                function_args_delta=tc.get("arguments", "{}"),
            )

        # Emit usage
        usage_data: dict[str, int] = entry.get("usage", {})
        yield StreamEvent(
            type="usage",
            usage=TokenUsage(
                input_tokens=usage_data.get("input_tokens", 5),
                output_tokens=usage_data.get("output_tokens", 5),
            ),
        )

    def reset(self) -> None:
        """Reset replay index to start."""
        self._index = 0


def load_fixture_tape(fixture_path: Path) -> FixtureTapeLLMClient:
    """Load a JSON fixture tape and return a stub LLM client."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return FixtureTapeLLMClient(responses=data.get("responses", []))


@pytest.fixture
def fixture_tape_llm(request: pytest.FixtureRequest) -> FixtureTapeLLMClient:
    """Return a FixtureTapeLLMClient loaded from the fixture file specified
    via an indirect parametrize or from the default multi_ministry_query.json.
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixture_name = getattr(request, "param", "multi_ministry_query.json")
    fixture_path = fixtures_dir / fixture_name
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")
    return load_fixture_tape(fixture_path)


# ---------------------------------------------------------------------------
# Minimal ToolRegistry restricted to {lookup, resolve_location}
# ---------------------------------------------------------------------------


def build_test_registry() -> ToolRegistry:
    """Return a ToolRegistry with NO real tools registered.

    Workers in tests see only the two facade functions (lookup,
    resolve_location) which are invoked directly via the engine — the
    registry is used for concurrency-safe lookup and export, not for
    actual dispatch in agent tests.

    The returned registry is empty; tests that need specific tool lookup
    behaviour should mock the lookup/resolve_location functions directly.
    """
    registry = ToolRegistry()
    return registry
