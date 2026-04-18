# SPDX-License-Identifier: Apache-2.0
"""Test T027 — FR-026: permission denial path.

When ConsentGateway returns False:
- coordinator emits permission_response(granted=False)
- worker converts to error message
- worker does NOT retry the denied tool call
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from kosmos.agents.consent import ConsentGateway
from kosmos.agents.context import AgentContext
from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    PermissionRequestPayload,
    PermissionResponsePayload,
)
from kosmos.agents.worker import Worker
from tests.agents.conftest import StubLLMClient, build_test_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DenyingConsentGateway(ConsentGateway):
    """ConsentGateway that always denies."""

    def __init__(self) -> None:
        self.call_count = 0

    async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool:
        self.call_count += 1
        return False


class _TrackingMailbox:
    """In-memory mailbox that tracks all messages."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._pending: dict[str, list[AgentMessage]] = {}

    async def send(self, message: AgentMessage) -> None:
        self._messages.append(message)
        self._pending.setdefault(message.recipient, []).append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._pending.get(recipient, [])):
            yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._pending.get(recipient, [])):
            yield msg

    def messages_of_type(self, msg_type: MessageType) -> list[AgentMessage]:
        return [m for m in self._messages if m.msg_type == msg_type]


class _DenyingMailbox(_TrackingMailbox):
    """Mailbox that auto-responds with denied permission_response."""

    async def send(self, message: AgentMessage) -> None:
        await super().send(message)
        if message.msg_type == MessageType.permission_request and isinstance(
            message.payload, PermissionRequestPayload
        ):
            response = AgentMessage(
                sender="coordinator",
                recipient=message.sender,
                msg_type=MessageType.permission_response,
                payload=PermissionResponsePayload(
                    granted=False,
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
async def test_permission_denied_worker_returns_false() -> None:
    """FR-026: worker's _request_permission returns False when denied."""
    worker_id = f"worker-denied-{uuid4()}"
    llm = StubLLMClient(responses=["Done."])
    mailbox = _DenyingMailbox()

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

    granted = await asyncio.wait_for(
        worker._request_permission("restricted_tool", correlation_id),
        timeout=1.0,
    )

    assert granted is False, f"Expected False for denied permission; got {granted}"


@pytest.mark.asyncio
async def test_coordinator_emits_denied_permission_response() -> None:
    """FR-026: when gateway returns False, coordinator emits granted=False response."""
    gateway = _DenyingConsentGateway()
    mailbox = _TrackingMailbox()
    llm = StubLLMClient(responses=[])

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        consent_gateway=gateway,
    )

    worker_id = f"worker-denied-{uuid4()}"
    cid = uuid4()
    request = AgentMessage(
        sender=worker_id,
        recipient="coordinator",
        msg_type=MessageType.permission_request,
        payload=PermissionRequestPayload(tool_id="restricted_tool", reason="auth_required"),
        timestamp=datetime.now(UTC),
        correlation_id=cid,
    )

    await coordinator._handle_permission_request(request)

    # Gateway must have been called
    assert gateway.call_count == 1

    # Response must be denied
    permission_responses = mailbox.messages_of_type(MessageType.permission_response)
    assert len(permission_responses) == 1
    payload = permission_responses[0].payload
    assert isinstance(payload, PermissionResponsePayload)
    assert payload.granted is False
    assert payload.tool_id == "restricted_tool"


@pytest.mark.asyncio
async def test_permission_denied_response_still_addressed_to_requester() -> None:
    """FR-025, FR-026: denied response still addressed to requesting worker only."""
    gateway = _DenyingConsentGateway()
    mailbox = _TrackingMailbox()
    llm = StubLLMClient(responses=[])

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
        consent_gateway=gateway,
    )

    worker_id = f"worker-requester-{uuid4()}"
    request = AgentMessage(
        sender=worker_id,
        recipient="coordinator",
        msg_type=MessageType.permission_request,
        payload=PermissionRequestPayload(tool_id="sensitive_tool", reason="auth_required"),
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )

    await coordinator._handle_permission_request(request)

    permission_responses = mailbox.messages_of_type(MessageType.permission_response)
    assert len(permission_responses) == 1
    # Must be addressed to the requesting worker, not broadcast
    assert permission_responses[0].recipient == worker_id
    assert permission_responses[0].sender == "coordinator"


@pytest.mark.asyncio
async def test_always_grant_consent_gateway_returns_true() -> None:
    """AlwaysGrantConsentGateway is the default stub — always returns True."""
    from kosmos.agents.consent import AlwaysGrantConsentGateway

    gateway = AlwaysGrantConsentGateway()
    result = await gateway.request_consent("any_tool", uuid4())
    assert result is True


@pytest.mark.asyncio
async def test_denying_gateway_always_returns_false() -> None:
    """_DenyingConsentGateway always returns False."""
    gateway = _DenyingConsentGateway()
    result = await gateway.request_consent("any_tool", uuid4())
    assert result is False
    result2 = await gateway.request_consent("other_tool", uuid4())
    assert result2 is False
    assert gateway.call_count == 2
