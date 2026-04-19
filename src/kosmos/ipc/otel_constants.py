# SPDX-License-Identifier: Apache-2.0
"""OTEL attribute-key constants for the KOSMOS IPC layer (Spec 032 T002).

All constants follow the ``kosmos.ipc.*`` namespace.  They are used by the
envelope emit path (``envelope.py``) to promote frame fields to OpenTelemetry
span attributes so that correlation_id, transaction_id, and backpressure state
are visible in OTEL Collector / Langfuse trace views.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Core correlation / identity attributes
# ---------------------------------------------------------------------------

#: The UUIDv7 correlation chain identifier threaded through a full request turn.
KOSMOS_IPC_CORRELATION_ID = "kosmos.ipc.correlation_id"

#: Per-action idempotency key (UUIDv7).  Populated only for irreversible-tool
#: frames; ``None`` for streaming chunks.
KOSMOS_IPC_TRANSACTION_ID = "kosmos.ipc.transaction_id"

# ---------------------------------------------------------------------------
# Transaction cache state
# ---------------------------------------------------------------------------

#: Transaction LRU cache state.  Values: ``"miss"``, ``"hit"``, ``"stored"``.
KOSMOS_IPC_TX_CACHE_STATE = "kosmos.ipc.tx.cache_state"

# ---------------------------------------------------------------------------
# Backpressure attributes
# ---------------------------------------------------------------------------

#: Backpressure signal kind.  Values: ``"pause"``, ``"resume"``, ``"throttle"``.
KOSMOS_IPC_BACKPRESSURE_KIND = "kosmos.ipc.backpressure.signal"

#: Severity of the backpressure event.  Values: ``"info"``, ``"warn"``,
#: ``"critical"``.
KOSMOS_IPC_BACKPRESSURE_SEVERITY = "kosmos.ipc.backpressure.severity"

#: Source component that raised the backpressure signal.  Values:
#: ``"tui_reader"``, ``"backend_writer"``, ``"upstream_429"``.
KOSMOS_IPC_BACKPRESSURE_SOURCE = "kosmos.ipc.backpressure.source"

#: Current outbound queue depth at the moment the signal was emitted.
KOSMOS_IPC_BACKPRESSURE_QUEUE_DEPTH = "kosmos.ipc.backpressure.queue_depth"

# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

#: SHA-256 hex digest of the committed ``frame.schema.json`` file.  Emitted
#: as an OTEL resource attribute at backend startup (FR-037).
KOSMOS_IPC_SCHEMA_HASH = "kosmos.ipc.schema.hash"

# ---------------------------------------------------------------------------
# Replay / resume tracking
# ---------------------------------------------------------------------------

#: Boolean (stored as string ``"true"``/``"false"``) — indicates that a span
#: belongs to a replayed frame (i.e., the frame was retransmitted after a
#: resume handshake).  Present only when ``True``.
KOSMOS_IPC_REPLAYED = "kosmos.ipc.replayed"

__all__ = [
    "KOSMOS_IPC_CORRELATION_ID",
    "KOSMOS_IPC_TRANSACTION_ID",
    "KOSMOS_IPC_TX_CACHE_STATE",
    "KOSMOS_IPC_BACKPRESSURE_KIND",
    "KOSMOS_IPC_BACKPRESSURE_SEVERITY",
    "KOSMOS_IPC_BACKPRESSURE_SOURCE",
    "KOSMOS_IPC_BACKPRESSURE_QUEUE_DEPTH",
    "KOSMOS_IPC_SCHEMA_HASH",
    "KOSMOS_IPC_REPLAYED",
]
