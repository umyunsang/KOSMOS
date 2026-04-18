# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the IPC frame schema (T014).

Covers:
- (a) Round-trip: model_validate_json → model_dump_json → model_validate_json
      for all 10 discriminated-union arms.
- (b) model_json_schema() contains all 10 discriminator kind values.
- (c) Invalid / missing required fields raise ValidationError.
- (d) Schema arms where per-file examples were absent: synthesised defaults are
      documented inline (see SYNTHESISED_ARMS).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from kosmos.ipc.frame_schema import IPCFrame, ipc_frame_json_schema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "287-tui-ink-react-bun"
    / "contracts"
)

# Arms whose per-arm JSON Schema files had no "examples" field; minimal valid
# payloads were synthesised from the schema's "required" properties and their
# stated types.
SYNTHESISED_ARMS: frozenset[str] = frozenset(
    {
        "user_input",
        "assistant_chunk",
        "tool_call",
        "tool_result",
        "coordinator_phase",
        "worker_status",
        "permission_request",
        "permission_response",
        "session_event",
        "error",
    }
)

_TS = "2025-01-01T00:00:00Z"
_SESSION_ID = "01HNMJ1Z000000000000000000"  # valid ULID-format string

# ---------------------------------------------------------------------------
# Minimal valid examples per arm
# ---------------------------------------------------------------------------

_MINIMAL_EXAMPLES: dict[str, dict[str, Any]] = {
    "user_input": {
        "kind": "user_input",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "text": "안녕하세요",
    },
    "assistant_chunk": {
        "kind": "assistant_chunk",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "message_id": "01HNMJ2Z000000000000000001",
        "delta": "안녕",
        "done": False,
    },
    "tool_call": {
        "kind": "tool_call",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "call_id": "01HNMJ3Z000000000000000002",
        "name": "lookup",
        "arguments": {"mode": "search", "query": "서울 병원"},
    },
    "tool_result": {
        "kind": "tool_result",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "call_id": "01HNMJ3Z000000000000000002",
        "envelope": {"kind": "lookup"},
    },
    "coordinator_phase": {
        "kind": "coordinator_phase",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "phase": "Research",
    },
    "worker_status": {
        "kind": "worker_status",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "worker_id": "worker-001",
        "role_id": "transport-specialist",
        "current_primitive": "lookup",
        "status": "running",
    },
    "permission_request": {
        "kind": "permission_request",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "request_id": "01HNMJ4Z000000000000000003",
        "worker_id": "worker-001",
        "primitive_kind": "submit",
        "description_ko": "제출 권한이 필요합니다",
        "description_en": "Permission to submit required",
        "risk_level": "medium",
    },
    "permission_response": {
        "kind": "permission_response",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "request_id": "01HNMJ4Z000000000000000003",
        "decision": "granted",
    },
    "session_event": {
        "kind": "session_event",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "event": "save",
        "payload": {},
    },
    "error": {
        "kind": "error",
        "session_id": _SESSION_ID,
        "ts": _TS,
        "code": "backend_crash",
        "message": "Unexpected backend error",
        "details": {},
    },
}

_EXPECTED_ARMS = frozenset(_MINIMAL_EXAMPLES.keys())
_ADAPTER: TypeAdapter[Any] = TypeAdapter(IPCFrame)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _validate_roundtrip(example: dict[str, Any]) -> None:
    """Parse → dump → parse and assert structural equality."""
    raw = json.dumps(example)
    frame1 = _ADAPTER.validate_json(raw)
    dumped = _ADAPTER.dump_json(frame1)
    frame2 = _ADAPTER.validate_json(dumped)
    assert _ADAPTER.dump_python(frame1) == _ADAPTER.dump_python(frame2), (
        f"Round-trip failed for kind={example['kind']!r}"
    )


# ---------------------------------------------------------------------------
# Tests: one per arm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", sorted(_MINIMAL_EXAMPLES.keys()))
def test_arm_round_trip(arm: str) -> None:
    """Each arm validates and round-trips without data loss."""
    _validate_roundtrip(_MINIMAL_EXAMPLES[arm])


@pytest.mark.parametrize("arm", sorted(_MINIMAL_EXAMPLES.keys()))
def test_arm_kind_field(arm: str) -> None:
    """Parsed frame has correct kind field."""
    raw = json.dumps(_MINIMAL_EXAMPLES[arm])
    frame = _ADAPTER.validate_json(raw)
    assert _ADAPTER.dump_python(frame)["kind"] == arm


