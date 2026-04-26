#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""KOSMOS PTY scenario harness — Spec 1978 T001 skeleton.

Drives `bun run tui` inside a real PTY (so Ink's raw-mode `useInput` works) and
captures the framed stdout (NDJSON IPC) and DEBUG stderr separately. Used by
reviewers to verify Epic #1978 acceptance scenarios per
`specs/1978-tui-kexaone-wiring/quickstart.md`.

KOSMOS-original — Claude Code's restored source has no equivalent harness.
The closest CC pattern is the inline reproduction recipes scattered through
`.references/claude-code-sourcemap/restored-src/src/utils/expect/` for
prompt fixtures, but those run against an in-process LLM mock, not a live
TTY-driven binary. KOSMOS needs a dedicated harness because memory
`feedback_runtime_verification` requires PTY-driven scenario capture rather
than code-grep claims of closure.

Subcommand bodies are intentionally minimal in T001 — Phase 2 only ships the
skeleton + the boot drain. Each subcommand's full keystroke / assertion
sequence lands in Phase 7 tasks T073-T077.

Usage::

    python scripts/pty-scenario.py greeting
    python scripts/pty-scenario.py lookup-emergency-room --capture-out /tmp/s2.log
    python scripts/pty-scenario.py submit-fine-pay --auto-allow-once
    python scripts/pty-scenario.py verify-gongdong
    python scripts/pty-scenario.py subscribe-cbs

Exit codes: 0 = scenario passed, 1 = scenario failed, 2 = harness error.

This file is dependency-free Python stdlib only. ``KOSMOS_FRIENDLI_TOKEN`` is
required for greeting / lookup; ``KOSMOS_DATA_GO_KR_API_KEY`` may be required
for live lookup runs. Mock-based scenarios (submit / verify / subscribe) need
no external secrets once Phase F adapter registration lands.
"""

from __future__ import annotations

import argparse
import os
import pty
import re
import select
import signal
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKTREE_ROOT = Path(__file__).resolve().parent.parent
TUI_DIR = WORKTREE_ROOT / "tui"
DEFAULT_BOOT_MS = 8_000
DEFAULT_TURN_TIMEOUT_MS = 25_000
DEFAULT_PERMISSION_TIMEOUT_MS = 60_000
DEFAULT_SUBSCRIBE_TIMEOUT_MS = 30_000

ANSI_RE = re.compile(rb"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>]|\x1b\([AB012]")


def strip_ansi(buf: bytes) -> str:
    """Drop terminal escape sequences so reviewers can scan content easily."""
    return ANSI_RE.sub(b"", buf).decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Harness primitives
# ---------------------------------------------------------------------------


@dataclass
class HarnessResult:
    """Result envelope returned by every scenario subcommand."""

    scenario: str
    pid: int
    exit_code: int | None
    boot_ms: int
    total_ms: int
    captured_stdout: bytearray = field(default_factory=bytearray)
    captured_stderr: bytearray = field(default_factory=bytearray)
    markers_seen: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def stdout_text(self) -> str:
        return strip_ansi(bytes(self.captured_stdout))

    @property
    def stderr_text(self) -> str:
        return self.captured_stderr.decode("utf-8", errors="replace")


def _spawn_tui(env_overrides: dict[str, str]) -> tuple[int, int]:
    """Fork the TUI under a PTY; returns (pid, master_fd).

    Direct ``bun src/main.tsx`` invocation, NOT ``bun run tui``: the ``bun run``
    wrapper does not pass through stdin/stdout TTY-ness to the child, which
    causes ``process.stdout.isTTY === false`` inside main.tsx and triggers the
    non-interactive --print branch (then dies with "Input must be provided ...").
    Direct invocation under PTY preserves TTY semantics on every fd.
    """
    cmd = ["bun", "src/main.tsx"]
    env = os.environ.copy()
    env.setdefault("DISABLE_INSTALLATION_CHECKS", "1")
    env.setdefault("KOSMOS_TUI_LOG_LEVEL", "DEBUG")
    env.setdefault("OTEL_SDK_DISABLED", "true")
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("COLUMNS", "120")
    env.setdefault("LINES", "40")
    env.setdefault("FORCE_COLOR", "0")
    env.update(env_overrides)

    pid, fd = pty.fork()
    if pid == 0:
        # Child — exec the TUI in the worktree's tui/ directory.
        os.chdir(str(TUI_DIR))
        os.execvpe(cmd[0], cmd, env)
    return pid, fd


def _drain(fd: int, deadline: float, dest: bytearray, label: str) -> None:
    """Read from ``fd`` until ``deadline``, appending bytes to ``dest``."""
    while time.time() < deadline:
        timeout = max(0.05, deadline - time.time())
        readable, _, _ = select.select([fd], [], [], timeout)
        if not readable:
            continue
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            return
        if not chunk:
            return
        dest.extend(chunk)
        sys.stdout.write(f"[{label}+{len(chunk)}B] ")
        sys.stdout.flush()


def _send(fd: int, payload: bytes, label: str) -> None:
    """Write bytes to PTY master."""
    os.write(fd, payload)
    sys.stdout.write(f"[{label}->{len(payload)}B] ")
    sys.stdout.flush()


def _shutdown(pid: int, fd: int, grace_ms: int = 1500) -> int | None:
    """Send Ctrl-C twice + SIGTERM, then reap. Returns exit code if available."""
    try:
        os.write(fd, b"\x03")  # Ctrl-C #1
        time.sleep(0.4)
        os.write(fd, b"\x03")  # Ctrl-C #2 — TUI's "press again to exit"
    except OSError:
        pass
    deadline = time.time() + grace_ms / 1000
    while time.time() < deadline:
        try:
            done_pid, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return None
        if done_pid != 0:
            if os.WIFEXITED(status):
                return os.WEXITSTATUS(status)
            if os.WIFSIGNALED(status):
                return 128 + os.WTERMSIG(status)
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.4)
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        _, status = os.waitpid(pid, 0)
    except ChildProcessError:
        return None
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return None


def _scan_markers(text: str, needles: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for needle in needles:
        n = text.count(needle)
        if n:
            counts[needle] = n
    return counts


# ---------------------------------------------------------------------------
# Common scenario runner skeleton
# ---------------------------------------------------------------------------


def _run_skeleton(
    scenario: str,
    boot_ms: int,
    env_overrides: dict[str, str] | None = None,
) -> HarnessResult:
    env_overrides = env_overrides or {}
    started = time.time()
    pid, fd = _spawn_tui(env_overrides)
    result = HarnessResult(
        scenario=scenario,
        pid=pid,
        exit_code=None,
        boot_ms=0,
        total_ms=0,
    )
    try:
        # Phase 1: drain boot output.
        boot_deadline = started + boot_ms / 1000
        _drain(fd, boot_deadline, result.captured_stdout, f"{scenario}-boot")
        result.boot_ms = int((time.time() - started) * 1000)
        # Phase 2-N: subcommand-specific keystrokes go here in Phase 7 tasks.
        # For T001 skeleton we just clean up.
    finally:
        result.exit_code = _shutdown(pid, fd)
        result.total_ms = int((time.time() - started) * 1000)
    return result


# ---------------------------------------------------------------------------
# Subcommand handlers (skeletons — bodies land in Phase 7)
# ---------------------------------------------------------------------------


def cmd_greeting(_args: argparse.Namespace) -> HarnessResult:
    """T073 will fill this with the actual ``안녕하세요`` keystroke + assertion."""
    result = _run_skeleton("greeting", DEFAULT_BOOT_MS)
    result.markers_seen = _scan_markers(result.stdout_text, ["KOSMOS", "K-EXAONE"])
    if "KOSMOS" not in result.markers_seen:
        result.errors.append("boot banner missing KOSMOS marker")
    return result


def cmd_lookup_emergency_room(_args: argparse.Namespace) -> HarnessResult:
    """T074 will send '응급실 알려줘' AND '강남구 응급실' to exercise resolve_location chain."""
    return _run_skeleton("lookup-emergency-room", DEFAULT_BOOT_MS)


def cmd_submit_fine_pay(_args: argparse.Namespace) -> HarnessResult:
    """T075 will send '교통 범칙금 납부 시뮬' + handle the consent modal per --auto-* flag."""
    return _run_skeleton("submit-fine-pay", DEFAULT_BOOT_MS)


def cmd_verify_gongdong(_args: argparse.Namespace) -> HarnessResult:
    """T076 will send '공동인증서로 인증해줘'."""
    return _run_skeleton("verify-gongdong", DEFAULT_BOOT_MS)


def cmd_subscribe_cbs(_args: argparse.Namespace) -> HarnessResult:
    """T077 will send '재난문자 구독해줘' and capture ≥ 1 simulated alert."""
    return _run_skeleton("subscribe-cbs", DEFAULT_BOOT_MS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pty-scenario.py",
        description="KOSMOS PTY scenario harness (Spec 1978).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, helptext, handler in [
        ("greeting", "User Story 1 — '안녕하세요' (FR-001 / SC-001)", cmd_greeting),
        ("lookup-emergency-room", "US1 — 응급실 lookup chain (SC-001)", cmd_lookup_emergency_room),
        ("submit-fine-pay", "US2 — Mock submit + permission gauntlet (SC-002)", cmd_submit_fine_pay),
        ("verify-gongdong", "US3 — Mock verify gongdong_injeungseo (SC-003)", cmd_verify_gongdong),
        ("subscribe-cbs", "US4 — Mock CBS subscribe (FR-012)", cmd_subscribe_cbs),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--capture-out", type=Path, default=None, help="Persist stdout (frame stream) here.")
        p.add_argument("--capture-err", type=Path, default=None, help="Persist stderr (DEBUG log) here.")
        p.add_argument("--auto-allow-once", action="store_true", help="(submit) auto-tap 'allow once' button.")
        p.add_argument("--auto-allow-session", action="store_true", help="(submit) auto-tap 'allow for this session'.")
        p.add_argument("--auto-deny", action="store_true", help="(submit) auto-tap 'deny'.")
        p.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = args.handler

    try:
        result = handler(args)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"\n[harness-error] {type(exc).__name__}: {exc}\n")
        return 2

    print(
        f"\n\n[summary] scenario={result.scenario} exit={result.exit_code} "
        f"boot={result.boot_ms}ms total={result.total_ms}ms "
        f"stdout_bytes={len(result.captured_stdout)} stderr_bytes={len(result.captured_stderr)}",
    )
    if result.markers_seen:
        print(f"[markers] {result.markers_seen}")
    if result.errors:
        for err in result.errors:
            print(f"[error] {err}", file=sys.stderr)

    if args.capture_out is not None:
        args.capture_out.parent.mkdir(parents=True, exist_ok=True)
        args.capture_out.write_bytes(bytes(result.captured_stdout))
        print(f"[capture] stdout → {args.capture_out}")
    if args.capture_err is not None:
        args.capture_err.parent.mkdir(parents=True, exist_ok=True)
        args.capture_err.write_bytes(bytes(result.captured_stderr))
        print(f"[capture] stderr → {args.capture_err}")

    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
