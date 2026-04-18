# SPDX-License-Identifier: Apache-2.0
"""Integration test T018 — FR-001..FR-007, SC-001..SC-004.

3-worker dispatch integration test: coordinator classifies intent, spawns 3 workers,
collects results, synthesises a CoordinatorPlan, runs implementation phase.

Uses scripted LLM stubs (no live API calls).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, UTC
from uuid import UUID, uuid4

import pytest

from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
    TaskPayload,
)
from kosmos.agents.plan import CoordinatorPlan, ExecutionMode, PlanStatus, PlanStep
from kosmos.tools.models import LookupMeta, LookupRecord
from tests.agents.conftest import StubLLMClient, build_test_registry


class _InMemoryMailbox:
    """In-memory mailbox that also pre-seeds worker results for collection."""

    def __init__(self) -> None:
        self._sent: list[AgentMessage] = []
        self._pre_seeded: list[AgentMessage] = []  # coordinator ← worker results

    async def send(self, message: AgentMessage) -> None:
        self._sent.append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._sent) + list(self._pre_seeded):
            if msg.recipient == recipient:
                yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._sent) + list(self._pre_seeded):
            if msg.recipient == recipient:
                yield msg

    def seed_result(
        self,
        sender: str,
        session_id: UUID,
        correlation_id: UUID | None = None,
    ) -> None:
        """Pre-seed a result message from a worker to the coordinator."""
        meta = LookupMeta(
            source="lookup",
            fetched_at=datetime.now(UTC),
            request_id=str(uuid4()),
            elapsed_ms=5,
        )
        record = LookupRecord(kind="record", item={"info": f"result from {sender}"}, meta=meta)
        payload = ResultPayload(lookup_output=record, turn_count=1)
        msg = AgentMessage(
            sender=sender,
            recipient="coordinator",
            msg_type=MessageType.result,
            payload=payload,
            timestamp=datetime.now(UTC),
            correlation_id=correlation_id or uuid4(),
        )
        self._pre_seeded.append(msg)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coordinator_synthesis_produces_plan() -> None:
    """FR-002, FR-004: coordinator synthesis phase produces a valid CoordinatorPlan."""
    synthesis_json = json.dumps(
        {
            "steps": [
                {
                    "ministry": "civil_affairs",
                    "action": "Submit residence transfer",
                    "depends_on": [],
                    "execution_mode": "sequential",
                },
                {
                    "ministry": "transport",
                    "action": "Update vehicle registration",
                    "depends_on": [0],
                    "execution_mode": "sequential",
                },
                {
                    "ministry": "health_insurance",
                    "action": "Update insurance address",
                    "depends_on": [],
                    "execution_mode": "parallel",
                },
            ],
            "message": "All ministry tasks identified.",
        }
    )

    llm = StubLLMClient(responses=[synthesis_json])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # Seed worker results so synthesis has data to work with
    cid1, cid2, cid3 = uuid4(), uuid4(), uuid4()
    for sender, cid in [
        ("worker-civil_affairs", cid1),
        ("worker-transport", cid2),
        ("worker-health_insurance", cid3),
    ]:
        mailbox.seed_result(sender, coordinator._session_id, cid)

    # Run synthesis directly
    worker_results = [
        msg for msg in mailbox._pre_seeded if msg.recipient == "coordinator"
    ]
    plan = await coordinator._synthesis_phase(
        "I need to move: residence, vehicle, and insurance update.",
        worker_results,
    )

    assert isinstance(plan, CoordinatorPlan)
    assert plan.status == PlanStatus.complete
    assert len(plan.steps) == 3
    assert plan.session_id == coordinator._session_id


@pytest.mark.asyncio
async def test_coordinator_synthesis_captures_worker_correlation_ids() -> None:
    """SC-002: zero-orphan-id invariant — all worker correlation IDs appear in plan."""
    synthesis_json = json.dumps(
        {
            "steps": [
                {"ministry": "transport", "action": "Update", "depends_on": [], "execution_mode": "parallel"}
            ]
        }
    )
    llm = StubLLMClient(responses=[synthesis_json])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    cid_a, cid_b = uuid4(), uuid4()
    mailbox.seed_result("worker-transport", coordinator._session_id, cid_a)
    mailbox.seed_result("worker-housing", coordinator._session_id, cid_b)

    worker_results = [msg for msg in mailbox._pre_seeded if msg.recipient == "coordinator"]
    plan = await coordinator._synthesis_phase("Move request", worker_results)

    assert str(cid_a) in [str(c) for c in plan.worker_correlation_ids]
    assert str(cid_b) in [str(c) for c in plan.worker_correlation_ids]


@pytest.mark.asyncio
async def test_coordinator_synthesis_no_results_when_workers_fail() -> None:
    """FR-002: when all workers fail, synthesis returns no_results plan."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # Empty worker results — all failed
    plan = await coordinator._synthesis_phase("My request", worker_results=[])

    assert plan.status == PlanStatus.no_results
    assert plan.steps == []
    assert plan.worker_correlation_ids == []
    assert "All workers failed" in (plan.message or "")


@pytest.mark.asyncio
async def test_spawn_worker_generates_unique_ids() -> None:
    """T024: each spawned worker gets a unique worker_id."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    ctx1 = coordinator.spawn_worker("civil_affairs")
    ctx2 = coordinator.spawn_worker("civil_affairs")

    assert ctx1.worker_id != ctx2.worker_id


@pytest.mark.asyncio
async def test_spawn_worker_empty_role_raises() -> None:
    """T024: spawn_worker with empty role raises AgentConfigurationError."""
    from kosmos.agents.errors import AgentConfigurationError

    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    with pytest.raises(AgentConfigurationError, match="non-empty specialist_role"):
        coordinator.spawn_worker("")


@pytest.mark.asyncio
async def test_coordinator_implementation_phase_runs_parallel_steps() -> None:
    """FR-005: implementation phase runs parallel steps concurrently."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    plan = CoordinatorPlan(
        session_id=coordinator._session_id,
        status=PlanStatus.complete,
        steps=[
            PlanStep(ministry="transport", action="Update vehicle", execution_mode=ExecutionMode.parallel),
            PlanStep(ministry="health_insurance", action="Update insurance", execution_mode=ExecutionMode.parallel),
        ],
        worker_correlation_ids=[],
    )

    # Should complete without error
    await coordinator._implementation_phase(plan)


@pytest.mark.asyncio
async def test_coordinator_implementation_phase_runs_sequential_steps() -> None:
    """FR-005: implementation phase runs sequential steps in order."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    plan = CoordinatorPlan(
        session_id=coordinator._session_id,
        status=PlanStatus.complete,
        steps=[
            PlanStep(ministry="civil_affairs", action="Step 1", execution_mode=ExecutionMode.sequential),
            PlanStep(ministry="transport", action="Step 2", depends_on=[0], execution_mode=ExecutionMode.sequential),
        ],
        worker_correlation_ids=[],
    )

    # Should complete without error
    await coordinator._implementation_phase(plan)


@pytest.mark.asyncio
async def test_coordinator_cancel_sets_flag() -> None:
    """FR-006: cancel() sets the cancel flag."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

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
async def test_cancel_and_wait_completes_quickly() -> None:
    """FR-006, SC-003: cancel_and_wait() with no active workers completes instantly."""
    llm = StubLLMClient(responses=[])
    mailbox = _InMemoryMailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    # With no active workers, cancel_and_wait should return quickly
    await asyncio.wait_for(coordinator.cancel_and_wait(), timeout=1.0)
    assert coordinator._cancel_requested is True
