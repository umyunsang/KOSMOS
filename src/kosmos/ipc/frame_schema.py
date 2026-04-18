# SPDX-License-Identifier: Apache-2.0
"""IPC frame schema — Pydantic v2 discriminated union.

Source of truth for the KOSMOS TUI ↔ Python backend JSONL protocol.
Every change here MUST be reflected in the TypeScript generated types by
running ``bun run gen:ipc`` from ``tui/``.

Protocol version: 1  (matches x-ipc-protocol-version in ipc-frames.schema.json)
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class _BaseFrame(BaseModel):
    """Shared envelope fields present on every IPC frame."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    session_id: str = Field(description="ULID; shared across all frames in a session.")
    correlation_id: str | None = Field(
        default=None,
        description="ULID of the triggering frame; null for unsolicited frames.",
    )
    ts: str = Field(description="RFC 3339 UTC timestamp.")


# ---------------------------------------------------------------------------
# Arm: user_input
# ---------------------------------------------------------------------------


class UserInputFrame(_BaseFrame):
    """TUI → backend: a citizen's typed input."""

    kind: Literal["user_input"] = Field(
        description="Frame discriminator.",
    )
    text: str = Field(
        description="Raw user text in UTF-8 (may contain Korean, English, emoji)."
    )


# ---------------------------------------------------------------------------
# Arm: assistant_chunk
# ---------------------------------------------------------------------------


class AssistantChunkFrame(_BaseFrame):
    """backend → TUI: streaming assistant text delta."""

    kind: Literal["assistant_chunk"] = Field(description="Frame discriminator.")
    message_id: str = Field(
        description="ULID of the assistant message this delta belongs to."
    )
    delta: str = Field(description="UTF-8 text appended to the message.")
    done: bool = Field(
        description="True if this is the terminal chunk for this message_id."
    )


# ---------------------------------------------------------------------------
# Arm: tool_call
# ---------------------------------------------------------------------------


class ToolCallFrame(_BaseFrame):
    """backend → TUI (display only): a tool invocation decision by the model."""

    kind: Literal["tool_call"] = Field(description="Frame discriminator.")
    call_id: str = Field(
        description="ULID correlating this call to its subsequent tool_result."
    )
    name: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = Field(
        description="Primitive name per Spec 031."
    )
    arguments: dict[str, Any] = Field(
        description="Primitive-specific arguments; shape per Spec 031 input schemas."
    )


# ---------------------------------------------------------------------------
# Arm: tool_result
# ---------------------------------------------------------------------------


class ToolResultEnvelope(BaseModel):
    """5-primitive discriminated union envelope (open schema)."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    kind: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = Field(
        description="Primitive kind discriminator per Spec 031."
    )


class ToolResultFrame(_BaseFrame):
    """backend → TUI (render): the output of a tool invocation."""

    kind: Literal["tool_result"] = Field(description="Frame discriminator.")
    call_id: str = Field(
        description="ULID correlating this result to its originating tool_call."
    )
    envelope: ToolResultEnvelope = Field(
        description="5-primitive discriminated union. Unknown kind falls to UnrecognizedPayload."
    )


# ---------------------------------------------------------------------------
# Arm: coordinator_phase
# ---------------------------------------------------------------------------


class CoordinatorPhaseFrame(_BaseFrame):
    """backend → TUI: Spec 027 coordinator phase update."""

    kind: Literal["coordinator_phase"] = Field(description="Frame discriminator.")
    phase: Literal["Research", "Synthesis", "Implementation", "Verification"] = Field(
        description="Current coordinator phase."
    )


# ---------------------------------------------------------------------------
# Arm: worker_status
# ---------------------------------------------------------------------------


class WorkerStatusFrame(_BaseFrame):
    """backend → TUI: per-worker status row update from Spec 027 swarm."""

    kind: Literal["worker_status"] = Field(description="Frame discriminator.")
    worker_id: str = Field(description="Unique worker identifier.")
    role_id: str = Field(
        description="Specialist label (e.g., transport-specialist, health-specialist)."
    )
    current_primitive: Literal[
        "lookup", "resolve_location", "submit", "subscribe", "verify"
    ] = Field(description="Primitive currently being invoked by this worker.")
    status: Literal["idle", "running", "waiting_permission", "error"] = Field(
        description="Worker execution status."
    )


# ---------------------------------------------------------------------------
# Arm: permission_request
# ---------------------------------------------------------------------------


class PermissionRequestFrame(_BaseFrame):
    """backend → TUI: a worker raises a permission request."""

    kind: Literal["permission_request"] = Field(description="Frame discriminator.")
    request_id: str = Field(
        description="ULID; round-trips in the matching permission_response frame."
    )
    worker_id: str = Field(description="Worker requesting permission.")
    primitive_kind: Literal[
        "lookup", "resolve_location", "submit", "subscribe", "verify"
    ] = Field(description="The primitive the worker wants to invoke.")
    description_ko: str = Field(
        description="Korean-language description shown to the citizen."
    )
    description_en: str = Field(
        description="English-language description shown alongside the Korean one."
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk classification of the requested operation."
    )


# ---------------------------------------------------------------------------
# Arm: permission_response
# ---------------------------------------------------------------------------


class PermissionResponseFrame(_BaseFrame):
    """TUI → backend: citizen's decision on a permission_request."""

    kind: Literal["permission_response"] = Field(description="Frame discriminator.")
    request_id: str = Field(
        description="ULID matching the originating permission_request.request_id."
    )
    decision: Literal["granted", "denied"] = Field(
        description="Citizen's permission decision."
    )


