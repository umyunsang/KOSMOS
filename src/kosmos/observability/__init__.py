# SPDX-License-Identifier: Apache-2.0
"""KOSMOS observability package.

Provides in-process metrics collection, structured event logging, and
OpenTelemetry tracing setup for the tool execution and error-recovery
pipelines.

Public API (legacy — FR-012/FR-013 backwards compatibility)::

    from kosmos.observability import MetricsCollector, ObservabilityEvent

Public API (OTel tracing — spec 021)::

    from kosmos.observability import setup_tracing, TracingSettings, filter_metadata

The ``MetricsCollector`` is intentionally lightweight — no external agents,
no network calls.  It collects counters, gauges, and histograms purely in
memory and exposes a ``snapshot()`` for periodic export or health-check
endpoints.
"""

from kosmos.observability.event_logger import ObservabilityEventLogger
from kosmos.observability.events import ObservabilityEvent
from kosmos.observability.metrics import MetricsCollector
from kosmos.observability.otel_bridge import filter_metadata
from kosmos.observability.semconv import (
    ERROR_TYPE,
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
from kosmos.observability.tracing import TracingSettings, setup_tracing

__all__ = [
    # Legacy exports — do not remove (FR-012, FR-013)
    "MetricsCollector",
    "ObservabilityEvent",
    "ObservabilityEventLogger",
    # OTel tracing — spec 021
    "TracingSettings",
    "filter_metadata",
    "setup_tracing",
    # GenAI semconv constants — spec 021
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
