# SPDX-License-Identifier: Apache-2.0
"""RetrievalManifest validation tests (spec 026, T016).

Covers:
- bm25 happy path (all dense fields None)
- dense happy path (all dense fields populated)
- hybrid happy path (same as dense)
- bm25 rejects populated dense field
- dense rejects missing weight_sha256
- invalid SHA-256 pattern rejected at field level
- invalid built_at accepted/rejected at model-validator level (str field, no
  ISO validation at pydantic layer — see note below)
- frozen=True enforced
- extra="forbid" enforced

Note on built_at: RetrievalManifest.built_at is typed as ``str`` with no
pydantic datetime validator, so invalid ISO strings pass field validation.
The spec mandates ISO 8601 at the application layer; the field constraint is
intentionally left to the emitter (DenseBackend).  test_invalid_built_at
therefore asserts that a non-ISO string does NOT raise ValidationError at
construction time — any stricter validation is a future spec concern.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.tools.retrieval.manifest import RetrievalManifest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_VALID_SHA256 = "a" * 64  # 64 lowercase hex chars — matches ^[a-f0-9]{64}$

_DENSE_KWARGS: dict = {
    "backend": "dense",
    "model_id": "intfloat/multilingual-e5-small",
    "weight_sha256": _VALID_SHA256,
    "tokenizer_version": "4.39.3",
    "embedding_dim": 384,
    "built_at": "2026-04-17T00:00:00Z",
}


def _dense_kwargs(**overrides) -> dict:
    """Return a copy of _DENSE_KWARGS with any overrides applied."""
    return {**_DENSE_KWARGS, **overrides}


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_bm25_happy_path() -> None:
    """backend='bm25' with all dense fields absent constructs successfully."""
    manifest = RetrievalManifest(
        backend="bm25",
        built_at="2026-04-17T00:00:00Z",
    )
    assert manifest.backend == "bm25"
    assert manifest.model_id is None
    assert manifest.weight_sha256 is None
    assert manifest.tokenizer_version is None
    assert manifest.embedding_dim is None


def test_dense_happy_path() -> None:
    """backend='dense' with all dense fields populated constructs successfully."""
    manifest = RetrievalManifest(**_dense_kwargs())
    assert manifest.backend == "dense"
    assert manifest.model_id == "intfloat/multilingual-e5-small"
    assert manifest.weight_sha256 == _VALID_SHA256
    assert manifest.tokenizer_version == "4.39.3"
    assert manifest.embedding_dim == 384
    assert manifest.built_at == "2026-04-17T00:00:00Z"


def test_hybrid_happy_path() -> None:
    """backend='hybrid' requires the same dense fields as 'dense'."""
    manifest = RetrievalManifest(**_dense_kwargs(backend="hybrid"))
    assert manifest.backend == "hybrid"
    assert manifest.weight_sha256 == _VALID_SHA256
    assert manifest.embedding_dim == 384


# ---------------------------------------------------------------------------
# Correlation validator — bm25 rejects populated dense fields
# ---------------------------------------------------------------------------


def test_bm25_rejects_model_id() -> None:
    """backend='bm25' with model_id populated raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(
            backend="bm25",
            model_id="intfloat/multilingual-e5-small",
            built_at="2026-04-17T00:00:00Z",
        )


def test_bm25_rejects_weight_sha256() -> None:
    """backend='bm25' with weight_sha256 populated raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(
            backend="bm25",
            weight_sha256=_VALID_SHA256,
            built_at="2026-04-17T00:00:00Z",
        )


def test_bm25_rejects_tokenizer_version() -> None:
    """backend='bm25' with tokenizer_version populated raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(
            backend="bm25",
            tokenizer_version="4.39.3",
            built_at="2026-04-17T00:00:00Z",
        )


def test_bm25_rejects_embedding_dim() -> None:
    """backend='bm25' with embedding_dim populated raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(
            backend="bm25",
            embedding_dim=384,
            built_at="2026-04-17T00:00:00Z",
        )


# ---------------------------------------------------------------------------
# Correlation validator — dense/hybrid requires all dense fields
# ---------------------------------------------------------------------------


def test_dense_rejects_missing_weight_sha256() -> None:
    """backend='dense' with weight_sha256=None raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256=None))


