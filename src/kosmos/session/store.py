# SPDX-License-Identifier: Apache-2.0
"""Append-only JSONL session store for KOSMOS session persistence.

Session files live at ``~/.kosmos/sessions/{session_id}.jsonl``.  Each line
is a JSON-serialised :class:`~kosmos.session.models.SessionEntry`.  The first
line is always a ``"metadata"`` entry so that :func:`list_sessions` can
cheaply read metadata without loading the full history.

File I/O is dispatched via :func:`asyncio.to_thread` so that the async event
loop is never blocked — no additional dependencies are required.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from kosmos.session.models import SessionEntry, SessionMetadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default session directory
# ---------------------------------------------------------------------------

_DEFAULT_SESSION_DIR = Path.home() / ".kosmos" / "sessions"


def _get_session_dir() -> Path:
    """Return the session directory, creating it if necessary.

    Honours the ``KOSMOS_SESSION_DIR`` environment variable when set, which
    allows tests to redirect session storage to a temporary directory without
    modifying the user's home directory.
    """
    env_override = os.environ.get("KOSMOS_SESSION_DIR", "").strip()
    session_dir = Path(env_override) if env_override else _DEFAULT_SESSION_DIR
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _session_path(session_id: str, session_dir: Path | None = None) -> Path:
    """Return the JSONL file path for a given session ID."""
    base = session_dir if session_dir is not None else _get_session_dir()
    return base / f"{session_id}.jsonl"


# ---------------------------------------------------------------------------
# Sync helpers (run inside asyncio.to_thread)
# ---------------------------------------------------------------------------


def _sync_write_line(path: Path, obj: dict[str, object]) -> None:
    """Append a single JSON line to *path* (sync, for use in to_thread)."""
    line = json.dumps(obj, ensure_ascii=False, default=str)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _sync_read_lines(path: Path) -> list[dict[str, object]]:
    """Read all valid JSON lines from *path*, skipping corrupt ones (sync)."""
    results: list[dict[str, object]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    results.append(json.loads(raw))
                except json.JSONDecodeError:
                    logger.warning("Skipping corrupt JSONL line %d in %s", lineno, path)
    except FileNotFoundError:
        pass
    return results


def _sync_read_first_line(path: Path) -> dict[str, object] | None:
    """Read only the first non-empty JSON line from *path* (sync)."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    result: dict[str, object] = json.loads(raw)
                    return result
                except json.JSONDecodeError:
                    logger.warning("Corrupt first line in %s — cannot read metadata", path)
                    return None
    except FileNotFoundError:
        pass
    return None


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def create_session(
    session_dir: Path | None = None,
) -> SessionMetadata:
    """Create a new session and write its metadata as the first JSONL line.

    Args:
        session_dir: Override directory (used in tests via ``tmp_path``).

    Returns:
        :class:`SessionMetadata` for the newly created session.
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    metadata = SessionMetadata(
        session_id=session_id,
        created_at=now,
        updated_at=now,
    )
    entry = SessionEntry(
        timestamp=now,
        entry_type="metadata",
        data=metadata.model_dump(mode="json"),
    )
    path = _session_path(session_id, session_dir)

    def _write() -> None:
        if session_dir is not None:
            session_dir.mkdir(parents=True, exist_ok=True)
        else:
            _get_session_dir()
        _sync_write_line(path, entry.model_dump(mode="json"))

    await asyncio.to_thread(_write)
    return metadata


async def save_entry(
    session_id: str,
    entry: SessionEntry,
    session_dir: Path | None = None,
) -> None:
    """Append *entry* to the session JSONL file.

    Args:
        session_id: UUID string identifying the target session.
        entry: The :class:`SessionEntry` to persist.
        session_dir: Override directory (used in tests via ``tmp_path``).
    """
    path = _session_path(session_id, session_dir)
    payload = entry.model_dump(mode="json")
    await asyncio.to_thread(_sync_write_line, path, payload)


async def load_session(
    session_id: str,
    session_dir: Path | None = None,
) -> list[SessionEntry]:
    """Load all entries for a session.

    Corrupt lines are silently skipped (a warning is logged).

    Args:
        session_id: UUID string identifying the session.
        session_dir: Override directory (used in tests via ``tmp_path``).

    Returns:
        Ordered list of :class:`SessionEntry` objects (including the leading
        metadata entry).
    """
    path = _session_path(session_id, session_dir)
    raw_lines = await asyncio.to_thread(_sync_read_lines, path)
    entries: list[SessionEntry] = []
    for raw in raw_lines:
        try:
            entries.append(SessionEntry.model_validate(raw))
        except Exception:  # noqa: BLE001
            logger.warning("Could not deserialise session entry: %r", raw)
    return entries


async def list_sessions(
    session_dir: Path | None = None,
) -> list[SessionMetadata]:
    """Return metadata for all persisted sessions, sorted newest-first.

    Only the first line of each JSONL file is read to keep this O(n) with
    respect to the number of sessions rather than the total history size.

    Args:
        session_dir: Override directory (used in tests via ``tmp_path``).

    Returns:
        List of :class:`SessionMetadata`, sorted by ``updated_at`` descending.
    """
    base = session_dir if session_dir is not None else _get_session_dir()

    def _collect() -> list[SessionMetadata]:
        metas: list[SessionMetadata] = []
        if not base.exists():
            return metas
        for jsonl_path in base.glob("*.jsonl"):
            first = _sync_read_first_line(jsonl_path)
            if first is None:
                continue
            # The first line is a SessionEntry whose data holds the metadata
            try:
                entry = SessionEntry.model_validate(first)
                if entry.entry_type == "metadata":
                    metas.append(SessionMetadata.model_validate(entry.data))
            except Exception:  # noqa: BLE001
                logger.warning("Could not parse metadata from %s", jsonl_path)
        metas.sort(key=lambda m: m.updated_at, reverse=True)
        return metas

    return await asyncio.to_thread(_collect)


async def delete_session(
    session_id: str,
    session_dir: Path | None = None,
) -> None:
    """Delete a session JSONL file.

    Silently succeeds if the file does not exist.

    Args:
        session_id: UUID string identifying the session to remove.
        session_dir: Override directory (used in tests via ``tmp_path``).
    """
    path = _session_path(session_id, session_dir)

    def _remove() -> None:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()

    await asyncio.to_thread(_remove)


async def get_session_metadata(
    session_id: str,
    session_dir: Path | None = None,
) -> SessionMetadata:
    """Read the metadata entry for a specific session.

    Args:
        session_id: UUID string identifying the session.
        session_dir: Override directory (used in tests via ``tmp_path``).

    Returns:
        :class:`SessionMetadata` parsed from the first JSONL line.

    Raises:
        FileNotFoundError: If no session file exists for *session_id*.
        ValueError: If the first line cannot be parsed as valid metadata.
    """
    path = _session_path(session_id, session_dir)
    first = await asyncio.to_thread(_sync_read_first_line, path)
    if first is None:
        raise FileNotFoundError(f"Session not found: {session_id}")
    try:
        entry = SessionEntry.model_validate(first)
        if entry.entry_type != "metadata":
            raise ValueError(
                f"Expected metadata entry at line 1 of {path}, got {entry.entry_type!r}"
            )
        return SessionMetadata.model_validate(entry.data)
    except Exception as exc:
        raise ValueError(f"Could not parse metadata for session {session_id}: {exc}") from exc


async def update_session_metadata(
    metadata: SessionMetadata,
    session_dir: Path | None = None,
) -> None:
    """Rewrite the first line of a session file with updated metadata.

    This reads all lines, replaces line 0, and rewrites the file atomically
    (write to a ``.tmp`` file then rename).

    Args:
        metadata: Updated :class:`SessionMetadata` to persist.
        session_dir: Override directory (used in tests via ``tmp_path``).
    """
    path = _session_path(metadata.session_id, session_dir)
    entry = SessionEntry(
        timestamp=metadata.updated_at,
        entry_type="metadata",
        data=metadata.model_dump(mode="json"),
    )

    def _rewrite() -> None:
        raw_lines = _sync_read_lines(path)
        if not raw_lines:
            # File was empty — just create it fresh
            _sync_write_line(path, entry.model_dump(mode="json"))
            return
        # Replace the first line (metadata) and keep the rest
        raw_lines[0] = entry.model_dump(mode="json")
        tmp_path = path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            for obj in raw_lines:
                fh.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        tmp_path.replace(path)

    await asyncio.to_thread(_rewrite)
