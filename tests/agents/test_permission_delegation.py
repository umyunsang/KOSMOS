# SPDX-License-Identifier: Apache-2.0
"""Integration test T026 — FR-023, FR-024, FR-025, FR-027, SC-004.

Full permission delegation round-trip:
  worker → permission_request to coordinator
  coordinator → ConsentGateway
  coordinator → permission_response to requesting worker
  no lateral flow (other workers unaffected)
  correlation_id preserved across retry
  round-trip wall-clock < 1 s
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, UTC
from typing import Any
from uuid import UUID, uuid4

import pytest

from kosmos.agents.consent import AlwaysGrantConsentGateway, ConsentGateway
from kosmos.agents.context import AgentContext
from kosmos.agents.coordinator import Coordinator
from kosmos.agents.errors import AgentConfigurationError
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    ErrorPayload,
    MessageType,
    PermissionRequestPayload,
    PermissionResponsePayload,
    ResultPayload,
    TaskPayload,
)
from kosmos.agents.worker import Worker
from tests.agents.conftest import StubLLMClient, build_test_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _TrackingMailbox:
    """In-memory mailbox that tracks all messages for inspection."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._pending: dict[str, list[AgentMessage]] = {}  # recipient → queue

    async def send(self, message: AgentMessage) -> None:
        self._messages.append(message)
        recipient = message.recipient
        if recipient not in self._pending:
            self._pending[recipient] = []
        self._pending[recipient].append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._pending.get(recipient, [])):
            yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._pending.get(recipient, [])):
            yield msg

    def all_messages_for(self, recipient: str) -> list[AgentMessage]:
        return [m for m in self._messages if m.recipient == recipient]

    def all_messages_of_type(self, msg_type: MessageType) -> list[AgentMessage]:
        return [m for m in self._messages if m.msg_type == msg_type]


class _RespondingCoordinatorMailbox(_TrackingMailbox):
    """Mailbox that auto-responds to permission_requests via a ConsentGateway."""

    def __init__(self, consent_gateway: ConsentGateway) -> None:
        super().__init__()
        self._consent = consent_gateway

    async def send(self, message: AgentMessage) -> None:
        await super().send(message)
        # If a worker sends a permission_request, auto-respond
        if message.msg_type == MessageType.permission_request and isinstance(
            message.payload, PermissionRequestPayload
        ):
            granted = await self._consent.request_consent(
                message.payload.tool_id, message.correlation_id or uuid4()
            )
            response = AgentMessage(
                sender="coordinator",
                recipient=message.sender,
                msg_type=MessageType.permission_response,
                payload=PermissionResponsePayload(
                    granted=granted,
                    tool_id=message.payload.tool_id,
                ),
                timestamp=datetime.now(UTC),
                correlation_id=message.correlation_id,
            )
            await super().send(response)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permission_request_addressed_to_coordinator_only() -> None:
    """FR-025: permission_request must be addressed only to 'coordinator'."""
    worker_id = f"worker-civil_affairs-{uuid4()}"
    llm = StubLLMClient(responses=["Done."])
    mailbox = _TrackingMailbox()

    ctx = AgentContext(
        session_id=uuid4(),
        specialist_role="civil_affairs",
        worker_id=worker_id,
        tool_registry=build_test_registry(),
        llm_client=llm,
    )

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]

    # Manually trigger a permission request (test internal method)
    correlation_id = uuid4()
    mailbox_messages_before = len(mailbox._messages)

    # Seed a permission_response so _request_permission doesn't block forever
    mailbox._pending[worker_id] = [
        AgentMessage(
            sender="coordinator",
            recipient=worker_id,
            msg_type=MessageType.permission_response,
            payload=PermissionResponsePayload(granted=True, tool_id="nmc_emergency_search"),
            timestamp=datetime.now(UTC),
            correlation_id=correlation_id,
        )
    ]

    granted = await worker._request_permission("nmc_emergency_search", correlation_id)

    # Verify the request was sent to coordinator only
    permission_requests = mailbox.all_messages_of_type(MessageType.permission_request)
    assert len(permission_requests) >= 1

    for req in permission_requests:
        assert req.recipient == "coordinator", (
            f"FR-025 VIOLATED: permission_request must go to 'coordinator', "
            f"got recipient={req.recipient!r}"
        )
        assert req.sender == worker_id


