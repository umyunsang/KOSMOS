# SPDX-License-Identifier: Apache-2.0
"""AgentMessage and payload models for the file-based mailbox IPC.

All models are Pydantic v2 with extra="forbid" and frozen=True.
The AgentMessagePayload is a closed discriminated union on the 'kind'
field — Any is forbidden everywhere per Constitution Principle III.

FR traces: FR-016, FR-025, data-model.md §2.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.tools.models import LookupCollection, LookupRecord, LookupTimeseries


class MessageType(StrEnum):
    """Closed enumeration of message types in the agent mailbox.

    Each value corresponds exactly to the 'kind' field in the matching
    payload model, enforced by AgentMessage._msg_type_matches_payload_kind.
    """

    task = "task"
    result = "result"
    error = "error"
    permission_request = "permission_request"
    permission_response = "permission_response"
    cancel = "cancel"


# ---------------------------------------------------------------------------
# Six payload union members — all frozen, all extra="forbid"
# ---------------------------------------------------------------------------


class TaskPayload(BaseModel):
    """Payload for a task message sent from coordinator to worker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["task"] = "task"
    instruction: str = Field(min_length=1)
    """Human-readable instruction for the worker specialist."""

    specialist_role: str = Field(min_length=1, max_length=64)
    """The specialist role this task is addressed to."""


class ResultPayload(BaseModel):
    """Payload for a result message sent from worker to coordinator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["result"] = "result"
    lookup_output: LookupRecord | LookupCollection | LookupTimeseries = Field(discriminator="kind")
    """The output from the worker's tool-loop run."""

    turn_count: int = Field(ge=0)
    """Number of tool-loop iterations the worker executed."""


class ErrorPayload(BaseModel):
    """Payload for an error message sent from worker to coordinator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["error"] = "error"
    error_type: str = Field(min_length=1)
    """Short error class name (e.g. 'max_iterations_reached', 'lookup_failed')."""

    message: str = Field(min_length=1)
    """Human-readable error description."""

    retryable: bool = False
    """Whether the coordinator may retry dispatching this worker."""


class PermissionRequestPayload(BaseModel):
    """Payload for a permission_request from worker to coordinator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["permission_request"] = "permission_request"
    tool_id: str = Field(min_length=1)
    """The tool ID that requires citizen consent."""

    reason: str = Field(min_length=1)
    """Why the tool requires auth (e.g., 'auth_required')."""


class PermissionResponsePayload(BaseModel):
    """Payload for a permission_response from coordinator to worker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["permission_response"] = "permission_response"
    granted: bool
    """Whether the citizen granted or denied consent."""

    tool_id: str = Field(min_length=1)
    """The tool ID the response pertains to."""


class CancelPayload(BaseModel):
    """Payload for a cancel message from coordinator to worker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["cancel"] = "cancel"
    reason: str = Field(min_length=1, default="coordinator_requested")
    """Reason for cancellation."""


# ---------------------------------------------------------------------------
# Closed discriminated union
# ---------------------------------------------------------------------------

AgentMessagePayload = Annotated[
    TaskPayload
    | ResultPayload
    | ErrorPayload
    | PermissionRequestPayload
    | PermissionResponsePayload
    | CancelPayload,
    Field(discriminator="kind"),
]
"""Closed union — six variants, no Any, no open-ended dict.

The discriminator is the 'kind' field present on every member.
Any is forbidden in this union and all its members (Constitution III).
"""


# ---------------------------------------------------------------------------
# AgentMessage — the envelope
# ---------------------------------------------------------------------------


class AgentMessage(BaseModel):
    """Envelope for all inter-agent messages in the KOSMOS mailbox.

    msg_type and payload.kind MUST match (enforced by model_validator).
    Routing is by the declared 'recipient' field; the FileMailbox enforces
    this at read time (FR-025 — permissions MUST NOT flow laterally).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    """Unique message identifier (UUID4). Also used as the on-disk filename stem."""

    sender: str = Field(min_length=1, max_length=128)
    """Sender ID (e.g., 'coordinator' or 'worker-transport-<uuid4>')."""

    recipient: str = Field(min_length=1, max_length=128)
    """Recipient ID. FileMailbox only yields messages to the declared recipient."""

    msg_type: MessageType
    """Message type discriminator — MUST match payload.kind."""

    payload: AgentMessagePayload
    """Closed discriminated union on payload.kind."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """ISO 8601 UTC timestamp of message creation."""

    correlation_id: UUID | None = None
    """Links related messages (e.g., permission_request ↔ permission_response)."""

    @model_validator(mode="after")
    def _msg_type_matches_payload_kind(self) -> AgentMessage:
        """Invariant: msg_type enum value == payload.kind string."""
        if self.msg_type.value != self.payload.kind:
            raise ValueError(
                f"msg_type={self.msg_type.value!r} does not match "
                f"payload.kind={self.payload.kind!r}"
            )
        return self
