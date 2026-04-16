# Phase 0 Research: MVP Main-Tool (`lookup` + `resolve_location`)

**Feature**: 022-mvp-main-tool | **Date**: 2026-04-16 | **Constitution**: v1.1.0

This document resolves every `NEEDS CLARIFICATION` from the Technical Context (there were none — the frozen design `docs/design/mvp-tools.md` pre-resolved all 12 decisions), validates the Deferred Items table against GitHub reality, maps each design layer to its authoritative reference per Constitution Principle I, and grounds the new dependency choices.

## 1. Reference-Mapping Matrix (Constitution §I gate)

Every design decision is traceable to either the frozen design doc or a reference repository. The table below satisfies the mandatory reference-mapping check.

| Decision | Frozen §§ | Primary reference | Secondary reference | Adaptation for KOSMOS |
|---|---|---|---|---|
| Two-tool facade (`resolve_location` + `lookup`) | §3, §4, §5 | Anthropic Tool Search Tool (platform.claude.com docs) | Arcade BM25 replication (`blog.arcade.dev/anthropic-tool-search-claude-mcp-runtime`) | `search_hint` field holds Korean+English morphemes; BM25 tokenized with `kiwipiepy` instead of plain whitespace |
| Discriminated-union outputs (`LookupRecord|Collection|Timeseries|Error`) | §5.4 | `.references/claude-reviews-claude/docs/chapters/02-tool-system.md` (tool factory, deferred tools) | Pydantic AI v2 schema-driven registry | Four shapes chosen to cover the seed matrix (point / list / time-series / error) without ad-hoc envelopes per adapter |
| `mode="search"` BM25 gate over cold-path adapters | §5, §5.5 | AnyTool (arXiv:2402.04253) hierarchical router | Cursor Dynamic Context Discovery (46.9% prod A/B) | `top_k` is adaptive: `min(KOSMOS_LOOKUP_TOPK, len(registry))` to handle sparse MVP registry |
| `mode="fetch"` typed invocation with fail-closed gate | §5.6, §8.1 | OpenAI Agents SDK guardrail pipeline | Claude Code reconstructed permission model (`.references/claude-reviews-claude/chapters/`) | Layer 3 ships as *interface only* — the short-circuit returns `LookupError(reason="auth_required")` from a stub guard before the handler executes |
| `resolve_location` 3-provider deterministic dispatch (Kakao → JUSO → SGIS) | §4 | Kakao Local API docs + juso.go.kr + sgis.kostat.go.kr | `docs/vision.md § Layer 2 — Tool System` | Dispatch order is deterministic (not parallel fan-out) to keep provenance traceable in the `source` field |
| `ResolveWant` enum with `coords_and_admcd` default | §4 (Q5) | `docs/design/mvp-tools.md` frozen decision Q5 | — | `all` is opt-in only; adapter-specific conventions (KMA grid, KOROAD sido/gugun) derived inside adapters, not exposed as `want` values |
| Korean tokenizer = `kiwipiepy>=0.17` (Q1) | §9 (Q1) | kiwipiepy MIT — https://github.com/bab2min/kiwipiepy | mecab-ko (rejected: CI install friction under `uv`) | 2024-2025 benchmarks show F1 parity on morpheme segmentation; pure Python so `uv sync` works without system-install |
| BM25 backend = `rank_bm25` (Okapi BM25) | §5.5 | `rank_bm25` Apache-2.0 — https://github.com/dorianbrown/rank_bm25 | Anthropic Tool Search Tool uses BM25 | Chosen over Lucene/Elasticsearch for footprint; dense retrieval is deferred until recall@5 falls <60% on eval (per deferred item) |
| Adaptive `top_k` clamp `[1, 20]` (Q2) | §9 (Q2) | `docs/design/mvp-tools.md` frozen decision Q2 | — | Floor handles 4-adapter MVP; ceiling prevents context blow-up at 200+ adapters |
| 30-query eval with recall@5 gate (Q4) | §5.5.1, §9 (Q4) | `docs/design/mvp-tools.md` frozen decision Q4 | MCP-Bench (arXiv:2508.20453) methodology | Gates: ≥80% pass / [60%, 80%) warn / <60% fail; recall@1 ≥ 50% secondary |
| 4-adapter seed set (KOROAD/KMA/HIRA/NMC) (Q3) | §5.8, §9 (Q3) | `docs/design/mvp-tools.md` frozen decision Q3 | KOROAD Portal reference memory (16 traffic APIs) | Covers both canonical shapes (`collection`+`timeseries`) and all four spatial-input conventions (code-pair / LCC grid / coord+radius / coord-only) |
| NMC interface-only with `is_personal_data=True` (Q4 harness) | §8.1 | `docs/vision.md § Layer 3 — Permission Pipeline` | PIPA (개인정보보호법) | One seed adapter PII-flagged so the stub guard fires on at least one end-to-end path — otherwise the Layer 3 slot is untested dead code |
| `#288` geocoding absorbed into `resolve_location` + KMA adapter | Epic #507 body, §4 | `docs/design/mvp-tools.md` §4 (ResolveWant) | Spec #288 legacy (`address_to_region`, `address_to_grid`) | No compat shim; adm-code via `resolve_location(want=["adm_code"])`; LCC grid internal to KMA adapter |

