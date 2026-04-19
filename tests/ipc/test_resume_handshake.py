# SPDX-License-Identifier: Apache-2.0
"""Test: resume handshake — 9 normative contract scenarios (Spec 032 T027, WS4).

Covers all 9 scenarios from contracts/resume-handshake.contract.md § 7:

1. Happy path, gap of 5 frames
2. Resume with last_seen_frame_seq = 0 (fresh TUI) → full buffer replay
3. Resume beyond ring capacity  → ring_evicted rejection
4. Resume with wrong token      → token_mismatch rejection
5. Resume of unknown session    → session_unknown rejection
6. Double resume (same last_seen_frame_seq) → idempotent second response
7. Resume during backpressure   → response always returned
8. Heartbeat timeout → dead → resume within grace → recovered
9. Heartbeat timeout → dead → resume after grace → session_unknown
"""

from __future__ import annotations

from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    ResumeRejectedFrame,
    ResumeRequestFrame,
    ResumeResponseFrame,
)
from kosmos.ipc.heartbeat import DeadlineState, HeartbeatSettings, HeartbeatState
from kosmos.ipc.resume_manager import RejectionReason, ResumeManager
from kosmos.ipc.ring_buffer import SessionRingBuffer
from tests.ipc.conftest import FakeClock, UUIDv7Factory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ring(session_id: str, size: int = 16) -> SessionRingBuffer:
    return SessionRingBuffer(session_id=session_id, ring_size=size)


def _make_chunk(
    session_id: str,
    correlation_id: str,
    ts: str,
    text: str = "hello",
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


def _make_resume_request(
    session_id: str,
    token: str,
    last_seen_frame_seq: int | None,
    correlation_id: str,
    ts: str,
) -> ResumeRequestFrame:
    return ResumeRequestFrame(
        kind="resume_request",
        session_id=session_id,
        correlation_id=correlation_id,
        ts=ts,
        role="tui",
        tui_session_token=token,
        last_seen_frame_seq=last_seen_frame_seq,
    )


def _fill_ring(
    ring: SessionRingBuffer,
    session_id: str,
    correlation_id: str,
    ts: str,
    count: int,
) -> None:
    for i in range(count):
        frame = _make_chunk(session_id, correlation_id, ts, text=f"chunk-{i}")
        ring.append(frame)


# ---------------------------------------------------------------------------
# Scenario 1: Happy path — gap of 5 frames
# ---------------------------------------------------------------------------


def test_happy_path_five_frame_gap(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 1: 10 frames in ring, TUI last saw frame_seq=4 → 5 replayed."""
    session_id = "s-001"
    token = "tok-001"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=10)

    mgr.register_session(session_id, token, ring)

    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=4,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeResponseFrame)
    resp: ResumeResponseFrame = result.response
    assert resp.replay_count == 5
    assert resp.resumed_from_frame_seq == 5
    assert resp.trailer is not None and resp.trailer.final is True
    assert len(result.replay_frames) == 5
    # Verify replay frames have original frame_seq values (5..9)
    replay_seqs = [f.frame_seq for f in result.replay_frames]
    assert replay_seqs == [5, 6, 7, 8, 9]


# ---------------------------------------------------------------------------
# Scenario 2: Fresh TUI (last_seen_frame_seq = None) → full buffer replay
# ---------------------------------------------------------------------------


def test_fresh_tui_full_replay(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 2: last_seen_frame_seq=None → replay all 8 frames in ring."""
    session_id = "s-002"
    token = "tok-002"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=8)

    mgr.register_session(session_id, token, ring)

    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=None,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeResponseFrame)
    resp = result.response
    assert resp.replay_count == 8
    assert resp.resumed_from_frame_seq == 0
    assert len(result.replay_frames) == 8


# ---------------------------------------------------------------------------
# Scenario 3: Ring eviction (last_seen_frame_seq < oldest_in_ring)
# ---------------------------------------------------------------------------


