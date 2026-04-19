"""
tests/test_mock_scenario_split.py

Spec 031 US5 — T061: Enforce the mock/scenario split invariants.

Asserts:
  (a) docs/mock/ subdirectory count == 6
  (b) exact subdirectory names == {data_go_kr, omnione, barocert, mydata, npki_crypto, cbs}
  (c) docs/scenarios/*.md count == 3 (README.md is excluded)
  (d) each of the 3 scenario files contains the heading
      "## KOSMOS ↔ real system handoff point"
"""

from __future__ import annotations

import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
MOCK_DIR = REPO_ROOT / "docs" / "mock"
SCENARIOS_DIR = REPO_ROOT / "docs" / "scenarios"

EXPECTED_MOCK_NAMES = {"data_go_kr", "omnione", "barocert", "mydata", "npki_crypto", "cbs"}
EXPECTED_MOCK_COUNT = 6
EXPECTED_SCENARIO_COUNT = 3
HANDOFF_HEADING = "## KOSMOS ↔ real system handoff point"


# ---------------------------------------------------------------------------
# (a) + (b) — mock subdirectory count and exact names
# ---------------------------------------------------------------------------


def test_mock_subdirectory_count() -> None:
    """docs/mock/ must contain exactly 6 subdirectories."""
    subdirs = [p for p in MOCK_DIR.iterdir() if p.is_dir()]
    actual_names = {p.name for p in subdirs}
    assert len(subdirs) == EXPECTED_MOCK_COUNT, (
        f"Expected {EXPECTED_MOCK_COUNT} mock subdirectories, "
        f"found {len(subdirs)}: {sorted(actual_names)}"
    )


def test_mock_subdirectory_exact_names() -> None:
    """docs/mock/ must contain exactly the six named subdirectories."""
    subdirs = [p for p in MOCK_DIR.iterdir() if p.is_dir()]
    actual_names = {p.name for p in subdirs}
    assert actual_names == EXPECTED_MOCK_NAMES, (
        f"Mock subdirectory names mismatch.\n"
        f"  Expected: {sorted(EXPECTED_MOCK_NAMES)}\n"
        f"  Actual:   {sorted(actual_names)}\n"
        f"  Missing:  {sorted(EXPECTED_MOCK_NAMES - actual_names)}\n"
        f"  Extra:    {sorted(actual_names - EXPECTED_MOCK_NAMES)}"
    )


# ---------------------------------------------------------------------------
# (c) — scenario file count (README.md excluded)
# ---------------------------------------------------------------------------


def _scenario_files() -> list[pathlib.Path]:
    """Return all .md files in docs/scenarios/ except README.md."""
    return [p for p in SCENARIOS_DIR.glob("*.md") if p.name.lower() != "readme.md"]


def test_scenario_file_count() -> None:
    """docs/scenarios/ must contain exactly 3 scenario .md files (README.md excluded)."""
    files = _scenario_files()
    assert len(files) == EXPECTED_SCENARIO_COUNT, (
        f"Expected {EXPECTED_SCENARIO_COUNT} scenario files (excluding README.md), "
        f"found {len(files)}: {sorted(f.name for f in files)}"
    )


# ---------------------------------------------------------------------------
# (d) — each scenario file contains the handoff heading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario_file", _scenario_files())
def test_scenario_has_handoff_heading(scenario_file: pathlib.Path) -> None:
    """Each scenario file must contain '## KOSMOS ↔ real system handoff point'."""
    content = scenario_file.read_text(encoding="utf-8")
    assert HANDOFF_HEADING in content, (
        f"{scenario_file.name} is missing the required heading: '{HANDOFF_HEADING}'"
    )
