# SPDX-License-Identifier: Apache-2.0
"""ResumeManager — reconnect handshake + blacklist (Spec 032 T021-T023, WS4).

Implements FR-018..025 (reconnect handshake) and the at-least-once replay
path described in contracts/resume-handshake.contract.md.

Responsibilities
----------------
- ``handle_resume_request()``: validates session existence, token authenticity,
  and ring-buffer availability; emits ``ResumeResponseFrame`` on success or
  ``ResumeRejectedFrame`` on failure.
- 5-value rejection enum: ``ring_evicted``, ``session_unknown``,
  ``token_mismatch``, ``protocol_incompatible``, ``session_expired``.
- 3-strike blacklist (FR-025): same ``session_id`` failing resume 3×
  consecutively is blacklisted; subsequent ``resume_request`` returns
  ``session_unknown`` immediately.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import NamedTuple

from kosmos.ipc.frame_schema import (
    FrameTrailer,
    ResumeRejectedFrame,
    ResumeRequestFrame,
    ResumeResponseFrame,
)
from kosmos.ipc.ring_buffer import SessionRingBuffer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rejection reason enum (normative per contract § 3)
# ---------------------------------------------------------------------------


class RejectionReason(StrEnum):
    """5-value rejection reason codes for ResumeRejectedFrame (FR-021/022/023)."""

    RING_EVICTED = "ring_evicted"
    """Requested last_seen_frame_seq is older than the oldest buffered frame."""

    SESSION_UNKNOWN = "session_unknown"
    """session_id not found — process restart or blacklisted session."""

    TOKEN_MISMATCH = "token_mismatch"  # noqa: S105
    """tui_session_token does not match the backend-recorded token."""

    PROTOCOL_INCOMPATIBLE = "protocol_incompatible"
    """TUI announced a version not supported by this backend."""

    SESSION_EXPIRED = "session_expired"
    """Session exceeded the idle TTL (governed by upstream session manager)."""


# Human-readable detail templates (Korean-first, English appended).
_REJECTION_DETAILS: dict[RejectionReason, str] = {
    RejectionReason.RING_EVICTED: (
        "세션이 너무 오래 끊겨 이력이 소실되었습니다. 새 세션을 시작해 주세요. "
        "(Session history evicted from ring buffer; please start a new session.)"
    ),
    RejectionReason.SESSION_UNKNOWN: (
        "세션을 찾을 수 없습니다. 새 세션을 시작해 주세요. "
        "(Session not found; please start a new session.)"
    ),
    RejectionReason.TOKEN_MISMATCH: (
        "세션 인증에 실패했습니다. 새 세션을 시작해 주세요. "
        "(Session token mismatch; please start a new session.)"
    ),
    RejectionReason.PROTOCOL_INCOMPATIBLE: (
        "프로토콜 버전이 맞지 않습니다. TUI를 최신 버전으로 업그레이드해 주세요. "
        "(Protocol version mismatch; please upgrade the TUI.)"
    ),
    RejectionReason.SESSION_EXPIRED: (
        "세션이 만료되었습니다. 새 세션을 시작해 주세요. "
        "(Session has expired; please start a new session.)"
    ),
}


# ---------------------------------------------------------------------------
# Internal session record
# ---------------------------------------------------------------------------


class _SessionRecord(NamedTuple):
    """Minimal record the ResumeManager holds per session."""

    session_id: str
    tui_session_token: str
    ring: SessionRingBuffer
    registered_at: datetime


# ---------------------------------------------------------------------------
# ResumeResult type
# ---------------------------------------------------------------------------


class ResumeResult(NamedTuple):
    """Return value from ``handle_resume_request``."""

    response: ResumeResponseFrame | ResumeRejectedFrame
    """The frame to emit to the TUI immediately."""

    replay_frames: Sequence[object]  # Sequence[IPCFrame] — typed loosely to avoid circular import
    """Ordered replay frames to emit after the response (empty on rejection)."""


# ---------------------------------------------------------------------------
# ResumeManager
# ---------------------------------------------------------------------------


class ResumeManager:
    """Handles the resume handshake lifecycle for one backend process.

    This is a process-scoped singleton (one per backend process).  The
    ``SessionRingBuffer`` lives inside this manager and is accessed by
    ``session_id``.

    Blacklist (FR-025)
    ------------------
    Three consecutive resume failures on the same ``session_id`` cause that
    session to be blacklisted.  A blacklisted session returns
    ``session_unknown`` immediately without touching the ring buffer.
    A successful resume RESETS the failure count for that session.

    Usage::

        mgr = ResumeManager()
        mgr.register_session("s-abc", token="tok", ring=ring)
        result = mgr.handle_resume_request(request_frame, correlation_id="...", ts="...")
        emit(result.response)
        for f in result.replay_frames:
            emit(f)
    """

    # Maximum consecutive failures before a session is blacklisted (FR-025).
    _BLACKLIST_THRESHOLD: int = 3

    def __init__(self) -> None:
        # session_id -> _SessionRecord
        self._sessions: dict[str, _SessionRecord] = {}
        # session_id -> consecutive failure count
        self._failure_counts: dict[str, int] = {}
        # Blacklisted session IDs (set)
        self._blacklist: set[str] = set()

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    def register_session(
        self,
        session_id: str,
        tui_session_token: str,
        ring: SessionRingBuffer,
    ) -> None:
        """Register a new session so the manager can service resume requests.

        Args:
            session_id: Unique session identifier (UUIDv7 recommended).
            tui_session_token: The opaque token the TUI will present for
                authenticity binding.
            ring: The ``SessionRingBuffer`` for this session.
        """
        if not session_id:
            raise ValueError("session_id must be non-empty")
        if not tui_session_token:
            raise ValueError("tui_session_token must be non-empty")

        self._sessions[session_id] = _SessionRecord(
            session_id=session_id,
            tui_session_token=tui_session_token,
            ring=ring,
            registered_at=datetime.now(tz=UTC),
        )
        # Clear any prior failure history when a session is freshly registered.
        self._failure_counts.pop(session_id, None)
        logger.debug(
            "resume_manager.session_registered",
            extra={"session_id": session_id},
        )

    def deregister_session(self, session_id: str) -> None:
        """Remove a session from the manager (e.g., on graceful teardown)."""
        self._sessions.pop(session_id, None)
        self._failure_counts.pop(session_id, None)
        self._blacklist.discard(session_id)

    # ------------------------------------------------------------------
    # Core handler
    # ------------------------------------------------------------------

    def handle_resume_request(
        self,
        request: ResumeRequestFrame,
        *,
        new_correlation_id: str,
        ts: str,
    ) -> ResumeResult:
        """Process a ``ResumeRequestFrame`` from the TUI.

        Validates the session, token, and ring-buffer window.  Returns a
        ``ResumeResult`` containing either a ``ResumeResponseFrame`` (success)
        or ``ResumeRejectedFrame`` (failure) plus the ordered replay list.

        Contract (resume-handshake.contract.md § 1):
        - On success: ``resumed_from_frame_seq == last_seen_frame_seq + 1``
          (or 0 if last_seen_frame_seq is None).
        - ``replay_count == len(replay_frames)``.
        - Replay frames keep their original ``frame_seq``.

        Args:
            request: The validated ``ResumeRequestFrame`` from the TUI.
            new_correlation_id: Fresh UUIDv7 to use for the response frame.
            ts: ISO-8601 UTC timestamp string for the response frame.

        Returns:
            A ``ResumeResult`` with the response frame and replay list.
        """
        session_id = request.session_id

        # --- Step 1: Check blacklist (FR-025) ---
        if session_id in self._blacklist:
            logger.warning(
                "resume_manager.blacklisted",
                extra={"session_id": session_id},
            )
            return self._make_rejected_result(
                request,
                reason=RejectionReason.SESSION_UNKNOWN,
                new_correlation_id=new_correlation_id,
                ts=ts,
            )

        # --- Step 2: Session existence check (FR-023) ---
        record = self._sessions.get(session_id)
        if record is None:
            logger.warning(
                "resume_manager.session_unknown",
                extra={"session_id": session_id},
            )
            self._record_failure(session_id)
            return self._make_rejected_result(
                request,
                reason=RejectionReason.SESSION_UNKNOWN,
                new_correlation_id=new_correlation_id,
                ts=ts,
            )

        # --- Step 3: Token authenticity check ---
        if request.tui_session_token != record.tui_session_token:
            logger.warning(
                "resume_manager.token_mismatch",
                extra={"session_id": session_id},
            )
            self._record_failure(session_id)
            return self._make_rejected_result(
                request,
                reason=RejectionReason.TOKEN_MISMATCH,
                new_correlation_id=new_correlation_id,
                ts=ts,
            )

        # --- Step 4: Ring-buffer eviction check (FR-021) ---
        ring = record.ring
        last_seq = request.last_seen_frame_seq

        if ring.ring_evicted(last_seq):
            logger.warning(
                "resume_manager.ring_evicted",
                extra={
                    "session_id": session_id,
                    "last_seen_frame_seq": last_seq,
                    "oldest_seq": ring.oldest_seq(),
                },
            )
            self._record_failure(session_id)
            return self._make_rejected_result(
                request,
                reason=RejectionReason.RING_EVICTED,
                new_correlation_id=new_correlation_id,
                ts=ts,
            )

        # --- Step 5: Success path ---
        replay_frames = ring.replay_since(last_seq)
        replay_count = len(replay_frames)

        # resumed_from_frame_seq is last_seen + 1 (or 0 for fresh TUI).
        resumed_from = (last_seq + 1) if last_seq is not None else 0

        from kosmos.ipc.heartbeat import HeartbeatSettings

        _settings = HeartbeatSettings()
        response = ResumeResponseFrame(
            session_id=session_id,
            correlation_id=new_correlation_id,
            ts=ts,
            role="backend",
            resumed_from_frame_seq=resumed_from,
            replay_count=replay_count,
            server_session_id=session_id,
            heartbeat_interval_ms=_settings.heartbeat_interval_ms,
            trailer=FrameTrailer(final=True),
        )

        # Reset failure count on success (FR-025: reset-on-success semantics).
        self._failure_counts.pop(session_id, None)

        logger.info(
            "resume_manager.resume_success",
            extra={
                "session_id": session_id,
                "replay_count": replay_count,
                "resumed_from_frame_seq": resumed_from,
            },
        )
        return ResumeResult(response=response, replay_frames=replay_frames)

    # ------------------------------------------------------------------
    # Blacklist helpers (FR-025)
    # ------------------------------------------------------------------

    def _record_failure(self, session_id: str) -> None:
        """Increment the failure counter; blacklist on threshold breach."""
        count = self._failure_counts.get(session_id, 0) + 1
        self._failure_counts[session_id] = count

        if count >= self._BLACKLIST_THRESHOLD:
            self._blacklist.add(session_id)
            logger.error(
                "resume_manager.session_blacklisted",
                extra={
                    "session_id": session_id,
                    "failure_count": count,
                    "threshold": self._BLACKLIST_THRESHOLD,
                },
            )

    def is_blacklisted(self, session_id: str) -> bool:
        """Return True if *session_id* is currently blacklisted."""
        return session_id in self._blacklist

    def reset_blacklist(self, session_id: str) -> None:
        """Remove a session from the blacklist (admin / test use only)."""
        self._blacklist.discard(session_id)
        self._failure_counts.pop(session_id, None)

    def failure_count(self, session_id: str) -> int:
        """Return the current consecutive failure count for *session_id*."""
        return self._failure_counts.get(session_id, 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_rejected_result(
        self,
        request: ResumeRequestFrame,
        *,
        reason: RejectionReason,
        new_correlation_id: str,
        ts: str,
    ) -> ResumeResult:
        """Build a ``ResumeRejectedFrame`` result."""
        frame = ResumeRejectedFrame(
            session_id=request.session_id,
            correlation_id=new_correlation_id,
            ts=ts,
            role="backend",
            reason=reason.value,
            detail=_REJECTION_DETAILS[reason],
            trailer=FrameTrailer(final=True),
        )
        return ResumeResult(response=frame, replay_frames=[])


__all__ = [
    "ResumeManager",
    "ResumeResult",
    "RejectionReason",
]
