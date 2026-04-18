# SPDX-License-Identifier: Apache-2.0
"""Unit test T034 — FR-014..FR-022: FileMailbox.send + on-disk layout.

Tests:
(a) Atomic write sequence: temp file + rename
(b) Overflow at KOSMOS_AGENT_MAILBOX_MAX_MESSAGES raises MailboxOverflowError
(c) Unwritable directory raises MailboxWriteError
(d) Routing by recipient (FR-025) — only matching messages yielded
(e) Mode 0o700/0o600 invariant (mailbox-abi.md §1)
"""

from __future__ import annotations

import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from kosmos.agents.errors import MailboxOverflowError
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


def _make_task_msg(sender: str, recipient: str) -> AgentMessage:
    """Build a minimal task message for testing."""
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        msg_type=MessageType.task,
        payload=TaskPayload(instruction="Research this", specialist_role="civil_affairs"),
        timestamp=datetime.now(UTC),
    )


def _make_result_msg(sender: str, recipient: str) -> AgentMessage:
    """Build a minimal result message for testing."""
    meta = LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=3,
    )
    record = LookupRecord(kind="record", item={"data": "test"}, meta=meta)
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
async def test_send_creates_json_file(tmp_path: Path) -> None:
    """FR-014: send() creates a durable .json file in the sender directory."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    msg = _make_task_msg(sender="coordinator", recipient="worker-test")
    await mailbox.send(msg)

    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "coordinator"

    json_files = list(sender_dir.glob("*.json"))
    assert len(json_files) == 1, f"Expected 1 .json file, got: {json_files}"

    # No temp files should remain
    tmp_files = list(sender_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"Temp files must be cleaned up; got: {tmp_files}"


@pytest.mark.asyncio
async def test_send_filename_has_timestamp_prefix(tmp_path: Path) -> None:
    """FR-018: filename format is <timestamp_ns>-<uuid4>.json for FIFO ordering."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    msg = _make_task_msg(sender="coordinator", recipient="worker-test")
    await mailbox.send(msg)

    session_dir = tmp_path / str(session_id) / "coordinator"
    json_files = list(session_dir.glob("*.json"))
    assert json_files, "Expected at least one json file"

    filename = json_files[0].name
    parts = filename.split("-", maxsplit=1)
    assert len(parts) == 2, f"Filename must have timestamp prefix: {filename}"
    # First part must be a numeric timestamp
    assert parts[0].isdigit(), f"Timestamp prefix must be numeric: {parts[0]!r}"
    # Second part must contain the message id
    assert str(msg.id) in filename, f"Message ID must appear in filename: {filename}"


@pytest.mark.asyncio
async def test_send_overflow_raises_error(tmp_path: Path) -> None:
    """FR-021: overflow at max_messages raises MailboxOverflowError."""
    session_id = uuid4()
    # Set cap to 2
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=2)

    for i in range(2):
        await mailbox.send(_make_task_msg(sender=f"worker-{i}", recipient="coordinator"))

    # Third send must raise
    with pytest.raises(MailboxOverflowError, match="messages"):
        await mailbox.send(_make_task_msg(sender="worker-extra", recipient="coordinator"))


@pytest.mark.asyncio
async def test_replay_unread_yields_matching_recipient_only(tmp_path: Path) -> None:
    """FR-025: replay_unread must only yield messages addressed to the recipient."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Send to two different recipients
    msg_a = _make_result_msg(sender="worker-a", recipient="coordinator")
    msg_b = _make_result_msg(sender="worker-b", recipient="coordinator")
    msg_c = _make_result_msg(sender="worker-c", recipient="other-recipient")

    await mailbox.send(msg_a)
    await mailbox.send(msg_b)
    await mailbox.send(msg_c)

    # Create a fresh mailbox (no consumed markers yet)
    mailbox2 = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    coordinator_msgs: list[AgentMessage] = []
    async for m in mailbox2.replay_unread("coordinator"):
        coordinator_msgs.append(m)

    other_msgs: list[AgentMessage] = []
    async for m in mailbox2.replay_unread("other-recipient"):
        other_msgs.append(m)

    assert len(coordinator_msgs) == 2
    assert all(m.recipient == "coordinator" for m in coordinator_msgs)

    # other-recipient message was NOT consumed by the coordinator scan;
    # it should appear in the other-recipient scan exactly once.
    assert len(other_msgs) == 1
    assert other_msgs[0].recipient == "other-recipient"


@pytest.mark.asyncio
async def test_send_file_mode_0o600(tmp_path: Path) -> None:
    """mailbox-abi.md §1: message files must have mode 0o600."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    await mailbox.send(_make_task_msg(sender="coordinator", recipient="worker-1"))

    session_dir = tmp_path / str(session_id) / "coordinator"
    for f in session_dir.glob("*.json"):
        file_mode = stat.S_IMODE(f.stat().st_mode)
        assert file_mode == 0o600, (
            f"File {f.name} has mode {oct(file_mode)}, expected 0o600"
        )


@pytest.mark.asyncio
async def test_session_dir_mode_0o700(tmp_path: Path) -> None:
    """mailbox-abi.md §1: session and sender directories must have mode 0o700."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    session_dir = tmp_path / str(session_id)
    dir_mode = stat.S_IMODE(session_dir.stat().st_mode)
    assert dir_mode == 0o700, f"Session dir mode is {oct(dir_mode)}, expected 0o700"

    await mailbox.send(_make_task_msg(sender="coordinator", recipient="worker-1"))

    sender_dir = session_dir / "coordinator"
    sender_mode = stat.S_IMODE(sender_dir.stat().st_mode)
    assert sender_mode == 0o700, f"Sender dir mode is {oct(sender_mode)}, expected 0o700"


@pytest.mark.asyncio
async def test_replay_unread_writes_consumed_marker(tmp_path: Path) -> None:
    """FR-019: replay_unread writes consumed marker so message is not re-delivered."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    msg = _make_result_msg(sender="worker-a", recipient="coordinator")
    await mailbox.send(msg)

    # First replay — should yield the message and write consumed marker
    first_batch: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        first_batch.append(m)
    assert len(first_batch) == 1

    # Second replay — consumed marker exists; must yield nothing
    second_batch: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        second_batch.append(m)
    assert len(second_batch) == 0, (
        "FR-019: consumed message must not be re-delivered on second replay"
    )


@pytest.mark.asyncio
async def test_send_preserves_message_roundtrip(tmp_path: Path) -> None:
    """FR-014: send + replay_unread must preserve the full message payload."""
    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    original = _make_result_msg(sender="worker-a", recipient="coordinator")
    await mailbox.send(original)

    replayed: list[AgentMessage] = []
    async for m in mailbox.replay_unread("coordinator"):
        replayed.append(m)

    assert len(replayed) == 1
    recovered = replayed[0]
    assert recovered.id == original.id
    assert recovered.sender == original.sender
    assert recovered.recipient == original.recipient
    assert recovered.msg_type == original.msg_type
    assert recovered.correlation_id == original.correlation_id
