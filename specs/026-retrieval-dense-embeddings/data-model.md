# Phase 1 — Data Model (Feature 026)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

This document enumerates every entity introduced by Feature 026, its fields, validation rules, and relationships. All schemas are Pydantic v2 (Constitution Principle III — no `Any`). Frozen entities from prior specs (`LookupSearchInput`, `LookupSearchResult`, `AdapterCandidate`, `GovAPITool`) are listed for reference only — they are **not** modified by this feature.

---

## 1. `Retriever` Protocol (new — structural type)

**Location**: `src/kosmos/tools/retrieval/backend.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Retriever(Protocol):
    """Structural contract that every retrieval backend satisfies.

    Mirrors the current ``BM25Index`` surface byte-for-byte so that
    ``ToolRegistry`` and ``kosmos.tools.search`` depend only on this
    protocol, not on a concrete class.
    """

    def rebuild(self, corpus: dict[str, str]) -> None:
        """Rebuild the index from ``{tool_id: search_hint}``. Called on
        registry construction and on every ``register()`` / ``unregister()``.
        MUST be idempotent on repeated identical input."""
        ...

    def score(self, query: str) -> list[tuple[str, float]]:
        """Return ``[(tool_id, score)]`` pairs. Ordering is backend-
        internal; final tie-break (score DESC, tool_id ASC) is applied
        downstream in ``search_tools``."""
        ...
```

**Invariants**:
- Empty corpus → `score(q)` returns `[]` for any query (FR Edge Case: empty registry).
- Empty query → returns an all-zero score list (same cardinality as corpus).
- Non-negative scores (aligned with `AdapterCandidate.score: float ≥ 0.0`).
- Deterministic across runs modulo FP noise ≤ 1e-6 given (weights, tokenizer version, corpus, query).

