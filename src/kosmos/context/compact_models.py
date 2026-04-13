# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 models for the KOSMOS Context Compaction subsystem.

All models are frozen (immutable after construction) per Constitution § III.
No ``Any`` types are used.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class CompactionConfig(BaseModel):
    """Configuration for context compaction behaviour.

    Compaction is triggered when the estimated token count of the assembled
    conversation history exceeds ``compact_trigger_ratio * max_context_tokens``.
    Three escalation strategies are attempted in order:

    1. **micro** — per-turn surgical trimming of oversized tool results.
    2. **session_summary** — older turns are replaced with a rule-based summary.
    3. **aggressive** — oldest non-summary turns are dropped until below threshold.
    """

    model_config = ConfigDict(frozen=True)

    max_context_tokens: int = 80_000
    """Hard ceiling on conversation history token count."""

    compact_trigger_ratio: float = 0.85
    """Compaction fires when history reaches this fraction of max_context_tokens."""

    micro_compact_budget: int = 2_000
    """Maximum tokens a single tool-result block may occupy before truncation."""

    summary_max_tokens: int = 4_000
    """Maximum tokens the generated session summary may consume."""

    preserve_recent_turns: int = 4
    """Number of most-recent turns that must never be compacted or removed."""

    @field_validator("max_context_tokens")
    @classmethod
    def _max_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"max_context_tokens must be > 0, got {v}")
        return v

    @field_validator("compact_trigger_ratio")
    @classmethod
    def _ratio_in_range(cls, v: float) -> float:
        if not (0.0 < v < 1.0):
            raise ValueError(f"compact_trigger_ratio must be in (0, 1), got {v}")
        return v

    @field_validator("micro_compact_budget")
    @classmethod
    def _micro_budget_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"micro_compact_budget must be > 0, got {v}")
        return v

    @field_validator("summary_max_tokens")
    @classmethod
    def _summary_max_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"summary_max_tokens must be > 0, got {v}")
        return v

    @field_validator("preserve_recent_turns")
    @classmethod
    def _preserve_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"preserve_recent_turns must be >= 0, got {v}")
        return v

    @property
    def trigger_threshold(self) -> int:
        """Absolute token count that triggers compaction."""
        return int(self.max_context_tokens * self.compact_trigger_ratio)


class CompactionResult(BaseModel):
    """Immutable record of a completed compaction operation.

    Returned by all compaction engines so callers can log, audit, and surface
    budget warnings without coupling to the compaction implementation.
    """

    model_config = ConfigDict(frozen=True)

    original_tokens: int
    """Estimated token count of the input message list."""

    compacted_tokens: int
    """Estimated token count of the output message list."""

    tokens_saved: int
    """Difference between original and compacted token counts."""

    strategy_used: Literal["micro", "session_summary", "aggressive", "none"]
    """Which compaction strategy was applied."""

    turns_removed: int
    """Number of full conversation turns removed from history."""

    summary_generated: str | None = None
    """The summary text inserted as a system message, if any."""

    @field_validator("original_tokens", "compacted_tokens", "tokens_saved", "turns_removed")
    @classmethod
    def _nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"Token/turn counts must be >= 0, got {v}")
        return v
