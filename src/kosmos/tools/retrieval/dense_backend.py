# SPDX-License-Identifier: Apache-2.0
"""Dense (embedding) retrieval backend for spec 026 (T021).

Uses ``sentence-transformers`` to encode corpus search_hints and queries
into L2-normalised vectors, then scores via cosine similarity (equivalent
to the dot product of unit vectors).

Hard rules (AGENTS.md):
- CPU-only; no CUDA code paths.
- No hardcoded synonym lists, keyword rewrites, or salvage loops.
- Stdlib ``logging`` only; no ``print()``.
- No ``Any`` types.
- Negative cosine values are clamped to 0.0 (AdapterCandidate.score >= 0.0).

E5-family prefix convention (Wang et al., 2022):
    https://arxiv.org/abs/2212.03533
    Queries:  "query: {text}"
    Passages: "passage: {text}"
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# E5-family model prefix (Wang et al. 2022, Multilingual-E5).
_E5_FAMILY_PREFIX = "intfloat/multilingual-e5-"
_DEFAULT_QUERY_PREFIX = "query: "
_DEFAULT_PASSAGE_PREFIX = "passage: "


class DenseBackendLoadError(Exception):
    """Raised when the encoder model cannot be loaded or hashed.

    Caught by ``build_retriever_from_env`` (T027) to trigger the
    DegradationRecord fail-open path (FR-002 / SC-005).
    """


class DenseBackend:
    """Semantic (dense) retrieval backend satisfying the ``Retriever`` protocol.

    Construction is two-phase:
    1. ``__init__``: records ``model_id`` and prefixes; no network I/O.
    2. ``rebuild(corpus)``: lazy-loads the encoder on first call, embeds all
       ``search_hint`` values, stores L2-normalised matrix.

    Args:
        model_id: HuggingFace model identifier.  Default:
            ``intfloat/multilingual-e5-small``.
        query_prefix: Prefix prepended to each query text before encoding.
            If ``None``, derived from ``model_id`` (E5-family → ``"query: "``,
            others → ``""``).
        passage_prefix: Prefix prepended to each corpus passage before
            encoding.  If ``None``, derived similarly.
    """

    def __init__(
        self,
        model_id: str = "intfloat/multilingual-e5-small",
        *,
        query_prefix: str | None = None,
        passage_prefix: str | None = None,
        cold_start: Literal["lazy", "eager"] = "lazy",
    ) -> None:
        self._model_id: str = model_id
        is_e5 = model_id.startswith(_E5_FAMILY_PREFIX)
        self._query_prefix: str = (
            query_prefix if query_prefix is not None else (_DEFAULT_QUERY_PREFIX if is_e5 else "")
        )
        self._passage_prefix: str = (
            passage_prefix
            if passage_prefix is not None
            else (_DEFAULT_PASSAGE_PREFIX if is_e5 else "")
        )
        self._cold_start: Literal["lazy", "eager"] = cold_start

        # Populated by rebuild() or lazy score().
        self._encoder: object | None = None
        self._tool_ids: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._weight_sha256: str = ""
        self._tokenizer_version: str = ""
        self._embedding_dim: int = 0
        # Corpus buffered between rebuild() (lazy mode, pre-load) and the
        # first .score() call that triggers the encoder load. None when no
        # corpus is pending (either cleared after embed or never set).
        self._pending_corpus: dict[str, str] | None = None

    # ------------------------------------------------------------------
    # Retriever protocol
    # ------------------------------------------------------------------

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Rebuild the dense index from ``{tool_id: search_hint}``.

        Cold-start behaviour (spec 026 FR-011 / NFR-BootBudget):

        * ``cold_start="lazy"`` (default): if the encoder has not been
          loaded yet, buffer *corpus* in ``_pending_corpus`` and return
          without touching HuggingFace. The first ``.score()`` call then
          loads the encoder and embeds the buffered corpus on demand so
          boot paths that register tools (which forces rebuild during
          startup) do not pay the model-load cost until an actual query
          arrives.
        * ``cold_start="eager"`` (opt-in): always load the encoder on
          first non-empty rebuild and embed synchronously. Preserved for
          warm pools, tests, and tooling that need deterministic
          post-rebuild state.

        Once the encoder is loaded, subsequent rebuild calls always
        re-embed in place regardless of cold-start mode — the flag only
        controls the *first* load.

        Args:
            corpus: Mapping of ``tool_id → search_hint``. Empty dict
                resets the index without triggering a model load.

        Raises:
            DenseBackendLoadError: If the encoder cannot be loaded or
                the weight file cannot be hashed. Only raised when the
                load is actually attempted (eager mode, or lazy mode
                after the encoder is already present).
        """
        if not corpus:
            self._tool_ids = []
            self._embeddings = None
            self._pending_corpus = None
            logger.debug("DenseBackend: empty corpus, index cleared")
            return

        # Lazy mode + encoder not yet loaded → defer load to first .score().
        # We still expose _tool_ids so that a read-only caller inspecting
        # the registry can see which tools *will* be ranked, without
        # paying the model-load cost at boot.
        if self._encoder is None and self._cold_start == "lazy":
            self._tool_ids = list(corpus.keys())
            self._embeddings = None
            self._pending_corpus = dict(corpus)
            logger.debug(
                "DenseBackend: lazy cold-start — buffered %d passages, "
                "encoder load deferred to first .score()",
                len(self._tool_ids),
            )
            return

        # Eager path, or lazy path after a prior score() already loaded.
        if self._encoder is None:
            self._encoder = self._load_encoder()

        self._embed_corpus(corpus)

    def _embed_corpus(self, corpus: dict[str, str]) -> None:
        """Encode *corpus* and populate embedding state.

        Precondition: ``self._encoder`` is non-None. Callers are
        responsible for triggering the lazy load before invoking this
        helper so it stays a pure embed step with no I/O surface.
        """
        assert self._encoder is not None, "_embed_corpus called before encoder load"
        self._tool_ids = list(corpus.keys())
        passages = [self._passage_prefix + hint for hint in corpus.values()]

        encoder = self._encoder
        raw: np.ndarray = encoder.encode(  # type: ignore[attr-defined]
            passages,
            convert_to_numpy=True,
            normalize_embeddings=False,
            batch_size=32,
            show_progress_bar=False,
        )

        self._embeddings = self._l2_normalise(raw)
        # sentence-transformers >= 3.x renamed the method; try new API first.
        if hasattr(encoder, "get_embedding_dimension"):
            self._embedding_dim = int(encoder.get_embedding_dimension())
        else:
            self._embedding_dim = int(encoder.get_sentence_embedding_dimension())  # type: ignore[attr-defined]
        # Clear any pending buffer — it has been realised into embeddings.
        self._pending_corpus = None
        logger.debug(
            "DenseBackend: indexed %d passages, dim=%d",
            len(self._tool_ids),
            self._embedding_dim,
        )

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return ``(tool_id, cosine_score)`` pairs for *query*.

        Scores are in ``[0.0, 1.0]`` (negatives clamped to 0.0).
        Returns ``[]`` when the corpus is empty.

        Lazy cold-start semantics: if a corpus was buffered by a prior
        ``rebuild()`` under ``cold_start="lazy"``, this method triggers
        the encoder load and embeds the buffered passages before
        scoring. On load failure the pending buffer is cleared and a
        ``DenseBackendLoadError`` is re-raised so the outer fail-open
        wrapper (``_DenseFailOpenWrapper`` for pure-dense, or
        ``HybridBackend`` for hybrid) can swap in its BM25 companion.
        Without this re-raise, pure-dense lazy-load failure would
        silently return ``[]`` forever — a hard regression surfaced by
        Codex review round 5 on #837.

        After buffers are cleared, subsequent ``.score()`` calls return
        ``[]`` (not raise), because ``_pending_corpus is None`` on the
        degraded instance. The wrapper remembers its degraded state and
        serves BM25 from the first failure onward.

        Args:
            query: Free-text citizen query.

        Returns:
            Unordered list of ``(tool_id, score)`` pairs; downstream
            tie-break (score DESC, tool_id ASC) is applied by
            ``kosmos.tools.search``.

        Raises:
            DenseBackendLoadError: On the first lazy load failure only.
                Wrapped exceptions (RuntimeError, OSError, ValueError,
                MemoryError) raised by sentence-transformers are
                re-packaged under this type so callers can catch a
                single class.
        """
        # Lazy fire: pending corpus → load encoder + embed before scoring.
        # Failures here clear the buffers and re-raise as
        # DenseBackendLoadError so the outer fail-open wrapper can swap
        # in BM25 for this AND all subsequent queries. Clearing the
        # buffers means the retry branch (``_pending_corpus is not None``)
        # does not fire again — the single WARN contract is preserved by
        # the wrapper latching its own ``_degraded`` flag.
        if self._pending_corpus is not None and self._encoder is None:
            try:
                self._encoder = self._load_encoder()
                self._embed_corpus(self._pending_corpus)
            except (
                DenseBackendLoadError,
                RuntimeError,
                OSError,
                ValueError,
                MemoryError,
            ) as exc:
                logger.warning(
                    "DenseBackend.score: lazy encoder load failed "
                    "(%s: %s) — clearing pending corpus, re-raising for "
                    "fail-open wrapper",
                    type(exc).__name__,
                    exc,
                )
                self._pending_corpus = None
                self._embeddings = None
                self._tool_ids = []
                if isinstance(exc, DenseBackendLoadError):
                    raise
                raise DenseBackendLoadError(
                    f"Lazy encoder load failed: {type(exc).__name__}: {exc}"
                ) from exc

        if self._embeddings is None or not self._tool_ids:
            return []

        q_text = self._query_prefix + query
        assert self._encoder is not None  # guaranteed by rebuild() having populated embeddings
        encoder = self._encoder
        try:
            q_raw: np.ndarray = encoder.encode(  # type: ignore[attr-defined]
                [q_text],
                convert_to_numpy=True,
                normalize_embeddings=False,
                batch_size=1,
                show_progress_bar=False,
            )
        except (RuntimeError, OSError, ValueError, MemoryError) as exc:
            # FR-002 fail-open: mid-session encoder failure (CUDA OOM, tokenizer
            # crash, corrupted weight buffer) must degrade to empty ranking so
            # HybridBackend can reuse its BM25 fallback and the citizen path
            # never surfaces 5xx. search.py also wraps .score() as a belt-and-
            # suspenders backstop; both layers log independently so the WARN
            # nearest the root cause is preserved.
            logger.warning(
                "DenseBackend.score: encoder failed (%s: %s) — returning empty ranking",
                type(exc).__name__,
                exc,
            )
            return []
        q_vec = self._l2_normalise(q_raw)[0]  # shape (d,)

        # Cosine = dot product of unit vectors.
        cosines: np.ndarray = self._embeddings @ q_vec  # shape (N,)

        # Clamp negatives to 0.0 (AdapterCandidate.score >= 0.0 invariant).
        cosines = np.maximum(0.0, cosines)

        return [(tid, float(cosines[i])) for i, tid in enumerate(self._tool_ids)]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_encoder(self) -> object:
        """Load the SentenceTransformer encoder and populate metadata.

        License enforcement is **design-time**, not runtime: the spec
        (spec.md:247) and quickstart (quickstart.md:167) pin the
        Apache-2.0-compatible model shortlist
        (multilingual-e5-small/large, paraphrase-multilingual-MiniLM-
        L12-v2, BAAI/bge-m3) during research. This method intentionally
        does NOT introspect HF card metadata at load time — doing so
        would couple runtime behaviour to HuggingFace availability and
        create a startup failure mode that the fail-open path (FR-002)
        cannot distinguish from a corrupted weight file. Operators who
        override ``KOSMOS_RETRIEVAL_MODEL_ID`` are responsible for
        staying inside the shortlist; the release manifest (FR-004)
        records the weight hash so license provenance is auditable
        post-hoc.

        Returns:
            A loaded ``SentenceTransformer`` instance.

        Raises:
            DenseBackendLoadError: On any load or hash failure.
        """
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("DenseBackend: loading encoder %r (CPU)", self._model_id)
            # CPU-only contract (AGENTS.md): pass explicit device to prevent
            # SentenceTransformer from auto-selecting CUDA/MPS when available.
            encoder = SentenceTransformer(self._model_id, device="cpu")
        except Exception as exc:
            raise DenseBackendLoadError(
                f"Failed to load SentenceTransformer({self._model_id!r}): {exc}"
            ) from exc

        # Capture tokenizer library version for RetrievalManifest (FR-004).
        # Use actual installed tokenizers/transformers package version so the
        # release manifest can pin the exact tokenisation behaviour — not the
        # model slug, which says nothing about tokenisation code.
        try:
            import tokenizers as _tokenizers_pkg  # type: ignore[import-untyped]

            self._tokenizer_version = f"tokenizers=={_tokenizers_pkg.__version__}"
        except Exception:  # pragma: no cover
            try:
                import transformers as _transformers_pkg

                self._tokenizer_version = f"transformers=={_transformers_pkg.__version__}"
            except Exception:
                self._tokenizer_version = "unknown"

        # Hash the primary weight file for RetrievalManifest.
        try:
            weight_path = self._find_weight_file(self._model_id)
            self._weight_sha256 = self._sha256_file(weight_path)
        except Exception as exc:
            raise DenseBackendLoadError(
                f"Failed to hash weight file for {self._model_id!r}: {exc}"
            ) from exc

        logger.info(
            "DenseBackend: encoder loaded, weight_sha256=%s…, tokenizer_version=%r",
            self._weight_sha256[:12],
            self._tokenizer_version,
        )
        return encoder

    @staticmethod
    def _find_weight_file(model_id: str) -> str:
        """Locate the primary weight file in the HuggingFace hub cache.

        Tries ``model.safetensors`` first (preferred), then
        ``pytorch_model.bin`` as fallback. Resolves via
        ``huggingface_hub.snapshot_download`` which returns a cached
        local path without re-downloading.

        Args:
            model_id: HuggingFace model identifier.

        Returns:
            Absolute path to the weight file as a string.

        Raises:
            FileNotFoundError: If no weight file is found.
        """
        try:
            from huggingface_hub import snapshot_download

            local_dir = snapshot_download(model_id, local_files_only=True)
        except Exception:
            # Fallback: resolve via sentence_transformers internal path
            try:
                from huggingface_hub import hf_hub_download
                from sentence_transformers import SentenceTransformer  # noqa: F401

                # The SentenceTransformer model directory is the first module's
                # save directory after download; use a heuristic path.

                local_dir = str(
                    Path(hf_hub_download(model_id, "config.json", local_files_only=True)).parent
                )
            except Exception as inner:
                raise FileNotFoundError(
                    f"Cannot locate HF cache dir for {model_id!r}: {inner}"
                ) from inner

        # Only actual weight files are acceptable — hashing a config.json
        # would produce a stable digest that is meaningless for manifest
        # pinning. Scan shallowly and recursively (sentence-transformers
        # sometimes nests weights under a transformer sub-module dir).
        local_root = Path(local_dir)
        for filename in ("model.safetensors", "pytorch_model.bin"):
            direct = local_root / filename
            if direct.exists():
                return str(direct)
        for filename in ("model.safetensors", "pytorch_model.bin"):
            for nested in local_root.rglob(filename):
                if nested.is_file():
                    return str(nested)

        raise FileNotFoundError(
            f"No weight file (model.safetensors or pytorch_model.bin) found in "
            f"{local_dir!r} for model {model_id!r}"
        )

    @staticmethod
    def _sha256_file(path: str) -> str:
        """Return the hex-encoded SHA-256 digest of a file.

        Args:
            path: Absolute path to the file.

        Returns:
            64-character lowercase hex string.
        """
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _l2_normalise(matrix: np.ndarray) -> np.ndarray:
        """L2-normalise each row of *matrix* in-place (safe against zero norm).

        Args:
            matrix: 2-D array of shape ``(N, d)``.

        Returns:
            Row-normalised copy; rows with zero norm are left as-is.
        """
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return matrix / norms
