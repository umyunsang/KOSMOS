# SPDX-License-Identifier: Apache-2.0
"""Q2 — Fail-closed defaults (6 checks).

These checks operate against the validated PluginManifest's embedded
``adapter`` (an ``AdapterRegistration``). They mirror Constitution §II
fail-closed rules: every safety boolean defaults to the more restrictive
value, and rate-limit / cache-TTL keep numbers conservative.
"""

from __future__ import annotations

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def check_auth_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-AUTH-DEFAULT — adapter.policy is present (fail-closed sentinel for auth gate).

    Epic δ #2295 Path B: ``requires_auth`` was removed from AdapterRegistration
    (it was a KOSMOS-invented field; AGENTS.md § CORE THESIS forbids invention).
    The fail-closed sentinel is now ``adapter.policy`` — every adapter that
    performs citizen authentication MUST cite its agency policy.

    For KOSMOS-internal synthetic surfaces (resolve_location / lookup) ``policy``
    may legitimately be None. A plugin adapter with ``policy=None`` is suspicious
    (it means no agency policy was cited) and fails this check.
    """
    blocked = _ensure_manifest(ctx, "Q2-AUTH-DEFAULT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.adapter.policy is None:
        return failed(
            ko=(
                "adapter.policy 가 None — 플러그인 어댑터는 반드시 기관 정책을 인용해야 함 "
                "(AGENTS.md § CORE THESIS: KOSMOS는 권한 정책을 발명하지 않음)"
            ),
            en=(
                "adapter.policy is None — plugin adapters must cite agency policy "
                "(AGENTS.md § CORE THESIS: KOSMOS does not invent permission policy)"
            ),
        )
    return passed()


def check_pii_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-PII-DEFAULT — derived pipa_class symmetric to manifest.processes_pii.

    Epic δ #2295 Path B: ``is_personal_data`` was removed from AdapterRegistration
    (KOSMOS-invented field). The symmetry check now uses ``derived pipa_class``
    from ``adapter.policy.citizen_facing_gate`` vs ``manifest.processes_pii``.

    Acceptable combinations:
      - derived pipa_class != "non_personal" AND processes_pii=True
      - derived pipa_class == "non_personal" AND processes_pii=False

    When ``adapter.policy is None`` (KOSMOS-internal surfaces) the check
    passes silently — Q2-AUTH-DEFAULT already catches policy=None for plugins.
    """
    blocked = _ensure_manifest(ctx, "Q2-PII-DEFAULT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    if a.policy is None:
        return passed()
    from kosmos.tools.policy_derivation import derive_pipa_class_default

    derived_pipa = derive_pipa_class_default(a.policy.citizen_facing_gate)
    derived_is_pii = derived_pipa != "non_personal"
    # Mismatch between derived PII classification and manifest.processes_pii is suspicious.
    if derived_is_pii != ctx.manifest.processes_pii:
        return failed(
            ko=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived pipa_class={derived_pipa!r} (is_pii={derived_is_pii}) 와 "
                f"manifest.processes_pii={ctx.manifest.processes_pii} 가 불일치 (Q2-PII-DEFAULT)"
            ),
            en=(
                f"citizen_facing_gate={a.policy.citizen_facing_gate!r} → "
                f"derived pipa_class={derived_pipa!r} (is_pii={derived_is_pii}) "
                f"does not match manifest.processes_pii={ctx.manifest.processes_pii} "
                "(Q2-PII-DEFAULT)"
            ),
        )
    return passed()


