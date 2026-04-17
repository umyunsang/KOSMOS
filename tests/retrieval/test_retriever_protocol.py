# SPDX-License-Identifier: Apache-2.0
"""Retriever protocol conformance tests for BM25Backend (spec 026, T014).

Validates four contractual guarantees defined in
``specs/026-retrieval-dense-embeddings/contracts/retriever_protocol.md``:

1. runtime_checkable — isinstance(BM25Backend(...), Retriever) is True.
2. empty-corpus    — score() on an empty-corpus index returns [].
3. empty-query     — score("") against a non-empty corpus returns an
                     all-zero vector of length len(corpus).
4. non-negative    — all scores are >= 0.0 for a real query against a
                     real corpus.
"""

from __future__ import annotations

from kosmos.tools.bm25_index import BM25Index
from kosmos.tools.retrieval.backend import Retriever
from kosmos.tools.retrieval.bm25_backend import BM25Backend

# ---------------------------------------------------------------------------
# Shared fixture — small non-empty corpus with real Korean search_hints.
# Three documents are required so BM25Okapi IDF is positive for single-doc
# terms (IDF = log((N - n + 0.5) / (n + 0.5)); N=2, n=1 → 0).
# ---------------------------------------------------------------------------

_SMALL_CORPUS: dict[str, str] = {
    "koroad_accident_hazard_search": (
        "교통사고 위험지점 사고다발구역 행정동코드 연도별 위험지역 "
        "accident hazard spot dangerous zone adm_cd year traffic safety"
    ),
    "kma_forecast_fetch": (
        "단기예보 날씨예보 기온 강수확률 하늘상태 습도 풍속 풍향 "
        "short-term forecast weather temperature precipitation sky humidity wind"
    ),
    "nmc_emergency_search": (
        "응급실 실시간 병상 응급의료센터 국립중앙의료원 "
        "emergency room bed availability nearest ER NMC"
    ),
}


# ---------------------------------------------------------------------------
# 1. runtime_checkable
# ---------------------------------------------------------------------------


class TestRetrieverProtocolConformance:
    """BM25Backend must satisfy the Retriever runtime_checkable Protocol."""

    def test_isinstance_check_passes(self) -> None:
        """isinstance(BM25Backend(BM25Index({})), Retriever) must be True.

        Verifies that BM25Backend structurally satisfies the @runtime_checkable
        Retriever Protocol without any explicit inheritance.
        """
        backend = BM25Backend(BM25Index({}))
        assert isinstance(backend, Retriever), (
            "BM25Backend does not satisfy the Retriever protocol. "
            "Ensure it implements rebuild(corpus) and score(query) with "
            "the exact signatures declared in backend.py."
        )


# ---------------------------------------------------------------------------
# 2. empty-corpus
# ---------------------------------------------------------------------------


class TestEmptyCorpusContract:
    """score() on an empty-corpus backend MUST return the literal empty list."""

    def test_score_returns_empty_list_on_empty_corpus(self) -> None:
        """BM25Backend built on an empty BM25Index returns [] for any query."""
        backend = BM25Backend(BM25Index({}))
        result = backend.score("교통사고")
        assert result == [], f"Expected [] for empty corpus, got {result!r}"

    def test_score_empty_query_returns_empty_list_on_empty_corpus(self) -> None:
        """An empty-corpus backend returns [] even for an empty query string."""
        backend = BM25Backend(BM25Index({}))
        result = backend.score("")
        assert result == [], f"Expected [] for empty corpus with empty query, got {result!r}"


# ---------------------------------------------------------------------------
# 3. empty-query → all-zero vector of length len(corpus)
# ---------------------------------------------------------------------------


class TestEmptyQueryContract:
    """score("") on a non-empty corpus MUST return an all-zero vector."""

    def test_empty_query_length_equals_corpus_size(self) -> None:
        """Result length must equal the number of documents in the corpus."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("")
        assert len(scored) == len(_SMALL_CORPUS), (
            f"Expected {len(_SMALL_CORPUS)} results for empty query, got {len(scored)}: {scored!r}"
        )

    def test_empty_query_all_scores_are_zero(self) -> None:
        """Every score in the result for an empty query must be exactly 0.0."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("")
        assert all(s == 0.0 for _, s in scored), (
            f"Expected all scores == 0.0 for empty query, got: {scored!r}"
        )

    def test_empty_query_combined_length_and_zero_invariant(self) -> None:
        """Combine length and zero-score checks as the canonical all-zero vector assert."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("")
        assert len(scored) == len(_SMALL_CORPUS) and all(s == 0.0 for _, s in scored), (
            f"Empty-query must return all-zero vector of length "
            f"{len(_SMALL_CORPUS)}, got: {scored!r}"
        )


# ---------------------------------------------------------------------------
# 4. non-negative scores
# ---------------------------------------------------------------------------


class TestNonNegativeScoresContract:
    """All scores returned by score() MUST be >= 0.0 (Retriever protocol §score)."""

    def test_korean_query_scores_non_negative(self) -> None:
        """Korean query against a real corpus must yield all non-negative scores."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("교통사고 위험지점")
        assert scored, "Expected at least one result for real Korean query"
        assert all(s >= 0.0 for _, s in scored), (
            f"Negative score detected for Korean query: {scored!r}"
        )

    def test_english_query_scores_non_negative(self) -> None:
        """English query against a real corpus must yield all non-negative scores."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("emergency room")
        assert scored, "Expected at least one result for real English query"
        assert all(s >= 0.0 for _, s in scored), (
            f"Negative score detected for English query: {scored!r}"
        )

    def test_mixed_query_scores_non_negative(self) -> None:
        """Mixed Korean/English query must yield all non-negative scores."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("날씨 forecast 기온")
        assert scored, "Expected at least one result for mixed query"
        assert all(s >= 0.0 for _, s in scored), (
            f"Negative score detected for mixed query: {scored!r}"
        )

    def test_disjoint_query_scores_non_negative(self) -> None:
        """A fully disjoint query must return zero (not negative) scores."""
        backend = BM25Backend(BM25Index(_SMALL_CORPUS))
        scored = backend.score("blockchain cryptocurrency decentralized")
        assert all(s >= 0.0 for _, s in scored), (
            f"Negative score detected for disjoint query: {scored!r}"
        )
