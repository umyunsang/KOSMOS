# SPDX-License-Identifier: Apache-2.0
"""Tests for CompactionConfig and CompactionResult (compact_models.py).

Covers:
- CompactionConfig defaults and validation
- CompactionConfig.trigger_threshold property
- CompactionResult construction and field validation
- Frozen (immutable) behaviour on both models
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.context.compact_models import CompactionConfig, CompactionResult


class TestCompactionConfigDefaults:
    """CompactionConfig default values are sensible and valid."""

    def test_default_max_context_tokens(self) -> None:
        cfg = CompactionConfig()
        assert cfg.max_context_tokens == 80_000

    def test_default_compact_trigger_ratio(self) -> None:
        cfg = CompactionConfig()
        assert cfg.compact_trigger_ratio == 0.85

    def test_default_micro_compact_budget(self) -> None:
        cfg = CompactionConfig()
        assert cfg.micro_compact_budget == 2_000

    def test_default_summary_max_tokens(self) -> None:
        cfg = CompactionConfig()
        assert cfg.summary_max_tokens == 4_000

    def test_default_preserve_recent_turns(self) -> None:
        cfg = CompactionConfig()
        assert cfg.preserve_recent_turns == 4


class TestCompactionConfigTriggerThreshold:
    """trigger_threshold property computes correctly."""

    def test_trigger_threshold_default(self) -> None:
        cfg = CompactionConfig()
        assert cfg.trigger_threshold == int(80_000 * 0.85)

    def test_trigger_threshold_custom(self) -> None:
        cfg = CompactionConfig(max_context_tokens=100_000, compact_trigger_ratio=0.9)
        assert cfg.trigger_threshold == 90_000


class TestCompactionConfigValidation:
    """CompactionConfig rejects invalid inputs."""

    def test_max_context_tokens_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="max_context_tokens"):
            CompactionConfig(max_context_tokens=0)

    def test_max_context_tokens_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionConfig(max_context_tokens=-1)

    def test_ratio_must_be_between_zero_and_one_exclusive(self) -> None:
        with pytest.raises(ValidationError, match="compact_trigger_ratio"):
            CompactionConfig(compact_trigger_ratio=0.0)

    def test_ratio_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionConfig(compact_trigger_ratio=1.0)

    def test_ratio_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionConfig(compact_trigger_ratio=1.5)

    def test_micro_compact_budget_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="micro_compact_budget"):
            CompactionConfig(micro_compact_budget=0)

    def test_summary_max_tokens_must_be_positive(self) -> None:
        with pytest.raises(ValidationError, match="summary_max_tokens"):
            CompactionConfig(summary_max_tokens=0)

    def test_preserve_recent_turns_zero_accepted(self) -> None:
        cfg = CompactionConfig(preserve_recent_turns=0)
        assert cfg.preserve_recent_turns == 0

    def test_preserve_recent_turns_negative_rejected(self) -> None:
        with pytest.raises(ValidationError, match="preserve_recent_turns"):
            CompactionConfig(preserve_recent_turns=-1)


class TestCompactionConfigFrozen:
    """CompactionConfig is immutable after construction."""

    def test_immutable_max_context_tokens(self) -> None:
        cfg = CompactionConfig()
        with pytest.raises(ValidationError):
            cfg.max_context_tokens = 999  # type: ignore[misc]


class TestCompactionResultConstruction:
    """CompactionResult builds correctly from valid inputs."""

    def test_basic_construction(self) -> None:
        r = CompactionResult(
            original_tokens=1000,
            compacted_tokens=600,
            tokens_saved=400,
            strategy_used="micro",
            turns_removed=0,
        )
        assert r.original_tokens == 1000
        assert r.compacted_tokens == 600
        assert r.tokens_saved == 400
        assert r.strategy_used == "micro"
        assert r.turns_removed == 0
        assert r.summary_generated is None

    def test_with_summary(self) -> None:
        r = CompactionResult(
            original_tokens=5000,
            compacted_tokens=1000,
            tokens_saved=4000,
            strategy_used="session_summary",
            turns_removed=10,
            summary_generated="Session summary text here.",
        )
        assert r.summary_generated == "Session summary text here."
        assert r.strategy_used == "session_summary"

    def test_all_strategies_accepted(self) -> None:
        for strategy in ("micro", "session_summary", "aggressive", "none"):
            r = CompactionResult(
                original_tokens=100,
                compacted_tokens=50,
                tokens_saved=50,
                strategy_used=strategy,  # type: ignore[arg-type]
                turns_removed=0,
            )
            assert r.strategy_used == strategy


class TestCompactionResultValidation:
    """CompactionResult rejects invalid values."""

    def test_negative_original_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Token/turn counts"):
            CompactionResult(
                original_tokens=-1,
                compacted_tokens=0,
                tokens_saved=0,
                strategy_used="micro",
                turns_removed=0,
            )

    def test_negative_compacted_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionResult(
                original_tokens=100,
                compacted_tokens=-5,
                tokens_saved=0,
                strategy_used="micro",
                turns_removed=0,
            )

    def test_negative_tokens_saved_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionResult(
                original_tokens=100,
                compacted_tokens=50,
                tokens_saved=-1,
                strategy_used="micro",
                turns_removed=0,
            )

    def test_negative_turns_removed_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionResult(
                original_tokens=100,
                compacted_tokens=50,
                tokens_saved=50,
                strategy_used="micro",
                turns_removed=-1,
            )

    def test_invalid_strategy_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompactionResult(
                original_tokens=100,
                compacted_tokens=50,
                tokens_saved=50,
                strategy_used="unknown",  # type: ignore[arg-type]
                turns_removed=0,
            )


class TestCompactionResultFrozen:
    """CompactionResult is immutable after construction."""

    def test_immutable(self) -> None:
        r = CompactionResult(
            original_tokens=100,
            compacted_tokens=50,
            tokens_saved=50,
            strategy_used="micro",
            turns_removed=0,
        )
        with pytest.raises(ValidationError):
            r.tokens_saved = 999  # type: ignore[misc]
