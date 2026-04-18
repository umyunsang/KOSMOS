# SPDX-License-Identifier: Apache-2.0
"""Contract test: validate agent-message.schema.json against all 6 AgentMessage variants.

T016 — FR-016, US1 contract gate.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

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

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "027-agent-swarm-core"
    / "contracts"
    / "agent-message.schema.json"
)


def _schema() -> dict:  # type: ignore[type-arg]
    return json.loads(_SCHEMA_PATH.read_text())


def _meta() -> LookupMeta:
    return LookupMeta(
        source="lookup",
        fetched_at=datetime.now(UTC),
        request_id=str(uuid4()),
        elapsed_ms=5,
    )


def _msg(msg_type: MessageType, payload: object) -> dict:  # type: ignore[type-arg]
    msg = AgentMessage(
        sender="coordinator",
        recipient="worker-test",
        msg_type=msg_type,
        payload=payload,  # type: ignore[arg-type]
        timestamp=datetime.now(UTC),
        correlation_id=uuid4(),
    )
    return json.loads(msg.model_dump_json())


def _validate(instance: dict) -> None:  # type: ignore[type-arg]
    """Validate instance against the schema using jsonschema if available."""
    try:
        import jsonschema  # type: ignore[import]

        jsonschema.validate(instance=instance, schema=_schema())
    except ImportError:
        # jsonschema not installed; just assert required fields are present
        for field in ["id", "sender", "recipient", "msg_type", "payload", "timestamp"]:
            assert field in instance, f"Missing required field: {field}"
        assert instance["msg_type"] in [
            "task",
            "result",
            "error",
            "permission_request",
            "permission_response",
            "cancel",
        ]
        payload = instance["payload"]
        assert "kind" in payload
        assert payload["kind"] == instance["msg_type"]


def test_task_message_schema() -> None:
    payload = TaskPayload(instruction="Research civil affairs", specialist_role="civil_affairs")
    instance = _msg(MessageType.task, payload)
    _validate(instance)
    assert instance["msg_type"] == "task"
    assert instance["payload"]["kind"] == "task"


def test_result_message_schema() -> None:
    record = LookupRecord(kind="record", item={"address": "Seoul"}, meta=_meta())
    payload = ResultPayload(lookup_output=record, turn_count=1)
    instance = _msg(MessageType.result, payload)
    _validate(instance)
    assert instance["payload"]["kind"] == "result"
    assert instance["payload"]["lookup_output"]["kind"] == "record"


def test_error_message_schema() -> None:
    payload = ErrorPayload(
        error_type="max_iterations_reached",
        message="Loop cap exceeded",
    )
    instance = _msg(MessageType.error, payload)
    _validate(instance)
    assert instance["payload"]["kind"] == "error"


def test_permission_request_message_schema() -> None:
    payload = PermissionRequestPayload(tool_id="nmc_emergency_search", reason="auth_required")
    instance = _msg(MessageType.permission_request, payload)
    _validate(instance)
    assert instance["payload"]["kind"] == "permission_request"


def test_permission_response_message_schema() -> None:
    payload = PermissionResponsePayload(granted=True, tool_id="nmc_emergency_search")
    instance = _msg(MessageType.permission_response, payload)
    _validate(instance)
    assert instance["payload"]["kind"] == "permission_response"


def test_cancel_message_schema() -> None:
    payload = CancelPayload()
    instance = _msg(MessageType.cancel, payload)
    _validate(instance)
    assert instance["payload"]["kind"] == "cancel"


def test_all_payload_kinds_have_no_additional_properties() -> None:
    """Schema requires additionalProperties=false for all payloads."""
    schema = _schema()
    for name in [
        "TaskPayload",
        "ResultPayload",
        "ErrorPayload",
        "PermissionRequestPayload",
        "PermissionResponsePayload",
        "CancelPayload",
    ]:
        definition = schema["$defs"][name]
        assert definition.get("additionalProperties") is False, (
            f"{name} must have additionalProperties=false"
        )
