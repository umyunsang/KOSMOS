# SPDX-License-Identifier: Apache-2.0
"""Test T020 — FR-007: solo mode backward compatibility.

Coordinator with role='solo' must NOT spawn workers and must return a
CoordinatorPlan with empty worker_correlation_ids.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import AgentMessage
from kosmos.agents.plan import PlanStatus
from tests.agents.conftest import StubLLMClient, build_test_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _InMemoryMailbox:
    """Minimal in-memory mailbox for unit tests."""

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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_solo_mode_no_workers_spawned() -> None:
    """FR-007: solo mode coordinator spawns NO workers."""
    synthesis_json = json.dumps(
        {
            "steps": [
                {
                    "ministry": "civil_affairs",
                    "action": "Submit request",
                    "depends_on": [],
                    "execution_mode": "parallel",
                }
            ],
            "message": "Solo plan.",
        }
    )
    llm = StubLLMClient(responses=[synthesis_json])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        role="solo",
    )

    plan = await coordinator.run("I need to renew my residence card.")

    # Solo mode: no workers spawned → no correlation IDs
    assert plan.worker_correlation_ids == []
    # The plan still returns a valid CoordinatorPlan
    assert plan.session_id == coordinator._session_id
    # LLM was called (synthesis phase executes)
    assert llm._stub_call_count >= 1


@pytest.mark.asyncio
async def test_solo_mode_mailbox_receives_no_worker_messages() -> None:
    """FR-007: in solo mode no task/result/error messages are posted to mailbox."""
    llm = StubLLMClient(responses=['{"steps": [], "message": "empty solo"}'])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        role="solo",
    )

    await coordinator.run("Citizens query.")

    # No messages from workers in the mailbox
    from kosmos.agents.mailbox.messages import MessageType

    worker_message_types = {MessageType.task, MessageType.result, MessageType.error}
    for msg in mailbox._messages:
        assert msg.msg_type not in worker_message_types, (
            f"Solo mode should not post {msg.msg_type!r} messages; got: {msg}"
        )


@pytest.mark.asyncio
async def test_solo_mode_returns_coordinator_plan() -> None:
    """FR-007: solo mode returns a proper CoordinatorPlan instance."""
    from kosmos.agents.plan import CoordinatorPlan

    llm = StubLLMClient(responses=['{"steps": [], "message": null}'])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        role="solo",
    )

    plan = await coordinator.run("Simple request.")

    assert isinstance(plan, CoordinatorPlan)
    assert plan.worker_correlation_ids == []


@pytest.mark.asyncio
async def test_solo_mode_no_results_plan_when_llm_empty() -> None:
    """FR-007: when LLM returns nothing, solo mode still returns no_results plan."""
    llm = StubLLMClient(responses=[""])  # Empty response
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        role="solo",
    )

    plan = await coordinator.run("Empty request.")

    assert plan.status == PlanStatus.no_results
    assert plan.steps == []
    assert plan.worker_correlation_ids == []


@pytest.mark.asyncio
async def test_coordinator_mode_not_solo() -> None:
    """Default coordinator role must NOT enter solo mode."""
    llm = StubLLMClient(responses=['["civil_affairs"]'])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        role="coordinator",  # explicit coordinator role
    )

    # The coordinator should NOT use solo path — verify role is set correctly
    assert coordinator._role == "coordinator"
    assert coordinator._role != "solo"
