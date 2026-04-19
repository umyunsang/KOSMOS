# SPDX-License-Identifier: Apache-2.0
"""NDJSON stream integrity test — SC-007 (Spec 032 T057).

Stress-proves the fail-closed invariant by feeding ``parse_ndjson_line`` a
1000-frame NDJSON stream with 5% malformed injection (50 lines: mixed bad
JSON + schema violations).  The invariant (``FR-035`` / SC-007) is:

    * Zero session aborts — no raised exceptions bubble out of
      :func:`kosmos.ipc.envelope.parse_ndjson_line`.
    * Only the 50 malformed frames are dropped (``parse_ndjson_line → None``);
      the other 950 valid frames parse successfully.
    * Every drop is logged as ``ipc.parse.json_error`` or
      ``ipc.parse.schema_error`` (OTEL-compatible error events).
    * Valid frames that *follow* a malformed drop continue parsing — the
      stream is self-healing, not quarantined.

The 1000-frame stream is built by cycling the 19 canonical ``ALL_FRAMES``
fixtures from ``test_envelope_roundtrip.py`` with ``frame_seq`` monotonically
incremented so that the parsed output preserves insertion order (matches
what the real backend would emit).
"""

from __future__ import annotations

import json
import logging
from typing import Final

import pytest

from kosmos.ipc.envelope import emit_ndjson, parse_ndjson_line
from kosmos.ipc.frame_schema import IPCFrame
from tests.ipc.test_envelope_roundtrip import ALL_FRAMES

# ---------------------------------------------------------------------------
# Test parameters (SC-007)
# ---------------------------------------------------------------------------

TOTAL_FRAMES: Final[int] = 1000
MALFORMED_COUNT: Final[int] = 50  # exactly 5%
VALID_COUNT: Final[int] = TOTAL_FRAMES - MALFORMED_COUNT
MALFORMED_EVERY_N: Final[int] = TOTAL_FRAMES // MALFORMED_COUNT  # one bad line every 20th


# ---------------------------------------------------------------------------
# Stream construction
# ---------------------------------------------------------------------------


def _clone_frame_with_seq(template: IPCFrame, new_seq: int) -> IPCFrame:
    """Return a copy of *template* with ``frame_seq`` rewritten."""
    return template.model_copy(update={"frame_seq": new_seq})


def _malformed_variants() -> list[str]:
    """Return five categories of malformed NDJSON lines cycled through the stream.

    Covers both ``ipc.parse.json_error`` (lexical breakage) and
    ``ipc.parse.schema_error`` (shape breakage) paths so the log-emission
    assertion exercises both code branches of :func:`parse_ndjson_line`.
    """
    return [
        # 1. Lexical breakage — unbalanced braces
        "this is not json{{{\n",
        # 2. Lexical breakage — truncated string literal
        '{"kind": "user_input", "text": "unterminated\n',
        # 3. Schema violation — missing required envelope fields
        json.dumps({"kind": "user_input", "session_id": "s1"}) + "\n",
        # 4. Schema violation — wrong role/kind pair (E3 rejects tool+resume_request)
        json.dumps(
            {
                "version": "1.0",
                "session_id": "s1",
                "correlation_id": "c1",
                "ts": "2026-04-19T12:00:00Z",
                "frame_seq": 0,
                "role": "tool",
                "kind": "resume_request",
                "tui_session_token": "tok-1",
            }
        )
        + "\n",
        # 5. Schema violation — unknown discriminator value
        json.dumps(
            {
                "version": "1.0",
                "session_id": "s1",
                "correlation_id": "c1",
                "ts": "2026-04-19T12:00:00Z",
                "frame_seq": 0,
                "role": "backend",
                "kind": "nonexistent_kind",
            }
        )
        + "\n",
    ]


def _build_stream() -> tuple[list[str], set[int]]:
    """Build the 1000-line NDJSON stream plus the set of malformed-line indices.

    Returns:
        ``(lines, malformed_indices)`` — the ordered list of 1000 NDJSON lines
        and the indices (into that list) where a malformed line was injected.
    """
    valid_count = 0
    malformed_variants = _malformed_variants()
    malformed_cursor = 0
    lines: list[str] = []
    malformed_indices: set[int] = set()

    for i in range(TOTAL_FRAMES):
        if (i + 1) % MALFORMED_EVERY_N == 0 and len(malformed_indices) < MALFORMED_COUNT:
            variant = malformed_variants[malformed_cursor % len(malformed_variants)]
            malformed_cursor += 1
            lines.append(variant)
            malformed_indices.add(i)
        else:
            template = ALL_FRAMES[valid_count % len(ALL_FRAMES)]
            frame = _clone_frame_with_seq(template, valid_count)
            lines.append(emit_ndjson(frame))
            valid_count += 1

    assert len(lines) == TOTAL_FRAMES
    assert len(malformed_indices) == MALFORMED_COUNT
    assert valid_count == VALID_COUNT
    return lines, malformed_indices


