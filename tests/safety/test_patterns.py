# SPDX-License-Identifier: Apache-2.0
"""SoT regression: _PII_PATTERNS lives only in kosmos.safety._patterns.

Verifies FR-002: after the step3 refactor (T010), `_PII_PATTERNS` and
`PII_ACCEPTING_PARAMS` are defined in exactly one place. Any future copy-paste
that re-introduces a sibling definition fails this test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from kosmos.permissions.steps import step3_params
from kosmos.safety import _patterns

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"


def _grep_definition(symbol: str) -> list[str]:
    """Return every file under src/ where *symbol* appears at module level."""
    pattern = re.compile(rf"^{re.escape(symbol)}\s*[:=]", re.MULTILINE)
    hits: list[str] = []
    for path in SRC_DIR.rglob("*.py"):
        if pattern.search(path.read_text(encoding="utf-8")):
            hits.append(str(path))
    return hits


@pytest.mark.parametrize("symbol", ["_PII_PATTERNS", "PII_ACCEPTING_PARAMS"])
def test_single_module_level_definition(symbol: str) -> None:
    """Exactly one file under src/ defines the symbol at module level."""
    hits = _grep_definition(symbol)
    assert len(hits) == 1, f"{symbol} defined in {len(hits)} files: {hits}"
    assert hits[0].endswith("src/kosmos/safety/_patterns.py"), (
        f"{symbol} should live in kosmos.safety._patterns; found: {hits[0]}"
    )


def test_step3_imports_same_object_not_copy() -> None:
    """step3_params.py uses the canonical object; `is` identity holds."""
    assert step3_params._PII_PATTERNS is _patterns._PII_PATTERNS
    assert step3_params.PII_ACCEPTING_PARAMS is _patterns.PII_ACCEPTING_PARAMS


def test_step3_does_not_redeclare_patterns() -> None:
    """Source of step3_params.py has no `_PII_PATTERNS = ...` assignment."""
    source = (SRC_DIR / "kosmos" / "permissions" / "steps" / "step3_params.py").read_text()
    assert not re.search(r"^_PII_PATTERNS\s*[:=]", source, re.MULTILINE)
    assert not re.search(r"^PII_ACCEPTING_PARAMS\s*[:=]", source, re.MULTILINE)
