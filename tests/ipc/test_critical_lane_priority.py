# SPDX-License-Identifier: Apache-2.0
"""Critical-lane bypass test — FR-017 / SC-009 (Spec 032 T061).

Proves that ``severity=critical`` frames — CBS 재난문자 (``notification_push`` with
``adapter_id="disaster_alert_cbs_push"``) and terminal ``error`` frames — bypass
the pause gate regardless of ring/queue state.

Invariants asserted:

* :func:`~kosmos.ipc.backpressure.is_critical_lane` classifies the expected kinds.
* :meth:`BackpressureController.check_critical_bypass` raises
  :class:`CriticalLaneBypassError` when the controller is paused **and** the
  frame is critical, and stays silent otherwise.
* p95 classification latency < 16 ms (SC-009 — 1 animation frame @60 Hz).
* Ordering invariant: in an interleaved critical/non-critical stream, every
  critical frame is routed to the bypass lane (raises) *before* any queued
  non-critical frame can drain.  The critical batch's own arrival order is
  preserved (FIFO).

Legal basis: 재난 및 안전관리 기본법 §38 — 재난경보 전송 의무.
"""

from __future__ import annotations

import time
from statistics import quantiles
from typing import Final

import pytest

from kosmos.ipc.backpressure import (
    BackpressureController,
    CriticalLaneBypassError,
    is_critical_lane,
)
from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    ErrorFrame,
    IPCFrame,
    NotificationPushFrame,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SESSION_ID: Final[str] = "sess-critical-lane"
CORRELATION_ID: Final[str] = "019da5b0-e60d-71a0-a393-000000000042"
_BASE_ENVELOPE = {
    "session_id": SESSION_ID,
    "correlation_id": CORRELATION_ID,
    "ts": "2026-04-19T12:00:00.000Z",
    "transaction_id": None,
    "trailer": None,
}

# SC-009 — disaster-alert lane p95 < 16 ms @ 60 Hz.
P95_LATENCY_BUDGET_NS: Final[int] = 16_000_000  # 16 ms
CRITICAL_BATCH_SIZE: Final[int] = 10


def _critical_frame(seq: int) -> NotificationPushFrame:
    """CBS 재난문자 push — legally mandated critical lane."""
    return NotificationPushFrame(
        **_BASE_ENVELOPE,
        role="notification",
        frame_seq=seq,
        kind="notification_push",
        subscription_id="sub-cbs-001",
        adapter_id="disaster_alert_cbs_push",
        event_guid=f"event-{seq:04d}",
        payload_content_type="text/plain",
        payload="재난 경보: 즉시 대피",
    )


def _non_critical_frame(seq: int) -> AssistantChunkFrame:
    """Ordinary chunk — must honour the pause gate."""
    return AssistantChunkFrame(
        **_BASE_ENVELOPE,
        role="backend",
        frame_seq=seq,
        kind="assistant_chunk",
        message_id=f"01HN-assistant-{seq:04d}",
        delta="서울시 강남구 응급실 병상 조회 중…",
        done=False,
    )


def _paused_controller() -> BackpressureController:
    """Return a controller whose ``backend_writer`` lane is paused at HWM."""
    ctrl = BackpressureController(
        session_id=SESSION_ID,
        hwm=64,
        correlation_id=CORRELATION_ID,
    )
    # Cross HWM to enter paused state — this is the precondition FR-017
    # guards against: the writer has queued up and would otherwise hold
    # critical frames behind an open pause.
    pause_frame = ctrl.emit_backend_writer_congested(
        depth=100,
        ts=_BASE_ENVELOPE["ts"],
        frame_seq=0,
    )
    assert pause_frame is not None
    assert ctrl.any_paused(), "fixture precondition: controller must be paused"
    return ctrl


# ---------------------------------------------------------------------------
# Test 1 — classifier coverage
# ---------------------------------------------------------------------------


def test_is_critical_lane_notification_disaster_alert() -> None:
    """CBS 재난문자 push → critical."""
    assert is_critical_lane(_critical_frame(seq=1)) is True


def test_is_critical_lane_error_frame() -> None:
    """Terminal error frames must bypass the gate to avoid silent session death."""
    error_frame = ErrorFrame(
        **_BASE_ENVELOPE,
        role="backend",
        frame_seq=1,
        kind="error",
        code="backend_crash",
        message="backend crashed — 백엔드 충돌",
        details={"recoverable": False},
    )
    assert is_critical_lane(error_frame) is True


def test_is_critical_lane_regular_chunk_is_not_critical() -> None:
    """Ordinary assistant chunks must not bypass the gate."""
    assert is_critical_lane(_non_critical_frame(seq=1)) is False


