# SPDX-License-Identifier: Apache-2.0
"""Q7 — Tier classification + mocking discipline (5 checks).

These checks bridge the manifest's `tier` declaration to actual code
behaviour: live adapters must import an HTTP client, mock adapters
must NOT, and both must ship a recorded fixture so CI can replay
without touching the network (Constitution §IV).
"""

from __future__ import annotations

import ast
from pathlib import Path

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def _adapter_path(ctx: CheckContext) -> Path | None:
    if ctx.manifest is None:
        return None
    pkg = f"plugin_{ctx.manifest.plugin_id}"
    candidate = ctx.plugin_root / pkg / "adapter.py"
    return candidate if candidate.is_file() else None


def _imports_in_module(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def check_tier_literal(ctx: CheckContext) -> CheckOutcome:
    """Q7-TIER-LITERAL — tier ∈ {live, mock}."""
    blocked = _ensure_manifest(ctx, "Q7-TIER-LITERAL")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.tier not in ("live", "mock"):
        return failed(
            ko=f"tier {ctx.manifest.tier!r} 가 {{live, mock}} 외",
            en=f"tier {ctx.manifest.tier!r} must be one of {{live, mock}}",
        )
    return passed()


def check_mock_source(ctx: CheckContext) -> CheckOutcome:
    """Q7-MOCK-SOURCE — tier=mock requires mock_source_spec non-empty."""
    blocked = _ensure_manifest(ctx, "Q7-MOCK-SOURCE")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.tier == "mock" and not (ctx.manifest.mock_source_spec or "").strip():
        return failed(
            ko=(
                "tier=mock 일 때 mock_source_spec 비어 있지 않음 (memory "
                "feedback_mock_evidence_based)"
            ),
            en=(
                "tier=mock requires non-empty mock_source_spec (memory "
                "feedback_mock_evidence_based)"
            ),
        )
    if ctx.manifest.tier == "live" and ctx.manifest.mock_source_spec:
        return failed(
            ko="tier=live 일 때 mock_source_spec 은 None 이어야 함",
            en="tier=live must have mock_source_spec=None",
        )
    return passed()


def check_live_uses_network(ctx: CheckContext) -> CheckOutcome:
    """Q7-LIVE-USES-NETWORK — tier=live adapter imports httpx or aiohttp."""
    blocked = _ensure_manifest(ctx, "Q7-LIVE-USES-NETWORK")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.tier != "live":
        return passed()
    adapter_path = _adapter_path(ctx)
    if adapter_path is None:
        return failed(
            ko="adapter.py 를 찾을 수 없음 (Q7-LIVE-USES-NETWORK)",
            en="adapter.py not found (Q7-LIVE-USES-NETWORK)",
        )
    imports = _imports_in_module(adapter_path)
    if not (imports & {"httpx", "aiohttp", "requests"}):
        return failed(
            ko=(
                "tier=live 어댑터는 httpx / aiohttp / requests 중 하나를 import 해야 함 "
                "(Q7-LIVE-USES-NETWORK)"
            ),
            en=("tier=live adapter must import httpx / aiohttp / requests (Q7-LIVE-USES-NETWORK)"),
        )
    return passed()


def check_mock_no_egress(ctx: CheckContext) -> CheckOutcome:
    """Q7-MOCK-NO-EGRESS — tier=mock adapter must NOT import an HTTP client.

    The runtime socket-block is verified via the autouse `block_network`
    fixture in the scaffold's `tests/conftest.py`; this static check
    catches egress imports before tests run.
    """
    blocked = _ensure_manifest(ctx, "Q7-MOCK-NO-EGRESS")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if ctx.manifest.tier != "mock":
        return passed()
    adapter_path = _adapter_path(ctx)
    if adapter_path is None:
        return failed(
            ko="adapter.py 를 찾을 수 없음 (Q7-MOCK-NO-EGRESS)",
            en="adapter.py not found (Q7-MOCK-NO-EGRESS)",
        )
    imports = _imports_in_module(adapter_path)
    forbidden = imports & {"httpx", "aiohttp", "requests", "urllib3"}
    if forbidden:
        return failed(
            ko=(f"tier=mock 어댑터에 네트워크 라이브러리 import 금지: {sorted(forbidden)}"),
            en=(f"tier=mock adapter must not import network libraries: {sorted(forbidden)}"),
        )
    return passed()


def check_live_fixture(ctx: CheckContext) -> CheckOutcome:
    """Q7-LIVE-FIXTURE — every adapter (live OR mock) ships a recorded fixture."""
    blocked = _ensure_manifest(ctx, "Q7-LIVE-FIXTURE")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    fixture_dir = ctx.plugin_root / "tests" / "fixtures"
    if not fixture_dir.is_dir():
        return failed(
            ko="tests/fixtures/ 디렉토리 없음 (Q7-LIVE-FIXTURE)",
            en="tests/fixtures/ directory missing (Q7-LIVE-FIXTURE)",
        )
    json_files = list(fixture_dir.glob("*.json"))
    if not json_files:
        return failed(
            ko="tests/fixtures/ 에 *.json fixture 가 1개 이상 필요",
            en="tests/fixtures/ must contain at least one *.json fixture",
        )
    return passed()


__all__ = [
    "check_tier_literal",
    "check_mock_source",
    "check_live_uses_network",
    "check_mock_no_egress",
    "check_live_fixture",
]
