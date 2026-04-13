# SPDX-License-Identifier: Apache-2.0
"""Structured observability event model for KOSMOS.

``ObservabilityEvent`` instances are emitted by the tool executor and
recovery pipeline at every significant moment (cache hits, retries, circuit
trips, errors).  They are designed to be:

- Logged via ``logging.getLogger(__name__).info(event.model_dump_json())``.
- Forwarded to an external system (future: OpenTelemetry, Datadog, etc.).
- Stored in a ring buffer for in-process diagnostics.

All fields are optional except ``timestamp`` and ``event_type`` so that
callers can construct minimal events without boilerplate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Allowed event type literals
# ---------------------------------------------------------------------------

EventType = Literal[
    "tool_call",
    "retry",
    "circuit_break",
    "cache_hit",
    "cache_miss",
    "error",
    "auth_refresh",
    "permission_decision",
    "llm_call",
]
"""Allowed values for ``ObservabilityEvent.event_type``.

Legacy types (``tool_call``, ``retry``, ``circuit_break``, ``cache_hit``,
``cache_miss``, ``error``, ``auth_refresh``) are retained for backwards
compatibility.  New types added in Phase A observability:

* ``permission_decision`` — emitted by ``PermissionPipeline`` after each
  step decision (allow/deny/degrade).
* ``llm_call`` — emitted by ``LLMClient`` after each chat completion (both
  ``complete()`` and ``stream()``).
"""


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class ObservabilityEvent(BaseModel):
    """Structured observability event for logging and telemetry.

    Designed to be JSON-serialisable without additional configuration.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
    )
    """UTC timestamp of the event.  Defaults to the current time."""

    event_type: EventType
    """Semantic type of the event."""

    tool_id: str | None = None
    """Identifier of the tool involved, if applicable."""

    duration_ms: float | None = None
    """Duration of the operation in milliseconds, if measured."""

    success: bool = True
    """Whether the operation represented by this event succeeded."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Arbitrary key/value pairs for additional context.

    Common keys:
    - ``attempt``: retry attempt number (int)
    - ``error_class``: ``ErrorClass`` string value
    - ``cache_key``: cache key hash (str)
    - ``circuit_state``: ``CircuitState`` string value
    """
