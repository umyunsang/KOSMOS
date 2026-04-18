# Phase 0 Research: Scenario 1 E2E — Route Safety (Re-baseline)

**Date**: 2026-04-18
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

---

## Research questions

### RQ-1: How do we drive the full pipeline with the two-tool facade?

**Decision**: Keep the existing `tests/e2e/` directory and its `AsyncMock(httpx.AsyncClient.get)` HTTP seam. Re-author the fixtures and test bodies against the `resolve_location` + `lookup` facade; do not introduce a new builder abstraction. The Claude-Code-style async-generator tool loop in `kosmos.engine.engine.QueryEngine` is already the correct runtime — we drive it with a `MockLLMClient` scripted to the 6-turn sequence from spec §Overview.

**Rationale**: Every ingredient exists — the facade (`resolve_location.py`, `lookup.py`), the two adapters (`koroad_accident_hazard_search`, `kma_forecast_fetch`), `MockLLMClient`, and the `httpx` mock seam. Spec 012's `E2EFixtureBuilder` was designed for the now-removed `road_risk_score` composite and its three fan-out sub-tools. Porting that builder forward would smuggle obsolete assumptions. A leaner per-test fixture assembled in the new `conftest.py` is clearer and closer to how `kosmos.tools.lookup.lookup` is invoked in unit tests.

**Alternatives considered**:
- *Keep the spec-012 `E2EFixtureBuilder` and only swap tool registrations.* Rejected — the builder bakes in the composite's two-iteration mock-LLM pattern; the re-baselined scenario needs six scripted turns with mid-sequence state.
- *Introduce `respx` as a cleaner mock-seam.* Rejected — violates the AGENTS.md "no new runtime deps" rule, and the existing `AsyncMock` pattern is adequate.

**Reference mapping**:
- Claude Agent SDK — async-generator tool loop (Layer 1 primary).
- `claude-code-sourcemap/query.ts` — tool-loop internals, state interleave.
- `specs/012-scenario1-e2e-route-safety/research.md §RQ-1` — prior decision, carried forward.

---

### RQ-2: Multi-turn follow-up — stateful session or re-prompt pattern?

**Decision**: **Defer** to the Context Assembly v2 epic. This spec asserts only the single-turn 6-call scripted sequence. No `QueryEngine.run()` is invoked a second time in a session; no follow-up citizen message is simulated.

**Rationale**: The spec text is unambiguous — `spec.md §Out of Scope (Permanent)` excludes "Multi-turn follow-up conversation (≥3 distinct citizen turns)". A multi-turn scenario would change three things simultaneously: (a) context compression policy (Layer 5 — microcompact + collapse budget), (b) tool-result caching semantics (cache_ttl_seconds), (c) the span-attribute shape across turns (span linking / conversation_id). Each of those has a separate target epic. Committing to a pattern here (stateful vs re-prompt) pre-empts decisions the Context Assembly v2 spec must make.

**Concrete implication for this spec**: `MockLLMClient.stream()` is called once. `QueryEngine.run()` is called once. `QueryState.messages` is **not** persisted across tests. The `NEEDS TRACKING` entry will be resolved by `/speckit-taskstoissues` creating a placeholder issue under the Context Assembly v2 epic.

**Reference mapping**:
- `docs/vision.md §Layer 5 (Context Assembly)` — three-tier context model, microcompact, collapse.
- Claude Code reconstructed (`claude-reviews-claude/architecture/05-context-assembly.md`).
- "Don't Break the Cache" (arXiv 2601.06007) — dynamic tool results at end of context preserve cache prefix; a multi-turn spec must pick a caching stance first.

---

### RQ-3: DeepEval harness — entry point + fixture strategy?

**Decision**: **Defer** to the observability / eval epic. Do not add DeepEval as a dependency under this spec. Instead, design the scenario's `RunReport` artifact (see `data-model.md`) so that a future DeepEval integration can read `RunReport.final_response` + `RunReport.tool_call_order` without modifying the scenario runner.

**Rationale**: DeepEval's strength is LLM-output *quality* (hallucination, bias, faithfulness). This spec's success criteria measure pipeline *mechanics* (tool-call order, schema conformance, span attributes, graceful degradation). SC-6 (token accounting) already asserts 0% deviation because the mock LLM is deterministic — DeepEval would add nothing for a scripted mock. Adding it now would invite two anti-patterns: (a) blurring mechanical vs semantic assertions, (b) quietly importing a harness that is only exercised later.

**Concrete implication for this spec**: No `tests/eval/deepeval_*` path is created. The `contracts/eval-output.schema.json` artifact this plan produces is DeepEval-compatible (it emits exactly the fields a future metric suite would read), but the scenario suite itself makes no DeepEval call. The `NEEDS TRACKING` entry is resolved by `/speckit-taskstoissues` creating a placeholder.

