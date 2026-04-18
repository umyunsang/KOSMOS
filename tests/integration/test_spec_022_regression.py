# SPDX-License-Identifier: Apache-2.0
"""T028 — Spec 022 regression gate.

Runs the full Spec 022 test suite as a subprocess and asserts that all tests
pass after the Spec 031 five-primitive harness migration (SC-003).

Spec 022 tests live under ``tests/tools/`` (the canonical location; there is no
separate ``specs/022-mvp-main-tool/tests/`` directory).  If the path is ever
relocated, update ``_SPEC_022_TEST_PATH`` here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Resolve project root relative to this file to avoid CWD dependencies.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Spec 022 tests live in tests/tools/ — confirmed by searching for test files
# that exercise lookup, resolve_location, and the 4 seed adapters.
_SPEC_022_TEST_PATH = _PROJECT_ROOT / "tests" / "tools"


def test_spec_022_suite_passes() -> None:
    """Assert all Spec 022 tests pass without modification after Spec 031 migration.

    SC-003: Spec 022 test suite must be green on the Spec 031 branch.
    Invokes pytest as a subprocess so failures surface as a single assertion
    with the captured stdout/stderr for diagnosis.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(_SPEC_022_TEST_PATH),
            "-q",
            "--tb=short",
        ],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )

    # Print output regardless of outcome so pytest -v shows context on CI.
    if result.stdout:
        print("\n--- Spec 022 pytest stdout ---\n", result.stdout)
    if result.stderr:
        print("\n--- Spec 022 pytest stderr ---\n", result.stderr)

    assert result.returncode == 0, (
        f"Spec 022 regression FAILED (exit {result.returncode}).\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )
