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

from typing import Any

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

    def __init__(self, model_id: str) -> None:  # noqa: ARG002
        self.model_id = model_id
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

    def __init__(self, model_id: str) -> None:  # noqa: ARG002
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


def _make_backend(model_id: str = "intfloat/multilingual-e5-small") -> DenseBackend:
    return DenseBackend(model_id=model_id)


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
        backend = _make_backend()
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
        backend = _make_backend()
        backend.rebuild({"tool_a": "some hint"})

        assert isinstance(backend._weight_sha256, str)
        assert len(backend._weight_sha256) == 64, (
            f"SHA-256 should be 64 hex chars, got: {backend._weight_sha256!r}"
        )

    def test_tokenizer_version_populated_after_rebuild(self, stub_encoder: None) -> None:
        """_tokenizer_version must be a non-empty string after rebuild()."""
        backend = _make_backend()
        backend.rebuild({"tool_a": "some hint"})

        assert isinstance(backend._tokenizer_version, str)
        assert len(backend._tokenizer_version) > 0


class TestDenseBackendLoadError:
    """Verify DenseBackendLoadError is raised on encoder failure."""

    def test_load_error_raised_when_encoder_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DenseBackendLoadError must be raised if SentenceTransformer raises on init."""

        def _failing_transformer(model_id: str) -> None:
            raise RuntimeError("simulated encoder failure")

        monkeypatch.setattr("sentence_transformers.SentenceTransformer", _failing_transformer)

        backend = _make_backend()
        with pytest.raises(DenseBackendLoadError):
            backend.rebuild({"tool_a": "some hint"})