def test_ring_evicted_rejection(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 3: ring has frames 10..25, TUI asks for last_seen=5 → ring_evicted."""
    session_id = "s-003"
    token = "tok-003"
    mgr = ResumeManager()
    # Use size=4 so we can easily fill and overflow
    ring = _make_ring(session_id, size=4)
    # Fill with 16 frames — ring overflows, oldest remaining seq = 12
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=16)

    mgr.register_session(session_id, token, ring)

    # TUI claims last_seen=5 which is older than oldest buffered frame
    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=5,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeRejectedFrame)
    rejected: ResumeRejectedFrame = result.response
    assert rejected.reason == RejectionReason.RING_EVICTED
    assert rejected.trailer is not None and rejected.trailer.final is True
    assert len(result.replay_frames) == 0
    # Detail must be a non-empty string
    assert rejected.detail


# ---------------------------------------------------------------------------
# Scenario 4: Token mismatch
# ---------------------------------------------------------------------------


def test_token_mismatch_rejection(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 4: wrong tui_session_token → token_mismatch rejection."""
    session_id = "s-004"
    token = "tok-004"
    wrong_token = "wrong-token"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=3)

    mgr.register_session(session_id, token, ring)

    request = _make_resume_request(
        session_id=session_id,
        token=wrong_token,
        last_seen_frame_seq=2,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeRejectedFrame)
    assert result.response.reason == RejectionReason.TOKEN_MISMATCH
    assert result.response.trailer is not None and result.response.trailer.final is True
    assert len(result.replay_frames) == 0


# ---------------------------------------------------------------------------
# Scenario 5: Unknown session
# ---------------------------------------------------------------------------


def test_session_unknown_rejection(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 5: session_id not registered → session_unknown rejection."""
    mgr = ResumeManager()

    request = _make_resume_request(
        session_id="nonexistent-session",
        token="any-token",
        last_seen_frame_seq=0,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeRejectedFrame)
    assert result.response.reason == RejectionReason.SESSION_UNKNOWN
    assert result.response.trailer is not None and result.response.trailer.final is True


# ---------------------------------------------------------------------------
# Scenario 6: Double resume — idempotent
# ---------------------------------------------------------------------------


def test_double_resume_idempotent(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 6: Same last_seen_frame_seq submitted twice → both succeed, same replay window."""
    session_id = "s-006"
    token = "tok-006"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=7)

    mgr.register_session(session_id, token, ring)

    def _do_resume() -> ResumeResponseFrame:
        request = _make_resume_request(
            session_id=session_id,
            token=token,
            last_seen_frame_seq=3,
            correlation_id=make_uuid7(),
            ts=fake_clock.utcnow_str(),
        )
        result = mgr.handle_resume_request(
            request,
            new_correlation_id=make_uuid7(),
            ts=fake_clock.utcnow_str(),
        )
        assert isinstance(result.response, ResumeResponseFrame)
        return result.response

    r1 = _do_resume()
    r2 = _do_resume()

    # Both responses must have the same semantics
    assert r1.replay_count == r2.replay_count == 3
    assert r1.resumed_from_frame_seq == r2.resumed_from_frame_seq == 4


# ---------------------------------------------------------------------------
# Scenario 7: Resume during simulated backpressure — response always returned
# ---------------------------------------------------------------------------


def test_resume_during_backpressure(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 7: BackpressureSignalFrame doesn't affect ResumeManager response."""
    session_id = "s-007"
    token = "tok-007"
    mgr = ResumeManager()
    # Fill ring to above HWM to simulate backpressure condition (depth > hwm)
    ring = _make_ring(session_id, size=16)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=15)

    mgr.register_session(session_id, token, ring)

    # ResumeManager response MUST complete regardless of ring depth
    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=10,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    # Should succeed — backpressure state is orthogonal to resume validation
    assert isinstance(result.response, ResumeResponseFrame)
    assert result.response.replay_count == 4  # frames 11..14


# ---------------------------------------------------------------------------
# Scenario 8: Heartbeat dead → resume within grace → recovered
# ---------------------------------------------------------------------------


