# SPDX-License-Identifier: Apache-2.0
"""Unit tests for context assembly Pydantic models (T005).

Covers:
- Frozen constraint enforcement
- Non-empty validators
- ContextBudget.from_estimate() threshold logic
- ContextLayer role/layer_name invariant
"""

from __future__ import annotations

import pytest

from kosmos.context.models import (
    AssembledContext,
    ContextBudget,
    ContextLayer,
    SystemPromptConfig,
)


# ---------------------------------------------------------------------------
# SystemPromptConfig
# ---------------------------------------------------------------------------


class TestSystemPromptConfig:
    def test_defaults(self) -> None:
        cfg = SystemPromptConfig()
        assert cfg.platform_name == "KOSMOS"
        assert cfg.language == "ko"
        assert cfg.reminder_cadence == 5
        assert cfg.personal_data_warning is True

    def test_frozen(self) -> None:
        cfg = SystemPromptConfig()
        with pytest.raises(Exception):  # noqa: B017
            cfg.platform_name = "OTHER"  # type: ignore[misc]

    def test_platform_name_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="platform_name"):
            SystemPromptConfig(platform_name="   ")

    def test_language_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="language"):
            SystemPromptConfig(language="")

    def test_reminder_cadence_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="reminder_cadence"):
            SystemPromptConfig(reminder_cadence=0)

    def test_reminder_cadence_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="reminder_cadence"):
            SystemPromptConfig(reminder_cadence=-1)


# ---------------------------------------------------------------------------
# ContextLayer
# ---------------------------------------------------------------------------


class TestContextLayer:
    def test_system_layer_valid(self) -> None:
        layer = ContextLayer(role="system", layer_name="system_prompt", content="Hello")
        assert layer.role == "system"
        assert layer.layer_name == "system_prompt"

    def test_user_layer_any_layer_name(self) -> None:
        layer = ContextLayer(role="user", layer_name="turn_attachment", content="context")
        assert layer.layer_name == "turn_attachment"

    def test_user_layer_custom_layer_name(self) -> None:
        layer = ContextLayer(role="user", layer_name="session_context", content="state")
        assert layer.layer_name == "session_context"

    def test_system_role_wrong_layer_name_raises(self) -> None:
        with pytest.raises(ValueError, match="layer_name='system_prompt'"):
            ContextLayer(role="system", layer_name="turn_attachment", content="bad")

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValueError, match="content"):
            ContextLayer(role="user", layer_name="turn_attachment", content="")

    def test_whitespace_content_raises(self) -> None:
        with pytest.raises(ValueError, match="content"):
            ContextLayer(role="user", layer_name="turn_attachment", content="   ")

    def test_empty_layer_name_raises(self) -> None:
        with pytest.raises(ValueError, match="layer_name"):
            ContextLayer(role="user", layer_name="", content="hello")

    def test_frozen(self) -> None:
        layer = ContextLayer(role="user", layer_name="turn_attachment", content="hi")
        with pytest.raises(Exception):  # noqa: B017
            layer.content = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContextBudget
# ---------------------------------------------------------------------------


class TestContextBudget:
    def test_within_limit(self) -> None:
        budget = ContextBudget.from_estimate(estimated=1000, hard_limit=10000, soft_limit=8000)
        assert budget.is_near_limit is False
        assert budget.is_over_limit is False

    def test_near_limit(self) -> None:
        budget = ContextBudget.from_estimate(estimated=8000, hard_limit=10000, soft_limit=8000)
        assert budget.is_near_limit is True
        assert budget.is_over_limit is False

    def test_over_limit(self) -> None:
        budget = ContextBudget.from_estimate(estimated=10000, hard_limit=10000, soft_limit=8000)
        assert budget.is_near_limit is True
        assert budget.is_over_limit is True

    def test_over_limit_exceeds_hard(self) -> None:
        budget = ContextBudget.from_estimate(estimated=15000, hard_limit=10000, soft_limit=8000)
        assert budget.is_over_limit is True

    def test_boundary_soft_minus_one(self) -> None:
        budget = ContextBudget.from_estimate(estimated=7999, hard_limit=10000, soft_limit=8000)
        assert budget.is_near_limit is False
        assert budget.is_over_limit is False

    def test_boundary_hard_minus_one(self) -> None:
        budget = ContextBudget.from_estimate(estimated=9999, hard_limit=10000, soft_limit=8000)
        assert budget.is_near_limit is True
        assert budget.is_over_limit is False

    def test_frozen(self) -> None:
        budget = ContextBudget.from_estimate(estimated=100, hard_limit=1000, soft_limit=800)
        with pytest.raises(Exception):  # noqa: B017
            budget.estimated_tokens = 999  # type: ignore[misc]

    def test_from_estimate_fields(self) -> None:
        budget = ContextBudget.from_estimate(estimated=500, hard_limit=2000, soft_limit=1600)
        assert budget.estimated_tokens == 500
        assert budget.hard_limit_tokens == 2000
        assert budget.soft_limit_tokens == 1600


# ---------------------------------------------------------------------------
# AssembledContext
# ---------------------------------------------------------------------------


class TestAssembledContext:
    def _system_layer(self) -> ContextLayer:
        return ContextLayer(role="system", layer_name="system_prompt", content="You are KOSMOS.")

    def test_minimal_construction(self) -> None:
        ctx = AssembledContext(system_layer=self._system_layer())
        assert ctx.turn_attachment is None
        assert ctx.tool_definitions == []
        assert ctx.budget is None

    def test_frozen(self) -> None:
        ctx = AssembledContext(system_layer=self._system_layer())
        with pytest.raises(Exception):  # noqa: B017
            ctx.turn_attachment = None  # type: ignore[misc]

    def test_with_budget(self) -> None:
        budget = ContextBudget.from_estimate(estimated=100, hard_limit=1000, soft_limit=800)
        ctx = AssembledContext(
            system_layer=self._system_layer(),
            budget=budget,
        )
        assert ctx.budget is not None
        assert ctx.budget.estimated_tokens == 100

    def test_with_turn_attachment(self) -> None:
        attachment = ContextLayer(
            role="user", layer_name="turn_attachment", content="Current state: ..."
        )
        ctx = AssembledContext(
            system_layer=self._system_layer(),
            turn_attachment=attachment,
        )
        assert ctx.turn_attachment is not None
        assert ctx.turn_attachment.layer_name == "turn_attachment"
