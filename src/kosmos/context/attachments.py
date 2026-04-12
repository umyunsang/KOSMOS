# SPDX-License-Identifier: Apache-2.0
"""Per-turn attachment collector for KOSMOS Context Assembly layer (Layer 5).

``AttachmentCollector`` assembles the dynamic context block that the engine
prepends to each user turn.  It surfaces resolved tasks, in-flight tool state,
API health degradations, auth expiry warnings, and periodic reminder blocks.

All input comes from ``QueryState`` structured fields — never from
``state.messages`` (FR-010).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from kosmos.context.models import SystemPromptConfig
from kosmos.engine.models import QueryState

logger = logging.getLogger(__name__)

# Threshold (seconds) before auth expiry at which a warning is emitted.
_AUTH_EXPIRY_WARN_SECONDS = 60


class AttachmentCollector:
    """Collects and formats the per-turn dynamic context attachment.

    Args:
        config: System prompt configuration supplying reminder_cadence.
    """

    def __init__(self, config: SystemPromptConfig | None = None) -> None:
        self._config = config or SystemPromptConfig()

    def collect(
        self,
        state: QueryState,
        api_health: dict[str, str] | None = None,
    ) -> str | None:
        """Assemble all attachment sections into a single string.

        Sections are concatenated in a fixed order.  Returns ``None`` when
        all sections are empty (e.g. turn 0 with no resolved tasks, no
        in-flight calls, no health degradations, and no reminder due).

        Args:
            state: Current mutable session state.
            api_health: Optional mapping of tool_id → degradation status string.

        Returns:
            Non-empty attachment string, or ``None``.
        """
        sections: list[str] = []

        resolved = self._resolved_tasks_section(state)
        if resolved is not None:
            sections.append(resolved)

        inflight = self._inflight_section(state)
        if inflight is not None:
            sections.append(inflight)

        health = self._api_health_section(api_health)
        if health is not None:
            sections.append(health)

        auth = self._auth_expiry_section(state)
        if auth is not None:
            sections.append(auth)

        reminder = self._reminder_section(state)
        if reminder is not None:
            sections.append(reminder)

        if not sections:
            return None
        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _resolved_tasks_section(self, state: QueryState) -> str | None:
        """List completed tasks from the session."""
        if not state.resolved_tasks:
            return None
        lines = ["[Resolved tasks this session]"]
        for i, task in enumerate(state.resolved_tasks, 1):
            lines.append(f"  {i}. {task}")
        return "\n".join(lines)

    def _inflight_section(self, state: QueryState) -> str | None:
        """List pending in-flight tool call IDs.

        V1: QueryState does not yet carry in-flight tool call state.
        This section is reserved for Phase 2 when tool-call correlation lands.
        """
        # V1 stub — no in-flight field on QueryState yet.
        return None

    def _api_health_section(self, api_health: dict[str, str] | None) -> str | None:
        """Warn about degraded APIs from the injected health map."""
        if not api_health:
            return None
        degraded = {tid: status for tid, status in api_health.items() if status}
        if not degraded:
            return None
        lines = ["[API health warnings]"]
        for tool_id, status in degraded.items():
            lines.append(f"  - {tool_id}: {status}")
        return "\n".join(lines)

    def _auth_expiry_section(self, state: QueryState) -> str | None:
        """Warn when citizen auth token expires within the threshold.

        V1 note: ``QueryState`` does not carry ``auth_expiry_at`` yet.
        Full integration deferred to Phase 2.  Test fixture support is
        provided via the ``_auth_expiry_at`` backdoor attribute.
        """
        # V1 fixture injection — tests may set state._auth_expiry_at directly.
        expiry_at: datetime | None = getattr(state, "_auth_expiry_at", None)
        if expiry_at is None:
            return None
        now = datetime.now(tz=UTC)
        seconds_remaining = (expiry_at - now).total_seconds()
        if 0 < seconds_remaining < _AUTH_EXPIRY_WARN_SECONDS:
            return (
                f"[Auth warning] Citizen authentication expires in "
                f"{int(seconds_remaining)} seconds. "
                "Please prompt the citizen to re-authenticate before proceeding."
            )
        return None

    def _reminder_section(self, state: QueryState) -> str | None:
        """Inject a structured reminder block at cadence boundaries (FR-008).

        Fires when ``state.turn_count % reminder_cadence == 0``
        and ``state.turn_count > 0``.  Never fires on turn 0.
        """
        cadence = self._config.reminder_cadence
        if state.turn_count == 0:
            return None
        if state.turn_count % cadence != 0:
            return None

        lines = [f"[Reminder — turn {state.turn_count}]"]
        if state.resolved_tasks:
            lines.append("Previously resolved tasks:")
            for i, task in enumerate(state.resolved_tasks, 1):
                lines.append(f"  {i}. {task}")
        else:
            lines.append("No tasks resolved yet in this session.")
        return "\n".join(lines)
