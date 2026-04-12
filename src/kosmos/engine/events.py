# SPDX-License-Identifier: Apache-2.0
"""Query engine event types for the KOSMOS async tool loop (Layer 1).

This module defines:
- ``StopReason`` — an exhaustive enum of reasons the engine can stop processing.
- ``QueryEvent`` — a frozen, discriminated-union Pydantic model that the async
  generator yields on every meaningful state change during a query run.

Each ``QueryEvent`` carries a ``type`` discriminator field that determines which
additional fields are populated. A ``@model_validator`` enforces that required
fields for each event type are present at construction time, so callers can
safely destructure events without extra None-guards.
"""

from __future__ import annotations

from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from kosmos.llm.models import TokenUsage
from kosmos.tools.models import ToolResult


class StopReason(StrEnum):
    """Reasons for which the query engine may stop yielding events.

    Each value maps to a distinct engine exit path so that callers can take
    appropriate follow-up action (e.g. prompt the user, refresh auth, abort).
    """

    task_complete = "task_complete"
    """The engine determined the original task has been fully addressed."""

    end_turn = "end_turn"
    """The model signalled end-of-turn with no further tool calls pending."""

    needs_citizen_input = "needs_citizen_input"
    """The engine cannot proceed without additional input from the user."""

    needs_authentication = "needs_authentication"
    """A required API or service requires citizen authentication."""

    api_budget_exceeded = "api_budget_exceeded"
    """Cumulative API token or cost budget for this session was exhausted."""

    max_iterations_reached = "max_iterations_reached"
    """The engine hit the configured maximum tool-call iteration limit."""

    error_unrecoverable = "error_unrecoverable"
    """An unrecoverable error occurred; further processing is not possible."""

    cancelled = "cancelled"
    """The caller requested cancellation of the in-progress query."""


class QueryEvent(BaseModel):
    """A single event emitted by the KOSMOS query engine async generator.

    ``type`` is the discriminator.  Only fields relevant to the active ``type``
    are populated; all others remain ``None``.  The ``@model_validator`` enforces
    this contract at construction time and raises ``ValueError`` on violations.

    Event types and their required fields:

    * ``"text_delta"``    — ``content``
    * ``"tool_use"``      — ``tool_name``, ``tool_call_id``
    * ``"tool_result"``   — ``tool_result``
    * ``"usage_update"``  — ``usage``
    * ``"stop"``          — ``stop_reason``
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["text_delta", "tool_use", "tool_result", "usage_update", "stop"]
    """Discriminator field identifying which event variant this instance represents."""

    # --- text_delta ---
    content: str | None = None
    """Incremental text content from the model; set for ``type="text_delta"``."""

    # --- tool_use ---
    tool_name: str | None = None
    """Name of the tool being invoked; set for ``type="tool_use"``."""

    tool_call_id: str | None = None
    """Opaque ID for the tool call, correlates with tool_result."""

    arguments: str | None = None
    """JSON-serialized tool arguments; set for ``type="tool_use"`` when available."""

    # --- tool_result ---
    tool_result: ToolResult | None = None
    """Outcome of a completed tool execution; set for ``type="tool_result"``."""

    # --- usage_update ---
    usage: TokenUsage | None = None
    """Cumulative or delta token usage snapshot; set for ``type="usage_update"``."""

    # --- stop ---
    stop_reason: StopReason | None = None
    """Why the engine stopped; set for ``type="stop"``."""

    stop_message: str | None = None
    """Optional human-readable elaboration on the stop reason; set for ``type="stop"``."""

    # ------------------------------------------------------------------
    # Invariant enforcement
    # ------------------------------------------------------------------

    # Maps event type → tuple of field names that must not be None.
    _REQUIRED_FIELDS: ClassVar[dict[str, tuple[str, ...]]] = {
        "text_delta": ("content",),
        "tool_use": ("tool_name", "tool_call_id"),
        "tool_result": ("tool_result",),
        "usage_update": ("usage",),
        "stop": ("stop_reason",),
    }

    @model_validator(mode="after")
    def _enforce_type_fields(self) -> QueryEvent:
        """Validate that all required fields for the active ``type`` are present.

        Raises:
            ValueError: When a required field for the declared ``type`` is ``None``.
        """
        required = self._REQUIRED_FIELDS.get(self.type, ())
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"QueryEvent type={self.type!r} requires fields: {missing}")
        return self
