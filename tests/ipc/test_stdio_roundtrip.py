# SPDX-License-Identifier: Apache-2.0
"""Round-trip integration test for the Python IPC stdio loop.

Spawns ``uv run kosmos --ipc stdio`` as a subprocess, writes frames of every
arm to its stdin, reads the responses from stdout, and validates that each
response deserialises cleanly as an ``IPCFrame``.

Task T029 (Plan Phase 3, US1 scenario): pytest-asyncio integration test that
exercises the full CLI → stdio path without any live data.go.kr calls.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from kosmos.ipc.frame_schema import (
    IPCFrame,
    SessionEventFrame,
    UserInputFrame,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ADAPTER: TypeAdapter[IPCFrame] = TypeAdapter(IPCFrame)

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _ts() -> str:
    now = datetime.now(tz=UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _encode(frame: IPCFrame) -> bytes:
    return (frame.model_dump_json() + "\n").encode("utf-8")


async def _read_lines(stream: asyncio.StreamReader, n: int, timeout: float = 10.0) -> list[str]:
    """Read up to *n* non-empty lines with a per-line timeout."""
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


# ---------------------------------------------------------------------------
# Fixture: spawn the kosmos backend in --ipc stdio mode
# ---------------------------------------------------------------------------


@pytest.fixture
async def backend_proc() -> AsyncIterator[asyncio.subprocess.Process]:
    """Spawn ``uv run kosmos --ipc stdio`` and yield the process handle.

    KOSMOS_IPC_HANDLER=echo selects the test-friendly echo handler so the
    round-trip test does not depend on FRIENDLI_API_KEY or network. The
    production handler (Epic #1633) routes user_input frames through
    LLMClient.stream() against FriendliAI.
    """
    import os

    env = {**os.environ, "KOSMOS_IPC_HANDLER": "echo"}
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "kosmos.cli",
        "--ipc",
        "stdio",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=_PROJECT_ROOT,
        env=env,
    )
    yield proc
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_starts(backend_proc: asyncio.subprocess.Process) -> None:
    """Backend process starts without immediate crash."""
    await asyncio.sleep(0.5)  # brief wait for process to initialise
    assert backend_proc.returncode is None, "Backend exited prematurely"


@pytest.mark.asyncio
async def test_user_input_echo_roundtrip(backend_proc: asyncio.subprocess.Process) -> None:
    """Sending a user_input frame gets back at least one IPCFrame response.

    The echo handler in stdio.run() replies with an assistant_chunk for every
    user_input frame, so we expect exactly 1 response line.
    """
    sid = "01HTESTST0000000000000ABCD"
    frame = UserInputFrame(
        session_id=sid,
        correlation_id="test-corr-roundtrip-001",
        role="tui",
        ts=_ts(),
        kind="user_input",
        text="hello",
    )
    assert backend_proc.stdin is not None
    backend_proc.stdin.write(_encode(frame))
    await backend_proc.stdin.drain()

    assert backend_proc.stdout is not None
    lines = await _read_lines(backend_proc.stdout, 1, timeout=5.0)
    assert len(lines) == 1, f"Expected 1 response line, got {len(lines)}"
    parsed = _ADAPTER.validate_json(lines[0])
    assert parsed.kind == "assistant_chunk"
    assert parsed.session_id == sid


@pytest.mark.asyncio
async def test_exit_event_triggers_shutdown(backend_proc: asyncio.subprocess.Process) -> None:
    """Sending a session_event {event='exit'} causes the backend to exit cleanly."""
    sid = "01HTESTST0000000000000ABCE"
    frame = SessionEventFrame(
        session_id=sid,
        correlation_id="test-corr-exit-001",
        role="tui",
        ts=_ts(),
        kind="session_event",
        event="exit",
        payload={},
    )
    assert backend_proc.stdin is not None
    backend_proc.stdin.write(_encode(frame))
    await backend_proc.stdin.drain()
    backend_proc.stdin.close()

    # Backend should exit within 5 seconds on exit event
    try:
        await asyncio.wait_for(backend_proc.wait(), timeout=5.0)
    except TimeoutError:
        pytest.fail("Backend did not exit within 5 s after session_event exit")

    assert backend_proc.returncode == 0, f"Non-zero exit: {backend_proc.returncode}"


@pytest.mark.asyncio
async def test_malformed_json_returns_error_frame(backend_proc: asyncio.subprocess.Process) -> None:
    """Sending garbage JSON gets back an error frame (not a crash)."""
    assert backend_proc.stdin is not None
    backend_proc.stdin.write(b"NOT_VALID_JSON\n")
    await backend_proc.stdin.drain()

    assert backend_proc.stdout is not None
    lines = await _read_lines(backend_proc.stdout, 1, timeout=5.0)
    assert len(lines) == 1, "Expected an error frame response"
    parsed = _ADAPTER.validate_json(lines[0])
    assert parsed.kind == "error"
    assert parsed.code == "ipc_decode_error"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_multiple_frames_fifo_order(backend_proc: asyncio.subprocess.Process) -> None:
    """Send 5 user_input frames; responses arrive in FIFO order (session_id preserved)."""
    sid = "01HTESTST0000000000000ABCF"
    texts = [f"msg-{i}" for i in range(5)]
    assert backend_proc.stdin is not None
    for i, text in enumerate(texts):
        f = UserInputFrame(
            session_id=sid,
            correlation_id=f"test-corr-fifo-{i:03d}",
            role="tui",
            ts=_ts(),
            kind="user_input",
            text=text,
        )
        backend_proc.stdin.write(_encode(f))
    await backend_proc.stdin.drain()

    assert backend_proc.stdout is not None
    lines = await _read_lines(backend_proc.stdout, 5, timeout=10.0)
    assert len(lines) == 5, f"Expected 5 responses, got {len(lines)}"
    for line in lines:
        parsed = _ADAPTER.validate_json(line)
        assert parsed.kind == "assistant_chunk"
        assert parsed.session_id == sid