# ---------------------------------------------------------------------------
# Tests: union-level schema
# ---------------------------------------------------------------------------


def test_json_schema_contains_all_discriminators() -> None:
    """ipc_frame_json_schema() exposes all 10 discriminator values."""
    schema = ipc_frame_json_schema()
    discriminator = schema.get("discriminator", {})
    mapping = discriminator.get("mapping", {})
    found = frozenset(mapping.keys())
    assert found == _EXPECTED_ARMS, (
        f"Missing arms: {_EXPECTED_ARMS - found}; unexpected: {found - _EXPECTED_ARMS}"
    )


def test_json_schema_is_serialisable() -> None:
    """ipc_frame_json_schema() output must be JSON-serialisable (no Python-only objects)."""
    schema = ipc_frame_json_schema()
    json.dumps(schema)  # raises TypeError on non-serialisable types


# ---------------------------------------------------------------------------
# Tests: contract files exist for all arms
# ---------------------------------------------------------------------------


def test_contract_files_present() -> None:
    """Each arm must have a corresponding *.schema.json file in contracts/."""
    arm_to_file = {
        "user_input": "user-input.schema.json",
        "assistant_chunk": "assistant-chunk.schema.json",
        "tool_call": "tool-call.schema.json",
        "tool_result": "tool-result.schema.json",
        "coordinator_phase": "coordinator-phase.schema.json",
        "worker_status": "worker-status.schema.json",
        "permission_request": "permission-request.schema.json",
        "permission_response": "permission-response.schema.json",
        "session_event": "session-event.schema.json",
        "error": "error.schema.json",
    }
    for arm, filename in arm_to_file.items():
        path = _CONTRACTS_DIR / filename
        assert path.exists(), f"Missing contract file for arm={arm!r}: {path}"


# ---------------------------------------------------------------------------
# Tests: invalid payloads are rejected
# ---------------------------------------------------------------------------


def test_missing_kind_rejected() -> None:
    """Payload without 'kind' must raise ValidationError."""
    payload = {"session_id": _SESSION_ID, "ts": _TS, "text": "hello"}
    with pytest.raises(ValidationError):
        _ADAPTER.validate_json(json.dumps(payload))


def test_unknown_kind_rejected() -> None:
    """Payload with unrecognised 'kind' must raise ValidationError."""
    payload = {"kind": "nonexistent_arm", "session_id": _SESSION_ID, "ts": _TS}
    with pytest.raises(ValidationError):
        _ADAPTER.validate_json(json.dumps(payload))


@pytest.mark.parametrize("arm", sorted(_MINIMAL_EXAMPLES.keys()))
def test_missing_required_field_rejected(arm: str) -> None:
    """Dropping any required field from a minimal example must raise ValidationError."""
    example = dict(_MINIMAL_EXAMPLES[arm])
    # Drop the first non-kind, non-session_id, non-ts field
    extra_keys = [k for k in example if k not in ("kind", "session_id", "ts")]
    if not extra_keys:
        pytest.skip(f"No extra required fields for arm={arm!r}")
    drop_key = extra_keys[0]
    del example[drop_key]
    with pytest.raises(ValidationError):
        _ADAPTER.validate_json(json.dumps(example))


def test_extra_field_rejected() -> None:
    """Extra fields on the union base are forbidden (extra='forbid')."""
    payload = dict(_MINIMAL_EXAMPLES["user_input"])
    payload["unknown_extra"] = "should_be_rejected"
    with pytest.raises(ValidationError):
        _ADAPTER.validate_json(json.dumps(payload))


# ---------------------------------------------------------------------------
# Tests: optional correlation_id
# ---------------------------------------------------------------------------


def test_correlation_id_null_accepted() -> None:
    """correlation_id=null is accepted on any arm."""
    payload = dict(_MINIMAL_EXAMPLES["assistant_chunk"])
    payload["correlation_id"] = None
    _validate_roundtrip(payload)


def test_correlation_id_string_accepted() -> None:
    """correlation_id as a ULID string is accepted."""
    payload = dict(_MINIMAL_EXAMPLES["assistant_chunk"])
    payload["correlation_id"] = "01HNMJ5Z000000000000000099"
    _validate_roundtrip(payload)
