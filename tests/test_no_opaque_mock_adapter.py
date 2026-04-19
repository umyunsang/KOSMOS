"""
tests/test_no_opaque_mock_adapter.py

Spec 031 US5 — T062: Enforce that no adapter under src/kosmos/tools/mock/
imports or references any OPAQUE system identifier.

OPAQUE systems (must stay in docs/scenarios/, never in src/kosmos/tools/mock/):
  - gov24          (Government 24 submission)
  - kec            (Korea Electronic Certification Authority XML signature)
  - npki_portal_session  (NPKI portal session handshake)

The check scans all .py files under src/kosmos/tools/mock/ for any of these
strings as identifiers, import targets, or string literals.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
MOCK_ADAPTER_DIR = REPO_ROOT / "src" / "kosmos" / "tools" / "mock"

# These strings must not appear in any mock adapter file.
OPAQUE_IDENTIFIERS = [
    "gov24",
    "kec",
    "npki_portal_session",
]

# Pre-compiled patterns for each forbidden identifier.
# Python's built-in ``\b`` treats ``_`` as a word character, so ``\bkec\b``
# would fail to match ``kec_sign``. We deliberately want ``kec`` and any
# ``kec_<suffix>`` snake_case identifier to count as a violation, while still
# excluding benign substrings like ``echecker``. The custom look-around below
# uses ``[A-Za-z0-9]`` (no underscore) as the alphanumeric class, so ``_`` is
# treated as a boundary — catching ``kec_sign`` while leaving ``echecker``
# alone. ``npki_portal_session`` stays matched as a literal multi-token id.
_OPAQUE_PATTERNS = [
    (
        identifier,
        re.compile(r"(?<![A-Za-z0-9])" + re.escape(identifier) + r"(?![A-Za-z0-9])"),
    )
    for identifier in OPAQUE_IDENTIFIERS
]


def _mock_python_files() -> list[pathlib.Path]:
    """Return all .py files under src/kosmos/tools/mock/."""
    if not MOCK_ADAPTER_DIR.exists():
        return []
    return list(MOCK_ADAPTER_DIR.rglob("*.py"))


def test_mock_adapter_dir_exists_or_is_absent() -> None:
    """
    src/kosmos/tools/mock/ may not exist yet (no mock adapters implemented).
    If it exists, it must not contain OPAQUE system references.
    This test always passes — the parametrized tests below enforce the content rule.
    """
    # This test is a no-op sanity check: it documents intent rather than asserting.
    assert True


@pytest.mark.parametrize("mock_file", _mock_python_files())
def test_no_opaque_identifier_in_mock_adapter(mock_file: pathlib.Path) -> None:
    """
    No .py file under src/kosmos/tools/mock/ may import or reference
    an OPAQUE system identifier (gov24, kec, npki_portal_session).
    """
    content = mock_file.read_text(encoding="utf-8")
    violations: list[str] = []
    for identifier, pattern in _OPAQUE_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            violations.append(
                f"  Found forbidden identifier '{identifier}' "
                f"({len(matches)} occurrence(s)) in {mock_file.relative_to(REPO_ROOT)}"
            )
    assert not violations, (
        f"{mock_file.name} contains references to OPAQUE systems that must "
        f"only appear in docs/scenarios/, not in mock adapters:\n" + "\n".join(violations)
    )
