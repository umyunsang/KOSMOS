# SPDX-License-Identifier: Apache-2.0
"""Q3 — Security V1–V6 invariants (5 checks).

These checks reuse the existing Spec 024 / 025 invariant logic by
re-running the manifest through PluginManifest's validators (which
embed the AdapterRegistration validators). The work was done at
manifest-construction time; this module just surfaces structured
failures for any drift introduced by `model_construct` or direct
``object.__setattr__`` on a frozen instance.
"""

from __future__ import annotations

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed
from kosmos.tools.models import _AUTH_TYPE_LEVEL_MAPPING


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
    """Q3-V2-DPA — pipa_class != non_personal ⇒ dpa_reference non-null."""
    blocked = _ensure_manifest(ctx, "Q3-V2-DPA")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.pipa_class != "non_personal" and not a.dpa_reference:
        return failed(
            ko=(f"pipa_class={a.pipa_class!r} 일 때 dpa_reference 필수 (Spec 024 V2)"),
            en=(f"pipa_class={a.pipa_class!r} requires non-null dpa_reference (Spec 024 V2)"),
        )
    return passed()


def check_v3_aal_match(ctx: CheckContext) -> CheckOutcome:
    """Q3-V3-AAL-MATCH — auth_level matches TOOL_MIN_AAL[tool_id] when registered.

    For freshly-authored plugins not yet in TOOL_MIN_AAL, the check
    passes (TOOL_MIN_AAL is host-side ground truth populated at
    registration). This is the fall-through path.
    """
    blocked = _ensure_manifest(ctx, "Q3-V3-AAL-MATCH")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    # Lazy import keeps Spec 024 audit module out of the standalone scaffold's
    # critical path.
    from kosmos.security.audit import TOOL_MIN_AAL

    a = ctx.manifest.adapter
    expected = TOOL_MIN_AAL.get(a.tool_id)
    if expected is not None and expected != a.auth_level:
        return failed(
            ko=(f"V3 위반: declared {a.auth_level!r} != TOOL_MIN_AAL {expected!r}"),
            en=(f"V3 violation: declared {a.auth_level!r} != TOOL_MIN_AAL {expected!r}"),
        )
    return passed()


def check_v4_irreversible_aal(ctx: CheckContext) -> CheckOutcome:
    """Q3-V4-IRREVERSIBLE-AAL — is_irreversible=True ⇒ auth_level ≥ AAL2."""
    blocked = _ensure_manifest(ctx, "Q3-V4-IRREVERSIBLE-AAL")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.is_irreversible and a.auth_level not in ("AAL2", "AAL3"):
        return failed(
            ko=(f"is_irreversible=True 인 어댑터는 auth_level ≥ AAL2 필요 (현재 {a.auth_level!r})"),
            en=(f"is_irreversible=True adapter requires auth_level ≥ AAL2 (got {a.auth_level!r})"),
        )
    return passed()


def check_v6_auth_level_map(ctx: CheckContext) -> CheckOutcome:
    """Q3-V6-AUTH-LEVEL-MAP — (auth_type, auth_level) ∈ canonical map."""
    blocked = _ensure_manifest(ctx, "Q3-V6-AUTH-LEVEL-MAP")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    allowed = _AUTH_TYPE_LEVEL_MAPPING.get(a.auth_type)
    if allowed is None:
        return failed(
            ko=f"unknown auth_type={a.auth_type!r} — V6 위반",
            en=f"unknown auth_type={a.auth_type!r} — V6 violation",
        )
    if a.auth_level not in allowed:
        return failed(
            ko=(
                f"V6 위반: auth_type={a.auth_type!r} 는 auth_level "
                f"{sorted(allowed)} 만 허용 (현재 {a.auth_level!r})"
            ),
            en=(
                f"V6 violation: auth_type={a.auth_type!r} only allows auth_level "
                f"{sorted(allowed)} (got {a.auth_level!r})"
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
