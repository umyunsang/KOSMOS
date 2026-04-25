# SPDX-License-Identifier: Apache-2.0
"""Q6 — PIPA §26 trustee acknowledgment (4 checks).

Owned by Phase 5 T035. Lives here because the validation workflow
matrix iterates every Q-module under ``checks/`` — putting Q6 in a
separate directory would special-case the loader. Phase 5 closes the
checklist row + integrates the TUI sub-flow; the four check functions
themselves are mechanical.
"""

from __future__ import annotations

from kosmos.plugins.canonical_acknowledgment import CANONICAL_ACKNOWLEDGMENT_SHA256
from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def check_pipa_present(ctx: CheckContext) -> CheckOutcome:
    """Q6-PIPA-PRESENT — block present when processes_pii=True."""
    blocked = _ensure_manifest(ctx, "Q6-PIPA-PRESENT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.processes_pii and ctx.manifest.pipa_trustee_acknowledgment is None:
        return failed(
            ko=(
                "processes_pii=True 일 때 pipa_trustee_acknowledgment 필수 "
                "(docs/plugins/security-review.md 참고)"
            ),
            en=(
                "processes_pii=True requires pipa_trustee_acknowledgment "
                "(see docs/plugins/security-review.md)"
            ),
        )
    if not ctx.manifest.processes_pii and ctx.manifest.pipa_trustee_acknowledgment is not None:
        return failed(
            ko="processes_pii=False 인데 pipa_trustee_acknowledgment 가 설정됨",
            en="processes_pii=False but pipa_trustee_acknowledgment is set",
        )
    return passed()


def check_pipa_hash(ctx: CheckContext) -> CheckOutcome:
    """Q6-PIPA-HASH — acknowledgment_sha256 == canonical hash."""
    blocked = _ensure_manifest(ctx, "Q6-PIPA-HASH")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    ack = ctx.manifest.pipa_trustee_acknowledgment
    if ack is None:
        # Symmetric pass when processes_pii=False.
        return passed()
    if ack.acknowledgment_sha256 != CANONICAL_ACKNOWLEDGMENT_SHA256:
        return failed(
            ko=(
                f"acknowledgment_sha256 mismatch: expected "
                f"{CANONICAL_ACKNOWLEDGMENT_SHA256}, got {ack.acknowledgment_sha256}"
            ),
            en=(
                f"acknowledgment_sha256 mismatch: expected "
                f"{CANONICAL_ACKNOWLEDGMENT_SHA256}, got {ack.acknowledgment_sha256}"
            ),
        )
    return passed()


def check_pipa_org(ctx: CheckContext) -> CheckOutcome:
    """Q6-PIPA-ORG — trustee_org_name + trustee_contact non-empty."""
    blocked = _ensure_manifest(ctx, "Q6-PIPA-ORG")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    ack = ctx.manifest.pipa_trustee_acknowledgment
    if ack is None:
        return passed()
    if not ack.trustee_org_name.strip() or not ack.trustee_contact.strip():
        return failed(
            ko="trustee_org_name / trustee_contact 가 비어 있음",
            en="trustee_org_name / trustee_contact must not be empty",
        )
    return passed()


def check_pipa_fields_list(ctx: CheckContext) -> CheckOutcome:
    """Q6-PIPA-FIELDS-LIST — pii_fields_handled non-empty list."""
    blocked = _ensure_manifest(ctx, "Q6-PIPA-FIELDS-LIST")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    ack = ctx.manifest.pipa_trustee_acknowledgment
    if ack is None:
        return passed()
    if not ack.pii_fields_handled:
        return failed(
            ko="pii_fields_handled 가 빈 배열",
            en="pii_fields_handled must be a non-empty list",
        )
    return passed()


__all__ = [
    "check_pipa_present",
    "check_pipa_hash",
    "check_pipa_org",
    "check_pipa_fields_list",
]