def test_is_critical_lane_non_disaster_notification_is_not_critical() -> None:
    """Non-CBS notification subscriptions use normal routing."""
    rss_frame = NotificationPushFrame(
        **_BASE_ENVELOPE,
        role="notification",
        frame_seq=1,
        kind="notification_push",
        subscription_id="sub-rss-001",
        adapter_id="rss_newsroom_subscribe",
        event_guid="rss-guid-001",
        payload_content_type="application/json",
        payload='{"title": "일반 뉴스"}',
    )
    assert is_critical_lane(rss_frame) is False


# ---------------------------------------------------------------------------
# Test 2 — gate behaviour (paused controller)
# ---------------------------------------------------------------------------


def test_check_critical_bypass_raises_for_critical_when_paused() -> None:
    """Paused controller + critical frame → CriticalLaneBypassError."""
    ctrl = _paused_controller()
    frame = _critical_frame(seq=1)
    with pytest.raises(CriticalLaneBypassError) as exc_info:
        ctrl.check_critical_bypass(frame)
    # Frame identity preserved for telemetry.
    assert exc_info.value.frame is frame


def test_check_critical_bypass_silent_for_non_critical_when_paused() -> None:
    """Paused controller + non-critical frame → no raise (caller queues normally)."""
    ctrl = _paused_controller()
    frame = _non_critical_frame(seq=1)
    # Must return None without raising.
    assert ctrl.check_critical_bypass(frame) is None


def test_check_critical_bypass_silent_when_not_paused() -> None:
    """Un-paused controller → critical frames flow through normal path (no raise)."""
    ctrl = BackpressureController(
        session_id=SESSION_ID,
        correlation_id=CORRELATION_ID,
    )
    assert not ctrl.any_paused()
    assert ctrl.check_critical_bypass(_critical_frame(seq=1)) is None


# ---------------------------------------------------------------------------
# Test 3 — SC-009 latency + ordering invariant
# ---------------------------------------------------------------------------


def test_critical_lane_p95_latency_and_ordering_under_pause() -> None:
    """Interleaved 10 × critical + 10 × non-critical under pause:

    * Every critical frame raises on the gate (bypass signal fired).
    * Every non-critical frame returns None (would be queued by caller).
    * p95 critical-frame gate latency < 16 ms (SC-009).
    * The 10 critical frames are released in arrival order (FIFO); no
      non-critical frame is evaluated *before* the critical frame that
      preceded it — so the critical batch cannot be delayed behind
      queued non-critical work.
    """
    ctrl = _paused_controller()

    # Interleaved: critical at even seqs, non-critical at odd seqs.
    # seqs start at 10 (after the fixture pause frame used frame_seq=0).
    interleaved: list[tuple[str, IPCFrame]] = []
    for i in range(CRITICAL_BATCH_SIZE):
        interleaved.append(("critical", _critical_frame(seq=10 + i * 2)))
        interleaved.append(("non_critical", _non_critical_frame(seq=11 + i * 2)))

    critical_latencies_ns: list[int] = []
    critical_release_order: list[int] = []
    non_critical_queued: list[int] = []

    for label, frame in interleaved:
        start = time.perf_counter_ns()
        try:
            ctrl.check_critical_bypass(frame)
        except CriticalLaneBypassError as exc:
            elapsed = time.perf_counter_ns() - start
            assert label == "critical", (
                f"non-critical frame raised CriticalLaneBypassError — "
                f"ordering invariant violated at seq={frame.frame_seq}"
            )
            assert exc.frame is frame
            critical_latencies_ns.append(elapsed)
            critical_release_order.append(frame.frame_seq)
        else:
            elapsed = time.perf_counter_ns() - start
            assert label == "non_critical", (
                f"critical frame did not raise at seq={frame.frame_seq} — FR-017 bypass missed"
            )
            non_critical_queued.append(frame.frame_seq)

    # 1. All critical frames fired the bypass; all non-critical were "queued".
    assert len(critical_latencies_ns) == CRITICAL_BATCH_SIZE
    assert len(non_critical_queued) == CRITICAL_BATCH_SIZE

    # 2. Critical release order preserved arrival order (FIFO within the lane).
    expected_critical_seqs = [10 + i * 2 for i in range(CRITICAL_BATCH_SIZE)]
    assert critical_release_order == expected_critical_seqs, (
        "critical-lane FIFO violated — CBS frames must emerge in arrival order"
    )

    # 3. p95 latency < 16 ms (SC-009).  Use quantiles with n=100 for percentile
    #    granularity; with only 10 samples this approximates 95th percentile
    #    as the 10th-sample slice — sufficient for the guard test.
    cutoffs = quantiles(critical_latencies_ns, n=100, method="inclusive")
    p95_ns = cutoffs[94]  # 95th percentile cutoff
    assert p95_ns < P95_LATENCY_BUDGET_NS, (
        f"SC-009 violated: p95 critical-lane gate latency {p95_ns} ns "
        f">= budget {P95_LATENCY_BUDGET_NS} ns (16 ms) — "
        f"samples (ns)={critical_latencies_ns}"
    )
