# SPDX-License-Identifier: Apache-2.0
"""FileMailbox — crash-resilient, at-least-once file-based mailbox.

Implements the Mailbox ABC for the coordinator ↔ worker IPC path.

On-disk layout (per mailbox-abi.md §1):

    $KOSMOS_AGENT_MAILBOX_ROOT/
    └── <session_id>/                   # mode 0o700
        ├── coordinator/                # mode 0o700
        │   ├── <msg_id>.json           # mode 0o600
        │   ├── <msg_id>.json.consumed  # mode 0o600 — consumed marker
        │   └── ...
        └── worker-<role>-<uuid4>/      # mode 0o700
            └── ...

Filename format: `<timestamp_ns>-<uuid4>.json` — alphabetical == write-order
(per-sender FIFO contract, FR-018).

Write protocol (mailbox-abi.md §2):
    tmp   = sender_dir / f"{message.id}.json.tmp"
    final = sender_dir / f"{message.id}.json"
    Step A: overflow check
    Step B: write to tmp, fsync(fd), close
    Step C: rename(tmp, final)
    Step D: fsync(sender_dir)

Consumption marker (mailbox-abi.md §3) — T039.

FR traces: FR-014..FR-022.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from opentelemetry import trace

from kosmos.agents.errors import MailboxOverflowError, MailboxWriteError
from kosmos.agents.mailbox.base import Mailbox
from kosmos.agents.mailbox.messages import AgentMessage
from kosmos.observability.semconv import (
    KOSMOS_AGENT_MAILBOX_CORRELATION_ID,
    KOSMOS_AGENT_MAILBOX_MSG_TYPE,
    KOSMOS_AGENT_MAILBOX_RECIPIENT,
    KOSMOS_AGENT_MAILBOX_SENDER,
)

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)

# Suffix used by the write-temp protocol
_TMP_SUFFIX = ".json.tmp"
# Suffix used for consumed markers
_CONSUMED_SUFFIX = ".json.consumed"
# Suffix for consumed marker temp files
_CONSUMED_TMP_SUFFIX = ".json.consumed.tmp"


def _ensure_dir(path: Path) -> None:
    """Create a directory with mode 0o700, no-op if already exists."""
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise MailboxWriteError(f"Cannot create mailbox directory {path}: {exc}") from exc


def _sender_dir(session_dir: Path, sender: str) -> Path:
    """Return (and create) the sender directory within a session."""
    d = session_dir / sender
    _ensure_dir(d)
    return d


def _count_json_files(session_dir: Path) -> int:
    """Count all *.json message files (not .consumed) across all sender dirs."""
    total = 0
    try:
        for sender_dir in session_dir.iterdir():
            if sender_dir.is_dir():
                for f in sender_dir.iterdir():
                    if f.suffix == ".json" and not f.name.endswith(_CONSUMED_SUFFIX):
                        total += 1
    except OSError:
        pass
    return total


def _fsync_file_and_dir(file_path: Path) -> None:
    """Fsync a file then its parent directory (mailbox-abi.md §2).

    This is the blocking portion; callers wrap it in asyncio.to_thread().
    """
    # Fsync the file itself
    fd = os.open(str(file_path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

    # Fsync the parent directory so the directory entry is durable
    dir_fd = os.open(str(file_path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _atomic_write(dest: Path, payload: bytes) -> None:
    """Perform the temp-write → fsync → rename → fsync(dir) sequence.

    Blocking; callers must use asyncio.to_thread() to avoid blocking the loop.
    """
    tmp = dest.parent / (dest.name + ".tmp")

    # Step B: write to temp file with exclusive create (O_EXCL)
    fd = os.open(
        str(tmp),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)

    # Step C: atomic rename
    os.rename(str(tmp), str(dest))

    # Step D: fsync directory
    dir_fd = os.open(str(dest.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _write_consumed_marker(message_path: Path) -> None:
    """Write the .consumed marker for a message file (mailbox-abi.md §3).

    Blocking; callers must use asyncio.to_thread().

    The marker is a zero-byte file: `<message_id>.json.consumed`
    """
    marker_path = message_path.parent / (message_path.name + ".consumed")
    if marker_path.exists():
        return  # already marked

    tmp = message_path.parent / (marker_path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fsync(fd)  # Zero-byte file, just fsync the fd
    finally:
        os.close(fd)

    os.rename(str(tmp), str(marker_path))

    dir_fd = os.open(str(marker_path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


class FileMailbox(Mailbox):
    """File-based at-least-once mailbox per mailbox-abi.md.

    Args:
        session_id: UUID of the current session; determines the session subdirectory.
        root: Base directory for all mailbox files. Defaults to
              ``KOSMOS_AGENT_MAILBOX_ROOT`` from settings if not provided.
        max_messages: Per-session message cap. Defaults to
                      ``KOSMOS_AGENT_MAILBOX_MAX_MESSAGES`` from settings.
    """

    def __init__(
        self,
        session_id: UUID,
        *,
        root: Path | None = None,
        max_messages: int | None = None,
    ) -> None:
        from kosmos.settings import KosmosSettings  # local to avoid circular import

        _settings = KosmosSettings()
        self._session_id = session_id
        self._root: Path = root or _settings.agent_mailbox_root
        self._max_messages: int = max_messages or _settings.agent_mailbox_max_messages

        # Session directory: <root>/<session_id>/
        self._session_dir: Path = self._root / str(session_id)
        _ensure_dir(self._session_dir)

        logger.debug(
            "FileMailbox initialised: session_dir=%s max_messages=%d",
            self._session_dir,
            self._max_messages,
        )

    # ------------------------------------------------------------------
    # Mailbox ABC implementation
    # ------------------------------------------------------------------

    async def send(self, message: AgentMessage) -> None:
        """Deliver a message with at-least-once guarantee (mailbox-abi.md §2).

        Raises:
            MailboxOverflowError: per-session message cap exceeded.
            MailboxWriteError: filesystem write or fsync failure.
        """
        # Emit OTel span (mailbox-abi.md §7, FR-030)
        with _tracer.start_as_current_span("gen_ai.agent.mailbox.message") as span:
            span.set_attribute(KOSMOS_AGENT_MAILBOX_MSG_TYPE, message.msg_type.value)
            span.set_attribute(
                KOSMOS_AGENT_MAILBOX_CORRELATION_ID,
                str(message.correlation_id) if message.correlation_id else "",
            )
            span.set_attribute(KOSMOS_AGENT_MAILBOX_SENDER, message.sender)
            span.set_attribute(KOSMOS_AGENT_MAILBOX_RECIPIENT, message.recipient)
            # PIPA: message body is NEVER included as a span attribute.

        # Step A: overflow check
        current_count = await asyncio.to_thread(_count_json_files, self._session_dir)
        if current_count >= self._max_messages:
            raise MailboxOverflowError(
                f"Session {self._session_id}: at {current_count}/{self._max_messages} "
                "messages. Cannot send more without exceeding the cap."
            )

        # Determine sender directory for the message
        sender_dir = await asyncio.to_thread(_sender_dir, self._session_dir, message.sender)

        # Filename: <timestamp_ns>-<message_id>.json
        ts_ns = time.time_ns()
        filename = f"{ts_ns:020d}-{message.id}.json"
        dest = sender_dir / filename

        # Step B → D: atomic write via temp → fsync → rename → fsync(dir)
        payload = message.model_dump_json().encode("utf-8")
        try:
            await asyncio.to_thread(_atomic_write, dest, payload)
        except OSError as exc:
            raise MailboxWriteError(f"Failed to write mailbox message to {dest}: {exc}") from exc

        logger.debug(
            "FileMailbox.send: %s → %s (msg_type=%s, id=%s)",
            message.sender,
            message.recipient,
            message.msg_type.value,
            message.id,
        )

    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        """Yield unread messages addressed to recipient in per-sender FIFO order.

        This implementation scans the on-disk message files once and yields
        matching messages. It does not block indefinitely — callers should
        use asyncio.wait_for() for timeout semantics.
        """
        async for message in self.replay_unread(recipient):
            yield message

    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:  # noqa: C901
        """Yield unread messages and write consumed markers (mailbox-abi.md §4).

        Skips:
        - .tmp files (crash remnants)
        - .consumed files (already processed)
        - Files that fail JSON deserialization (FR-020 — log WARNING, continue)
        - Messages addressed to a different recipient (FR-025 routing)
        """
        try:
            sender_dirs = sorted(self._session_dir.iterdir())
        except OSError:
            return

        for sd in sender_dirs:
            if not sd.is_dir():
                continue

            try:
                files = sorted(sd.iterdir())
            except OSError:
                continue

            for path in files:
                # Skip non-.json files (.tmp, .consumed, .consumed.tmp)
                if path.suffix != ".json":
                    continue
                if path.name.endswith(".consumed"):
                    continue

                # Skip if consumed marker exists
                consumed_marker = path.parent / (path.name + ".consumed")
                if consumed_marker.exists():
                    continue

                # Parse the message
                try:
                    raw = await asyncio.to_thread(path.read_bytes)
                    message = AgentMessage.model_validate_json(raw)
                except Exception as exc:
                    logger.warning(
                        "FileMailbox.replay_unread: skipping corrupt file %s: %s",
                        path,
                        exc,
                    )
                    continue

                # FR-025: strict routing by recipient
                if message.recipient != recipient:
                    continue

                # Write consumed marker before yielding (at-least-once ack)
                try:
                    await asyncio.to_thread(_write_consumed_marker, path)
                except OSError as exc:
                    logger.warning(
                        "FileMailbox.replay_unread: failed to write consumed marker "
                        "for %s: %s — message will be re-delivered on next replay",
                        path,
                        exc,
                    )
                    # Yield anyway: at-least-once means we may re-deliver on crash
                    # The coordinator's duplicate-result handler is the idempotency guard.

                yield message

    # ------------------------------------------------------------------
    # T039: consumed-marker public helper
    # ------------------------------------------------------------------

    async def mark_consumed(self, message_id: UUID, sender: str) -> None:
        """Write the consumed marker for a specific message.

        This method is called by Coordinator/Worker after successful processing
        to prevent replay on restart (mailbox-abi.md §3).

        Args:
            message_id: The UUID of the message to mark consumed.
            sender: The sender directory name to locate the message file.
        """
        sender_dir = self._session_dir / sender
        # Find the message file (might have a timestamp prefix)
        if not sender_dir.exists():
            return

        for path in sender_dir.iterdir():
            if path.suffix == ".json" and str(message_id) in path.name:
                try:
                    await asyncio.to_thread(_write_consumed_marker, path)
                    return
                except OSError as exc:
                    logger.warning(
                        "FileMailbox.mark_consumed: failed for message %s: %s",
                        message_id,
                        exc,
                    )
                    return
