# SPDX-License-Identifier: Apache-2.0
"""Token budget estimation for the KOSMOS Context Assembly layer.

BudgetEstimator computes token estimates for an AssembledContext and produces
a ContextBudget snapshot.  Token estimation uses the character-based heuristic
from ``kosmos.engine.tokens.estimate_tokens()``.
"""
from __future__ import annotations

import json
import logging

from kosmos.context.models import AssembledContext, ContextBudget
from kosmos.engine.tokens import estimate_tokens

logger = logging.getLogger(__name__)


class BudgetEstimator:
    """Estimates token usage for an assembled context.

    Stateless: each call to ``estimate()`` produces a fresh ContextBudget.
    """

    def estimate(
        self,
        context: AssembledContext,
        hard_limit: int,
        soft_limit: int,
    ) -> ContextBudget:
        """Compute token budget for the given assembled context.

        Sums token estimates for:
        - system_layer content
        - turn_attachment content (if present)
        - tool_definitions (serialized to JSON)

        Args:
            context: The assembled context (without budget field set).
            hard_limit: Hard token limit (e.g. 128_000).
            soft_limit: Soft warning threshold (e.g. 102_400 = 80% of hard).

        Returns:
            Frozen ContextBudget with all fields computed.
        """
        total = 0

        # System layer tokens
        total += estimate_tokens(context.system_layer.content)

        # Turn attachment tokens (optional)
        if context.turn_attachment is not None:
            total += estimate_tokens(context.turn_attachment.content)

        # Tool definitions tokens
        if context.tool_definitions:
            tool_json = json.dumps(context.tool_definitions)
            total += estimate_tokens(tool_json)

        budget = ContextBudget.from_estimate(
            estimated=total,
            hard_limit=hard_limit,
            soft_limit=soft_limit,
        )

        logger.debug(
            "Budget estimate: %d tokens (soft=%d, hard=%d, near=%s, over=%s)",
            budget.estimated_tokens,
            budget.soft_limit_tokens,
            budget.hard_limit_tokens,
            budget.is_near_limit,
            budget.is_over_limit,
        )

        return budget
