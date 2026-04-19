# SPDX-License-Identifier: Apache-2.0
"""Tests for BackpressureController — Spec 032 T037.

Contract coverage (contracts/tx-dedup.contract.md § 5.1 Backpressure matrix):

Scenario 1  Queue depth crosses 64               → exactly one ``pause`` emitted
Scenario 2  Queue drains to 31                   → exactly one ``resume`` emitted
Scenario 3  Queue oscillates 60↔64 repeatedly    → at most one ``pause`` (hysteresis holds)
Scenario 4  Upstream 429 during idle queue        → ``throttle`` emitted, no ``pause``
Scenario 5  Session teardown with outstanding pause → synthetic ``resume`` before terminal error
Scenario 6  HUD copy interpolation (retry_after=15)
            → "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다."
Additional  Retry-After clamp [1000, 900000] ms   → below min clamped, above max clamped
Additional  dual-locale min_length                → tested in test_backpressure_dual_locale.py
"""

from __future__ import annotations

import pytest

from kosmos.ipc.backpressure import BackpressureController
from kosmos.ipc.frame_schema import BackpressureSignalFrame

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ctrl() -> BackpressureController:
    """Return a fresh BackpressureController with default HWM=64."""
    return BackpressureController(
        session_id="test-session",
        hwm=64,
        correlation_id="test-corr-id",
    )


def _frame(signal: str, source: str, depth: int) -> BackpressureSignalFrame:
    """Helper: build a minimal BackpressureSignalFrame for assertions."""
    return BackpressureSignalFrame(
        session_id="s",
        correlation_id="c",
        ts="2026-04-19T12:00:00+00:00",
        version="1.0",
        role="backend",
        frame_seq=0,
        transaction_id=None,
        trailer=None,
        kind="backpressure",
        signal=signal,  # type: ignore[arg-type]
        source=source,  # type: ignore[arg-type]
        queue_depth=depth,
        hwm=64,
        retry_after_ms=None,
        hud_copy_ko="서비스가 일시적으로 지연됩니다. 잠시 기다려 주세요.",
        hud_copy_en="Backpressure detected.",
    )


# ---------------------------------------------------------------------------
# Scenario 1 — Queue crosses HWM → exactly one pause emitted
# ---------------------------------------------------------------------------


def test_pause_emitted_at_hwm(ctrl: BackpressureController) -> None:
    """Crossing depth=64 should emit exactly one pause frame."""
    result = ctrl.tick(depth=64, source="backend_writer")
    assert result is not None
    assert result.signal == "pause"
    assert result.source == "backend_writer"
    assert result.queue_depth == 64
    assert result.hwm == 64


def test_no_duplicate_pause_above_hwm(ctrl: BackpressureController) -> None:
    """Second tick at depth=65 (already paused) must be no-op."""
    ctrl.tick(depth=64, source="backend_writer")   # pauses
    result = ctrl.tick(depth=65, source="backend_writer")  # already paused → no-op
    assert result is None


# ---------------------------------------------------------------------------
# Scenario 2 — Queue drains to ≤ HWM/2 → exactly one resume emitted
# ---------------------------------------------------------------------------


def test_resume_emitted_after_drain(ctrl: BackpressureController) -> None:
    """After pause, draining to depth=31 (< 32) emits resume."""
    ctrl.tick(depth=64, source="backend_writer")   # pause
    result = ctrl.tick(depth=31, source="backend_writer")
    assert result is not None
    assert result.signal == "resume"
    assert result.source == "backend_writer"
    assert result.queue_depth == 31


def test_resume_at_exact_threshold(ctrl: BackpressureController) -> None:
    """Draining to exactly HWM/2=32 does NOT emit resume (boundary: threshold is < 32)."""
    ctrl.tick(depth=64, source="backend_writer")
    result = ctrl.tick(depth=32, source="backend_writer")
    # HWM/2 = 32; resume condition is depth <= hwm/2 i.e. depth <= 32 → resume
    # Contract says "depth ≤ hwm/2=32 → resume"; so 32 is inclusive.
    assert result is not None
    assert result.signal == "resume"


