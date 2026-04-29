# SPDX-License-Identifier: Apache-2.0
"""Local conftest for tests/unit/tools/.

Background: ``kosmos/tools/mock/__init__.py`` eagerly imports Phase 4B submit
mock modules (``submit_module_gov24_minwon``, ``submit_module_hometax_taxreturn``,
``submit_module_public_mydata_action``) when any ``kosmos.tools.mock.*`` submodule
is imported. Those Phase 4B modules currently have a validation bug —
``published_tier_minimum="simple_auth_module_aal2"`` is not a valid ``PublishedTier``
literal — so importing any submodule of ``kosmos.tools.mock`` causes a
``pydantic.ValidationError`` at module collection time.

This conftest works around the issue for T028/T029 (lookup mock tests) by
temporarily stubbing the broken modules ONLY for the duration of the
``mock/__init__.py`` import, then removing the stubs so that tests that
specifically test those modules (``test_mock_submit_module_*.py``) can still
import the real modules later.

Safe to remove once Phase 4B T024 fixes ``published_tier_minimum`` in
``submit_module_gov24_minwon.py``.
"""

from __future__ import annotations

import sys
import types


def _temporarily_stub_broken_submit_modules() -> None:
    """Temporarily add empty stubs for broken Phase 4B submit modules.

    This allows ``kosmos/tools/mock/__init__.py`` to complete its import
    without crashing on the invalid ``AdapterRegistration`` construction in the
    Phase 4B submit adapters.

    The stubs are removed from sys.modules immediately after use so that
    tests that directly import these modules (``test_mock_submit_module_*.py``)
    still see the real module when they perform ``from kosmos.tools.mock.X import Y``.
    """
    _broken = [
        "kosmos.tools.mock.submit_module_gov24_minwon",
        "kosmos.tools.mock.submit_module_hometax_taxreturn",
        "kosmos.tools.mock.submit_module_public_mydata_action",
    ]

    # Only stub modules that are NOT already successfully imported.
    stubs_added: list[str] = []
    for name in _broken:
        if name not in sys.modules:
            try:
                __import__(name)
            except Exception:
                stub = types.ModuleType(name)
                sys.modules[name] = stub
                stubs_added.append(name)

    # Now import kosmos.tools.mock (the package __init__.py) if not already done.
    if "kosmos.tools.mock" not in sys.modules:
        try:
            import kosmos.tools.mock  # noqa: F401
        except Exception:
            pass  # Best-effort; lookup modules don't depend on __init__ exports.

    # Remove the stubs so later direct imports of those modules still work.
    for name in stubs_added:
        sys.modules.pop(name, None)


# Run the stub dance once at conftest load time (before any tests in this
# directory are collected). After this point, importing
# ``kosmos.tools.mock.lookup_module_hometax_simplified`` will trigger
# ``kosmos/tools/mock/__init__.py`` which is now already in sys.modules
# (cached from the stub dance), so it won't run again.
_temporarily_stub_broken_submit_modules()
