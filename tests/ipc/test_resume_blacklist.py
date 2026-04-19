# SPDX-License-Identifier: Apache-2.0
"""Test: 3-strike blacklist + reset-on-success semantics (Spec 032 T028, WS4).

Covers FR-025: same session_id failing resume 3× consecutively → blacklisted.
After blacklist: subsequent resume returns session_unknown without ring access.
Successful resume RESETS the failure count.
"""

from __future__ import annotations

from kosmos.ipc.frame_schema import ResumeRejectedFrame, ResumeResponseFrame
from kosmos.ipc.resume_manager import RejectionReason, ResumeManager
from kosmos.ipc.ring_buffer import SessionRingBuffer
from tests.ipc.conftest import FakeClock, UUIDv7Factory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ring(session_id: str, count: int = 5) -> SessionRingBuffer:
    from kosmos.ipc.frame_schema import AssistantChunkFrame

    ring = SessionRingBuffer(session_id=session_id, ring_size=16)
    for i in range(count):
        frame = AssistantChunkFrame(
            kind="assistant_chunk",
            session_id=session_id,
            correlation_id=f"corr-{i:04d}",
            ts="2026-04-19T12:00:00+00:00",
            role="backend",
            delta=f"delta-{i}",
            message_id=f"msg-{i:04d}",
            done=False,
        )
        ring.append(frame)
    return ring


def _resume(
    mgr: ResumeManager,
    session_id: str,
    token: str,
    last_seen_frame_seq: int | None = None,
    *,
    make_uuid7: UUIDv7Factory,
    fake_clock: FakeClock,
) -> ResumeRejectedFrame | ResumeResponseFrame:
    from kosmos.ipc.frame_schema import ResumeRequestFrame

    request = ResumeRequestFrame(
        session_id=session_id,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
        role="tui",
        tui_session_token=token,
        last_seen_frame_seq=last_seen_frame_seq,
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    return result.response


# ---------------------------------------------------------------------------
# Blacklist: 3-strike rule
# ---------------------------------------------------------------------------


def test_three_wrong_tokens_causes_blacklist(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """3 consecutive token mismatches on same session → blacklisted."""
    session_id = "s-bl-001"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # Failure 1
    r1 = _resume(mgr, session_id, "bad-1", make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r1, ResumeRejectedFrame)
    assert r1.reason == RejectionReason.TOKEN_MISMATCH
    assert not mgr.is_blacklisted(session_id)
    assert mgr.failure_count(session_id) == 1

    # Failure 2
    r2 = _resume(mgr, session_id, "bad-2", make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r2, ResumeRejectedFrame)
    assert not mgr.is_blacklisted(session_id)
    assert mgr.failure_count(session_id) == 2

    # Failure 3 — threshold breach
    r3 = _resume(mgr, session_id, "bad-3", make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r3, ResumeRejectedFrame)
    assert mgr.is_blacklisted(session_id)


def test_blacklisted_session_returns_session_unknown(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """After blacklist, even correct token → session_unknown (not token_mismatch)."""
    session_id = "s-bl-002"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # Trigger blacklist with 3 failures
    for i in range(3):
        _resume(mgr, session_id, f"bad-{i}", make_uuid7=make_uuid7, fake_clock=fake_clock)

    assert mgr.is_blacklisted(session_id)

    # Even the correct token is rejected after blacklist
    r = _resume(mgr, session_id, token, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r, ResumeRejectedFrame)
    assert r.reason == RejectionReason.SESSION_UNKNOWN


def test_blacklisted_session_no_ring_access(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Blacklisted session must NOT touch the ring buffer."""
    session_id = "s-bl-003"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # Trigger blacklist
    for i in range(3):
        _resume(mgr, session_id, f"bad-{i}", make_uuid7=make_uuid7, fake_clock=fake_clock)

    # Ring's depth must be unchanged (not drained / modified by rejection logic)
    depth_before = ring.depth
    _resume(mgr, session_id, token, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert ring.depth == depth_before, "Ring depth must not change on blacklisted attempt"


# ---------------------------------------------------------------------------
# Reset-on-success: successful resume clears failure count
# ---------------------------------------------------------------------------


def test_successful_resume_resets_failure_count(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Two failures followed by a success → failure count resets to 0."""
    session_id = "s-bl-004"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # Two failures
    _resume(mgr, session_id, "bad-1", make_uuid7=make_uuid7, fake_clock=fake_clock)
    _resume(mgr, session_id, "bad-2", make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert mgr.failure_count(session_id) == 2
    assert not mgr.is_blacklisted(session_id)

    # Success with correct token
    r = _resume(mgr, session_id, token, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r, ResumeResponseFrame)
    assert mgr.failure_count(session_id) == 0
    assert not mgr.is_blacklisted(session_id)


def test_success_prevents_blacklist_after_two_failures(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """2 failures → success → 2 more failures → NOT yet blacklisted (count reset)."""
    session_id = "s-bl-005"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # 2 failures
    _resume(mgr, session_id, "bad", make_uuid7=make_uuid7, fake_clock=fake_clock)
    _resume(mgr, session_id, "bad", make_uuid7=make_uuid7, fake_clock=fake_clock)

    # 1 success → reset
    _resume(mgr, session_id, token, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert mgr.failure_count(session_id) == 0

    # 2 more failures — count starts fresh, so NOT blacklisted (count = 2 < 3)
    _resume(mgr, session_id, "bad", make_uuid7=make_uuid7, fake_clock=fake_clock)
    _resume(mgr, session_id, "bad", make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert mgr.failure_count(session_id) == 2
    assert not mgr.is_blacklisted(session_id)


# ---------------------------------------------------------------------------
# Manual blacklist reset
# ---------------------------------------------------------------------------


def test_reset_blacklist_re_enables_session(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """reset_blacklist() allows the session to attempt resume again."""
    session_id = "s-bl-006"
    token = "correct-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    mgr.register_session(session_id, token, ring)

    # Trigger blacklist
    for i in range(3):
        _resume(mgr, session_id, f"bad-{i}", make_uuid7=make_uuid7, fake_clock=fake_clock)

    assert mgr.is_blacklisted(session_id)

    # Admin reset
    mgr.reset_blacklist(session_id)
    assert not mgr.is_blacklisted(session_id)
    assert mgr.failure_count(session_id) == 0

    # Now correct token should succeed
    r = _resume(mgr, session_id, token, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r, ResumeResponseFrame)


# ---------------------------------------------------------------------------
# Isolation: blacklist of one session doesn't affect another
# ---------------------------------------------------------------------------


def test_blacklist_isolation_across_sessions(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Blacklisting session A must not affect session B."""
    session_a = "s-bl-007a"
    session_b = "s-bl-007b"
    token_b = "tok-b"
    mgr = ResumeManager()

    ring_a = _make_ring(session_a)
    ring_b = _make_ring(session_b)
    mgr.register_session(session_a, "tok-a", ring_a)
    mgr.register_session(session_b, token_b, ring_b)

    # Blacklist session A
    for i in range(3):
        _resume(mgr, session_a, f"bad-{i}", make_uuid7=make_uuid7, fake_clock=fake_clock)

    assert mgr.is_blacklisted(session_a)
    assert not mgr.is_blacklisted(session_b)

    # Session B still works
    r = _resume(mgr, session_b, token_b, make_uuid7=make_uuid7, fake_clock=fake_clock)
    assert isinstance(r, ResumeResponseFrame)
