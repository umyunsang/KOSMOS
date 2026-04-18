# SPDX-License-Identifier: Apache-2.0
"""Test T036 — FR-020, spec Edge Case: corruption tolerance.

Writes a truncated .json file (simulating a crash mid-write) and asserts
that replay_unread logs a WARNING and continues with remaining valid
messages without raising an exception.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, UTC
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


def _make_result_msg(sender: str, recipient: str) -> AgentMessage:
    meta = LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=3,
    )
    record = LookupRecord(kind="record", item={"data": "valid"}, meta=meta)
    return AgentMessage(
        sender=sender,
        recipient=recipient,
        msg_type=MessageType.result,
        payload=ResultPayload(lookup_output=record, turn_count=1),
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )


def _write_truncated_file(sender_dir: Path, ts_ns: int) -> Path:
    """Write a .json file with truncated/invalid JSON content."""
    sender_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    corrupt_id = uuid4()
    filename = f"{ts_ns:020d}-{corrupt_id}.json"
    dest = sender_dir / filename
    truncated = b'{"sender": "worker-x", "recipient": "coordinator", "msg_type":'  # truncated
    fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, truncated)
        os.fsync(fd)
    finally:
        os.close(fd)
    return dest


def _write_valid_msg_file(sender_dir: Path, msg: AgentMessage, ts_ns: int) -> Path:
    """Write a valid message file directly."""
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corrupt_file_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """FR-020: replay_unread skips corrupt file, logs WARNING, continues."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-x"

    # Write a corrupted file (timestamp 100)
    _write_truncated_file(sender_dir, ts_ns=100)
    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    with caplog.at_level(logging.WARNING, logger="kosmos.agents.mailbox.file_mailbox"):
        replayed: list[AgentMessage] = []
        async for msg in mailbox.replay_unread("coordinator"):
            replayed.append(msg)

    # No messages yielded (only corrupt file exists)
    assert len(replayed) == 0, f"Expected 0 messages from corrupt-only mailbox; got {len(replayed)}"

    # WARNING must have been logged
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) >= 1, (
        "FR-020: corrupt file must cause a WARNING log in replay_unread"
    )


@pytest.mark.asyncio
async def test_corrupt_file_does_not_raise(tmp_path: Path) -> None:
    """FR-020: replay_unread must not raise even if a file is corrupt."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-y"

    _write_truncated_file(sender_dir, ts_ns=200)
    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    # Must complete without exception
    async for _ in mailbox.replay_unread("coordinator"):
        pass


@pytest.mark.asyncio
async def test_corrupt_file_skipped_valid_message_still_delivered(
    tmp_path: Path,
) -> None:
    """FR-020 + spec Edge Case: corrupt file is skipped; valid files are delivered."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-z"

    # Corrupt file (earlier timestamp)
    _write_truncated_file(sender_dir, ts_ns=300)

    # Valid message (later timestamp)
    valid_msg = _make_result_msg(sender="worker-z", recipient="coordinator")
    _write_valid_msg_file(sender_dir, valid_msg, ts_ns=400)

    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    replayed: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        replayed.append(msg)

    # Only the valid message should be yielded
    assert len(replayed) == 1, f"Expected 1 valid message; got {len(replayed)}"
    assert replayed[0].id == valid_msg.id


@pytest.mark.asyncio
async def test_empty_json_file_skipped(tmp_path: Path) -> None:
    """FR-020: zero-byte .json file is skipped with WARNING, no raise."""
    session_id = uuid4()
    session_dir = tmp_path / str(session_id)
    sender_dir = session_dir / "worker-empty"
    sender_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    empty_id = uuid4()
    empty_file = sender_dir / f"00000000000000000500-{empty_id}.json"
    fd = os.open(str(empty_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)  # Zero bytes

    session_dir.chmod(0o700)

    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=1000)

    replayed: list[AgentMessage] = []
    async for msg in mailbox.replay_unread("coordinator"):
        replayed.append(msg)

    assert len(replayed) == 0
