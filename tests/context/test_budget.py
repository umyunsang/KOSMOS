# SPDX-License-Identifier: Apache-2.0
"""Tests for BudgetEstimator (US4 / FR-006, FR-007).

Covers:
- Token counting from system layer only
- Token counting with turn attachment
- Token counting with tool definitions
- is_near_limit flag when estimated >= soft_limit
- is_over_limit flag when estimated >= hard_limit
- Both flags False for small contexts
- Empty tool_definitions list adds no tokens
"""

from __future__ import annotations

import json

from kosmos.context.budget import BudgetEstimator
from kosmos.context.models import AssembledContext, ContextLayer
from kosmos.engine.tokens import estimate_tokens

# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------


def _make_context(
    content: str = "Test system prompt content.",
    attachment: str | None = None,
    tool_defs: list | None = None,
) -> AssembledContext:
    """Construct a minimal AssembledContext for budget tests."""
    system = ContextLayer(role="system", layer_name="system_prompt", content=content)
    attach = None
    if attachment:
        attach = ContextLayer(role="user", layer_name="turn_attachment", content=attachment)
    return AssembledContext(
        system_layer=system,
        turn_attachment=attach,
        tool_definitions=tool_defs or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBudgetEstimator:
    """BudgetEstimator token counting and budget computation."""

    def test_system_only(self) -> None:
        """Context with system_layer only, no attachment, no tools."""
        ctx = _make_context(content="Hello world system prompt.")
        estimator = BudgetEstimator()
        budget = estimator.estimate(ctx, hard_limit=10_000, soft_limit=8_000)

        expected = estimate_tokens("Hello world system prompt.")
        assert budget.estimated_tokens == expected
        assert budget.hard_limit_tokens == 10_000
        assert budget.soft_limit_tokens == 8_000

    def test_with_attachment(self) -> None:
        """System + attachment: total > system alone."""
        system_content = "System prompt here."
        attach_content = "Attachment content for this turn."
        ctx = _make_context(content=system_content, attachment=attach_content)
        estimator = BudgetEstimator()
        budget = estimator.estimate(ctx, hard_limit=10_000, soft_limit=8_000)

        system_tokens = estimate_tokens(system_content)
        attach_tokens = estimate_tokens(attach_content)
        expected = system_tokens + attach_tokens
        assert budget.estimated_tokens == expected
        assert budget.estimated_tokens > system_tokens

    def test_with_tool_definitions(self) -> None:
        """System + tool defs: total includes tool JSON tokens."""
        system_content = "System prompt here."
        tool_defs = [{"type": "function", "function": {"name": "test_tool", "parameters": {}}}]
        ctx = _make_context(content=system_content, tool_defs=tool_defs)
        estimator = BudgetEstimator()
        budget = estimator.estimate(ctx, hard_limit=10_000, soft_limit=8_000)

        system_tokens = estimate_tokens(system_content)
        tool_tokens = estimate_tokens(json.dumps(tool_defs))
        expected = system_tokens + tool_tokens
        assert budget.estimated_tokens == expected
        assert budget.estimated_tokens > system_tokens

    def test_near_limit_flag(self) -> None:
        """is_near_limit=True when estimated >= soft_limit."""
        # Build a system prompt with enough content to exceed a tiny soft limit.
        long_content = "A" * 400  # 400 non-Korean chars → ceil(400/4) = 100 tokens
        ctx = _make_context(content=long_content)
        estimator = BudgetEstimator()
        estimated = estimate_tokens(long_content)
        # Set soft_limit just at the estimated value so the flag fires.
        budget = estimator.estimate(ctx, hard_limit=estimated + 1000, soft_limit=estimated)
        assert budget.is_near_limit is True
        assert budget.is_over_limit is False

    def test_over_limit_flag(self) -> None:
        """is_over_limit=True when estimated >= hard_limit."""
        long_content = "B" * 400  # 100 tokens
        ctx = _make_context(content=long_content)
        estimator = BudgetEstimator()
        estimated = estimate_tokens(long_content)
        # Set hard_limit at or below estimated value.
        budget = estimator.estimate(ctx, hard_limit=estimated, soft_limit=estimated - 1)
        assert budget.is_over_limit is True
        assert budget.is_near_limit is True  # over implies near

    def test_under_limit(self) -> None:
        """Small context: both is_near_limit and is_over_limit are False."""
        ctx = _make_context(content="Short prompt.")
        estimator = BudgetEstimator()
        budget = estimator.estimate(ctx, hard_limit=100_000, soft_limit=80_000)
        assert budget.is_near_limit is False
        assert budget.is_over_limit is False

    def test_empty_tool_definitions(self) -> None:
        """Empty tool_definitions list adds no additional tokens."""
        system_content = "System prompt content."
        ctx_no_tools = _make_context(content=system_content, tool_defs=[])
        ctx_none_tools = _make_context(content=system_content)
        estimator = BudgetEstimator()
        budget_no_tools = estimator.estimate(ctx_no_tools, hard_limit=10_000, soft_limit=8_000)
        budget_none_tools = estimator.estimate(ctx_none_tools, hard_limit=10_000, soft_limit=8_000)
        assert budget_no_tools.estimated_tokens == budget_none_tools.estimated_tokens
        assert budget_no_tools.estimated_tokens == estimate_tokens(system_content)
