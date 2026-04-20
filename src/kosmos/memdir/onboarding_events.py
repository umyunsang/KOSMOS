# SPDX-License-Identifier: Apache-2.0
"""Router for TUI onboarding stdio events → memdir USER-tier atomic writes.

Feature: Epic H #1302 (035-onboarding-brand-port).

The TUI emits JSONL envelopes on stderr for each consent / ministry-scope
record produced by the citizen-facing onboarding flow:

    {"event": "onboarding.write_consent_record", "payload": {...}, "ts": "..."}
    {"event": "onboarding.write_scope_record",   "payload": {...}, "ts": "..."}

This module is the Python-side consumer.  The Spec 032 stdio IPC bridge is
responsible for parsing each line, recognising the `event` field, and
dispatching to `handle_onboarding_event()`.  The bridge → handler wiring is
tracked under Spec 032 follow-up work; this module provides a stable,
tested entry point so the wiring is a one-line change there.

Security:
- Both writers (`write_consent_atomic` / `write_scope_atomic`) accept
  already-validated Pydantic models only.  Any envelope whose payload fails
  Pydantic validation is rejected at the handler boundary; no unvalidated
  dict ever touches disk.
- Unknown `event` values are rejected with `UnknownOnboardingEventError` so
  the bridge can log them without dispatching.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from kosmos.memdir.ministry_scope import (
    MinistryScopeAcknowledgment,
    write_scope_atomic,
)
from kosmos.memdir.user_consent import (
    PIPAConsentRecord,
    write_consent_atomic,
)

__all__ = [
    "DEFAULT_MEMDIR_ROOT",
    "OnboardingEventError",
    "OnboardingEventResult",
    "UnknownOnboardingEventError",
    "handle_onboarding_event",
]

logger = logging.getLogger(__name__)

DEFAULT_MEMDIR_ROOT = Path.home() / ".kosmos" / "memdir"


class OnboardingEventError(Exception):
    """Base class for handler rejections (invalid payload / write failure)."""


class UnknownOnboardingEventError(OnboardingEventError):
    """Raised for `event` values the handler does not route."""


OnboardingEventResult = dict[str, Any]


def _handle_consent(payload: dict[str, Any], memdir_root: Path) -> Path:
    try:
        record = PIPAConsentRecord.model_validate(payload)
    except ValidationError as exc:
        raise OnboardingEventError(
            f"invalid onboarding.write_consent_record payload: {exc.errors()}"
        ) from exc
    base = memdir_root / "user" / "consent"
    return write_consent_atomic(record, base)


def _handle_scope(payload: dict[str, Any], memdir_root: Path) -> Path:
    try:
        record = MinistryScopeAcknowledgment.model_validate(payload)
    except ValidationError as exc:
        raise OnboardingEventError(
            f"invalid onboarding.write_scope_record payload: {exc.errors()}"
        ) from exc
    base = memdir_root / "user" / "ministry-scope"
    return write_scope_atomic(record, base)


_HANDLERS: dict[
    Literal[
        "onboarding.write_consent_record",
        "onboarding.write_scope_record",
    ],
    Any,
] = {
    "onboarding.write_consent_record": _handle_consent,
    "onboarding.write_scope_record": _handle_scope,
}


def handle_onboarding_event(
    event: dict[str, Any],
    *,
    memdir_root: Path = DEFAULT_MEMDIR_ROOT,
) -> OnboardingEventResult:
    """Dispatch one TUI stdio envelope to the matching atomic writer.

    Args:
        event: JSONL envelope with keys `event` (str) and `payload` (dict).
        memdir_root: root of the memdir USER tier; defaults to the per-user
            `~/.kosmos/memdir/`.

    Returns:
        `{"event": str, "written_path": str}` on success.

    Raises:
        OnboardingEventError: payload failed Pydantic validation.
        UnknownOnboardingEventError: `event` not in the registered set.
        OSError: atomic write failed (bubbled up; caller logs).
    """
    event_name = event.get("event")
    payload = event.get("payload")
    if not isinstance(event_name, str) or not isinstance(payload, dict):
        raise OnboardingEventError(
            "onboarding event envelope missing str `event` + dict `payload`"
        )
    handler = _HANDLERS.get(event_name)  # type: ignore[arg-type]
    if handler is None:
        raise UnknownOnboardingEventError(
            f"unknown onboarding event: {event_name!r}"
        )
    written_path = handler(payload, memdir_root)
    logger.info(
        "onboarding event handled: %s -> %s", event_name, written_path
    )
    return {"event": event_name, "written_path": str(written_path)}
