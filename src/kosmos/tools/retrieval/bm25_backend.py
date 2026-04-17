# SPDX-License-Identifier: Apache-2.0
"""BM25 backend wrapper satisfying the ``Retriever`` protocol (spec 026).

Composition-only shim around the pre-#585 ``BM25Index``. Scoring is
delegated verbatim so the committed 30-query baseline remains
byte-identical (SC-04 schema snapshot + parity test guard).
"""

from __future__ import annotations

from kosmos.tools.bm25_index import BM25Index


class BM25Backend:
    """``Retriever``-compatible adapter over the existing ``BM25Index``.

    The wrapper exists so that ``ToolRegistry`` depends on the
    ``Retriever`` protocol rather than a concrete class, which is the
    single dependency-injection seam added by spec 026.
    """

    def __init__(self, index: BM25Index) -> None:
        """Store an already-constructed ``BM25Index``.

        Args:
            index: Pre-built BM25 index. Ownership transfers to the
                backend; callers MUST NOT mutate it afterwards. Empty
                index is legal.
        """
        self._index = index

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Delegate to ``BM25Index.rebuild`` without modification."""
        self._index.rebuild(corpus)

    def score(self, query: str) -> list[tuple[str, float]]:
        """Delegate to ``BM25Index.score`` without modification.

        Returns the same ``(tool_id, score)`` list the legacy path
        produced, preserving the deterministic tie-break applied by
        ``BM25Index`` (score DESC, tool_id ASC).
        """
        return self._index.score(query)
