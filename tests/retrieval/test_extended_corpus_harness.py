# SPDX-License-Identifier: Apache-2.0
"""Extended-corpus harness test — T030 (spec 026, US3 P2).

Tests that ``run_extended_gate()`` in ``kosmos.eval.retrieval``:

1. Emits ``sc_01_status: "PENDING_#22"`` with a machine-readable
   ``sc_01_reason`` when the registry has only the 4 seed adapters (either
   because ``registry_size < 8`` or because every tool_id starts with a
   seed-adapter prefix).

2. Preserves ALL existing baseline schema fields that ``test_retrieval_gate.py``
   depends on — adding new keys never removes existing ones.

Uses a ``tmp_path`` fixture to write a minimal synthetic
``retrieval_queries.yaml`` with only ``koroad_*`` expected_tool_ids (still
exercises the 4-adapter registry, just a smaller corpus).  No changes to the
committed ``eval/`` directory are made.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Baseline schema fields required by test_retrieval_gate.py
# ---------------------------------------------------------------------------

_BASELINE_FIELDS: frozenset[str] = frozenset(
    {
        "total_queries",
        "recall_at_1",
        "recall_at_5",
        "per_adapter",
        "registry_size",
        "warnings",
        "timestamp",
    }
)

# The synthetic corpus targets koroad only so the registry is kept at 4 adapters
# (below the _SC01_MIN_REGISTRY_SIZE=8 threshold), reliably triggering PENDING_#22.
_SYNTHETIC_YAML_CONTENT = """\
version: 1
queries:
  - id: SQ001
    query: "교통사고 위험지역 알려줘"
    expected_tool_id: koroad_accident_hazard_search
    notes: "Synthetic — koroad only"
  - id: SQ002
    query: "traffic accident hotspots in Seoul"
    expected_tool_id: koroad_accident_hazard_search
    notes: "Synthetic — koroad only"
  - id: SQ003
    query: "사고다발구역 확인"
    expected_tool_id: koroad_accident_hazard_search
    notes: "Synthetic — koroad only"
  - id: SQ004
    query: "도로 위험지점 조회"
    expected_tool_id: koroad_accident_hazard_search
    notes: "Synthetic — koroad only"
"""


@pytest.fixture(scope="module")
def synthetic_queries_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write a minimal synthetic queries YAML to a temporary directory."""
    tmp = tmp_path_factory.mktemp("harness_queries")
    path = tmp / "retrieval_queries_synthetic.yaml"
    path.write_text(_SYNTHETIC_YAML_CONTENT, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def seed_registry():
    """Build a ToolRegistry with only the 4 seed adapters (registry_size == 4)."""
    from kosmos.eval.retrieval import _build_registry

    registry, _ = _build_registry()
    return registry


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestExtendedCorpusHarness:
    """run_extended_gate() emits PENDING_#22 when Epic #22 has not landed."""

    def test_sc01_status_is_pending(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """SC-01 status must be PENDING_#22 with a 4-adapter registry.

        The harness is invoked with backend='hybrid' and the synthetic
        4-koroad-query corpus.  Because the registry has only 4 seed adapters
        (all starting with seed prefixes and registry_size < 8), the function
        MUST return sc_01_status='PENDING_#22'.
        """
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        assert report.get("sc_01_status") == "PENDING_#22", (
            f"Expected sc_01_status='PENDING_#22', got: {report.get('sc_01_status')!r}. "
            f"Full report keys: {list(report.keys())}"
        )

    def test_sc01_reason_is_machine_readable(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """sc_01_reason must mention registry_size < 8 or Phase-3 adapter heuristic."""
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        reason: str = report.get("sc_01_reason", "")
        assert reason, "sc_01_reason must be a non-empty string when status is PENDING_#22"

        # The reason must reference one of the two heuristics used by _compute_sc01_status.
        registry_size_mention = "registry_size < 8" in reason
        phase3_mention = "Phase-3 adapter" in reason or "awaiting #22" in reason
        assert registry_size_mention or phase3_mention, (
            f"sc_01_reason does not mention registry_size < 8 or Phase-3-adapter "
            f"heuristic. Got: {reason!r}"
        )

    def test_baseline_schema_fields_preserved(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """All fields required by test_retrieval_gate.py must still be present.

        New fields (sc_01_status, sc_01_reason, sc_02_status) are ADDITIVE —
        they must not replace or remove any existing field.
        """
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        missing = _BASELINE_FIELDS - set(report.keys())
        assert not missing, (
            f"run_extended_gate() dropped required baseline fields: {sorted(missing)}"
        )

    def test_baseline_field_types(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """Baseline field types must match the existing schema contract."""
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        assert isinstance(report["total_queries"], int), "total_queries must be int"
        assert isinstance(report["recall_at_1"], float), "recall_at_1 must be float"
        assert isinstance(report["recall_at_5"], float), "recall_at_5 must be float"
        assert isinstance(report["per_adapter"], dict), "per_adapter must be dict"
        assert isinstance(report["registry_size"], int), "registry_size must be int"
        assert isinstance(report["warnings"], list), "warnings must be list"
        assert isinstance(report["timestamp"], str), "timestamp must be str"

    def test_new_sc_fields_present(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """New SC-status fields must be present in the extended report."""
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        assert "sc_01_status" in report, "sc_01_status must be in extended report"
        assert "sc_01_reason" in report, "sc_01_reason must be in extended report"
        assert "sc_02_status" in report, "sc_02_status must be in extended report"

    def test_recall_values_in_range(
        self,
        synthetic_queries_path: Path,
        seed_registry: object,
    ) -> None:
        """Recall values must remain in [0.0, 1.0] under the extended gate."""
        from kosmos.eval.retrieval import run_extended_gate

        report = run_extended_gate(
            backend="hybrid",
            queries_path=synthetic_queries_path,
            report_path=None,
            registry=seed_registry,
        )

        assert 0.0 <= report["recall_at_1"] <= 1.0, (
            f"recall_at_1 out of range: {report['recall_at_1']}"
        )
        assert 0.0 <= report["recall_at_5"] <= 1.0, (
            f"recall_at_5 out of range: {report['recall_at_5']}"
        )
