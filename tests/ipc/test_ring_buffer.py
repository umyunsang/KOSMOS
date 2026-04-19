# SPDX-License-Identifier: Apache-2.0
"""Test: SessionRingBuffer — overflow, consumed markers, ring_evicted (Spec 032 T030).

Covers:
- deque(maxlen=256) overflow eviction (FIFO)
- .consumed marker replay gating (mark_consumed prevents re-replay)
- ring_evicted(last_seen_frame_seq) boolean correctness
- replay_since returns only unconsumed frames above threshold
- Backpressure helpers (is_above_hwm, is_below_resume_threshold)
"""

from __future__ import annotations

import pytest

from kosmos.ipc.frame_schema import AssistantChunkFrame
from kosmos.ipc.ring_buffer import SessionRingBuffer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ring(session_id: str = "s-ring-001", size: int = 256, hwm: int = 64) -> SessionRingBuffer:
    return SessionRingBuffer(session_id=session_id, ring_size=size, hwm=hwm)


def _make_chunk(
    session_id: str = "s-ring-001",
    correlation_id: str = "corr-001",
    ts: str = "2026-04-19T12:00:00+00:00",
    text: str = "chunk",
) -> AssistantChunkFrame:
    return AssistantChunkFrame(
        kind="assistant_chunk",
        session_id=session_id,
        correlation_id=correlation_id,
        ts=ts,
        role="backend",
        delta=text,
        message_id="msg-001",
        done=False,
    )


def _fill_ring(ring: SessionRingBuffer, count: int) -> list:
    """Append *count* frames to the ring; return list of stamped frames."""
    frames = []
    for i in range(count):
        frame = _make_chunk(
            session_id=ring.session_id,
            correlation_id=f"corr-{i:04d}",
            text=f"chunk-{i}",
        )
        stamped = ring.append(frame)
        frames.append(stamped)
    return frames


# ---------------------------------------------------------------------------
# Basic append and frame_seq stamping
# ---------------------------------------------------------------------------


def test_append_stamps_frame_seq() -> None:
    """append() assigns monotonic frame_seq starting at 0."""
    ring = _make_ring(size=4)
    f0 = ring.append(_make_chunk())
    f1 = ring.append(_make_chunk())
    assert f0.frame_seq == 0
    assert f1.frame_seq == 1


def test_append_increments_depth() -> None:
    ring = _make_ring(size=4)
    assert ring.depth == 0
    ring.append(_make_chunk())
    assert ring.depth == 1
    ring.append(_make_chunk())
    assert ring.depth == 2


def test_append_updates_frame_seq_counter() -> None:
    ring = _make_ring(size=4)
    _fill_ring(ring, 3)
    assert ring.frame_seq_counter == 3


# ---------------------------------------------------------------------------
# FIFO overflow eviction (maxlen=N)
# ---------------------------------------------------------------------------


def test_overflow_evicts_oldest_frame() -> None:
    """When capacity exceeded, oldest frame is evicted (FIFO)."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 5)  # 5 frames, capacity 4 → frame_seq=0 evicted

    # ring now contains frame_seq 1, 2, 3, 4
    seqs = [f.frame_seq for f in ring._frames]
    assert 0 not in seqs
    assert 1 in seqs and 4 in seqs
    assert ring.depth == 4


def test_overflow_keeps_ring_size_constant() -> None:
    """After overflow, depth never exceeds ring_size."""
    ring = _make_ring(size=8)
    _fill_ring(ring, 20)
    assert ring.depth == 8


def test_frame_seq_counter_continues_after_overflow() -> None:
    """frame_seq_counter does not reset after overflow."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 10)
    assert ring.frame_seq_counter == 10


def test_default_ring_size_256() -> None:
    """Default ring size is 256 (or env-overridden to 16 in tests)."""
    # Use explicit size=256 to avoid env override
    ring = SessionRingBuffer(session_id="s-256", ring_size=256)
    _fill_ring(ring, 256)
    assert ring.depth == 256
    _fill_ring(ring, 10)
    assert ring.depth == 256


# ---------------------------------------------------------------------------
# replay_since
# ---------------------------------------------------------------------------


def test_replay_since_returns_frames_above_threshold() -> None:
    """replay_since(3) returns frames with frame_seq 4, 5, 6."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 7)

    replayed = ring.replay_since(3)
    seqs = [f.frame_seq for f in replayed]
    assert seqs == [4, 5, 6]


def test_replay_since_none_returns_all() -> None:
    """replay_since(None) replays all frames in the buffer."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 5)
    replayed = ring.replay_since(None)
    assert len(replayed) == 5
    seqs = [f.frame_seq for f in replayed]
    assert seqs == [0, 1, 2, 3, 4]


def test_replay_since_all_seen_returns_empty() -> None:
    """replay_since(last_seq == highest) returns empty list."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 5)
    replayed = ring.replay_since(4)  # 4 is the last frame_seq
    assert replayed == []


def test_replay_preserves_original_frame_seq() -> None:
    """Replay frames keep their original frame_seq (not renumbered)."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 10)
    replayed = ring.replay_since(7)
    assert [f.frame_seq for f in replayed] == [8, 9]


