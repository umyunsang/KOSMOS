# SPDX-License-Identifier: Apache-2.0
"""T037 — Grep-style assertion: verify.py must contain zero signing / CA / VC-issuer code.

FR-009 (harness-not-reimplementation): KOSMOS is a delegation-only harness.
The verify primitive MUST NOT contain any of the following:
  - The string "sign" (signing operations)
  - The string "BEGIN PRIVATE KEY" (embedded PEM private key)
  - The string "issue_credential" (VC-issuer logic)

Uses pathlib + re only (no subprocess).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SRC_ROOT = Path(__file__).parents[4] / "src"
_VERIFY_MODULE = _SRC_ROOT / "kosmos" / "primitives" / "verify.py"

# Forbidden patterns (FR-009).  Case-sensitive; any single match = fail.
_FORBIDDEN: list[tuple[str, str]] = [
    # pattern, human-readable label
    (r"(?<![a-zA-Z])sign(?![a-zA-Z])", "signing operation ('sign' token)"),
    (r"BEGIN PRIVATE KEY", "embedded PEM private key material"),
    (r"issue_credential", "VC-issuer function call"),
]


@pytest.fixture(scope="module")
def verify_source() -> str:
    assert _VERIFY_MODULE.exists(), f"verify.py not found at {_VERIFY_MODULE}"
    return _VERIFY_MODULE.read_text(encoding="utf-8")


@pytest.mark.parametrize("pattern, label", _FORBIDDEN)
def test_no_forbidden_pattern(verify_source: str, pattern: str, label: str) -> None:
    """Assert that the forbidden pattern does not appear in verify.py."""
    matches = re.findall(pattern, verify_source)
    assert not matches, (
        f"FR-009 violation: verify.py contains forbidden pattern for "
        f"{label!r} (pattern={pattern!r}). "
        f"KOSMOS is a harness — no CA/HSM/signing code is allowed here."
    )


def test_verify_module_is_readable(verify_source: str) -> None:
    """Sanity: file exists and is non-empty."""
    assert len(verify_source) > 100, "verify.py appears too short / empty"
