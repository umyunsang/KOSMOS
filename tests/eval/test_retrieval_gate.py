# SPDX-License-Identifier: Apache-2.0
"""Retrieval quality gate integration test — T037.

Runs the full eval harness against the committed 30-query set and asserts
recall@5 >= 0.80 when all 4 seed adapters are registered.

If only KOROAD is registered (Stage 2a), the test skips with a clear message.

No network calls are made — eval uses in-memory BM25 only.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_QUERIES_PATH = Path(__file__).parent.parent.parent / "eval" / "retrieval_queries.yaml"
_MIN_RECALL5_PASS = 0.80

# The 4 seed adapter IDs that must all be registered for a full eval run.
_ALL_SEED_IDS: frozenset[str] = frozenset(
    {
        "koroad_accident_hazard_search",
        "kma_forecast_fetch",
        "hira_hospital_search",
        "nmc_emergency_search",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_registry() -> tuple[object, object]:
    """Build the test registry using the eval harness registry builder.

    Delegates to ``kosmos.eval.retrieval._build_registry`` which registers
    each seed adapter individually and is resilient to partial availability.
    """
    from kosmos.eval.retrieval import _build_registry as eval_build_registry

    return eval_build_registry()


def _registered_ids(registry: object) -> frozenset[str]:
    """Return frozenset of all tool IDs in the registry."""
    from kosmos.tools.registry import ToolRegistry

    assert isinstance(registry, ToolRegistry)
    return frozenset(t.id for t in registry.all_tools())


# ---------------------------------------------------------------------------
# T037: Gate test
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestRetrievalGate:
    """Recall@5 gate against the committed 30-query eval set."""

    @pytest.fixture(scope="class")
    def registry_and_executor(self):
        """Build registry once for all tests in this class."""
        return _build_registry()

    def test_queries_yaml_exists(self) -> None:
        """The committed queries YAML file must exist."""
        assert _QUERIES_PATH.exists(), f"eval/retrieval_queries.yaml not found at {_QUERIES_PATH}"

    def test_queries_yaml_has_30_entries(self) -> None:
        """The queries YAML must contain exactly 30 queries."""
        import yaml

        with _QUERIES_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        queries = data.get("queries", [])
        assert len(queries) == 30, (
            f"Expected 30 queries in retrieval_queries.yaml, found {len(queries)}"
        )

    def test_recall_gate_with_available_adapters(
        self,
        registry_and_executor,
    ) -> None:
        """Run the full eval and assert recall@5 >= 0.80.

        Skips if fewer than all 4 seed adapters are registered (Stage 2a
        only has KOROAD; Stage 3 will add KMA/HIRA/NMC).
        """
        registry, _ = registry_and_executor
        registered = _registered_ids(registry)
        missing = _ALL_SEED_IDS - registered

        if missing:
            pytest.skip(
                f"Stage 2b teams have not registered HIRA/KMA/NMC yet. "
                f"Missing adapters: {sorted(missing)}. "
                "Re-run after Stage 3 lands all seed adapter registrations."
            )

        # All 4 adapters are registered — run the full eval
        import yaml

        from kosmos.eval.retrieval import _evaluate

        with _QUERIES_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        queries = data["queries"]

        report = asyncio.run(_evaluate(queries, registry))

        recall5 = report["recall_at_5"]
        assert recall5 >= _MIN_RECALL5_PASS, (
            f"recall@5 {recall5:.2%} is below the pass threshold of "
            f"{_MIN_RECALL5_PASS:.0%}. Per-adapter results: "
            f"{report['per_adapter']}"
        )

    def test_recall_gate_koroad_only_emits_warning(
        self,
        registry_and_executor,
    ) -> None:
        """When not all 4 adapters are registered, the harness emits a WARN.

        This test passes in Stage 2a (only KOROAD registered) by verifying
        the warnings list is non-empty and contains the registry-size notice.
        It becomes informational once all adapters are registered.
        """
        registry, _ = registry_and_executor
        registered = _registered_ids(registry)
        missing = _ALL_SEED_IDS - registered

        if not missing:
            # All adapters registered — no warning expected; skip this check.
            pytest.skip("All 4 seed adapters are registered; warning check is not applicable.")

        import yaml

        from kosmos.eval.retrieval import _evaluate

        with _QUERIES_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        queries = data["queries"]

        report = asyncio.run(_evaluate(queries, registry))

        # When adapters are missing, the harness must emit at least one warning.
        assert report["warnings"], (
            "Expected at least one warning when seed adapters are missing, "
            f"but got empty warnings list. Registry: {sorted(registered)}"
        )

    def test_report_has_required_fields(
        self,
        registry_and_executor,
    ) -> None:
        """The eval report must contain all required JSON schema fields."""
        registry, _ = registry_and_executor

        import yaml

        from kosmos.eval.retrieval import _evaluate

        with _QUERIES_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        queries = data["queries"]

        report = asyncio.run(_evaluate(queries, registry))

        required_fields = {
            "total_queries",
            "recall_at_1",
            "recall_at_5",
            "per_adapter",
            "registry_size",
            "warnings",
            "timestamp",
        }
        missing_fields = required_fields - set(report.keys())
        assert not missing_fields, f"Report is missing required fields: {missing_fields}"

    def test_report_values_are_in_range(
        self,
        registry_and_executor,
    ) -> None:
        """recall@1 and recall@5 must be in [0.0, 1.0]."""
        registry, _ = registry_and_executor

        import yaml

        from kosmos.eval.retrieval import _evaluate

        with _QUERIES_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        queries = data["queries"]

        report = asyncio.run(_evaluate(queries, registry))

        assert 0.0 <= report["recall_at_1"] <= 1.0, (
            f"recall_at_1 out of range: {report['recall_at_1']}"
        )
        assert 0.0 <= report["recall_at_5"] <= 1.0, (
            f"recall_at_5 out of range: {report['recall_at_5']}"
        )
        assert report["total_queries"] == 30