# ---------------------------------------------------------------------------
# .consumed marker replay gating
# ---------------------------------------------------------------------------


def test_mark_consumed_excludes_from_replay() -> None:
    """Frames marked consumed are not returned by replay_since."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 5)

    ring.mark_consumed(2)
    ring.mark_consumed(4)

    replayed = ring.replay_since(0)
    seqs = [f.frame_seq for f in replayed]
    assert 2 not in seqs
    assert 4 not in seqs
    assert seqs == [1, 3]


def test_mark_consumed_multiple_times_is_idempotent() -> None:
    """Marking the same frame_seq consumed twice does not error."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 3)
    ring.mark_consumed(1)
    ring.mark_consumed(1)  # second call — no error
    replayed = ring.replay_since(None)
    seqs = [f.frame_seq for f in replayed]
    assert 1 not in seqs


def test_consumed_marker_survives_overflow() -> None:
    """Consumed markers are retained even when frames roll out of the ring."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 6)
    # frame_seq 0, 1 are evicted; 2..5 remain
    ring.mark_consumed(3)
    replayed = ring.replay_since(1)
    seqs = [f.frame_seq for f in replayed]
    assert 3 not in seqs
    assert 2 in seqs and 4 in seqs and 5 in seqs


# ---------------------------------------------------------------------------
# ring_evicted
# ---------------------------------------------------------------------------


def test_ring_evicted_false_when_seq_in_ring() -> None:
    """ring_evicted returns False when last_seen_frame_seq is still in ring."""
    ring = _make_ring(size=16)
    _fill_ring(ring, 10)
    assert not ring.ring_evicted(5)


def test_ring_evicted_false_for_none() -> None:
    """ring_evicted(None) → False (fresh TUI, no prior seq claimed)."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 10)
    assert not ring.ring_evicted(None)


def test_ring_evicted_true_when_seq_older_than_oldest() -> None:
    """ring_evicted True when last_seen_frame_seq < oldest buffered frame."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 10)
    # ring has frames 6..9 (oldest_seq=6)
    oldest = ring.oldest_seq()
    assert oldest is not None
    assert ring.ring_evicted(oldest - 1)


def test_ring_evicted_false_at_exact_oldest_boundary() -> None:
    """ring_evicted False when last_seen_frame_seq == oldest buffered seq.

    The boundary condition: client has seen the oldest frame in the ring,
    so replay_since(oldest) returns everything after it.
    """
    ring = _make_ring(size=4)
    _fill_ring(ring, 8)
    # ring has frames 4..7 (oldest_seq=4)
    oldest = ring.oldest_seq()
    assert oldest is not None
    # last_seen = oldest means client got the oldest frame — NOT evicted
    assert not ring.ring_evicted(oldest)


def test_ring_evicted_true_when_ring_empty_with_prior_seq() -> None:
    """Empty ring + non-None last_seen → evicted (all history gone)."""
    ring = _make_ring(size=4)
    assert ring.ring_evicted(0)  # buffer empty, client had frame 0 → evicted


def test_ring_evicted_false_when_ring_empty_and_none() -> None:
    """Empty ring + None last_seen → not evicted (fresh TUI, nothing to replay)."""
    ring = _make_ring(size=4)
    assert not ring.ring_evicted(None)


# ---------------------------------------------------------------------------
# oldest_seq
# ---------------------------------------------------------------------------


def test_oldest_seq_none_when_empty() -> None:
    ring = _make_ring()
    assert ring.oldest_seq() is None


def test_oldest_seq_after_overflow() -> None:
    """oldest_seq returns first frame in deque after overflow."""
    ring = _make_ring(size=4)
    _fill_ring(ring, 10)
    # After 10 frames through size-4 ring, frames 6..9 remain
    assert ring.oldest_seq() == 6


# ---------------------------------------------------------------------------
# Backpressure helpers
# ---------------------------------------------------------------------------


def test_is_above_hwm_false_when_below() -> None:
    ring = _make_ring(size=128, hwm=64)
    _fill_ring(ring, 60)
    assert not ring.is_above_hwm()


def test_is_above_hwm_true_when_at_threshold() -> None:
    ring = _make_ring(size=128, hwm=64)
    _fill_ring(ring, 64)
    assert ring.is_above_hwm()


def test_is_below_resume_threshold_true_when_drained() -> None:
    ring = _make_ring(size=128, hwm=64)
    _fill_ring(ring, 30)
    # resume threshold = hwm // 2 = 32; depth 30 < 32 → True
    assert ring.is_below_resume_threshold()


def test_is_below_resume_threshold_false_when_full() -> None:
    ring = _make_ring(size=128, hwm=64)
    _fill_ring(ring, 64)
    assert not ring.is_below_resume_threshold()


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_empty_session_id_raises() -> None:
    with pytest.raises(ValueError, match="session_id"):
        SessionRingBuffer(session_id="")
