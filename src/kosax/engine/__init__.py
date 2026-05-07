# SPDX-License-Identifier: Apache-2.0
"""KOSAX Query Engine — async generator tool loop (Layer 1).

Public API:
    QueryEngine         — per-session orchestrator (the only entry point)
    QueryEngineConfig   — immutable session configuration
    QueryEvent          — discriminated union of progress events
    StopReason          — enum of engine stop reasons
    QueryState          — mutable per-session state
    QueryContext        — frozen per-turn context
    SessionBudget       — frozen budget snapshot
"""

from kosax.engine.config import QueryEngineConfig
from kosax.engine.engine import QueryEngine
from kosax.engine.events import QueryEvent, StopReason
from kosax.engine.models import QueryContext, QueryState, SessionBudget

__all__ = [
    "QueryEngine",
    "QueryEngineConfig",
    "QueryContext",
    "QueryEvent",
    "QueryState",
    "SessionBudget",
    "StopReason",
]
