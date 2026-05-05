# G4 Fixes — Backend IPC arms · suffix allow-list · agentic-loop dedup · KMA envelope

> Wave-2 Lead Opus G4. Closes F-ε-02 (partially — wiring confirmed alive, residual silence belongs to G2 useInput dispatcher), F-ε-03 (partially), F-beta-01 (full), F-beta-02 (full), F-beta-03 (full).

## Summary

Five backend / Python-side surfaces touched. Zero new runtime dependencies. Zero new IPC arms. The `plugin_op` arm is already wired in `stdio.py:3201-3241` → `plugin_op_dispatcher.handle_plugin_op_request`; F-ε-02 / F-ε-03 silence belongs to a TUI-side bridge multiplexing issue that surfaces only after G2 (useInput dispatcher) lands.

## Fix-by-fix

### F-beta-01 — `kma_pre_warning` envelope wrap

**File**: `src/kosmos/tools/kma/kma_pre_warning.py:316-340`

Wrapped the registered adapter so it returns a `LookupCollection`-shaped envelope (`{kind: "collection", items: [...], total_count: N}`) instead of the raw `KmaPreWarningOutput` dict. Mirrors the working pattern in `kma_short_term_forecast.py:432-440`. Without the wrap, `envelope.normalize()`'s `LookupOutput` discriminator extraction fails with the β6 capture's `Unable to extract tag using discr`.

### F-beta-02 — Suffix builder primitive routing allow-list

**File**: `src/kosmos/ipc/stdio.py:1198-1356` (suffix builder `_build_available_adapters_suffix`)

Each BM25 candidate now renders with a `[primitive=<name>]` label (data was already populated by `search.py:142`; we just surface it). Footer adds two new rules:

1. "각 후보의 [primitive=...] 라벨을 확인하세요. lookup 후보가 아닌 도구를 lookup 으로 호출하면 unknown_tool 오류가 납니다." (β6 case: `mock_cbs_disaster_v1` is `primitive=subscribe` — the LLM tried to route it through `lookup`).
2. "동일 tool_id 를 같은 params 로 두 번째 호출하지 마세요." (companion to the dedup-guard prompt directive — sets the LLM up to honor the dedup short-circuit).

### F-beta-03 — Agentic-loop dedup guard (KOSMOS-specific addition)

**File**: `src/kosmos/ipc/stdio.py:2399-2462` (helper definitions) + `2950-3050` (short-circuit) + `3180-3214` (outcome classification).

Three components:

1. `_seen_calls: dict[str, str]` — content-hash tracker, lifetime = single chat-request.
2. `_hash_call(tool_id, params)` — SHA-256(canonical-JSON), 16-char prefix.
3. `_classify_envelope_outcome(env)` — maps result envelopes to `'no_data' | 'error' | 'ok'`. Recognizes empty `collection`, `total_count=0`, `kind=error`, `record.found=False`, `record.matched=[]`.

Short-circuit: when the same `(tool_id, params_hash)` was already attempted this turn AND the prior outcome was `no_data`/`error`, emit a synthetic `repeat_call_blocked` envelope INSTEAD of dispatching. The next iteration sees the synthetic result and the model has explicit context to switch tools or answer.

System prompt (`prompts/system_v1.md`) gets a paired CRITICAL block: "동일 호출 재시도 금지". Manifest SHA-256 updated to match.

This is a KOSMOS-specific divergence from CC's query engine (CC has no content-hash dedup) — documented in `research/g4-backend.md § 6` with rationale: K-EXAONE on FriendliAI has higher tool-retry rate than Claude on NO_DATA.

### F-ε-02 / F-ε-03 — plugin_op IPC arm

**No code change required**. `stdio.py:3201-3241` already wires `plugin_op` → `plugin_op_dispatcher.handle_plugin_op_request` (the dispatcher implements all 3 handlers: install/uninstall/list). The "silent" symptom traces to a TUI-side bridge fan-out issue (PluginInstallFlow's `bridge.frames()` consumer racing with PromptInput's `useInput` overlay gate — pattern P-A from triage). Wave-3 re-smoke after G2 will close.

**Instrumentation added**: `write_frame` OTEL span now sets `kosmos.frame.correlation_id` (in addition to existing `kosmos.frame.kind` / `kosmos.frame.direction` / `kosmos.session.id`) so cross-team triage can grep OTLP for which arm + correlation went out the wire.

## Tests

- `tests/tools/kma/test_kma_pre_warning.py` — added `TestRegister::test_registered_adapter_wraps_envelope_with_collection_kind` and `::test_registered_adapter_passes_envelope_normalizer`. 35 tests pass.
- `tests/ipc/test_g4_suffix_primitive_label.py` — 2 tests: real BM25 retrieval surfaces `mock_cbs_disaster_v1` with `primitive=subscribe`; suffix-builder source contains the `[primitive=` template.
- `tests/ipc/test_g4_agentic_loop_dedup.py` — 5 tests: source presence of `_seen_calls` / `repeat_call_blocked` / `_classify_envelope_outcome`; classifier semantic regression (collection-empty, error, record-found-false); hash stability (sort-keys); system-prompt directive presence; pre-warning envelope kind round-trip.
- `tests/ipc/test_stdio.py` — 233 existing tests still pass.
- `tests/integration/test_agentic_loop.py` — 3 existing tests still pass.

Total: **42 G4 + 233 stdio + 3 agentic = 278 passing tests**, no regressions.

TUI-side: `bun test src/ipc/` — 21 / 21 pass (no IPC drift).

## Files modified

- `src/kosmos/ipc/stdio.py` (suffix builder + agentic loop dedup + write_frame correlation_id span)
- `src/kosmos/tools/kma/kma_pre_warning.py` (envelope wrap)
- `prompts/system_v1.md` (NO DATA / 동일 호출 재시도 금지 directive)
- `prompts/manifest.yaml` (SHA-256 sync)
- `tests/tools/kma/test_kma_pre_warning.py` (envelope tests)
- `tests/ipc/test_g4_suffix_primitive_label.py` (new)
- `tests/ipc/test_g4_agentic_loop_dedup.py` (new)
- `specs/realuse-audit-2026-05-05/research/g4-backend.md` (research)
- `specs/realuse-audit-2026-05-05/fixes/g4-backend.md` (this doc)

## Constraints honored

- ✅ Zero new runtime dependencies.
- ✅ Zero new IPC arms.
- ✅ G1/G2/G3/G5/G6/G7 surfaces untouched (verified via grep on commit diff).
- ✅ Wire-level CC parity preserved (dedup operates at the dispatch layer below the IPC envelope; IPC schemas unchanged).
- ✅ All Python edits backend-only — no TUI changes.

## Verification (Layer 1a / 1b / 5)

| Layer | What | Status |
|---|---|---|
| 1a | `pytest tests/tools/kma/test_kma_pre_warning.py` | 35 pass |
| 1a | `pytest tests/ipc/test_g4_*` | 7 pass |
| 1a | `pytest tests/ipc/test_stdio.py` | 233 pass |
| 1a | `pytest tests/integration/test_agentic_loop.py` | 3 pass |
| 1b | `bun test src/ipc/` (TS-side IPC, no drift) | 21 pass |
| 5 | re-smoke β6 (`재난문자` query) | Wave-3 follow-up; primitive label + envelope wrap both shipped |
| 5 | re-smoke β7 (`mohw_welfare_eligibility_search` retry-loop) | Wave-3 follow-up; dedup short-circuit shipped |
| 5 | re-smoke ε2/ε3/ε5 (plugin_op silence) | Wave-3 follow-up after G2 useInput dispatcher fix |
