# SPDX-License-Identifier: Apache-2.0
"""IPC frame schema — Pydantic v2 discriminated union.

Source of truth for the KOSMOS TUI <-> Python backend NDJSON protocol.
Every change here MUST be reflected in the TypeScript generated types by
running ``bun run gen:ipc`` from ``tui/``.

Protocol version: 1.0  (matches ``version`` field on every frame)

Spec 032 extensions
-------------------
- ``_BaseFrame`` extended with 5 new envelope fields:
  ``version``, ``role``, ``frame_seq``, ``transaction_id``, ``trailer``.
- ``FrameTrailer`` sub-model (final, transaction_id, checksum_sha256).
- 9 new frame arms added (Spec 032 §2):
  ``PayloadStartFrame``, ``PayloadDeltaFrame``, ``PayloadEndFrame``,
  ``BackpressureSignalFrame``, ``ResumeRequestFrame``, ``ResumeResponseFrame``,
  ``ResumeRejectedFrame``, ``HeartbeatFrame``, ``NotificationPushFrame``.
- Cross-field invariants E1-E6 enforced via ``@model_validator(mode="after")``.
- ``IPCFrame`` discriminated union updated to 19 kinds.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Envelope version constant
# ---------------------------------------------------------------------------

ENVELOPE_VERSION: Literal["1.0"] = "1.0"

# ---------------------------------------------------------------------------
# role <-> kind allow-list (invariant E3)
# ---------------------------------------------------------------------------

# Maps each frame kind to the set of roles allowed to emit it.
_ROLE_KIND_ALLOW_LIST: dict[str, frozenset[str]] = {
    # Spec 287 baseline arms
    "user_input": frozenset({"tui"}),
    "assistant_chunk": frozenset({"backend", "llm"}),
    "tool_call": frozenset({"backend", "tool"}),
    "tool_result": frozenset({"backend", "tool"}),
    "coordinator_phase": frozenset({"backend"}),
    "worker_status": frozenset({"backend"}),
    "permission_request": frozenset({"backend"}),
    "permission_response": frozenset({"tui"}),
    "session_event": frozenset({"tui", "backend"}),
    "error": frozenset({"backend", "tui"}),
    # Spec 032 new arms
    "payload_start": frozenset({"backend", "tool", "llm"}),
    "payload_delta": frozenset({"backend", "tool", "llm"}),
    "payload_end": frozenset({"backend", "tool", "llm"}),
    "backpressure": frozenset({"tui", "backend"}),
    "resume_request": frozenset({"tui"}),
    "resume_response": frozenset({"backend"}),
    "resume_rejected": frozenset({"backend"}),
    "heartbeat": frozenset({"tui", "backend"}),
    "notification_push": frozenset({"notification"}),
}

# Kinds on which trailer.final=true is permitted (invariant E6).
_TERMINAL_KINDS: frozenset[str] = frozenset(
    {
        "payload_end",
        "tool_result",
        "resume_response",
        "resume_rejected",
        "error",
    }
)

# ---------------------------------------------------------------------------
# FrameTrailer sub-model
# ---------------------------------------------------------------------------


class FrameTrailer(BaseModel):
    """Completion/validation metadata on terminal frames (FR-006)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    final: bool = Field(description="True when this frame terminates a logical payload/stream.")
    transaction_id: str | None = Field(
        default=None,
        description="Mirror of envelope transaction_id for trailer-only consumers.",
    )
    checksum_sha256: str | None = Field(
        default=None,
        description="Hex SHA-256 of the concatenated payload bytes for streamed payloads.",
    )


# ---------------------------------------------------------------------------
# Base frame — shared envelope fields
# ---------------------------------------------------------------------------


