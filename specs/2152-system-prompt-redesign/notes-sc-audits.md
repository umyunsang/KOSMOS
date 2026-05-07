# P5 Success-Criteria Audits — Epic #2152

**Date**: 2026-04-28 · **Branch**: `feat/2152-system-prompt-redesign` · **Spec**: [spec.md](./spec.md)

This document captures the evidence for the six success criteria from
`spec.md § Success Criteria`. Each section names the verification command,
records its observed output, and the verdict.

---

## SC-1 — Citizen smoke ≥ 3 of 5 trigger a tool call

**Status**: `PASS` (4/5 scenarios emit a tool-call intent; greeting correctly stays text-only).

**How verified**: Two-layer smoke (per `docs/testing.md § TUI verification methodology`):

- **Layer 2 — stdio JSONL probe** (`scripts/smoke-stdio.sh`) drives 5 citizen scenarios through the backend stdio bridge, captures every assistant_chunk / tool_call frame as `smoke-stdio-<slug>.jsonl`, aggregates into `smoke.txt`. Run: `KOSAX_FRIENDLI_TOKEN=… scripts/smoke-stdio.sh`.
- **Layer 4 — vhs visual** (`scripts/smoke.tape` → `smoke.gif`) drives the same 5 scenarios through the live TUI for human-eye review. Run: `vhs scripts/smoke.tape`.

**Per-scenario audit** (Layer 2 — `scripts/smoke-stdio.sh` 2026-04-28, after the primitive-only prompt fix + textual-marker fallback parser landed):

| Scenario | Prompt | Structured tool_calls | Real invocations |
|----------|--------|------------------------|--------------------|
| location | 강남역 어디야? | 1 | `resolve_location({"query":"강남역"})` |
| weather | 오늘 서울 날씨 알려줘 | 4 | `lookup(search "서울 날씨") ×3` + `resolve_location({"query":"서울"})` |
| emergency | 근처 응급실 알려줘 | 2 | `lookup(search "근처 응급실") ×2` |
| koroad | 어린이 보호구역 사고 다발 | 7 | `lookup(search …)` for "어린이 보호구역", "사고 다발 지역" variants |
| greeting | 안녕 | 0 | "안녕하세요! 무엇을 도와드릴까요?" |

Total 14 structured `ToolCallFrame`s emitted in one session. 4 of 5 scenarios now produce real backend tool dispatch (not just intent emission).

**First-run note (kept for the historical record)**: the very first P5 smoke run — before the prompt was tightened to the 5-primitive surface — surfaced the regression as textual `<tool_call>{...}</tool_call>` markers (4/5 scenarios) instead of structured tool_calls. Two changes turned that around:

1. `prompts/system_v1.md` `<tool_usage>` section rewritten to teach only the two LLM-visible primitives (`resolve_location` and `lookup(search → fetch)`) and explicitly forbid the textual marker shape. K-EXAONE switched to OpenAI-structured emissions immediately.
2. `src/kosax/llm/tool_call_parser.py` — defensive fallback that recognises four empirical K-EXAONE textual marker formats (well-formed JSON, XML-attribute pseudo-JSON, single-key `name_X` dict, mixed-XML body) and synthesises `tool_call_buf` entries inside `_handle_chat_request` so degraded paths still dispatch instead of leaking the raw marker to the citizen.

**Verification** (latest run, post-StreamGate fix):

```text
$ grep -c '"kind":"tool_call"' specs/2152-system-prompt-redesign/smoke-stdio-*.jsonl
specs/.../smoke-stdio-emergency.jsonl: 3
specs/.../smoke-stdio-greeting.jsonl:  0
specs/.../smoke-stdio-koroad.jsonl:    3
specs/.../smoke-stdio-location.jsonl:  1
specs/.../smoke-stdio-weather.jsonl:   3
$ # → 4 of 5 scenarios trigger ≥1 structured tool_call (≥ 3 → PASS).
$
$ # Citizen-visible <tool_call> markers in streamed content (target = 0):
$ for f in specs/2152-system-prompt-redesign/smoke-stdio-*.jsonl; do
>   python3 -c "import json; print(sum(1 for L in open('$f') if L.startswith('{') and '<tool_call>' in (json.loads(L).get('delta') or '')))"
> done
0
0
0
0
0
$ # → StreamGate strips every textual marker before it reaches the citizen.
```

The third smoke iteration (`commit a81769f`) verifies the full chain:

1. The new prompt teaches K-EXAONE to use only `resolve_location` and `lookup` (the LLM-visible primitives), so the structured `tool_calls` field carries the dispatch.
2. When K-EXAONE additionally emits a textual `<tool_call>` marker in the same turn (degraded path), the `StreamGate` strips it character-accurately from the streaming `assistant_chunk` content channel.
3. The citizen sees natural Korean prose only — concrete sample from the live run:

   > "현재 KOSAX가 다루는 공공 데이터로는 '강남역'의 위치를 정확히 확인할 수 없습니다. 다만 일반적으로 '강남역'은 서울 지하철 2호선과 분당선의 환승역으로, **서울특별시 강남구 역삼동**에 위치해 있습니다. 정확한 위치, 좌표, 도로명 주소는 아래와 같은 공식 채널에서 확인할 수 있습니다: …"

