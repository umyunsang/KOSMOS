# SPDX-License-Identifier: Apache-2.0
"""Integration tests for session_event frame routing in the stdio IPC loop.

Spawns ``python -m ummaya.cli --ipc stdio`` as a subprocess with a hermetic
``UMMAYA_SESSION_DIR`` pointing at ``tmp_path/sessions``.  All tests exercise
the session lifecycle without touching the user's home directory or any live
data.go.kr APIs.

Task T110 (Spec 287, Phase 8 US6): round-trip integration test for
session_event routing wired in T111.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from ummaya.ipc.frame_schema import (
    IPCFrame,
    SessionEventFrame,
)

# ---------------------------------------------------------------------------
# Helpers (mirrors test_stdio_roundtrip.py pattern)
# ---------------------------------------------------------------------------

_ADAPTER: TypeAdapter[IPCFrame] = TypeAdapter(IPCFrame)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SESSION_EVENT_TIMEOUT = 20.0


def _ts() -> str:
    """Return current UTC time as an RFC 3339 string."""
    now = datetime.now(tz=UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _encode(frame: IPCFrame) -> bytes:
    return (frame.model_dump_json() + "\n").encode("utf-8")


async def _read_lines(
    stream: asyncio.StreamReader,
    n: int,
    timeout: float = 10.0,
) -> list[str]:
    """Read up to *n* non-empty lines with a total deadline timeout."""
    lines: list[str] = []
    deadline = time.monotonic() + timeout
    while len(lines) < n:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(stream.readline(), timeout=remaining)
        except TimeoutError:
            break
        if not raw:
            break
        line = raw.decode("utf-8", errors="replace").strip()
        if line:
            lines.append(line)
    return lines


async def _read_session_event(
    stream: asyncio.StreamReader,
    *,
    event: str | None = None,
    timeout: float = 10.0,
) -> SessionEventFrame | None:
    """Read until a session_event frame is observed, skipping boot frames."""
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        lines = await _read_lines(stream, 1, timeout=remaining)
        if not lines:
            return None
        parsed = _ADAPTER.validate_json(lines[0])
        if parsed.kind != "session_event":
            continue
        if event is not None and parsed.event != event:
            continue
        return parsed


# ---------------------------------------------------------------------------
# Fixture: hermetic backend subprocess
# ---------------------------------------------------------------------------


@pytest.fixture
async def session_backend(
    tmp_path: Path,
) -> AsyncIterator[tuple[asyncio.subprocess.Process, Path]]:
    """Spawn the backend with UMMAYA_SESSION_DIR overriding the real session dir.

    Yields (proc, session_dir) so tests can inspect the filesystem.
    """
    session_dir = tmp_path / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Inherit the current environment so UMMAYA_* API-key vars are available
    # (required by verify_startup guard in app.py), then override session dir.
    env = {
        **os.environ,
        "UMMAYA_SESSION_DIR": str(session_dir),
        "UMMAYA_DATA_GO_KR_API_KEY": "test-dummy",
        "UMMAYA_FRIENDLI_TOKEN": "test-dummy",
        "UMMAYA_KAKAO_API_KEY": "test-dummy",
        "UMMAYA_KMA_API_HUB_AUTH_KEY": "test-dummy",
        "OTEL_SDK_DISABLED": "true",
    }

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "ummaya.cli",
        "--ipc",
        "stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=4 * 1024 * 1024,
        cwd=_PROJECT_ROOT,
        env=env,
    )
    yield proc, session_dir

    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()


# ---------------------------------------------------------------------------
# Helpers for common frame dispatch
# ---------------------------------------------------------------------------


def _session_event(sid: str, event: str, payload: dict | None = None) -> bytes:
    frame = SessionEventFrame(
        session_id=sid,
        correlation_id=f"test-corr-{event}-001",
        role="tui",
        ts=_ts(),
        kind="session_event",
        event=event,  # type: ignore[arg-type]
        payload=payload or {},
    )
    return _encode(frame)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_creates_session(
    session_backend: tuple[asyncio.subprocess.Process, Path],
) -> None:
    """session_event new → backend emits a reply frame with a session_id."""
    proc, session_dir = session_backend
    sid = "01TEST-SESSION-NEW-00000001"

    assert proc.stdin is not None
    proc.stdin.write(_session_event(sid, "new"))
    await proc.stdin.drain()

    assert proc.stdout is not None
    parsed = await _read_session_event(proc.stdout, event="new", timeout=_SESSION_EVENT_TIMEOUT)
    assert parsed is not None, "Expected at least one response frame after session_event new"
    new_sid = parsed.payload.get("session_id")
    assert new_sid, "Response payload must include session_id"

    # Verify a JSONL file was created in the hermetic session dir.
    jsonl_files = list(session_dir.glob("*.jsonl"))
    assert jsonl_files, "Expected at least one session file on disk"


@pytest.mark.asyncio
async def test_save_emits_ack(
    session_backend: tuple[asyncio.subprocess.Process, Path],
) -> None:
    """session_event save → backend emits a save ack frame with session_id."""
    proc, session_dir = session_backend
    sid = "01TEST-SESSION-SAVE-0000001"

    assert proc.stdin is not None
    # First create a session so _sm has an active session_id.
    proc.stdin.write(_session_event(sid, "new"))
    await proc.stdin.drain()

    assert proc.stdout is not None
    new_parsed = await _read_session_event(proc.stdout, event="new", timeout=_SESSION_EVENT_TIMEOUT)
    assert new_parsed is not None, "Expected new reply before save"
    new_sid = new_parsed.payload.get("session_id")
    assert new_sid

    # Now send save.
    proc.stdin.write(_session_event(new_sid, "save"))
    await proc.stdin.drain()

    save_parsed = await _read_session_event(proc.stdout, event="save", timeout=_SESSION_EVENT_TIMEOUT)
    assert save_parsed is not None, "Expected ack frame for session_event save"
    assert save_parsed.payload.get("session_id"), "save ack must include session_id"


@pytest.mark.asyncio
async def test_list_returns_sessions(
    session_backend: tuple[asyncio.subprocess.Process, Path],
) -> None:
    """session_event list → sessions array is non-empty with required fields."""
    proc, session_dir = session_backend
    sid = "01TEST-SESSION-LIST-0000001"

    assert proc.stdin is not None

    # Create a session first so the list is non-empty.
    proc.stdin.write(_session_event(sid, "new"))
    await proc.stdin.drain()

    assert proc.stdout is not None
    await _read_session_event(proc.stdout, event="new", timeout=_SESSION_EVENT_TIMEOUT)

    # Ask for the list.
    proc.stdin.write(_session_event(sid, "list"))
    await proc.stdin.drain()

    list_parsed = await _read_session_event(proc.stdout, event="list", timeout=_SESSION_EVENT_TIMEOUT)
    assert list_parsed is not None, "Expected a response frame for session_event list"
    sessions = list_parsed.payload.get("sessions")
    assert isinstance(sessions, list) and len(sessions) > 0, "sessions must be non-empty"
    for entry in sessions:
        assert "id" in entry, "Each session entry must have 'id'"
        assert "created_at" in entry, "Each session entry must have 'created_at'"
        assert "turn_count" in entry, "Each session entry must have 'turn_count'"


@pytest.mark.asyncio
async def test_resume_emits_load_frame(
    session_backend: tuple[asyncio.subprocess.Process, Path],
) -> None:
    """session_event resume with a known id → backend emits session_event load frame."""
    proc, session_dir = session_backend
    sid = "01TEST-SESSION-RESUME-000001"

    assert proc.stdin is not None

    # Step 1: create a session and capture its ID.
    proc.stdin.write(_session_event(sid, "new"))
    await proc.stdin.drain()

    assert proc.stdout is not None
    new_parsed = await _read_session_event(proc.stdout, event="new", timeout=_SESSION_EVENT_TIMEOUT)
    assert new_parsed is not None, "Expected new reply"
    new_sid: str = new_parsed.payload.get("session_id")
    assert new_sid

    # Step 2: resume that session.
    proc.stdin.write(_session_event(sid, "resume", {"id": new_sid}))
    await proc.stdin.drain()

    load_parsed = await _read_session_event(proc.stdout, event="load", timeout=_SESSION_EVENT_TIMEOUT)
    assert load_parsed is not None, "Expected a load frame for session_event resume"
    payload = load_parsed.payload
    assert payload.get("session_id") == new_sid, "load frame must echo session_id"
    assert isinstance(payload.get("messages"), list), "load frame must include messages array"


@pytest.mark.asyncio
async def test_exit_event_shuts_down(
    session_backend: tuple[asyncio.subprocess.Process, Path],
) -> None:
    """session_event exit → backend emits session_event exit and exits 0 within 3s."""
    proc, session_dir = session_backend
    sid = "01TEST-SESSION-EXIT-0000001"

    assert proc.stdin is not None
    proc.stdin.write(_session_event(sid, "exit"))
    await proc.stdin.drain()
    proc.stdin.close()

    assert proc.stdout is not None
    exit_parsed = await _read_session_event(proc.stdout, event="exit", timeout=_SESSION_EVENT_TIMEOUT)
    assert exit_parsed is not None, "Expected an exit frame response"
    # The loop always emits a final session_event exit frame on shutdown.

    # Wait for the backend process to exit cleanly within 3s.
    try:
        await asyncio.wait_for(proc.wait(), timeout=3.0)
    except TimeoutError:
        pytest.fail("Backend did not exit within 3 s after session_event exit")
    assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}"