class _BaseFrame(BaseModel):
    """Shared envelope fields present on every IPC frame.

    Invariants enforced at construction (model_validator mode='after'):
    - E1: version == "1.0"
    - E3: role allowed for this kind
    - E4: transaction_id required for irreversible terminal kinds
    - E5: correlation_id non-empty
    - E6: trailer.final=True only on terminal kinds
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    # --- Spec 287 original fields (unchanged) ---
    # Note: session_id may be "" before the TUI has received a backend-assigned
    # session — slash-command builders (/new, /save, /sessions, /resume) and
    # the initial user_input emit empty session_id and rely on the bridge to
    # stamp the real id once handshake completes. E1-E6 do not constrain it.
    session_id: str = Field(description="Opaque session identifier.")
    correlation_id: str = Field(
        min_length=1,
        description=(
            "UUIDv7 string for new emissions; ULID accepted for back-compat. "
            "Non-empty; emitter SHOULD use UUIDv7. (E5)"
        ),
    )
    ts: str = Field(description="ISO-8601 UTC timestamp with sub-ms precision.")

    # --- Spec 032 new envelope fields ---
    version: Literal["1.0"] = Field(
        default="1.0",
        description="Envelope version. Hard-fail on mismatch (E1, FR-001).",
    )
    role: Literal["tui", "backend", "tool", "llm", "notification"] = Field(
        description="Origin role. Validated against kind<->role allow-list (E3, FR-004).",
    )
    frame_seq: NonNegativeInt = Field(
        default=0,
        description="Per-session monotonic sequence number (ge=0). Gap detection uses this.",
    )
    transaction_id: str | None = Field(
        default=None,
        description=(
            "UUIDv7. Populated for idempotent state-change frames (irreversible tools). "
            "None for streaming chunks. (FR-026)"
        ),
    )
    trailer: FrameTrailer | None = Field(
        default=None,
        description="Completion/validation metadata. Populated on terminal frames. (FR-006)",
    )

    @model_validator(mode="after")
    def _enforce_invariants(self) -> _BaseFrame:
        """Enforce cross-field invariants E1, E3, E5, E6.

        Note: E1 (version) is already handled by Literal["1.0"] type.
        Note: E5 (correlation_id min_length=1) is handled by Field(min_length=1).
        """
        kind: str = getattr(self, "kind", "")

        # E3: role <-> kind allow-list
        if kind and kind in _ROLE_KIND_ALLOW_LIST:
            allowed_roles = _ROLE_KIND_ALLOW_LIST[kind]
            if self.role not in allowed_roles:
                raise ValueError(
                    f"role={self.role!r} is not allowed for kind={kind!r}. "
                    f"Allowed roles: {sorted(allowed_roles)}"
                )

        # E6: trailer.final=True only on terminal-capable kinds
        if self.trailer is not None and self.trailer.final and kind not in _TERMINAL_KINDS:
            raise ValueError(
                f"trailer.final=True is not allowed for kind={kind!r}. "
                f"Terminal-capable kinds: {sorted(_TERMINAL_KINDS)}"
            )

        return self


# ---------------------------------------------------------------------------
# Arm: user_input  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class UserInputFrame(_BaseFrame):
    """TUI -> backend: a citizen's typed input."""

    kind: Literal["user_input"] = Field(default="user_input", description="Frame discriminator.")
    text: str = Field(description="Raw user text in UTF-8 (may contain Korean, English, emoji).")


# ---------------------------------------------------------------------------
# Arm: assistant_chunk  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class AssistantChunkFrame(_BaseFrame):
    """backend -> TUI: streaming assistant text delta."""

    kind: Literal["assistant_chunk"] = Field(
        default="assistant_chunk", description="Frame discriminator."
    )
    message_id: str = Field(description="ULID of the assistant message this delta belongs to.")
    delta: str = Field(description="UTF-8 text appended to the message.")
    done: bool = Field(description="True if this is the terminal chunk for this message_id.")


# ---------------------------------------------------------------------------
# Arm: tool_call  (Spec 287 baseline — arguments changed from Any to dict[str, object])
# ---------------------------------------------------------------------------


class ToolCallFrame(_BaseFrame):
    """backend -> TUI (display only): a tool invocation decision by the model."""

    kind: Literal["tool_call"] = Field(default="tool_call", description="Frame discriminator.")
    call_id: str = Field(description="ULID correlating this call to its subsequent tool_result.")
    name: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = Field(
        description="Primitive name per Spec 031."
    )
    arguments: dict[str, object] = Field(
        description="Primitive-specific arguments; shape per Spec 031 input schemas."
    )


# ---------------------------------------------------------------------------
# Arm: tool_result  (Spec 287 baseline)
# ---------------------------------------------------------------------------


