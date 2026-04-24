"""Permission-tier derivation from existing GovAPITool fields.

Single source of truth consumed by:
- TUI permission gauntlet (UI-C C1 layer color rendering — green/orange/red)
- Audit ledger entry interpretation (Spec 024)
- Permission-mode transitions (Spec 033 Shift+Tab)
"""

from typing import Literal

# AALLevel is re-exported via ``kosmos.security.audit`` (the canonical source).
# Import from there directly to satisfy mypy's "explicitly exported" check.
from kosmos.security.audit import AALLevel  # Literal["public","AAL1","AAL2","AAL3"]


def compute_permission_tier(
    auth_level: AALLevel,
    is_irreversible: bool,
) -> Literal[1, 2, 3]:
    """Derive the UI-C permission layer from auth_level + irreversibility.

    Mapping (per spec FR-011 + research.md § 1.3 / Q3 clarification):
      public, AAL1                 → 1  (green ⓵)
      AAL2                         → 2  (orange ⓶)
      AAL3                         → 3  (red ⓷)
      is_irreversible=True         → 3  (overrides AAL mapping)

    Preserves Spec 025 v6 (auth_type, auth_level) invariant — does not read
    auth_type and therefore cannot drift from the v6 allow-list.
    """
    if is_irreversible:
        return 3
    if auth_level in ("public", "AAL1"):
        return 1
    if auth_level == "AAL2":
        return 2
    if auth_level == "AAL3":
        return 3
    raise ValueError(f"Unknown auth_level: {auth_level!r}")
