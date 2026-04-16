# SPDX-License-Identifier: Apache-2.0
"""BM25 retrieval property tests — T035.

Verifies three core BM25 properties:
1. BM25 scores strictly positive for matching terms.
2. BM25 scores zero for fully disjoint terms.
3. Deterministic across 10 repeated runs (same query → same ranking,
   including tie-break by tool_id ASC per FR-013).

No live API calls are made.
"""

from __future__ import annotations

from kosmos.tools.bm25_index import BM25Index

# ---------------------------------------------------------------------------
# Fixtures — small synthetic corpora
#
# NOTE on BM25Okapi IDF: The BM25Okapi IDF formula is
#   log((N - n + 0.5) / (n + 0.5))
# where N = corpus size, n = number of docs containing the term.
# When N=2 and n=1: IDF = log(1.5/1.5) = 0 → ALL scores are zero.
# Positive scores require N >= 3, with term appearing in fewer than N docs.
# All corpora below have at least 3 documents for this reason.
# ---------------------------------------------------------------------------

_CORPUS_MULTI = {
    "koroad_accident_hazard_search": (
        "교통사고 위험지점 사고다발구역 행정동코드 연도별 위험지역 "
        "accident hazard spot dangerous zone adm_cd year traffic safety Korea"
    ),
    "kma_forecast": (
        "단기예보 날씨예보 기온 강수확률 하늘상태 습도 풍속 풍향 "
        "short-term forecast weather temperature precipitation sky humidity wind"
    ),
    "hira_hospital": ("병원 의원 의료기관 hospital clinic HIRA 근처 nearby"),
    "nmc_emergency": (
        "응급실 실시간 병상 응급의료센터 국립중앙의료원 "
        "emergency room bed availability nearest ER NMC"
    ),
}

_DISJOINT_TOOL_ID = "completely_disjoint_tool"
# 3-document corpus where all documents have only non-KOROAD terms.
# Used to verify that a KOROAD query produces zero scores for all docs.
_DISJOINT_CORPUS_3: dict[str, str] = {
    _DISJOINT_TOOL_ID: "blockchain cryptocurrency decentralized ledger bitcoin",
    "tool_alpha": "날씨 기온 weather forecast temperature precipitation",
    "tool_beta": "병원 의원 의료기관 hospital clinic nearby",
}


# ---------------------------------------------------------------------------
# T035-A: BM25 scores strictly positive for matching terms
# ---------------------------------------------------------------------------


class TestBM25PositiveScores:
    """BM25 must return positive scores when query tokens appear in a document.

    NOTE: BM25Okapi IDF = log((N - n + 0.5) / (n + 0.5)).  With N=2 docs and n=1,
    IDF = log(1) = 0, so all scores are zero regardless of query.  Positive scores
    require N >= 3 with the matching term appearing in fewer than N documents.
    _CORPUS_MULTI has 4 documents, guaranteeing positive IDF for single-doc terms.
    """

    def test_korean_matching_query_has_positive_score(self) -> None:
        """Korean query term in one of 4 corpus docs should produce score > 0."""
        # Use _CORPUS_MULTI (4 docs) so IDF is positive for terms in 1 doc.
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("교통사고 위험지점")
        assert results, "Expected at least one result"
        tool_id, score = results[0]
        assert tool_id == "koroad_accident_hazard_search"
        assert score > 0.0, f"Expected positive BM25 score for matching Korean query, got {score}"

    def test_english_matching_query_has_positive_score(self) -> None:
        """English query term in one of 4 corpus docs should produce score > 0."""
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("accident hazard spot")
        assert results, "Expected at least one result"
        tool_id, score = results[0]
        assert tool_id == "koroad_accident_hazard_search"
        assert score > 0.0, f"Expected positive BM25 score for matching English query, got {score}"

    def test_best_matching_tool_ranks_first(self) -> None:
        """The most relevant tool must have the highest score."""
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("교통사고 위험지점")
        assert results, "Expected results"
        top_id, top_score = results[0]
        assert top_id == "koroad_accident_hazard_search", (
            f"Expected koroad_accident_hazard_search first, got {top_id}"
        )
        assert top_score > 0.0

    def test_weather_query_scores_kma_forecast_highest(self) -> None:
        """A weather query should score the kma tool highest."""
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("날씨 기온 forecast")
        assert results, "Expected results"
        top_id, top_score = results[0]
        assert top_id == "kma_forecast", (
            f"Expected kma_forecast first for weather query, got {top_id}"
        )
        assert top_score > 0.0

    def test_emergency_query_scores_nmc_highest(self) -> None:
        """Emergency room query should score the NMC tool highest."""
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("응급실 병상")
        assert results, "Expected results"
        top_id, top_score = results[0]
        assert top_id == "nmc_emergency", f"Expected nmc_emergency first for ER query, got {top_id}"
        assert top_score > 0.0