**Future fixture strategy (documented, not implemented)**: When the eval epic is picked up, DeepEval test cases should read `tests/e2e/run_reports/*.json` exports written when `KOSMOS_E2E_DUMP_DIR` is set. This keeps the scenario suite fixture-driven and the eval suite report-driven — no cross-coupling.

**Reference mapping**:
- `specs/012-scenario1-e2e-route-safety/research.md §New Reference Sources` — DeepEval identified but not adopted.
- `docs/vision.md §References` — DeepEval is not in the canonical reference-materials table; adopting it requires an ADR.
- Anthropic official docs — tool-use protocol (scenario suite asserts protocol-level invariants; quality is orthogonal).

---

### RQ-4: Prompt-cache instrumentation — OTel span attribute name + measurement point?

**Decision**: **Defer** cache counter emission to the cache epic. This spec asserts existing span attributes only (`gen_ai.tool.name`, `gen_ai.tool.call.id`, `kosmos.tool.outcome`, `kosmos.tool.adapter`). No new `kosmos.cache.*` attribute is introduced, and `cache_ttl_seconds=0` remains the fail-closed default on both adapters (FR-009).

**Rationale**: Two `resolve_location` calls occur in the scripted sequence (강남구 then 서울역). They resolve **different** queries, so a hypothetical resolve-layer cache would miss both. Introducing a cache-counter attribute for a code path that does not hit in this scenario would either (a) ship a zero-valued attribute that adds telemetry noise, or (b) require a second scenario (same query twice) that spec 030 explicitly does not cover. Neither is acceptable this side of a cache spec.

**Recommended future shape (documented for the cache spec)**:
- Attribute name: `kosmos.cache.outcome ∈ {"hit", "miss", "bypass"}` — parallels `kosmos.tool.outcome`.
- Measurement point: inside `resolve_location.py` before any backend dispatch; inside `ToolExecutor.invoke()` before the tool handler fires.
- Span placement: attribute on the existing `execute_tool` span; no new span.

The shape above is **illustrative, not binding** — it is recorded here so the future cache spec inherits a consistent vocabulary.

**Reference mapping**:
- "Don't Break the Cache" (arXiv 2601.06007) — dynamic tool results at end preserve cache prefix; 41–80% cost cut in 30–50+ tool-call sessions.
- Anthropic docs — prompt caching semantics (vision.md §Layer 5).
- `specs/021-observability-otel-genai/spec.md` — span attribute naming convention (`<vendor>.<subsystem>.<field>`).

---

### RQ-5: How to align span-name wording between spec.md FR-017 and the existing `execute_tool` span?

**Decision**: Align on the existing `execute_tool` span name (from `kosmos.tools.executor.dispatch` / `invoke`). Do **not** create a `gen_ai.tool.execute` span; that string is an operation-*name* convention, not a span-name convention, and the OTel GenAI v1.40 semconv `GEN_AI_OPERATION_NAME` constant already resolves to `"execute_tool"` in `kosmos.observability.semconv`.

**Rationale**: FR-017 as worded says "every tool call MUST emit one `gen_ai.tool.execute` span". The current codebase emits one `execute_tool <tool_name>` span with `gen_ai.operation.name = "execute_tool"`. These are the same thing at different levels: the GenAI semconv uses the operation-name "execute_tool" to describe an outbound tool call, and our span-name convention echoes that operation-name. Creating a second span with a different name would double-count tool calls in downstream observability and contradict spec 021.

**Concrete action**: The scenario's span-attribute assertion (FR-017) matches spans whose `gen_ai.operation.name == "execute_tool"`, not spans whose literal name equals `"gen_ai.tool.execute"`. The test code documents this alignment. A one-line clarification in spec.md §FR-017 wording can be folded into `/speckit-tasks` if reviewers prefer; no blocking clarification is required for this plan.

**Reference mapping**:
- `specs/021-observability-otel-genai/spec.md §FR-* span naming`.
- OTel GenAI v1.40 semconv — `GEN_AI_OPERATION_NAME` = `"execute_tool"` for outbound tool calls.
- `src/kosmos/observability/semconv.py` — single source of truth.

---

### RQ-6: Where do the missing `kosmos.tool.outcome` / `kosmos.tool.adapter` attributes belong?

