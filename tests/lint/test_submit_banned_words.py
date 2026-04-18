# SPDX-License-Identifier: Apache-2.0
"""T017 — SC-002 banned-word lint test for submit.py.

Scans ``src/kosmos/primitives/submit.py`` using stdlib ``re`` (no ripgrep
runtime dep) for the 10 domain-specific strings that are prohibited from
appearing in the submit primitive module.

Rationale: the submit envelope is domain-agnostic by design (FR-001..FR-003).
Domain vocabulary belongs exclusively in adapter modules, never in the main
primitive surface. This test enforces that contract statically.

SC-002 banned strings:
  check_eligibility, reserve_slot, subscribe_alert, pay, issue_certificate,
  submit_application, declared_income_krw, certificate_type,
  family_register, resident_register

Zero matches required.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_SUBMIT_MODULE = (
    pathlib.Path(__file__).parents[2]  # repo root
    / "src"
    / "kosmos"
    / "primitives"
    / "submit.py"
)

# SC-002 banned strings — domain vocabulary forbidden from the main envelope.
_BANNED_STRINGS = [
    "check_eligibility",
    "reserve_slot",
    "subscribe_alert",
    "pay",
    "issue_certificate",
    "submit_application",
    "declared_income_krw",
    "certificate_type",
    "family_register",
    "resident_register",
]


@pytest.fixture(scope="module")
def submit_source() -> str:
    """Load the submit.py source once for all parametrize cases."""
    assert _SUBMIT_MODULE.exists(), (
        f"submit.py not found at {_SUBMIT_MODULE}. "
        "T021 must create this file before T017 can pass."
    )
    return _SUBMIT_MODULE.read_text(encoding="utf-8")


@pytest.mark.parametrize("banned", _BANNED_STRINGS)
def test_banned_word_absent(submit_source: str, banned: str) -> None:
    """Assert the banned word does not appear as a standalone identifier in submit.py (SC-002).

    Uses ``\\b`` word boundaries so that ``pay`` matches ``pay`` / ``pay_v1``
    but not compound words like ``payment``, ``fines_pay``, or ``payco`` (which
    are legitimate English terms unrelated to the banned 8-verb surface).
    The intent of SC-002 is to exclude the *verb names* (pay, submit_application,
    etc.) as standalone identifiers or quoted strings — not every word that
    contains their characters.
    """
    pattern = re.compile(rf"\b{re.escape(banned)}\b")
    match = pattern.search(submit_source)
    assert match is None, (
        f"SC-002 violation: banned identifier {banned!r} found in "
        f"src/kosmos/primitives/submit.py at position {match.start() if match else 0}. "
        "Domain vocabulary (the 8 old verb names) must live in adapter modules, "
        "not the main primitive surface."
    )
