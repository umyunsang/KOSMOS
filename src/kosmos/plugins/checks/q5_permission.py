# SPDX-License-Identifier: Apache-2.0
"""Q5 — Permission tier (3 checks).

These three checks enforce the migration tree § UI-C permission layer
discipline: every plugin declares 1 / 2 / 3, the layer is consistent
with PII handling, and the README explains why.
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


def check_layer_declared(ctx: CheckContext) -> CheckOutcome:
    """Q5-LAYER-DECLARED — permission_layer ∈ {1, 2, 3}."""
    blocked = _ensure_manifest(ctx, "Q5-LAYER-DECLARED")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.permission_layer not in (1, 2, 3):
        return failed(
            ko="permission_layer 가 {1,2,3} 중 하나여야 함",
            en="permission_layer must be one of {1, 2, 3}",
        )
    return passed()


def check_layer_matches_pii(ctx: CheckContext) -> CheckOutcome:
    """Q5-LAYER-MATCHES-PII — processes_pii=True ⇒ permission_layer ≥ 2."""
    blocked = _ensure_manifest(ctx, "Q5-LAYER-MATCHES-PII")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.processes_pii and ctx.manifest.permission_layer < 2:
        return failed(
            ko=("processes_pii=True 인데 permission_layer=1 — Layer 2 (orange) 이상 권장"),
            en=(
                "processes_pii=True but permission_layer=1 — Layer 2 (orange) or "
                "higher is recommended"
            ),
        )
    return passed()


def check_layer_doc(ctx: CheckContext) -> CheckOutcome:
    """Q5-LAYER-DOC — README.ko.md mentions the chosen permission layer."""
    blocked = _ensure_manifest(ctx, "Q5-LAYER-DOC")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    readme = ctx.plugin_root / "README.ko.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    layer_token = f"Layer {ctx.manifest.permission_layer}"
    layer_ko = f"권한 Layer {ctx.manifest.permission_layer}"
    if (
        layer_token not in text
        and layer_ko not in text
        and (f"permission_layer: {ctx.manifest.permission_layer}" not in text)
    ):
        return failed(
            ko=(
                f"README.ko.md 에 permission_layer ({ctx.manifest.permission_layer}) 근거 설명 권장"
            ),
            en=(
                f"README.ko.md should explain the chosen permission_layer "
                f"({ctx.manifest.permission_layer})"
            ),
        )
    return passed()


__all__ = [
    "check_layer_declared",
    "check_layer_matches_pii",
    "check_layer_doc",
]
