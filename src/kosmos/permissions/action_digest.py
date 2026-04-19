# SPDX-License-Identifier: Apache-2.0
"""Action digest computation — Spec 033 T031 (WS4).

Provides ``compute_action_digest()`` which produces a per-call SHA-256 hex
digest over a canonical representation of the tool call.

Invariants:
- K6: Two identical bypass calls MUST get distinct digests.  Distinctness is
      guaranteed by the ``nonce`` parameter — a freshly generated UUID is passed
      for every call, so the canonical payload differs even when tool_id and
      arguments are identical.
- FR-B04: Killswitch-triggered calls are recorded with a ``scope="one-shot"``
          ledger record that carries this digest.

The canonical payload is built as a JSON object:
    ``{"tool_id": <str>, "arguments": <dict>, "nonce": <str(uuid)>}``
serialized via the RFC 8785 JCS encoder from ``canonical_json.py`` to ensure
deterministic byte-level representation suitable for hashing (Invariant L5).

Note on uuid7: The spec references ``uuid.uuid7()`` (stdlib 3.13+).  This
module provides ``generate_nonce()`` as a compatibility shim that uses
``uuid.uuid7()`` when available (Python 3.13+) and falls back to ``uuid.uuid4()``
on Python 3.12.  Both are cryptographically unique; uuid7 additionally
provides time-ordering which aids log correlation.

Reference:
    specs/033-permission-v2-spectrum/spec.md §US3, FR-B04
    specs/033-permission-v2-spectrum/data-model.md § 2.1 K6
    specs/033-permission-v2-spectrum/tasks.md T031
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Mapping
from typing import Any

from kosmos.permissions.canonical_json import canonicalize

__all__ = ["compute_action_digest", "generate_nonce"]

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UUID nonce generator with Python 3.12 / 3.13 compatibility
# ---------------------------------------------------------------------------


def generate_nonce() -> uuid.UUID:
    """Generate a unique nonce UUID for action digest computation.

    Uses ``uuid.uuid7()`` (time-ordered, Python 3.13+) when available,
    falling back to ``uuid.uuid4()`` (random, Python 3.12) for compatibility.
    Both variants guarantee uniqueness per call and satisfy Invariant K6.

    Returns:
        A freshly generated ``uuid.UUID`` instance.

    Note:
        Callers MUST call this function once per tool invocation — never reuse
        a nonce.  Reusing a nonce with identical arguments would produce an
        identical digest, violating K6.
    """
    uuid7_fn = getattr(uuid, "uuid7", None)
    if uuid7_fn is not None:
        result: uuid.UUID = uuid7_fn()
        return result
    return uuid.uuid4()


def compute_action_digest(
    tool_id: str,
    arguments: Mapping[str, Any],
    nonce: uuid.UUID,
) -> str:
    """Compute a per-call SHA-256 hex digest for action audit linkage.

    Produces a 64-character lowercase hexadecimal SHA-256 digest over the
    RFC 8785 JCS canonical encoding of:
        ``{"tool_id": tool_id, "arguments": arguments, "nonce": str(nonce)}``

    Invariant K6 — Distinct digests per call:
        Because ``nonce`` differs on every call (callers MUST pass a freshly
        generated ``uuid.uuid7()`` per call), two invocations with identical
        ``tool_id`` and ``arguments`` will produce different digests.  This
        ensures that the consent ledger records each bypass call as a distinct
        action (no deduplication across calls).

    Args:
        tool_id: The canonical adapter identifier (e.g. ``minwon_submit``).
        arguments: The adapter call arguments.  Values must be JSON-compatible
            (str, int, float, bool, None, dict, list).  ``Mapping`` is accepted
            to support frozen models.
        nonce: A ``uuid.UUID`` instance.  Callers SHOULD use ``uuid.uuid7()``
            (time-ordered monotonic UUID, stdlib 3.12+) to ensure each call
            gets a unique nonce.  The nonce is converted to its canonical
            string representation (``str(nonce)``, lowercase hex with dashes).

    Returns:
        A 64-character lowercase hexadecimal SHA-256 string.

    Raises:
        TypeError: If ``arguments`` contains non-JSON-serializable values.
        ValueError: If ``tool_id`` is empty.

    Example::

        from kosmos.permissions.action_digest import compute_action_digest, generate_nonce

        nonce1 = generate_nonce()
        nonce2 = generate_nonce()

        d1 = compute_action_digest("minwon_submit", {"form": "A"}, nonce1)
        d2 = compute_action_digest("minwon_submit", {"form": "A"}, nonce2)
        assert d1 != d2          # K6: distinct nonces → distinct digests
        assert len(d1) == 64     # SHA-256 hex = 64 chars
    """
    if not tool_id:
        raise ValueError("tool_id must be a non-empty string for action digest computation.")

    # Build the canonical payload dict.
    # Key ordering is handled by the JCS encoder (RFC 8785 UTF-16 sort),
    # so the insertion order here does not affect the output.
    payload: dict[str, Any] = {
        "tool_id": tool_id,
        "arguments": dict(arguments),  # Convert Mapping to plain dict for JCS encoder
        "nonce": str(nonce),
    }

    canonical_bytes: bytes = canonicalize(payload)

    digest_hex: str = hashlib.sha256(canonical_bytes).hexdigest()

    _logger.debug(
        "compute_action_digest: tool_id=%r nonce=%s digest=%s",
        tool_id,
        str(nonce),
        digest_hex[:16] + "...",  # Log only first 16 chars for brevity
    )

    return digest_hex
