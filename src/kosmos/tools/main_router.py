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
    CURRENT_SCOPE_VERSION,
    MINISTRY_CODES,
    MinistryCode,
    MinistryScopeAcknowledgment,
    latest_scope,
    opt_in_lookup,
)

__all__ = [
    "COMPOSITE_TOOL_MINISTRIES",
    "MINISTRY_TOOL_PREFIX",
    "MinistryOptOutRefusal",
    "check_ministry_scope",
    "ministries_for_composite",
    "ministry_for_tool",
    "ministry_korean_name",
    "resolve_with_scope_guard",
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

# Composite tools whose `tool_id` does NOT carry a single-ministry prefix but
# that fan out to multiple ministries under the hood.  Every ministry in the
# set must be opted-in for the composite call to proceed; one opted-out
# ministry refuses the whole call.  Extend this map when a new composite is
# registered in `src/kosmos/tools/register_all.py`.
COMPOSITE_TOOL_MINISTRIES: dict[str, frozenset[MinistryCode]] = {
    "road_risk_score": frozenset(("KOROAD", "KMA")),
}


def ministry_for_tool(tool_id: str) -> MinistryCode | None:
    """Resolve a tool_id to its owning ministry, or None if not ministry-bound.

    `tool_id` is case-folded before matching so that a mis-cased registration
    (e.g., `Koroad_...` or `KOROAD_...`) cannot evade the scope guard.
    Returns None for composite tools — callers must use
    `ministries_for_composite()` for those.
    """
    normalized = tool_id.casefold()
    for prefix, code in MINISTRY_TOOL_PREFIX.items():
        if normalized.startswith(prefix):
            return code
    return None


def ministries_for_composite(tool_id: str) -> frozenset[MinistryCode] | None:
    """Return the ministry fan-out set for a composite tool, or None.

    Composite tool IDs are matched case-sensitively against
    `COMPOSITE_TOOL_MINISTRIES` keys — the registry pins these IDs
    authoritatively, so no case normalisation is needed here.
    """
    return COMPOSITE_TOOL_MINISTRIES.get(tool_id)


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

    - Non-ministry tool                            → pass.
    - Composite tool with any opt-out ministry     → refusal (first-opt-out wins).
    - No scope record                              → refusal (fail-closed default).
    - Stale scope_version != CURRENT_SCOPE_VERSION → refusal (forces re-onboard).
    - Single-ministry opt-out                      → refusal.
    - Single-ministry opt-in                       → pass.
    """
    composite = ministries_for_composite(tool_id)
    ministry = ministry_for_tool(tool_id)
    if composite is None and ministry is None:
        return "pass"

    scope = scope_override
    if scope is None:
        scope = latest_scope(memdir_root / "user" / "ministry-scope")

    # Pick a representative ministry for the refusal message when the scope
    # record is missing / stale — use the first ministry in the composite
    # set (sorted for determinism) or the single ministry.  This ministry
    # appears in the citizen-facing Korean refusal copy.
    canonical: MinistryCode = (
        ministry if ministry is not None else sorted(composite)[0]  # type: ignore[arg-type]
    )

    if scope is None:
        return _build_refusal(canonical)
    if scope.scope_version != CURRENT_SCOPE_VERSION:
        return _build_refusal(canonical)

    # Composite: refuse if ANY fan-out ministry is opted out.
    if composite is not None:
        for needed in sorted(composite):
            if not opt_in_lookup(scope, needed):
                return _build_refusal(needed)
        return "pass"

    # Single-ministry: standard opt-in check.
    assert ministry is not None  # narrowed by earlier guard
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
    check = check_ministry_scope(tool_id, memdir_root=memdir_root, scope_override=scope_override)
    if isinstance(check, MinistryOptOutRefusal):
        raise check
    return await resolver(tool_id, params)