def test_no_duplicate_resume(ctrl: BackpressureController) -> None:
    """Second drain call (already resumed) must be no-op."""
    ctrl.tick(depth=64, source="backend_writer")
    ctrl.tick(depth=31, source="backend_writer")   # resume
    result = ctrl.tick(depth=20, source="backend_writer")  # already resumed → no-op
    assert result is None


# ---------------------------------------------------------------------------
# Scenario 3 — Oscillation 60↔64 → at most one pause (hysteresis)
# ---------------------------------------------------------------------------


def test_hysteresis_oscillation_emits_at_most_one_pause(ctrl: BackpressureController) -> None:
    """Queue oscillating 60↔64 must not emit multiple pause frames.

    Contract § 5.1 row 3: 'Queue oscillates 60↔64 repeatedly → At most one pause'.
    """
    signals: list[str] = []

    # First crossing: 60→64 → should emit pause
    result = ctrl.tick(depth=64, source="backend_writer")
    if result is not None:
        signals.append(result.signal)

    # Oscillate within (32, 64) — hysteresis band — many times
    for _ in range(10):
        for depth in (60, 63, 61, 64, 62):
            result = ctrl.tick(depth=depth, source="backend_writer")
            if result is not None:
                signals.append(result.signal)

    # Count pause signals
    pause_count = signals.count("pause")
    assert pause_count <= 1, (
        f"Expected at most 1 pause, got {pause_count}. Signals: {signals}"
    )


def test_hysteresis_band_no_op(ctrl: BackpressureController) -> None:
    """Ticks in band (33..63) with no prior pause → no signal."""
    for depth in range(33, 64):
        result = ctrl.tick(depth=depth, source="backend_writer")
        assert result is None, f"Unexpected signal at depth={depth}: {result}"


# ---------------------------------------------------------------------------
# Scenario 4 — upstream_429 → throttle, not pause; no pause/resume pairing
# ---------------------------------------------------------------------------


def test_upstream_429_emits_throttle(ctrl: BackpressureController) -> None:
    """upstream_429 path emits throttle, NOT pause."""
    result = ctrl.emit_upstream_429(retry_after_header=15, queue_depth=48)
    assert result is not None
    assert result.signal == "throttle"
    assert result.source == "upstream_429"
    assert result.retry_after_ms == 15_000  # 15s * 1000 = 15000 ms


def test_upstream_429_does_not_set_paused_state(ctrl: BackpressureController) -> None:
    """upstream_429 throttle must NOT affect the pause/resume state machine."""
    ctrl.emit_upstream_429(retry_after_header=10)
    # After throttle, no outstanding pause → teardown returns empty list
    synth = ctrl.emit_teardown_resumes()
    assert synth == [], "Throttle must not create an outstanding pause"


def test_upstream_429_idle_queue_no_pause(ctrl: BackpressureController) -> None:
    """Contract § 5.1 row 4: 'Upstream 429 during idle queue → throttle, no pause'."""
    result = ctrl.emit_upstream_429(retry_after_header=5, queue_depth=0)
    assert result.signal == "throttle"
    assert not ctrl.is_paused("backend_writer")


def test_upstream_429_tick_raises_for_upstream_source(ctrl: BackpressureController) -> None:
    """Calling tick() with source='upstream_429' must raise ValueError."""
    with pytest.raises(ValueError, match="emit_upstream_429"):
        ctrl.tick(depth=64, source="upstream_429")


# ---------------------------------------------------------------------------
# Retry-After parsing and clamp [1000, 900000] ms
# ---------------------------------------------------------------------------


def test_retry_after_seconds_int(ctrl: BackpressureController) -> None:
    """Integer Retry-After=15 → retry_after_ms=15000."""
    result = ctrl.emit_upstream_429(retry_after_header=15)
    assert result.retry_after_ms == 15_000


