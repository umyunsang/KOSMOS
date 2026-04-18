# SPDX-License-Identifier: Apache-2.0
"""Contract test: validate coordinator-plan.schema.json against CoordinatorPlan instances.

T017 — FR-005, SC-002, US1 contract gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from kosmos.agents.plan import (
    CoordinatorPlan,
    ExecutionMode,
    PlanStatus,
    PlanStep,
    StepStatus,
)

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "027-agent-swarm-core"
    / "contracts"
    / "coordinator-plan.schema.json"
)


def _schema() -> dict:  # type: ignore[type-arg]
    return json.loads(_SCHEMA_PATH.read_text())


def _validate(instance: dict) -> None:  # type: ignore[type-arg]
    try:
        import jsonschema  # type: ignore[import]

        jsonschema.validate(instance=instance, schema=_schema())
    except ImportError:
        for field in ["session_id", "status", "steps", "worker_correlation_ids"]:
            assert field in instance, f"Missing required field: {field}"
        assert instance["status"] in ["complete", "partial", "no_results", "failed"]


def _plan(*steps: PlanStep, status: PlanStatus = PlanStatus.complete) -> dict:  # type: ignore[type-arg]
    plan = CoordinatorPlan(
        session_id=uuid4(),
        status=status,
        steps=list(steps),
        worker_correlation_ids=[uuid4(), uuid4()],
        message=None,
    )
    return json.loads(plan.model_dump_json())


def test_complete_plan_schema() -> None:
    s0 = PlanStep(
        ministry="civil_affairs",
        action="Submit residence transfer",
        execution_mode=ExecutionMode.sequential,
    )
    s1 = PlanStep(
        ministry="transport",
        action="Update vehicle registration",
        depends_on=[0],
        execution_mode=ExecutionMode.sequential,
    )
    s2 = PlanStep(
        ministry="health_insurance",
        action="Update insurance address",
        execution_mode=ExecutionMode.parallel,
    )
    instance = _plan(s0, s1, s2)
    _validate(instance)
    assert instance["status"] == "complete"
    assert len(instance["steps"]) == 3


def test_no_results_plan_schema() -> None:
    instance = _plan(status=PlanStatus.no_results)
    instance_obj = CoordinatorPlan(
        session_id=uuid4(),
        status=PlanStatus.no_results,
        steps=[],
        worker_correlation_ids=[],
        message="All workers failed.",
    )
    data = json.loads(instance_obj.model_dump_json())
    _validate(data)
    assert data["status"] == "no_results"
    assert data["message"] == "All workers failed."


def test_plan_step_execution_mode_values() -> None:
    schema = _schema()
    step_schema = schema["$defs"]["PlanStep"]
    mode_enum = step_schema["properties"]["execution_mode"]["enum"]
    assert "sequential" in mode_enum
    assert "parallel" in mode_enum


def test_plan_schema_has_no_additional_properties() -> None:
    schema = _schema()
    assert schema.get("additionalProperties") is False
    assert schema["$defs"]["PlanStep"].get("additionalProperties") is False


def test_worker_correlation_ids_in_schema() -> None:
    """Zero-orphan-id invariant (SC-002): correlation IDs must appear in output."""
    cid1, cid2 = uuid4(), uuid4()
    plan = CoordinatorPlan(
        session_id=uuid4(),
        status=PlanStatus.complete,
        steps=[],
        worker_correlation_ids=[cid1, cid2],
    )
    data = json.loads(plan.model_dump_json())
    ids = data["worker_correlation_ids"]
    assert str(cid1) in ids
    assert str(cid2) in ids
