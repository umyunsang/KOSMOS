# SPDX-License-Identifier: Apache-2.0
"""Unit tests for CoordinatorPlan model validator.

Covers:
- Rejection of depends_on with out-of-range index
- Rejection of self-reference (steps[i].depends_on == [i])
- Acceptance of empty depends_on

T015 — FR-005, SC-002.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from kosmos.agents.plan import (
    CoordinatorPlan,
    ExecutionMode,
    PlanStatus,
    PlanStep,
    StepStatus,
)


def _step(
    ministry: str = "civil_affairs",
    action: str = "Do something",
    depends_on: list[int] | None = None,
    execution_mode: ExecutionMode = ExecutionMode.parallel,
    status: StepStatus = StepStatus.pending,
) -> PlanStep:
    return PlanStep(
        ministry=ministry,
        action=action,
        depends_on=depends_on or [],
        execution_mode=execution_mode,
        status=status,
    )


def _plan(steps: list[PlanStep], status: PlanStatus = PlanStatus.complete) -> CoordinatorPlan:
    return CoordinatorPlan(
        session_id=uuid4(),
        status=status,
        steps=steps,
        worker_correlation_ids=[uuid4()],
    )


def test_valid_plan_no_deps() -> None:
    """A plan with no inter-step dependencies should be accepted."""
    plan = _plan([_step(), _step(ministry="transport")])
    assert len(plan.steps) == 2


def test_valid_plan_with_valid_dep() -> None:
    """depends_on=[0] is valid when step 1 references step 0."""
    s0 = _step(ministry="civil_affairs")
    s1 = _step(ministry="transport", depends_on=[0])
    plan = _plan([s0, s1])
    assert plan.steps[1].depends_on == [0]


def test_reject_out_of_range_dep() -> None:
    """depends_on index >= len(steps) must raise ValidationError."""
    s0 = _step()
    s1 = _step(depends_on=[5])  # index 5 does not exist in a 2-step plan
    with pytest.raises(ValidationError, match="out-of-range"):
        _plan([s0, s1])


def test_reject_negative_dep() -> None:
    """Negative depends_on index must raise ValidationError."""
    s0 = _step()
    s1 = _step(depends_on=[-1])
    with pytest.raises(ValidationError, match="out-of-range"):
        _plan([s0, s1])


def test_reject_self_reference() -> None:
    """steps[i].depends_on == [i] must raise ValidationError."""
    s0 = _step()
    s1 = _step(depends_on=[1])  # self-reference (step 1 → step 1)
    with pytest.raises(ValidationError, match="references itself"):
        _plan([s0, s1])


def test_accept_empty_depends_on() -> None:
    """depends_on=[] (no predecessors) must be accepted."""
    s = _step(depends_on=[])
    plan = _plan([s])
    assert plan.steps[0].depends_on == []


def test_plan_no_results_status() -> None:
    """A plan with status='no_results' and no steps is valid."""
    plan = CoordinatorPlan(
        session_id=uuid4(),
        status=PlanStatus.no_results,
        steps=[],
        worker_correlation_ids=[],
        message="All workers failed.",
    )
    assert plan.status == PlanStatus.no_results
    assert plan.message == "All workers failed."


def test_plan_frozen() -> None:
    """CoordinatorPlan must be frozen (immutable)."""
    plan = _plan([_step()])
    with pytest.raises((TypeError, ValidationError)):
        plan.status = PlanStatus.failed  # type: ignore[misc]
