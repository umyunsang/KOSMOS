"""Schema validation tests for .devcontainer/devcontainer.json (T022 / FR-B01..B04)."""

import json
from pathlib import Path

DEVCONTAINER_PATH = Path(__file__).parents[2] / ".devcontainer" / "devcontainer.json"


def _load() -> dict:
    with DEVCONTAINER_PATH.open() as f:
        return json.load(f)


def test_devcontainer_json_parses():
    """FR-B01: file exists and is valid JSON."""
    data = _load()
    assert isinstance(data, dict)


def test_image_pinned_to_python312():
    """FR-B01: image must be mcr.microsoft.com/devcontainers/python:3.12."""
    data = _load()
    assert data["image"] == "mcr.microsoft.com/devcontainers/python:3.12"


def test_uv_feature_present():
    """FR-B02: uv devcontainer feature must be listed."""
    data = _load()
    features = data.get("features", {})
    uv_keys = [k for k in features if "uv" in k.lower()]
    assert uv_keys, "uv feature not found in 'features'"


def test_post_create_command():
    """FR-B02: postCreateCommand must be 'uv sync'."""
    data = _load()
    assert data["postCreateCommand"] == "uv sync"


def test_forward_ports():
    """FR-B03: ports 4000 (LiteLLM) and 4318 (OTEL) must be forwarded."""
    data = _load()
    ports = data.get("forwardPorts", [])
    assert 4000 in ports
    assert 4318 in ports


def test_vscode_extensions():
    """FR-B04: required VS Code extensions must be listed."""
    data = _load()
    extensions = data.get("customizations", {}).get("vscode", {}).get("extensions", [])
    assert "ms-python.python" in extensions
    assert "ms-python.vscode-pylance" in extensions


def test_python_interpreter_path():
    """FR-B04: defaultInterpreterPath must point to .venv in workspaces mount."""
    data = _load()
    settings = data.get("customizations", {}).get("vscode", {}).get("settings", {})
    assert settings.get("python.defaultInterpreterPath") == "/workspaces/KOSMOS/.venv/bin/python"


def test_remote_user():
    """FR-B04: remoteUser must be 'vscode'."""
    data = _load()
    assert data.get("remoteUser") == "vscode"


def test_name_present():
    """Devcontainer must have an identifiable name."""
    data = _load()
    assert data.get("name"), "devcontainer 'name' field is missing or empty"
