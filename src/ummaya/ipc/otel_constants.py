# SPDX-License-Identifier: Apache-2.0
"""OTEL attribute-key constants for the UMMAYA IPC layer (Spec 032 T002).

All constants follow the ``ummaya.ipc.*`` namespace.  They are used by the
envelope emit path (``envelope.py``) to promote frame fields to OpenTelemetry
span attributes so that correlation_id, transaction_id, and backpressure state
are visible in OTEL Collector / Langfuse trace views.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Core correlation / identity attributes
# ---------------------------------------------------------------------------

#: The UUIDv7 correlation chain identifier threaded through a full request turn.
UMMAYA_IPC_CORRELATION_ID = "ummaya.ipc.correlation_id"

#: Per-action idempotency key (UUIDv7).  Populated only for irreversible-tool
#: frames; ``None`` for streaming chunks.
UMMAYA_IPC_TRANSACTION_ID = "ummaya.ipc.transaction_id"

# ---------------------------------------------------------------------------
# Transaction cache state
# ---------------------------------------------------------------------------

#: Transaction LRU cache state.  Values: ``"miss"``, ``"hit"``, ``"stored"``.
UMMAYA_IPC_TX_CACHE_STATE = "ummaya.ipc.tx.cache_state"

# ---------------------------------------------------------------------------
# Backpressure attributes
# ---------------------------------------------------------------------------

#: Backpressure signal kind.  Values: ``"pause"``, ``"resume"``, ``"throttle"``.
UMMAYA_IPC_BACKPRESSURE_KIND = "ummaya.ipc.backpressure.signal"

#: Severity of the backpressure event.  Values: ``"info"``, ``"warn"``,
#: ``"critical"``.
UMMAYA_IPC_BACKPRESSURE_SEVERITY = "ummaya.ipc.backpressure.severity"

#: Source component that raised the backpressure signal.  Values:
#: ``"tui_reader"``, ``"backend_writer"``, ``"upstream_429"``.
UMMAYA_IPC_BACKPRESSURE_SOURCE = "ummaya.ipc.backpressure.source"

#: Current outbound queue depth at the moment the signal was emitted.
UMMAYA_IPC_BACKPRESSURE_QUEUE_DEPTH = "ummaya.ipc.backpressure.queue_depth"

# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

#: SHA-256 hex digest of the committed ``frame.schema.json`` file.  Emitted
#: as an OTEL resource attribute at backend startup (FR-037).
UMMAYA_IPC_SCHEMA_HASH = "ummaya.ipc.schema.hash"

# ---------------------------------------------------------------------------
# Replay / resume tracking
# ---------------------------------------------------------------------------

#: Boolean (stored as string ``"true"``/``"false"``) — indicates that a span
#: belongs to a replayed frame (i.e., the frame was retransmitted after a
#: resume handshake).  Present only when ``True``.
UMMAYA_IPC_REPLAYED = "ummaya.ipc.replayed"

__all__ = [
    "UMMAYA_IPC_CORRELATION_ID",
    "UMMAYA_IPC_TRANSACTION_ID",
    "UMMAYA_IPC_TX_CACHE_STATE",
    "UMMAYA_IPC_BACKPRESSURE_KIND",
    "UMMAYA_IPC_BACKPRESSURE_SEVERITY",
    "UMMAYA_IPC_BACKPRESSURE_SOURCE",
    "UMMAYA_IPC_BACKPRESSURE_QUEUE_DEPTH",
    "UMMAYA_IPC_SCHEMA_HASH",
    "UMMAYA_IPC_REPLAYED",
]