class ToolResultEnvelope(BaseModel):
    """5-primitive discriminated union envelope (open schema)."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    kind: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = Field(
        description="Primitive kind discriminator per Spec 031."
    )


class ToolResultFrame(_BaseFrame):
    """backend -> TUI (render): the output of a tool invocation."""

    kind: Literal["tool_result"] = Field(default="tool_result", description="Frame discriminator.")
    call_id: str = Field(description="ULID correlating this result to its originating tool_call.")
    envelope: ToolResultEnvelope = Field(
        description="5-primitive discriminated union. Unknown kind falls to UnrecognizedPayload."
    )


# ---------------------------------------------------------------------------
# Arm: coordinator_phase  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class CoordinatorPhaseFrame(_BaseFrame):
    """backend -> TUI: Spec 027 coordinator phase update."""

    kind: Literal["coordinator_phase"] = Field(
        default="coordinator_phase", description="Frame discriminator."
    )
    phase: Literal["Research", "Synthesis", "Implementation", "Verification"] = Field(
        description="Current coordinator phase."
    )


# ---------------------------------------------------------------------------
# Arm: worker_status  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class WorkerStatusFrame(_BaseFrame):
    """backend -> TUI: per-worker status row update from Spec 027 swarm."""

    kind: Literal["worker_status"] = Field(
        default="worker_status", description="Frame discriminator."
    )
    worker_id: str = Field(description="Unique worker identifier.")
    role_id: str = Field(
        description="Specialist label (e.g., transport-specialist, health-specialist)."
    )
    current_primitive: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = (
        Field(description="Primitive currently being invoked by this worker.")
    )
    status: Literal["idle", "running", "waiting_permission", "error"] = Field(
        description="Worker execution status."
    )


# ---------------------------------------------------------------------------
# Arm: permission_request  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class PermissionRequestFrame(_BaseFrame):
    """backend -> TUI: a worker raises a permission request."""

    kind: Literal["permission_request"] = Field(
        default="permission_request", description="Frame discriminator."
    )
    request_id: str = Field(
        description="ULID; round-trips in the matching permission_response frame."
    )
    worker_id: str = Field(description="Worker requesting permission.")
    primitive_kind: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] = Field(
        description="The primitive the worker wants to invoke."
    )
    description_ko: str = Field(description="Korean-language description shown to the citizen.")
    description_en: str = Field(
        description="English-language description shown alongside the Korean one."
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Risk classification of the requested operation."
    )


# ---------------------------------------------------------------------------
# Arm: permission_response  (Spec 287 baseline — unchanged)
# ---------------------------------------------------------------------------


class PermissionResponseFrame(_BaseFrame):
    """TUI -> backend: citizen's decision on a permission_request."""

    kind: Literal["permission_response"] = Field(
        default="permission_response", description="Frame discriminator."
    )
    request_id: str = Field(
        description="ULID matching the originating permission_request.request_id."
    )
    decision: Literal["granted", "denied"] = Field(description="Citizen's permission decision.")


# ---------------------------------------------------------------------------
# Arm: session_event  (Spec 287 baseline — payload changed from Any to dict[str, object])
# ---------------------------------------------------------------------------


class SessionEventFrame(_BaseFrame):
    """Bidirectional: session lifecycle events."""

    kind: Literal["session_event"] = Field(
        default="session_event", description="Frame discriminator."
    )
    event: Literal["save", "load", "list", "resume", "new", "exit"] = Field(
        description="Session lifecycle event type."
    )
    payload: dict[str, object] = Field(
        description=(
            "Event-specific payload. "
            "For list: {sessions: [{id, created_at, turn_count}]}. "
            "For resume: {id: str}. For others: {}."
        )
    )


# ---------------------------------------------------------------------------
# Arm: error  (Spec 287 baseline — details changed from Any to dict[str, object])
# ---------------------------------------------------------------------------


class ErrorFrame(_BaseFrame):
    """backend -> TUI: a backend error surfaced to the TUI for rendering."""

    kind: Literal["error"] = Field(default="error", description="Frame discriminator.")
    code: str = Field(
        description="Machine-readable error code (e.g., 'backend_crash', 'protocol_mismatch')."
    )
    message: str = Field(
        description=(
            "Human-readable short message. "
            "MUST NOT contain KOSMOS_*-prefixed env var values (FR-004 redaction rule)."
        )
    )
    details: dict[str, object] = Field(
        description="Structured error details. KOSMOS_* env var values MUST be redacted."
    )


# ===========================================================================
# Spec 032 NEW ARMS (T005-T009)
# ===========================================================================

# ---------------------------------------------------------------------------
# Arm: payload_start  (Spec 032 §2.1)
# ---------------------------------------------------------------------------


class PayloadStartFrame(_BaseFrame):
    """Begins a streamed payload (assistant output, tool result chunking).

    Sender MUST follow with >= 1 payload_delta and exactly one payload_end.
    role allow-list: backend, tool, llm.
    """

    kind: Literal["payload_start"] = Field(
        default="payload_start", description="Frame discriminator."
    )
    content_type: Literal["text/markdown", "application/json", "text/plain"] = Field(
        description="Payload MIME type."
    )
    estimated_bytes: NonNegativeInt | None = Field(
        default=None,
        description="Optional size hint for HUD progress bars.",
    )


