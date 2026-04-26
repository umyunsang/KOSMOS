#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""KOSMOS IPC bridge diagnostic probe — Spec 1978 T079.

Sends a hand-rolled ChatRequestFrame directly to a freshly-spawned backend
(``uv run kosmos --ipc stdio``) via its stdin pipe, reads all resulting frames
from stdout until the process exits or a timeout fires, and pretty-prints each
frame with its kind, correlation_id, and elapsed time.

This is the "On failure" diagnostic described in
``specs/1978-tui-kexaone-wiring/quickstart.md``.

Usage::

    python scripts/probe-bridge.py
    python scripts/probe-bridge.py --message "강남구 응급실 알려줘"
    python scripts/probe-bridge.py --timeout 30 --message "안녕하세요"
    python scripts/probe-bridge.py --help

Exit codes:
  0 — at least one frame received from the backend
  1 — no frames received (timeout or crash)
  2 — harness / import error
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import selectors
import subprocess
import sys
import time
import uuid
from pathlib import Path

log = logging.getLogger("probe-bridge")

WORKTREE_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Frame construction
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="milliseconds")


def _make_chat_request(message: str, session_id: str = "", correlation_id: str | None = None) -> dict:
    """Build a minimal ChatRequestFrame dict matching the Pydantic schema.

    Constructs the dict directly (no import of kosmos.ipc.frame_schema needed
    at the call site) so the probe works even when the package is not installed,
    while still honouring the schema contract.
    """
    return {
        "kind": "chat_request",
        "version": "1.0",
        "session_id": session_id,
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "ts": _now_iso(),
        "role": "tui",
        "frame_seq": 0,
        "transaction_id": None,
        "trailer": None,
        "messages": [
            {
                "role": "user",
                "content": message,
                "name": None,
                "tool_call_id": None,
            }
        ],
        "tools": [],
        "system": None,
        "max_tokens": 8192,
        "temperature": 1.0,
        "top_p": 0.95,
    }


# ---------------------------------------------------------------------------
# Backend spawning
# ---------------------------------------------------------------------------


def _spawn_backend(env_overrides: dict[str, str]) -> subprocess.Popen:
    """Spawn ``uv run kosmos --ipc stdio`` with pipes on stdin/stdout."""
    cmd = ["uv", "run", "kosmos", "--ipc", "stdio"]
    env = os.environ.copy()
    env.setdefault("OTEL_SDK_DISABLED", "true")
    env.setdefault("KOSMOS_TUI_LOG_LEVEL", "DEBUG")
    env.update(env_overrides)
    log.debug("spawning: %s", " ".join(cmd))
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(WORKTREE_ROOT),
        env=env,
    )


# ---------------------------------------------------------------------------
# Frame reader
# ---------------------------------------------------------------------------


def _read_frames(proc: subprocess.Popen, timeout_s: float) -> list[dict]:
    """Read NDJSON frames from *proc.stdout* until timeout or EOF."""
    frames: list[dict] = []
    assert proc.stdout is not None  # noqa: S101
    assert proc.stderr is not None  # noqa: S101

    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
    sel.register(proc.stderr, selectors.EVENT_READ, "stderr")

    deadline = time.time() + timeout_s
    stdout_buf = b""

    while time.time() < deadline:
        remaining = max(0.1, deadline - time.time())
        events = sel.select(timeout=remaining)
        if not events:
            # Check if process already exited.
            if proc.poll() is not None:
                break
            continue
        for key, _ in events:
            data = key.fileobj.read1(65536)  # type: ignore[attr-defined]
            if not data:
                sel.unregister(key.fileobj)
                continue
            if key.data == "stderr":
                log.debug("[stderr] %s", data.decode("utf-8", errors="replace").rstrip())
                continue
            stdout_buf += data
            # Parse complete NDJSON lines.
            while b"\n" in stdout_buf:
                line, stdout_buf = stdout_buf.split(b"\n", 1)
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str.startswith("{"):
                    continue
                try:
                    obj = json.loads(line_str)
                    if "kind" in obj:
                        frames.append(obj)
                except json.JSONDecodeError:
                    log.debug("non-JSON line: %s", line_str[:120])

    sel.close()
    return frames


# ---------------------------------------------------------------------------
# Pretty printer
# ---------------------------------------------------------------------------


