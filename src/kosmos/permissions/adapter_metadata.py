# SPDX-License-Identifier: Apache-2.0
"""Read-only projection from ``GovAPITool`` to ``AdapterPermissionMetadata``.

Spec 033 FR-F01 — Integration with Spec 024 ``GovAPITool`` schema.

This module provides a single function ``project()`` that extracts the
permission-relevant fields from a ``GovAPITool`` instance and returns a
frozen ``AdapterPermissionMetadata`` model.  It never modifies the source
tool and raises ``AdapterMetadataIncomplete`` (Invariant A1) if any required
field is missing or ``None``.

Reference: specs/033-permission-v2-spectrum/data-model.md § 1.4
Source of ``GovAPITool``: ``src/kosmos/tools/models.py``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type hints to avoid circular imports at runtime.
    # The actual ``GovAPITool`` class is imported lazily in ``project()``.
    pass

from kosmos.permissions.models import AdapterPermissionMetadata

__all__ = [
    "AdapterMetadataIncomplete",
    "AdapterMetadataIncompleteError",
    "project",
]

_logger = logging.getLogger(__name__)


class AdapterMetadataIncompleteError(ValueError):
    """Raised when a required ``GovAPITool`` field is missing (Invariant A1).

    The permission pipeline fails closed if ``is_irreversible``, ``auth_level``,
    or ``pipa_class`` is not set on the adapter definition.  Partial or
    ``None`` values are NOT acceptable — every adapter that can be invoked
    through the permission pipeline MUST declare these fields explicitly.

    Attributes:
        tool_id: The id of the adapter missing the field.
        missing_fields: A tuple of field names that were missing or ``None``.
    """

    def __init__(self, tool_id: str, missing_fields: tuple[str, ...]) -> None:
        self.tool_id = tool_id
        self.missing_fields = missing_fields
        super().__init__(
            f"Invariant A1 violation: adapter {tool_id!r} is missing required "
            f"permission metadata fields: {missing_fields!r}. "
            "The permission pipeline cannot proceed without these fields. "
            "Declare them on the GovAPITool definition."
        )


# Keep the old name as an alias for backwards compatibility with any code that
# uses AdapterMetadataIncomplete (data-model references).
AdapterMetadataIncomplete = AdapterMetadataIncompleteError


_PIPA_CLASS_MAP: dict[str, str] = {
    "non_personal": "일반",
    "personal": "일반",
    "sensitive": "민감",
    "identifier": "고유식별",
}
"""Map from ``GovAPITool.pipa_class`` (English) to Permission v2 Korean literals.

``GovAPITool`` uses English enum values (``non_personal``, ``personal``,
``sensitive``, ``identifier``).  Permission v2 ``AdapterPermissionMetadata``
uses the PIPA Korean classification literals required by PIPA §23/§24.

Mapping rationale (data-model.md § 1.4):
- ``non_personal`` → ``일반`` (no personal data; lowest sensitivity)
- ``personal``     → ``일반`` (general personal data per PIPA §2.1)
- ``sensitive``    → ``민감`` (sensitive data per PIPA §23)
- ``identifier``   → ``고유식별`` (unique identifiers per PIPA §24)

Note: ``특수`` (special category) is not represented in the current
``GovAPITool.pipa_class`` enum.  Adapters that handle special-category data
would require a dedicated ``pipa_class`` value extension (deferred to future
work per spec.md).
"""


def project(tool: object) -> AdapterPermissionMetadata:
    """Project a ``GovAPITool`` instance to ``AdapterPermissionMetadata``.

    Extracts the subset of ``GovAPITool`` fields required by the Permission v2
    pipeline.  This is a read-only projection — it does not modify *tool*.

    Fails closed (Invariant A1): if ``is_irreversible``, ``auth_level``, or
    ``pipa_class`` is ``None`` or missing on *tool*, raises
    ``AdapterMetadataIncomplete``.

    Args:
        tool: A ``GovAPITool`` instance (typed as ``object`` to avoid a hard
              import-time dependency; validated via ``hasattr`` checks).

    Returns:
        A frozen ``AdapterPermissionMetadata`` instance.

    Raises:
        AdapterMetadataIncomplete: If required security metadata is absent.
        TypeError: If *tool* is not a ``GovAPITool``-compatible object.
    """
    # Validate that the object has the expected shape.
    _require_attrs(
        tool, ("id", "auth_level", "pipa_class", "is_irreversible", "requires_auth", "auth_type")
    )

    # Access attributes directly (B009: avoid getattr with constant string).
    # The _require_attrs call above guarantees these attributes exist.
    tool_id: str = tool.id  # type: ignore[attr-defined]
    missing: list[str] = []

    auth_level = tool.auth_level  # type: ignore[attr-defined]
    if auth_level is None:
        missing.append("auth_level")

    pipa_class_raw = tool.pipa_class  # type: ignore[attr-defined]
    if pipa_class_raw is None:
        missing.append("pipa_class")

    is_irreversible = tool.is_irreversible  # type: ignore[attr-defined]
    if is_irreversible is None:
        missing.append("is_irreversible")

    requires_auth = tool.requires_auth  # type: ignore[attr-defined]
    if requires_auth is None:
        missing.append("requires_auth")

    auth_type = tool.auth_type  # type: ignore[attr-defined]
    if auth_type is None:
        missing.append("auth_type")

    if missing:
        _logger.error(
            "Invariant A1: adapter %r missing permission fields: %s",
            tool_id,
            missing,
        )
        raise AdapterMetadataIncompleteError(tool_id, tuple(missing))

    # Map GovAPITool.pipa_class (English) to Permission v2 Korean literals.
    pipa_class_v2 = _PIPA_CLASS_MAP.get(pipa_class_raw)
    if pipa_class_v2 is None:
        raise AdapterMetadataIncompleteError(
            tool_id,
            (f"pipa_class={pipa_class_raw!r} has no Korean mapping",),
        )

    return AdapterPermissionMetadata(
        tool_id=tool_id,
        is_irreversible=bool(is_irreversible),
        auth_level=auth_level,
        pipa_class=pipa_class_v2,  # type: ignore[arg-type]
        requires_auth=bool(requires_auth),
        auth_type=auth_type,
    )


def _require_attrs(obj: object, attrs: tuple[str, ...]) -> None:
    """Raise ``TypeError`` if *obj* is missing any of the required attributes."""
    missing = [a for a in attrs if not hasattr(obj, a)]
    if missing:
        raise TypeError(
            f"Object {type(obj).__name__!r} is not a GovAPITool-compatible "
            f"instance: missing attributes {missing!r}."
        )
