# SPDX-License-Identifier: Apache-2.0
"""Session-level token budget tracker for the KOSMOS LLM client."""

from __future__ import annotations

import logging

from kosmos.llm.errors import BudgetExceededError
from kosmos.llm.models import TokenUsage

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks cumulative token usage against a session budget."""

    def __init__(self, budget: int) -> None:
        """Initialize with a token budget.

        Args:
            budget: Maximum total tokens allowed for this session. Must be > 0.

        Raises:
            ValueError: If budget is not a positive integer.
        """
        if budget <= 0:
            raise ValueError(f"budget must be > 0, got {budget}")
        self._budget = budget
        self._input_tokens_used = 0
        self._output_tokens_used = 0
        self._call_count = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def can_afford(self, estimated_input_tokens: int) -> bool:
        """Pre-flight check: is there likely enough budget for this call?

        Conservative estimate — checks if remaining budget can accommodate
        the estimated input tokens (does not account for output tokens).

        Args:
            estimated_input_tokens: Expected number of input tokens for the
                upcoming LLM call.

        Returns:
            True if remaining budget is greater than or equal to the estimate.
        """
        return self.remaining >= estimated_input_tokens

    def debit(self, usage: TokenUsage) -> None:
        """Record usage from a completed call.

        Args:
            usage: Token usage from the LLM response.

        Raises:
            BudgetExceededError: If the debit causes total consumption to
                exceed the configured budget.
        """
        new_input = self._input_tokens_used + usage.input_tokens
        new_output = self._output_tokens_used + usage.output_tokens
        new_total = new_input + new_output

        self._input_tokens_used = new_input
        self._output_tokens_used = new_output
        self._call_count += 1

        logger.debug(
            "Token debit: input=%d output=%d | session total=%d / budget=%d",
            usage.input_tokens,
            usage.output_tokens,
            new_total,
            self._budget,
        )

        if new_total > self._budget:
            raise BudgetExceededError(
                f"Session token budget exceeded: used {new_total}, budget {self._budget}"
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def remaining(self) -> int:
        """Remaining token budget."""
        return max(0, self._budget - self._input_tokens_used - self._output_tokens_used)

    @property
    def is_exhausted(self) -> bool:
        """Whether the budget is fully consumed."""
        return self.remaining == 0

    @property
    def call_count(self) -> int:
        """Number of LLM calls made in this session."""
        return self._call_count

    @property
    def total_used(self) -> int:
        """Total tokens consumed so far."""
        return self._input_tokens_used + self._output_tokens_used
