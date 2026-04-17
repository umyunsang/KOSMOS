# SPDX-License-Identifier: Apache-2.0
"""RRF math unit test for HybridBackend (spec 026, T017).

Validates the Reciprocal Rank Fusion formula:
    fused = 1/(k + rank_bm25) + 1/(k + rank_dense)
at k=60 against competition-ranking semantics from Cormack, Clarke &
Buettcher, "Reciprocal Rank Fusion outperforms Condorcet and Individual
Rank Learning Methods", SIGIR 2009.

Standard competition ranking (1-2-2-4): tied documents share the lowest
rank among them; the next rank after a tie group skips accordingly.

Missing-from-one-list: rank = N + 1 where N is the retriever's list size.
All fused scores MUST be strictly positive.
"""

from __future__ import annotations

from kosmos.tools.retrieval.hybrid import HybridBackend  # noqa: F401


class _MockBM25:
    """Deterministic stub mimicking the BM25Backend Retriever surface."""

    def __init__(self, scores: list[tuple[str, float]]) -> None:
        self._scores = scores

    def rebuild(self, corpus: dict[str, float]) -> None:  # type: ignore[override]
        pass

    def score(self, query: str) -> list[tuple[str, float]]:  # noqa: ARG002
        return list(self._scores)


class _MockDense:
    """Deterministic stub mimicking the DenseBackend Retriever surface."""

    def __init__(self, scores: list[tuple[str, float]]) -> None:
        self._scores = scores

    def rebuild(self, corpus: dict[str, float]) -> None:  # type: ignore[override]
        pass

    def score(self, query: str) -> list[tuple[str, float]]:  # noqa: ARG002
        return list(self._scores)


# ---------------------------------------------------------------------------
# Helper: compute expected RRF fused scores manually
# ---------------------------------------------------------------------------


def _competition_rank(scores: list[tuple[str, float]]) -> dict[str, int]:
    """Assign competition ranks (1-2-2-4) to a descending score list.

    Returns a dict mapping tool_id → rank (1-indexed).
    """
    sorted_scores = sorted(scores, key=lambda x: -x[1])
    ranks: dict[str, int] = {}
    current_rank = 1
    i = 0
    while i < len(sorted_scores):
        j = i
        while j < len(sorted_scores) and sorted_scores[j][1] == sorted_scores[i][1]:
            j += 1
        # All items i..j-1 share the same rank (competition rank = i+1).
        for k in range(i, j):
            ranks[sorted_scores[k][0]] = i + 1
        current_rank = j + 1  # noqa: F841
        i = j
    return ranks


