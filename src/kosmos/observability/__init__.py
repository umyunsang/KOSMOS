# SPDX-License-Identifier: Apache-2.0
"""KOSMOS observability package.

Provides in-process metrics collection and structured event logging for
the tool execution and error-recovery pipelines.

Public API::

    from kosmos.observability import MetricsCollector, ObservabilityEvent

The ``MetricsCollector`` is intentionally lightweight — no external agents,
no network calls.  It collects counters, gauges, and histograms purely in
memory and exposes a ``snapshot()`` for periodic export or health-check
endpoints.
"""

from kosmos.observability.events import ObservabilityEvent
from kosmos.observability.metrics import MetricsCollector

__all__ = [
    "MetricsCollector",
    "ObservabilityEvent",
]
