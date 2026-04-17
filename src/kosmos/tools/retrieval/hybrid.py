# SPDX-License-Identifier: Apache-2.0
"""Hybrid (BM25 + Dense) retrieval backend via Reciprocal Rank Fusion (spec 026, T022).

Fuses BM25 lexical scores and dense semantic scores using the RRF formula
from Cormack, Clarke & Büttcher, "Reciprocal Rank Fusion outperforms
Condorcet and Individual Rank Learning Methods", SIGIR 2009.

    fused(d) = 1/(k + rank_bm25(d)) + 1/(k + rank_dense(d))

where k = 60 (Cormack default) and missing-from-list rank = N + 1
(N = retriever output size), ensuring every union member has a strictly
positive fused score.

Competition ranking (1-2-2-4): documents tied in raw score share the
lowest rank among them; the next rank skips over the tie group.

Hard rules (AGENTS.md):
- Stdlib ``logging`` only; no ``print()``.
- No ``Any`` types.
- Fused score is strictly positive for every tool_id in the union.
- Determinism: identical (bm25, dense, query) inputs → identical output.
"""

from __future__ import annotations

import logging

from kosmos.tools.retrieval.bm25_backend import BM25Backend
from kosmos.tools.retrieval.degrade import DegradationRecord
from kosmos.tools.retrieval.dense_backend import DenseBackend, DenseBackendLoadError

logger = logging.getLogger(__name__)


def _competition_rank(scores: list[tuple[str, float]]) -> dict[str, int]:
    """Assign competition ranks (1-2-2-4 pattern) to a score list.

    Scores are sorted descending; tied scores share the *lowest* rank in
    their group (standard competition / "1224" ranking used in
    information-retrieval evaluation).

    Args:
        scores: Arbitrary list of ``(tool_id, score)`` pairs.

    Returns:
        Dict mapping ``tool_id → rank`` (1-indexed).
    """
    sorted_scores = sorted(scores, key=lambda x: -x[1])
    ranks: dict[str, int] = {}
    i = 0
    while i < len(sorted_scores):
        j = i
        # Advance j to the end of the tie group.
        while j < len(sorted_scores) and sorted_scores[j][1] == sorted_scores[i][1]:
            j += 1
        # All items i..j-1 receive rank = i + 1 (1-indexed position of group start).
        for pos in range(i, j):
            ranks[sorted_scores[pos][0]] = i + 1
        i = j
    return ranks


class HybridBackend:
    """RRF fusion of a BM25 lexical retriever and a Dense semantic retriever.

    Satisfies the ``Retriever`` protocol.

    Args:
        bm25: The lexical retriever (``BM25Backend``).
        dense: The semantic retriever (``DenseBackend``).
        rrf_k: The RRF constant ``k`` (Cormack 2009 default = 60).
    """

    def __init__(
        self,
        bm25: BM25Backend,
        dense: DenseBackend,
        *,
        rrf_k: int = 60,
        degradation_record: DegradationRecord | None = None,
    ) -> None:
        self._bm25 = bm25
        self._dense = dense
        self._rrf_k = rrf_k
        self._degradation_record = degradation_record

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Rebuild both sub-backends from the same corpus.

        Args:
            corpus: Mapping of ``tool_id → search_hint``. Empty dict
                resets both backends.
        """
        self._bm25.rebuild(corpus)
        self._dense.rebuild(corpus)
        logger.debug("HybridBackend: rebuilt both backends, corpus_size=%d", len(corpus))

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return RRF-fused ``(tool_id, fused_score)`` pairs for *query*.

        Algorithm:
        1. Obtain raw scores from BM25 and Dense independently.
        2. Assign competition ranks (descending) within each list.
        3. For each tool_id in the union, compute
               fused = 1/(k + rank_bm25) + 1/(k + rank_dense)
           with missing-from-list rank = N + 1 (where N = list size).
        4. Return unordered; downstream tie-break is applied by
           ``kosmos.tools.search``.

        Args:
            query: Free-text citizen query.

        Returns:
            Unordered list of ``(tool_id, fused_score)`` with
            ``fused_score > 0`` for every entry.
        """
        bm25_scores = self._bm25.score(query)
        try:
            dense_scores = self._dense.score(query)
        except (
            DenseBackendLoadError,
            RuntimeError,
            OSError,
            ValueError,
            MemoryError,
        ) as exc:
            if self._degradation_record is not None:
                self._degradation_record.emit_if_needed(
                    logger,
                    requested_backend="hybrid",
                    effective_backend="bm25",
                    reason=f"dense score failed: {type(exc).__name__}: {exc}",
                )
            # Reuse the BM25 ranking we already computed; calling .score() a
            # second time would double tokenisation cost on every degraded
            # query and risk diverging from the BM25 list the degradation
            # latch was reported against.
            return bm25_scores

        n_bm25 = len(bm25_scores)
        n_dense = len(dense_scores)

        # Early exit: if both are empty, return empty.
        if n_bm25 == 0 and n_dense == 0:
            return []

        bm25_ranks = _competition_rank(bm25_scores)
        dense_ranks = _competition_rank(dense_scores)

        all_tool_ids: set[str] = {tid for tid, _ in bm25_scores} | {tid for tid, _ in dense_scores}

        k = self._rrf_k
        fused: list[tuple[str, float]] = []
        for tool_id in all_tool_ids:
            rank_b = bm25_ranks.get(tool_id, n_bm25 + 1)
            rank_d = dense_ranks.get(tool_id, n_dense + 1)
            fused_score = 1.0 / (k + rank_b) + 1.0 / (k + rank_d)
            fused.append((tool_id, fused_score))

        return fused
