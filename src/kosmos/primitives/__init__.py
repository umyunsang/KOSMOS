# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Five-Primitive Harness surface.

Exports the five primitive symbols that make up the main-tool surface:

- ``lookup``: read/search/fetch (re-exported from Spec 022, byte-identical).
- ``resolve_location``: geocoding (re-exported from Spec 022, byte-identical).
- ``submit``: write-transaction absorber (Spec 031 US1, T024).
- ``subscribe``: CBS / REST pull / RSS 2.0 iterator (Spec 031 US3, T057).
- ``verify``: delegation-only identity binding (Spec 031 US2, T042).

All five primitives are now real implementations — the Phase 1 scaffold
placeholders have been fully replaced by their user-story coroutines.
"""

from __future__ import annotations

from kosmos.primitives.submit import submit
from kosmos.primitives.subscribe import subscribe
from kosmos.primitives.verify import verify
from kosmos.tools.lookup import lookup
from kosmos.tools.resolve_location import resolve_location

__all__ = ["lookup", "resolve_location", "submit", "subscribe", "verify"]
