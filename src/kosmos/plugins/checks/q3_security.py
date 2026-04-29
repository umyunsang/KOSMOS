# SPDX-License-Identifier: Apache-2.0
"""Q3 — Security V1–V6 invariants (5 checks).

Epic δ #2295 Path B: V2/V3/V4/V6 invariants are rewritten to derive
``auth_level`` / ``is_irreversible`` / ``pipa_class`` from
``manifest.adapter.policy.citizen_facing_gate`` (via
:mod:`kosmos.tools.policy_derivation`) rather than reading standalone
KOSMOS-invented fields that are no longer stored.

The derivation guarantees V1/V4/V5 hold by construction:
  - PII-class gates (login/action/sign/submit) → AAL ≥ AAL2 (V1 preserved).
  - sign/submit → is_irreversible=True AND AAL3 (V4 tautology preserved).
  - read-only → non_personal pipa_class, AAL1 (V5 read-only path preserved).

What remains as runtime checks:
  - V1-NO-EXTRA: manifest does not carry unknown top-level keys.
  - V2-DPA: derived pipa_class != non_personal ⇒ dpa_reference non-null.
  - V3-AAL-MATCH: when tool_id appears in TOOL_MIN_AAL, derived AAL must match.
  - V4-IRREVERSIBLE-AAL: derived is_irreversible=True ⇒ derived AAL ≥ AAL2
    (tautological but kept for spec adherence; derivation guarantees it).
  - V6-AUTH-LEVEL-MAP: (auth_type, derived_auth_level) ∈ canonical map.

When ``manifest.adapter.policy is None`` (KOSMOS-internal synthetic surfaces)
all derivation-dependent checks pass silently — there is no agency-published
policy to validate against.
"""

from __future__ import annotations

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed
from kosmos.tools.models import _AUTH_TYPE_LEVEL_MAPPING
from kosmos.tools.policy_derivation import (
    derive_is_irreversible,
    derive_min_auth_level,
    derive_pipa_class_default,
)


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def check_v1_no_extra(ctx: CheckContext) -> CheckOutcome:
    """Q3-V1-NO-EXTRA — manifest does NOT carry unknown top-level keys."""
    blocked = _ensure_manifest(ctx, "Q3-V1-NO-EXTRA")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    # Pydantic v2.11+ deprecates instance access; read from the class.
    declared = set(type(ctx.manifest).model_fields.keys())
    raw = set(ctx.raw_manifest.keys())
    extras = raw - declared
    if extras:
        return failed(
            ko=f"manifest 에 정의되지 않은 키: {sorted(extras)}",
            en=f"manifest contains unknown keys: {sorted(extras)}",
        )
    return passed()


def check_v2_dpa(ctx: CheckContext) -> CheckOutcome:
    """Q3-V2-DPA — derived pipa_class != non_personal ⇒ dpa_reference non-null.

    Epic δ #2295 Path B: pipa_class is derived from
    ``adapter.policy.citizen_facing_gate`` rather than a stored field.
    When ``adapter.policy is None`` the derivation cannot run — the check
    passes silently (KOSMOS-internal surfaces have no agency policy).
    """
    blocked = _ensure_manifest(ctx, "Q3-V2-DPA")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.policy is None:
        # No agency policy — derivation not applicable; pass silently.
        return passed()
    derived_pipa = derive_pipa_class_default(a.policy.citizen_facing_gate)
    if derived_pipa != "non_personal" and not ctx.manifest.dpa_reference:
        return failed(
            ko=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived pipa_class={derived_pipa!r} 일 때 "
                "manifest.dpa_reference 필수 (Spec 024 V2)"
            ),
            en=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived pipa_class={derived_pipa!r} requires non-null "
                "manifest.dpa_reference (Spec 024 V2)"
            ),
        )
    return passed()


