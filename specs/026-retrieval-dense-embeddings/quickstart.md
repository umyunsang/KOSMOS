# Quickstart — Retrieval Backend Evolution (Spec 026)

**Audience**: KOSMOS operators and developers who want to exercise the three
retrieval backends (BM25 default, Dense opt-in, Hybrid opt-in) without
changing any caller-visible contract.

**Prerequisites**: a working `uv run pytest` on `feat/585-retrieval-dense`
(the spec 022/023/024/025 stack is already in place).

---

## 1. Default path — BM25 (zero-change)

This is the safe path. No new env vars, no model download, no dep install.

```bash
# Nothing to set. BM25 is the default.
uv run python - <<'PY'
import asyncio
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import LookupSearchInput
from kosmos.tools.lookup import lookup
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

reg = ToolRegistry()
executor = ToolExecutor(reg)
register_all_tools(reg, executor)

result = asyncio.run(
    lookup(LookupSearchInput(mode="search", query="기상 특보"), registry=reg)
)
for c in result.candidates:
    print(c.tool_id, round(c.score, 3))
PY
```

**Expected**: identical ranking to `main` on all 30 curated queries.
**Gate**: `uv run pytest tests/eval/test_retrieval_gate.py -q` passes (pass
threshold 0.80; baseline recall@5 = 1.0).

---

## 2. Dense backend — opt-in

The Dense backend loads `intfloat/multilingual-e5-small` (MIT, 100M params,
384-dim, MIRACL-ko MRR@10=55.4) on first `search()` call (lazy cold-start).

```bash
export KOSMOS_RETRIEVAL_BACKEND=dense
# KOSMOS_RETRIEVAL_MODEL_ID is optional; default is the e5-small above.
# Example override (NOT recommended unless you know why):
# export KOSMOS_RETRIEVAL_MODEL_ID="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

uv run python - <<'PY'
import asyncio
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.lookup import lookup
from kosmos.tools.models import LookupSearchInput
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

reg = ToolRegistry()
executor = ToolExecutor(reg)
register_all_tools(reg, executor)

# First call triggers model download + embedding. Subsequent calls are < 20 ms.
result = asyncio.run(
    lookup(LookupSearchInput(mode="search", query="폭염 특보가 있으면 알려줘"), registry=reg)
)
for c in result.candidates:
    print(c.tool_id, round(c.score, 3), "→", c.why_matched)
PY
```

**Expected**:
- First query tail latency spike is acceptable (NFR-BootBudget gates **only**
  the `backend=bm25` boot path).
- Subsequent queries: p99 < 50 ms on the 4-adapter seed set.
- Result **shape** (`LookupSearchResult`) is byte-identical to the BM25 path.

**Failure mode (fail-open, per FR-002)**: if the model fails to load
(sentence-transformers missing, network blocked, weight hash mismatch), the
registry silently falls back to BM25 and emits exactly one structured WARN
log line per `RetrievalManifest.load()` attempt. The citizen sees no 5xx.

---

## 3. Hybrid backend — opt-in

The Hybrid backend composes BM25 + Dense under Reciprocal Rank Fusion
(Cormack, Clarke, Buettcher SIGIR 2009) with `k=60` by default.

```bash
export KOSMOS_RETRIEVAL_BACKEND=hybrid
# Optional RRF knob; default is 60. Values < 1 reject at startup.
# export KOSMOS_RETRIEVAL_FUSION_K=60
# Optional fusion algorithm; default is rrf. Only rrf is shipped in spec 026.
# export KOSMOS_RETRIEVAL_FUSION=rrf

uv run python - <<'PY'
import asyncio
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.lookup import lookup
from kosmos.tools.models import LookupSearchInput
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

reg = ToolRegistry()
executor = ToolExecutor(reg)
register_all_tools(reg, executor)

result = asyncio.run(
    lookup(LookupSearchInput(mode="search", query="폐렴 유행주의보 현황"), registry=reg)
)
for c in result.candidates:
    print(c.tool_id, round(c.score, 3))
PY
```

**Expected on the #22-extended + adversarial query set (SC-01/SC-02)**:
- SC-01: recall@5 ≥ 0.90 AND recall@1 uplift ≥ +5%p over BM25-only.
- SC-02: adversarial paraphrase subset achieves recall@5 ≥ 0.80 while
  BM25-only falls below 0.50 — that is the synonym-robustness payoff that
  motivates #585.

