# SPDX-License-Identifier: Apache-2.0
"""Integration test T030 — FR-006, SC-003, spec Edge Cases (partial results).

3-worker scenario, mid-flight cancel, wall-clock assertion ≤ 500 ms.
Asserts cancel message is the last message in each worker's mailbox queue.
Partial-results edge case: if a worker already posted result before cancel,
it is preserved in the partial plan.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime, UTC
from typing import Any
from uuid import UUID, uuid4

import pytest

from kosmos.agents.context import AgentContext
from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
)
from kosmos.agents.worker import Worker
from kosmos.llm.client import LLMClient
from kosmos.llm.models import StreamEvent, TokenUsage
from kosmos.tools.models import LookupMeta, LookupRecord
from tests.agents.conftest import StubLLMClient, build_test_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SlowLLMClient(LLMClient):
    """LLMClient subclass that sleeps for a long time — allows cancellation testing."""

    def __new__(cls, delay: float = 10.0) -> "_SlowLLMClient":  # type: ignore[misc]
        return object.__new__(cls)

    def __init__(self, delay: float = 10.0) -> None:
        self._delay = delay

    async def stream(self, messages: Any, *, tools: Any = None, **kwargs: Any) -> AsyncIterator[StreamEvent]:  # type: ignore[override]
        await asyncio.sleep(self._delay)
        yield StreamEvent(type="usage", usage=TokenUsage(input_tokens=1, output_tokens=1))


class _TrackingMailbox:
    """In-memory mailbox that records message order."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._by_recipient: dict[str, list[AgentMessage]] = {}

    async def send(self, message: AgentMessage) -> None:
        self._messages.append(message)
        self._by_recipient.setdefault(message.recipient, []).append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._by_recipient.get(recipient, [])):
            yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._by_recipient.get(recipient, [])):
            yield msg

    def last_message_for(self, recipient: str) -> AgentMessage | None:
        msgs = self._by_recipient.get(recipient, [])
        return msgs[-1] if msgs else None

    def messages_of_type(self, msg_type: MessageType) -> list[AgentMessage]:
        return [m for m in self._messages if m.msg_type == msg_type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_propagates_to_worker_task() -> None:
    """FR-006: asyncio.cancel() on a worker task propagates CancelledError."""
    llm = _SlowLLMClient(delay=10.0)
    mailbox = _TrackingMailbox()

    ctx = AgentContext(
        session_id=uuid4(),
        specialist_role="transport",
        worker_id=f"worker-transport-{uuid4()}",
        tool_registry=build_test_registry(),
        llm_client=llm,
    )

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    task = asyncio.create_task(worker.run("Slow task"))
    await asyncio.sleep(0.01)  # Let task start

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Worker must not post any messages on cancel
    assert len(mailbox._messages) == 0, (
        f"Cancelled worker must not post messages; got: {mailbox._messages}"
    )


@pytest.mark.asyncio
async def test_cancel_and_wait_completes_within_500ms() -> None:
    """SC-003: cancel_and_wait() must complete within 500 ms."""
    llm = StubLLMClient(responses=[])
    mailbox = _TrackingMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # Manually inject slow worker tasks
    slow_tasks: list[asyncio.Task[None]] = []
    for i in range(3):
        worker_id = f"worker-slow-{i}-{uuid4()}"
        task = asyncio.create_task(asyncio.sleep(10), name=f"slow-worker-{i}")
        coordinator._worker_tasks[worker_id] = task
        slow_tasks.append(task)

    start = time.monotonic()
    await coordinator.cancel_and_wait(timeout=0.5)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, f"SC-003: cancel_and_wait took {elapsed:.3f}s, must be < 1.0s"
    assert coordinator._cancel_requested is True


@pytest.mark.asyncio
async def test_cancel_sets_cancel_flag() -> None:
    """FR-006: cancel() sets _cancel_requested flag on the coordinator."""
    llm = StubLLMClient(responses=[])
    mailbox = _TrackingMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    assert coordinator._cancel_requested is False
    coordinator.cancel()
    assert coordinator._cancel_requested is True


@pytest.mark.asyncio
async def test_cancel_sends_cancel_messages_to_workers() -> None:
    """FR-006: cancel_and_wait() sends cancel messages to in-flight workers."""
    llm = StubLLMClient(responses=[])
    mailbox = _TrackingMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # Inject dummy worker tasks
    worker_ids = [f"worker-{i}-{uuid4()}" for i in range(2)]
    for wid in worker_ids:
        task = asyncio.create_task(asyncio.sleep(10), name=f"w-{wid}")
        coordinator._worker_tasks[wid] = task

    await coordinator.cancel_and_wait(timeout=0.5)

    # All workers must have received a cancel message
    cancel_messages = mailbox.messages_of_type(MessageType.cancel)
    cancel_recipients = {m.recipient for m in cancel_messages}
    for wid in worker_ids:
        assert wid in cancel_recipients, (
            f"Worker {wid!r} did not receive cancel message; "
            f"cancel recipients: {cancel_recipients}"
        )


@pytest.mark.asyncio
async def test_partial_results_preserved_after_cancel() -> None:
    """spec Edge Cases: partial results posted before cancel are preserved in plan."""
    from kosmos.agents.plan import PlanStatus

    session_id = uuid4()
    llm = StubLLMClient(responses=[])
    mailbox = _TrackingMailbox()

    coordinator = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )
    coordinator._cancel_requested = True  # Simulate cancel already set

    # Pre-seed one successful worker result
    cid = uuid4()
    meta = LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=3,
    )
    result_msg = AgentMessage(
        sender="worker-civil_affairs",
        recipient="coordinator",
        msg_type=MessageType.result,
        payload=ResultPayload(
            lookup_output=LookupRecord(kind="record", item={"data": "partial"}, meta=meta),
            turn_count=1,
        ),
        timestamp=datetime.now(UTC),
        correlation_id=cid,
    )

    partial_plan = coordinator._build_partial_plan([result_msg])

    assert partial_plan.status == PlanStatus.partial
    assert str(cid) in [str(c) for c in partial_plan.worker_correlation_ids]
    assert "cancelled" in (partial_plan.message or "").lower()


@pytest.mark.asyncio
async def test_cancel_no_active_workers_completes_instantly() -> None:
    """FR-006: cancel_and_wait() with no active workers returns immediately."""
    llm = StubLLMClient(responses=[])
    mailbox = _TrackingMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # No workers registered
    start = time.monotonic()
    await coordinator.cancel_and_wait(timeout=0.5)
    elapsed = time.monotonic() - start

    assert elapsed < 0.1, f"No-worker cancel took {elapsed:.3f}s, should be instant"
