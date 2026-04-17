# SPDX-License-Identifier: Apache-2.0
"""DenseBackend mocked-encoder tests (spec 026, T018).

Uses monkeypatch.setattr to replace sentence_transformers.SentenceTransformer
with a deterministic stub, so no network or GPU access is required in CI.

Verifies:
  - "query: " prefix applied on score() but not on corpus (passage uses "passage: ").
  - L2-normalisation before cosine similarity.
  - cos < 0 clamped to 0.0 (satisfies AdapterCandidate.score: float >= 0.0).
  - Empty corpus short-circuit (no encoder call; returns []).
  - Cardinality: len(score(q)) == len(corpus).
  - _weight_sha256 populated after first rebuild().
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pytest

from kosmos.tools.retrieval.dense_backend import DenseBackend, DenseBackendLoadError  # noqa: F401

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _FixedStubTransformer:
    """Deterministic SentenceTransformer stub.

    Returns fixed embeddings depending on the prefix of the text:
    - "passage: " prefix → returns _passage_vec
    - "query: " prefix  → returns _query_vec
    - No prefix         → returns _no_prefix_vec

    All returned embeddings are unit-length so cosine = dot product.
    """

    # Orthogonal 3-D basis vectors for unambiguous prefix detection.
    _passage_vec: np.ndarray = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    _query_vec: np.ndarray = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    _no_prefix_vec: np.ndarray = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    def __init__(self, model_id: str, *, device: str | None = None) -> None:  # noqa: ARG002
        self.model_id = model_id
        self.device = device
        self.tokenizer = _FakeTokenizer(model_id)

    def encode(  # noqa: PLR0913
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool = True,  # noqa: ARG002
        normalize_embeddings: bool = False,  # noqa: ARG002
        batch_size: int = 32,  # noqa: ARG002
        show_progress_bar: bool = False,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> np.ndarray:
        rows = []
        for text in texts:
            if text.startswith("passage: "):
                rows.append(self._passage_vec.copy())
            elif text.startswith("query: "):
                rows.append(self._query_vec.copy())
            else:
                rows.append(self._no_prefix_vec.copy())
        return np.stack(rows, axis=0)

    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def get_embedding_dimension(self) -> int:
        return 3


class _FakeTokenizer:
    def __init__(self, model_id: str) -> None:
        self.init_kwargs = {"name_or_path": model_id}


class _NegativeScoreStub:
    """Returns vectors whose dot product yields a negative cosine."""

    def __init__(self, model_id: str, *, device: str | None = None) -> None:  # noqa: ARG002
        self.device = device
        self.tokenizer = _FakeTokenizer(model_id)

    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool = True,  # noqa: ARG002
        normalize_embeddings: bool = False,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> np.ndarray:
        # Return vectors pointing in opposite hemispheres for query vs passage:
        # query: [1, 0, 0], passage: [-1, 0, 0] → dot = -1 (before normalisation)
        rows = []
        for text in texts:
            if text.startswith("query: "):
                rows.append(np.array([1.0, 0.0, 0.0], dtype=np.float32))
            else:
                rows.append(np.array([-1.0, 0.0, 0.0], dtype=np.float32))
        return np.stack(rows, axis=0)

    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def get_embedding_dimension(self) -> int:
        return 3


# ---------------------------------------------------------------------------
# Shared fixture: patch both SentenceTransformer AND _find_weight_file
# so tests never hit the network or file system.
# ---------------------------------------------------------------------------

_FAKE_SHA256 = "a" * 64  # 64-char fake hex digest


@pytest.fixture()
def stub_encoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch SentenceTransformer + weight-file lookup for offline testing."""
    monkeypatch.setattr("sentence_transformers.SentenceTransformer", _FixedStubTransformer)
    monkeypatch.setattr(
        "kosmos.tools.retrieval.dense_backend.DenseBackend._find_weight_file",
        staticmethod(lambda model_id: "/fake/path/model.safetensors"),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "kosmos.tools.retrieval.dense_backend.DenseBackend._sha256_file",
        staticmethod(lambda path: _FAKE_SHA256),  # noqa: ARG005
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_backend(
    model_id: str = "intfloat/multilingual-e5-small",
    *,
    cold_start: Literal["lazy", "eager"] = "lazy",
) -> DenseBackend:
    """Build a ``DenseBackend`` instance for tests.

    ``cold_start`` defaults to ``"lazy"`` to match the production default
    (FR-011 / NFR-BootBudget). Tests that inspect post-rebuild state
    (weight hash, tokenizer version, or encoder-call side effects during
    rebuild) must pass ``cold_start="eager"`` to force synchronous load.
    """
    return DenseBackend(model_id=model_id, cold_start=cold_start)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDenseBackendPrefixes:
    """Verify query vs passage prefix application."""

    def test_query_prefix_applied_on_score(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """score() must prepend 'query: ' when model_id starts with 'intfloat/multilingual-e5-'."""
        seen_texts: list[str] = []

        class _Tracker(_FixedStubTransformer):
            def encode(self, texts: list[str], **kwargs: Any) -> np.ndarray:
                seen_texts.extend(texts)
                return super().encode(texts, **kwargs)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _Tracker)
        backend = _make_backend()
        corpus = {"tool_a": "교통사고 위험지점"}
        backend.rebuild(corpus)

        # Reset tracking after rebuild (we only care about score's prefix).
        seen_texts.clear()
        backend.score("도로 위험")

        # The query text must start with "query: "
        assert any(t.startswith("query: ") for t in seen_texts), (
            f"Expected 'query: ' prefix on score() call; got: {seen_texts}"
        )

    def test_passage_prefix_applied_on_rebuild(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rebuild() must prepend 'passage: ' for E5-family models."""
        seen_texts: list[str] = []

        class _PassageTracker(_FixedStubTransformer):
            def encode(self, texts: list[str], **kwargs: Any) -> np.ndarray:
                seen_texts.extend(texts)
                return super().encode(texts, **kwargs)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _PassageTracker)
        # Eager so rebuild() actually invokes the encoder (lazy would defer to score()).
        backend = _make_backend(cold_start="eager")
        corpus = {"tool_a": "교통사고", "tool_b": "날씨 예보"}
        backend.rebuild(corpus)

        passage_texts = [t for t in seen_texts if t.startswith("passage: ")]
        assert len(passage_texts) == 2, f"Expected 2 passage-prefixed texts; got: {seen_texts}"

    def test_no_prefix_for_non_e5_model(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-E5 model_id must not add prefixes."""
        seen_texts: list[str] = []

        class _NonE5Tracker(_FixedStubTransformer):
            def encode(self, texts: list[str], **kwargs: Any) -> np.ndarray:
                seen_texts.extend(texts)
                return super().encode(texts, **kwargs)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _NonE5Tracker)
        backend = DenseBackend(model_id="generic-model/some-bert")
        corpus = {"tool_a": "some text"}
        backend.rebuild(corpus)

        seen_texts.clear()
        backend.score("query text")

        assert not any(t.startswith("query: ") or t.startswith("passage: ") for t in seen_texts), (
            f"Non-E5 model should have no prefix; got: {seen_texts}"
        )


class TestDenseBackendNormalisation:
    """Verify L2-normalisation and cosine computation."""

    def test_cosine_equals_dot_product_of_unit_vectors(self, stub_encoder: None) -> None:
        """For unit vectors, cosine = dot product; verify numerically."""
        backend = _make_backend()
        corpus = {"passage_tool": "some passage"}
        backend.rebuild(corpus)

        result = dict(backend.score("some query"))

        # passage_vec = [1,0,0], query_vec = [0,1,0] → dot = 0.0 → clamped to 0.0
        assert abs(result["passage_tool"] - 0.0) < 1e-6

    def test_negative_cosine_clamped_to_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Negative cosine similarities must be clamped to 0.0."""
        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _NegativeScoreStub)
        monkeypatch.setattr(
            "kosmos.tools.retrieval.dense_backend.DenseBackend._find_weight_file",
            staticmethod(lambda model_id: "/fake/path/model.safetensors"),
        )
        monkeypatch.setattr(
            "kosmos.tools.retrieval.dense_backend.DenseBackend._sha256_file",
            staticmethod(lambda path: _FAKE_SHA256),
        )
        backend = _make_backend()
        corpus = {"tool_x": "opposite vector passage"}
        backend.rebuild(corpus)

        result = dict(backend.score("forward query"))
        assert result["tool_x"] == 0.0, (
            f"Expected negative cosine clamped to 0.0, got {result['tool_x']}"
        )


class TestDenseBackendEmptyCorpus:
    """Verify empty-corpus behaviour."""

    def test_empty_corpus_returns_empty_list(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """score() must return [] when corpus is empty."""
        call_count = {"n": 0}

        class _TrackingStub(_FixedStubTransformer):
            def encode(self, texts: list[str], **kwargs: Any) -> np.ndarray:
                call_count["n"] += 1
                return super().encode(texts, **kwargs)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _TrackingStub)
        backend = _make_backend()
        # Rebuild with non-empty corpus first to load the encoder.
        backend.rebuild({"tool_a": "hint"})
        # Now clear with empty corpus.
        backend.rebuild({})

        initial_calls = call_count["n"]
        result = backend.score("any query")

        assert result == [], f"Expected [], got {result}"
        # No additional encode call for the query when corpus is empty.
        assert call_count["n"] == initial_calls, (
            "Encoder was called on score() with empty corpus — should short-circuit"
        )

    def test_score_before_any_rebuild_returns_empty(self, stub_encoder: None) -> None:
        """score() on a freshly constructed DenseBackend (no rebuild) must return []."""
        backend = _make_backend()
        # Do NOT call rebuild; verify [] is returned for empty state.
        result = backend.score("any query")
        assert result == []


class TestDenseBackendCardinality:
    """Verify output cardinality matches corpus size."""

    @pytest.mark.parametrize("n", [1, 3, 4])
    def test_score_cardinality_matches_corpus(self, n: int, stub_encoder: None) -> None:
        """len(score(q)) must equal len(corpus) for any non-empty corpus."""
        backend = _make_backend()
        corpus = {f"tool_{i}": f"hint {i}" for i in range(n)}
        backend.rebuild(corpus)

        result = backend.score("test query")
        assert len(result) == n, f"Expected {n} results, got {len(result)}"


class TestDenseBackendWeightHash:
    """Verify _weight_sha256 and _tokenizer_version are populated after rebuild."""

    def test_weight_sha256_populated_after_rebuild(self, stub_encoder: None) -> None:
        """_weight_sha256 must be a 64-char hex string after first rebuild()."""
        # Eager mode so hashing fires synchronously in rebuild (lazy would defer).
        backend = _make_backend(cold_start="eager")
        backend.rebuild({"tool_a": "some hint"})

        assert isinstance(backend._weight_sha256, str)
        assert len(backend._weight_sha256) == 64, (
            f"SHA-256 should be 64 hex chars, got: {backend._weight_sha256!r}"
        )

    def test_tokenizer_version_populated_after_rebuild(self, stub_encoder: None) -> None:
        """_tokenizer_version must be a non-empty string after rebuild()."""
        # Eager mode so metadata capture fires synchronously in rebuild.
        backend = _make_backend(cold_start="eager")
        backend.rebuild({"tool_a": "some hint"})

        assert isinstance(backend._tokenizer_version, str)
        assert len(backend._tokenizer_version) > 0


class TestDenseBackendLoadError:
    """Verify DenseBackendLoadError is raised on encoder failure."""

    def test_load_error_raised_when_encoder_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DenseBackendLoadError must be raised if SentenceTransformer raises on init.

        Uses eager cold-start so the load attempt happens inside rebuild().
        Lazy-mode load failures are exercised by TestLazyBehavior below,
        where they collapse to an empty ranking instead of raising
        (FR-002 fail-open on the score path).
        """

        def _failing_transformer(model_id: str) -> None:
            raise RuntimeError("simulated encoder failure")

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _failing_transformer)

        backend = _make_backend(cold_start="eager")
        with pytest.raises(DenseBackendLoadError):
            backend.rebuild({"tool_a": "some hint"})


