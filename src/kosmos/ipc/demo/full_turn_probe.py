# SPDX-License-Identifier: Apache-2.0
"""Full-turn correlation probe (Spec 032 T052, quickstart § 5.1).

Drives a synthetic 5-frame turn to stdout as NDJSON so that
``jq -s '[.[] | .correlation_id] | unique | length' == 1`` validates FR-003.

Usage::

    uv run python -m kosmos.ipc.demo.full_turn_probe --session s-trace > /tmp/trace.ndjson
    jq -s '[.[] | .correlation_id] | unique | length' /tmp/trace.ndjson  # → 1

Frame sequence::

    user_input  → tui
    tool_call   → backend
    tool_result → backend
    assistant_chunk (done=true) → backend
    payload_end (status=ok) → backend
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime

from kosmos.ipc.envelope import emit_ndjson
from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    PayloadEndFrame,
    ToolCallFrame,
    ToolResultEnvelope,
    ToolResultFrame,
    UserInputFrame,
)


def _ts() -> str:
    now = datetime.now(tz=UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _new_uuidv7() -> str:
    """Prefer stdlib ``uuid.uuid7()`` (Python 3.13+); fall back to uuid4."""
    uuid7 = getattr(uuid, "uuid7", None)
    return str(uuid7()) if callable(uuid7) else str(uuid.uuid4())


def build_full_turn(session_id: str) -> list[object]:
    """Build five frames sharing one correlation_id."""
    correlation_id = _new_uuidv7()
    call_id = _new_uuidv7()
    message_id = _new_uuidv7()
    tx_id = _new_uuidv7()

    user_input = UserInputFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="tui",
        ts=_ts(),
        kind="user_input",
        text="서울 지역 교통 사고 다발지역 알려줘",
    )
    tool_call = ToolCallFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="tool_call",
        call_id=call_id,
        name="lookup",
        arguments={"tool_id": "koroad_accident_hazard_search", "q": "서울"},
        transaction_id=tx_id,
    )
    tool_result = ToolResultFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="tool_result",
        call_id=call_id,
        envelope=ToolResultEnvelope(kind="lookup"),
        transaction_id=tx_id,
    )
    assistant_chunk = AssistantChunkFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="assistant_chunk",
        message_id=message_id,
        delta="분석 결과 요약입니다.",
        done=True,
    )
    payload_end = PayloadEndFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="payload_end",
        delta_count=1,
        status="ok",
    )
    return [user_input, tool_call, tool_result, assistant_chunk, payload_end]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Spec 032 full-turn correlation probe")
    parser.add_argument(
        "--session",
        default="s-probe",
        help="Session identifier to stamp on every frame (default: s-probe).",
    )
    args = parser.parse_args(argv)

    frames = build_full_turn(args.session)
    for frame in frames:
        sys.stdout.write(emit_ndjson(frame))  # type: ignore[arg-type]
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
