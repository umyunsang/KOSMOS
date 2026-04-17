# SPDX-License-Identifier: Apache-2.0
"""KOSMOS security layer — audit records, AAL lookup, and permission primitives.

Spec: ``specs/024-tool-security-v1`` (Tool Template Security Spec v1).

The ``audit`` submodule exports:

- ``TOOL_MIN_AAL``: single-source-of-truth min-AAL table per canonical tool.
- ``PublicPathMeta``: dataclass capturing ``public_path`` rules-only fallback.
- ``PUBLIC_PATH_META``: mapping of tool IDs to their public-path metadata.
- ``AALLevel``: ``Literal["public", "AAL1", "AAL2", "AAL3"]`` alias.
- ``AdapterMode``, ``PermissionDecision``, ``PIPAClass``, ``MerkleCoveredHash``:
  ``Literal`` aliases covering the canonical enum surfaces of the audit record.
- ``ToolCallAuditRecord``: immutable per-call evidence artifact (schema v1).
"""

from __future__ import annotations

from kosmos.security.audit import (
    PUBLIC_PATH_META,
    TOOL_MIN_AAL,
    AALLevel,
    AdapterMode,
    MerkleCoveredHash,
    PermissionDecision,
    PIPAClass,
    PublicPathMeta,
    ToolCallAuditRecord,
)

__all__ = [
    "AALLevel",
    "AdapterMode",
    "MerkleCoveredHash",
    "PermissionDecision",
    "PIPAClass",
    "PUBLIC_PATH_META",
    "PublicPathMeta",
    "TOOL_MIN_AAL",
    "ToolCallAuditRecord",
]