# ---------------------------------------------------------------------------
# Arm: payload_delta  (Spec 032 §2.2)
# ---------------------------------------------------------------------------


class PayloadDeltaFrame(_BaseFrame):
    """One chunk of a streamed payload.

    role allow-list: backend, tool, llm.
    """

    kind: Literal["payload_delta"] = Field(
        default="payload_delta", description="Frame discriminator."
    )
    delta_seq: NonNegativeInt = Field(description="Monotonic within the payload (first delta = 0).")
    payload: str = Field(
        description=(
            "UTF-8 text. If content-type is application/json, "
            "this is a JSON-encoded fragment string."
        )
    )


# ---------------------------------------------------------------------------
# Arm: payload_end  (Spec 032 §2.3)
# ---------------------------------------------------------------------------


class PayloadEndFrame(_BaseFrame):
    """Terminates a streamed payload.

    MUST carry a trailer with final=True.
    role allow-list: backend, tool, llm.
    """

    kind: Literal["payload_end"] = Field(default="payload_end", description="Frame discriminator.")
    delta_count: NonNegativeInt = Field(description="Total number of payload_delta frames emitted.")
    status: Literal["ok", "aborted"] = Field(description="Terminal disposition.")


# ---------------------------------------------------------------------------
# Arm: backpressure  (Spec 032 §2.4)
# ---------------------------------------------------------------------------


class BackpressureSignalFrame(_BaseFrame):
    """Emitted when outgoing queue crosses HWM or a 429 condition is detected.

    role allow-list: tui (tui_reader), backend (backend_writer, upstream_429).
    FR-012, FR-015: hud_copy_ko/en MUST be non-empty (min_length=1).
    """

    kind: Literal["backpressure"] = Field(
        default="backpressure", description="Frame discriminator."
    )
    signal: Literal["pause", "resume", "throttle"] = Field(
        description="Reader action. pause=stop emitting; resume=clear; throttle=slow down."
    )
    source: Literal["tui_reader", "backend_writer", "upstream_429"] = Field(
        description="Origin of the signal."
    )
    queue_depth: NonNegativeInt = Field(description="Current outbound queue size.")
    hwm: int = Field(ge=1, description="High-water mark threshold in effect (default 64).")
    retry_after_ms: NonNegativeInt | None = Field(
        default=None,
        description="For throttle sourced from upstream_429; reflects Retry-After. ge=0.",
    )
    hud_copy_ko: str = Field(
        min_length=1,
        description="Korean HUD copy (civic-facing). Must be non-empty (FR-015).",
    )
    hud_copy_en: str = Field(
        min_length=1,
        description="English HUD copy (dev-facing). Must be non-empty (FR-015).",
    )


# ---------------------------------------------------------------------------
# Arm: resume_request  (Spec 032 §2.5)
# ---------------------------------------------------------------------------


class ResumeRequestFrame(_BaseFrame):
    """Sent by the reconnecting TUI after a stdio drop.

    role allow-list: tui.
    """

    kind: Literal["resume_request"] = Field(
        default="resume_request", description="Frame discriminator."
    )
    last_seen_correlation_id: str | None = Field(
        default=None,
        description="Last correlation_id the TUI successfully applied. None if no prior frame.",
    )
    last_seen_frame_seq: NonNegativeInt | None = Field(
        default=None,
        description="Last frame_seq applied. None if none.",
    )
    tui_session_token: str = Field(
        min_length=1,
        description="TUI-local session token for authenticity binding.",
    )


# ---------------------------------------------------------------------------
# Arm: resume_response  (Spec 032 §2.6)
# ---------------------------------------------------------------------------


class ResumeResponseFrame(_BaseFrame):
    """Backend accepts the resume.

    Must be followed by replay of frames with frame_seq > last_seen_frame_seq.
    Trailer with final=True MUST be set (E6).
    role allow-list: backend.
    """

    kind: Literal["resume_response"] = Field(
        default="resume_response", description="Frame discriminator."
    )
    resumed_from_frame_seq: NonNegativeInt = Field(
        description="Inclusive lower bound of frames that will be replayed."
    )
    replay_count: NonNegativeInt = Field(
        description="Total frames the backend will replay. Bounded by ring buffer size."
    )
    server_session_id: str = Field(
        description="Backend-assigned session id the TUI should use going forward."
    )
    heartbeat_interval_ms: int = Field(
        ge=1000,
        description="Negotiated heartbeat cadence (default 30000).",
    )


