# SPDX-License-Identifier: Apache-2.0
"""Test T021 — FR-008..FR-013: worker lifecycle.

Verifies:
- Worker sees only {lookup, resolve_location} in its tool registry (FR-011)
- Worker posts a result message after successful run (FR-008)
- Worker posts an error message on unrecoverable exception (FR-008, spec Edge Cases)
- Worker propagates CancelledError without posting a further message (FR-006)
- AgentConfigurationError raised for disallowed tools (FR-011)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from kosmos.agents.context import AgentContext
from kosmos.agents.errors import AgentConfigurationError
from kosmos.agents.mailbox.messages import AgentMessage, MessageType
from kosmos.agents.worker import Worker
from kosmos.llm.client import LLMClient
from kosmos.llm.models import StreamEvent, TokenUsage
from kosmos.tools.registry import ToolRegistry
from tests.agents.conftest import StubLLMClient, build_test_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FailingLLMClient(LLMClient):
    """LLMClient subclass that raises on stream()."""

    def __new__(cls) -> _FailingLLMClient:  # type: ignore[misc]
        return object.__new__(cls)

    def __init__(self) -> None:
        pass  # bypass super().__init__()

    async def stream(  # type: ignore[override]
        self, messages: Any, *, tools: Any = None, **kwargs: Any
    ) -> AsyncIterator[StreamEvent]:
        raise RuntimeError("LLM failed catastrophically")
        yield  # make it an async generator


class _CancellableLLMClient(LLMClient):
    """LLMClient subclass that blocks forever (cancelled by test)."""

    def __new__(cls) -> _CancellableLLMClient:  # type: ignore[misc]
        return object.__new__(cls)

    def __init__(self) -> None:
        pass

    async def stream(  # type: ignore[override]
        self, messages: Any, *, tools: Any = None, **kwargs: Any
    ) -> AsyncIterator[StreamEvent]:
        await asyncio.sleep(10)  # Will be cancelled
        yield StreamEvent(type="usage", usage=TokenUsage(input_tokens=1, output_tokens=1))


class _InMemoryMailbox:
    """Minimal in-memory mailbox for worker tests."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []

    async def send(self, message: AgentMessage) -> None:
        self._messages.append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._messages):
            if msg.recipient == recipient:
                yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._messages):
            if msg.recipient == recipient:
                yield msg

    def messages_of_type(self, msg_type: MessageType) -> list[AgentMessage]:
        return [m for m in self._messages if m.msg_type == msg_type]


