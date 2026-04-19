# SPDX-License-Identifier: Apache-2.0
"""Quickstart Scenario B synthetic backend — session drop + resume (Spec 032 T053).

Spec 032 ``quickstart.md § 2.1``::

    uv run python -m kosmos.ipc.demo.session_backend --session-id s-demo &

Drives a single session through a scripted frame sequence so that a TUI probe
(``tui/src/ipc/demo/resume_probe.ts``) can apply the first N frames, drop
stdin, reconnect with a ``resume_request(last_seen_frame_seq=N-1)`` frame,
and observe the backend replay frames ``N..N+K-1`` out of its ring buffer.

Frame sequence (default ``--total-frames=25``, ``--after-frames=20``):

1. Emit 20 ``assistant_chunk`` frames (``frame_seq`` 0..19) to stdout.  The
   probe consumes these and records ``last_seen_frame_seq=19``.
2. Emit 5 additional ``assistant_chunk`` frames (``frame_seq`` 20..24) to
   stdout, buffered in the ring.  The probe is expected to MISS these
   because its stdin has already been closed at that point.
3. Block on stdin awaiting a ``resume_request`` frame from the probe on a
   reconnected fd.  On receipt, call ``ResumeManager.handle_resume_request``
   → emit ``ResumeResponseFrame(replay_count=5, resumed_from_frame_seq=20)``
   followed by the 5 buffered replay frames.
4. Exit 0 when stdin closes (probe's final act after applying the replay).

This harness is **synthetic** — it does NOT touch the LLM, tools, or
SessionManager.  It validates the FR-018..025 handshake surface end-to-end
through the real ``SessionRingBuffer`` + ``ResumeManager`` code paths.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime

from kosmos.ipc.envelope import emit_ndjson, parse_ndjson_line
from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    FrameTrailer,
    IPCFrame,
    PayloadEndFrame,
    ResumeRequestFrame,
)
from kosmos.ipc.resume_manager import ResumeManager
from kosmos.ipc.ring_buffer import SessionRingBuffer

logger = logging.getLogger(__name__)


def _ts() -> str:
    now = datetime.now(tz=UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _new_uuidv7() -> str:
    uuid7 = getattr(uuid, "uuid7", None)
    return str(uuid7()) if callable(uuid7) else str(uuid.uuid4())


def _write(frame: IPCFrame) -> None:
    sys.stdout.write(emit_ndjson(frame))
    sys.stdout.flush()


def _build_chunk(
    session_id: str,
    correlation_id: str,
    message_id: str,
    idx: int,
) -> AssistantChunkFrame:
    return AssistantChunkFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="assistant_chunk",
        message_id=message_id,
        delta=f"frame#{idx:02d} ",
        done=False,
    )


async def _read_resume_request(session_id: str) -> ResumeRequestFrame | None:
    """Read one line from stdin and validate it as a ResumeRequestFrame."""
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    while True:
        line = await reader.readline()
        if not line:
            return None
        raw = line.decode("utf-8", errors="replace").strip()
        if not raw:
            continue
        frame = parse_ndjson_line(raw)
        if frame is None:
            logger.warning("session_backend.unparseable_line: %r", raw[:200])
            continue
        if frame.kind != "resume_request":
            logger.warning("session_backend.unexpected_kind: %s", frame.kind)
            continue
        if frame.session_id != session_id:
            logger.warning(
                "session_backend.session_mismatch: got=%s want=%s",
                frame.session_id,
                session_id,
            )
            continue
        return frame  # type: ignore[return-value]


async def run(args: argparse.Namespace) -> int:
    session_id: str = args.session_id
    total_frames: int = args.total_frames
    after_frames: int = args.after_frames
    tui_token: str = args.tui_token

    if after_frames >= total_frames:
        logger.error(
            "session_backend.invalid_args: after_frames(%d) must be < total_frames(%d)",
            after_frames,
            total_frames,
        )
        return 2

    ring = SessionRingBuffer(session_id=session_id)
    mgr = ResumeManager()
    mgr.register_session(session_id=session_id, tui_session_token=tui_token, ring=ring)

    correlation_id = _new_uuidv7()
    message_id = _new_uuidv7()

    # Phase 1: emit frames 0..after_frames-1 to stdout AND buffer them.
    for idx in range(after_frames):
        frame = _build_chunk(session_id, correlation_id, message_id, idx)
        stamped = ring.append(frame)
        _write(stamped)

    # Phase 2: emit + buffer the remaining frames; stdout writes succeed but
    # the probe's stdin has already been closed so it will miss these.
    for idx in range(after_frames, total_frames):
        frame = _build_chunk(session_id, correlation_id, message_id, idx)
        stamped = ring.append(frame)
        _write(stamped)

    # Phase 3: wait for resume_request on stdin (reconnected fd).
    request = await _read_resume_request(session_id)
    if request is None:
        logger.warning("session_backend.stdin_eof_before_resume_request")
        return 1

    result = mgr.handle_resume_request(
        request,
        new_correlation_id=_new_uuidv7(),
        ts=_ts(),
    )
    _write(result.response)  # type: ignore[arg-type]
    for replayed in result.replay_frames:
        _write(replayed)  # type: ignore[arg-type]

    # Phase 4: emit a terminal payload_end so the probe has a clean stop cue.
    _write(
        PayloadEndFrame(
            session_id=session_id,
            correlation_id=correlation_id,
            role="backend",
            ts=_ts(),
            kind="payload_end",
            delta_count=total_frames,
            status="ok",
            trailer=FrameTrailer(final=True),
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Spec 032 Scenario B synthetic session backend",
    )
    parser.add_argument(
        "--session-id",
        default="s-demo",
        help="Session identifier shared with the TUI probe (default: s-demo).",
    )
    parser.add_argument(
        "--total-frames",
        type=int,
        default=25,
        help="Total frames the backend will produce (default: 25).",
    )
    parser.add_argument(
        "--after-frames",
        type=int,
        default=20,
        help=(
            "Count of frames the probe is expected to apply before dropping "
            "stdin (default: 20).  The remainder (total - after) is what the "
            "backend replays after the resume handshake."
        ),
    )
    parser.add_argument(
        "--tui-token",
        default="tok-demo",
        help="Token the probe must echo in its resume_request (default: tok-demo).",
    )
    args = parser.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
