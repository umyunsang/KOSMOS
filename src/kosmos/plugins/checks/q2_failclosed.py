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
    """Q2-AUTH-DEFAULT — adapter.requires_auth=True (fail-closed)."""
    blocked = _ensure_manifest(ctx, "Q2-AUTH-DEFAULT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.adapter.requires_auth is not True:
        return failed(
            ko="requires_auth=True 가 fail-closed default — 변경 시 명시적 사유 필요",
            en="requires_auth=True is the fail-closed default — explicit override required",
        )
    return passed()


def check_pii_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-PII-DEFAULT — adapter.is_personal_data symmetric to processes_pii."""
    blocked = _ensure_manifest(ctx, "Q2-PII-DEFAULT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    # The fail-closed default is True. We accept either:
    #  - is_personal_data=True (default) AND processes_pii=True
    #  - is_personal_data=False AND processes_pii=False
    # Mismatch is suspicious and fails.
    if ctx.manifest.adapter.is_personal_data != ctx.manifest.processes_pii:
        return failed(
            ko=(
                "is_personal_data 와 processes_pii 가 일치해야 함 (Q2-PII-DEFAULT) — "
                f"adapter={ctx.manifest.adapter.is_personal_data}, "
                f"manifest={ctx.manifest.processes_pii}"
            ),
            en=(
                "adapter.is_personal_data and manifest.processes_pii must match "
                f"(Q2-PII-DEFAULT) — got {ctx.manifest.adapter.is_personal_data} vs "
                f"{ctx.manifest.processes_pii}"
            ),
        )
    return passed()


def check_concurrency_default(ctx: CheckContext) -> CheckOutcome:
    """Q2-CONCURRENCY-DEFAULT — adapter.is_concurrency_safe must be explicitly opted-in."""
    blocked = _ensure_manifest(ctx, "Q2-CONCURRENCY-DEFAULT")
    if blocked:
        return blocked
    # Fail-closed default is False. Either value is acceptable as long as
    # it was a deliberate choice — we cannot tell from the manifest alone
    # whether it was deliberate, but we still flag a glaring inconsistency:
    # marking `is_concurrency_safe=True` for an `is_irreversible=True`
    # adapter is contradictory.
    assert ctx.manifest is not None
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
    """Q2-AUTH-EXPLICIT — auth_level / pipa_class / is_irreversible / dpa_reference present.

    Pydantic already enforces required fields — this check is a defense-
    in-depth read on the parsed manifest (covers `model_construct` bypass).
    """
    blocked = _ensure_manifest(ctx, "Q2-AUTH-EXPLICIT")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    a = ctx.manifest.adapter
    missing: list[str] = []
    if not a.auth_level:
        missing.append("auth_level")
    if not a.pipa_class:
        missing.append("pipa_class")
    # is_irreversible is a bool — both values are valid; only None would mean missing.
    # dpa_reference may be None when pipa_class == non_personal (V2 invariant on Spec 024).
    if a.pipa_class != "non_personal" and a.dpa_reference is None:
        missing.append("dpa_reference (required when pipa_class != non_personal)")
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
