# SPDX-License-Identifier: Apache-2.0
"""Unit tests for AgentMessage and payload discriminated union.

Covers:
- Round-trip JSON serialize/parse for each of 6 payload kinds
- Rejection of msg_type/payload.kind mismatch
- Closed union (no extra fields allowed in any member)

T014 — FR-016, data-model.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from kosmos.agents.mailbox.messages import (
    AgentMessage,
    CancelPayload,
    ErrorPayload,
    MessageType,
    PermissionRequestPayload,
    PermissionResponsePayload,
    ResultPayload,
    TaskPayload,
)
from kosmos.tools.models import LookupMeta, LookupRecord


def _meta() -> LookupMeta:
    return LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id="00000000-0000-0000-0000-000000000001",
        elapsed_ms=5,
    )


def _make_message(msg_type: MessageType, payload: object) -> AgentMessage:
    return AgentMessage(
        id=uuid4(),
        sender="coordinator",
        recipient="worker-transport-test",
        msg_type=msg_type,
        payload=payload,  # type: ignore[arg-type]
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )


# ---------------------------------------------------------------------------
# Round-trip tests for all 6 payload kinds
# ---------------------------------------------------------------------------


def test_task_payload_round_trip() -> None:
    payload = TaskPayload(instruction="Do something", specialist_role="transport")
    msg = _make_message(MessageType.task, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.task
    assert isinstance(restored.payload, TaskPayload)
    assert restored.payload.instruction == "Do something"


def test_result_payload_round_trip() -> None:
    record = LookupRecord(kind="record", item={"key": "value"}, meta=_meta())
    payload = ResultPayload(lookup_output=record, turn_count=2)
    msg = _make_message(MessageType.result, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.result
    assert isinstance(restored.payload, ResultPayload)
    assert restored.payload.turn_count == 2


def test_error_payload_round_trip() -> None:
    payload = ErrorPayload(
        error_type="max_iterations_reached",
        message="Exceeded loop limit",
        retryable=False,
    )
    msg = _make_message(MessageType.error, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.error
    assert isinstance(restored.payload, ErrorPayload)
    assert restored.payload.error_type == "max_iterations_reached"


def test_permission_request_payload_round_trip() -> None:
    payload = PermissionRequestPayload(
        tool_id="nmc_emergency_search", reason="auth_required"
    )
    msg = _make_message(MessageType.permission_request, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.permission_request
    assert isinstance(restored.payload, PermissionRequestPayload)
    assert restored.payload.tool_id == "nmc_emergency_search"


def test_permission_response_payload_round_trip() -> None:
    payload = PermissionResponsePayload(granted=True, tool_id="nmc_emergency_search")
    msg = _make_message(MessageType.permission_response, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.permission_response
    assert isinstance(restored.payload, PermissionResponsePayload)
    assert restored.payload.granted is True


def test_cancel_payload_round_trip() -> None:
    payload = CancelPayload(reason="coordinator_requested")
    msg = _make_message(MessageType.cancel, payload)
    json_str = msg.model_dump_json()
    restored = AgentMessage.model_validate_json(json_str)
    assert restored.msg_type == MessageType.cancel
    assert isinstance(restored.payload, CancelPayload)


# ---------------------------------------------------------------------------
# msg_type / payload.kind mismatch
# ---------------------------------------------------------------------------


def test_reject_msg_type_payload_mismatch() -> None:
    """msg_type=result but payload.kind=task must raise ValidationError."""
    with pytest.raises(ValidationError, match="does not match"):
        _make_message(
            MessageType.result,
            TaskPayload(instruction="oops", specialist_role="transport"),
        )


# ---------------------------------------------------------------------------
# extra="forbid" on payload members
# ---------------------------------------------------------------------------


def test_task_payload_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="extra_fields_not_permitted|Extra inputs"):
        TaskPayload(instruction="x", specialist_role="y", unexpected="boom")  # type: ignore[call-arg]


def test_cancel_payload_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="extra_fields_not_permitted|Extra inputs"):
        CancelPayload(reason="test", bogus="field")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# AgentMessage extra="forbid"
# ---------------------------------------------------------------------------


def test_agent_message_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match="extra_fields_not_permitted|Extra inputs"):
        payload = CancelPayload()
        AgentMessage(
            sender="coordinator",
            recipient="worker",
            msg_type=MessageType.cancel,
            payload=payload,
            timestamp=datetime.now(UTC),
            extra_unknown_field="boom",  # type: ignore[call-arg]
        )