def _pretty_print_frame(frame: dict, elapsed_ms: int) -> None:
    kind = frame.get("kind", "?")
    cid = frame.get("correlation_id", "")[:16]
    tid = frame.get("transaction_id") or ""

    # Kind-specific summary fields.
    extras = ""
    if kind == "assistant_chunk":
        delta = frame.get("delta", "")[:60]
        done = frame.get("done", False)
        extras = f" delta={delta!r} done={done}"
    elif kind == "tool_call":
        extras = f" name={frame.get('name')} call_id={frame.get('call_id', '')[:12]}"
    elif kind == "tool_result":
        extras = f" call_id={frame.get('call_id', '')[:12]}"
    elif kind == "error":
        extras = f" code={frame.get('code')} msg={frame.get('message', '')[:60]!r}"
    elif kind == "session_event":
        extras = f" event={frame.get('event')}"
    elif kind == "heartbeat":
        extras = f" direction={frame.get('direction')}"

    tid_part = f" txn={tid[:12]}" if tid else ""
    print(f"[+{elapsed_ms:>6}ms] {kind:<22} cid={cid}{tid_part}{extras}")


# ---------------------------------------------------------------------------
# Validation via Pydantic (optional — graceful fallback if package unavailable)
# ---------------------------------------------------------------------------


def _try_validate_frames(frames: list[dict]) -> list[str]:
    """Attempt Pydantic v2 validation of each frame; return list of error strings."""
    errors: list[str] = []
    try:
        from pydantic import TypeAdapter, ValidationError  # type: ignore[import]

        from kosmos.ipc.frame_schema import IPCFrame  # type: ignore[import]

        adapter: TypeAdapter = TypeAdapter(IPCFrame)  # type: ignore[type-arg]
        for i, f in enumerate(frames):
            try:
                adapter.validate_python(f)
            except ValidationError as exc:
                errors.append(f"frame[{i}] kind={f.get('kind')!r}: {exc.error_count()} validation error(s)")
    except ImportError:
        log.debug("kosmos package not importable — skipping Pydantic validation")
    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="probe-bridge.py",
        description=(
            "KOSMOS IPC bridge diagnostic (Spec 1978 T079). "
            "Spawns the backend, sends one ChatRequestFrame, and pretty-prints the responses."
        ),
    )
    parser.add_argument(
        "--message",
        default="안녕하세요",
        help="User message to send (default: '안녕하세요')",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Seconds to wait for backend responses (default: 30)",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Session ID to embed in the frame (default: empty string)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run Pydantic validation on received frames (requires kosmos package installed).",
    )
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging to stderr.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    frame = _make_chat_request(args.message, session_id=args.session_id)
    frame_json = json.dumps(frame, ensure_ascii=False) + "\n"

    print(f"[probe] spawning backend in {WORKTREE_ROOT}")
    print(f"[probe] sending ChatRequestFrame  message={args.message!r}")
    print(f"[probe] correlation_id={frame['correlation_id']}")
    print(f"[probe] waiting up to {args.timeout}s for frames…")
    print()

    start_ts = time.time()
    try:
        proc = _spawn_backend({})
    except FileNotFoundError as exc:
        sys.stderr.write(f"[probe-error] could not spawn backend: {exc}\n")
        sys.stderr.write("[probe-error] ensure 'uv' is on PATH and the kosmos package is installed.\n")
        return 2

    try:
        assert proc.stdin is not None  # noqa: S101
        proc.stdin.write(frame_json.encode("utf-8"))
        proc.stdin.flush()
        proc.stdin.close()

        frames = _read_frames(proc, args.timeout)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass

    total_ms = int((time.time() - start_ts) * 1000)

    if not frames:
        print(f"[probe] NO frames received in {total_ms}ms — backend may need FRIENDLI_API_KEY or is not wired.")
        return 1

    for f in frames:
        elapsed_ms = int((time.time() - start_ts) * 1000)
        _pretty_print_frame(f, elapsed_ms)

    print()
    print(f"[probe] {len(frames)} frame(s) received in {total_ms}ms")

    if args.validate:
        errors = _try_validate_frames(frames)
        if errors:
            print("[probe] Pydantic validation errors:")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"[probe] all {len(frames)} frames passed Pydantic validation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
