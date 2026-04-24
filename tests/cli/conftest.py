# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for CLI tests."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from rich.console import Console

from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage
from kosmos.tools.models import GovAPITool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockQueryEngine:
    """Minimal mock engine that replays a pre-baked list of QueryEvent objects."""

    def __init__(self, events: list[QueryEvent]) -> None:
        self._events = events

    async def run(self, user_message: str) -> AsyncIterator[QueryEvent]:  # noqa: ARG002
        for event in self._events:
            yield event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_text_events() -> list[QueryEvent]:
    """A minimal sequence: text_delta → usage_update → stop."""
    return [
        QueryEvent(type="text_delta", content="안녕하세요"),
        QueryEvent(
            type="usage_update",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        ),
        QueryEvent(
            type="stop",
            stop_reason=StopReason.task_complete,
            stop_message="done",
        ),
    ]


@pytest.fixture
def mock_query_engine(simple_text_events: list[QueryEvent]) -> _MockQueryEngine:
    """Mock engine that yields a simple text + stop sequence."""
    return _MockQueryEngine(simple_text_events)


@pytest.fixture
def mock_console() -> Console:
    """Rich Console that writes to a StringIO buffer for output capture."""
    return Console(file=io.StringIO(), force_terminal=True, width=120)


class _DummyInput(BaseModel):
    """Dummy input schema for test tools."""

    query: str


class _DummyOutput(BaseModel):
    """Dummy output schema for test tools."""

    result: str


@pytest.fixture
def sample_tool() -> GovAPITool:
    """A minimal GovAPITool for testing registry lookup."""
    return GovAPITool(
        id="test_tool",
        name_ko="테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type="public",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="test 테스트",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_personal_data=False,
    )


@pytest.fixture
def mock_tool_registry(sample_tool: GovAPITool) -> Any:
    """Mock ToolRegistry whose lookup() returns the sample_tool."""
    registry = MagicMock()
    registry.lookup.return_value = sample_tool
    return registry
