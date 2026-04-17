# SPDX-License-Identifier: Apache-2.0
"""Authoritative Authenticator Assurance Level (AAL) lookup for KOSMOS tools.

Implements the single-source-of-truth ``TOOL_MIN_AAL`` table and the
``PublicPathMeta`` dataclass that captures the ``check_eligibility`` rules-only
fallback path.

References
----------
- NIST SP 800-63-4 "Digital Identity Guidelines" (2024, supersedes withdrawn
  SP 800-63-3): defines AAL1/AAL2/AAL3 and the "no authentication" baseline
  used here as ``"public"``.
- ``specs/024-tool-security-v1/data-model.md`` §2 — authoritative table.
- ``specs/024-tool-security-v1/spec.md`` — FR-002, FR-003, FR-004.

The table covers every canonical tool exposed by the KOSMOS tool loop:

- ``lookup`` — AAL1
- ``resolve_location`` — AAL1
- ``check_eligibility`` — AAL2 with ``public_path`` marker (AAL1 permitted for
  rules-only evaluation over public inputs with no PII in request or response)
- ``subscribe_alert`` — AAL2
- ``reserve_slot`` — AAL2
- ``issue_certificate`` — AAL3
- ``submit_application`` — AAL2
- ``pay`` — AAL3

Every ``GovAPITool.auth_level`` MUST equal its row here; drift is a load-time
failure enforced by validator ``V3`` in ``kosmos.tools.models``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, model_validator

AALLevel = Literal["public", "AAL1", "AAL2", "AAL3"]
PIPAClass = Literal["non_personal", "personal", "sensitive", "identifier"]
AdapterMode = Literal["mock", "live"]
PermissionDecision = Literal[
    "allow",
    "deny_aal",
    "deny_scope",
    "deny_irreversible_introspect_failed",
    "deny_deny_by_default",
]
MerkleCoveredHash = Literal["sanitized_output_hash", "output_hash"]

TOOL_MIN_AAL: Final[dict[str, AALLevel]] = {
    "lookup": "AAL1",
    "resolve_location": "AAL1",
    "check_eligibility": "AAL2",
    "subscribe_alert": "AAL2",
    "reserve_slot": "AAL2",
    "issue_certificate": "AAL3",
    "submit_application": "AAL2",
    "pay": "AAL3",
}


@dataclass(frozen=True)
class PublicPathMeta:
    """Metadata describing a tool's rules-only public-path fallback.

    Only ``check_eligibility`` carries a public-path today: it may be invoked
    at AAL1 when the evaluation is purely rules-based over public inputs with
    no PII in either the request or the response. Every other tool MUST run at
    its declared ``TOOL_MIN_AAL`` row.

    Attributes
    ----------
    tool_id:
        Canonical tool identifier the public-path applies to.
    fallback_aal:
        AAL level permitted when the public-path preconditions hold.
    condition:
        Human-readable precondition narrative reproduced verbatim from the
        spec so audit reviewers can trace the carve-out.
    """

    tool_id: str
    fallback_aal: AALLevel
    condition: str


PUBLIC_PATH_META: Final[dict[str, PublicPathMeta]] = {
    "check_eligibility": PublicPathMeta(
        tool_id="check_eligibility",
        fallback_aal="AAL1",
        condition=(
            "AAL1 permitted for rules-only evaluation over public inputs "
            "with no PII in request or response"
        ),
    ),
}


_HEX_SHA256_LEN: Final[int] = 64


def _is_hex_sha256(value: str) -> bool:
    """Return True when *value* is a lowercase hex SHA-256 digest."""
    if len(value) != _HEX_SHA256_LEN:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


class ToolCallAuditRecord(BaseModel):
    """Immutable per-call evidence artifact for KOSMOS tool invocations.

    Schema version ``v1``. Authoritative field spec and invariants live in
    ``specs/024-tool-security-v1/data-model.md`` §3 and the JSON Schema at
    ``contracts/tool-call-audit-record.schema.json``.

    Invariants enforced via ``model_validator(mode="after")``:

    - ``I1``: ``sanitized_output_hash is not None`` ↔
      ``merkle_covered_hash == "sanitized_output_hash"``.
    - ``I2``: ``public_path_marker = True`` →
      ``tool_id == "check_eligibility"`` AND
      ``auth_level_presented == "AAL1"`` AND
      ``pipa_class == "non_personal"``.
    - ``I3``: ``pipa_class != "non_personal"`` → ``dpa_reference is not None``.
    - ``I4``: ``timestamp.tzinfo is not None`` (RFC 3339 naive timestamps
      rejected).

    Mock/live parity: the only permitted shape-differing field between a mock
    record and a live record for the same tool is ``adapter_mode``.

    Performance target: ``model_validate`` runs in < 5 ms per record, averaged
    over 1000 iterations (validated in ``tests/unit/test_tool_call_audit_record.py``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_version: Literal["v1"]
    tool_id: str
    adapter_mode: AdapterMode
    session_id: str
    caller_identity: str
    permission_decision: PermissionDecision
    auth_level_presented: AALLevel
    pipa_class: PIPAClass
    dpa_reference: str | None = None
    input_hash: str
    output_hash: str
    sanitized_output_hash: str | None = None
    merkle_covered_hash: MerkleCoveredHash
    merkle_leaf_id: str | None = None
    timestamp: datetime
    cost_tokens: int
    rate_limit_bucket: str
    public_path_marker: bool

    @model_validator(mode="after")
    def _validate_invariants(self) -> ToolCallAuditRecord:
        # Field-shape checks that JSON Schema enforces via pattern/minLength.
        if not self.tool_id or not self.tool_id[0].islower():
            raise ValueError(
                f"tool_id must match ^[a-z][a-z0-9_]*$; got {self.tool_id!r}"
            )
        for ch in self.tool_id:
            if not (ch.islower() or ch.isdigit() or ch == "_"):
                raise ValueError(
                    f"tool_id must match ^[a-z][a-z0-9_]*$; got {self.tool_id!r}"
                )
        if not self.session_id:
            raise ValueError("session_id must be non-empty")
        if not self.caller_identity:
            raise ValueError("caller_identity must be non-empty")
        if not self.rate_limit_bucket:
            raise ValueError("rate_limit_bucket must be non-empty")
        if self.cost_tokens < 0:
            raise ValueError(
                f"cost_tokens must be >= 0; got {self.cost_tokens}"
            )
        if not _is_hex_sha256(self.input_hash):
            raise ValueError(
                "input_hash must be a lowercase hex SHA-256 digest (64 chars)"
            )
        if not _is_hex_sha256(self.output_hash):
            raise ValueError(
                "output_hash must be a lowercase hex SHA-256 digest (64 chars)"
            )
        if self.sanitized_output_hash is not None and not _is_hex_sha256(
            self.sanitized_output_hash
        ):
            raise ValueError(
                "sanitized_output_hash must be a lowercase hex SHA-256 digest "
                "(64 chars) when provided"
            )

        # I1: sanitized_output_hash non-null iff merkle_covered_hash binds it.
        if self.sanitized_output_hash is not None:
            if self.merkle_covered_hash != "sanitized_output_hash":
                raise ValueError(
                    "I1 violation: sanitized_output_hash is set but "
                    "merkle_covered_hash != 'sanitized_output_hash'."
                )
        else:
            if self.merkle_covered_hash != "output_hash":
                raise ValueError(
                    "I1 violation: sanitized_output_hash is None but "
                    "merkle_covered_hash != 'output_hash'."
                )

        # I2: public_path_marker implies check_eligibility + AAL1 + non_personal.
        if self.public_path_marker:
            if self.tool_id != "check_eligibility":
                raise ValueError(
                    "I2 violation: public_path_marker=True requires "
                    f"tool_id='check_eligibility'; got {self.tool_id!r}."
                )
            if self.auth_level_presented != "AAL1":
                raise ValueError(
                    "I2 violation: public_path_marker=True requires "
                    "auth_level_presented='AAL1'; got "
                    f"{self.auth_level_presented!r}."
                )
            if self.pipa_class != "non_personal":
                raise ValueError(
                    "I2 violation: public_path_marker=True requires "
                    f"pipa_class='non_personal'; got {self.pipa_class!r}."
                )

        # I3: pipa_class != non_personal implies dpa_reference is non-null.
        if self.pipa_class != "non_personal" and not self.dpa_reference:
            raise ValueError(
                "I3 violation: pipa_class="
                f"{self.pipa_class!r} requires a non-empty dpa_reference."
            )

        # I4: timestamps must be timezone-aware (RFC 3339 with tz).
        if self.timestamp.tzinfo is None:
            raise ValueError(
                "I4 violation: timestamp must be timezone-aware (RFC 3339)."
            )

        return self


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
