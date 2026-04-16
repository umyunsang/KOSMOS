# SPDX-License-Identifier: Apache-2.0
"""rank_bm25 wrapper with deterministic tie-break for the KOSMOS tool registry.

The BM25 index is rebuilt in full whenever a new adapter is registered.  On a
registry of 4–50 adapters, a rebuild takes < 5 ms and is called only on
startup or explicit ``rebuild()`` — never on the hot BM25 query path.
"""

from __future__ import annotations

import logging

from kosmos.tools.tokenizer import tokenize

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25Okapi index over a corpus of ``{tool_id: search_hint}`` strings.

    Usage::

        index = BM25Index({"koroad_accident_hazard_search": "교통사고 accident …"})
        results = index.score("교통사고 위험지역")
        # → [("koroad_accident_hazard_search", 1.23), ...]
    """

    def __init__(self, corpus: dict[str, str]) -> None:
        """Build the BM25 index from *corpus*.

        Args:
            corpus: Mapping of ``tool_id → search_hint`` strings.
                    An empty mapping is valid (queries will return empty lists).
        """
        self._tool_ids: list[str] = []
        self._bm25: object | None = None
        self._build(corpus)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Rebuild the index in place from a fresh corpus.

        Thread-safety: single-threaded rebuild; callers must ensure mutual
        exclusion if the registry is shared across threads.
        """
        self._build(corpus)

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return ``(tool_id, score)`` pairs for *query*, sorted DESC by score
        then ASC by ``tool_id`` for a deterministic tie-break (FR-013).

        Args:
            query: Free-text query in Korean or English.

        Returns:
            List of ``(tool_id, score)`` tuples.  Tuples with score ≤ 0 are
            included so that callers can decide their own threshold.
        """
        if self._bm25 is None or not self._tool_ids:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            # Return zero scores for all tools so callers see the full list.
            return [(tid, 0.0) for tid in sorted(self._tool_ids)]

        try:
            raw_scores: list[float] = self._bm25.get_scores(query_tokens).tolist()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover
            logger.warning("BM25 scoring failed: %s", exc)
            return [(tid, 0.0) for tid in sorted(self._tool_ids)]

        # Primary sort: score DESC; secondary sort: tool_id ASC (tie-break).
        paired = list(zip(self._tool_ids, raw_scores, strict=True))
        paired.sort(key=lambda x: (-x[1], x[0]))
        return [(tid, score) for tid, score in paired]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build(self, corpus: dict[str, str]) -> None:
        """Tokenise every document and initialise BM25Okapi."""
        if not corpus:
            self._tool_ids = []
            self._bm25 = None
            logger.debug("BM25Index: empty corpus, index cleared")
            return

        self._tool_ids = list(corpus.keys())
        tokenized_corpus = [tokenize(hint) for hint in corpus.values()]

        try:
            from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

            self._bm25 = BM25Okapi(tokenized_corpus)
            logger.debug("BM25Index rebuilt: %d documents", len(self._tool_ids))
        except Exception as exc:  # pragma: no cover
            logger.error("BM25Okapi init failed: %s", exc)
            self._bm25 = None
