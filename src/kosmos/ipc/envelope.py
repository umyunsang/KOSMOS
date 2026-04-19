# SPDX-License-Identifier: Apache-2.0
"""NDJSON emit/parse helpers for the KOSMOS IPC frame protocol (Spec 032 T012).

Responsibilities:
- ``emit_ndjson(frame)``: serialise an IPCFrame to a single NDJSON line ending
  with ``\\n``.  ``json.dumps`` natively escapes newlines in string values to
  the two-character JSON sequence ``\\n`` (FR-009), so no pre-processing is
  required — a pre-escape step would double-encode and corrupt multi-line
  payloads on the receiver.
- ``parse_ndjson_line(line)``: parse one NDJSON line into a validated IPCFrame.
  Fail-closed: malformed JSON or schema violations return None + log error.
- ``attach_envelope_span_attributes(frame, *, tx_cache_state)``: promote envelope
  ``correlation_id`` / ``transaction_id`` / ``tx.cache_state`` to the current OTEL
  span (Spec 032 T048 / FR-053).

All outbound frames use stdout (FR-036).  This module never writes to stderr.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

from opentelemetry import trace
from pydantic import TypeAdapter, ValidationError

from kosmos.ipc.frame_schema import IPCFrame
from kosmos.ipc.otel_constants import (
    KOSMOS_IPC_CORRELATION_ID,
    KOSMOS_IPC_SCHEMA_HASH,
    KOSMOS_IPC_TRANSACTION_ID,
    KOSMOS_IPC_TX_CACHE_STATE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic TypeAdapter (module-level singleton for performance)
# ---------------------------------------------------------------------------

_IPC_ADAPTER: TypeAdapter[IPCFrame] = TypeAdapter(IPCFrame)

# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def emit_ndjson(frame: IPCFrame) -> str:
    """Serialise *frame* to a single NDJSON line terminated by ``\\n``.

    ``json.dumps`` escapes bare newlines in string values to the two-character
    JSON sequence ``\\n`` automatically, so the emitted line is guaranteed to
    contain exactly one terminal ``\\n`` (FR-009) without any pre-processing.
    Pre-escaping would cause the receiver's ``json.loads`` to yield a literal
    backslash-n string in place of the original newline.

    Args:
        frame: A validated IPCFrame instance.

    Returns:
        A JSON string ending with a single ``\\n``.
    """
    return json.dumps(frame.model_dump(mode="json"), ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Parse (fail-closed)
# ---------------------------------------------------------------------------


def parse_ndjson_line(line: str) -> IPCFrame | None:
    """Parse one NDJSON line into a validated IPCFrame.

    Fail-closed (FR-035): if the line is malformed JSON or fails Pydantic
    schema validation, the frame is DROPPED (returns None) and an OTEL-
    compatible error is logged.  The session is never killed.

    Args:
        line: A single JSON string (with or without trailing newline).

    Returns:
        A validated IPCFrame, or None if parsing failed.
    """
    stripped = line.rstrip("\n").strip()
    if not stripped:
        return None

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        logger.error(
            "ipc.parse.json_error",
            extra={
                "error": str(exc),
                "raw_line_preview": stripped[:200],
            },
        )
        return None

    try:
        return _IPC_ADAPTER.validate_python(parsed)
    except ValidationError as exc:
        logger.error(
            "ipc.parse.schema_error",
            extra={
                "error": str(exc),
                "kind": (
                    parsed.get("kind", "<unknown>") if isinstance(parsed, dict) else "<non-dict>"
                ),
            },
        )
        return None


# ---------------------------------------------------------------------------
# Schema hash (FR-037)
# ---------------------------------------------------------------------------


def compute_schema_file_hash(schema_path: Path) -> str:
    """Return the SHA-256 hex digest of the committed JSON Schema file.

    Used at backend startup to emit ``kosmos.ipc.schema.hash`` as an OTEL
    resource attribute so deployment version consistency can be audited.

    Args:
        schema_path: Absolute path to ``tui/src/ipc/schema/frame.schema.json``.

    Returns:
        64-character hex string.
    """
    data = schema_path.read_bytes()
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# OTEL span attribute promotion (Spec 032 T048 / FR-053)
# ---------------------------------------------------------------------------


def attach_envelope_span_attributes(
    frame: IPCFrame,
    *,
    tx_cache_state: Literal["miss", "hit", "stored"] | None = None,
) -> None:
    """Promote envelope identifiers to the currently active OTEL span.

    Sets ``kosmos.ipc.correlation_id`` (always) and, when populated,
    ``kosmos.ipc.transaction_id`` and ``kosmos.ipc.tx.cache_state``.  The
    caller is responsible for opening the span context.  When no span is
    recording (no-op tracer), this function is a silent no-op.

    Args:
        frame: Any validated ``IPCFrame`` instance.
        tx_cache_state: ``"miss"`` / ``"hit"`` / ``"stored"`` from the
            :class:`~kosmos.ipc.transaction_lru.TransactionLRU` path when an
            irreversible-tool frame is being emitted; ``None`` otherwise.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return
    span.set_attribute(KOSMOS_IPC_CORRELATION_ID, frame.correlation_id)
    tx_id = getattr(frame, "transaction_id", None)
    if tx_id is not None:
        span.set_attribute(KOSMOS_IPC_TRANSACTION_ID, tx_id)
    if tx_cache_state is not None:
        span.set_attribute(KOSMOS_IPC_TX_CACHE_STATE, tx_cache_state)


# ---------------------------------------------------------------------------
# Schema-hash OTEL resource attribute emission (Spec 032 T050 / FR-037)
# ---------------------------------------------------------------------------


_DEFAULT_SCHEMA_REL_PATH = Path("tui/src/ipc/schema/frame.schema.json")


def _resolve_schema_path(schema_path: Path | None) -> Path | None:
    """Walk up from this file until the committed schema file is found."""
    if schema_path is not None:
        return schema_path if schema_path.is_file() else None
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / _DEFAULT_SCHEMA_REL_PATH
        if candidate.is_file():
            return candidate
    return None


def emit_schema_hash_resource_attribute(schema_path: Path | None = None) -> str | None:
    """Emit ``kosmos.ipc.schema.hash`` on the current OTEL span at backend startup.

    The span attribute mirrors the digest onto the current root span so that
    OTEL Collector / Langfuse can surface deployment version consistency even
    when resource attributes are not customisable at runtime (FR-037).

    Args:
        schema_path: Override for the committed schema file location.  When
            ``None`` (default), the function walks upward from this module
            looking for ``tui/src/ipc/schema/frame.schema.json``.

    Returns:
        The hex digest when the schema file was located, else ``None``.
    """
    resolved = _resolve_schema_path(schema_path)
    if resolved is None:
        logger.warning(
            "ipc.schema_hash.resolve_failed",
            extra={"searched": str(_DEFAULT_SCHEMA_REL_PATH)},
        )
        return None

    digest = compute_schema_file_hash(resolved)
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(KOSMOS_IPC_SCHEMA_HASH, digest)
    logger.info(
        "ipc.schema_hash.emitted",
        extra={"schema_hash": digest, "schema_path": str(resolved)},
    )
    return digest


__all__ = [
    "emit_ndjson",
    "parse_ndjson_line",
    "compute_schema_file_hash",
    "attach_envelope_span_attributes",
    "emit_schema_hash_resource_attribute",
]
