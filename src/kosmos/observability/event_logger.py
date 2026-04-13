# SPDX-License-Identifier: Apache-2.0
"""Structured event logger for KOSMOS observability.

``ObservabilityEventLogger`` is the single emit point for all structured
observability events in KOSMOS.  It:

1. Enforces a PII key whitelist — only the labels ``tool_id``, ``step``,
   ``decision``, ``error_class``, and ``model`` are allowed in
   ``ObservabilityEvent.metadata``.  Non-whitelisted keys are stripped
   *before* emission and a WARNING is logged.

2. Maps ``(event_type, success)`` pairs to appropriate Python log levels:
   - Success path events → ``logging.INFO``
   - Failure/error path events → ``logging.WARNING``

3. Is fail-safe: any exception raised during emission is caught and logged
   as a WARNING.  It never propagates to callers (AC-A9).

4. Serialises events as JSON via ``ObservabilityEvent.model_dump_json()``.

Usage::

    from kosmos.observability import ObservabilityEventLogger, ObservabilityEvent

    logger = ObservabilityEventLogger()
    logger.emit(ObservabilityEvent(event_type="llm_call", success=True))

The underlying Python logger name is ``kosmos.events``.  Consumers can
attach handlers to that logger (e.g. for file export, ring-buffer capture,
or test assertion).
"""

from __future__ import annotations

import logging

from kosmos.observability.events import EventType, ObservabilityEvent

_events_logger = logging.getLogger("kosmos.events")

# ---------------------------------------------------------------------------
# PII whitelist
# ---------------------------------------------------------------------------

_ALLOWED_METADATA_KEYS: frozenset[str] = frozenset(
    {"tool_id", "step", "decision", "error_class", "model"}
)
"""Only these metadata keys may be logged.  All others are stripped to prevent
accidental PII leakage (AC-A10)."""

# ---------------------------------------------------------------------------
# Log-level map
# ---------------------------------------------------------------------------

#: Default level for event types where success=True.
_DEFAULT_SUCCESS_LEVEL: int = logging.INFO

#: Default level for event types where success=False.
_DEFAULT_FAILURE_LEVEL: int = logging.WARNING

#: Per-(event_type, success) overrides.  Covers all known event types; falls
#: back to the defaults above for any future additions.
_LEVEL_MAP: dict[tuple[str, bool], int] = {
    # LLM calls
    ("llm_call", True): logging.INFO,
    ("llm_call", False): logging.WARNING,
    # Permission decisions
    ("permission_decision", True): logging.INFO,
    ("permission_decision", False): logging.WARNING,
    # Tool calls
    ("tool_call", True): logging.INFO,
    ("tool_call", False): logging.WARNING,
    # Retry attempts — always informational
    ("retry", True): logging.INFO,
    ("retry", False): logging.INFO,
    # Circuit break — notable even on success probe
    ("circuit_break", True): logging.INFO,
    ("circuit_break", False): logging.WARNING,
    # Cache operations
    ("cache_hit", True): logging.DEBUG,
    ("cache_hit", False): logging.DEBUG,
    ("cache_miss", True): logging.DEBUG,
    ("cache_miss", False): logging.DEBUG,
    # Errors
    ("error", True): logging.WARNING,
    ("error", False): logging.WARNING,
    # Auth refresh
    ("auth_refresh", True): logging.INFO,
    ("auth_refresh", False): logging.WARNING,
}


def _log_level_for(event_type: EventType, success: bool) -> int:
    """Return the appropriate log level for *event_type* + *success* pair."""
    return _LEVEL_MAP.get(
        (event_type, success),
        _DEFAULT_SUCCESS_LEVEL if success else _DEFAULT_FAILURE_LEVEL,
    )


# ---------------------------------------------------------------------------
# ObservabilityEventLogger
# ---------------------------------------------------------------------------


class ObservabilityEventLogger:
    """Fail-safe structured event emitter for KOSMOS observability.

    Args:
        logger: Optional custom Python logger.  Defaults to ``kosmos.events``
            which allows fine-grained log filtering without affecting other
            KOSMOS loggers.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger if logger is not None else _events_logger

    def emit(self, event: ObservabilityEvent) -> None:
        """Emit *event* as structured JSON to the backing logger.

        Behaviour:
        - Non-whitelisted keys in ``event.metadata`` are stripped and a
          WARNING is emitted for each stripped key (AC-A10).
        - The (possibly filtered) event is serialised to JSON and logged at
          the level determined by ``(event_type, success)``.
        - Any exception from serialisation or logging is caught and logged as
          a WARNING.  Never propagates to the caller (AC-A9).

        Args:
            event: The observability event to emit.
        """
        try:
            # --- PII whitelist enforcement ---
            disallowed = {k for k in event.metadata if k not in _ALLOWED_METADATA_KEYS}
            if disallowed:
                self._log.warning(
                    "ObservabilityEventLogger: dropping non-whitelisted metadata keys %s "
                    "for event_type=%s (AC-A10)",
                    sorted(disallowed),
                    event.event_type,
                )
                # Build a clean copy with only allowed keys.
                clean_metadata = {k: v for k, v in event.metadata.items() if k not in disallowed}
                event = event.model_copy(update={"metadata": clean_metadata})

            level = _log_level_for(event.event_type, event.success)
            self._log.log(level, event.model_dump_json())
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).warning(
                "ObservabilityEventLogger.emit failed silently", exc_info=True
            )
