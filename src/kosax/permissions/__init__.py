# SPDX-License-Identifier: Apache-2.0
"""KOSAX Permission Layer (Spec 035 receipt set + harness session schema).

KOSAX-invented permission orchestration classes removed in Epic δ #2295.
Retained surface: Spec 035 ledger models + SessionContext for query engine.

Quick start::

    from kosax.permissions import SessionContext, PermissionMode
    from kosax.permissions import ConsentLedgerRecord, LedgerVerifyReport
    from kosax.permissions import ToolPermissionContext, AdapterPermissionMetadata
"""

from __future__ import annotations

from kosax.permissions.models import (
    AdapterPermissionMetadata,
    ConsentDecision,
    ConsentLedgerRecord,
    LedgerVerifyReport,
    PermissionMode,
    SessionContext,
    ToolPermissionContext,
)

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "AdapterPermissionMetadata",
    "ConsentDecision",
    "ConsentLedgerRecord",
    "LedgerVerifyReport",
    "PermissionMode",
    "SessionContext",
    "ToolPermissionContext",
]
