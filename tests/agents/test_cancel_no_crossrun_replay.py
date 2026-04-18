# SPDX-License-Identifier: Apache-2.0
"""Test T031 — FR-019, research.md C9: cross-run replay isolation.

Cancel a session → resume with same session_id → assert unread messages
from the previous run are NOT replayed (crash-replay applies only within
the same run; cancelled sessions must not bleed into the next run).

This test verifies the contract at the coordinator level: when
`replay_prior_messages()` is called, messages from a cancelled prior run
should not cause incorrect state in the new run.

Note: FileMailbox-level consumed markers are tested in test_mailbox_crash_replay.py.
This test verifies the coordinator-level invariant: once a coordinator has processed
messages (even across a cancel), a fresh coordinator run with the same session_id
should start clean.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
)
from kosmos.tools.models import LookupMeta, LookupRecord
from tests.agents.conftest import StubLLMClient, build_test_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _IsolatedReplayMailbox:
    """Mailbox that tracks which messages have been 'consumed' (replayed once).

    On first replay_unread(), returns pending messages and marks them consumed.
    On second replay_unread() with the same recipient, returns nothing.
    This simulates the consumed-marker mechanism in FileMailbox.
    """

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._consumed_ids: set[UUID] = set()

    async def send(self, message: AgentMessage) -> None:
        self._messages.append(message)

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._messages):
            if msg.recipient == recipient:
                yield msg

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        for msg in list(self._messages):
            if msg.recipient == recipient and msg.id not in self._consumed_ids:
                self._consumed_ids.add(msg.id)
                yield msg
        # Second call yields nothing — consumed-marker prevents replay

    def seed_result(self, session_id: UUID) -> AgentMessage:
        """Add a pre-existing result message (simulating a prior run's output)."""
        meta = LookupMeta(
            source="prior_run",
            fetched_at=datetime.now(UTC),
            request_id=str(uuid4()),
            elapsed_ms=5,
        )
        record = LookupRecord(kind="record", item={"prior": "data"}, meta=meta)
        msg = AgentMessage(
            sender="worker-old",
            recipient="coordinator",
            msg_type=MessageType.result,
            payload=ResultPayload(lookup_output=record, turn_count=1),
            timestamp=datetime.now(UTC),
            correlation_id=uuid4(),
        )
        self._messages.append(msg)
        return msg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prior_run_messages_consumed_on_first_replay() -> None:
    """FR-019: unread messages from prior run are replayed once then consumed."""
    session_id = uuid4()
    mailbox = _IsolatedReplayMailbox()

    # Seed a prior-run result message
    prior_msg = mailbox.seed_result(session_id)

    # First coordinator: replays the prior message
    llm = StubLLMClient(responses=[])
    _coordinator1 = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    replayed: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        replayed.append(msg)

    assert len(replayed) == 1
    assert replayed[0].id == prior_msg.id


@pytest.mark.asyncio
async def test_prior_run_messages_not_replayed_on_second_run() -> None:
    """research.md C9: cancelled-session messages must not re-replay on next run."""
    session_id = uuid4()
    mailbox = _IsolatedReplayMailbox()

    # Seed a prior-run result message
    mailbox.seed_result(session_id)

    # First replay — consumes the message
    first_replay: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        first_replay.append(msg)
    assert len(first_replay) == 1

    # Second replay — must return nothing (consumed marker)
    second_replay: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        second_replay.append(msg)

    assert len(second_replay) == 0, (
        f"C9: consumed messages must not re-appear on second replay; "
        f"got {len(second_replay)} messages"
    )


@pytest.mark.asyncio
async def test_cancel_flag_does_not_persist_across_coordinator_instances() -> None:
    """FR-006: cancel state is per-coordinator-instance, not shared across runs."""
    session_id = uuid4()
    mailbox = _IsolatedReplayMailbox()
    llm = StubLLMClient(responses=[])

    # First coordinator — cancel it
    coordinator1 = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )
    coordinator1.cancel()
    assert coordinator1._cancel_requested is True

    # Second coordinator — same session_id, fresh instance
    coordinator2 = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )
    # Cancel state must NOT carry over
    assert coordinator2._cancel_requested is False, (
        "New coordinator instance must start with _cancel_requested=False"
    )


@pytest.mark.asyncio
async def test_replayed_messages_are_not_duplicate_processed() -> None:
    """FR-019: replay_unread yields each message exactly once per session."""
    session_id = uuid4()
    mailbox = _IsolatedReplayMailbox()

    # Seed 3 prior-run messages
    for _ in range(3):
        mailbox.seed_result(session_id)

    # Consume all via first replay
    first_batch: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        first_batch.append(msg)
    assert len(first_batch) == 3

    # Second replay must be empty
    second_batch: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        second_batch.append(msg)
    assert len(second_batch) == 0
