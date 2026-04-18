# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Five-Primitive Harness surface.

Exports the five primitive symbols that make up the main-tool surface:

- ``lookup``: read/search/fetch (re-exported from Spec 022, byte-identical).
- ``resolve_location``: geocoding (re-exported from Spec 022, byte-identical).
- ``submit``: write-transaction absorber (Spec 031, lands in Phase 3).
- ``subscribe``: CBS / REST pull / RSS 2.0 iterator (Spec 031, lands in Phase 3).
- ``verify``: delegation-only identity binding (Spec 031, lands in Phase 3).

T013 — ``lookup`` and ``resolve_location`` are the real Spec 022 coroutines
(not placeholders). The remaining three are Phase 1 placeholders that raise
``NotImplementedError`` until their user-story phases land.
"""

from __future__ import annotations

from kosmos.tools.lookup import lookup
from kosmos.tools.resolve_location import resolve_location

# T024 — replace Phase 1 placeholder with real submit dispatcher (Spec 031 US1)
from kosmos.primitives.submit import submit  # noqa: E402

__all__ = ["lookup", "resolve_location", "submit", "subscribe", "verify"]


def _placeholder(name: str):  # pragma: no cover - Phase 1 scaffold only
    raise NotImplementedError(
        f"kosmos.primitives.{name} is a Phase 1 placeholder. "
        "Real implementation lands in Spec 031 Phase 3+ tasks."
    )


async def subscribe(*args, **kwargs):  # pragma: no cover
    return _placeholder("subscribe")


async def verify(*args, **kwargs):  # pragma: no cover
    return _placeholder("verify")