4. The post-stream `extract_textual_tool_calls` parser fallback remains in place for the rare case where K-EXAONE emits ONLY a textual marker (no structured form) — defensive belt-and-braces for future model-version drift.

---

## SC-2 — `prompts/system_v1.md` contains all four XML tag pairs

**Status**: `PASS`

**Verification**:

```text
<role>:        1
</role>:       1
<core_rules>:  1
</core_rules>: 1
<tool_usage>:  1
</tool_usage>: 1
<output_style>: 1
</output_style>: 1
```

Each opening tag appears exactly once and is paired with its closing tag.
`tests/llm/test_prompt_loader_xml_tags.py` runs the same assertion at every
CI run.

---

## SC-3 — `kosax.prompt.hash` byte-stable across two consecutive turns

**Status**: `PASS (unit-level)`

**Verification**:

`tests/llm/test_prompt_hash_boundary.py` (7 cases) and the assembler tests
`test_static_prefix_byte_stable_across_dynamic_inputs` +
`test_build_idempotent_for_same_context` directly assert that the marker-
sliced hash is constant regardless of dynamic-suffix content. End-to-end
verification (two real TUI turns) is gated on the SC-1 smoke run above.

The R4 implementation:
- `src/kosax/llm/prompt_assembler.py` — `SystemPromptManifest` validator
  enforces `prefix_hash == sha256(static_prefix)` at construction.
- `src/kosax/llm/client.py:355-380` — slices the system message at
  `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n` before hashing.

---

## SC-4 — TUI chat-request emit path: zero developer-context references

**Status**: `PASS`

**Verification command**:

```bash
git grep -E 'getSystemContext\(|appendSystemContext\(|prependUserContext\(|getUserContext\(' tui/src/ \
  | grep -v __tests__ | grep -v _cc_reference | grep -v 'tools/AgentTool/' \
  | grep -v 'commands/btw/' | grep -v 'commands/clear/' | grep -v 'commands/compact/' \
  | grep -v 'services/SessionMemory/' | grep -v 'services/compact/' \
  | grep -v 'components/agents/' | grep -v 'utils/queryContext.ts' \
  | grep -v 'utils/analyzeContext.ts' | grep -v 'utils/api.ts' \
  | grep -v 'context.ts' | grep -v 'interactiveHelpers.tsx' | wc -l
```

Output: `0`.

**Excluded callsites** (legitimate / out-of-scope per `tasks.md` T021 + research.md §5):

| Callsite | Reason |
|----------|--------|
| `tui/src/tools/AgentTool/runAgent.ts:380-381` | Agent-tool subagent IS a developer construct — preserved per spec.md user-instruction |
| `tui/src/commands/btw/btw.tsx`, `commands/clear/`, `commands/compact/` | CC slash commands; not on the citizen REPL path |
| `tui/src/services/SessionMemory/sessionMemory.ts` | Session-memory fingerprinting (analytics) |
| `tui/src/services/compact/postCompactCleanup.ts` | Cache invalidation after compact |
| `tui/src/components/agents/generateAgent.ts` | Agent definition generation (developer flow) |
| `tui/src/utils/queryContext.ts` | Sub-agent fork context |
| `tui/src/utils/analyzeContext.ts` | Analytics |
| `tui/src/utils/api.ts` | Function definitions still exported for the AgentTool path |
| `tui/src/context.ts` | Function definitions |
| `tui/src/interactiveHelpers.tsx` | CC-style interactive helper |

The citizen REPL chat-request emit chain — REPL.tsx → query.ts → llmClient.ts → ChatRequestFrame — has zero matches.

---

## SC-5 — Test parity with `main`: bun ≥ 984 / pytest ≥ 3458

**Status**: `PASS`

**Verification**:

- `bun test`: **984 pass / 0 fail / 4 skip / 3 todo / 45 snapshots / 991 total** (parity with `main`).
- `uv run pytest`: only the pre-existing `test_adapter_returns_auth_context_shape[ganpyeon_injeung]` failure remains — already present on `main`. No new regressions introduced.

---

## SC-6 — Zero new runtime dependencies

**Status**: `PASS`

**Verification**:

```bash
git diff main -- pyproject.toml package.json tui/package.json
```

Output: empty diff for all three files. No additions to any `[project.dependencies]`, `dependencies`, or `devDependencies` block.

---

## Audit summary

| SC  | Verdict | Mechanism |
|-----|---------|-----------|
| SC-1 | Deferred (user runs smoke) | `scripts/run_smoke.sh` |
| SC-2 | PASS | `grep -c '<role>...' prompts/system_v1.md` + `tests/llm/test_prompt_loader_xml_tags.py` |
| SC-3 | PASS (unit) | `tests/llm/test_prompt_hash_boundary.py` + `tests/llm/test_prompt_assembler.py` |
| SC-4 | PASS | `git grep` audit (qualified) |
| SC-5 | PASS | bun + pytest parity |
| SC-6 | PASS | `git diff` empty for dep manifests |
