"""Structural contract tests for .devcontainer/devcontainer.json (T022, Epic #467).

These tests validate the devcontainer configuration against the requirements
defined in spec 026-cicd-prompt-registry:
  (a) image targets microsoft/devcontainers/python:3.12
  (b) features includes a uv feature reference
  (c) postCreateCommand is exactly "uv sync"
  (d) forwardPorts contains 4000 and 4318
  (e) no host-required env vars beyond those declared in .env.example (FR-B04)

Expected state at authoring time (RED): .devcontainer/devcontainer.json does
not exist.  Every test in this module will raise FileNotFoundError until T036
creates the file.  That is the intended TDD RED phase.
"""

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEVCONTAINER_PATH = _REPO_ROOT / ".devcontainer" / "devcontainer.json"
_ENV_EXAMPLE_PATH = _REPO_ROOT / ".env.example"


# ---------------------------------------------------------------------------
# JSONC parser (stdlib-only: re + json)
# ---------------------------------------------------------------------------


def _load_jsonc(path: Path) -> dict:
    """Parse a JSON-with-comments file using stdlib re and json.

    Strips:
      - // single-line comments
      - /* */ block comments
      - trailing commas before } or ]
    Raises FileNotFoundError if *path* does not exist.
    """
    text = path.read_text(encoding="utf-8")
    # Strip // line comments (do not touch URLs inside strings — acceptable
    # simplification for devcontainer files that rarely embed raw URLs in
    # string values after a //)
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    # Strip /* */ block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Strip trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# Module-level fixture: parse the config once
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def config() -> dict:
    """Load and parse .devcontainer/devcontainer.json.

    FileNotFoundError is the expected exception in the RED phase (before T036).
    """
    return _load_jsonc(_DEVCONTAINER_PATH)


# ---------------------------------------------------------------------------
# Fixture: allowed env var keys from .env.example
# ---------------------------------------------------------------------------


def _parse_env_example_keys(path: Path) -> set[str]:
    """Return the set of non-commented, non-empty variable names from an env file."""
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Lines may optionally be commented out with a leading #; skip those.
        # Accept KEY=value and KEY= (empty value)
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key:
                keys.add(key)
    return keys


# ---------------------------------------------------------------------------
# Test 1 — image field
# ---------------------------------------------------------------------------


def test_devcontainer_image_is_microsoft_python_312(config: dict) -> None:
    """Assert image starts with the Microsoft devcontainers Python 3.12 base."""
    image: str = config["image"]
    assert image.startswith("mcr.microsoft.com/devcontainers/python:3.12"), (
        f"Expected image to start with 'mcr.microsoft.com/devcontainers/python:3.12', "
        f"got: {image!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — features include uv
# ---------------------------------------------------------------------------


def test_devcontainer_features_include_uv(config: dict) -> None:
    """Assert that at least one features key references a uv feature (case-insensitive)."""
    features: dict = config.get("features", {})
    assert features, "devcontainer.json 'features' must not be empty"
    matching_keys = [k for k in features if "uv" in k.lower()]
    assert matching_keys, (
        f"No uv feature found in 'features'. Keys present: {list(features.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 3 — postCreateCommand
# ---------------------------------------------------------------------------


def test_postcreatecommand_is_uv_sync(config: dict) -> None:
    """Assert postCreateCommand is exactly 'uv sync'."""
    cmd = config.get("postCreateCommand")
    assert cmd == "uv sync", f"Expected postCreateCommand == 'uv sync', got: {cmd!r}"


# ---------------------------------------------------------------------------
# Test 4 — forwardPorts
# ---------------------------------------------------------------------------


def test_forwardports_includes_4000_and_4318(config: dict) -> None:
    """Assert forwardPorts contains both 4000 (app) and 4318 (OTLP/HTTP collector)."""
    ports: list = config.get("forwardPorts", [])
    assert 4000 in ports, f"4000 missing from forwardPorts: {ports}"
    assert 4318 in ports, f"4318 missing from forwardPorts: {ports}"


# ---------------------------------------------------------------------------
# Test 5 — no host-required env vars beyond .env.example (FR-B04)
# ---------------------------------------------------------------------------


def test_no_host_env_vars_beyond_env_example(config: dict) -> None:
    """Assert remoteEnv/containerEnv keys are a subset of those in .env.example.

    FR-B04: the devcontainer must not require host env vars that are not
    declared in .env.example, preventing silent misconfigurations in fresh
    clones.

    If .env.example does not exist yet, the test is skipped with an
    explanatory message so the RED suite remains well-defined.
    """
    if not _ENV_EXAMPLE_PATH.exists():
        pytest.skip(
            ".env.example not present — cannot validate FR-B04 env var constraint. "
            "Create .env.example listing all required KOSMOS_* variables before "
            "enabling this assertion."
        )

    allowed_keys = _parse_env_example_keys(_ENV_EXAMPLE_PATH)

    # Collect all env var keys declared in the devcontainer config
    devcontainer_env_keys: set[str] = set()
    for env_section in ("remoteEnv", "containerEnv"):
        section: dict = config.get(env_section, {})
        devcontainer_env_keys.update(section.keys())

    undeclared = devcontainer_env_keys - allowed_keys
    assert not undeclared, (
        f"devcontainer declares env vars not present in .env.example (FR-B04). "
        f"Add them to .env.example or remove them from devcontainer.json: "
        f"{sorted(undeclared)}"
    )
