# SPDX-License-Identifier: Apache-2.0
"""Test T035 — FR-019, SC-005: crash-replay integration.

Places a pre-written result JSON in a tmp session directory, starts a fresh
FileMailbox instance, asserts:
- The message is read in FIFO order
- Deserialized correctly (full roundtrip fidelity)
- Marked consumed after replay
- NOT re-delivered on a second replay (consumed marker prevents replay)
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from kosmos.agents.mailbox.file_mailbox import FileMailbox
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
)
from kosmos.tools.models import LookupMeta, LookupRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_message_file(sender_dir: Path, msg: AgentMessage, ts_ns: int) -> Path:
    """Write a pre-serialized message file as if placed by a prior run."""
    sender_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    filename = f"{ts_ns:020d}-{msg.id}.json"
    dest = sender_dir / filename
    payload = msg.model_dump_json().encode("utf-8")
    fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    return dest


def _make_result_msg(sender: str, recipient: str) -> AgentMessage:
    meta = LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=3,
    )
    record = LookupRecord(kind="record", item={"data": "crash-replay"}, meta=meta)
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        msg_type=MessageType.result,
        payload=ResultPayload(lookup_output=record, turn_count=1),
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crash_replay_reads_pre_written_message(tmp_path: Path) -> None:
    """FR-019: A fresh FileMailbox reads messages written by a prior run."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-a"

    # Simulate prior run: write message without using FileMailbox
    original = _make_result_msg(sender="worker-a", recipient="coordinator")
    ts = time.time_ns()
    _write_message_file(sender_dir, original, ts)

    # Ensure session dir has correct mode (FileMailbox expects it or creates it)
    session_dir.chmod(0o700)

    # Fresh FileMailbox — simulates a coordinator restart
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    replayed: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        replayed.append(msg)

    assert len(replayed) == 1, f"Expected 1 replayed message, got {len(replayed)}"
    recovered = replayed[0]
    assert recovered.id == original.id
    assert recovered.sender == original.sender
    assert recovered.recipient == original.recipient
    assert recovered.msg_type == original.msg_type
    assert recovered.correlation_id == original.correlation_id


@pytest.mark.asyncio
async def test_crash_replay_consumed_marker_written(tmp_path: Path) -> None:
    """FR-019: replay writes consumed marker so message is not re-delivered."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-b"

    original = _make_result_msg(sender="worker-b", recipient="coordinator")
    ts = time.time_ns()
    msg_file = _write_message_file(sender_dir, original, ts)
    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # First replay — yields message
    first_batch: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        first_batch.append(msg)
    assert len(first_batch) == 1

    # Consumed marker must now exist
    consumed_marker = msg_file.parent / (msg_file.name + ".consumed")
    assert consumed_marker.exists(), (
        f"Consumed marker {consumed_marker} must exist after replay"
    )


@pytest.mark.asyncio
async def test_crash_replay_no_redelivery_on_second_restart(tmp_path: Path) -> None:
    """SC-005: consumed message is not re-delivered on second coordinator restart."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-c"

    original = _make_result_msg(sender="worker-c", recipient="coordinator")
    ts = time.time_ns()
    _write_message_file(sender_dir, original, ts)
    session_dir.chmod(0o700)

    # First coordinator run — replays and consumes
    mailbox1 = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)
    first_batch: list[AgentMessage] = []
    async for msg in mailbox1.replay_unread("coordinator"):
        first_batch.append(msg)
    assert len(first_batch) == 1

    # Second coordinator run — fresh FileMailbox, same session_id
    mailbox2 = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)
    second_batch: list[AgentMessage] = []
    async for msg in mailbox2.replay_unread("coordinator"):
        second_batch.append(msg)

    assert len(second_batch) == 0, (
        f"SC-005: consumed message must not re-deliver on second coordinator restart; "
        f"got {len(second_batch)} messages"
    )


@pytest.mark.asyncio
async def test_crash_replay_fifo_order_preserved(tmp_path: Path) -> None:
    """FR-019: messages replayed in per-sender FIFO order (by timestamp filename prefix)."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-d"

    # Write 3 messages with ascending timestamps
    msgs = [_make_result_msg(sender="worker-d", recipient="coordinator") for _ in range(3)]
    for i, msg in enumerate(msgs):
        ts = 1000 + i  # ascending timestamps
        _write_message_file(sender_dir, msg, ts)

    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    replayed: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        replayed.append(msg)

    assert len(replayed) == 3
    # Must arrive in timestamp-ascending order (FIFO)
    assert [m.id for m in replayed] == [m.id for m in msgs], (
        "FR-019: per-sender FIFO order must match write order"
    )
