# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Permission Pipeline (Layer 3).

Public API for the 7-step permission gauntlet (v1) and the Permission v2
mode-spectrum + rule-store + consent-ledger layer (Spec 033, Epic #1297).

Quick start (v1 gauntlet)::

    from kosmos.permissions import PermissionPipeline, SessionContext

    pipeline = PermissionPipeline(executor=executor, registry=registry)
    result = await pipeline.run(
        tool_id="my_tool",
        arguments_json='{"query": "test"}',
        session_context=SessionContext(session_id="s1"),
    )

Quick start (v2 surface)::

    from kosmos.permissions import PermissionMode, ToolPermissionContext
    from kosmos.permissions import PermissionRule, ConsentLedgerRecord
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# v1 gauntlet surface (preserved; never removed)
# ---------------------------------------------------------------------------
from kosmos.permissions.bypass import BYPASS_IMMUNE_RULES, check_bypass_immune
from kosmos.permissions.models import (
    AccessTier,
    AdapterPermissionMetadata,
    AuditLogEntry,
    ConsentDecision,
    ConsentLedgerRecord,
    LedgerVerifyReport,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionRule,
    PermissionStepResult,
    SessionContext,
    ToolPermissionContext,
)
from kosmos.permissions.modes import PermissionMode
from kosmos.permissions.pipeline import PermissionPipeline

__version__ = "1.0.0"

__all__ = [
    # v1 gauntlet exports (Spec 001..032)
    "AccessTier",
    "AuditLogEntry",
    "BYPASS_IMMUNE_RULES",
    "PermissionCheckRequest",
    "PermissionDecision",
    "PermissionPipeline",
    "PermissionStepResult",
    "SessionContext",
    "check_bypass_immune",
    # v2 surface exports (Spec 033)
    "__version__",
    "AdapterPermissionMetadata",
    "ConsentDecision",
    "ConsentLedgerRecord",
    "LedgerVerifyReport",
    "PermissionMode",
    "PermissionRule",
    "ToolPermissionContext",
]
