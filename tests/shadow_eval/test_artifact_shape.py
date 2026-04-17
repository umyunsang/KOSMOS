"""Artifact-shape tests for the shadow-eval battery JSON output (T020, Epic #467).

Verifies that the JSON artifact produced by running the shadow-eval battery
for both environments has the expected structure:

  - Top-level ``spans`` key holding a list.
  - Every span has ``attributes.deployment.environment`` present.
  - Every ``deployment.environment`` value is in ``{"main", "shadow"}``.
  - The twin-run principle holds: grouped-by-environment span counts are equal
    (FR-D04, FR-D03).

Expected RED state: ``tests/shadow_eval/battery.py`` does not exist until T040,
so collection raises ``ImportError`` and every test in this module fails.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Import the battery module — EXPECTED TO FAIL (ImportError) until T040.
# This is the deliberate RED gate mandated by the TDD rule in tasks.md.
# ---------------------------------------------------------------------------
from tests.shadow_eval import battery  # noqa: F401  # type: ignore[import]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_transport() -> httpx.MockTransport:
    """Return a minimal mock transport for artifact-shape tests."""

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "mock-0",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    return httpx.MockTransport(_handler)


def _build_artifact(tmp_path: Path) -> dict[str, Any]:
    """Run battery for both environments, merge spans, write JSON, return parsed dict.

    The battery CLI accepts ``--environment {main|shadow}`` and ``--out <path>``.
    We invoke it twice programmatically, collect both span lists into a single
    artifact at ``tmp_path/eval-report.json``, and return the parsed dict.
    """
    main_out = tmp_path / "main.json"
    shadow_out = tmp_path / "shadow.json"

    battery.run(environment="main", transport=_make_mock_transport(), out=main_out)
    battery.run(environment="shadow", transport=_make_mock_transport(), out=shadow_out)

    main_data: dict[str, Any] = json.loads(main_out.read_text(encoding="utf-8"))
    shadow_data: dict[str, Any] = json.loads(shadow_out.read_text(encoding="utf-8"))

    merged_spans: list[dict[str, Any]] = []
    merged_spans.extend(main_data.get("spans", []))
    merged_spans.extend(shadow_data.get("spans", []))

    artifact = {"spans": merged_spans}
    artifact_path = tmp_path / "eval-report.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")

    return artifact


# ---------------------------------------------------------------------------
# Shared fixture — build once per test invocation via tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture()
def artifact(tmp_path: Path) -> dict[str, Any]:
    """Return the merged artifact dict built by running the battery twice."""
    return _build_artifact(tmp_path)


# ---------------------------------------------------------------------------
# Test 1: top-level ``spans`` is a non-empty list
# ---------------------------------------------------------------------------


def test_artifact_has_top_level_spans_list(artifact: dict[str, Any]) -> None:
    """Merged artifact must have ``spans: list`` with at least two entries.

    Two entries is the absolute minimum: at least one span from the ``main``
    run and at least one from the ``shadow`` run (FR-D03, FR-D04).
    """
    assert "spans" in artifact, "artifact missing top-level 'spans' key"
    assert isinstance(artifact["spans"], list), "'spans' must be a list"
    assert len(artifact["spans"]) >= 2, (
        "'spans' must contain at least two entries (one per environment)"
    )


# ---------------------------------------------------------------------------
# Test 2: every span carries ``attributes.deployment.environment``
# ---------------------------------------------------------------------------


def test_every_span_has_deployment_environment_attribute(artifact: dict[str, Any]) -> None:
    """Each span dict must have ``attributes.deployment.environment`` present."""
    spans: list[dict[str, Any]] = artifact["spans"]
    assert spans, "no spans in artifact — cannot validate attribute presence"

    missing = [
        i
        for i, span in enumerate(spans)
        if "deployment.environment" not in span.get("attributes", {})
    ]
    assert not missing, (
        f"spans at indices {missing} are missing 'attributes.deployment.environment'"
    )


# ---------------------------------------------------------------------------
# Test 3: every ``deployment.environment`` value is in ``{"main", "shadow"}``
# ---------------------------------------------------------------------------


def test_deployment_environment_values_are_valid(artifact: dict[str, Any]) -> None:
    """Every ``deployment.environment`` value must be exactly ``"main"`` or ``"shadow"``."""
    valid_values = {"main", "shadow"}
    spans: list[dict[str, Any]] = artifact["spans"]
    assert spans, "no spans in artifact — cannot validate environment values"

    invalid = [
        (i, span["attributes"]["deployment.environment"])
        for i, span in enumerate(spans)
        if span.get("attributes", {}).get("deployment.environment") not in valid_values
    ]
    assert not invalid, (
        f"spans with invalid deployment.environment values: {invalid}. Allowed: {valid_values}"
    )


# ---------------------------------------------------------------------------
# Test 4: main and shadow span counts are equal (twin-run principle)
# ---------------------------------------------------------------------------


def test_main_and_shadow_counts_match(artifact: dict[str, Any]) -> None:
    """Grouped-by-environment span counts must be equal (FR-D04 twin-run principle).

    The battery runs an identical fixture-backed input set for both environments.
    Therefore the number of spans tagged ``main`` must equal those tagged ``shadow``.
    """
    spans: list[dict[str, Any]] = artifact["spans"]
    assert spans, "no spans in artifact — cannot compare environment counts"

    counts: Counter[str] = Counter(
        span["attributes"]["deployment.environment"]
        for span in spans
        if "deployment.environment" in span.get("attributes", {})
    )

    assert "main" in counts, "no spans tagged deployment.environment=main"
    assert "shadow" in counts, "no spans tagged deployment.environment=shadow"
    assert counts["main"] == counts["shadow"], (
        f"twin-run span count mismatch: main={counts['main']}, shadow={counts['shadow']}. "
        "Both environments must process identical battery inputs."
    )