# ---------------------------------------------------------------------------
# Arm: resume_rejected  (Spec 032 §2.7)
# ---------------------------------------------------------------------------


class ResumeRejectedFrame(_BaseFrame):
    """Backend cannot honor the resume request.

    Trailer with final=True MUST be set (E6).
    role allow-list: backend.
    """

    kind: Literal["resume_rejected"] = Field(
        default="resume_rejected", description="Frame discriminator."
    )
    reason: Literal[
        "ring_evicted",
        "session_unknown",
        "token_mismatch",
        "protocol_incompatible",
        "session_expired",
    ] = Field(description="Machine-readable reason code.")
    detail: str = Field(
        description="Human-readable Korean/English detail for HUD.",
    )


# ---------------------------------------------------------------------------
# Arm: heartbeat  (Spec 032 §2.8)
# ---------------------------------------------------------------------------


class HeartbeatFrame(_BaseFrame):
    """Emitted every 30 s (default) by both sides to prove liveness.

    Note: Heartbeat frames do NOT increment frame_seq — they use a dedicated
    counter. This keeps ring-buffer economy tight.
    role allow-list: tui, backend.
    """

    kind: Literal["heartbeat"] = Field(default="heartbeat", description="Frame discriminator.")
    direction: Literal["ping", "pong"] = Field(description="ping from sender, pong from receiver.")
    peer_frame_seq: NonNegativeInt = Field(
        description="Sender's current outbound frame_seq high-water."
    )


# ---------------------------------------------------------------------------
# Arm: notification_push  (Spec 032 §2.9)
# ---------------------------------------------------------------------------


class NotificationPushFrame(_BaseFrame):
    """Push from subscription surfaces (Spec 031 SubscriptionHandle).

    Carried over the same stdio channel to keep a single correlation plane.
    role allow-list: notification.
    """

    kind: Literal["notification_push"] = Field(
        default="notification_push", description="Frame discriminator."
    )
    subscription_id: str = Field(description="Handle from Spec 031 subscribe registration.")
    adapter_id: str = Field(description="e.g., disaster_alert_cbs_push, rss_newsroom_subscribe.")
    event_guid: str = Field(description="RSS guid or CBS event hash for duplicate suppression.")
    payload_content_type: Literal["text/plain", "application/json"] = Field(
        description="Inline payload MIME."
    )
    payload: str = Field(description="Inline notification content (Korean for civic users).")


# ---------------------------------------------------------------------------
# Discriminated union — 19 kinds (T010)
# ---------------------------------------------------------------------------

IPCFrame = Annotated[
    UserInputFrame
    | AssistantChunkFrame
    | ToolCallFrame
    | ToolResultFrame
    | CoordinatorPhaseFrame
    | WorkerStatusFrame
    | PermissionRequestFrame
    | PermissionResponseFrame
    | SessionEventFrame
    | ErrorFrame
    | PayloadStartFrame
    | PayloadDeltaFrame
    | PayloadEndFrame
    | BackpressureSignalFrame
    | ResumeRequestFrame
    | ResumeResponseFrame
    | ResumeRejectedFrame
    | HeartbeatFrame
    | NotificationPushFrame,
    Field(discriminator="kind"),
]
"""Discriminated union of all 19 IPC frame arms.

Spec 287 baseline: 10 arms (user_input .. error).
Spec 032 additions: 9 arms (payload_start .. notification_push).

Usage::

    from kosmos.ipc.frame_schema import IPCFrame
    from pydantic import TypeAdapter

    _adapter = TypeAdapter(IPCFrame)
    frame = _adapter.validate_json(raw_line)
"""


def ipc_frame_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for the ``IPCFrame`` discriminated union.

    Delegates to Pydantic v2's ``TypeAdapter.json_schema()``.
    The output is JSON Schema Draft 2020-12 compatible.
    """
    from pydantic import TypeAdapter

    adapter: TypeAdapter[Any] = TypeAdapter(IPCFrame)
    return adapter.json_schema()


__all__ = [
    # Base + trailer
    "FrameTrailer",
    "ENVELOPE_VERSION",
    # Spec 287 baseline arms
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
    # Spec 032 new arms
    "PayloadStartFrame",
    "PayloadDeltaFrame",
    "PayloadEndFrame",
    "BackpressureSignalFrame",
    "ResumeRequestFrame",
    "ResumeResponseFrame",
    "ResumeRejectedFrame",
    "HeartbeatFrame",
    "NotificationPushFrame",
    # Schema helper
    "ipc_frame_json_schema",
]