# ---------------------------------------------------------------------------
# T035-B: BM25 scores zero for fully disjoint terms
# ---------------------------------------------------------------------------


class TestBM25ZeroScoresForDisjointTerms:
    """BM25 must return zero scores when query tokens are absent from all documents."""

    def test_disjoint_query_returns_zero_score(self) -> None:
        """A query with no overlapping tokens should score zero for all documents.

        Uses _CORPUS_MULTI (4 docs) to ensure IDF is non-zero for real terms,
        then queries with blockchain terms that appear in no document.
        """
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("blockchain cryptocurrency decentralized")
        assert results, "Expected result list (score zero is included)"
        for tool_id, score in results:
            assert score == 0.0, (
                f"Expected zero score for fully disjoint query, got {score} for {tool_id}"
            )

    def test_disjoint_corpus_vs_koroad_query_returns_zero(self) -> None:
        """Querying KOROAD terms against a disjoint 3-doc corpus should score zero.

        _DISJOINT_CORPUS_3 has 3 docs: blockchain content + two other docs.
        KOROAD tokens don't appear in any of the 3 docs → all scores zero.
        """
        index = BM25Index(_DISJOINT_CORPUS_3)
        # Blockchain doc has no KOROAD tokens; other two docs also have no KOROAD tokens
        results = index.score("교통사고 위험지점 accident hazard")
        assert results, "Expected result list"
        for tool_id, score in results:
            assert score == 0.0, (
                f"Expected zero score for disjoint corpus query, got {score} for {tool_id}"
            )

    def test_mixed_corpus_disjoint_tool_scores_zero(self) -> None:
        """A tool with fully disjoint terms in a multi-tool corpus should score zero."""
        corpus = dict(_CORPUS_MULTI)
        corpus["disjoint_tool"] = "blockchain cryptocurrency decentralized ledger"
        index = BM25Index(corpus)
        results = index.score("교통사고 위험지점 accident")
        score_map = dict(results)
        assert "disjoint_tool" in score_map, "Expected disjoint_tool in results"
        assert score_map["disjoint_tool"] == 0.0, (
            f"Expected zero score for disjoint_tool, got {score_map['disjoint_tool']}"
        )


# ---------------------------------------------------------------------------
# T035-C: Deterministic across 10 repeated runs with tie-break by tool_id ASC
# ---------------------------------------------------------------------------


class TestBM25Determinism:
    """BM25 scoring must be fully deterministic (FR-013)."""

    def test_same_query_produces_identical_ranking_10_times(self) -> None:
        """Same query against the same index must yield identical results 10 times."""
        index = BM25Index(_CORPUS_MULTI)
        query = "교통사고 위험지점"

        results_runs = [index.score(query) for _ in range(10)]
        first_run = results_runs[0]

        for i, run in enumerate(results_runs[1:], start=2):
            assert run == first_run, (
                f"Run {i} produced different ranking than run 1: {run} != {first_run}"
            )

    def test_english_query_deterministic_10_times(self) -> None:
        """English query must also produce identical results on every run."""
        index = BM25Index(_CORPUS_MULTI)
        query = "accident hazard spot"

        results_runs = [index.score(query) for _ in range(10)]
        first_run = results_runs[0]

        for i, run in enumerate(results_runs[1:], start=2):
            assert run == first_run, f"Run {i} differs from run 1: {run} != {first_run}"

    def test_zero_score_tie_break_by_tool_id_asc(self) -> None:
        """When all scores are zero, results must be sorted by tool_id ASC (FR-013)."""
        # Use a query that does not match anything → all scores zero
        index = BM25Index(_CORPUS_MULTI)
        results = index.score("xyzzy_nonexistent_term_12345")
        # All scores should be zero; order must be tool_id ascending
        tool_ids = [tid for tid, _ in results]
        assert tool_ids == sorted(tool_ids), (
            f"Expected tool_ids sorted ASC on zero-score tie-break, got {tool_ids}"
        )

    def test_tie_break_determinism_on_equal_scores(self) -> None:
        """For any query producing equal scores across tools, order is tool_id ASC."""
        # Rebuild index multiple times and verify consistent tie-break order
        query = "xyzzy_nonexistent_term_12345"
        for _ in range(10):
            index = BM25Index(_CORPUS_MULTI)
            results = index.score(query)
            tool_ids = [tid for tid, _ in results]
            assert tool_ids == sorted(tool_ids), f"Tie-break order not consistently ASC: {tool_ids}"

    def test_rebuild_does_not_change_determinism(self) -> None:
        """After rebuild, the same query must produce the same order."""
        index = BM25Index(_CORPUS_MULTI)
        query = "응급실 emergency room"
        before_rebuild = index.score(query)

        # Rebuild with the same corpus
        index.rebuild(_CORPUS_MULTI)
        after_rebuild = index.score(query)

        assert before_rebuild == after_rebuild, (
            f"Rebuild changed query results: before={before_rebuild} after={after_rebuild}"
        )
