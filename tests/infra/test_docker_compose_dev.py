# SPDX-License-Identifier: Apache-2.0
"""T005 — CI-safe compose-schema validation test.

Shells out to ``docker compose -f docker-compose.dev.yml config --quiet``
and asserts exit code 0.  The test is skipped automatically when the
``docker`` binary is absent (e.g., on non-Docker CI runners or sandboxed
environments) so it never produces a hard failure on machines without Docker.

This test is NOT marked ``@pytest.mark.live`` — GitHub-hosted runners have
Docker pre-installed and should execute it in CI.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_FILE = _REPO_ROOT / "docker-compose.dev.yml"


def _docker_available() -> bool:
    """Return True if the ``docker`` binary (v2 Compose plugin) is on PATH."""
    return shutil.which("docker") is not None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _docker_available(),
    reason="docker binary not found; skipping compose-schema lint",
)
def test_docker_compose_dev_config_valid() -> None:
    """``docker compose config --quiet`` exits 0 for docker-compose.dev.yml."""
    assert _COMPOSE_FILE.exists(), f"Compose file not found: {_COMPOSE_FILE}"

    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(_COMPOSE_FILE),
            "config",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"docker compose config failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