**Graceful degradation (FR-002)**: if the Dense subsystem fails mid-session
(model OOM, tokenizer crash), `HybridBackend` transparently returns the
BM25-only ranking, logs `retrieval.degraded=true` once per latched
registry instance, and preserves the fail-closed posture on every auth /
invocation gate downstream.

---

## 4. A/B evaluation harness

```bash
# Baseline (BM25)
unset KOSMOS_RETRIEVAL_BACKEND
uv run python -m kosmos.eval.retrieval \
  --queries eval/retrieval_queries.yaml \
  --report reports/retrieval_bm25.json

# Hybrid
KOSMOS_RETRIEVAL_BACKEND=hybrid \
uv run python -m kosmos.eval.retrieval \
  --queries eval/retrieval_queries.yaml \
  --report reports/retrieval_hybrid.json

# Adversarial subset (ships in this PR per CL-1 decision)
KOSMOS_RETRIEVAL_BACKEND=hybrid \
uv run python -m kosmos.eval.retrieval \
  --queries eval/retrieval_queries_adversarial.yaml \
  --report reports/retrieval_adversarial.json
```

The harness output schema is preserved (see
`tests/eval/test_retrieval_gate.py`). Existing CI consumers do not change.

---

## 5. Env-var reference

| Variable | Values | Default | Owner | Purpose |
|----------|--------|---------|-------|---------|
| `KOSMOS_RETRIEVAL_BACKEND` | `bm25` \| `dense` \| `hybrid` | `bm25` | #468 | Select ranking backend. Unknown values fail-closed at registry construction (FR-001). |
| `KOSMOS_RETRIEVAL_MODEL_ID` | HF model slug (Apache-2.0-compatible only) | `intfloat/multilingual-e5-small` | #468 | Dense model identifier. Licence is vetted during spec review (shortlist in `research.md` §Models); operators overriding to a non-vetted slug take responsibility for compatibility. No runtime licence enforcement is performed at load time. |
| `KOSMOS_RETRIEVAL_FUSION` | `rrf` | `rrf` | #468 | Fusion algorithm for hybrid mode. RSF is deferred (`NEEDS TRACKING`). |
| `KOSMOS_RETRIEVAL_FUSION_K` | integer ≥ 1 | `60` | #468 | RRF dampening constant. `k=60` per Cormack SIGIR 2009. |
| `KOSMOS_LOOKUP_TOPK` | 1..20 | `5` | #022 | Adaptive top-k clamp (FROZEN — preserved by FR-005). |

**All four new variables must land in #468's registry before this spec
merges** — spec 026 proposes them; #468 ratifies them.

---

## 6. What you CANNOT change

These surfaces are byte-level FROZEN by spec 507 (parent Epic). The
schema-snapshot regression test (Appendix B in `spec.md`) will block any
drift:

- `LookupSearchInput` (see `contracts/lookup_search_input.schema.json`)
- `LookupSearchResult` (see `contracts/lookup_search_result.schema.json`)
- `AdapterCandidate` (see `contracts/adapter_candidate.schema.json`)
- `GovAPITool` (spec 024/025 V1–V6)
- Adaptive clamp `max(1, min(k, registry_size, 20))`
- Deterministic tie-break `(score DESC, tool_id ASC)`

If you need to change any of the above, open a new spec and coordinate with
#507.

---

## 7. Troubleshooting

**"Model weight download blocked in CI"** → by design. The DenseBackend
MUST load from a local HF cache in CI (NFR-NoNetAtRuntime). Pre-seed the
cache in your dev environment (`uv run python -c "from
sentence_transformers import SentenceTransformer;
SentenceTransformer('intfloat/multilingual-e5-small')"`) and let the weight
hash propagate through the release manifest (#467).

**"Recall fell on the 30-query set"** → expected. The 30-query set is
saturated at recall@5 = 1.0 under BM25 (Background §1 of spec 026); any
re-ranking move that favors synonyms over exact lexical overlap may trade
one keyword-match query for several synonym-match queries. Use the
#22-extended set for honest A/B, not the seed set.

**"Why does `backend=hybrid` sometimes return exactly BM25 ranking?"** →
the Dense subsystem latched into degraded mode at boot. Check for the
`retrieval.backend_degraded=true` WARN log line; the `DegradationRecord`
entity in `data-model.md` §7 documents the latch.
