# SPDX-License-Identifier: Apache-2.0
"""Main-tool router with ministry-scope guard (Epic H #1302, task T028).

Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md § 5
Reference: Spec 022 (`kosmos.tools.lookup.lookup()`) — the actual routing
           engine.  This module wraps the lookup dispatch with a pre-network
           refusal path that reads the citizen's `MinistryScopeAcknowledgment`
           memdir record and blocks any tool call against a declined ministry
           in < 100 ms (SC-009).

The guard is synchronous by design — reading one JSON file from the memdir
USER tier is bounded by filesystem latency, not network latency — so the
< 100 ms target is structural, not a soft SLO.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from kosmos.memdir.ministry_scope import (
    MINISTRY_CODES,
    MinistryCode,
    MinistryScopeAcknowledgment,
    latest_scope,
    opt_in_lookup,
)

__all__ = [
    "MINISTRY_TOOL_PREFIX",
    "MinistryOptOutRefusal",
    "resolve_with_scope_guard",
    "ministry_for_tool",
    "ministry_korean_name",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool-prefix → ministry mapping (derived from Spec 022 adapter registry)
# ---------------------------------------------------------------------------

MINISTRY_TOOL_PREFIX: dict[str, MinistryCode] = {
    "koroad_": "KOROAD",
    "kma_": "KMA",
    "hira_": "HIRA",
    "nmc_": "NMC",
}


def ministry_for_tool(tool_id: str) -> MinistryCode | None:
    """Resolve a tool_id to its owning ministry, or None if not ministry-bound."""
    for prefix, code in MINISTRY_TOOL_PREFIX.items():
        if tool_id.startswith(prefix):
            return code
    return None


_MINISTRY_KOREAN: dict[MinistryCode, str] = {
    "KOROAD": "한국도로공사",
    "KMA": "기상청",
    "HIRA": "건강보험심사평가원",
    "NMC": "국립중앙의료원",
}


def ministry_korean_name(code: MinistryCode) -> str:
    return _MINISTRY_KOREAN[code]


# ---------------------------------------------------------------------------
# Refusal exception
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RefusalPayload:
    ministry: MinistryCode
    message: str


class MinistryOptOutRefusal(Exception):  # noqa: N818
    """Raised before any network call when the citizen opted out of `ministry`.

    Attributes:
        ministry:  The MinistryCode that was declined (or absent from scope).
        message:   Citizen-facing Korean refusal copy per contract § 5.

    N818 waiver: this exception's name is a contract-level identifier fixed by
    `specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md
    § 5`.  Renaming to `MinistryOptOutRefusalError` would break the spec
    reference and is therefore refused at the style-gate boundary.
    """

    def __init__(self, *, ministry: MinistryCode, message: str) -> None:
        self._payload = _RefusalPayload(ministry=ministry, message=message)
        super().__init__(message)

    @property
    def ministry(self) -> MinistryCode:
        return self._payload.ministry

    @property
    def message(self) -> str:
        return self._payload.message


# ---------------------------------------------------------------------------
# Scope-guarded dispatch
# ---------------------------------------------------------------------------

Resolver = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _build_refusal(ministry: MinistryCode) -> MinistryOptOutRefusal:
    message = (
        f"{ministry_korean_name(ministry)}의 데이터 사용에 동의하지 않으셨습니다. "
        f"다시 온보딩을 실행하시려면 세션을 종료하고 재시작하십시오."
    )
    return MinistryOptOutRefusal(ministry=ministry, message=message)


def check_ministry_scope(
    tool_id: str,
    *,
    memdir_root: Path,
    scope_override: MinistryScopeAcknowledgment | None = None,
) -> Literal["pass"] | MinistryOptOutRefusal:
    """Fail-closed ministry-scope check.

    - Non-ministry tool       → pass.
    - No scope record         → refusal (fail-closed default).
    - Ministry opt-out        → refusal.
    - Ministry opt-in         → pass.
    """
    ministry = ministry_for_tool(tool_id)
    if ministry is None:
        return "pass"

    scope = scope_override
    if scope is None:
        scope = latest_scope(memdir_root / "user" / "ministry-scope")
    if scope is None:
        return _build_refusal(ministry)
    if not opt_in_lookup(scope, ministry):
        return _build_refusal(ministry)
    return "pass"


async def resolve_with_scope_guard(
    tool_id: str,
    params: dict[str, Any],
    *,
    memdir_root: Path,
    resolver: Resolver,
    scope_override: MinistryScopeAcknowledgment | None = None,
) -> Any:
    """Run the ministry-scope guard, then dispatch to `resolver(tool_id, params)`.

    `resolver` is injected so callers can bind to Spec 022's `lookup()` (the
    real routing engine) or to a test double.  The guard itself is
    independent of the routing engine.
    """
    assert set(MINISTRY_TOOL_PREFIX.values()) == set(MINISTRY_CODES), (
        "MINISTRY_TOOL_PREFIX must cover all four Phase 1 MinistryCodes"
    )
    check = check_ministry_scope(
        tool_id, memdir_root=memdir_root, scope_override=scope_override
    )
    if isinstance(check, MinistryOptOutRefusal):
        raise check
    return await resolver(tool_id, params)
