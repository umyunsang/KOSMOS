# SPDX-License-Identifier: Apache-2.0
"""Asyncio-based JSONL stdio reader/writer loop for the TUI ↔ backend IPC bridge.

Protocol
--------
* Every frame is a single line of JSON terminated by a newline (``\\n``).
* The backend reads frames from ``stdin`` and writes frames to ``stdout``.
* ``stderr`` is reserved for diagnostic / log output; TUI consumes it for crash notices.
* Graceful shutdown: ``SIGTERM`` / ``SIGINT`` → drain in-flight work → write
  ``session_event {event="exit"}`` → flush stdout → exit 0.
* ``stdout`` is flushed after every written frame (FR-005 ordering invariant).

Usage
-----
This module is invoked by the CLI when ``--ipc stdio`` is passed::

    uv run kosmos --ipc stdio

The ``run()`` coroutine is the public entry point; it blocks until the session
exits.  The ``write_frame()`` helper is available for code that needs to push
frames from outside this module.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
from typing import Callable, Any

from pydantic import TypeAdapter, ValidationError

from kosmos.ipc.frame_schema import (
    IPCFrame,
    SessionEventFrame,
    UserInputFrame,
    ErrorFrame,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_frame_adapter: TypeAdapter[Any] = TypeAdapter(IPCFrame)

# Module-level stdout lock — prevents interleaved JSON if multiple async tasks
# write simultaneously (guards the flush-after-every-frame invariant).
_stdout_lock: asyncio.Lock | None = None


def _get_stdout_lock() -> asyncio.Lock:
    global _stdout_lock
    if _stdout_lock is None:
        _stdout_lock = asyncio.Lock()
    return _stdout_lock


# ---------------------------------------------------------------------------
# Frame I/O primitives
# ---------------------------------------------------------------------------


async def write_frame(frame: IPCFrame) -> None:
    """Serialise *frame* to a single JSON line and write it to stdout.

    Flushes stdout immediately after every frame to preserve the FIFO ordering
    invariant required by the TUI (FR-005).

    Thread-safety: serialised by ``_stdout_lock`` so concurrent coroutines
    cannot interleave partial JSON.
    """
    payload = frame.model_dump_json() + "\n"
    encoded = payload.encode("utf-8")
    lock = _get_stdout_lock()
    async with lock:
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


def _write_frame_sync(frame: IPCFrame) -> None:
    """Synchronous variant used in signal handlers (no event loop available)."""
    payload = frame.model_dump_json() + "\n"
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.buffer.flush()


# ---------------------------------------------------------------------------
# Reader loop
# ---------------------------------------------------------------------------


async def _reader_loop(
    stream: asyncio.StreamReader,
    on_frame: Callable[[IPCFrame], Any],
    session_id: str,
) -> None:
    """Read newline-delimited JSON frames from *stream* and dispatch them.

    Malformed lines are logged at ERROR and an ``error`` frame is sent back
    rather than crashing the loop (data-model.md § 1.4).
    """
    while True:
        try:
            line = await stream.readline()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.debug("stdin EOF or connection reset — stopping reader loop")
            break

        if not line:
            logger.debug("stdin EOF — stopping reader loop")
            break

        raw = line.decode("utf-8", errors="replace").strip()
        if not raw:
            continue  # skip blank lines

        try:
            frame = _frame_adapter.validate_json(raw)
        except (ValidationError, ValueError) as exc:
            logger.error("IPC decode error: %s | raw=%r", exc, raw[:200])
            # Emit an error frame back to the TUI (malformed input from TUI
            # should be surfaced, not silently dropped).
            err_frame = ErrorFrame(
                session_id=session_id,
                ts=_utcnow(),
                kind="error",
                code="ipc_decode_error",
                message="Failed to decode IPC frame from TUI",
                details={"raw_preview": raw[:200]},
            )
            await write_frame(err_frame)
            continue

        logger.debug("IPC frame received: kind=%s session=%s", frame.kind, frame.session_id)
        try:
            result = on_frame(frame)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001
            logger.exception("on_frame handler raised: %s", exc)


# ---------------------------------------------------------------------------
# Shutdown helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return current UTC time as RFC 3339 string."""
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(tz=timezone.utc).microsecond // 1000:03d}Z"


async def _emit_exit_frame(session_id: str) -> None:
    """Write a ``session_event {event='exit'}`` frame and flush stdout."""
    exit_frame = SessionEventFrame(
        session_id=session_id,
        ts=_utcnow(),
        kind="session_event",
        event="exit",
        payload={},
    )
    await write_frame(exit_frame)
    logger.debug("Emitted session_event exit frame")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run(
    session_id: str | None = None,
    on_frame: Callable[[IPCFrame], Any] | None = None,
) -> None:
    """Run the asyncio JSONL stdio loop until stdin closes or a signal arrives.

    Parameters
    ----------
    session_id:
        Session ULID shared with the TUI.  If omitted a random placeholder is
        used (suitable for smoke tests).
    on_frame:
        Callable invoked for every inbound ``IPCFrame``.  May be a coroutine
        function.  Defaults to a no-op echo handler that bounces the frame
        straight back to stdout (useful for integration tests).
    """
    import uuid

    sid = session_id or str(uuid.uuid4())
    logger.info("IPC stdio loop starting — session_id=%s", sid)

    # Install shutdown flag
    _shutdown = asyncio.Event()

    def _handle_signal(sig: signal.Signals, *_args: Any) -> None:  # type: ignore[type-arg]
        logger.info("Received signal %s — initiating graceful shutdown", sig.name)
        _shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except (ValueError, NotImplementedError):
            # Windows or restricted environments — fall back to signal.signal
            signal.signal(sig, _handle_signal)

    # Connect asyncio StreamReader to sys.stdin.buffer
    stdin_reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(stdin_reader)
    transport, _ = await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    # Default on_frame: echo back (no-op that echoes every inbound frame)
    if on_frame is None:
        async def _echo(frame: IPCFrame) -> None:  # type: ignore[misc]
            if frame.kind == "user_input":
                # Echo: produce a trivial assistant_chunk back.
                # Mirror the inbound session_id so callers can correlate.
                from kosmos.ipc.frame_schema import AssistantChunkFrame
                echo_frame = AssistantChunkFrame(
                    session_id=frame.session_id,  # mirror inbound session_id
                    ts=_utcnow(),
                    kind="assistant_chunk",
                    message_id=str(uuid.uuid4()),
                    delta=f"[echo] {frame.text}",  # type: ignore[attr-defined]
                    done=True,
                )
                await write_frame(echo_frame)
            elif frame.kind == "session_event" and frame.event == "exit":  # type: ignore[attr-defined]
                _shutdown.set()

        on_frame = _echo

    # Run reader loop concurrently with shutdown watcher
    reader_task = asyncio.create_task(
        _reader_loop(stdin_reader, on_frame, sid),
        name="ipc-reader",
    )
    shutdown_task = asyncio.create_task(_shutdown.wait(), name="ipc-shutdown")

    done, pending = await asyncio.wait(
        {reader_task, shutdown_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Cancel whatever is still running
    for task in pending:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    # Emit exit frame and flush
    try:
        await _emit_exit_frame(sid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to emit exit frame: %s", exc)

    transport.close()
    logger.info("IPC stdio loop exited cleanly — session_id=%s", sid)


__all__ = [
    "run",
    "write_frame",
]