**Decision**:
- `kosmos.tool.outcome`: emitted on the `execute_tool` span inside `ToolExecutor.dispatch()` / `ToolExecutor.invoke()` `finally` block, derived from `_final_result.success` → `"ok" | "error"`. This covers every tool call uniformly — including `resolve_location`, `lookup`, and both adapters when invoked via `lookup(mode="fetch")`.
- `kosmos.tool.adapter`: emitted only when `LookupInput.mode == "fetch"`, inside `kosmos.tools.lookup.lookup()`, on the current (not new) span. Value = the resolved `tool_id`. `mode="search"` and `resolve_location` calls MUST NOT carry this attribute — this is how the test distinguishes fetch spans from others (FR-018).

**Rationale**: Both attributes are required by the spec (FR-017/018) and are within the scope of spec 021's span schema but were not wired end-to-end before this scenario tested for them. They belong in the two places where the authoritative information lives — the executor knows success/failure, the facade knows which adapter the LLM asked for. No new span is created; no new dependency is added.

**Reference mapping**:
- `src/kosmos/tools/executor.py` — existing `finally`-block span finalization.
- `src/kosmos/tools/lookup.py` — existing dispatch on `LookupInput.mode`.
- `specs/021-observability-otel-genai/spec.md` — attribute naming + PII masking.

---

### RQ-7: How do we neutralize the startup guard (#468) without bypassing it?

**Decision**: Use `monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-dummy")` and `monkeypatch.setenv("KOSMOS_KAKAO_REST_KEY", "test-dummy")` in a session-scoped pytest fixture. The startup guard then passes on real logic — we populate the required env vars instead of disabling the guard. This satisfies FR-011 and FR-012 without weakening the production check.

**Rationale**: Bypassing the guard (e.g., monkey-patching the check function) would create a CI-only code path that diverges from production. Setting dummy values exercises the guard's normal happy path and confirms it does not reject well-formed (if non-functional) keys. The dummy values never reach `data.go.kr` because all HTTP calls are intercepted by fixtures (FR-004).

**Reference mapping**:
- `specs/026-secrets-infisical-oidc/spec.md §FR-* startup guard`.
- Constitution §II (fail-closed) — guard remains active; tests do not weaken it.

---

## Deferred Items Validation

| Item (from spec §Deferred) | Tracking Issue | Status |
|---|---|---|
| Multi-turn follow-up E2E | NEEDS TRACKING — to be created by `/speckit-taskstoissues` under Context Assembly v2 epic | RESOLVED (disposition in plan.md) |
| Agent Swarm participation | #13, #14 | OPEN — verified below |
| LLM output quality metrics (DeepEval) | NEEDS TRACKING — to be created by `/speckit-taskstoissues` under observability/eval epic | RESOLVED (disposition in plan.md) |
| Scenario 2–5 E2E tests | #18, #19 (and successors) | OPEN — verified below |
| Dense-embedding retrieval upgrade | #585 | OPEN — verified below |
| Prompt-cache instrumentation | NEEDS TRACKING — to be created by `/speckit-taskstoissues` under Context Assembly / cache epic | RESOLVED (disposition in plan.md) |

**Unregistered deferral pattern scan**: spec.md grepped for "separate epic", "future phase", "v2", "deferred to", "later release", "out of scope for v1". All matches fall inside the Deferred Items table or the "Out of Scope (Permanent)" list. No untracked deferral prose. PASS.

**Open-issue verification** (to be run by `/speckit-taskstoissues` before task issue creation):
- `gh issue view 13` — Agent Swarm epic.
- `gh issue view 14` — Agent Swarm epic (parallel).
- `gh issue view 18` — Scenario 2 epic (HIRA).
- `gh issue view 19` — Scenario 3 epic.
- `gh issue view 585` — Dense-embedding retrieval upgrade.

Any issue that returns `STATE: CLOSED` without a successor is a spec 030 blocker — `/speckit-taskstoissues` surfaces this.

---

## New reference sources (identified during research, not adopted)

None. All design decisions map to references already listed in `docs/vision.md § Reference materials`. No new dependencies introduced.

---

## Carry-forward notes for `/speckit-tasks`

1. Tasks for `T-spans` must include a `pytest.mark.skipif(os.getenv("OTEL_SDK_DISABLED") == "true")` guard to satisfy FR-020 gracefully.
2. Tasks for `T-quirk` need a matching `tests/fixtures/koroad/` tape with `siDo=51` in the recorded request URL (and one with `siDo=42` for the `year=2022` control case).
3. The production-edit tasks (`kosmos.tool.outcome` on executor, `kosmos.tool.adapter` on lookup fetch) MUST appear before the `T-spans` task so the assertions pass on a clean run.
4. A one-line clarification in spec.md §FR-017 aligning "`gen_ai.tool.execute` span" wording with the implementation's `execute_tool` span name (RQ-5) may be folded in as a `chore:` task — not a blocker.
