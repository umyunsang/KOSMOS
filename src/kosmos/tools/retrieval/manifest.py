# SPDX-License-Identifier: Apache-2.0
"""Reproducibility manifest for retrieval backends (spec 026, FR-004).

The manifest surfaces the weight hash + tokenizer version so Epic #467
can fold them into the release manifest. This spec owns the semantic
shape; #467 owns the on-disk format.

Non-dense backends populate only ``backend`` and ``built_at`` — the
``@model_validator`` below enforces the bm25 ↔ None vs dense/hybrid ↔
populated correlation so invalid manifests fail at construction, not at
manifest-emit time (fail-closed per Constitution Principle II).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetrievalManifest(BaseModel):
    """Pydantic v2 manifest describing the active retrieval backend.

    All fields are immutable post-construction (``frozen=True``) and
    unknown fields are rejected (``extra="forbid"``) so downstream
    consumers cannot accidentally see typo'd keys.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = Field(
        ...,
        pattern="^(bm25|dense|hybrid)$",
        description="Backend label. One of bm25 | dense | hybrid.",
    )
    model_id: str | None = Field(
        default=None,
        description="HF model id when backend != bm25; None otherwise.",
    )
    weight_sha256: str | None = Field(
        default=None,
        pattern="^([a-f0-9]{64})?$",
        description="SHA-256 of the primary weight file; None for bm25.",
    )
    tokenizer_version: str | None = Field(
        default=None,
        description="Tokenizer version from HF; None for bm25.",
    )
    embedding_dim: int | None = Field(
        default=None,
        ge=1,
        description="Dense embedding dimension; None for bm25.",
    )
    built_at: str = Field(
        ...,
        description="RFC 3339 / ISO 8601 UTC timestamp at manifest emission.",
    )

    @model_validator(mode="after")
    def _enforce_backend_field_correlation(self) -> RetrievalManifest:
        """Enforce bm25 ↔ all-None vs dense/hybrid ↔ all-populated.

        Prevents partially-specified manifests from reaching Epic #467's
        consumer, which is the contract point where a missing weight
        hash would become a reproducibility hole.
        """
        dense_fields = {
            "model_id": self.model_id,
            "weight_sha256": self.weight_sha256,
            "tokenizer_version": self.tokenizer_version,
            "embedding_dim": self.embedding_dim,
        }

        if self.backend == "bm25":
            populated = [name for name, value in dense_fields.items() if value is not None]
            if populated:
                raise ValueError(
                    "RetrievalManifest(backend='bm25') MUST leave "
                    f"{populated} unset; got populated values."
                )
        else:  # dense | hybrid
            missing = [name for name, value in dense_fields.items() if value is None]
            if missing:
                raise ValueError(
                    f"RetrievalManifest(backend={self.backend!r}) MUST populate "
                    f"{missing}; got None."
                )

        return self