**Relationships**:
- Implemented by: `BM25Backend`, `DenseBackend`, `HybridBackend`.
- Depended on by: `ToolRegistry` (via `retrieval` attribute; replaces today's `bm25_index` attribute, old name retained as alias for one release cycle per FR-009).
- Consumed by: `kosmos.tools.search.search_tools()`.

---

## 2. `BM25Backend` (new — wraps existing `BM25Index`)

**Location**: `src/kosmos/tools/retrieval/bm25_backend.py`

**Fields**:
| Field | Type | Default | Constraint |
|---|---|---|---|
| `_index` | `BM25Index` | — | Composed verbatim from `kosmos.tools.bm25_index`; behaviour unchanged. |

**Methods**: Delegates `rebuild` and `score` to `self._index`.

**Invariants**:
- Byte-identical scoring to pre-#585 code for any (query, corpus) pair.
- `test_bm25_backend.py` asserts per-query score-vector equality against a captured golden output on the committed 30-query set.

**Relationships**: Satisfies `Retriever`. Used standalone when `KOSMOS_RETRIEVAL_BACKEND=bm25` (default). Composed by `HybridBackend`.

---

## 3. `DenseBackend` (new)

**Location**: `src/kosmos/tools/retrieval/dense_backend.py`

**Fields (runtime-only; not a Pydantic model — holds non-serialisable torch tensors)**:
| Field | Type | Purpose |
|---|---|---|
| `_model_id` | `str` | HF model id (e.g., `intfloat/multilingual-e5-small`). |
| `_encoder` | `sentence_transformers.SentenceTransformer` | Loaded encoder (lazy by default). |
| `_tool_ids` | `list[str]` | Stable order; aligned with `_embeddings` rows. |
| `_embeddings` | `numpy.ndarray` of shape `(N, d)` | L2-normalised; corpus embeddings. |
| `_query_prefix` | `str` | `"query: "` for E5-family, empty for others. |
| `_passage_prefix` | `str` | `"passage: "` for E5-family, empty for others. |
| `_weight_sha256` | `str` | SHA-256 of the weight file at load time; populated into `RetrievalManifest`. |
| `_tokenizer_version` | `str` | Tokenizer version string from HF. |
| `_embedding_dim` | `int` | `self._embeddings.shape[1]`. |

**Construction contract**:
- `__init__(model_id: str, ...)` does NOT load the model under `cold_start=lazy`; it records the model id only.
- First `rebuild()` triggers load-then-embed; subsequent `rebuild()` calls re-embed only.
- On model load failure / tokenizer init failure / SHA-256 mismatch → raise `DenseBackendLoadError`; `HybridBackend` or the factory catches and degrades (FR-002).

**Scoring contract**:
- `score(query)`:
  1. If corpus is empty → return `[]`.
  2. If `_embeddings` is None (lazy not yet fired) → trigger `rebuild()` now.
  3. Encode query with `_query_prefix`; L2-normalise.
  4. Cosine = normalised dot product = `self._embeddings @ q_vec`.
  5. Return `[(tool_id, float(score))]` for every row.
- All scores clamped to `[0.0, 1.0]` via `max(0.0, cos)` to respect `AdapterCandidate.score: float ≥ 0.0` (negative cosine indicates irrelevance in unit-length space; floor at 0 is semantically equivalent for ranking).

**Invariants**:
- Determinism: identical (model, corpus, query) → identical score vector within FP tolerance.
- `_embedding_dim` matches `_encoder.get_sentence_embedding_dimension()`.

---

## 4. `HybridBackend` (new)

**Location**: `src/kosmos/tools/retrieval/hybrid.py`

**Fields**:
| Field | Type | Default | Constraint |
|---|---|---|---|
| `_bm25` | `BM25Backend` | required | Composed retriever (always the lexical retriever). |
| `_dense` | `DenseBackend` | required | Composed retriever (the semantic retriever). |
| `_rrf_k` | `int` | 60 | Constant from Cormack SIGIR 2009; overridable via `KOSMOS_RETRIEVAL_FUSION_K`. |

**Scoring contract** — Reciprocal Rank Fusion (RRF):
1. Call `_bm25.score(q)` and `_dense.score(q)` in parallel (`asyncio.gather` or sync — sync acceptable at current scale).
2. Rank each list descending by score. Handle ties via the standard competition ranking (1224): adapters tied in raw score share the same rank.
3. For each `tool_id` appearing in either list, compute `fused = 1/(k + rank_bm25) + 1/(k + rank_dense)` (treat missing as rank = N+1 where N is the retriever's output size, so missing contributes a small positive amount rather than breaking the sum).
4. Return `[(tool_id, fused)]` for every `tool_id` in the union of both inputs.

**Invariants**:
- Fused score is strictly > 0 for any `tool_id` in the union.
- Fused score is deterministic given deterministic inputs from BM25 and Dense.
- Final tie-break (score DESC, tool_id ASC) is applied downstream in `search_tools`.

**Relationships**: Satisfies `Retriever`. Consumed by factory when `KOSMOS_RETRIEVAL_BACKEND=hybrid`.

---

## 5. `RetrievalManifest` (new — Pydantic v2 model)

**Location**: `src/kosmos/tools/retrieval/manifest.py`

```python
from pydantic import BaseModel, Field, ConfigDict

class RetrievalManifest(BaseModel):
    """Reproducibility manifest surfaced into the release manifest.

    Final field names are owned by Epic #467; this spec provides the
    semantic shape. Non-dense backends populate only ``backend`` and
    ``built_at``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: str = Field(..., pattern="^(bm25|dense|hybrid)$")
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
```

**Validation rules**:
- `backend in {"bm25", "dense", "hybrid"}`.
- If `backend == "bm25"`: `model_id`, `weight_sha256`, `tokenizer_version`, `embedding_dim` MUST all be `None`.
- If `backend in {"dense", "hybrid"}`: all dense-specific fields MUST be populated.
- `built_at` is a valid ISO 8601 string; naïve timestamps rejected.

**Relationships**: Emitted by `DenseBackend` at first successful load; consumed by Epic #467's release-manifest builder. Not persisted to disk in this spec (in-memory only; manifest serialisation owned by #467).

---

## 6. `AdversarialQuerySet` (new — YAML-serialised, Pydantic-validated)

**Location**: file `eval/retrieval_queries_adversarial.yaml`; loader in `src/kosmos/eval/retrieval.py`.

**On-disk schema** (per entry):
```yaml
queries:
  - query: "아이 열이 40도 넘어요 지금 응급실 가려면 어디가 가까워요?"
    expected_tool_id: "nmc_emergency_search"
    lexical_overlap_score: 0.0
    notes: "paraphrase: 응급실 ≠ 응급의료센터 (adapter search_hint); 열 ≠ 중증"
```

**Pydantic loader**:
```python
class AdversarialQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    query: str = Field(..., min_length=1)
    expected_tool_id: str = Field(..., min_length=1)
    lexical_overlap_score: float = Field(..., ge=0.0, le=1.0)
    notes: str = Field(default="")

class AdversarialQuerySet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    queries: list[AdversarialQuery] = Field(..., min_length=20)
```

**Validation rules**:
- `min_length=20` enforces FR-012 (≥ 20 queries).
- `lexical_overlap_score == 0.0` for every entry at author time; an offline script (`scripts/check_adversarial_overlap.py`, new) computes kiwipiepy-token overlap against all registered adapters' `search_hint` and asserts zero overlap in CI.
- `expected_tool_id` MUST resolve to a registered adapter (checked by the harness at eval time).

---

## 7. `DegradationRecord` (new — in-memory only)

**Location**: `src/kosmos/tools/retrieval/degrade.py`

**Purpose**: Tracks whether a WARN has been emitted for a given registry instance, so FR-002 "exactly one WARN line per degraded registry" holds.

**Fields**:
| Field | Type | Default | Constraint |
|---|---|---|---|
| `_emitted` | `bool` | `False` | Flips to `True` after the first emission. |
| `_requested_backend` | `str` | — | `dense` or `hybrid`. |
| `_effective_backend` | `str` | — | Always `bm25`. |
| `_reason` | `str` | — | One-line cause. |

Not a Pydantic model — purely a mutable internal latch; zero serialisation surface.

---

## 8. Frozen entities (reference only — NOT modified)

These schemas appear here to make the byte-level contract surface explicit. They are locked by Epic #507 (CLOSED) and preserved by FR-003 + SC-004. `contracts/*.schema.json` snapshots guard them at CI.

### `LookupSearchInput` (frozen)

```python
class LookupSearchInput(BaseModel):
    mode: Literal["search"]
    query: str
    top_k: int | None
    domain: str | None
```

### `LookupSearchResult` (frozen)

```python
class LookupSearchResult(BaseModel):
    kind: Literal["search"]
    candidates: list[AdapterCandidate]
    total_registry_size: int
    effective_top_k: int
    reason: str
```

### `AdapterCandidate` (frozen)

```python
class AdapterCandidate(BaseModel):
    tool_id: str
    score: float  # ≥ 0.0
    required_params: list[str]
    search_hint: str
    why_matched: str
    requires_auth: bool
    is_personal_data: bool
```

### `GovAPITool` (frozen — Spec 024/025 V1–V6 invariants)

Not reprinted; reference `src/kosmos/tools/models.py`. V6 `auth_type`/`auth_level` consistency invariant stands.

---

## Entity Relationship Diagram (text)

```
ToolRegistry
  └── retrieval: Retriever (interface)
        ├── BM25Backend (default)
        │     └── BM25Index (existing, unchanged)
        ├── DenseBackend (opt-in)
        │     ├── SentenceTransformer (lazy)
        │     ├── numpy cosine matrix
        │     └── emits RetrievalManifest
        └── HybridBackend (opt-in)
              ├── BM25Backend (composed)
              ├── DenseBackend (composed)
              └── RRF(k=60) fusion

kosmos.tools.search.search_tools(query, registry)
  └── uses registry.retrieval.score(query) → final sort + tie-break

lookup.py (FROZEN)
  └── wraps search_tools; returns LookupSearchResult (FROZEN schema)

eval.retrieval._evaluate(queries, registry)
  └── runs the above with either committed 30-query set
        or AdversarialQuerySet (new)

DegradationRecord (per-registry latch)
  └── guards single WARN emission on FR-002 path
```

---

## Summary

- 1 new Protocol (`Retriever`), 3 new backend classes (`BM25Backend`, `DenseBackend`, `HybridBackend`), 2 new Pydantic v2 models (`RetrievalManifest`, `AdversarialQuerySet`), 1 new in-memory latch (`DegradationRecord`).
- 4 frozen entities (`LookupSearchInput`, `LookupSearchResult`, `AdapterCandidate`, `GovAPITool`) — untouched.
- Zero `Any` types; Constitution Principle III preserved.
- Zero changes to auth-bearing defaults; Constitution Principle II preserved.
- Every new surface is internal to `src/kosmos/tools/retrieval/` or `src/kosmos/eval/`; the public tool contract is unchanged.