def check_concurrency_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-CONCURRENCY-DEFAULT — adapter.is_concurrency_safe must be explicitly opted-in.

    Epic δ #2295 Path B: ``is_irreversible`` is now a ``computed_field``
    derived from ``adapter.policy.citizen_facing_gate`` (sign/submit → True).
    The check reads the computed property directly — no API change needed.
    When ``adapter.policy is None`` the derived value is False (conservative).
    """
    blocked = _ensure_manifest(ctx, "Q2-CONCURRENCY-DEFAULT")
    if blocked:
        return blocked
    # Fail-closed default is False. Either value is acceptable as long as
    # it was a deliberate choice — we cannot tell from the manifest alone
    # whether it was deliberate, but we still flag a glaring inconsistency:
    # marking `is_concurrency_safe=True` for an `is_irreversible=True`
    # adapter is contradictory.
    assert ctx.manifest is not None
    # is_irreversible is a computed_field — read via the computed property.
    if ctx.manifest.adapter.is_concurrency_safe and ctx.manifest.adapter.is_irreversible:
        return failed(
            ko="is_concurrency_safe=True 와 is_irreversible=True 는 모순",
            en="is_concurrency_safe=True conflicts with is_irreversible=True",
        )
    return passed()


def check_cache_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-CACHE-DEFAULT — cache_ttl_seconds must be ≥ 0 (no negative).

    Default 0 (no cache) is the fail-closed value. Any non-negative value
    is acceptable; negative values would be a fail-open mistake.
    """
    blocked = _ensure_manifest(ctx, "Q2-CACHE-DEFAULT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.adapter.cache_ttl_seconds < 0:
        return failed(
            ko=f"cache_ttl_seconds={ctx.manifest.adapter.cache_ttl_seconds} 음수 금지",
            en=f"cache_ttl_seconds={ctx.manifest.adapter.cache_ttl_seconds} must not be negative",
        )
    return passed()


def check_rate_limit_conservative(ctx: CheckContext) -> CheckOutcome:
    """Q2-RATE-LIMIT-CONSERVATIVE — rate_limit_per_minute ≤ 30 (guidance)."""
    blocked = _ensure_manifest(ctx, "Q2-RATE-LIMIT-CONSERVATIVE")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.adapter.rate_limit_per_minute > 30:
        return failed(
            ko=(
                f"rate_limit_per_minute={ctx.manifest.adapter.rate_limit_per_minute} > 30 — "
                "보수적 default 권장 (docs/tool-adapters.md guidance)"
            ),
            en=(
                f"rate_limit_per_minute={ctx.manifest.adapter.rate_limit_per_minute} exceeds the "
                "≤30 guidance (docs/tool-adapters.md)"
            ),
        )
    return passed()


def check_auth_explicit(ctx: CheckContext) -> CheckOutcome:
    """Q2-AUTH-EXPLICIT — policy / auth_type / derived auth_level / derived pipa_class present.

    Epic δ #2295 Path B: ``auth_level`` and ``pipa_class`` are now
    ``computed_field``s derived from ``adapter.policy.citizen_facing_gate``.
    They cannot be missing as long as the policy field is present and valid.

    This check is a defense-in-depth read on the parsed manifest (covers
    ``model_construct`` bypass). It verifies:
    1. ``auth_type`` is non-empty (required field in AdapterRegistration).
    2. When ``adapter.policy`` is set, derived ``auth_level`` + ``pipa_class``
       are non-empty (derivation mapping is exhaustive; this guards against
       an empty string slipping through a future mapping table edit).
    3. When derived ``pipa_class != non_personal`` and ``adapter.policy`` is
       set, ``manifest.dpa_reference`` must be non-null (V2 / Spec 024).

    Pydantic already enforces required fields — this is an additional backstop.
    """
    blocked = _ensure_manifest(ctx, "Q2-AUTH-EXPLICIT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    missing: list[str] = []

    # auth_type is a required stored field — both values are always valid strings.
    if not a.auth_type:
        missing.append("auth_type")

    if a.policy is not None:
        # Computed fields — read the properties (computed_field access).
        derived_aal = a.auth_level
        derived_pipa = a.pipa_class
        if not derived_aal:
            missing.append("auth_level (derived from policy.citizen_facing_gate)")
        if not derived_pipa:
            missing.append("pipa_class (derived from policy.citizen_facing_gate)")
        # V2 invariant — dpa_reference required for non-public PII gates.
        # dpa_reference is a standalone manifest field (PIPA §26 trustee cite).
        if derived_pipa != "non_personal" and ctx.manifest.dpa_reference is None:
            missing.append("dpa_reference (required when derived pipa_class != non_personal)")

    if missing:
        return failed(
            ko=f"Spec 024 필드 누락: {missing}",
            en=f"Spec 024 fields missing: {missing}",
        )
    return passed()


__all__ = [
    "check_auth_default",
    "check_pii_default",
    "check_concurrency_default",
    "check_cache_default",
    "check_rate_limit_conservative",
    "check_auth_explicit",
]
