# SPDX-License-Identifier: Apache-2.0
"""OTEL attribute-key constants for the KOSAX IPC layer (Spec 032 T002).

All constants follow the ``kosax.ipc.*`` namespace.  They are used by the
envelope emit path (``envelope.py``) to promote frame fields to OpenTelemetry
span attributes so that correlation_id, transaction_id, and backpressure state
are visible in OTEL Collector / Langfuse trace views.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Core correlation / identity attributes
# ---------------------------------------------------------------------------

#: The UUIDv7 correlation chain identifier threaded through a full request turn.
KOSAX_IPC_CORRELATION_ID = "kosax.ipc.correlation_id"

#: Per-action idempotency key (UUIDv7).  Populated only for irreversible-tool
#: frames; ``None`` for streaming chunks.
KOSAX_IPC_TRANSACTION_ID = "kosax.ipc.transaction_id"

# ---------------------------------------------------------------------------
# Transaction cache state
# ---------------------------------------------------------------------------

#: Transaction LRU cache state.  Values: ``"miss"``, ``"hit"``, ``"stored"``.
KOSAX_IPC_TX_CACHE_STATE = "kosax.ipc.tx.cache_state"

# ---------------------------------------------------------------------------
# Backpressure attributes
# ---------------------------------------------------------------------------

#: Backpressure signal kind.  Values: ``"pause"``, ``"resume"``, ``"throttle"``.
KOSAX_IPC_BACKPRESSURE_KIND = "kosax.ipc.backpressure.signal"

#: Severity of the backpressure event.  Values: ``"info"``, ``"warn"``,
#: ``"critical"``.
KOSAX_IPC_BACKPRESSURE_SEVERITY = "kosax.ipc.backpressure.severity"

#: Source component that raised the backpressure signal.  Values:
#: ``"tui_reader"``, ``"backend_writer"``, ``"upstream_429"``.
KOSAX_IPC_BACKPRESSURE_SOURCE = "kosax.ipc.backpressure.source"

#: Current outbound queue depth at the moment the signal was emitted.
KOSAX_IPC_BACKPRESSURE_QUEUE_DEPTH = "kosax.ipc.backpressure.queue_depth"

# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

#: SHA-256 hex digest of the committed ``frame.schema.json`` file.  Emitted
#: as an OTEL resource attribute at backend startup (FR-037).
KOSAX_IPC_SCHEMA_HASH = "kosax.ipc.schema.hash"

# ---------------------------------------------------------------------------
# Replay / resume tracking
# ---------------------------------------------------------------------------

#: Boolean (stored as string ``"true"``/``"false"``) — indicates that a span
#: belongs to a replayed frame (i.e., the frame was retransmitted after a
#: resume handshake).  Present only when ``True``.
KOSAX_IPC_REPLAYED = "kosax.ipc.replayed"

__all__ = [
    "KOSAX_IPC_CORRELATION_ID",
    "KOSAX_IPC_TRANSACTION_ID",
    "KOSAX_IPC_TX_CACHE_STATE",
    "KOSAX_IPC_BACKPRESSURE_KIND",
    "KOSAX_IPC_BACKPRESSURE_SEVERITY",
    "KOSAX_IPC_BACKPRESSURE_SOURCE",
    "KOSAX_IPC_BACKPRESSURE_QUEUE_DEPTH",
    "KOSAX_IPC_SCHEMA_HASH",
    "KOSAX_IPC_REPLAYED",
]
