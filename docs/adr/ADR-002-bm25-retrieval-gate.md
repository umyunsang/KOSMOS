# ADR-002: BM25 Retrieval Gate — rank_bm25 + kiwipiepy

**Status**: Accepted
**Date**: 2026-04-16
**Epic**: #507 (KOSMOS MVP Main Tool)

---

## Context

The `lookup` tool's `search` mode must rank registered tool adapters by relevance
to a free-text user query (Korean or English) and return the top-k candidates to
the LLM.  Without a retrieval gate, adding new adapters can silently degrade
ranking quality and increase the LLM's tool-selection error rate.

Requirements driving the design:

1. **Korean morpheme awareness**: Korean agglutinates stems and particles; raw
   whitespace splitting produces poor IDF distributions and low recall on
   morphologically varied queries.  A morpheme-level tokenizer is needed at both
   index time and query time.
2. **Pure-Python, zero system deps**: KOSMOS CI runs under `uv`; any library
   requiring a system-installed binary (e.g. mecab C extension) breaks the CI
   matrix without extra setup steps.
3. **MVP scale**: the registry holds 4–50 adapters at MVP.  Vector-store
   infrastructure (embedding model + vector DB) is premature at this scale.
4. **Regression prevention**: the BM25 index must be guarded by a measurable
   quality gate so that search hint changes or new adapter registrations that
   degrade retrieval quality are caught in CI before shipping.

Candidates evaluated:

| Tokenizer | License | System dep? | Korean F1 (2024-2025) | Notes |
|-----------|---------|-------------|----------------------|-------|
| `kiwipiepy>=0.17` | MIT | None (pure Python) | Parity with mecab-ko | Actively maintained |
| `mecab-ko` | LGPL-2.1 | Yes (`libmecab.so`) | Reference | Rejected — CI friction |
| Whitespace only | N/A | None | Poor (Korean) | Insufficient |

| BM25 library | License | Notes |
|--------------|---------|-------|
| `rank_bm25>=0.2.2` | Apache-2.0 | BM25Okapi implementation; pure Python |

---

## Decision

**Use `rank_bm25>=0.2.2` (Apache-2.0) for BM25Okapi scoring** and
**`kiwipiepy>=0.17` (MIT) for Korean morpheme tokenization**.

**Key design points:**

1. **Tokenizer dispatch**: `tokenizer.tokenize()` detects ASCII-only text and
   applies lowercase whitespace splitting; all other text (Korean) is routed
   through a lazy-loaded `kiwipiepy.Kiwi` singleton with POS filter
   `{NNG, NNP, VV, VA, SL}` to retain content-bearing tokens only.

2. **Index rebuild**: `BM25Index` rebuilds the full corpus whenever a new
   adapter is registered.  At MVP registry size (4–50 adapters) a rebuild takes
   < 5 ms; rebuild is called only at startup or on explicit `rebuild()` — never
   on the hot scoring path.

3. **Deterministic tie-break**: when two adapters share the same BM25 score,
   results are ordered by `tool_id` ASC (FR-013).  This makes evaluation
   reproducible across Python sessions regardless of dict insertion order.

4. **30-query eval gate** (`eval/retrieval_queries.yaml`): 30 manually curated
   Korean and English queries with labeled `expected_tool_id` covering all 4
   seed adapters (KOROAD × 10, KMA × 7, HIRA × 7, NMC × 6).  CI test at
   `tests/retrieval/test_recall.py` enforces:

   | Band | `recall@5` | Action |
   |------|-----------|--------|
   | Pass | ≥ 80% AND `recall@1` ≥ 50% | ship |
   | Warn | 60% ≤ `recall@5` < 80% | reinforce `search_hint`, re-test |
   | Fail | < 60% | block merge |

   The 80% target is the Kruczek/MCP-Bench midpoint for BM25 at < 100-tool
   scale.  The 60% fail threshold equals Anthropic's published 64% BM25 accuracy
   at 4K-tool scale; anything worse at KOSMOS's smaller scale indicates a
   structural retrieval problem, not a scale problem.

**Rejected alternative — mecab-ko**: requires a system-installed `libmecab`
C extension.  Under `uv` on a stock CI runner this adds a mandatory `apt-get`
step, coupling the Python build to the OS image.  `kiwipiepy` achieves F1 parity
on 2024-2025 Korean morpheme segmentation benchmarks without any system
dependency.

---

## Consequences

**Positive:**

- `rank_bm25` and `kiwipiepy` are pure-Python packages; `uv add` is the only
  installation step in any environment.
- Apache-2.0 (`rank_bm25`) and MIT (`kiwipiepy`) licenses are compatible with
  KOSMOS's Apache-2.0 project license.
- The `Kiwi` singleton is initialised lazily on first use (~300 ms startup cost,
  paid once per process); the hot BM25 scoring path adds negligible latency.
- The 30-query eval gate in CI prevents silent retrieval regressions as the
  registry grows; adding a new adapter requires adding at least one eval query
  referencing it.

**Negative / Trade-offs:**

- **IDF collapse edge case**: when the registry contains only 2 tools, BM25
  IDF terms collapse to 0.0 for tokens present in both documents.  This is an
  expected mathematical behaviour of BM25Okapi at very small corpus sizes.  The
  MVP 4-adapter seed set avoids this in practice; the edge case is documented in
  `BM25Index` source comments for future maintainers.
- `kiwipiepy` adds ~300 ms to the first query in a cold process.  Acceptable for
  the interactive CLI use case; would need profiling for high-throughput batch
  workloads.
- BM25 is a bag-of-words model: it does not capture semantic similarity.  If
  recall falls below 60% as the registry scales beyond 50 adapters, the upgrade
  path is a vector-retrieval layer (deferred post-MVP per
  `docs/design/mvp-tools.md §5.5`).
- The eval gate threshold (recall@5 ≥ 80%) applies only to the 4 seed adapters.
  New adapters must each contribute at least one eval query to maintain gate
  coverage.

---

## Alternatives Rejected

- **mecab-ko**: C extension requiring system-level install (`libmecab.so`).
  Breaks `uv`-only CI setup without an additional `apt-get` step.  License
  (LGPL-2.1) also requires additional compliance review for a project targeting
  Apache-2.0 distribution.  Rejected in favour of `kiwipiepy` which achieves
  parity on 2024-2025 Korean morpheme F1 benchmarks.
- **Whitespace-only tokenizer**: Adequate for ASCII/English but produces
  sub-optimal IDF distributions for Korean text.  Korean agglutination means a
  single eojeol like "교통사고위험지역을" would never match the indexed token
  "위험" even though the semantic content overlaps.
- **Vector store (embeddings + ANN index)**: Appropriate at > 100-tool scale.
  Zero infra cost of BM25 is preferred at MVP scale; vector upgrade is gated on
  recall falling below 60% on the eval set (see `docs/design/mvp-tools.md §5.5`).

---

## References

- Epic #507 — KOSMOS MVP Main Tool
- `docs/design/mvp-tools.md §3.3` (frozen design, BM25 retrieval gate) and
  `§5.5.1` (retrieval quality gate definition)
- `src/kosmos/tools/bm25_index.py` — BM25Okapi wrapper with deterministic tie-break
- `src/kosmos/tools/tokenizer.py` — kiwipiepy thin wrapper with ASCII fast path
- `eval/retrieval_queries.yaml` — 30-query labeled evaluation set
- Arcade replication of Anthropic Tool Search Tool (BM25, 64% accuracy at 4K tools):
  https://blog.arcade.dev/anthropic-tool-search-claude-mcp-runtime