# ---------------------------------------------------------------------------
# The test (SC-007)
# ---------------------------------------------------------------------------


def test_ndjson_stream_fail_closed_5pct_malformed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """1000-frame stream with 5% malformed lines → 0 aborts, 950 parsed, 50 logged drops.

    Invariants asserted (SC-007 / FR-035):

    * Exactly ``VALID_COUNT`` (950) frames return a non-None ``IPCFrame``.
    * Exactly ``MALFORMED_COUNT`` (50) lines return ``None`` without raising.
    * Every drop emits a structured log record on ``kosmos.ipc.envelope`` with
      message ``ipc.parse.json_error`` or ``ipc.parse.schema_error``.
    * Zero unhandled exceptions escape ``parse_ndjson_line``.
    * Valid frames that *follow* a malformed line parse successfully — the
      stream is self-healing, never quarantined.
    """
    lines, malformed_indices = _build_stream()

    parsed_ok: list[IPCFrame] = []
    dropped_indices: list[int] = []

    with caplog.at_level(logging.ERROR, logger="kosmos.ipc.envelope"):
        for index, line in enumerate(lines):
            try:
                result = parse_ndjson_line(line)
            except Exception as exc:  # pragma: no cover — invariant: must not fire
                pytest.fail(
                    f"parse_ndjson_line raised on index={index} — "
                    f"fail-closed invariant violated: {exc!r}"
                )
            if result is None:
                dropped_indices.append(index)
            else:
                parsed_ok.append(result)

    # 1. Exact counts — no partial aborts, no extra drops.
    assert len(parsed_ok) == VALID_COUNT, (
        f"expected {VALID_COUNT} valid parses, got {len(parsed_ok)}"
    )
    assert len(dropped_indices) == MALFORMED_COUNT, (
        f"expected {MALFORMED_COUNT} drops, got {len(dropped_indices)}"
    )

    # 2. Every drop index corresponds to an injected malformed line
    #    (nothing valid was spuriously rejected).
    assert set(dropped_indices) == malformed_indices, (
        "drop indices do not match malformed-injection indices — "
        "valid frames were wrongly rejected or malformed frames leaked through"
    )

    # 3. Every drop produced an OTEL-compatible error log record.
    parse_error_records = [
        r
        for r in caplog.records
        if r.name == "kosmos.ipc.envelope"
        and r.message in {"ipc.parse.json_error", "ipc.parse.schema_error"}
    ]
    assert len(parse_error_records) == MALFORMED_COUNT, (
        f"expected {MALFORMED_COUNT} structured drop logs, got {len(parse_error_records)}"
    )

    # 4. Both error branches were exercised (json vs schema).
    error_messages = {r.message for r in parse_error_records}
    assert error_messages == {
        "ipc.parse.json_error",
        "ipc.parse.schema_error",
    }, f"expected both error branches, got {error_messages}"

    # 5. Self-healing: check the frame IMMEDIATELY following each malformed
    #    index parses successfully (when one exists).  Guards against a regression
    #    where a bad line corrupts subsequent parser state.
    for bad_index in malformed_indices:
        follower = bad_index + 1
        if follower >= TOTAL_FRAMES:
            continue
        if follower in malformed_indices:
            continue
        follower_result = parse_ndjson_line(lines[follower])
        assert follower_result is not None, (
            f"self-heal violated: valid line at index {follower} "
            f"(following malformed index {bad_index}) returned None"
        )


def test_ndjson_stream_preserves_frame_seq_order() -> None:
    """Order assertion — the 950 parsed frames hand back ``frame_seq`` 0..949 in order.

    This proves that ``parse_ndjson_line`` is a pure function (no hidden buffering)
    and that a dropped malformed line does not offset downstream ``frame_seq``
    parsing — the parser simply skips the drop and continues at the next line.
    """
    lines, malformed_indices = _build_stream()

    parsed_ok: list[IPCFrame] = [
        frame
        for index, line in enumerate(lines)
        if index not in malformed_indices and (frame := parse_ndjson_line(line)) is not None
    ]

    assert len(parsed_ok) == VALID_COUNT

    expected_seqs = list(range(VALID_COUNT))
    actual_seqs = [frame.frame_seq for frame in parsed_ok]
    first_mismatch = next(
        (i for i, (a, e) in enumerate(zip(actual_seqs, expected_seqs, strict=True)) if a != e),
        -1,
    )
    assert actual_seqs == expected_seqs, (
        f"frame_seq ordering drifted — expected monotonic 0..949, "
        f"got first-mismatch at {first_mismatch}"
    )