def check_v3_aal_match(ctx: CheckContext) -> CheckOutcome:
    """Q3-V3-AAL-MATCH — derived auth_level matches TOOL_MIN_AAL[tool_id].

    For freshly-authored plugins not yet in TOOL_MIN_AAL, the check
    passes (TOOL_MIN_AAL is host-side ground truth populated at
    registration). This is the fall-through path.

    Epic δ #2295 Path B: auth_level is derived from
    ``adapter.policy.citizen_facing_gate`` rather than a stored field.
    When ``adapter.policy is None`` the check passes silently.
    """
    blocked = _ensure_manifest(ctx, "Q3-V3-AAL-MATCH")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    # Lazy import keeps Spec 024 audit module out of the standalone scaffold's
    # critical path.
    from kosmos.security.audit import TOOL_MIN_AAL

    a = ctx.manifest.adapter
    if a.policy is None:
        # No agency policy — derivation not applicable; pass silently.
        return passed()
    derived_aal = derive_min_auth_level(a.policy.citizen_facing_gate)
    expected = TOOL_MIN_AAL.get(a.tool_id)
    if expected is not None and expected != derived_aal:
        return failed(
            ko=(
                f"V3 위반: citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived {derived_aal!r} != TOOL_MIN_AAL {expected!r}"
            ),
            en=(
                f"V3 violation: citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived {derived_aal!r} != TOOL_MIN_AAL {expected!r}"
            ),
        )
    return passed()


def check_v4_irreversible_aal(ctx: CheckContext) -> CheckOutcome:
    """Q3-V4-IRREVERSIBLE-AAL — derived is_irreversible=True ⇒ derived AAL ≥ AAL2.

    Epic δ #2295 Path B: both is_irreversible and auth_level are derived
    from ``adapter.policy.citizen_facing_gate``. The derivation mapping
    guarantees V4 holds by construction (sign/submit → irreversible + AAL3).
    The check is kept for spec adherence and as a defense-in-depth guard
    against future mapping table edits that might break the invariant.

    When ``adapter.policy is None`` the check passes silently.
    """
    blocked = _ensure_manifest(ctx, "Q3-V4-IRREVERSIBLE-AAL")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.policy is None:
        return passed()
    derived_irrev = derive_is_irreversible(a.policy.citizen_facing_gate)
    derived_aal = derive_min_auth_level(a.policy.citizen_facing_gate)
    if derived_irrev and derived_aal not in ("AAL2", "AAL3"):
        return failed(
            ko=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived is_irreversible=True 이지만 derived auth_level={derived_aal!r} < AAL2 "
                "(policy_derivation 매핑 테이블 버그 — ADR 필요)"
            ),
            en=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived is_irreversible=True but derived auth_level={derived_aal!r} < AAL2 "
                "(policy_derivation mapping table bug — requires ADR)"
            ),
        )
    return passed()


def check_v6_auth_level_map(ctx: CheckContext) -> CheckOutcome:
    """Q3-V6-AUTH-LEVEL-MAP — (auth_type, derived auth_level) ∈ canonical map.

    Epic δ #2295 Path B: auth_level is derived from
    ``adapter.policy.citizen_facing_gate`` rather than a stored field.
    When ``adapter.policy is None`` the check passes silently
    (KOSMOS-internal surfaces use their own auth_type governance).
    """
    blocked = _ensure_manifest(ctx, "Q3-V6-AUTH-LEVEL-MAP")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.policy is None:
        return passed()
    allowed = _AUTH_TYPE_LEVEL_MAPPING.get(a.auth_type)
    if allowed is None:
        return failed(
            ko=f"unknown auth_type={a.auth_type!r} — V6 위반",
            en=f"unknown auth_type={a.auth_type!r} — V6 violation",
        )
    derived_aal = derive_min_auth_level(a.policy.citizen_facing_gate)
    if derived_aal not in allowed:
        return failed(
            ko=(
                f"V6 위반: citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived auth_level={derived_aal!r}, "
                f"auth_type={a.auth_type!r} 는 {sorted(allowed)} 만 허용"
            ),
            en=(
                f"V6 violation: citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived auth_level={derived_aal!r}, "
                f"auth_type={a.auth_type!r} only allows {sorted(allowed)}"
            ),
        )
    return passed()


__all__ = [
    "check_v1_no_extra",
    "check_v2_dpa",
    "check_v3_aal_match",
    "check_v4_irreversible_aal",
    "check_v6_auth_level_map",
]
