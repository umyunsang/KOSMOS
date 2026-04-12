# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 data models for the KOSMOS Permission Pipeline (Layer 3).

All models are frozen (immutable). No ``Any`` types. The pipeline is stateless;
sessions are owned by the query engine and passed in via ``SessionContext``.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccessTier(StrEnum):
    """Permission tier mapped from ``GovAPITool.auth_type``.

    Determines the minimum credential requirements at step 1.
    """

    public = "public"
    """No auth required; allow unconditionally at step 1."""

    api_key = "api_key"
    """``KOSMOS_DATA_GO_KR_API_KEY`` must be set and non-empty."""

    authenticated = "authenticated"
    """Citizen identity verification required; denied in v1."""

    restricted = "restricted"
    """Special approval gate; denied in v1."""


class PermissionDecision(StrEnum):
    """Verdict returned by each pipeline step."""

    allow = "allow"
    """Proceed to next step or execute."""

    deny = "deny"
    """Halt; return error result to query engine."""

    escalate = "escalate"
    """Treated as ``deny`` in v1; reserved for v2 human-in-the-loop."""


class SessionContext(BaseModel):
    """Session state passed in from the query engine.

    The pipeline does not create or mutate sessions.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    """Unique session identifier for audit trail."""

    citizen_id: str | None = None
    """Citizen identity; ``None`` in v1 (no auth yet)."""

    auth_level: int = 0
    """Authentication level: 0=anonymous, 1=basic, 2=verified."""

    consented_providers: list[str] = Field(default_factory=list)
    """Providers for which the citizen has accepted ToS."""


class PermissionCheckRequest(BaseModel):
    """Single input passed to every step function.

    Constructed once at ``PermissionPipeline.run()`` entry and never mutated.
    ``arguments_json`` is never parsed by the pipeline itself and is never
    written to logs, error messages, or ``AuditLogEntry``.
    """

    model_config = ConfigDict(frozen=True)

    tool_id: str
    """Stable tool identifier (e.g. ``koroad_accident_search``)."""

    access_tier: AccessTier
    """Mapped from ``GovAPITool.auth_type`` at pipeline entry."""

    arguments_json: str
    """Raw JSON string of tool arguments (not parsed by pipeline)."""

    session_context: SessionContext
    """Session state from query engine."""

    is_personal_data: bool
    """From ``GovAPITool.is_personal_data``; drives bypass-immune checks."""

    is_bypass_mode: bool = False
    """If ``True``, bypass-immune rules still apply; warning is emitted."""


class PermissionStepResult(BaseModel):
    """Result returned by every step function (active or stub)."""

    model_config = ConfigDict(frozen=True)

    decision: PermissionDecision
    """The step's verdict."""

    step: int
    """Step number (1-7) for audit trail clarity."""

    reason: str | None = None
    """Machine-readable deny reason; ``None`` on allow."""


class AuditLogEntry(BaseModel):
    """Structured audit log entry written after every invocation.

    Intentionally absent: ``arguments_json``, ``citizen_id``, and any field
    that could contain PII, preventing personal data from appearing in log
    aggregators (ELK, CloudWatch, Loki).
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    """UTC timestamp at log time."""

    tool_id: str
    """Tool identifier."""

    access_tier: AccessTier
    """Tier at time of call."""

    decision: PermissionDecision
    """Final pipeline decision."""

    step_that_decided: int
    """Which step produced the final decision."""

    outcome: Literal["success", "failure", "denied"]
    """Execution outcome."""

    error_type: str | None = None
    """Error type string from ``ToolResult`` on failure."""

    deny_reason: str | None = None
    """Machine-readable deny reason on denied outcome."""

    session_id: str
    """From ``session_context.session_id``."""