## 2. Deferred Items Validation (Constitution §VI gate)

The `/speckit-plan` skill mandates validating every entry in spec.md's "Deferred to Future Work" table. I ran `gh issue view` on each cited number and compared the title against the spec's claim.

### 2.1 Cross-check results

| Spec row (Item) | Spec claims issue = | Actual issue title | Match? |
|---|---|---|---|
| Full Layer 3 permission gauntlet | #16 | `#16 Permission Pipeline v2 (Layer 3)` | ✅ match |
| NMC freshness SLO enforcement | NEEDS TRACKING | — | n/a (placeholder) |
| Retry matrix for upstream 5xx | #20 | `#20 Permission Pipeline v3 — Full PIPA Compliance (Layer 3)` | ❌ **mismatch** (#20 is permissions, not Error Recovery retry matrix) |
| Scenario graph / multi-turn planning | #15 | `#15 Phase 2 API Adapters (119, MOHW)` | ❌ **mismatch** (#15 is adapter work, not scenario graph) |
| Agent Swarm / orchestrator-workers | #22 | `#22 Phase 3 API Adapters (Gov24, Vehicle, Insurance, NEMA)` | ❌ **mismatch** (#22 is adapter work, not Agent Swarms) |
| Prompt-cache instrumentation | #287 | `#287 Epic: Full TUI (Ink + React + Bun)` | ❌ **mismatch** (#287 is the TUI epic) |
| TUI surface | #13 | `#13 Agent Swarm Core (Layer 4)` | ❌ **mismatch** (#13 is Agent Swarms, not TUI) |
| Additional adapters beyond 4 seeds | #14 | `#14 Ministry Specialist Agents` | ❌ **mismatch** (#14 is agents, not adapters) |
| OTel GenAI spans on two-tool surface | #21 | `#21 Agent Swarm Production (Layer 4)` | ❌ **mismatch** (#21 is swarm production, not observability) |
| `parallel_safe` parallelization | NEEDS TRACKING | — | n/a (placeholder) |
| I18n beyond ko+en | NEEDS TRACKING | — | n/a (placeholder) |
| Account-wide rate-limit orchestration | NEEDS TRACKING | — | n/a (placeholder) |
| Write-capable adapters (POST) | NEEDS TRACKING | — | n/a (placeholder) |
| Tokenizer replacement / dense retrieval | NEEDS TRACKING | — | n/a (placeholder) |

