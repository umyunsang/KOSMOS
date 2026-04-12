# SPDX-License-Identifier: Apache-2.0
"""Unit tests for UsageTracker in the KOSMOS LLM client module."""

from __future__ import annotations

import pytest

from kosmos.llm.errors import BudgetExceededError
from kosmos.llm.models import TokenUsage
from kosmos.llm.usage import UsageTracker


def _make_usage(input_tokens: int = 0, output_tokens: int = 0) -> TokenUsage:
    return TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)


class TestInitialState:
    def test_initial_state(self) -> None:
        """New tracker has remaining == budget, is_exhausted == False, call_count == 0."""
        tracker = UsageTracker(budget=1000)
        assert tracker.remaining == 1000
        assert tracker.is_exhausted is False
        assert tracker.call_count == 0


class TestCanAfford:
    def test_can_afford_within_budget(self) -> None:
        """can_afford returns True when the estimate fits within remaining budget."""
        tracker = UsageTracker(budget=1000)
        assert tracker.can_afford(100) is True

    def test_can_afford_exceeds_budget(self) -> None:
        """can_afford returns False when the estimate exceeds remaining budget."""
        tracker = UsageTracker(budget=100)
        assert tracker.can_afford(200) is False

    def test_can_afford_exact_budget(self) -> None:
        """can_afford returns True when the estimate equals remaining budget exactly."""
        tracker = UsageTracker(budget=100)
        assert tracker.can_afford(100) is True


class TestDebit:
    def test_debit_reduces_remaining(self) -> None:
        """After a debit, remaining decreases by the total tokens in the usage object."""
        tracker = UsageTracker(budget=1000)
        tracker.debit(_make_usage(input_tokens=50, output_tokens=30))
        assert tracker.remaining == 1000 - 80

    def test_debit_increments_call_count(self) -> None:
        """After 3 successive debits, call_count equals 3."""
        tracker = UsageTracker(budget=10_000)
        for _ in range(3):
            tracker.debit(_make_usage(input_tokens=10, output_tokens=10))
        assert tracker.call_count == 3

    def test_exhaustion(self) -> None:
        """Debiting exactly the budget amount leaves is_exhausted True."""
        tracker = UsageTracker(budget=100)
        # Debit exactly the full budget — should not raise
        tracker.debit(_make_usage(input_tokens=60, output_tokens=40))
        assert tracker.is_exhausted is True
        assert tracker.remaining == 0

    def test_remaining_never_negative(self) -> None:
        """remaining returns 0 (not negative) even after an over-debit."""
        tracker = UsageTracker(budget=100)
        with pytest.raises(BudgetExceededError):
            tracker.debit(_make_usage(input_tokens=80, output_tokens=80))
        # State was updated before the exception; remaining is clamped to 0
        assert tracker.remaining >= 0

    def test_total_used(self) -> None:
        """total_used equals the cumulative sum of all debited tokens."""
        tracker = UsageTracker(budget=10_000)
        tracker.debit(_make_usage(input_tokens=100, output_tokens=50))
        tracker.debit(_make_usage(input_tokens=200, output_tokens=75))
        assert tracker.total_used == 425


class TestBudgetExceeded:
    def test_debit_raises_on_exceed(self) -> None:
        """debit raises BudgetExceededError when the new total surpasses the budget."""
        tracker = UsageTracker(budget=100)
        with pytest.raises(BudgetExceededError):
            tracker.debit(_make_usage(input_tokens=60, output_tokens=60))


class TestInvalidBudget:
    def test_invalid_budget_zero(self) -> None:
        """Constructing a tracker with budget=0 raises ValueError."""
        with pytest.raises(ValueError):
            UsageTracker(budget=0)

    def test_invalid_budget_negative(self) -> None:
        """Constructing a tracker with budget=-1 raises ValueError."""
        with pytest.raises(ValueError):
            UsageTracker(budget=-1)
