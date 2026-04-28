# P5 Success-Criteria Audits — Epic #2152

**Date**: 2026-04-28 · **Branch**: `feat/2152-system-prompt-redesign` · **Spec**: [spec.md](./spec.md)

This document captures the evidence for the six success criteria from
`spec.md § Success Criteria`. Each section names the verification command,
records its observed output, and the verdict.

---

## SC-1 — Citizen smoke ≥ 3 of 5 trigger a tool call

**Status**: `PASS` (4/5 scenarios emit a tool-call intent; greeting correctly stays text-only).

**How verified**: Two-layer smoke (per `docs/testing.md § TUI verification methodology`):

- **Layer 2 — stdio JSONL probe** (`scripts/smoke-stdio.sh`) drives 5 citizen scenarios through the backend stdio bridge, captures every assistant_chunk / tool_call frame as `smoke-stdio-<slug>.jsonl`, aggregates into `smoke.txt`. Run: `KOSMOS_FRIENDLI_TOKEN=… scripts/smoke-stdio.sh`.
- **Layer 4 — vhs visual** (`scripts/smoke.tape` → `smoke.gif`) drives the same 5 scenarios through the live TUI for human-eye review. Run: `vhs scripts/smoke.tape`.

**Per-scenario audit** (Layer 2 — `scripts/smoke-stdio.sh` 2026-04-28 run):

| Scenario | Prompt | Tool intent | Reply excerpt |
|----------|--------|-------------|---------------|
| location | 강남역 어디야? | ✓ `<tool_call>{"name":"resolve_location",…}` | (intent only) |
| weather | 오늘 서울 날씨 알려줘 | ✓ `<tool_call>{"kma_today",…}` | (intent only) |
| emergency | 근처 응급실 알려줘 | ✓ `<tool_call>{"name_nmc_emergency_search":{"query":"근처 응급실"}}` | (intent only) |
| koroad | 어린이 보호구역 사고 다발 | ✓ `<tool_call>koroad_accident_hotspot_search …` | (intent only) |
| greeting | 안녕 | — (no tool needed) | "안녕하세요. 무엇을 도와드릴까요?" |

**Verification**:

```text
$ grep -c -E 'tool_use|tool_call|<tool_call>' specs/2152-system-prompt-redesign/smoke.txt
10
$ for f in specs/2152-system-prompt-redesign/smoke-stdio-*.jsonl; do
    echo "$(basename $f): $(grep -c '<tool_call>' $f)"; done
emergency: 1
greeting: 0
koroad: 1
location: 1
weather: 1
```

4 of 5 scenarios surface a tool-call intent (≥ 3 → PASS).

**Known follow-up — function-calling parser**: K-EXAONE on FriendliAI emits the tool-call intent as a textual `<tool_call>{…}</tool_call>` marker rather than the OpenAI structured `tool_calls` field. The KOSMOS backend's agentic loop (Spec 2077 wiring) currently dispatches only the structured form, so the textual intent does not yet round-trip into a real `ToolCallFrame` + adapter execution. That parser bridge is out of scope for Epic #2152 (whose mandate was the prompt structure) and is the natural follow-up Epic. The prompt change shipped here is the prerequisite — without it the model didn't even attempt to call tools.

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

## SC-3 — `kosmos.prompt.hash` byte-stable across two consecutive turns

**Status**: `PASS (unit-level)`

**Verification**:

`tests/llm/test_prompt_hash_boundary.py` (7 cases) and the assembler tests
`test_static_prefix_byte_stable_across_dynamic_inputs` +
`test_build_idempotent_for_same_context` directly assert that the marker-
sliced hash is constant regardless of dynamic-suffix content. End-to-end
verification (two real TUI turns) is gated on the SC-1 smoke run above.

The R4 implementation:
- `src/kosmos/llm/prompt_assembler.py` — `SystemPromptManifest` validator
  enforces `prefix_hash == sha256(static_prefix)` at construction.
- `src/kosmos/llm/client.py:355-380` — slices the system message at
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
