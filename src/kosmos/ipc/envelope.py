# SPDX-License-Identifier: Apache-2.0
"""NDJSON emit/parse helpers for the KOSMOS IPC frame protocol (Spec 032 T012).

Responsibilities:
- ``emit_ndjson(frame)``: serialise an IPCFrame to a single NDJSON line ending
  with ``\\n``.  Payload-internal newlines are JSON-escaped.
- ``parse_ndjson_line(line)``: parse one NDJSON line into a validated IPCFrame.
  Fail-closed: malformed JSON or schema violations return None + log error.
- ``escape_newlines_in_payload(obj)``: recursively replace bare ``\\n`` in
  string values with ``\\\\n`` so NDJSON line integrity is preserved (FR-009).

All outbound frames use stdout (FR-036).  This module never writes to stderr.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from kosmos.ipc.frame_schema import IPCFrame

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic TypeAdapter (module-level singleton for performance)
# ---------------------------------------------------------------------------

_IPC_ADAPTER: TypeAdapter[IPCFrame] = TypeAdapter(IPCFrame)

# ---------------------------------------------------------------------------
# Newline escape
# ---------------------------------------------------------------------------


def escape_newlines_in_payload(obj: Any) -> Any:
    """Recursively replace bare '\\n' with '\\\\n' in all string leaf values.

    This ensures that payload text containing newlines does not break NDJSON
    line integrity (FR-009).  The resulting object is still valid JSON when
    serialised — ``\\\\n`` decodes back to ``\\n`` on the receiver.

    Args:
        obj: Any JSON-serialisable Python value.

    Returns:
        A new value with all string leaves having bare newlines escaped.
    """
    if isinstance(obj, str):
        return obj.replace("\n", "\\n")
    if isinstance(obj, dict):
        return {k: escape_newlines_in_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [escape_newlines_in_payload(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------


def emit_ndjson(frame: IPCFrame) -> str:
    """Serialise *frame* to a single NDJSON line terminated by ``\\n``.

    Payload string values that contain bare newlines are escaped before
    serialisation so that each frame occupies exactly one line (FR-009).

    Args:
        frame: A validated IPCFrame instance.

    Returns:
        A JSON string ending with a single ``\\n``.
    """
    raw_dict = frame.model_dump(mode="json")
    safe_dict = escape_newlines_in_payload(raw_dict)
    return json.dumps(safe_dict, ensure_ascii=False) + "\n"


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
                    parsed.get("kind", "<unknown>")
                    if isinstance(parsed, dict)
                    else "<non-dict>"
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


__all__ = [
    "emit_ndjson",
    "parse_ndjson_line",
    "escape_newlines_in_payload",
    "compute_schema_file_hash",
]