**Summary**: 1 of 8 issue refs matches (#16). 7 of 8 are semantically mismatched — the numeric refs appear to have been picked without verification. This is a Constitution §VI issue quality flag.

### 2.2 Remediation decision

**Recommendation — apply before `/speckit-taskstoissues`**: downgrade the 7 mismatched refs to `NEEDS TRACKING` and let `/speckit-taskstoissues` create fresh tracking issues with the correct titles (per the skill's documented behavior: "creates placeholder issues for any `NEEDS TRACKING` markers and back-fills the spec with the issue number"). Keep #16 as-is.

**Rationale**: correcting to the *correct* existing issue (if one exists) would require an inventory scan we haven't done; creating fresh placeholders is the lower-risk path and matches the skill's intended flow. The 6 already-`NEEDS TRACKING` rows are unaffected.

**Action item** (pre-`/speckit-tasks`): edit spec.md Deferred Items table rows for #20, #15, #22, #287, #13, #14, #21 → replace with `NEEDS TRACKING`. This is a spec-only edit, no source code impact.

### 2.3 Free-text deferral scan

Scanned spec.md for unregistered deferral patterns. Matches found:

- "Phase 2+" — line in User Story 5 (TUI context) → already tracked via the "TUI surface" row
- "post-MVP" — multiple appearances in design-doc quotes and FR-022 rationale → all tied to existing table rows (Layer 3, NMC freshness, HIRA MadmDtl join)
- "future epic" — zero matches
- "separate epic" — zero matches
- "v2" — zero matches in spec prose (only in `Pydantic v2` which is a version identifier, not a deferral)
- "future work" — one match in the Deferred Items section header itself (not a violation)
- "later release" — zero matches
- "out of scope for v1" — zero matches (spec uses "Out of Scope (Permanent)" as a structured header, fine)

**Conclusion**: no unregistered deferrals. The only §VI issue is the 7 mismatched tracking refs (§2.2 above).

## 3. Dependency Additions

Two new runtime dependencies land in `pyproject.toml` via this spec PR (per `AGENTS.md § Hard rules`: "Never add a dependency outside a spec-driven PR").

### 3.1 `rank_bm25`

- **License**: Apache-2.0 (compatible with KOSMOS Apache-2.0)
- **Role**: BM25 scoring for `lookup(mode="search")`
- **Alternatives considered**:
  - Whoosh / Lucene-py — heavier, bring their own tokenizer assumptions; rejected per §5.5 of design doc
  - Elasticsearch — external service; rejected as MVP complexity
  - Plain TF-IDF (`sklearn.feature_extraction.text`) — weaker on short documents like `search_hint` strings; rejected for recall
  - Dense retrieval (sentence-transformers) — 100+ MB model download; deferred until BM25 fails eval gate (tracked as "Tokenizer replacement / dense retrieval" deferred item)
- **Risk**: single maintainer; fallback plan is to inline the ~200 LOC Okapi-BM25 implementation if the package becomes unmaintained

### 3.2 `kiwipiepy>=0.17`

- **License**: MIT (compatible)
- **Role**: Korean morpheme tokenizer for BM25 term extraction on `search_hint`
- **Alternatives considered**:
  - `mecab-ko` — frozen §9 Q1 rejects: CI system-install friction under `uv`; kiwipiepy is pure Python
  - `konlpy` (Okt/Komoran/Hannanum) — Java JVM dep, heavy
  - No tokenizer (whitespace split) — Korean agglutinative morphology gets destroyed; English+Korean hybrid queries score poorly
- **Performance**: kiwipiepy benchmarks ~5k tokens/s single-threaded — well above the 10–50 adapter × ~30 token `search_hint` workload
- **Risk**: bab2min single-maintainer; falls back to whitespace if init fails (adapter-internal defensive fallback — to be wired in `tokenizer.py`, not a separate feature)

## 4. Seed-Adapter Research Notes

Each adapter's upstream API was previously scoped in the frozen design. Phase 0 re-verifies the quirks list and confirms fixture-capture paths.

### 4.1 `koroad_accident_hazard_search` (KOROAD / data.go.kr)

- **Upstream**: KOROAD 교통사고분석시스템 — `getRestFrequentzoneLonLat.do` (hazard by sido+gugun+year)
- **Code-pair inputs**: `siDo` (광역) + `guGun` (기초) codes
- **Year-dependent quirks** (encapsulated in adapter, not exposed):
  - 2023 강원 42 → 51 (강원특별자치도 승격)
  - 2023 전북 45 → 52 (전북특별자치도 승격)
  - 부천시 historical split (원미구/소사구/오정구) merged back 2016
- **Fail-closed**: `requires_auth=False` (public read), `is_personal_data=False`, `is_concurrency_safe=True`, `cache_ttl_seconds=3600` — relaxed per design §5.8
- **Fixture**: captured via `@pytest.mark.live` one-time run against 2024 강남구 + 2023 강원(quirk year) + invalid year (error path)

### 4.2 `kma_forecast_fetch` (KMA / data.go.kr)

- **Upstream**: 기상청 단기예보조회 `getVilageFcst`
- **Input shape**: `base_date (YYYYMMDD) + base_time (02/05/08/11/14/17/20/23시) + nx + ny` — **nx/ny are LCC grid**, not lat/lon
- **Adapter-internal**: LCC projection from `(lat, lon)` to `(nx, ny)` using 기상청 격자 분포식 (grid spacing 5km, origin 38°N 126°E, reference (60, 127))
- **Category pivot**: KMA returns flat `{category, fcstDate, fcstTime, fcstValue}` rows; adapter pivots to time-series of `{ts, temperature_c, precipitation_mm, sky, humidity_pct, wind_ms, pop_pct, ...}`
- **Fail-closed**: same as KOROAD (public, read, safe, 1h cache)
- **Fixture**: 종로구 coordinate + valid base_time + invalid base_time (error path) + out-of-Korea coord (`LookupError(reason="out_of_domain")`)

### 4.3 `hira_hospital_search` (HIRA / data.go.kr)

- **Upstream**: 건강보험심사평가원 병원정보서비스 `getHospBasisList` with `xPos + yPos + radius` (m)
- **Output join key**: `ykiho` (요양기관기호) — links to HIRA's `MadmDtlInfoService2.7` (11 sub-operations, deferred)
- **radius_m validation**: clamp `[100, 10000]` at schema layer
- **Fail-closed**: same as KOROAD/KMA
- **Fixture**: 강남역 ±2km + 0 results area + invalid radius (error path)

### 4.4 `nmc_emergency_search` (NMC / data.go.kr) — interface-only

- **Upstream**: 국립중앙의료원 실시간 응급실 — `getEmrrmRltmSrmInfoInqire` (real-time bed counts)
- **PII classification**: adapter declares `is_personal_data=True` because real-time bed-count + hospital-roster overlap with identifiable patient flow; citizen consent required for operational use per PIPA
- **MVP behavior**: `requires_auth=True` short-circuits to `LookupError(reason="auth_required", retryable=False)` **before** any upstream call (SC-006 = 0 upstream calls)
- **Post-MVP freshness SLO** (documented, not enforced in MVP): `hvidate` older than `KOSMOS_NMC_FRESHNESS_MINUTES` (default 30, clamp [1, 1440]) → `LookupError(reason="stale_data")`
- **PII field inventory** (captured for the follow-on NMC live-data epic):
  - `hpid` (응급실 ID — unique identifier)
  - `dutyName`, `dutyAddr`, `dutyTel1`, `dutyTel3` (hospital identity; non-personal but enables patient-flow profiling)
  - `hvidate` (last-update timestamp — freshness SLO input)
  - `hv1`–`hv61` (real-time bed counts by category — quasi-identifiers for hospital utilization profiling)
  - `hvec`, `hvoc`, `hvcc`, `hvncc`, `hvccc`, `hvicc` (specialty bed availability)
  - `mkioskty1`–`mkioskty28` (real-time acceptance acknowledgments)
  - `wgs84Lat`, `wgs84Lon` (coordinates — non-PII but combined with `hpid` enables patient-arrival re-identification)
- **Fixture**: asserts `LookupError(reason="auth_required")` shape + fixture tape shows zero HTTP calls

## 5. 30-Query BM25 Eval Set — Draft Schema

The eval set lives at `eval/retrieval_queries.yaml` (FR-010). Draft schema and seed-corpus coverage plan:

### 5.1 Schema

```yaml
# eval/retrieval_queries.yaml
version: 1
queries:
  - id: Q001
    query: "교통사고 위험지역 알려줘"
    expected_tool_id: koroad_accident_hazard_search
    notes: "Canonical KOROAD phrasing"
  - id: Q002
    query: "traffic accident hotspots"
    expected_tool_id: koroad_accident_hazard_search
    notes: "English equivalent — tests bilingual hint"
  # ... 28 more
```

### 5.2 Coverage plan (30 queries)

- **KOROAD (10 queries)**: canonical ko, English equivalent, paraphrases ("사고 많은 곳", "accident blackspots"), edge phrasings ("위험 도로", "dangerous intersections")
- **KMA (7)**: "오늘 날씨", "비 와?", "weather forecast", "short-term forecast", "시간별 기온", "강수 확률", "hourly temperature"
- **HIRA (7)**: "근처 병원", "가까운 의원", "nearby hospitals", "응급실 아닌 병원", "동네 병원", "medical clinics nearby", "internal medicine 찾아줘"
- **NMC (6)**: "응급실", "응급실 병상", "emergency room beds", "실시간 응급실", "가장 가까운 응급실", "ER availability"

### 5.3 Gate thresholds (per FR-011, Q4)

- `recall@5 ≥ 80%` → pass (silent)
- `60% ≤ recall@5 < 80%` → warn (CI annotation only)
- `recall@5 < 60%` → fail the job
- Secondary: `recall@1 ≥ 50%` reported but not gated (informational — the LLM reads the full top-k anyway)

## 6. Open Questions — None

All 12 frozen decisions pre-resolved; spec.md has 0 `[NEEDS CLARIFICATION]` markers; Technical Context has 0 unknowns. Phase 1 can proceed.

## 7. Outputs

- ✅ Reference-mapping matrix (§1) — Constitution §I gate
- ✅ Deferred Items validation (§2) — Constitution §VI gate, with remediation action item flagged
- ✅ Dependency rationale (§3)
- ✅ Seed-adapter quirks + PII inventory (§4)
- ✅ Eval-set schema + coverage plan (§5)

**Next**: Phase 1 generates `data-model.md`, `contracts/`, `quickstart.md`, then updates agent context.