class TestLazyBehavior:
    """Verify FR-011 lazy cold-start semantics.

    Under ``cold_start="lazy"`` (the production default), ``rebuild()``
    must buffer the corpus and defer encoder load + embedding to the
    first ``.score()`` call. This keeps boot paths that register tools
    (and thus force ``rebuild`` during startup) from paying the model-
    load cost before any query arrives.
    """

    def test_lazy_rebuild_defers_encoder_load(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rebuild() under lazy cold-start must NOT instantiate the encoder."""
        init_count = {"n": 0}

        class _CountingStub(_FixedStubTransformer):
            def __init__(self, model_id: str, *, device: str | None = None) -> None:
                init_count["n"] += 1
                super().__init__(model_id, device=device)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _CountingStub)

        backend = _make_backend(cold_start="lazy")
        backend.rebuild({"tool_a": "교통사고", "tool_b": "날씨"})

        assert init_count["n"] == 0, (
            f"Lazy rebuild must not load the encoder; got {init_count['n']} init(s)"
        )
        # Embeddings must NOT be populated yet.
        assert backend._embeddings is None
        assert backend._weight_sha256 == ""
        assert backend._tokenizer_version == ""
        # But tool_ids must be visible so upstream callers see the planned corpus.
        assert backend._tool_ids == ["tool_a", "tool_b"]
        # Pending corpus must be buffered for score() to consume.
        assert backend._pending_corpus == {"tool_a": "교통사고", "tool_b": "날씨"}

    def test_lazy_score_triggers_load_and_populates_hash(
        self, stub_encoder: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """First score() call under lazy mode must load encoder and populate metadata."""
        init_count = {"n": 0}

        class _CountingStub(_FixedStubTransformer):
            def __init__(self, model_id: str, *, device: str | None = None) -> None:
                init_count["n"] += 1
                super().__init__(model_id, device=device)

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _CountingStub)

        backend = _make_backend(cold_start="lazy")
        backend.rebuild({"tool_a": "교통사고"})
        assert init_count["n"] == 0  # precondition: lazy hasn't fired yet

        result = backend.score("도로 위험")

        assert init_count["n"] == 1, "Lazy score() must load encoder exactly once"
        assert len(result) == 1 and result[0][0] == "tool_a"
        # Metadata must now be populated via _load_encoder().
        assert len(backend._weight_sha256) == 64
        assert backend._tokenizer_version != ""
        assert backend._embeddings is not None
        # Pending buffer must be cleared after successful embed.
        assert backend._pending_corpus is None

        # A second score() call must reuse the already-loaded encoder — no re-init.
        backend.score("다른 질의")
        assert init_count["n"] == 1, "Encoder must be loaded exactly once across calls"

    def test_lazy_score_load_failure_raises_and_clears_pending(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lazy encoder load failure must raise DenseBackendLoadError + clear buffers.

        Codex review round 5 on #837: the previous contract (return [])
        silently 0-recalled under ``KOSMOS_RETRIEVAL_BACKEND=dense``
        because ``ToolRegistry.register()``'s fail-open path already
        ran at register-time. The new contract re-raises so the outer
        wrapper (``_DenseFailOpenWrapper`` for pure-dense, or
        ``HybridBackend`` for hybrid) can swap in BM25. Subsequent
        calls on the same bare instance still return [] safely because
        ``_pending_corpus`` has been cleared.
        """

        def _failing_transformer(model_id: str) -> None:
            raise RuntimeError("simulated encoder failure")

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _failing_transformer)
        # _find_weight_file / _sha256_file won't be reached because load fails first,
        # but we patch them defensively so the test can't accidentally hit disk.
        monkeypatch.setattr(
            "kosmos.tools.retrieval.dense_backend.DenseBackend._find_weight_file",
            staticmethod(lambda model_id: "/fake/path/model.safetensors"),  # noqa: ARG005
        )
        monkeypatch.setattr(
            "kosmos.tools.retrieval.dense_backend.DenseBackend._sha256_file",
            staticmethod(lambda path: _FAKE_SHA256),  # noqa: ARG005
        )

        backend = _make_backend(cold_start="lazy")
        backend.rebuild({"tool_a": "교통사고"})  # buffers corpus, no load yet

        # First score() triggers load — must raise DenseBackendLoadError.
        with pytest.raises(DenseBackendLoadError):
            backend.score("도로 위험")

        # Pending state must be cleared so subsequent queries do NOT retry.
        assert backend._pending_corpus is None
        assert backend._embeddings is None
        assert backend._tool_ids == []
        assert backend._encoder is None

        # Subsequent score() on the same (now-degraded) bare instance
        # returns [] — no retry, no raise — so outer wrappers that miss
        # the first raise still behave safely.
        result2 = backend.score("다른 질의")
        assert result2 == []
