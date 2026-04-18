# SPDX-License-Identifier: Apache-2.0
"""T038 — Lint test: no CA / private-key material in src/ or docs/.

SC-006 (AGENTS.md hard rule + Constitution §II): private key files
(.pem private-half, .p12, .pfx) MUST NOT appear under src/ or docs/,
except in the explicit allow-list for recorded test fixtures:
  docs/mock/npki_crypto/fixtures/*

Uses pathlib + re only (no subprocess). This is a repo-level lint gate that
runs in CI on every PR.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parents[3]

# Directories to scan.
_SCAN_ROOTS: list[Path] = [
    _REPO_ROOT / "src",
    _REPO_ROOT / "docs",
]

# Allow-listed prefixes (relative to repo root). Files under these paths are
# exempt from the private-key check (fixture-only cryptographic test data).
_ALLOWLIST_PREFIXES: tuple[str, ...] = (str(Path("docs") / "mock" / "npki_crypto" / "fixtures"),)

# Extensions that indicate private-key / PKCS#12 / PFX material.
_FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset({".p12", ".pfx"})

# Regex to detect PEM private-key headers inside text files
# (matches both PKCS#8 and traditional RSA/EC key headers).
_PEM_PRIVATE_RE = re.compile(r"-----BEGIN (?:RSA |EC |ENCRYPTED |)PRIVATE KEY-----")


def _is_allowlisted(path: Path) -> bool:
    """Return True if the file is in an allow-listed directory."""
    try:
        rel = path.relative_to(_REPO_ROOT)
    except ValueError:
        return False
    rel_str = str(rel)
    return any(rel_str.startswith(prefix) for prefix in _ALLOWLIST_PREFIXES)


def _iter_files(*roots: Path) -> Iterator[Path]:
    """Yield all files under the given root directories (recursively)."""
    for root in roots:
        if not root.exists():
            continue
        yield from (p for p in root.rglob("*") if p.is_file())


def _collect_violations() -> list[tuple[str, str]]:
    """Return list of (relative_path, reason) for all violations found."""
    violations: list[tuple[str, str]] = []

    for path in _iter_files(*_SCAN_ROOTS):
        if _is_allowlisted(path):
            continue

        # 1. Extension check.
        if path.suffix.lower() in _FORBIDDEN_EXTENSIONS:
            rel = path.relative_to(_REPO_ROOT)
            violations.append((str(rel), f"forbidden extension {path.suffix!r}"))
            continue

        # 2. PEM private-key header inside text files.
        #    Skip binary files silently.
        try:
            content = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, PermissionError):
            # Binary file or unreadable — skip PEM check.
            continue

        if _PEM_PRIVATE_RE.search(content):
            rel = path.relative_to(_REPO_ROOT)
            violations.append((str(rel), "contains PEM private-key header (SC-006 violation)"))

    return violations


# Pre-collect so the parametrize list is available at collection time.
_VIOLATIONS = _collect_violations()


@pytest.mark.skipif(
    not _VIOLATIONS,
    reason="No CA / private-key material found — scan passed.",
)
@pytest.mark.parametrize("rel_path, reason", _VIOLATIONS)
def test_no_ca_material(rel_path: str, reason: str) -> None:
    pytest.fail(
        f"SC-006 violation: {rel_path!r} — {reason}.\n"
        "Remove private-key material from src/ and docs/. "
        "If this is a test fixture, move it to docs/mock/npki_crypto/fixtures/ "
        "and add the path to _ALLOWLIST_PREFIXES in this test."
    )


def test_scan_completed_without_violation() -> None:
    """Asserts that the CA-material scan found zero violations."""
    assert _VIOLATIONS == [], (
        f"SC-006: {len(_VIOLATIONS)} CA material violation(s) detected:\n"
        + "\n".join(f"  {p}: {r}" for p, r in _VIOLATIONS)
    )