def _make_ctx(
    llm: LLMClient,
    registry: ToolRegistry | None = None,
    role: str = "civil_affairs",
) -> AgentContext:
    """Build a minimal AgentContext for tests."""
    reg = registry or build_test_registry()
    return AgentContext(
        session_id=uuid4(),
        specialist_role=role,
        worker_id=f"worker-{role}-{uuid4()}",
        tool_registry=reg,
        llm_client=llm,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worker_rejects_disallowed_tools() -> None:
    """FR-011: Worker construction fails if registry contains non-facade tools."""
    from unittest.mock import MagicMock

    llm = StubLLMClient(responses=[])

    # Inject a sentinel object directly into the registry's internal dict
    # to simulate a tool that is not in {lookup, resolve_location}.
    bad_registry = ToolRegistry()
    bad_registry._tools["forbidden_tool"] = MagicMock()  # type: ignore[assignment]

    ctx = AgentContext(
        session_id=uuid4(),
        specialist_role="transport",
        worker_id=f"worker-transport-{uuid4()}",
        tool_registry=bad_registry,
        llm_client=llm,
    )

    with pytest.raises(AgentConfigurationError, match="forbidden_tool"):
        Worker(ctx, _InMemoryMailbox())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_worker_posts_result_after_text_response() -> None:
    """FR-008: Worker posts a result message after completing with text response."""
    llm = StubLLMClient(responses=["The answer is 42."])
    mailbox = _InMemoryMailbox()
    ctx = _make_ctx(llm)

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    await worker.run("What is the answer?")

    results = mailbox.messages_of_type(MessageType.result)
    errors = mailbox.messages_of_type(MessageType.error)

    assert len(results) == 1, f"Expected 1 result message, got {len(results)}"
    assert len(errors) == 0, f"Expected 0 error messages, got {len(errors)}"

    result_msg = results[0]
    assert result_msg.sender == ctx.worker_id
    assert result_msg.recipient == ctx.coordinator_id
    assert result_msg.msg_type == MessageType.result


@pytest.mark.asyncio
async def test_worker_result_contains_lookup_output() -> None:
    """FR-008: The result payload must contain a LookupRecord or similar."""
    from kosmos.agents.mailbox.messages import ResultPayload

    llm = StubLLMClient(responses=["Transport info found."])
    mailbox = _InMemoryMailbox()
    ctx = _make_ctx(llm, role="transport")

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    await worker.run("Find transport options.")

    results = mailbox.messages_of_type(MessageType.result)
    assert results, "Worker must post a result message"

    payload = results[0].payload
    assert isinstance(payload, ResultPayload)
    assert payload.lookup_output is not None
    assert payload.turn_count >= 0


@pytest.mark.asyncio
async def test_worker_posts_error_on_exception() -> None:
    """FR-008: Worker posts an error message if an unrecoverable exception occurs."""
    llm = _FailingLLMClient()
    mailbox = _InMemoryMailbox()
    ctx = _make_ctx(llm)

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    await worker.run("This will fail.")

    errors = mailbox.messages_of_type(MessageType.error)
    results = mailbox.messages_of_type(MessageType.result)

    assert len(errors) == 1, f"Expected 1 error message, got {len(errors)}"
    assert len(results) == 0

    from kosmos.agents.mailbox.messages import ErrorPayload

    payload = errors[0].payload
    assert isinstance(payload, ErrorPayload)
    assert "RuntimeError" in payload.error_type or "LLM failed" in payload.message


@pytest.mark.asyncio
async def test_worker_propagates_cancelled_error() -> None:
    """FR-006: CancelledError propagates without posting error to mailbox."""
    llm = _CancellableLLMClient()
    mailbox = _InMemoryMailbox()
    ctx = _make_ctx(llm)

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]

    task = asyncio.create_task(worker.run("Long running task"))
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # No messages should have been posted
    assert len(mailbox._messages) == 0, (
        f"CancelledError must NOT cause worker to post a message; "
        f"got {len(mailbox._messages)} messages"
    )


@pytest.mark.asyncio
async def test_worker_tool_restriction_empty_registry() -> None:
    """FR-011: Worker with empty registry (subset of allowed tools) is valid."""
    llm = StubLLMClient(responses=["Ok."])
    mailbox = _InMemoryMailbox()
    registry = build_test_registry()  # empty registry — subset of {lookup, resolve_location}

    ctx = _make_ctx(llm, registry=registry)
    # Should NOT raise
    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    assert worker.worker_id == ctx.worker_id


@pytest.mark.asyncio
async def test_worker_correlation_id_from_task_message() -> None:
    """Worker uses task message's ID as correlation_id when provided."""
    from kosmos.agents.mailbox.messages import TaskPayload

    llm = StubLLMClient(responses=["Result."])
    mailbox = _InMemoryMailbox()
    ctx = _make_ctx(llm)

    task_msg_id = uuid4()
    task_msg = AgentMessage(
        sender="coordinator",
        recipient=ctx.worker_id,
        msg_type=MessageType.task,
        payload=TaskPayload(instruction="Research this", specialist_role="civil_affairs"),
        timestamp=datetime.now(UTC),
        id=task_msg_id,
    )

    worker = Worker(ctx, mailbox, task_message=task_msg)  # type: ignore[arg-type]
    await worker.run("Research this")

    results = mailbox.messages_of_type(MessageType.result)
    assert results, "Expected a result message"
    assert results[0].correlation_id == task_msg_id
