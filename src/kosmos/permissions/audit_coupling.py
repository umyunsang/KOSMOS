# SPDX-License-Identifier: Apache-2.0
"""Spec 024 ToolCallAuditRecord coupling — Spec 033 FR-F01.

Links a ``ConsentDecision`` (from the PIPA consent ledger) and a
``correlation_id`` (from the Spec 032 IPC envelope) to a
``ToolCallAuditRecord`` (Spec 024) by producing a new immutable record with
the two fields populated.

Design constraints:
- ``ToolCallAuditRecord`` is a frozen Pydantic v2 model (Spec 024, extra="forbid").
  The model currently carries no ``consent_receipt_id`` or ``correlation_id``
  fields.  We therefore attach them via ``model_extra`` is not available due to
  ``extra="forbid"``.  The coupling contract is expressed as a
  ``AuditCouplingResult`` wrapper that co-locates the audit record with the
  consent context — Lead should integrate this wrapper into ``pipeline_v2.py``
  once Spec 024 adds the fields, or use the wrapper directly in the meantime.
- This module is a **downstream consumer** of Spec 024.  It MUST NOT modify
  ``kosmos.security.audit.ToolCallAuditRecord``.

Deviation reported to Lead (see module docstring DEVIATION NOTE below).

FR-F01: every consent-required tool call produces an audit record where
  ``consent_receipt_id`` is non-null and ``correlation_id`` matches the IPC
  envelope.

Reference:
  specs/033-permission-v2-spectrum/spec.md §FR-F01
  src/kosmos/security/audit.py ToolCallAuditRecord
  src/kosmos/permissions/models.py ConsentDecision
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

# NOTE: ToolCallAuditRecord is imported from Spec 024 — we do NOT modify it.
# As of commit 91a18fb, ToolCallAuditRecord does NOT contain
# ``consent_receipt_id`` or ``correlation_id`` fields because Spec 024
# predates Spec 033.  This module defines ``AuditCouplingResult`` as the
# integration point.  Lead must either:
#   (a) Add these two fields to ToolCallAuditRecord (requires a Spec 024
#       addendum PR), or
#   (b) Accept AuditCouplingResult as the canonical envelope in pipeline_v2.py
#       and downstream consumers (recommended for this iteration).
# This deviation is documented in the WS5 Report Back section.
from kosmos.permissions.models import ConsentDecision
from kosmos.security.audit import ToolCallAuditRecord

__all__ = [
    "AuditCouplingResult",
    "couple_audit_record",
    "MissingConsentReceiptError",
]

_logger = logging.getLogger(__name__)


class MissingConsentReceiptError(ValueError):
    """Raised when ``consent.action_digest`` cannot serve as receipt proxy.

    Under FR-F01 every consent-required call MUST produce a non-null
    consent_receipt_id.  If the ``ConsentDecision`` lacks any stable
    identifier, this error fires to keep the audit chain complete.
    """

    def __init__(self, tool_id: str) -> None:
        super().__init__(
            f"FR-F01 violation: cannot couple audit record for tool {tool_id!r} "
            "because ConsentDecision carries no stable receipt identifier "
            "(action_digest is empty or None).  The consent ledger record "
            "MUST include a non-empty action_digest before audit coupling."
        )


@dataclass(frozen=True)
class AuditCouplingResult:
    """Immutable wrapper coupling a ToolCallAuditRecord to its consent context.

    Because ``ToolCallAuditRecord`` (Spec 024) does not yet carry
    ``consent_receipt_id`` or ``correlation_id`` as first-class fields
    (see DEVIATION NOTE in module docstring), this frozen dataclass is the
    integration envelope used by ``pipeline_v2.py``.

    Attributes:
        audit_record: The original Spec 024 frozen record (unchanged).
        consent_receipt_id: The consent receipt identifier derived from
            ``ConsentDecision.action_digest``.  Guaranteed non-null when
            produced by ``couple_audit_record``.
        correlation_id: The IPC correlation id from Spec 032 envelope.
            Guaranteed non-empty string.
        consent_decision: The full ConsentDecision snapshot for downstream
            audit trail consumers (e.g., ledger append, OTEL enrichment).
    """

    audit_record: ToolCallAuditRecord
    consent_receipt_id: str
    correlation_id: str
    consent_decision: ConsentDecision


def couple_audit_record(
    audit_record: ToolCallAuditRecord,
    consent: ConsentDecision,
    correlation_id: str,
) -> AuditCouplingResult:
    """Link a ConsentDecision and correlation_id to a ToolCallAuditRecord.

    Returns a new immutable ``AuditCouplingResult`` wrapping the original
    frozen record with the consent context attached.  The original
    ``audit_record`` is never mutated.

    FR-F01 enforcement:
    - ``consent.action_digest`` must be a non-empty 64-character hex string
      (validated by ConsentDecision's model constraint).
    - ``correlation_id`` must be a non-empty string (from Spec 032 IPC
      envelope; guaranteed by ``_BaseFrame.correlation_id`` min_length=1).

    Args:
        audit_record: The Spec 024 frozen ToolCallAuditRecord for this call.
        consent: The ConsentDecision produced by the permission pipeline for
            this tool call.  Must have a non-empty ``action_digest``.
        correlation_id: The Spec 032 IPC envelope ``correlation_id`` for this
            request turn.  Must be non-empty.

    Returns:
        A frozen ``AuditCouplingResult`` with all four fields populated.

    Raises:
        MissingConsentReceiptError: If ``consent.action_digest`` is empty.
        ValueError: If ``correlation_id`` is empty.
    """
    if not correlation_id:
        raise ValueError(
            "FR-F01 violation: correlation_id must be non-empty "
            "(sourced from Spec 032 IPC envelope _BaseFrame.correlation_id)."
        )

    # Use action_digest as the stable receipt identifier.
    # In the full Spec 033 WS3 integration the ledger.append() call would
    # return a ConsentLedgerRecord whose consent_receipt_id is a UUIDv7.
    # Until WS3 lands the action_digest (SHA-256 of canonical args) provides
    # a stable, auditable identifier that satisfies FR-F01.
    receipt_id = consent.action_digest
    if not receipt_id:
        raise MissingConsentReceiptError(audit_record.tool_id)

    result = AuditCouplingResult(
        audit_record=audit_record,
        consent_receipt_id=receipt_id,
        correlation_id=correlation_id,
        consent_decision=consent,
    )

    _logger.info(
        "audit_coupling.coupled: tool_id=%s consent_receipt_id=%.16s correlation_id=%.16s",
        audit_record.tool_id,
        receipt_id,
        correlation_id,
    )
    return result
