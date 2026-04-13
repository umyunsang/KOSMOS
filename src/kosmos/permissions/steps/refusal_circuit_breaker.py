# SPDX-License-Identifier: Apache-2.0
"""Refusal Circuit Breaker for the Permission Pipeline.

Tracks consecutive denials per (session_id, tool_id) pair.  When the
consecutive denial count reaches CONSECUTIVE_DENIAL_THRESHOLD, a WARNING is
logged and a suggested user action is emitted.  The counter resets to zero on
any successful allow.

This mirrors the denial-tracking pattern from the Claude Code permission
pipeline (``denialTracking.ts``, threshold 3) adapted for the KOSMOS context.

The circuit breaker is *advisory*: it does not change the pipeline decision.
The pipeline calls ``record_denial()`` / ``record_success()`` after each step
result and the circuit breaker logs escalation information when the threshold
is crossed.

Thread-safety: all mutation is protected by a single module-level lock so the
circuit breaker is safe to use from async contexts (called from sync code, the
lock is plain ``threading.Lock``).
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold
# ---------------------------------------------------------------------------

CONSECUTIVE_DENIAL_THRESHOLD: int = 3

# ---------------------------------------------------------------------------
# Per-(session, tool) state
# ---------------------------------------------------------------------------

# Structure: {(session_id, tool_id): consecutive_denial_count}
_denial_counts: dict[tuple[str, str], int] = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_denial(session_id: str, tool_id: str) -> int:
    """Increment the consecutive denial counter for *(session_id, tool_id)*.

    When the counter reaches ``CONSECUTIVE_DENIAL_THRESHOLD``, a WARNING is
    logged suggesting the user review the tool's access requirements.

    Args:
        session_id: Current session identifier.
        tool_id: Tool that was denied.

    Returns:
        The updated consecutive denial count after incrementing.
    """
    with _lock:
        key = (session_id, tool_id)
        count = _denial_counts.get(key, 0) + 1
        _denial_counts[key] = count

    if count >= CONSECUTIVE_DENIAL_THRESHOLD:
        logger.warning(
            "RefusalCircuitBreaker: tool %s has been denied %d consecutive times "
            "in session %s. Review the tool's access tier, terms of use, and "
            "authentication requirements before retrying.",
            tool_id,
            count,
            session_id,
        )

    return count


def record_success(session_id: str, tool_id: str) -> None:
    """Reset the consecutive denial counter for *(session_id, tool_id)*.

    Args:
        session_id: Current session identifier.
        tool_id: Tool that was allowed.
    """
    with _lock:
        _denial_counts.pop((session_id, tool_id), None)


def get_denial_count(session_id: str, tool_id: str) -> int:
    """Return the current consecutive denial count.

    Args:
        session_id: Current session identifier.
        tool_id: Tool identifier.

    Returns:
        Current consecutive denial count (0 if no denials recorded).
    """
    with _lock:
        return _denial_counts.get((session_id, tool_id), 0)


def reset_all() -> None:
    """Wipe all denial-count state.

    Intended for testing only.
    """
    with _lock:
        _denial_counts.clear()