def test_retry_after_seconds_string(ctrl: BackpressureController) -> None:
    """String '30' → retry_after_ms=30000."""
    result = ctrl.emit_upstream_429(retry_after_header="30")
    assert result.retry_after_ms == 30_000


def test_retry_after_clamp_min(ctrl: BackpressureController) -> None:
    """Retry-After=0 → clamped to 1000 ms (minimum)."""
    result = ctrl.emit_upstream_429(retry_after_header=0)
    assert result.retry_after_ms == 1_000


def test_retry_after_clamp_max(ctrl: BackpressureController) -> None:
    """Retry-After=9999 seconds → clamped to 900000 ms (maximum)."""
    result = ctrl.emit_upstream_429(retry_after_header=9999)
    assert result.retry_after_ms == 900_000


def test_retry_after_none_clamps_to_min(ctrl: BackpressureController) -> None:
    """None Retry-After → clamped to 1000 ms minimum."""
    result = ctrl.emit_upstream_429(retry_after_header=None)
    assert result.retry_after_ms == 1_000


def test_retry_after_invalid_string_clamps_to_min(ctrl: BackpressureController) -> None:
    """Unparseable date string → clamped to 1000 ms minimum."""
    result = ctrl.emit_upstream_429(retry_after_header="not-a-date")
    assert result.retry_after_ms == 1_000


def test_retry_after_boundary_1s(ctrl: BackpressureController) -> None:
    """Retry-After=1 → 1000 ms (exactly the minimum)."""
    result = ctrl.emit_upstream_429(retry_after_header=1)
    assert result.retry_after_ms == 1_000


def test_retry_after_boundary_900s(ctrl: BackpressureController) -> None:
    """Retry-After=900 → 900000 ms (exactly the maximum)."""
    result = ctrl.emit_upstream_429(retry_after_header=900)
    assert result.retry_after_ms == 900_000


# ---------------------------------------------------------------------------
# Scenario 5 — Teardown with outstanding pause → synthetic resume
# ---------------------------------------------------------------------------


def test_teardown_synthetic_resume_emitted(ctrl: BackpressureController) -> None:
    """Contract § 5.1 row 5: outstanding pause at teardown → synthetic resume."""
    ctrl.tick(depth=64, source="backend_writer")  # sets pause
    assert ctrl.is_paused("backend_writer")

    synth = ctrl.emit_teardown_resumes(depth=0)
    assert len(synth) == 1
    frame = synth[0]
    assert frame.signal == "resume"
    assert frame.source == "backend_writer"
    assert frame.queue_depth == 0


def test_teardown_no_outstanding_pause_empty(ctrl: BackpressureController) -> None:
    """Teardown with no outstanding pause emits nothing."""
    synth = ctrl.emit_teardown_resumes()
    assert synth == []


def test_teardown_clears_paused_state(ctrl: BackpressureController) -> None:
    """After teardown, is_paused() returns False."""
    ctrl.tick(depth=64, source="backend_writer")
    ctrl.emit_teardown_resumes()
    assert not ctrl.is_paused("backend_writer")


def test_teardown_two_sources_both_paused(ctrl: BackpressureController) -> None:
    """Teardown with two paused sources emits two synthetic resumes."""
    ctrl.tick(depth=64, source="backend_writer")
    ctrl.tick(depth=64, source="tui_reader")  # This also pauses tui_reader
    synth = ctrl.emit_teardown_resumes()
    sources = {f.source for f in synth}
    assert sources == {"backend_writer", "tui_reader"}
    assert all(f.signal == "resume" for f in synth)


# ---------------------------------------------------------------------------
# Scenario 6 — HUD copy interpolation
# ---------------------------------------------------------------------------


def test_hud_copy_ko_15s(ctrl: BackpressureController) -> None:
    """Contract § 5.1 row 6: retry_after=15 → Korean copy exact match."""
    result = ctrl.emit_upstream_429(retry_after_header=15, queue_depth=48)
    expected_ko = "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다."
    assert result.hud_copy_ko == expected_ko


