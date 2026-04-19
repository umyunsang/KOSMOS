# SPDX-License-Identifier: Apache-2.0
"""T052 — NDJSON-level correlation_id stability across a synthetic full turn.

Mirrors ``quickstart.md § 5.2``::

    uv run python -m kosmos.ipc.demo.full_turn_probe --session s-trace \\
        | jq -s '[.[] | .correlation_id] | unique | length'
    # → 1

Runs the probe as a subprocess so the test also exercises the stdout NDJSON
line terminator + UTF-8 encoding path that the TUI reader observes.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("session", ["s-trace", "s-probe-1"])
def test_probe_emits_single_correlation_id(session: str) -> None:
    """Probe output has exactly 1 unique correlation_id across all emitted frames."""
    result = subprocess.run(
        [sys.executable, "-m", "kosmos.ipc.demo.full_turn_probe", "--session", session],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert len(lines) == 5, f"Expected 5 frames, got {len(lines)}"

    frames = [json.loads(line) for line in lines]
    corr_ids = {f["correlation_id"] for f in frames}
    assert len(corr_ids) == 1, (
        f"Expected 1 unique correlation_id across a turn, got {len(corr_ids)}: {corr_ids}"
    )

    # Envelope sanity: every frame also shares the same session_id.
    session_ids = {f["session_id"] for f in frames}
    assert session_ids == {session}, f"session_id drift: {session_ids}"


def test_probe_frames_are_ndjson() -> None:
    """Every frame occupies exactly one line (FR-009 line integrity)."""
    result = subprocess.run(
        [sys.executable, "-m", "kosmos.ipc.demo.full_turn_probe", "--session", "s-ndjson"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    # Every non-empty line parses as standalone JSON; no line wraps a newline.
    for line in result.stdout.splitlines():
        if line.strip():
            obj = json.loads(line)
            assert isinstance(obj, dict)
            assert obj["version"] == "1.0"


def test_probe_tool_call_carries_transaction_id() -> None:
    """FR-026: tool_call + tool_result share the same transaction_id."""
    result = subprocess.run(
        [sys.executable, "-m", "kosmos.ipc.demo.full_turn_probe", "--session", "s-tx"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    frames = [json.loads(ln) for ln in result.stdout.splitlines() if ln.strip()]
    by_kind = {f["kind"]: f for f in frames}
    assert by_kind["tool_call"].get("transaction_id") is not None
    assert by_kind["tool_call"]["transaction_id"] == by_kind["tool_result"].get("transaction_id")
    # Streaming chunks must NOT carry a transaction_id.
    assert by_kind["assistant_chunk"].get("transaction_id") is None
