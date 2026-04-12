# SPDX-License-Identifier: Apache-2.0
"""Configuration model for the KOSMOS Query Engine.

QueryEngineConfig controls per-session engine behavior including iteration
and turn budgets, context window sizing, and context-compression thresholds.
It is a plain immutable Pydantic model — not loaded from env vars.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class QueryEngineConfig(BaseModel):
    """Immutable configuration for a single Query Engine session.

    All integer fields must be strictly positive.  The preprocessing threshold
    must fall in the range (0.0, 1.0] — zero is rejected because it would
    trigger compression on every message, which is never useful.
    """

    model_config = ConfigDict(frozen=True)

    max_iterations: int = 10
    """Per-turn iteration limit to prevent infinite tool-calling loops."""

    max_turns: int = 50
    """Session-level turn limit for budget enforcement."""

    context_window: int = 128_000
    """Model context window in tokens. Used for preprocessing threshold."""

    preprocessing_threshold: float = 0.8
    """Fraction of context_window that triggers aggressive compression."""

    tool_result_budget: int = 2000
    """Max tokens per individual tool result before truncation."""

    snip_turn_age: int = 5
    """Tool results older than this many turns are candidates for snipping."""

    microcompact_turn_age: int = 3
    """Messages older than this many turns get whitespace compression."""

    @field_validator(
        "max_iterations",
        "max_turns",
        "context_window",
        "tool_result_budget",
        "snip_turn_age",
        "microcompact_turn_age",
        mode="before",
    )
    @classmethod
    def int_fields_must_be_positive(cls, value: object) -> object:
        """Reject any integer field that is zero or negative."""
        if isinstance(value, int) and value <= 0:
            raise ValueError(f"value must be > 0, got {value}")
        return value

    @field_validator("preprocessing_threshold")
    @classmethod
    def threshold_must_be_in_range(cls, value: float) -> float:
        """Reject threshold <= 0.0 or > 1.0."""
        if value <= 0.0 or value > 1.0:
            raise ValueError(f"preprocessing_threshold must be in (0.0, 1.0], got {value}")
        return value
