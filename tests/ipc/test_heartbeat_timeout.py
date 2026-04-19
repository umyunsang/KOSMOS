# SPDX-License-Identifier: Apache-2.0
"""Test: HeartbeatState — 45s dead threshold, 120s grace window (Spec 032 T029).

Tests the 30s/45s/120s model from data-model.md §5 and contract §5:
- HEALTHY when activity within dead_threshold_ms.
- DEAD after dead_threshold_ms of silence.
- GRACE while grace window open after dead declaration.
- DEAD again (GC signal) when grace window expires.
- notify_resume_success() resets dead state.
- should_gc_ring() returns True only after grace expires.
- HeartbeatFrame ping/pong recording symmetry.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from kosmos.ipc.heartbeat import DeadlineState, HeartbeatSettings, HeartbeatState
from tests.ipc.conftest import FakeClock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hb(
    session_id: str = "s-hb-001",
    interval_ms: int = 500,
    dead_ms: int = 1500,
    grace_ms: int = 5000,
    start_ts: datetime | None = None,
) -> HeartbeatState:
    settings = HeartbeatSettings(
        heartbeat_interval_ms=interval_ms,
        heartbeat_dead_ms=dead_ms,
        heartbeat_grace_ms=grace_ms,
    )
    hb = HeartbeatState(session_id=session_id, settings=settings)
    if start_ts is not None:
        # Override _channel_open_ts to anchor to the fake clock's origin.
        # This ensures elapsed-time calculations are deterministic in tests.
        hb._channel_open_ts = start_ts
    return hb


# ---------------------------------------------------------------------------
# Basic lifecycle
# ---------------------------------------------------------------------------


def test_initial_state_healthy(fake_clock: FakeClock) -> None:
    """Immediately after construction, tick() returns HEALTHY."""
    hb = _make_hb(start_ts=fake_clock.now)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY
    assert not hb.dead_declared


def test_healthy_before_dead_threshold(fake_clock: FakeClock) -> None:
    """Tick at t=1.4s (< 1.5s dead_ms) returns HEALTHY."""
    hb = _make_hb(start_ts=fake_clock.now)
    fake_clock.advance(seconds=1.4)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY


def test_dead_after_dead_threshold(fake_clock: FakeClock) -> None:
    """Tick at t=1.5s (== dead_ms) → DEAD; dead_declared latched."""
    hb = _make_hb(start_ts=fake_clock.now)
    fake_clock.advance(seconds=1.5)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.DEAD
    assert hb.dead_declared
    assert hb.dead_declared_ts is not None


def test_dead_after_exceeds_dead_threshold(fake_clock: FakeClock) -> None:
    """Tick at t=2.0s (> dead_ms) → DEAD."""
    hb = _make_hb(start_ts=fake_clock.now)
    fake_clock.advance(seconds=2.0)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.DEAD


def test_grace_state_immediately_after_dead_declare(fake_clock: FakeClock) -> None:
    """tick() returns GRACE on second call after dead is declared."""
    hb = _make_hb(start_ts=fake_clock.now)
    # Declare dead
    fake_clock.advance(seconds=1.5)
    s1 = hb.tick(now=fake_clock.now)
    assert s1 == DeadlineState.DEAD

    # Small advance — still within grace window
    fake_clock.advance(seconds=0.1)
    s2 = hb.tick(now=fake_clock.now)
    assert s2 == DeadlineState.GRACE


def test_grace_throughout_grace_window(fake_clock: FakeClock) -> None:
    """GRACE is returned for all ticks within the 5s grace window."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)

    # Declare dead at t=1.5s
    fake_clock.advance(seconds=1.5)
    s1 = hb.tick(now=fake_clock.now)
    assert s1 == DeadlineState.DEAD

    # At 1s into grace (t=2.5s total) → GRACE
    fake_clock.advance(seconds=1.0)
    assert hb.tick(now=fake_clock.now) == DeadlineState.GRACE

    # At 4.9s into grace (t=6.4s total) → GRACE
    fake_clock.advance(seconds=3.9)
    assert hb.tick(now=fake_clock.now) == DeadlineState.GRACE


def test_dead_after_grace_expires(fake_clock: FakeClock) -> None:
    """After grace window expires, tick() returns DEAD (GC signal)."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)

    fake_clock.advance(seconds=1.5)
    hb.tick(now=fake_clock.now)  # declare dead
    assert hb.dead_declared

    # Advance 6s past dead declaration (> 5s grace)
    fake_clock.advance(seconds=6.0)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.DEAD


# ---------------------------------------------------------------------------
# should_gc_ring
# ---------------------------------------------------------------------------


def test_should_gc_ring_false_when_healthy(fake_clock: FakeClock) -> None:
    """should_gc_ring is False when the peer is healthy."""
    hb = _make_hb(start_ts=fake_clock.now)
    assert not hb.should_gc_ring(now=fake_clock.now)


def test_should_gc_ring_false_within_grace(fake_clock: FakeClock) -> None:
    """should_gc_ring is False while dead but within grace window."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)
    fake_clock.advance(seconds=1.5)
    hb.tick(now=fake_clock.now)  # declare dead
    fake_clock.advance(seconds=2.0)  # 2s into grace (< 5s)
    assert not hb.should_gc_ring(now=fake_clock.now)


