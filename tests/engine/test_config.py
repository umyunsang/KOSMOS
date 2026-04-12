# SPDX-License-Identifier: Apache-2.0
"""Unit tests for kosmos.engine.config.QueryEngineConfig.

Covers:
- Default field values
- Custom valid construction
- Immutability (frozen model)
- Positive-integer validation for all six integer fields
- preprocessing_threshold range validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.engine.config import QueryEngineConfig

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaults:
    """Verify that the documented default values are correct."""

    def test_max_iterations_default(self) -> None:
        """max_iterations should default to 10."""
        assert QueryEngineConfig().max_iterations == 10

    def test_max_turns_default(self) -> None:
        """max_turns should default to 50."""
        assert QueryEngineConfig().max_turns == 50

    def test_context_window_default(self) -> None:
        """context_window should default to 128 000 tokens."""
        assert QueryEngineConfig().context_window == 128_000

    def test_preprocessing_threshold_default(self) -> None:
        """preprocessing_threshold should default to 0.8."""
        assert QueryEngineConfig().preprocessing_threshold == pytest.approx(0.8)

    def test_tool_result_budget_default(self) -> None:
        """tool_result_budget should default to 2 000."""
        assert QueryEngineConfig().tool_result_budget == 2000

    def test_snip_turn_age_default(self) -> None:
        """snip_turn_age should default to 5."""
        assert QueryEngineConfig().snip_turn_age == 5

    def test_microcompact_turn_age_default(self) -> None:
        """microcompact_turn_age should default to 3."""
        assert QueryEngineConfig().microcompact_turn_age == 3


# ---------------------------------------------------------------------------
# Custom valid construction
# ---------------------------------------------------------------------------


class TestCustomValues:
    """Verify that valid non-default values are accepted and stored correctly."""

    def test_custom_all_fields(self) -> None:
        """All fields accept custom valid values simultaneously."""
        cfg = QueryEngineConfig(
            max_iterations=5,
            max_turns=20,
            context_window=32_000,
            preprocessing_threshold=0.5,
            tool_result_budget=1000,
            snip_turn_age=3,
            microcompact_turn_age=2,
        )
        assert cfg.max_iterations == 5
        assert cfg.max_turns == 20
        assert cfg.context_window == 32_000
        assert cfg.preprocessing_threshold == pytest.approx(0.5)
        assert cfg.tool_result_budget == 1000
        assert cfg.snip_turn_age == 3
        assert cfg.microcompact_turn_age == 2

    def test_min_valid_integer_values(self) -> None:
        """Each integer field accepts 1 (the smallest positive integer)."""
        cfg = QueryEngineConfig(
            max_iterations=1,
            max_turns=1,
            context_window=1,
            tool_result_budget=1,
            snip_turn_age=1,
            microcompact_turn_age=1,
        )
        assert cfg.max_iterations == 1
        assert cfg.max_turns == 1
        assert cfg.context_window == 1
        assert cfg.tool_result_budget == 1
        assert cfg.snip_turn_age == 1
        assert cfg.microcompact_turn_age == 1

    def test_preprocessing_threshold_exactly_one(self) -> None:
        """preprocessing_threshold accepts the boundary value 1.0."""
        cfg = QueryEngineConfig(preprocessing_threshold=1.0)
        assert cfg.preprocessing_threshold == pytest.approx(1.0)

    def test_preprocessing_threshold_half(self) -> None:
        """preprocessing_threshold accepts an intermediate value like 0.5."""
        cfg = QueryEngineConfig(preprocessing_threshold=0.5)
        assert cfg.preprocessing_threshold == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Immutability (frozen model)
# ---------------------------------------------------------------------------


class TestFrozen:
    """QueryEngineConfig must be immutable after construction."""

    def test_assign_max_iterations_raises(self) -> None:
        """Assigning to max_iterations on a frozen instance raises ValidationError."""
        cfg = QueryEngineConfig()
        with pytest.raises(ValidationError):
            cfg.max_iterations = 99  # type: ignore[misc]

    def test_assign_preprocessing_threshold_raises(self) -> None:
        """Assigning to preprocessing_threshold on a frozen instance raises ValidationError."""
        cfg = QueryEngineConfig()
        with pytest.raises(ValidationError):
            cfg.preprocessing_threshold = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integer-field positive validation
# ---------------------------------------------------------------------------

_INT_FIELDS = [
    "max_iterations",
    "max_turns",
    "context_window",
    "tool_result_budget",
    "snip_turn_age",
    "microcompact_turn_age",
]


@pytest.mark.parametrize("field_name", _INT_FIELDS)
def test_int_field_rejects_zero(field_name: str) -> None:
    """Every integer field must raise ValidationError when set to 0."""
    with pytest.raises(ValidationError):
        QueryEngineConfig(**{field_name: 0})


@pytest.mark.parametrize("field_name", _INT_FIELDS)
def test_int_field_rejects_negative(field_name: str) -> None:
    """Every integer field must raise ValidationError when set to -1."""
    with pytest.raises(ValidationError):
        QueryEngineConfig(**{field_name: -1})


@pytest.mark.parametrize("field_name", _INT_FIELDS)
def test_int_field_rejects_large_negative(field_name: str) -> None:
    """Every integer field must raise ValidationError for highly negative values."""
    with pytest.raises(ValidationError):
        QueryEngineConfig(**{field_name: -1000})


@pytest.mark.parametrize("field_name", _INT_FIELDS)
def test_int_field_accepts_one(field_name: str) -> None:
    """Every integer field must accept 1 (minimum positive value)."""
    cfg = QueryEngineConfig(**{field_name: 1})
    assert getattr(cfg, field_name) == 1


# ---------------------------------------------------------------------------
# preprocessing_threshold range validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        0.0,  # boundary — exactly zero is rejected
        -0.1,  # slightly negative
        -1.0,  # clearly negative
        1.1,  # just above 1.0
        2.0,  # well above 1.0
    ],
)
def test_preprocessing_threshold_rejects_out_of_range(bad_value: float) -> None:
    """preprocessing_threshold must raise ValidationError for values outside (0.0, 1.0]."""
    with pytest.raises(ValidationError):
        QueryEngineConfig(preprocessing_threshold=bad_value)


@pytest.mark.parametrize(
    "good_value",
    [
        0.5,  # midpoint
        1.0,  # upper boundary (inclusive)
        0.01,  # just above lower boundary
        0.99,  # just below upper boundary
    ],
)
def test_preprocessing_threshold_accepts_valid(good_value: float) -> None:
    """preprocessing_threshold must accept values in the range (0.0, 1.0]."""
    cfg = QueryEngineConfig(preprocessing_threshold=good_value)
    assert cfg.preprocessing_threshold == pytest.approx(good_value)
