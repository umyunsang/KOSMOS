# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 data models for the KOSMOS safety pipeline.

Defines five entity groups used across all three safety layers:
  1. Redaction   — RedactionMatch, RedactionResult
  2. Injection   — InjectionSignalSet
  3. Moderation  — SafetyDecision
  4. Events      — RedactedEvent, InjectionBlockedEvent,
                   ModerationBlockedEvent, ModerationWarnedEvent
  5. Union       — SafetyEvent (discriminated on `kind`)

Reference: specs/026-safety-rails/spec.md § Data Model.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class RedactionMatch(BaseModel):
    """A single PII span detected and redacted from user input."""

    model_config = ConfigDict(frozen=True, strict=True)

    category: Literal["rrn", "phone_kr", "email", "passport_kr", "credit_card"]
    start: int
    end: int


class RedactionResult(BaseModel):
    """Outcome of running the PII redaction pass over one text input."""

    model_config = ConfigDict(frozen=True, strict=True)

    original_length: int
    redacted_length: int
    matches: tuple[RedactionMatch, ...]
    redacted_text: str


class InjectionSignalSet(BaseModel):
    """Numeric signals and decision produced by the injection-detection layer."""

    model_config = ConfigDict(frozen=True, strict=True)

    structural_score: float
    entropy_score: float
    length_deviation: float
    decision: Literal["allow", "block"]


class SafetyDecision(BaseModel):
    """Aggregated safety verdict returned by the moderation layer."""

    model_config = ConfigDict(frozen=True, strict=True)

    flagged: bool
    categories: tuple[str, ...]
    decision: Literal["allow", "block", "warn"]


# ---------------------------------------------------------------------------
# Discriminated-union event variants
# ---------------------------------------------------------------------------


class RedactedEvent(BaseModel):
    """Emitted when PII was detected and redacted from the input."""

    model_config = ConfigDict(frozen=True, strict=True)

    kind: Literal["redacted"] = "redacted"
    match_count: int


class InjectionBlockedEvent(BaseModel):
    """Emitted when the injection-detection layer blocks the request."""

    model_config = ConfigDict(frozen=True, strict=True)

    kind: Literal["injection_blocked"] = "injection_blocked"
    signal_summary: InjectionSignalSet


class ModerationBlockedEvent(BaseModel):
    """Emitted when the moderation layer issues a hard block."""

    model_config = ConfigDict(frozen=True, strict=True)

    kind: Literal["moderation_blocked"] = "moderation_blocked"
    categories: tuple[str, ...]


class ModerationWarnedEvent(BaseModel):
    """Emitted when the moderation layer issues a soft warning or is degraded."""

    model_config = ConfigDict(frozen=True, strict=True)

    kind: Literal["moderation_warned"] = "moderation_warned"
    detail: Literal["outage", "partial_error"]


# ---------------------------------------------------------------------------
# Top-level discriminated union
# ---------------------------------------------------------------------------

SafetyEvent = Annotated[
    RedactedEvent
    | InjectionBlockedEvent
    | ModerationBlockedEvent
    | ModerationWarnedEvent,
    Field(discriminator="kind"),
]