def test_should_gc_ring_true_after_grace(fake_clock: FakeClock) -> None:
    """should_gc_ring returns True once grace window has elapsed."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)
    fake_clock.advance(seconds=1.5)
    hb.tick(now=fake_clock.now)  # declare dead
    fake_clock.advance(seconds=6.0)  # past grace
    assert hb.should_gc_ring(now=fake_clock.now)


# ---------------------------------------------------------------------------
# Ping / pong recording
# ---------------------------------------------------------------------------


def test_record_ping_resets_idle_timer(fake_clock: FakeClock) -> None:
    """record_ping() refreshes last_peer_ping_ts → activity resets idle clock."""
    hb = _make_hb(dead_ms=1500, start_ts=fake_clock.now)

    # Advance close to dead threshold
    fake_clock.advance(seconds=1.3)
    # Receive a ping — resets activity time
    hb.record_ping(ts=fake_clock.now)
    assert hb.last_peer_ping_ts == fake_clock.now

    # Advance another 1.3s (total ~2.6s since start, but only 1.3s since last ping)
    fake_clock.advance(seconds=1.3)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY


def test_record_pong_resets_idle_timer(fake_clock: FakeClock) -> None:
    """record_pong() refreshes last_peer_pong_ts → activity resets idle clock."""
    hb = _make_hb(dead_ms=1500, start_ts=fake_clock.now)

    fake_clock.advance(seconds=1.3)
    hb.record_pong(ts=fake_clock.now)
    assert hb.last_peer_pong_ts == fake_clock.now

    fake_clock.advance(seconds=1.2)
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY


def test_record_ping_during_grace_recovers_session(fake_clock: FakeClock) -> None:
    """record_ping() within grace window → dead_declared reset → HEALTHY."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)

    fake_clock.advance(seconds=1.5)
    hb.tick(now=fake_clock.now)  # declare dead
    assert hb.dead_declared

    # Peer re-connects within grace and sends a ping
    fake_clock.advance(seconds=2.0)
    hb.record_ping(ts=fake_clock.now)

    # dead_declared should be reset
    assert not hb.dead_declared
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY


def test_ping_pong_symmetry(fake_clock: FakeClock) -> None:
    """Both ping and pong are accepted and recorded independently."""
    hb = _make_hb(start_ts=fake_clock.now)
    hb.record_ping(ts=fake_clock.now)
    t0 = hb.last_peer_ping_ts

    fake_clock.advance(seconds=0.5)
    hb.record_pong(ts=fake_clock.now)
    t1 = hb.last_peer_pong_ts

    assert t0 != t1
    assert hb.last_peer_ping_ts == t0
    assert hb.last_peer_pong_ts == t1


# ---------------------------------------------------------------------------
# notify_resume_success
# ---------------------------------------------------------------------------


def test_notify_resume_success_clears_dead_state(fake_clock: FakeClock) -> None:
    """notify_resume_success() resets dead_declared and dead_declared_ts."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)

    fake_clock.advance(seconds=1.5)
    hb.tick(now=fake_clock.now)
    assert hb.dead_declared

    hb.notify_resume_success()
    assert not hb.dead_declared
    assert hb.dead_declared_ts is None


def test_notify_resume_success_sets_last_ping(fake_clock: FakeClock) -> None:
    """notify_resume_success() treats the resume as an implicit ping."""
    hb = _make_hb(dead_ms=1500, grace_ms=5000, start_ts=fake_clock.now)
    # Don't advance — just call directly
    hb.notify_resume_success()
    assert hb.last_peer_ping_ts is not None


def test_notify_resume_success_noop_when_healthy(fake_clock: FakeClock) -> None:
    """notify_resume_success() on a healthy session has no negative side effects."""
    hb = _make_hb(start_ts=fake_clock.now)
    hb.notify_resume_success()
    assert not hb.dead_declared
    state = hb.tick(now=fake_clock.now)
    assert state == DeadlineState.HEALTHY


# ---------------------------------------------------------------------------
# Session ID validation
# ---------------------------------------------------------------------------


def test_empty_session_id_raises(fake_clock: FakeClock) -> None:
    """HeartbeatState constructor rejects empty session_id."""
    with pytest.raises(ValueError, match="session_id"):
        HeartbeatState(session_id="")


# ---------------------------------------------------------------------------
# Default settings (30s / 45s / 120s)
# ---------------------------------------------------------------------------


def test_default_settings() -> None:
    """Default settings match spec: 30s interval, 45s dead, 120s grace."""
    settings = HeartbeatSettings()
    assert settings.heartbeat_interval_ms == 30_000
    assert settings.heartbeat_dead_ms == 45_000
    assert settings.heartbeat_grace_ms == 120_000


def test_default_interval_exposed_via_property() -> None:
    """ping_interval_ms / dead_threshold_ms / resume_grace_ms properties work."""
    hb = HeartbeatState(session_id="s-defaults")
    assert hb.ping_interval_ms == 30_000
    assert hb.dead_threshold_ms == 45_000
    assert hb.resume_grace_ms == 120_000
