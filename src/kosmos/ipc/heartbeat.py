# SPDX-License-Identifier: Apache-2.0
"""HeartbeatState — per-channel dead-peer detector (Spec 032 T015).

Detects dead peers via the 30s/45s/120s interval/dead/grace-window model
described in data-model.md §5.  Configuration via pydantic-settings from
KOSMOS_IPC_* env vars — no new runtime deps (SC-008).

Lifecycle (FR-039):
- Send heartbeat ping every ``ping_interval_ms`` milliseconds.
- Declare peer dead when ``dead_threshold_ms`` elapses without a ping or pong.
- Keep ring buffer for ``resume_grace_ms`` after dead declaration so TUI can
  reconnect and resume.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings (KOSMOS_IPC_* env vars)
# ---------------------------------------------------------------------------


class HeartbeatSettings(BaseSettings):
    """Heartbeat knobs loaded from KOSMOS_IPC_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="KOSMOS_IPC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    heartbeat_interval_ms: int = 30_000
    """Ping cadence in milliseconds (default 30 s)."""

    heartbeat_dead_ms: int = 45_000
    """Declare peer dead after this idle period (default 45 s)."""

    heartbeat_grace_ms: int = 120_000
    """Keep ring buffer this long after dead declaration for TUI reconnect (120 s)."""


# ---------------------------------------------------------------------------
# DeadlineState enum
# ---------------------------------------------------------------------------


class DeadlineState(StrEnum):
    """Return value from HeartbeatState.tick()."""

    HEALTHY = "healthy"
    DEAD = "dead"
    GRACE = "grace"  # Dead declared, grace window still open for resume


# ---------------------------------------------------------------------------
# HeartbeatState
# ---------------------------------------------------------------------------


