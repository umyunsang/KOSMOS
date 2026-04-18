# SPDX-License-Identifier: Apache-2.0
"""CoordinatorPlan and PlanStep Pydantic v2 models.

The CoordinatorPlan is produced by the Synthesis phase of the Coordinator
and consumed by the Implementation + Verification phases.

FR traces: FR-005, SC-002, data-model.md §3.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanStatus(StrEnum):
    """Status of the CoordinatorPlan as a whole."""

    complete = "complete"
    partial = "partial"
    no_results = "no_results"
    failed = "failed"


class ExecutionMode(StrEnum):
    """Whether a PlanStep can run in parallel or must run sequentially."""

    sequential = "sequential"
    parallel = "parallel"


class StepStatus(StrEnum):
    """Execution status of a single PlanStep."""

    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"


class PlanStep(BaseModel):
    """A single actionable step in the CoordinatorPlan.

    depends_on references indices into the parent CoordinatorPlan.steps list.
    An empty list means the step has no predecessors and can start immediately.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    ministry: str = Field(min_length=1, max_length=64)
    """Ministry or agency responsible for this step."""

    action: str = Field(min_length=1)
    """Human-readable description of the action required."""

    depends_on: list[int] = Field(default_factory=list)
    """Indices into CoordinatorPlan.steps; empty list means 'no predecessors'."""

    execution_mode: ExecutionMode
    """Whether this step can run in parallel or must run after predecessors."""

    status: StepStatus = StepStatus.pending
    """Current execution status."""


class CoordinatorPlan(BaseModel):
    """Output of the Coordinator Synthesis phase.

    The plan captures which ministry tasks are needed, their ordering
    constraints, and which worker results contributed to the synthesis.

    SC-002 (zero-orphan-id invariant): every UUID in worker_correlation_ids
    MUST correspond to a result message delivered before Synthesis began.
    This invariant is enforced by the coordinator at synthesis time, not
    here; the model records the claim.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID
    """Session identifier from the coordinator."""

    status: PlanStatus
    """Overall plan status."""

    steps: list[PlanStep]
    """Ordered list of actionable steps. May be empty when status='no_results'."""

    worker_correlation_ids: list[UUID]
    """Every correlation_id of the worker `result` messages that contributed.

    Zero-orphan-id invariant (SC-002): every element here MUST correspond to a
    result message delivered before the Synthesis phase began.
    """

    message: str | None = None
    """Human-readable summary; populated when status is `no_results` or `partial`."""

    @model_validator(mode="after")
    def _depends_on_indices_are_valid(self) -> CoordinatorPlan:
        """Validate that all depends_on references are in-range and non-self-referential."""
        n = len(self.steps)
        for i, step in enumerate(self.steps):
            for dep in step.depends_on:
                if not 0 <= dep < n:
                    raise ValueError(
                        f"steps[{i}].depends_on references out-of-range index {dep} "
                        f"(steps length={n})"
                    )
                if dep == i:
                    raise ValueError(f"steps[{i}].depends_on references itself (index {i})")
        return self