def test_heartbeat_dead_resume_within_grace(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 8: Peer declared dead; resume arrives before grace expires → HEALTHY."""
    session_id = "s-008"
    settings = HeartbeatSettings(
        heartbeat_interval_ms=500,
        heartbeat_dead_ms=1500,
        heartbeat_grace_ms=5000,
    )
    hb = HeartbeatState(session_id=session_id, settings=settings)
    # Anchor the channel open time to the fake clock's origin
    hb._channel_open_ts = fake_clock.now

    # Advance past dead threshold
    fake_clock.advance(seconds=2.0)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.DEAD
    assert hb.dead_declared

    # Within grace window — advance only 2s (< 5s grace)
    fake_clock.advance(seconds=2.0)
    assert not hb.should_gc_ring(now=fake_clock.now), "Ring should NOT be GC'd within grace"

    # Simulate successful resume (notified by ResumeManager after success)
    hb.notify_resume_success()

    # HeartbeatState should now be healthy
    assert not hb.dead_declared
    state_after = hb.tick(now=fake_clock.now)
    assert state_after == DeadlineState.HEALTHY


# ---------------------------------------------------------------------------
# Scenario 9: Heartbeat dead → resume after grace → session_unknown
# ---------------------------------------------------------------------------


def test_heartbeat_dead_resume_after_grace(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """Scenario 9: Grace window expired → should_gc_ring=True → session_unknown."""
    session_id = "s-009"
    token = "tok-009"
    settings = HeartbeatSettings(
        heartbeat_interval_ms=500,
        heartbeat_dead_ms=1500,
        heartbeat_grace_ms=3000,
    )
    hb = HeartbeatState(session_id=session_id, settings=settings)
    # Anchor channel open time to fake clock origin
    hb._channel_open_ts = fake_clock.now

    # Advance past dead threshold
    fake_clock.advance(seconds=2.0)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.DEAD

    # Advance past grace window
    fake_clock.advance(seconds=4.0)  # total 6s > 3s grace
    assert hb.should_gc_ring(now=fake_clock.now), "Ring SHOULD be GC'd after grace"

    # After grace expiry, the ring is GC'd — caller removes from session manager.
    # Simulate: mgr does not have the session (ring was dropped)
    mgr = ResumeManager()  # Fresh manager — session not registered (post-GC)
    ring = _make_ring(session_id)
    _fill_ring(ring, make_uuid7(), make_uuid7(), fake_clock.utcnow_str(), count=5)
    # NOTE: We do NOT register the session, simulating post-GC state

    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=2,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeRejectedFrame)
    assert result.response.reason == RejectionReason.SESSION_UNKNOWN


# ---------------------------------------------------------------------------
# Additional: resumed_from_frame_seq invariant (contract § 6)
# ---------------------------------------------------------------------------


def test_resumed_from_strictly_greater_than_last_seen(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """resumed_from_frame_seq == last_seen_frame_seq + 1 (contract § 6)."""
    session_id = "s-010"
    token = "tok-010"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=6)

    mgr.register_session(session_id, token, ring)

    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=2,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeResponseFrame)
    assert result.response.resumed_from_frame_seq == 3  # last_seen + 1


def test_replay_count_equals_replay_frames_length(
    fake_clock: FakeClock,
    make_uuid7: UUIDv7Factory,
) -> None:
    """replay_count field must match len(replay_frames) (contract § 6)."""
    session_id = "s-011"
    token = "tok-011"
    mgr = ResumeManager()
    ring = _make_ring(session_id)
    _fill_ring(ring, session_id, make_uuid7(), fake_clock.utcnow_str(), count=10)

    mgr.register_session(session_id, token, ring)

    request = _make_resume_request(
        session_id=session_id,
        token=token,
        last_seen_frame_seq=1,
        correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )
    result = mgr.handle_resume_request(
        request,
        new_correlation_id=make_uuid7(),
        ts=fake_clock.utcnow_str(),
    )

    assert isinstance(result.response, ResumeResponseFrame)
    assert result.response.replay_count == len(result.replay_frames)
