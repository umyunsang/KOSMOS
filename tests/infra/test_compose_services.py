# SPDX-License-Identifier: Apache-2.0
"""T006 — Compose service field assertions (CI-safe, no Docker required).

Parses ``docker-compose.dev.yml`` as YAML using the stdlib ``tomllib``
-style minimal fallback or ``yaml`` (via PyYAML, already a transitive dev
dep through ``langfuse``/opentelemetry extras) and asserts:

  (a) service ``otelcol`` exists
  (b) its ``image`` field is the manifest-list digest pin
  (c) ``depends_on.langfuse-web.condition == "service_healthy"``
  (d) the config volume mount ends with ``:ro``
  (e) only port 4318 is exposed (no 4317)
  (f) ``langfuse/langfuse`` image tag is pinned to ``3.35.0``
  (g) ``langfuse/langfuse-worker`` tag is pinned to ``3.35.0``

No Docker binary is required.  Requires PyYAML (a transitive dev dep) via
``pytest.importorskip`` — the entire module is skipped when PyYAML is absent,
ensuring the test never silently passes on a broken YAML parse.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_FILE = _REPO_ROOT / "docker-compose.dev.yml"

_OTELCOL_IMAGE_DIGEST = (
    "otel/opentelemetry-collector-contrib"
    "@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114"
)
_LANGFUSE_IMAGE_TAG = "3.35.0"
_LANGFUSE_WORKER_IMAGE_TAG = "3.35.0"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def compose_data() -> dict:
    """Return the parsed docker-compose.dev.yml as a dict."""
    yaml = pytest.importorskip("yaml", reason="PyYAML not installed; skipping compose assertions")
    raw = _COMPOSE_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(raw)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_otelcol_service_exists(compose_data: dict) -> None:
    """(a) Service ``otelcol`` is declared."""
    assert "otelcol" in compose_data.get("services", {}), (
        "Expected 'otelcol' service in docker-compose.dev.yml"
    )


def test_otelcol_image_pinned_to_digest(compose_data: dict) -> None:
    """(b) otelcol image uses manifest-list digest pin."""
    image = compose_data["services"]["otelcol"]["image"]
    assert image == _OTELCOL_IMAGE_DIGEST, (
        f"otelcol image must be digest-pinned.\n"
        f"  Expected: {_OTELCOL_IMAGE_DIGEST}\n"
        f"  Got:      {image}"
    )


def test_otelcol_depends_on_langfuse_web_healthy(compose_data: dict) -> None:
    """(c) otelcol depends_on langfuse-web with condition service_healthy."""
    depends_on = compose_data["services"]["otelcol"].get("depends_on", {})
    assert "langfuse-web" in depends_on, (
        "otelcol must declare depends_on.langfuse-web"
    )
    condition = depends_on["langfuse-web"].get("condition")
    assert condition == "service_healthy", (
        f"depends_on.langfuse-web.condition must be 'service_healthy', got: {condition!r}"
    )


def test_otelcol_config_volume_is_readonly(compose_data: dict) -> None:
    """(d) Config volume mount ends with ':ro'."""
    volumes: list[str] = compose_data["services"]["otelcol"].get("volumes", [])
    config_mounts = [v for v in volumes if "config.yaml" in str(v)]
    assert config_mounts, "No config.yaml volume mount found for otelcol"
    mount = str(config_mounts[0])
    assert mount.endswith(":ro"), (
        f"Config volume mount must end with ':ro' (fail-closed invariant).\n"
        f"  Got: {mount}"
    )


def test_otelcol_only_exposes_otlp_http_port(compose_data: dict) -> None:
    """(e) Only port 4318 is exposed; gRPC port 4317 must NOT be present."""
    ports: list[str] = compose_data["services"]["otelcol"].get("ports", [])
    ports_str = [str(p) for p in ports]

    # At least one port maps to container 4318
    assert any("4318" in p for p in ports_str), (
        f"otelcol must expose port 4318; ports found: {ports_str}"
    )

    # gRPC port 4317 must not appear
    assert not any("4317" in p for p in ports_str), (
        f"otelcol must NOT expose gRPC port 4317 (FR-003); ports found: {ports_str}"
    )


def test_langfuse_image_pinned(compose_data: dict) -> None:
    """(f) langfuse/langfuse image is pinned to 3.35.0 or a digest (no floating tag)."""
    image: str = compose_data["services"]["langfuse-web"]["image"]
    # Accept either an exact version tag (:3.35.0) or a digest pin (@sha256:...)
    has_version_tag = f":{_LANGFUSE_IMAGE_TAG}" in image
    has_digest_pin = "@sha256:" in image
    assert has_version_tag or has_digest_pin, (
        f"langfuse/langfuse image must be pinned to :{_LANGFUSE_IMAGE_TAG} or @sha256:...\n"
        f"  Got: {image}"
    )
    # Ensure it is not the old floating ':3' tag (single digit, no patch)
    assert not image.endswith(":3"), (
        f"langfuse/langfuse image must not use floating ':3' tag. Got: {image}"
    )


def test_langfuse_worker_image_pinned(compose_data: dict) -> None:
    """(g) langfuse/langfuse-worker image is pinned to 3.35.0 or a digest (no floating tag)."""
    image: str = compose_data["services"]["langfuse-worker"]["image"]
    # Accept either an exact version tag (:3.35.0) or a digest pin (@sha256:...)
    has_version_tag = f":{_LANGFUSE_WORKER_IMAGE_TAG}" in image
    has_digest_pin = "@sha256:" in image
    assert has_version_tag or has_digest_pin, (
        f"langfuse/langfuse-worker image must be pinned to "
        f":{_LANGFUSE_WORKER_IMAGE_TAG} or @sha256:...\n"
        f"  Got: {image}"
    )
    assert not image.endswith(":3"), (
        f"langfuse/langfuse-worker must not use floating ':3' tag. Got: {image}"
    )