def test_dense_rejects_missing_model_id() -> None:
    """backend='dense' with model_id=None raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(model_id=None))


def test_dense_rejects_missing_tokenizer_version() -> None:
    """backend='dense' with tokenizer_version=None raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(tokenizer_version=None))


def test_dense_rejects_missing_embedding_dim() -> None:
    """backend='dense' with embedding_dim=None raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(embedding_dim=None))


# ---------------------------------------------------------------------------
# Field-level validators
# ---------------------------------------------------------------------------


def test_invalid_sha_pattern_not_hex() -> None:
    """weight_sha256 containing non-hex chars raises ValidationError."""
    bad_sha = "g" * 64  # 'g' is outside [a-f0-9]
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256=bad_sha))


def test_invalid_sha_pattern_too_short() -> None:
    """weight_sha256 shorter than 64 chars raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256="abc123"))


def test_invalid_sha_pattern_too_long() -> None:
    """weight_sha256 longer than 64 chars raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256="a" * 65))


def test_invalid_sha_pattern_uppercase() -> None:
    """weight_sha256 containing uppercase hex chars raises ValidationError.

    The pattern ^[a-f0-9]{64}$ is lowercase-only.
    """
    uppercase_sha = "A" * 64
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256=uppercase_sha))


def test_invalid_sha_pattern_empty_string() -> None:
    """weight_sha256='' must be rejected — empty is NOT a valid digest.

    Regression for Codex round-4 P2: the previous pattern
    ``^([a-f0-9]{64})?$`` accepted the empty string because the whole
    capture group was optional, which let a dense/hybrid manifest pass
    construction with no real weight digest — weakening the
    reproducibility contract (FR-004).  The tightened pattern
    ``^[a-f0-9]{64}$`` requires exactly 64 hex chars when the field is
    supplied; None remains valid for the bm25 backend via the optional
    type annotation.
    """
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(weight_sha256=""))


def test_invalid_backend_value() -> None:
    """backend value outside {bm25, dense, hybrid} raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(backend="faiss", built_at="2026-04-17T00:00:00Z")


def test_invalid_embedding_dim_zero() -> None:
    """embedding_dim=0 violates ge=1 and raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(embedding_dim=0))


def test_invalid_embedding_dim_negative() -> None:
    """embedding_dim=-1 violates ge=1 and raises ValidationError."""
    with pytest.raises(ValidationError):
        RetrievalManifest(**_dense_kwargs(embedding_dim=-1))


# ---------------------------------------------------------------------------
# built_at — str field; no pydantic ISO validator (see module docstring)
# ---------------------------------------------------------------------------


def test_invalid_built_at_does_not_raise() -> None:
    """built_at is a plain str field; non-ISO values pass construction.

    Semantic validation is the emitter's responsibility (DenseBackend).
    This test documents the current contract boundary explicitly so that
    if a future spec adds a datetime validator here, this case will flip
    to a pytest.raises and serve as a breaking-change signal.
    """
    manifest = RetrievalManifest(
        backend="bm25",
        built_at="not-an-iso-date",
    )
    assert manifest.built_at == "not-an-iso-date"


# ---------------------------------------------------------------------------
# ConfigDict enforcement
# ---------------------------------------------------------------------------


def test_frozen_enforced() -> None:
    """Mutating a field on a frozen manifest raises ValidationError."""
    manifest = RetrievalManifest(backend="bm25", built_at="2026-04-17T00:00:00Z")
    with pytest.raises(ValidationError):
        manifest.backend = "dense"  # type: ignore[misc]


def test_extra_forbidden() -> None:
    """Unknown keyword argument raises ValidationError (extra='forbid')."""
    with pytest.raises(ValidationError):
        RetrievalManifest(
            backend="bm25",
            built_at="2026-04-17T00:00:00Z",
            foo="bar",
        )
