# SPDX-License-Identifier: Apache-2.0
"""OpenTelemetry GenAI semantic convention constants for KOSMOS.

Re-exports attribute-name constants from the official
``opentelemetry-semantic-conventions`` package where available (incubating
GenAI module, v1.40 Development stability).  Any constant not yet shipped by
the SDK package is defined here as a string literal, matching the OTel GenAI
semconv v1.40 specification.

Deprecated names (e.g. ``gen_ai.system`` renamed to ``gen_ai.provider.name``
in v1.37) are intentionally absent.  Use the constants in this module as the
single source of truth across all KOSMOS instrumentation code.

Usage::

    from kosmos.observability.semconv import (
        GEN_AI_OPERATION_NAME,
        GEN_AI_PROVIDER_NAME,
        ERROR_TYPE,
    )
"""

from __future__ import annotations

from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_AGENT_NAME,
    GEN_AI_CONVERSATION_ID,
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_FINISH_REASONS,
    GEN_AI_RESPONSE_MODEL,
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_NAME,
    GEN_AI_TOOL_TYPE,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)
from opentelemetry.semconv.attributes.error_attributes import ERROR_TYPE

__all__ = [
    "ERROR_TYPE",
    "GEN_AI_AGENT_NAME",
    "GEN_AI_CONVERSATION_ID",
    "GEN_AI_OPERATION_NAME",
    "GEN_AI_PROVIDER_NAME",
    "GEN_AI_REQUEST_MODEL",
    "GEN_AI_RESPONSE_FINISH_REASONS",
    "GEN_AI_RESPONSE_MODEL",
    "GEN_AI_TOOL_CALL_ID",
    "GEN_AI_TOOL_NAME",
    "GEN_AI_TOOL_TYPE",
    "GEN_AI_USAGE_INPUT_TOKENS",
    "GEN_AI_USAGE_OUTPUT_TOKENS",
    # --- Agent Swarm (Epic #13) ---
    "KOSMOS_AGENT_COORDINATOR_PHASE",
    "KOSMOS_AGENT_ROLE",
    "KOSMOS_AGENT_SESSION_ID",
    "KOSMOS_AGENT_MAILBOX_MSG_TYPE",
    "KOSMOS_AGENT_MAILBOX_CORRELATION_ID",
    "KOSMOS_AGENT_MAILBOX_SENDER",
    "KOSMOS_AGENT_MAILBOX_RECIPIENT",
]

# ---------------------------------------------------------------------------
# Agent Swarm attribute-name constants (Epic #13 — FR-031)
# Submitted to Epic #501's boundary table before any collector deployment.
# All names are in the kosmos.agent.* namespace per spec/027 data-model.md §8.
# ---------------------------------------------------------------------------

KOSMOS_AGENT_COORDINATOR_PHASE: str = "kosmos.agent.coordinator.phase"
"""Coordinator phase name attribute for gen_ai.agent.coordinator.phase spans.

Value: Literal["research", "synthesis", "implementation", "verification"]
FR-028.
"""

KOSMOS_AGENT_ROLE: str = "kosmos.agent.role"
"""Worker specialist role attribute for gen_ai.agent.worker.iteration spans.

Value: the AgentContext.specialist_role string (e.g. 'transport', 'civil_affairs').
FR-029.
"""

KOSMOS_AGENT_SESSION_ID: str = "kosmos.agent.session_id"
"""Session UUID attribute for gen_ai.agent.worker.iteration spans.

Value: str(AgentContext.session_id). Not PII — this is a random UUID.
FR-029.
"""

KOSMOS_AGENT_MAILBOX_MSG_TYPE: str = "kosmos.agent.mailbox.msg_type"
"""Message type attribute for gen_ai.agent.mailbox.message spans.

Value: one of task/result/error/permission_request/permission_response/cancel.
FR-030.
"""

KOSMOS_AGENT_MAILBOX_CORRELATION_ID: str = "kosmos.agent.mailbox.correlation_id"
"""Correlation ID attribute for gen_ai.agent.mailbox.message spans.

Value: str(AgentMessage.correlation_id) or empty string.
FR-030.
"""

KOSMOS_AGENT_MAILBOX_SENDER: str = "kosmos.agent.mailbox.sender"
"""Sender ID attribute for gen_ai.agent.mailbox.message spans.

Value: AgentMessage.sender. Message body MUST NOT be included (PIPA).
FR-030.
"""

KOSMOS_AGENT_MAILBOX_RECIPIENT: str = "kosmos.agent.mailbox.recipient"
"""Recipient ID attribute for gen_ai.agent.mailbox.message spans.

Value: AgentMessage.recipient. Message body MUST NOT be included (PIPA).
FR-030.
"""
