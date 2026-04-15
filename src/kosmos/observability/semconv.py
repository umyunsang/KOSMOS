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
]
