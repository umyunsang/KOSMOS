# SPDX-License-Identifier: Apache-2.0
"""Test T037 — FR-018: per-sender FIFO ordering.

Two senders, multiple messages each, assert per-sender FIFO holds by
<timestamp_ns>-<uuid4>.json filename sort order.

FR-018: "Filenames sort lexicographically in write order for each sender."
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from kosmos.agents.mailbox.file_mailbox import FileMailbox
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
    TaskPayload,
)
from kosmos.tools.models import LookupMeta, LookupRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result_msg(sender: str, recipient: str, label: str = "") -> AgentMessage:
    meta = LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=1,
    )
    record = LookupRecord(kind="record", item={"label": label}, meta=meta)
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        msg_type=MessageType.result,
        payload=ResultPayload(lookup_output=record, turn_count=1),
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )


def _make_task_msg(sender: str, recipient: str) -> AgentMessage:
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        msg_type=MessageType.task,
        payload=TaskPayload(instruction="Do something", specialist_role="civil_affairs"),
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_sender_fifo_order(tmp_path: Path) -> None:
    """FR-018: messages from a single sender are replayed in send order."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Send 5 messages in sequence
    msgs = [
        _make_result_msg(sender="worker-a", recipient="coordinator", label=f"msg-{i}")
        for i in range(5)
    ]
    for msg in msgs:
        await mailbox.send(msg)
        # Small delay to ensure distinct timestamp_ns values
        await asyncio.sleep(0)

    replayed: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        replayed.append(m)

    assert len(replayed) == 5
    # Must arrive in send order
    assert [m.id for m in replayed] == [m.id for m in msgs], (
        "FR-018: single-sender FIFO order violated"
    )


@pytest.mark.asyncio
async def test_two_senders_per_sender_fifo(tmp_path: Path) -> None:
    """FR-018: per-sender FIFO holds for two concurrent senders."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Sender A: 3 messages
    msgs_a = [
        _make_result_msg(sender="worker-a", recipient="coordinator", label=f"a-{i}")
        for i in range(3)
    ]
    # Sender B: 3 messages
    msgs_b = [
        _make_result_msg(sender="worker-b", recipient="coordinator", label=f"b-{i}")
        for i in range(3)
    ]

    # Interleave sends: a0, b0, a1, b1, a2, b2
    for i in range(3):
        await mailbox.send(msgs_a[i])
        await mailbox.send(msgs_b[i])

    replayed: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        replayed.append(m)

    assert len(replayed) == 6

    # Per-sender FIFO: extract messages from each sender in replay order
    a_replayed = [m for m in replayed if m.sender == "worker-a"]
    b_replayed = [m for m in replayed if m.sender == "worker-b"]

    assert len(a_replayed) == 3
    assert len(b_replayed) == 3

    # Check FIFO for each sender independently
    assert [m.id for m in a_replayed] == [m.id for m in msgs_a], (
        "FR-018: worker-a FIFO order violated"
    )
    assert [m.id for m in b_replayed] == [m.id for m in msgs_b], (
        "FR-018: worker-b FIFO order violated"
    )


@pytest.mark.asyncio
async def test_fifo_filename_sort_is_lexicographic(tmp_path: Path) -> None:
    """FR-018: <timestamp_ns>-<uuid4>.json files sort lexicographically in write order."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Send 3 messages and collect their filenames
    msgs = [
        _make_result_msg(sender="worker-c", recipient="coordinator", label=f"c-{i}")
        for i in range(3)
    ]
    for msg in msgs:
        await mailbox.send(msg)

    sender_dir = tmp_path / str(session_id) / "worker-c"
    json_files = sorted([f.name for f in sender_dir.glob("*.json")])

    # Verify lexicographic sort == write order by checking message IDs in files
    import json as json_mod

    file_ids = []
    for fname in json_files:
        raw = (sender_dir / fname).read_bytes()
        data = json_mod.loads(raw)
        file_ids.append(data["id"])

    expected_ids = [str(m.id) for m in msgs]
    assert file_ids == expected_ids, (
        f"FR-018: lexicographic filename sort must match write order\n"
        f"  filenames: {json_files}\n"
        f"  file_ids: {file_ids}\n"
        f"  expected: {expected_ids}"
    )


@pytest.mark.asyncio
async def test_fifo_across_multiple_sends_same_sender(tmp_path: Path) -> None:
    """FR-018: FIFO holds even after many sends from the same sender."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    n = 10
    msgs = [
        _make_result_msg(sender="worker-many", recipient="coordinator", label=f"m-{i}")
        for i in range(n)
    ]
    for msg in msgs:
        await mailbox.send(msg)

    replayed: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        replayed.append(m)

    assert len(replayed) == n
    assert [m.id for m in replayed] == [m.id for m in msgs], (
        f"FR-018: FIFO violated for {n}-message sequence"
    )


@pytest.mark.asyncio
async def test_mixed_recipients_fifo_per_sender(tmp_path: Path) -> None:
    """FR-018 + FR-025: per-sender FIFO holds independently for each recipient."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Coordinator-bound messages from worker-d
    coord_msgs = [
        _make_result_msg(sender="worker-d", recipient="coordinator", label=f"coord-{i}")
        for i in range(3)
    ]
    # Other-recipient messages from worker-d (same sender dir)
    other_msgs = [
        _make_result_msg(sender="worker-d", recipient="other-agent", label=f"other-{i}")
        for i in range(2)
    ]

    # Interleave
    for i in range(2):
        await mailbox.send(coord_msgs[i])
        await mailbox.send(other_msgs[i])
    await mailbox.send(coord_msgs[2])

    # Replay for coordinator only
    coord_replayed: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        coord_replayed.append(m)

    assert len(coord_replayed) == 3
    assert [m.id for m in coord_replayed] == [m.id for m in coord_msgs], (
        "FR-018: coordinator-bound FIFO violated when mixed with other-recipient messages"
    )