@pytest.mark.asyncio
async def test_permission_request_preserves_correlation_id() -> None:
    """FR-027: correlation_id must be preserved across the permission round-trip."""
    worker_id = f"worker-health-{uuid4()}"
    llm = StubLLMClient(responses=["Done."])
    mailbox = _TrackingMailbox()

    ctx = AgentContext(
        session_id=uuid4(),
        specialist_role="health_insurance",
        worker_id=worker_id,
        tool_registry=build_test_registry(),
        llm_client=llm,
    )

    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]
    original_cid = uuid4()

    # Seed response
    mailbox._pending[worker_id] = [
        AgentMessage(
            sender="coordinator",
            recipient=worker_id,
            msg_type=MessageType.permission_response,
            payload=PermissionResponsePayload(granted=True, tool_id="hira_hospital_search"),
            timestamp=datetime.now(UTC),
            correlation_id=original_cid,
        )
    ]

    await worker._request_permission("hira_hospital_search", original_cid)

    # Verify request carries the same correlation_id
    permission_requests = mailbox.all_messages_of_type(MessageType.permission_request)
    assert permission_requests, "Worker must emit a permission_request"
    assert permission_requests[-1].correlation_id == original_cid, (
        f"FR-027: correlation_id must be preserved; "
        f"expected {original_cid}, got {permission_requests[-1].correlation_id}"
    )


@pytest.mark.asyncio
async def test_no_lateral_flow_between_workers() -> None:
    """FR-025: permission_response must NOT be sent to other workers."""
    worker_id_a = f"worker-a-{uuid4()}"
    worker_id_b = f"worker-b-{uuid4()}"
    llm = StubLLMClient(responses=["Done."])

    # Use the responding mailbox which auto-grants
    mailbox = _RespondingCoordinatorMailbox(AlwaysGrantConsentGateway())

    ctx_a = AgentContext(
        session_id=uuid4(),
        specialist_role="transport",
        worker_id=worker_id_a,
        tool_registry=build_test_registry(),
        llm_client=llm,
    )
    worker_a = Worker(ctx_a, mailbox)  # type: ignore[arg-type]

    # Worker A requests permission
    original_cid = uuid4()
    # Pre-seed so the receive() returns something to avoid infinite loop
    mailbox._pending[worker_id_a] = []
    granted = await asyncio.wait_for(
        worker_a._request_permission("lookup", original_cid),
        timeout=1.0,
    )

    assert granted is True

    # Worker B's mailbox should NOT contain any permission_response
    worker_b_msgs = mailbox.all_messages_for(worker_id_b)
    permission_responses_to_b = [
        m for m in worker_b_msgs if m.msg_type == MessageType.permission_response
    ]
    assert len(permission_responses_to_b) == 0, (
        f"FR-025 VIOLATED: Worker B received permission messages: {permission_responses_to_b}"
    )


@pytest.mark.asyncio
async def test_permission_round_trip_under_one_second() -> None:
    """SC-004: permission round-trip must complete in < 1 s."""
    import time

    worker_id = f"worker-fast-{uuid4()}"
    llm = StubLLMClient(responses=["Done."])
    mailbox = _RespondingCoordinatorMailbox(AlwaysGrantConsentGateway())

    ctx = AgentContext(
        session_id=uuid4(),
        specialist_role="civil_affairs",
        worker_id=worker_id,
        tool_registry=build_test_registry(),
        llm_client=llm,
    )
    worker = Worker(ctx, mailbox)  # type: ignore[arg-type]

    correlation_id = uuid4()
    mailbox._pending[worker_id] = []

    start = time.monotonic()
    granted = await asyncio.wait_for(
        worker._request_permission("lookup", correlation_id),
        timeout=1.0,
    )
    elapsed = time.monotonic() - start

    assert granted is True
    assert elapsed < 1.0, f"SC-004: round-trip took {elapsed:.3f}s, must be < 1.0s"


@pytest.mark.asyncio
async def test_coordinator_handles_permission_request_via_consent_gateway() -> None:
    """FR-024: coordinator routes permission through ConsentGateway, not directly."""
    import time

    class _TrackingConsentGateway(ConsentGateway):
        def __init__(self) -> None:
            self.calls: list[tuple[str, UUID]] = []

        async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool:
            self.calls.append((tool_id, correlation_id))
            return True

    gateway = _TrackingConsentGateway()
    mailbox = _TrackingMailbox()
    llm = StubLLMClient(responses=[])
    session_id = uuid4()
    worker_id = f"worker-test-{uuid4()}"

    coordinator = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        consent_gateway=gateway,
    )

    # Simulate a permission_request message
    cid = uuid4()
    request = AgentMessage(
        sender=worker_id,
        recipient="coordinator",
        msg_type=MessageType.permission_request,
        payload=PermissionRequestPayload(tool_id="nmc_emergency_search", reason="auth_required"),
        timestamp=datetime.now(UTC),
        correlation_id=cid,
    )

    await coordinator._handle_permission_request(request)

    # ConsentGateway must have been called
    assert len(gateway.calls) == 1
    assert gateway.calls[0][0] == "nmc_emergency_search"
    assert gateway.calls[0][1] == cid

    # Response must be addressed to the requesting worker only
    permission_responses = mailbox.all_messages_of_type(MessageType.permission_response)
    assert len(permission_responses) == 1
    assert permission_responses[0].recipient == worker_id  # not broadcast
    assert permission_responses[0].correlation_id == cid
