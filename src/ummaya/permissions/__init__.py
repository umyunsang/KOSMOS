# SPDX-License-Identifier: Apache-2.0
"""UMMAYA Permission Layer (Spec 035 receipt set + harness session schema).

UMMAYA-invented permission orchestration classes removed in Epic δ #2295.
Retained surface: Spec 035 ledger models + SessionContext for query engine.

Quick start::

    from ummaya.permissions import SessionContext, PermissionMode
    from ummaya.permissions import ConsentLedgerRecord, LedgerVerifyReport
    from ummaya.permissions import ToolPermissionContext, AdapterPermissionMetadata
"""

from __future__ import annotations

from ummaya.permissions.models import (
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