def test_hud_copy_en_present(ctrl: BackpressureController) -> None:
    """English HUD copy must be non-empty for upstream_429 throttle."""
    result = ctrl.emit_upstream_429(retry_after_header=15)
    assert len(result.hud_copy_en) >= 1
    assert "15" in result.hud_copy_en


# ---------------------------------------------------------------------------
# Source-specific helpers (T033)
# ---------------------------------------------------------------------------


def test_emit_tui_reader_saturated(ctrl: BackpressureController) -> None:
    """emit_tui_reader_saturated() at depth=64 emits pause for tui_reader."""
    result = ctrl.emit_tui_reader_saturated(depth=64)
    assert result is not None
    assert result.signal == "pause"
    assert result.source == "tui_reader"


def test_drain_tui_reader(ctrl: BackpressureController) -> None:
    """drain_tui_reader() after saturation emits resume."""
    ctrl.emit_tui_reader_saturated(depth=64)
    result = ctrl.drain_tui_reader(depth=20)
    assert result is not None
    assert result.signal == "resume"
    assert result.source == "tui_reader"


def test_emit_backend_writer_congested(ctrl: BackpressureController) -> None:
    """emit_backend_writer_congested() at depth=64 emits pause."""
    result = ctrl.emit_backend_writer_congested(depth=64)
    assert result is not None
    assert result.signal == "pause"
    assert result.source == "backend_writer"


def test_drain_backend_writer(ctrl: BackpressureController) -> None:
    """drain_backend_writer() after congestion emits resume."""
    ctrl.emit_backend_writer_congested(depth=64)
    result = ctrl.drain_backend_writer(depth=15)
    assert result is not None
    assert result.signal == "resume"
    assert result.source == "backend_writer"


# ---------------------------------------------------------------------------
# Frame schema validation
# ---------------------------------------------------------------------------


def test_backpressure_frame_validates(ctrl: BackpressureController) -> None:
    """The emitted frame must pass Pydantic validation (BackpressureSignalFrame)."""
    result = ctrl.tick(depth=64, source="backend_writer")
    assert isinstance(result, BackpressureSignalFrame)


def test_upstream_429_frame_validates(ctrl: BackpressureController) -> None:
    """upstream_429 frame must pass Pydantic validation."""
    result = ctrl.emit_upstream_429(retry_after_header=30)
    assert isinstance(result, BackpressureSignalFrame)
    assert result.retry_after_ms is not None


def test_hud_copy_non_empty_pause(ctrl: BackpressureController) -> None:
    """HUD copy on pause frame must be non-empty (FR-015)."""
    result = ctrl.tick(depth=64, source="backend_writer")
    assert result is not None
    assert len(result.hud_copy_ko) >= 1
    assert len(result.hud_copy_en) >= 1


def test_hud_copy_non_empty_resume(ctrl: BackpressureController) -> None:
    """HUD copy on resume frame must be non-empty (FR-015)."""
    ctrl.tick(depth=64, source="backend_writer")
    result = ctrl.tick(depth=20, source="backend_writer")
    assert result is not None
    assert len(result.hud_copy_ko) >= 1
    assert len(result.hud_copy_en) >= 1


# ---------------------------------------------------------------------------
# is_paused / any_paused state queries
# ---------------------------------------------------------------------------


def test_is_paused_false_initially(ctrl: BackpressureController) -> None:
    assert not ctrl.is_paused("backend_writer")
    assert not ctrl.is_paused("tui_reader")


def test_is_paused_true_after_pause(ctrl: BackpressureController) -> None:
    ctrl.tick(depth=64, source="backend_writer")
    assert ctrl.is_paused("backend_writer")


def test_any_paused_reflects_any_source(ctrl: BackpressureController) -> None:
    assert not ctrl.any_paused()
    ctrl.tick(depth=64, source="tui_reader")
    assert ctrl.any_paused()
    ctrl.tick(depth=20, source="tui_reader")  # resume
    assert not ctrl.any_paused()
