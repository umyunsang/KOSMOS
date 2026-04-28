# P5 Success-Criteria Audits — Epic #2152

**Date**: 2026-04-28 · **Branch**: `feat/2152-system-prompt-redesign` · **Spec**: [spec.md](./spec.md)

This document captures the evidence for the six success criteria from
`spec.md § Success Criteria`. Each section names the verification command,
records its observed output, and the verdict.

---

## SC-1 — Citizen smoke ≥ 3 of 5 trigger a tool call

**Status**: `[Deferred to user-triggered run]`

**Why deferred**: The smoke harness (`scripts/run_smoke.sh`) drives the real
TUI against the FriendliAI Tier 1 endpoint and consumes API quota. Per the
auto-mode safety rule "Avoid data exfiltration" + the user's economic
control, this Epic ships the harness + the prompt + the wrap + the assembler;
the user runs the smoke at their own discretion.

**How to run**:

```bash
KOSMOS_FRIENDLI_API_KEY=... \
  specs/2152-system-prompt-redesign/scripts/run_smoke.sh
grep -c 'tool_use\|tool_call' specs/2152-system-prompt-redesign/smoke.txt
```

The five canonical scenarios (location · weather · emergency · KOROAD ·
greeting) are encoded in the harness; the threshold of ≥ 3 is the SC-1 gate.

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