def _fuse(
    bm25_scores: list[tuple[str, float]],
    dense_scores: list[tuple[str, float]],
    k: int = 60,
) -> dict[str, float]:
    """Compute RRF fused scores for all tool_ids in the union of both lists."""
    n_bm25 = len(bm25_scores)
    n_dense = len(dense_scores)

    bm25_ranks = _competition_rank(bm25_scores)
    dense_ranks = _competition_rank(dense_scores)

    all_ids = {t for t, _ in bm25_scores} | {t for t, _ in dense_scores}

    fused: dict[str, float] = {}
    for tool_id in all_ids:
        rank_b = bm25_ranks.get(tool_id, n_bm25 + 1)
        rank_d = dense_ranks.get(tool_id, n_dense + 1)
        fused[tool_id] = 1.0 / (k + rank_b) + 1.0 / (k + rank_d)

    return fused


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRRFFormula:
    """Unit tests for the RRF fused-score formula at k=60."""

    def _build_hybrid(
        self,
        bm25_scores: list[tuple[str, float]],
        dense_scores: list[tuple[str, float]],
        k: int = 60,
    ) -> HybridBackend:
        bm25 = _MockBM25(bm25_scores)
        dense = _MockDense(dense_scores)
        return HybridBackend(bm25=bm25, dense=dense, rrf_k=k)

    def test_cormack_basic_two_docs(self) -> None:
        """Two docs both present in both lists: verify formula exactly."""
        bm25_scores = [("tool_a", 10.0), ("tool_b", 5.0)]
        dense_scores = [("tool_a", 0.9), ("tool_b", 0.7)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result = hybrid.score("query")
        result_dict = dict(result)

        expected = _fuse(bm25_scores, dense_scores, k=60)
        assert set(result_dict.keys()) == set(expected.keys())
        for tid in expected:
            assert abs(result_dict[tid] - expected[tid]) < 1e-9, (
                f"tool_id={tid}: got {result_dict[tid]}, expected {expected[tid]}"
            )

    def test_missing_from_bm25_uses_n_plus_one_rank(self) -> None:
        """A doc absent from BM25 list uses rank = N+1 (N = BM25 list size)."""
        # BM25 returns only tool_a; dense returns tool_a + tool_b.
        bm25_scores = [("tool_a", 5.0)]
        dense_scores = [("tool_b", 0.95), ("tool_a", 0.80)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result_dict = dict(hybrid.score("query"))

        # tool_b is missing from BM25 → rank = 1 + 1 = 2
        expected_tool_b = 1.0 / (60 + 2) + 1.0 / (60 + 1)  # dense rank 1
        assert abs(result_dict["tool_b"] - expected_tool_b) < 1e-9

    def test_missing_from_dense_uses_n_plus_one_rank(self) -> None:
        """A doc absent from Dense list uses rank = N+1 (N = Dense list size)."""
        bm25_scores = [("tool_a", 10.0), ("tool_b", 5.0)]
        dense_scores = [("tool_a", 0.9)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result_dict = dict(hybrid.score("query"))

        # tool_b is missing from dense → rank = 1 + 1 = 2
        expected_tool_b = 1.0 / (60 + 2) + 1.0 / (60 + 2)  # bm25 rank 2, dense N+1=2
        assert abs(result_dict["tool_b"] - expected_tool_b) < 1e-9

    def test_all_fused_scores_strictly_positive(self) -> None:
        """Every tool_id in the union must have a strictly positive fused score."""
        bm25_scores = [("a", 1.0), ("b", 0.5), ("c", 0.0)]
        dense_scores = [("b", 0.8), ("d", 0.6), ("a", 0.1)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result = hybrid.score("query")
        assert all(score > 0.0 for _, score in result), (
            f"Expected all fused scores > 0, got: {result}"
        )

    def test_union_cardinality(self) -> None:
        """Result must contain all tool_ids from both retrievers (union)."""
        bm25_scores = [("a", 1.0), ("b", 0.5)]
        dense_scores = [("b", 0.8), ("c", 0.6)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result_ids = {tid for tid, _ in hybrid.score("any")}
        expected_ids = {"a", "b", "c"}
        assert result_ids == expected_ids

    def test_determinism_identical_inputs(self) -> None:
        """Same inputs must yield byte-identical output across two calls."""
        bm25_scores = [("x", 3.0), ("y", 2.0), ("z", 1.0)]
        dense_scores = [("x", 0.9), ("z", 0.8), ("y", 0.7)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        first = hybrid.score("determinism test")
        second = hybrid.score("determinism test")
        assert first == second, "HybridBackend.score is not deterministic"

    def test_competition_ranking_tie(self) -> None:
        """Tied raw scores share the same competition rank (1-2-2-4 pattern)."""
        # Both BM25 docs have same score → both get rank 1, next rank is 3.
        bm25_scores = [("a", 5.0), ("b", 5.0)]
        dense_scores = [("a", 0.9), ("b", 0.6)]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result_dict = dict(hybrid.score("q"))

        # Both a and b have BM25 rank 1 (tied at 5.0), dense: a=rank1, b=rank2.
        expected_a = 1.0 / (60 + 1) + 1.0 / (60 + 1)
        expected_b = 1.0 / (60 + 1) + 1.0 / (60 + 2)
        assert abs(result_dict["a"] - expected_a) < 1e-9
        assert abs(result_dict["b"] - expected_b) < 1e-9

    def test_four_seed_adapters_full_fusion(self) -> None:
        """Smoke test with 4 seed adapter IDs (representative of real usage)."""
        bm25_scores = [
            ("koroad_accident_hazard_search", 2.5),
            ("kma_forecast_fetch", 1.8),
            ("hira_hospital_search", 1.2),
            ("nmc_emergency_search", 0.3),
        ]
        dense_scores = [
            ("kma_forecast_fetch", 0.92),
            ("koroad_accident_hazard_search", 0.80),
            ("nmc_emergency_search", 0.70),
            ("hira_hospital_search", 0.60),
        ]
        hybrid = self._build_hybrid(bm25_scores, dense_scores)

        result = hybrid.score("기상 예보")
        result_dict = dict(result)

        expected = _fuse(bm25_scores, dense_scores, k=60)
        assert set(result_dict.keys()) == set(expected.keys())
        for tid in expected:
            assert abs(result_dict[tid] - expected[tid]) < 1e-9

    def test_rebuild_does_not_corrupt_scores(self) -> None:
        """Calling rebuild() then score() should produce consistent results."""
        bm25 = _MockBM25([("a", 5.0)])
        dense = _MockDense([("a", 0.9)])
        hybrid = HybridBackend(bm25=bm25, dense=dense, rrf_k=60)

        hybrid.rebuild({"a": "some hint"})
        result = hybrid.score("q")
        assert len(result) >= 1
        assert all(score > 0 for _, score in result)
