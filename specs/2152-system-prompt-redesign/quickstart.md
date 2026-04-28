# Quickstart — KOSMOS System Prompt Redesign (Epic #2152)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md) · **Contracts**: [contracts/](./contracts/)

How a developer working on KOSMOS would touch the new prompt-assembly surface, after Epic #2152 ships.

---

## 1. Read the citizen system prompt

After the Epic ships, `prompts/system_v1.md` is the four-XML-section Korean-public-services prompt. The body lives in the repo as canonical source-of-truth; the SHA-256 in `prompts/manifest.yaml` matches it.

```bash
cat prompts/system_v1.md
# <role>
# 당신은 KOSMOS, 한국 공공 서비스 AI 어시스턴트입니다 ...
# </role>
#
# <core_rules>
# - 항상 한국어로 응답합니다 ...
# </core_rules>
#
# <tool_usage>
# 시민이 위치, 날씨, 응급실, 사고 다발 구역 등을 물으면 ...
# </tool_usage>
#
# <output_style>
# 응답은 한국어로, 자료 출처를 명확히 인용합니다 ...
# </output_style>
```

---

## 2. Build a system prompt manifest in Python

```python
from pathlib import Path
from kosmos.context.prompt_loader import PromptLoader
from kosmos.llm.prompt_assembler import (
    PromptAssembler,
    PromptAssemblyContext,
    system_prompt,
)

loader = PromptLoader(manifest_path=Path("prompts/manifest.yaml"))
assembler = PromptAssembler(static_prefix_source=loader)

manifest = assembler.build(
    PromptAssemblyContext(
        session_id="0193f3c9-9eaf-7000-a000-000000000001",
        session_started_at=...,  # datetime.now(UTC)
        tool_inventory=("lookup", "resolve_location", "kma_forecast_fetch"),
        dynamic_inputs={},
    )
)

assert "<role>" in manifest.static_prefix
assert manifest.static_prefix.endswith("\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n")
assert manifest.dynamic_suffix == ""        # no injector registered
assert len(manifest.prefix_hash) == 64      # SHA-256 hex
```

---

## 3. Register a dynamic-suffix injector (R2 surface)

```python
@system_prompt(assembler, name="ministry_scope")
def ministry_scope_section(ctx: PromptAssemblyContext) -> str | None:
    scope = ctx.dynamic_inputs.get("ministry_scope")
    if not scope:
        return None
    return f"<ministry_scope>{scope}</ministry_scope>"
```

The decorator runs at module-import time. Once registered, every subsequent `assembler.build(ctx)` call invokes the injector. Returning `None` opts out for that turn without producing a stray newline (CC parity).

The cache-prefix invariant still holds: registering or unregistering injectors does not change `manifest.static_prefix` or `manifest.prefix_hash`.

---

## 4. Verify the cache-prefix hash is byte-stable across turns (SC-3)

```python
ctx_turn1 = PromptAssemblyContext(
    session_id="...", session_started_at=...,
    tool_inventory=("lookup",), dynamic_inputs={"ministry_scope": "kma"},
)
ctx_turn2 = PromptAssemblyContext(
    session_id="...", session_started_at=...,
    tool_inventory=("lookup",), dynamic_inputs={"ministry_scope": "kma,hira"},
)

m1 = assembler.build(ctx_turn1)
m2 = assembler.build(ctx_turn2)

assert m1.prefix_hash == m2.prefix_hash      # static prefix is stable
assert m1.dynamic_suffix != m2.dynamic_suffix  # dynamic suffix grew
```

---

## 5. Run the citizen-domain TUI smoke (SC-1, SC-4)

The text-log-first smoke convention (memory `feedback_vhs_tui_smoke`) — `expect`/`asciinema` text logs are the primary artefact, gif/png are auxiliary.

```bash
# 1) launch TUI under expect with the 5 citizen scenarios
specs/2152-system-prompt-redesign/scripts/run_smoke.sh \
    > specs/2152-system-prompt-redesign/smoke.txt

# 2) SC-1 — count tool-call frames in the smoke log
grep -c 'tool_use\|tool_call' specs/2152-system-prompt-redesign/smoke.txt
# → must be ≥ 3

# 3) SC-4 — confirm no developer context in chat-request emit path
git grep -E 'getSystemContext|appendSystemContext|prependUserContext|getUserContext' tui/src/ \
    | grep -v __tests__ \
    | grep -v _cc_reference
# → must be empty
```

The five scenarios are:

1. "강남역 어디야?" — expect `resolve_location` call (SC-1 + Story 1).
2. "오늘 서울 날씨 알려줘" — expect `kma_forecast_fetch` call (SC-1 + Story 2).
3. "근처 응급실 알려줘" — expect `nmc_emergency_search` or `nfa119_*` call.
4. "어린이 보호구역 사고 다발" — expect `koroad_*` call.
5. "안녕" — greeting; no tool call expected. (SC-1 lower-bound check: ≥ 3 of 5 trigger a tool, leaving room for 1–2 non-tool scenarios.)

---

## 6. Test parity (SC-5)

```bash
uv run pytest -q                    # → ≥ 3458 passing (1 pre-existing failure tolerated)
cd tui && bun test --bail=false     # → ≥ 984 passing (1 pre-existing snapshot failure tolerated)
```

---

## 7. Dependency invariant (SC-6)

```bash
git diff main -- pyproject.toml package.json tui/package.json
# → must show no net additions inside [project.dependencies]
#   or "dependencies" / "devDependencies"
```

---

## 8. References

- Static prompt source-of-truth: `prompts/system_v1.md` + `prompts/manifest.yaml` (Spec 026)
- Assembler module: `src/kosmos/llm/prompt_assembler.py` (new)
- Tool inventory augmentation: `src/kosmos/llm/system_prompt_builder.py` (R6 extension)
- IPC wiring: `src/kosmos/ipc/stdio.py:_handle_chat_request` (R3 + R4 wiring)
- TUI excision callsites: `tui/src/utils/api.ts`, `tui/src/utils/queryContext.ts`, `tui/src/query.ts`, `tui/src/screens/REPL.tsx`, `tui/src/main.tsx` (R5)
- CC reference: `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:175-590`, `:30-123` `systemPrompt.ts`, `systemPromptSections.ts:1-68`
- Anthropic prompt-engineering guide (cached): `~/.claude/projects/-Users-um-yunsang-KOSMOS/d2a7266a-45dc-478b-9a8c-7c21f2257281/tool-results/toolu_01AxMFGJ4MYWLbPLWbRt9qju.txt`
- Pydantic AI core concepts: https://pydantic.dev/docs/ai/core-concepts/agent/
- Deep research synthesis: `docs/research/system-prompt-harness-comparison.md`
