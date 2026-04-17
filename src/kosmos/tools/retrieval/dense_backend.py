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
from typing import TYPE_CHECKING

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

        # Populated by rebuild().
        self._encoder: object | None = None
        self._tool_ids: list[str] = []
        self._embeddings: np.ndarray | None = None
        self._weight_sha256: str = ""
        self._tokenizer_version: str = ""
        self._embedding_dim: int = 0

    # ------------------------------------------------------------------
    # Retriever protocol
    # ------------------------------------------------------------------

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Rebuild the dense index from ``{tool_id: search_hint}``.

        On first call: loads the encoder from HuggingFace (or local cache).
        On subsequent calls: re-embeds without reloading the encoder.

        Args:
            corpus: Mapping of ``tool_id → search_hint``. Empty dict resets
                the index without triggering a model load.

        Raises:
            DenseBackendLoadError: If the encoder cannot be loaded or the
                weight file cannot be hashed.
        """
        if not corpus:
            self._tool_ids = []
            self._embeddings = None
            logger.debug("DenseBackend: empty corpus, index cleared")
            return

        # Lazy-load the encoder on first non-empty rebuild.
        if self._encoder is None:
            self._encoder = self._load_encoder()

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
        logger.debug(
            "DenseBackend: indexed %d passages, dim=%d",
            len(self._tool_ids),
            self._embedding_dim,
        )

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return ``(tool_id, cosine_score)`` pairs for *query*.

        Scores are in ``[0.0, 1.0]`` (negatives clamped to 0.0).
        Returns ``[]`` when the corpus is empty.

        Args:
            query: Free-text citizen query.

        Returns:
            Unordered list of ``(tool_id, score)`` pairs; downstream
            tie-break (score DESC, tool_id ASC) is applied by
            ``kosmos.tools.search``.
        """
        if self._embeddings is None or not self._tool_ids:
            return []

        q_text = self._query_prefix + query
        assert self._encoder is not None  # guaranteed by rebuild() having populated embeddings
        encoder = self._encoder
        q_raw: np.ndarray = encoder.encode(  # type: ignore[attr-defined]
            [q_text],
            convert_to_numpy=True,
            normalize_embeddings=False,
            batch_size=1,
            show_progress_bar=False,
        )
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
