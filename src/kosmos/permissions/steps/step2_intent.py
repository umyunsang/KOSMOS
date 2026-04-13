# SPDX-License-Identifier: Apache-2.0
"""Step 2: Rule-based intent analysis.

Analyses the PermissionCheckRequest to detect suspicious usage patterns that
indicate the tool call intent may not match its declared purpose.  This is
deliberately rule-based (NOT LLM-based) to keep latency low and behaviour
predictable.

Checks performed:
- Rapid tool-call rate: more than RAPID_CALL_THRESHOLD calls to the same tool
  within the last RAPID_CALL_WINDOW_SECONDS are flagged as a suspicious burst.
- Unusual argument size: argument payloads larger than MAX_ARGS_BYTES are
  flagged because legitimate public-API calls rarely need huge payloads.
- Bypass escalation mismatch: a tool tagged is_personal_data that arrives via
  an unexpected elevated access tier is flagged.

All suspicious patterns return PermissionDecision.deny with a machine-readable
reason.  Unknown / unexpected exceptions cause a fail-closed deny.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque

from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

_STEP = 2

# ---------------------------------------------------------------------------
# Tunable thresholds
# ---------------------------------------------------------------------------

# Maximum number of calls to the same tool in a sliding window before the
# rate is considered a suspicious burst.
RAPID_CALL_THRESHOLD: int = 10

# Width of the sliding window in seconds.
RAPID_CALL_WINDOW_SECONDS: float = 5.0

# Maximum argument payload size (bytes, UTF-8 encoded).  Public government API
# calls are typically small; an unusually large payload warrants inspection.
MAX_ARGS_BYTES: int = 16_384  # 16 KiB

# ---------------------------------------------------------------------------
# Per-session rapid-call tracking (module-level, thread-safe)
# ---------------------------------------------------------------------------
# Structure: {(session_id, tool_id): deque of call timestamps}
_call_timestamps: dict[tuple[str, str], deque[float]] = {}
_timestamps_lock = threading.Lock()


def _record_and_check_rapid_calls(session_id: str, tool_id: str) -> bool:
    """Record a call and return True if the rate exceeds the threshold.

    Uses a fixed-size deque to keep only the last RAPID_CALL_THRESHOLD
    timestamps.  If the oldest entry in the full deque falls within the
    window, the burst limit is exceeded.
    """
    now = time.monotonic()
    key = (session_id, tool_id)

    with _timestamps_lock:
        if key not in _call_timestamps:
            _call_timestamps[key] = deque(maxlen=RAPID_CALL_THRESHOLD)

        timestamps = _call_timestamps[key]
        timestamps.append(now)

        if len(timestamps) == RAPID_CALL_THRESHOLD:
            oldest = timestamps[0]
            if (now - oldest) <= RAPID_CALL_WINDOW_SECONDS:
                return True  # burst detected

    return False


def reset_call_tracking(session_id: str | None = None, tool_id: str | None = None) -> None:
    """Reset rapid-call tracking state.

    Intended for testing only.  Clears tracking for the given (session_id,
    tool_id) pair, or wipes the entire table if both arguments are None.
    """
    with _timestamps_lock:
        if session_id is None and tool_id is None:
            _call_timestamps.clear()
        elif session_id is not None and tool_id is not None:
            _call_timestamps.pop((session_id, tool_id), None)


# ---------------------------------------------------------------------------
# Main step function
# ---------------------------------------------------------------------------


def check_intent(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 2: Analyse request intent for suspicious patterns.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult allow if intent looks legitimate, deny otherwise.
    """
    try:
        session_id = request.session_context.session_id
        tool_id = request.tool_id

        # --- Check 1: Rapid call rate ---
        if _record_and_check_rapid_calls(session_id, tool_id):
            logger.warning(
                "Step %d: rapid-call burst detected for tool %s in session %s "
                "(>=%d calls in %.1fs)",
                _STEP,
                tool_id,
                session_id,
                RAPID_CALL_THRESHOLD,
                RAPID_CALL_WINDOW_SECONDS,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="rapid_call_burst",
            )

        # --- Check 2: Unusually large argument payload ---
        args_size = len(request.arguments_json.encode("utf-8"))
        if args_size > MAX_ARGS_BYTES:
            logger.warning(
                "Step %d: argument payload too large for tool %s (%d bytes > %d limit)",
                _STEP,
                tool_id,
                args_size,
                MAX_ARGS_BYTES,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="argument_payload_too_large",
            )

        # --- Check 3: Personal-data tool accessed with suspiciously low tier ---
        # A tool marked is_personal_data should be at least api_key tier.
        # If somehow it arrives as public, deny — misconfiguration or tampering.
        if request.is_personal_data and request.access_tier == AccessTier.public:
            logger.warning(
                "Step %d: personal_data tool %s has public access_tier — misconfiguration",
                _STEP,
                tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="personal_data_public_tier_mismatch",
            )

        # --- Check 4: arguments_json must be a JSON object (not a bare scalar) ---
        try:
            parsed = json.loads(request.arguments_json)
        except json.JSONDecodeError:
            logger.warning(
                "Step %d: arguments_json is not valid JSON for tool %s",
                _STEP,
                tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="invalid_arguments_json",
            )

        if not isinstance(parsed, dict):
            logger.warning(
                "Step %d: arguments_json is not a JSON object for tool %s (got %s)",
                _STEP,
                tool_id,
                type(parsed).__name__,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="arguments_not_object",
            )

        logger.debug("Step %d: intent check passed for tool %s", _STEP, tool_id)
        return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

    except Exception as exc:
        logger.exception(
            "Step %d: unexpected exception during intent check for tool %s: %s",
            _STEP,
            request.tool_id,
            exc,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="internal_error",
        )
