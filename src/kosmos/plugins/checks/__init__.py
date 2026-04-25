# SPDX-License-Identifier: Apache-2.0
"""Plugin validation check modules (Q1–Q10).

Each Q-module exports check functions named ``check_<id_suffix>`` where
``id_suffix`` is the lowercased part after ``Q<n>-``. Example: the
``Q1-PYV2`` row in ``checklist_manifest.yaml`` resolves to
``kosmos.plugins.checks.q1_schema:check_pyv2``.

Every check accepts a :class:`CheckContext` and returns a
:class:`CheckOutcome`. The workflow driver iterates over rows in
``tests/fixtures/plugin_validation/checklist_manifest.yaml`` and looks
up the implementation via ``check_implementation`` (dotted path), so
adding a new row + writing a new function is the only authoring step
— no hand-edited workflow YAML branches.
"""

from __future__ import annotations

from kosmos.plugins.checks.framework import (
    CheckContext,
    CheckOutcome,
    failed,
    passed,
    resolve_check,
    run_all_checks,
)

__all__ = [
    "CheckContext",
    "CheckOutcome",
    "failed",
    "passed",
    "resolve_check",
    "run_all_checks",
]