# ---------------------------------------------------------------------------
# Arm: session_event
# ---------------------------------------------------------------------------


class SessionEventFrame(_BaseFrame):
    """Bidirectional: session lifecycle events."""

    kind: Literal["session_event"] = Field(description="Frame discriminator.")
    event: Literal["save", "load", "list", "resume", "new", "exit"] = Field(
        description="Session lifecycle event type."
    )
    payload: dict[str, Any] = Field(
        description=(
            "Event-specific payload. "
            "For list: {sessions: [{id, created_at, turn_count}]}. "
            "For resume: {id: str}. For others: {}."
        )
    )


# ---------------------------------------------------------------------------
# Arm: error
# ---------------------------------------------------------------------------


class ErrorFrame(_BaseFrame):
    """backend → TUI: a backend error surfaced to the TUI for rendering."""

    kind: Literal["error"] = Field(description="Frame discriminator.")
    code: str = Field(
        description="Machine-readable error code (e.g., 'backend_crash', 'protocol_mismatch')."
    )
    message: str = Field(
        description=(
            "Human-readable short message. "
            "MUST NOT contain KOSMOS_*-prefixed env var values (FR-004 redaction rule)."
        )
    )
    details: dict[str, Any] = Field(
        description="Structured error details. KOSMOS_* env var values MUST be redacted."
    )


# ---------------------------------------------------------------------------
# Discriminated union
# ---------------------------------------------------------------------------

IPCFrame = Annotated[
    Union[
        UserInputFrame,
        AssistantChunkFrame,
        ToolCallFrame,
        ToolResultFrame,
        CoordinatorPhaseFrame,
        WorkerStatusFrame,
        PermissionRequestFrame,
        PermissionResponseFrame,
        SessionEventFrame,
        ErrorFrame,
    ],
    Field(discriminator="kind"),
]
"""Discriminated union of all 10 IPC frame arms.

Usage::

    from kosmos.ipc.frame_schema import IPCFrame
    from pydantic import TypeAdapter

    _adapter = TypeAdapter(IPCFrame)
    frame = _adapter.validate_json(raw_line)
"""


def ipc_frame_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for the ``IPCFrame`` discriminated union.

    Delegates to Pydantic v2's ``TypeAdapter.json_schema()``.
    """
    from pydantic import TypeAdapter

    adapter: TypeAdapter[Any] = TypeAdapter(IPCFrame)
    return adapter.json_schema()


__all__ = [
    "IPCFrame",
    "UserInputFrame",
    "AssistantChunkFrame",
    "ToolCallFrame",
    "ToolResultFrame",
    "ToolResultEnvelope",
    "CoordinatorPhaseFrame",
    "WorkerStatusFrame",
    "PermissionRequestFrame",
    "PermissionResponseFrame",
    "SessionEventFrame",
    "ErrorFrame",
    "ipc_frame_json_schema",
]