class HeartbeatState:
    """In-memory per-channel heartbeat tracker.

    Attributes
    ----------
    session_id : str
        Session identifier.
    last_peer_ping_ts : datetime | None
        Last time we received a heartbeat(direction='ping') from the peer.
    last_peer_pong_ts : datetime | None
        Last time the peer answered our ping.
    dead_declared : bool
        Latched True once the dead threshold is exceeded.
    dead_declared_ts : datetime | None
        When dead was declared (for grace-window calculation).
    """

    def __init__(
        self,
        session_id: str,
        settings: HeartbeatSettings | None = None,
    ) -> None:
        if not session_id:
            raise ValueError("session_id must be non-empty")

        self.session_id: str = session_id
        self._settings: HeartbeatSettings = settings or HeartbeatSettings()

        self.last_peer_ping_ts: datetime | None = None
        self.last_peer_pong_ts: datetime | None = None
        self._channel_open_ts: datetime = datetime.now(tz=UTC)

        self.dead_declared: bool = False
        self.dead_declared_ts: datetime | None = None

    # ------------------------------------------------------------------
    # Properties (expose settings for callers)
    # ------------------------------------------------------------------

    @property
    def ping_interval_ms(self) -> int:
        return self._settings.heartbeat_interval_ms

    @property
    def dead_threshold_ms(self) -> int:
        return self._settings.heartbeat_dead_ms

    @property
    def resume_grace_ms(self) -> int:
        return self._settings.heartbeat_grace_ms

    # ------------------------------------------------------------------
    # Record events
    # ------------------------------------------------------------------

    def record_ping(self, ts: datetime | None = None) -> None:
        """Record receipt of a heartbeat(direction='ping') from peer.

        Resets dead_declared if called during grace window (peer came back).
        """
        now = ts or datetime.now(tz=UTC)
        self.last_peer_ping_ts = now
        if self.dead_declared:
            # Peer reconnected within grace window
            logger.info(
                "heartbeat.peer_recovered",
                extra={"session_id": self.session_id},
            )
            self.dead_declared = False
            self.dead_declared_ts = None

    def record_pong(self, ts: datetime | None = None) -> None:
        """Record receipt of a heartbeat(direction='pong') from peer."""
        now = ts or datetime.now(tz=UTC)
        self.last_peer_pong_ts = now

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, now: datetime | None = None) -> DeadlineState:
        """Check peer liveness.

        Called periodically (typically every second by the heartbeat scheduler).
        Returns the current DeadlineState; if DEAD is returned for the first
        time, ``dead_declared`` is latched True.

        Args:
            now: Current wall-clock time (injectable for tests).

        Returns:
            DeadlineState.HEALTHY, DEAD, or GRACE.
        """
        current = now or datetime.now(tz=UTC)

        # If already dead, check if grace window has expired
        if self.dead_declared:
            assert self.dead_declared_ts is not None
            elapsed_grace_ms = (current - self.dead_declared_ts).total_seconds() * 1000
            if elapsed_grace_ms >= self._settings.heartbeat_grace_ms:
                logger.warning(
                    "heartbeat.grace_expired",
                    extra={
                        "session_id": self.session_id,
                        "elapsed_grace_ms": int(elapsed_grace_ms),
                    },
                )
                return DeadlineState.DEAD  # Grace expired — caller should GC ring buffer
            return DeadlineState.GRACE

        # Determine last activity time (most recent of ping/pong, or channel open)
        last_activity = self._channel_open_ts
        if self.last_peer_ping_ts and self.last_peer_ping_ts > last_activity:
            last_activity = self.last_peer_ping_ts
        if self.last_peer_pong_ts and self.last_peer_pong_ts > last_activity:
            last_activity = self.last_peer_pong_ts

        elapsed_ms = (current - last_activity).total_seconds() * 1000

        if elapsed_ms >= self._settings.heartbeat_dead_ms:
            if not self.dead_declared:
                self.dead_declared = True
                self.dead_declared_ts = current
                logger.warning(
                    "heartbeat.peer_dead",
                    extra={
                        "session_id": self.session_id,
                        "elapsed_ms": int(elapsed_ms),
                        "dead_threshold_ms": self._settings.heartbeat_dead_ms,
                    },
                )
            return DeadlineState.DEAD

        return DeadlineState.HEALTHY

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Resume ↔ heartbeat coupling (T024, contract § 5)
    # ------------------------------------------------------------------

    def notify_resume_success(self) -> None:
        """Signal that a resume handshake succeeded within the grace window.

        Resets ``dead_declared`` so the session re-enters the HEALTHY state
        and normal heartbeat pinging resumes.  Called by ``ResumeManager``
        after a successful ``ResumeResponseFrame`` is emitted.
        """
        if self.dead_declared:
            logger.info(
                "heartbeat.resume_cancelled_teardown",
                extra={"session_id": self.session_id},
            )
            self.dead_declared = False
            self.dead_declared_ts = None
        # Treat resume as an implicit liveness proof.
        self.last_peer_ping_ts = datetime.now(tz=UTC)

    def should_gc_ring(self, now: datetime | None = None) -> bool:
        """Return True when the grace window has expired and the ring may be GC'd.

        The ring buffer MUST NOT be garbage-collected while in GRACE state.
        Only when ``should_gc_ring()`` is True should the caller drop the
        ``SessionRingBuffer`` (contract § 5: grace-window expiry → GC ring).

        Args:
            now: Current wall-clock time (injectable for tests).

        Returns:
            True only when ``dead_declared=True`` AND the grace window has
            elapsed; False in all other cases.
        """
        if not self.dead_declared or self.dead_declared_ts is None:
            return False
        current = now or datetime.now(tz=UTC)
        elapsed_grace_ms = (current - self.dead_declared_ts).total_seconds() * 1000
        return elapsed_grace_ms >= self._settings.heartbeat_grace_ms

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"HeartbeatState(session_id={self.session_id!r}, "
            f"dead={self.dead_declared}, "
            f"interval={self.ping_interval_ms}ms)"
        )


__all__ = [
    "HeartbeatSettings",
    "HeartbeatState",
    "DeadlineState",
]
