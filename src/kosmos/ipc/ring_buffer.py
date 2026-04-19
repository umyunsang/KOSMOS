# SPDX-License-Identifier: Apache-2.0
"""SessionRingBuffer — in-memory 256-frame FIFO per session (Spec 032 T013).

Implements the at-least-once replay substrate for the reconnect handshake
(FR-019..020).  Uses stdlib ``collections.deque(maxlen=N)`` — no new deps.

Backpressure coupling (data-model.md §3.4):
- When ``len(frames) / maxlen >= 0.25`` (64-frame default threshold), the
  writer SHOULD emit a ``BackpressureSignalFrame(signal="pause")``.
- When depth drops below ``hwm // 2`` (32 default), writer SHOULD emit
  ``signal="resume"``.
"""

from __future__ import annotations

import logging
import os
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kosmos.ipc.frame_schema import IPCFrame

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via KOSMOS_IPC_* env vars)
# ---------------------------------------------------------------------------

_DEFAULT_RING_SIZE: int = int(os.environ.get("KOSMOS_IPC_RING_SIZE", "256"))
_DEFAULT_HWM: int = int(os.environ.get("KOSMOS_IPC_HWM", "64"))


# ---------------------------------------------------------------------------
# SessionRingBuffer
# ---------------------------------------------------------------------------


class SessionRingBuffer:
    """In-memory ring buffer holding the last *ring_size* outbound frames.

    Operations
    ----------
    append(frame) -> IPCFrame
        Stamp frame_seq from internal counter, push to deque (FIFO eviction
        beyond *ring_size*), update last_append_ts.

    replay_since(last_seen_frame_seq) -> list[IPCFrame]
        Return frames whose frame_seq > last_seen_frame_seq and that are
        NOT marked consumed.

    mark_consumed(frame_seq) -> None
        Record that the peer has acknowledged this frame_seq.

    ring_evicted(last_seen_frame_seq) -> bool
        True when last_seen_frame_seq is older than the oldest buffered frame.

    Backpressure helpers
    --------------------
    is_above_hwm() -> bool
        True when depth >= hwm.

    is_below_resume_threshold() -> bool
        True when depth < hwm // 2.
    """

    def __init__(
        self,
        session_id: str,
        ring_size: int | None = None,
        hwm: int | None = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id must be non-empty")

        self.session_id: str = session_id
        self._ring_size: int = ring_size if ring_size is not None else _DEFAULT_RING_SIZE
        self._hwm: int = hwm if hwm is not None else _DEFAULT_HWM

        self._frames: deque[IPCFrame] = deque(maxlen=self._ring_size)
        self._frame_seq_counter: int = 0
        self._consumed_markers: set[int] = set()
        self.last_append_ts: datetime = datetime.now(tz=UTC)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def frame_seq_counter(self) -> int:
        """Current monotonic frame_seq high-water mark."""
        return self._frame_seq_counter

    @property
    def hwm(self) -> int:
        """High-water mark threshold (immutable post-construction)."""
        return self._hwm

    @property
    def depth(self) -> int:
        """Number of frames currently in the buffer."""
        return len(self._frames)

    @property
    def ring_size(self) -> int:
        """Maximum capacity of the ring buffer."""
        return self._ring_size

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def append(self, frame: IPCFrame) -> IPCFrame:
        """Stamp *frame* with the next frame_seq and push to the ring.

        Because _BaseFrame is frozen (Pydantic ConfigDict frozen=True), we
        must create a copy with the new frame_seq via ``model_copy(update=...)``.

        Returns:
            The stamped frame (with frame_seq set).
        """
        stamped = frame.model_copy(update={"frame_seq": self._frame_seq_counter})
        self._frames.append(stamped)
        self._frame_seq_counter += 1
        self.last_append_ts = datetime.now(tz=UTC)
        logger.debug(
            "ring.append",
            extra={
                "session_id": self.session_id,
                "frame_seq": stamped.frame_seq,
                "kind": stamped.kind,
                "depth": self.depth,
            },
        )
        return stamped

    def replay_since(self, last_seen_frame_seq: int | None) -> list[IPCFrame]:
        """Return frames with frame_seq > *last_seen_frame_seq* not yet consumed.

        Args:
            last_seen_frame_seq: The last frame_seq the peer acknowledged, or
                None to replay everything in the buffer.

        Returns:
            Ordered list of IPCFrame instances to be replayed.
        """
        threshold = last_seen_frame_seq if last_seen_frame_seq is not None else -1
        result = [
            f
            for f in self._frames
            if f.frame_seq > threshold and f.frame_seq not in self._consumed_markers
        ]
        logger.debug(
            "ring.replay_since",
            extra={
                "session_id": self.session_id,
                "last_seen_frame_seq": last_seen_frame_seq,
                "replay_count": len(result),
            },
        )
        return result

    def mark_consumed(self, frame_seq: int) -> None:
        """Record that the peer has confirmed receipt of *frame_seq*.

        Mirrors the Spec 027 ``.consumed`` marker idiom (in-memory variant).
        """
        self._consumed_markers.add(frame_seq)

    def ring_evicted(self, last_seen_frame_seq: int | None) -> bool:
        """Return True when the requested seq is older than what the ring holds.

        If last_seen_frame_seq is None (fresh TUI), the ring is NOT evicted.
        """
        if last_seen_frame_seq is None:
            return False
        if not self._frames:
            # Buffer empty — if caller has any prior seq, it's been evicted.
            return last_seen_frame_seq >= 0
        oldest_seq: int = self._frames[0].frame_seq
        return last_seen_frame_seq < oldest_seq

    # ------------------------------------------------------------------
    # Backpressure helpers
    # ------------------------------------------------------------------

    def is_above_hwm(self) -> bool:
        """True when current depth >= high-water mark."""
        return self.depth >= self._hwm

    def is_below_resume_threshold(self) -> bool:
        """True when current depth < hwm // 2 (drain complete)."""
        return self.depth < (self._hwm // 2)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def oldest_seq(self) -> int | None:
        """Return the frame_seq of the oldest buffered frame, or None."""
        if self._frames:
            return self._frames[0].frame_seq
        return None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"SessionRingBuffer(session_id={self.session_id!r}, "
            f"depth={self.depth}/{self._ring_size}, "
            f"seq_counter={self._frame_seq_counter})"
        )


__all__ = ["SessionRingBuffer"]
