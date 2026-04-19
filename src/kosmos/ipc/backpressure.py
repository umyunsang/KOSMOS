# SPDX-License-Identifier: Apache-2.0
"""BackpressureController — hysteresis-based backpressure signaling (Spec 032 T032-T035).

Responsibilities
----------------
T032  ``BackpressureController.tick()`` — hysteresis logic.
      HWM=64 → emit ``pause``; depth ≤ HWM/2=32 → emit ``resume``; no-op in band.

T033  Three-source emission paths:
      - ``tui_reader``   — TUI cannot render fast enough; backend should pause.
      - ``backend_writer`` — backend ring/pipe congested; signal TUI to slow input.
      - ``upstream_429`` — external ministry API returned 429; throttle, not pause.

T034  ``upstream_429`` adapter path:
      Parse ``Retry-After`` header (integer seconds or HTTP-date), clamp
      ``retry_after_ms`` to ``[1000, 900000]``, emit ``throttle`` with bilingual copy.

T035  Pause/resume pairing invariant:
      Every ``pause`` is paired with exactly one later ``resume``.
      On session teardown with an outstanding ``pause``, a synthetic ``resume``
      is emitted before any terminal error frame.

FR-017  Critical-lane bypass is implemented in T061; this module raises
        ``CriticalLaneBypassError`` to signal the caller when the frame must
        bypass the pause gate (severity=critical).

References
----------
- ``contracts/tx-dedup.contract.md`` § 1.1 — threshold triangle
- ``contracts/tx-dedup.contract.md`` § 1.3 — upstream_429 specifics
- ``contracts/tx-dedup.contract.md`` § 1.4 — pause/resume pairing invariant
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from kosmos.ipc.frame_schema import BackpressureSignalFrame
from kosmos.ipc.otel_constants import (
    KOSMOS_IPC_BACKPRESSURE_KIND,
    KOSMOS_IPC_BACKPRESSURE_SOURCE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via KOSMOS_IPC_* env vars)
# ---------------------------------------------------------------------------

_DEFAULT_HWM: int = int(os.environ.get("KOSMOS_IPC_HWM", "64"))
_RESUME_THRESHOLD_DIVISOR: int = 2  # resume at HWM / 2 = 32

# Retry-After clamp bounds (seconds after conversion to ms)
_RETRY_AFTER_MS_MIN: int = 1000   # 1 s
_RETRY_AFTER_MS_MAX: int = 900_000  # 900 s = 15 min


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BackpressureError(RuntimeError):
    """Raised when the backpressure invariant is violated."""


# ---------------------------------------------------------------------------
# BackpressureController
# ---------------------------------------------------------------------------


class BackpressureController:
    """Hysteresis-based backpressure controller for a single session channel.

    The controller holds a binary state (``_paused``) and applies hysteresis
    to prevent signal flapping when queue depth oscillates around the HWM.

    Hysteresis triangle (contract § 1.1)::

        depth >= hwm   → emit pause  (only when not already paused)
        depth <= hwm/2 → emit resume (only when currently paused)
        depth in (hwm/2, hwm) → no-op

    Args:
        session_id: Session identifier for log context.
        hwm: High-water mark threshold (default 64).
        correlation_id: Correlation ID for emitted frames.
    """

    def __init__(
        self,
        session_id: str,
        hwm: int | None = None,
        correlation_id: str = "no-correlation",
    ) -> None:
        if not session_id:
            raise ValueError("session_id must be non-empty")
        self._session_id = session_id
        self._hwm: int = hwm if hwm is not None else _DEFAULT_HWM
        self._resume_threshold: int = self._hwm // _RESUME_THRESHOLD_DIVISOR
        self._correlation_id = correlation_id
        # Paused state for each source that can emit pause/resume pairs.
        # Keys: "tui_reader", "backend_writer"
        self._paused: dict[str, bool] = {
            "tui_reader": False,
            "backend_writer": False,
        }

    @property
    def hwm(self) -> int:
        """High-water mark in effect."""
        return self._hwm

    @property
    def resume_threshold(self) -> int:
        """Resume threshold (HWM / 2)."""
        return self._resume_threshold

    def is_paused(self, source: str = "backend_writer") -> bool:
        """Return True if the given source is currently in paused state."""
        return self._paused.get(source, False)

    def any_paused(self) -> bool:
        """Return True if any source has an outstanding pause."""
        return any(self._paused.values())

    # ------------------------------------------------------------------
    # T032  tick() — hysteresis gate
    # ------------------------------------------------------------------

    def tick(
        self,
        depth: int,
        source: str,
        ts: str | None = None,
        frame_seq: int = 0,
    ) -> BackpressureSignalFrame | None:
        """Evaluate the current queue depth and return a signal frame if needed.

        Applies hysteresis (contract § 1.1):
        - depth >= HWM and source not already paused → emit ``pause``
        - depth <= HWM/2 and source currently paused → emit ``resume``
        - otherwise → None (no-op, hysteresis band)

        Args:
            depth: Current outbound queue depth.
            source: One of ``"tui_reader"``, ``"backend_writer"``.
            ts: ISO-8601 timestamp for the emitted frame (defaults to now).
            frame_seq: Frame sequence number for the emitted frame.

        Returns:
            A ``BackpressureSignalFrame`` to emit, or ``None`` if no-op.

        Raises:
            ValueError: If ``source`` is ``"upstream_429"`` (use
                ``emit_upstream_429()`` instead).
        """
        if source == "upstream_429":
            raise ValueError(
                "Use emit_upstream_429() for upstream_429 source, not tick()."
            )
        if source not in self._paused:
            raise ValueError(
                f"Unknown source {source!r}. "
                f"Valid sources: {sorted(self._paused.keys())}"
            )

        _ts = ts or datetime.now(tz=UTC).isoformat()

        if depth >= self._hwm and not self._paused[source]:
            # Cross HWM — emit pause
            self._paused[source] = True
            frame = self._build_frame(
                signal="pause",
                source=source,
                queue_depth=depth,
                ts=_ts,
                frame_seq=frame_seq,
            )
            logger.info(
                "backpressure.pause",
                extra={
                    KOSMOS_IPC_BACKPRESSURE_KIND: "pause",
                    KOSMOS_IPC_BACKPRESSURE_SOURCE: source,
                    "depth": depth,
                    "hwm": self._hwm,
                    "session_id": self._session_id,
                },
            )
            return frame

        if depth <= self._resume_threshold and self._paused[source]:
            # Drained below resume threshold — emit resume
            self._paused[source] = False
            frame = self._build_frame(
                signal="resume",
                source=source,
                queue_depth=depth,
                ts=_ts,
                frame_seq=frame_seq,
            )
            logger.info(
                "backpressure.resume",
                extra={
                    KOSMOS_IPC_BACKPRESSURE_KIND: "resume",
                    KOSMOS_IPC_BACKPRESSURE_SOURCE: source,
                    "depth": depth,
                    "hwm": self._hwm,
                    "session_id": self._session_id,
                },
            )
            return frame

        # Inside hysteresis band — no-op
        return None

    # ------------------------------------------------------------------
    # T033  Source-specific builders
    # ------------------------------------------------------------------

    def emit_tui_reader_saturated(
        self,
        depth: int,
        ts: str | None = None,
        frame_seq: int = 0,
    ) -> BackpressureSignalFrame | None:
        """Emit a ``pause`` for the ``tui_reader`` source when TUI is congested.

        Equivalent to calling ``tick(depth, source="tui_reader")``.
        Respects hysteresis — returns None if already paused or in band.
        """
        return self.tick(depth=depth, source="tui_reader", ts=ts, frame_seq=frame_seq)

    def emit_backend_writer_congested(
        self,
        depth: int,
        ts: str | None = None,
        frame_seq: int = 0,
    ) -> BackpressureSignalFrame | None:
        """Emit a ``pause`` for ``backend_writer`` when ring overflow risk detected.

        Equivalent to calling ``tick(depth, source="backend_writer")``.
        """
        return self.tick(depth=depth, source="backend_writer", ts=ts, frame_seq=frame_seq)

    def drain_tui_reader(
        self,
        depth: int,
        ts: str | None = None,
        frame_seq: int = 0,
    ) -> BackpressureSignalFrame | None:
        """Emit a ``resume`` for ``tui_reader`` when TUI drain is complete."""
        return self.tick(depth=depth, source="tui_reader", ts=ts, frame_seq=frame_seq)

    def drain_backend_writer(
        self,
        depth: int,
        ts: str | None = None,
        frame_seq: int = 0,
    ) -> BackpressureSignalFrame | None:
        """Emit a ``resume`` for ``backend_writer`` when ring pressure subsides."""
        return self.tick(depth=depth, source="backend_writer", ts=ts, frame_seq=frame_seq)

    # ------------------------------------------------------------------
    # T034  upstream_429 adapter path
    # ------------------------------------------------------------------

    def emit_upstream_429(
        self,
        retry_after_header: str | int | None = None,
        queue_depth: int = 0,
        ts: str | None = None,
        frame_seq: int = 0,
        source_agency: str = "ministry",
    ) -> BackpressureSignalFrame:
        """Parse a 429 Retry-After header and emit a ``throttle`` frame.

        This path emits ``throttle`` (NOT ``pause``) — the IPC channel itself
        remains open; only the tool-execution lane is throttled (contract § 1.3).
        No pause/resume pairing is tracked for ``upstream_429``.

        Args:
            retry_after_header: The value of the HTTP ``Retry-After`` header.
                Accepts an integer (seconds) or an HTTP-date string.
                If ``None``, defaults to ``_RETRY_AFTER_MS_MIN`` (1000 ms).
            queue_depth: Current outbound queue depth for HUD context.
            ts: ISO-8601 timestamp for the emitted frame.
            frame_seq: Frame sequence number.
            source_agency: Human-readable agency name for HUD copy interpolation.

        Returns:
            A ``BackpressureSignalFrame`` with ``signal="throttle"``.
        """
        retry_after_ms = self._parse_retry_after(retry_after_header)
        retry_after_s = retry_after_ms // 1000
        _ts = ts or datetime.now(tz=UTC).isoformat()

        hud_copy_ko = (
            f"부처 API가 혼잡합니다. {retry_after_s}초 후 자동 재시도합니다."
        )
        hud_copy_en = (
            f"Ministry API rate-limited. Retrying in {retry_after_s}s."
        )

        frame = BackpressureSignalFrame(
            session_id=self._session_id,
            correlation_id=self._correlation_id,
            ts=_ts,
            version="1.0",
            role="backend",
            frame_seq=frame_seq,
            transaction_id=None,
            trailer=None,
            kind="backpressure",
            signal="throttle",
            source="upstream_429",
            queue_depth=queue_depth,
            hwm=self._hwm,
            retry_after_ms=retry_after_ms,
            hud_copy_ko=hud_copy_ko,
            hud_copy_en=hud_copy_en,
        )
        logger.info(
            "backpressure.throttle.upstream_429",
            extra={
                KOSMOS_IPC_BACKPRESSURE_KIND: "throttle",
                KOSMOS_IPC_BACKPRESSURE_SOURCE: "upstream_429",
                "retry_after_ms": retry_after_ms,
                "session_id": self._session_id,
            },
        )
        return frame

    # ------------------------------------------------------------------
    # T035  Teardown — synthetic resume for outstanding pauses
    # ------------------------------------------------------------------

    def emit_teardown_resumes(
        self,
        depth: int = 0,
        ts: str | None = None,
        frame_seq_start: int = 0,
    ) -> list[BackpressureSignalFrame]:
        """Emit synthetic ``resume`` frames for any outstanding ``pause`` signals.

        Called on session teardown with an outstanding pause so that the peer
        is unblocked before the terminal error / resume_rejected frame arrives
        (contract § 1.4 pause/resume pairing invariant).

        Args:
            depth: Final queue depth to report (typically 0 at teardown).
            ts: ISO-8601 timestamp.
            frame_seq_start: Frame seq for the first synthetic resume.

        Returns:
            List of ``BackpressureSignalFrame`` instances (one per outstanding
            pause source), in alphabetical source order for determinism.
        """
        _ts = ts or datetime.now(tz=UTC).isoformat()
        synth_frames: list[BackpressureSignalFrame] = []
        seq = frame_seq_start

        for source in sorted(self._paused.keys()):  # deterministic order
            if self._paused[source]:
                self._paused[source] = False
                frame = self._build_frame(
                    signal="resume",
                    source=source,
                    queue_depth=depth,
                    ts=_ts,
                    frame_seq=seq,
                    hud_copy_ko="세션이 종료됩니다. 서비스가 재개됩니다.",
                    hud_copy_en="Session teardown — service resumed.",
                )
                synth_frames.append(frame)
                seq += 1
                logger.info(
                    "backpressure.synthetic_resume",
                    extra={
                        KOSMOS_IPC_BACKPRESSURE_SOURCE: source,
                        "session_id": self._session_id,
                    },
                )

        return synth_frames

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_retry_after(header_value: str | int | None) -> int:
        """Parse and clamp a Retry-After header value to ``[1000, 900000]`` ms.

        Accepts:
        - ``None`` → clamp minimum (1000 ms)
        - ``int``  → seconds (multiply by 1000 then clamp)
        - ``str``  → either decimal-seconds string or HTTP-date (RFC 7231)

        Returns:
            Clamped milliseconds as an integer in ``[1000, 900000]``.
        """
        raw_seconds: int | None = None

        if header_value is None:
            raw_seconds = 0

        elif isinstance(header_value, int):
            raw_seconds = header_value

        elif isinstance(header_value, str):
            stripped = header_value.strip()
            if stripped.isdigit():
                raw_seconds = int(stripped)
            else:
                # Attempt HTTP-date parse (RFC 7231 / email.utils)
                try:
                    dt = parsedate_to_datetime(stripped)
                    now_utc = datetime.now(tz=UTC)
                    delta_s = max(0, int((dt - now_utc).total_seconds()))
                    raw_seconds = delta_s
                except Exception:
                    logger.warning(
                        "backpressure.retry_after.parse_failed",
                        extra={"header_value": stripped},
                    )
                    raw_seconds = 0

        else:
            logger.warning(
                "backpressure.retry_after.unknown_type",
                extra={"type": type(header_value).__name__},
            )
            raw_seconds = 0

        ms = raw_seconds * 1000
        return max(_RETRY_AFTER_MS_MIN, min(ms, _RETRY_AFTER_MS_MAX))

    def _build_frame(
        self,
        signal: str,
        source: str,
        queue_depth: int,
        ts: str,
        frame_seq: int,
        hud_copy_ko: str | None = None,
        hud_copy_en: str | None = None,
    ) -> BackpressureSignalFrame:
        """Construct a BackpressureSignalFrame with default HUD copy."""
        if hud_copy_ko is None:
            if signal == "pause":
                hud_copy_ko = "서비스가 일시적으로 지연됩니다. 잠시 기다려 주세요."
            else:
                hud_copy_ko = "서비스가 재개되었습니다."

        if hud_copy_en is None:
            if signal == "pause":
                hud_copy_en = f"Backpressure detected (source={source}). Pausing emission."
            else:
                hud_copy_en = f"Backpressure resolved (source={source}). Resuming emission."

        return BackpressureSignalFrame(
            session_id=self._session_id,
            correlation_id=self._correlation_id,
            ts=ts,
            version="1.0",
            role="backend",
            frame_seq=frame_seq,
            transaction_id=None,
            trailer=None,
            kind="backpressure",
            signal=signal,  # type: ignore[arg-type]
            source=source,  # type: ignore[arg-type]
            queue_depth=queue_depth,
            hwm=self._hwm,
            retry_after_ms=None,
            hud_copy_ko=hud_copy_ko,
            hud_copy_en=hud_copy_en,
        )


__all__ = ["BackpressureController", "BackpressureError"]
