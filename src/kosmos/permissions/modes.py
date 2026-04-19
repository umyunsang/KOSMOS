# SPDX-License-Identifier: Apache-2.0
"""Permission mode spectrum — Spec 033 FR-A01..A05.

Ports Claude Code 2.1.88 ``PermissionMode`` external modes to the KOSMOS
citizen-API harness. Internal CC modes (``auto``, ``bubble``) are excluded
per spec.md Assumption #8 — they are tied to CC's TRANSCRIPT_CLASSIFIER
growth-book feature and have no citizen-domain equivalent.

Reference: ``src/utils/permissions/PermissionMode.ts`` (CC 2.1.88 sourcemap)
           ``src/utils/permissions/getNextPermissionMode.ts`` (CC 2.1.88 sourcemap)
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# PermissionMode type alias
# ---------------------------------------------------------------------------

PermissionMode = Literal["default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"]
"""5-mode external permission spectrum.

| Value               | Description                                                   |
|---------------------|---------------------------------------------------------------|
| ``default``         | Ask on every call unless a persistent ``allow`` rule exists.  |
| ``plan``            | Dry-run — no side effects permitted (observationally pure).   |
| ``acceptEdits``     | Auto-approve reversible AAL1/public reads; still asks others. |
| ``bypassPermissions`` | Auto-approve all except killswitch gates (irreversible, etc.) |
| ``dontAsk``         | Auto-approve pre-saved allow-list; fallback to default.       |

Invariant M1: Killswitch runs BEFORE mode evaluation. Mode cannot widen the
killswitch set. See ``contracts/mode-transition.contract.md § 5``.

Invariant M3: Mode is session-scoped. It never persists across restarts.
"""

# ---------------------------------------------------------------------------
# Shift+Tab fast-cycle (low/mid-risk modes only)
# ---------------------------------------------------------------------------

# High-risk modes are deliberately EXCLUDED from the fast cycle.
# Reaching bypassPermissions / dontAsk requires an explicit slash command
# + confirmation dialog (Invariant S1: escape hatch always available).
_SHIFT_TAB_CYCLE: tuple[PermissionMode, PermissionMode, PermissionMode] = (
    "default",
    "plan",
    "acceptEdits",
)

_SHIFT_TAB_NEXT: dict[PermissionMode, PermissionMode] = {
    "default": "plan",
    "plan": "acceptEdits",
    "acceptEdits": "default",
    # High-risk escape hatch: both return directly to default (Invariant S1).
    "bypassPermissions": "default",
    "dontAsk": "default",
}

# ---------------------------------------------------------------------------
# Adjacency table — full state machine
# ---------------------------------------------------------------------------

# Frozenset of valid (from_mode, to_mode) transitions.
# High-risk transitions (→ bypassPermissions or → dontAsk) always require
# explicit slash command + confirmation; they are listed here for completeness
# but the confirmation requirement is enforced in the TUI layer, not here.
MODE_ADJACENCY: frozenset[tuple[PermissionMode, PermissionMode]] = frozenset(
    {
        # Shift+Tab cycle
        ("default", "plan"),
        ("plan", "acceptEdits"),
        ("acceptEdits", "default"),
        # Shift+Tab escape hatch from high-risk modes
        ("bypassPermissions", "default"),
        ("dontAsk", "default"),
        # /permissions default resets from any mode
        ("plan", "default"),
        ("acceptEdits", "default"),
        # /permissions bypass (requires confirmation)
        ("default", "bypassPermissions"),
        ("plan", "bypassPermissions"),
        ("acceptEdits", "bypassPermissions"),
        ("dontAsk", "bypassPermissions"),
        # /permissions dontAsk (requires confirmation)
        ("default", "dontAsk"),
        ("plan", "dontAsk"),
        ("acceptEdits", "dontAsk"),
        ("bypassPermissions", "dontAsk"),
        # Self-transition (no-op) — /permissions default while already default
        ("default", "default"),
        ("bypassPermissions", "bypassPermissions"),
        ("dontAsk", "dontAsk"),
    }
)


def next_mode_shift_tab(current: PermissionMode) -> PermissionMode:
    """Return the next mode when the user presses Shift+Tab.

    Fast cycle: ``default → plan → acceptEdits → default → …``

    High-risk escape hatch:
    - ``bypassPermissions`` → ``default``  (Invariant S1)
    - ``dontAsk``           → ``default``  (Invariant S1)

    Args:
        current: The current permission mode.

    Returns:
        The mode to transition to.
    """
    return _SHIFT_TAB_NEXT[current]


def is_high_risk(mode: PermissionMode) -> bool:
    """Return True if *mode* is a high-risk mode requiring explicit activation.

    High-risk modes (``bypassPermissions``, ``dontAsk``) are excluded from the
    Shift+Tab fast cycle.  They require ``/permissions bypass`` or
    ``/permissions dontAsk`` plus an explicit confirmation dialog
    (contracts/mode-transition.contract.md § 6, Invariant UI2).
    """
    return mode in {"bypassPermissions", "dontAsk"}
