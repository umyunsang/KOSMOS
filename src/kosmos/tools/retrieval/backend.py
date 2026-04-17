# SPDX-License-Identifier: Apache-2.0
"""Retriever protocol + environment-driven factory (spec 026).

The Protocol is the single dependency-injection seam that lets
``ToolRegistry`` swap between BM25, Dense, and Hybrid backends without
altering the byte-level public contract (``LookupSearchInput``,
``LookupSearchResult``, ``AdapterCandidate``) owned by spec 507.

Fusion algorithm:
    Reciprocal Rank Fusion (Cormack, Clarke, Buettcher, SIGIR 2009,
    "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank
    Learning Methods"). Default k = 60.

Hard rule:
    Backends MUST NOT introduce hardcoded synonym lists, keyword
    rewrites, or query-salvage loops (see ``feedback_no_hardcoding.md``).
    LLM self-correction handles residual misses.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Literal, Protocol, runtime_checkable

from kosmos.tools.bm25_index import BM25Index
from kosmos.tools.retrieval.bm25_backend import BM25Backend
from kosmos.tools.retrieval.degrade import DegradationRecord
from kosmos.tools.retrieval.dense_backend import DenseBackend, DenseBackendLoadError
from kosmos.tools.retrieval.hybrid import HybridBackend

logger = logging.getLogger(__name__)


@runtime_checkable
class Retriever(Protocol):
    """Pluggable ranking backend consumed by ``ToolRegistry``.

    Implementations MUST be pure CPU and MUST preserve non-negativity at
    the score layer. Final tie-break (score DESC, tool_id ASC) is
    applied downstream by ``kosmos.tools.search``.
    """

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Replace the index with a new corpus.

        Empty dict is legal and resets the index. MUST be idempotent on
        repeated identical input.

        Implementations MAY raise on unrecoverable init failure
        (e.g. ``DenseBackendLoadError`` when the encoder weights cannot
        be loaded or hashed). Fail-open degradation to pure BM25 is
        handled one layer up by ``build_retriever_from_env``, which
        catches these exceptions and emits a single structured WARN via
        ``DegradationRecord`` (FR-002 / SC-005). Once ``rebuild`` has
        returned successfully, subsequent calls on the same instance
        MUST NOT raise.
        """
        ...

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return ``(tool_id, score)`` pairs for *query*.

        Scores MUST be in ``[0.0, +inf)``. Empty list is legal when the
        corpus is empty or every document scores zero.
        """
        ...


class _DenseFailOpenWrapper:
    """Pure-dense backend wrapper that fail-opens to BM25 on load failure.

    When ``KOSMOS_RETRIEVAL_BACKEND=dense`` and cold-start is ``lazy``
    (the default), a model-load failure does not manifest until the
    first ``.score()`` call. Without this wrapper the failure would
    produce an empty ranking forever (no BM25 fallback) because
    ``ToolRegistry.register()`` already ran successfully at registry
    construction time, so its built-in fail-open path never fires.

    This wrapper holds a companion ``BM25Backend`` kept in sync with
    the dense backend's corpus via ``rebuild()``. On the first
    ``DenseBackendLoadError`` from ``.score()`` it:

    1. Emits exactly one structured WARN via ``DegradationRecord``
       (FR-002 / SC-005 — one-shot latch).
    2. Flips an internal ``_degraded`` flag.
    3. Returns the BM25 companion's ranking for this query.

    Every subsequent ``.score()`` short-circuits to the BM25 companion
    without re-invoking dense. This preserves the "serve citizen with
    BM25 results, never 5xx" contract and guarantees a single WARN per
    degraded instance.

    Hybrid does not need this wrapper because ``HybridBackend.score()``
    already computes BM25 first and can reuse it on dense failure.
    """

    # Logical backend label for structured WARN logs. The registry's
    # fail-open path (registry.py) and the wrapper's own lazy-path
    # emit_if_needed() must both report ``requested_backend='dense'``
    # even though the Python type is ``_DenseFailOpenWrapper``. The
    # registry reads this attribute via ``getattr(retriever, ...)``
    # instead of deriving the label from ``type(retriever).__name__``.
    _requested_backend_label = "dense"

    def __init__(
        self,
        *,
        dense: DenseBackend,
        bm25: BM25Backend,
        degradation_record: DegradationRecord | None,
    ) -> None:
        self._dense = dense
        self._bm25 = bm25
        self._degradation_record = degradation_record
        self._degraded = False

    def rebuild(self, corpus: dict[str, str]) -> None:
        # Keep BM25 companion in sync so it can serve the degraded path
        # with the same corpus snapshot the dense backend would have
        # embedded. Rebuilding BM25 is cheap (pure Python, no model).
        self._bm25.rebuild(corpus)
        # Dense rebuild() under lazy mode just buffers the corpus;
        # under eager it embeds. Either path is safe to call.
        self._dense.rebuild(corpus)

    def score(self, query: str) -> list[tuple[str, float]]:
        if self._degraded:
            return self._bm25.score(query)
        try:
            return self._dense.score(query)
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
                    requested_backend="dense",
                    effective_backend="bm25",
                    reason=f"dense score failed: {type(exc).__name__}: {exc}",
                )
            self._degraded = True
            return self._bm25.score(query)


def _resolve_cold_start() -> Literal["lazy", "eager"]:
    """Parse and validate ``KOSMOS_RETRIEVAL_COLD_START``.

    Defaults to ``"lazy"`` (FR-011 / NFR-BootBudget): encoder load is
    deferred to the first ``.score()`` call so boot paths that register
    tools (and thus force rebuild during startup) do not pay model-load
    cost before any query arrives.

    Raises:
        ValueError: On any value other than ``lazy`` or ``eager``.
            Unknown strings fail-closed at registry construction.
    """
    raw = os.getenv("KOSMOS_RETRIEVAL_COLD_START", "lazy").strip().lower()
    if raw not in {"lazy", "eager"}:
        raise ValueError(
            f"KOSMOS_RETRIEVAL_COLD_START={raw!r} is not recognised "
            "(allowed: lazy, eager). Fail-closed per FR-011."
        )
    return raw  # type: ignore[return-value]


def _resolve_hybrid_fusion_k() -> int:
    """Parse and validate KOSMOS_RETRIEVAL_FUSION / KOSMOS_RETRIEVAL_FUSION_K.

    Raises:
        ValueError: On unrecognised fusion algorithm or invalid k value.
    """
    fusion = os.getenv("KOSMOS_RETRIEVAL_FUSION", "rrf").strip().lower()
    if fusion != "rrf":
        raise ValueError(
            f"KOSMOS_RETRIEVAL_FUSION={fusion!r} is not recognised "
            "(only 'rrf' is supported). Fail-closed per FR-001."
        )
    fusion_k_raw = os.getenv("KOSMOS_RETRIEVAL_FUSION_K", "60").strip()
    try:
        fusion_k = int(fusion_k_raw)
    except ValueError as exc:
        raise ValueError(
            f"KOSMOS_RETRIEVAL_FUSION_K={fusion_k_raw!r} is not a valid integer."
        ) from exc
    if fusion_k < 1:
        raise ValueError(f"KOSMOS_RETRIEVAL_FUSION_K={fusion_k} is invalid; must be >= 1.")
    return fusion_k


def build_retriever_from_env(
    *,
    bm25_index_factory: Callable[[], BM25Index] | None = None,
    degradation_record: DegradationRecord | None = None,
) -> Retriever:
    """Construct a ``Retriever`` from ``KOSMOS_RETRIEVAL_*`` env vars.

    Env vars (spec 026, registered via #468):
        KOSMOS_RETRIEVAL_BACKEND: ``bm25`` | ``dense`` | ``hybrid``
            (default ``bm25``). Unknown values fail-closed via ValueError.

    Args:
        bm25_index_factory: Optional callable producing a ``BM25Index``
            for the default / fallback path. Injected by
            ``ToolRegistry`` so tests can stub it.
        degradation_record: Optional latch used to emit exactly one
            structured WARN when dense/hybrid construction falls back
            to BM25 (FR-002 / SC-005). Supplied by ``ToolRegistry``.

    Returns:
        A ``Retriever`` instance.

    Raises:
        ValueError: Unknown backend name (FR-001 fail-closed at
            registry construction). Also raised for invalid fusion /
            fusion-k config — operator errors MUST still fail-closed.
    """
    backend = os.getenv("KOSMOS_RETRIEVAL_BACKEND", "bm25").strip().lower()
    if backend not in {"bm25", "dense", "hybrid"}:
        raise ValueError(
            f"KOSMOS_RETRIEVAL_BACKEND={backend!r} is not recognised "
            "(allowed: bm25, dense, hybrid). Fail-closed per FR-001."
        )

    index_factory = bm25_index_factory or (lambda: BM25Index({}))

    if backend == "bm25":
        return BM25Backend(index_factory())

    # --- Dense and Hybrid paths (T023) -----------------------------------
    model_id = os.getenv("KOSMOS_RETRIEVAL_MODEL_ID", "intfloat/multilingual-e5-small").strip()
    cold_start = _resolve_cold_start()

    if backend == "dense":
        try:
            dense_backend = DenseBackend(model_id=model_id, cold_start=cold_start)
        except (DenseBackendLoadError, ImportError, RuntimeError, OSError) as exc:
            # Construction-time failure (e.g. sentence-transformers import
            # failure) → fail-open to pure BM25 immediately. The lazy-load
            # failure path at first .score() is handled by the wrapper below.
            if degradation_record is not None:
                degradation_record.emit_if_needed(
                    logger,
                    requested_backend=backend,
                    effective_backend="bm25",
                    reason=f"dense load failed: {type(exc).__name__}: {exc}",
                )
            return BM25Backend(index_factory())
        # Wrap pure-dense with a BM25 companion so lazy-load failure at
        # first .score() degrades to BM25 instead of silently serving
        # empty rankings forever (Codex review round 5 on #837).
        return _DenseFailOpenWrapper(
            dense=dense_backend,
            bm25=BM25Backend(index_factory()),
            degradation_record=degradation_record,
        )

    # backend == "hybrid"
    fusion_k = _resolve_hybrid_fusion_k()
    try:
        bm25_backend = BM25Backend(index_factory())
        dense_backend = DenseBackend(model_id=model_id, cold_start=cold_start)
        return HybridBackend(
            bm25=bm25_backend,
            dense=dense_backend,
            rrf_k=fusion_k,
            degradation_record=degradation_record,
        )
    except (DenseBackendLoadError, ImportError, RuntimeError, OSError) as exc:
        if degradation_record is not None:
            degradation_record.emit_if_needed(
                logger,
                requested_backend=backend,
                effective_backend="bm25",
                reason=f"dense load failed: {type(exc).__name__}: {exc}",
            )
        return BM25Backend(index_factory())
