# SPDX-License-Identifier: Apache-2.0
"""OTel bridge utilities for KOSMOS observability.

Provides ``filter_metadata``, a PII-safe prefilter that strips non-whitelisted
keys and non-primitive values from a raw metadata dict before it is attached
as span attributes.

The whitelist is imported from ``event_logger._ALLOWED_METADATA_KEYS`` — that
module is the **single source of truth** for which metadata keys may be
observed.  This module must never define its own parallel whitelist.

Usage::

    from kosmos.observability.otel_bridge import filter_metadata

    safe_attrs = filter_metadata({"tool_id": "koroad_accident", "step": 3})
    span.set_attributes(safe_attrs)
"""

from __future__ import annotations

from kosmos.observability.event_logger import _ALLOWED_METADATA_KEYS

# Primitive types accepted by the OTel AttributeValue spec.
_Primitive = str | bool | int | float


def _is_primitive(value: object) -> bool:
    """Return True if *value* is a scalar OTel-compatible primitive."""
    # Note: bool must be checked before int because bool is a subclass of int.
    return isinstance(value, (str, bool, int, float))


def _is_primitive_list(value: object) -> bool:
    """Return True if *value* is a list whose every element is a primitive."""
    if not isinstance(value, list):
        return False
    return all(_is_primitive(item) for item in value)


def filter_metadata(raw: dict[str, object]) -> dict[str, object]:
    """Return a whitelisted, type-safe copy of *raw* suitable for span attributes.

    Rules applied in order:
    1. Drop any key not in ``_ALLOWED_METADATA_KEYS`` (PII prefilter, data-model § E5).
    2. Drop any value that is not ``str | bool | int | float`` or a homogeneous
       list of those primitives (OTel AttributeValue compatibility).

    The original dict is never mutated.  Dropped entries are silently discarded
    to avoid log noise on hot paths.

    Args:
        raw: Arbitrary metadata dictionary from the tool execution pipeline.

    Returns:
        A new dict containing only the entries that pass both the whitelist and
        the type filter.
    """
    result: dict[str, object] = {}
    for key, value in raw.items():
        if key not in _ALLOWED_METADATA_KEYS:
            continue
        if _is_primitive(value) or _is_primitive_list(value):
            result[key] = value
    return result
