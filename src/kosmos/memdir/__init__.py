"""Memdir USER tier persistence for citizen onboarding (Epic H #1302).

Re-exports PIPA consent and ministry-scope schemas plus their atomic readers /
writers. Populated by Phase 4 (T019) and Phase 5 (T026); this module exists
from Phase 1 (T001) so that downstream imports compile against a stable path.
"""

from __future__ import annotations

__all__: list[str] = []
