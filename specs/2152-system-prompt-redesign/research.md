# Phase 0 Research — KOSMOS System Prompt Redesign (Epic #2152)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-04-28

This document resolves every NEEDS CLARIFICATION marker (none present in spec.md), maps each of the six R1–R6 design decisions to a concrete reference under `docs/vision.md § Reference materials` (constitution Principle I "Mandatory reference mapping"), and validates the deferred-item table against constitution Principle VI.

The companion deep-research artifact `docs/research/system-prompt-harness-comparison.md` (PR #2151, 433 LOC, 12 sources) is the upstream comparison study; this document is the per-decision distillation that the planning gate requires.

---

## 1. R1 — Section-based static prompt with XML tags

**Decision**: Rewrite `prompts/system_v1.md` as four XML-tagged sections — `<role>`, `<core_rules>`, `<tool_usage>`, `<output_style>` — replacing the current 5-paragraph monolith.

**Primary reference**: `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:444-577` — `getSystemPrompt` composes seven static cacheable sections (`getSimpleIntroSection`, `getSimpleSystemSection`, `getSimpleDoingTasksSection`, `getActionsSection`, `getUsingYourToolsSection`, `getSimpleToneAndStyleSection`, `getOutputEfficiencySection`) before the `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker (line 572), then appends 12 dynamic sections after. KOSMOS collapses CC's seven into four because (a) `getActionsSection` and `getOutputEfficiencySection` are developer-domain concerns (rm -rf, force-push, token efficiency) that do not apply to citizens, and (b) `getSimpleSystemSection` and `getSimpleDoingTasksSection` collapse into `<core_rules>` for the citizen domain.

**Secondary reference**: Anthropic prompt-engineering official guide §8.2 "XML tags for structured content" — "XML tags help Claude parse complex prompts unambiguously, especially when your prompt mixes instructions, context, examples, and variable inputs. Wrapping each type of content in its own tag (e.g. `<instructions>`, `<context>`, `<input>`) reduces misinterpretation. Best practices: consistent, descriptive tag names; nest tags for hierarchy."

**Constitution mapping**: Principle I — Context Assembly row maps to "Claude Code reconstructed (context assembly) primary, Anthropic docs (prompt caching) secondary". Both references satisfied.

**Rationale**: (a) The current 5-paragraph monolith gives the model no structural anchor to differentiate identity prose from tool-usage guidance from language rules; concrete failure observed in `specs/2112-dead-anthropic-models/smoke.txt`. (b) XML tags give Anthropic-family models (and K-EXAONE, which inherits the OpenAI-compatible function-calling surface) a deterministic parse. (c) Four tags is the smallest set that maps 1-to-1 to the four FRs that matter most: identity (FR-002), core rules (FR-011), tool-usage examples (FR-003), output style (FR-011 second clause).

**Alternatives considered**:
- *Keep the 5-paragraph format and add bullet sub-headings.* Rejected — Anthropic guide §8.2 specifically calls out XML tags as preferable to Markdown headings for instruction surfaces; bullet sub-headings would still mix instruction with example with constraint inside the same section.
- *Adopt all seven CC sections verbatim.* Rejected — `<actions>` and `<output_efficiency>` carry developer-domain concerns (file deletion, force-push, token thrift) that do not apply to a citizen-facing reply. Carrying them would re-leak developer framing through the prompt.
- *Use Markdown horizontal rules (`---`) as section dividers.* Rejected — horizontal rules are visual, not semantic; the model has no direct hook to distinguish "this is the role section" from "this is the rule section". XML tags provide the semantic hook.

---

## 2. R2 — Dynamic section assembler with decorator surface

**Decision**: Introduce `kosmos.llm.prompt_assembler` (new module). It exposes a typed `Callable[[PromptAssemblyContext], str | None]` decorator surface so future per-turn injectors (memdir consent summary, ministry-scope opt-ins, session-start date) can register without touching the static prefix.

**Primary reference**: Pydantic AI core concepts — https://pydantic.dev/docs/ai/core-concepts/agent/ (cited in `docs/research/system-prompt-harness-comparison.md §4.2`). Pydantic AI's `@agent.system_prompt` decorator pattern: multiple decorators append in definition order, each receives an optional `RunContext[T]`, executes lazily just before each model request. Constitution Principle I — Tool System row maps to "Pydantic AI (schema-driven registry) primary".

**Secondary reference**: `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:491-555` — CC's `dynamicSections` array. Two memoization classes: `systemPromptSection(name, compute)` (memoized via section cache, cleared on `/clear`/`/compact`) and `DANGEROUS_uncachedSystemPromptSection(name, compute, reason)` (recomputes per turn; explicit reason required). KOSMOS adopts the same two-class memoization framework verbatim. CC `systemPromptSections.ts:1-68` is the framework definition.

**Constitution mapping**: Principle III — all decorator return types are `str | None`; decorator function takes `PromptAssemblyContext` (a Pydantic v2 frozen model). No `Any`.

**Rationale**: (a) The hardest property to preserve as the prompt grows is byte-stability of the static prefix (R4 cache invariant). A decorator-registered dynamic suffix keeps the static prefix lexically separate — there is no code path where adding a new dynamic injector touches the static text. (b) Pydantic AI's pattern is the cleanest in the seven-harness study (per `system-prompt-harness-comparison.md §4`); LangGraph's "callable receives full graph state" is more powerful but heavier and would pull in graph-state types KOSMOS does not have. (c) CC's two-class memoization (cached vs DANGEROUS_uncached) gives the future-injector author a structural choice, not a free-for-all.

**Alternatives considered**:
- *Single inline assembly inside `_handle_chat_request`.* Rejected — every new injector mutates a hot-path function and risks re-introducing the byte-stability bug. The decorator surface is the structural defence.
- *OpenAI Agents SDK pattern (`instructions: str | Callable[[ctx, agent], str | Awaitable[str]]`)* — Rejected for primary because the callable returns the *entire* prompt, not a section, so the static prefix would have to be re-assembled on every turn. Pydantic AI's per-section decorator is the correct grain.
- *LangGraph `Prompt = SystemMessage | str | Callable[[StateSchema], LanguageModelInput]`.* Rejected — too heavyweight; KOSMOS does not have a graph-state schema, and would need to invent one to satisfy the signature.

---

## 3. R3 — Citizen utterance XML envelope

**Decision**: Wrap each citizen user message in `<citizen_request>...</citizen_request>` XML tags at the chat-request boundary inside `_handle_chat_request` (Python backend) before the message is added to the LLM message stack. The wrapping is structural — it is invisible to the citizen but visible to the model, and it gives the model a reliable hook to distinguish system instructions from citizen-pasted content.

**Primary reference**: Anthropic prompt-engineering guide §8.2 (XML tags) + the long-context guidance §8.3 ("Place your long documents and inputs near the top of your prompt, above your query, instructions, and examples"). The same XML-tag mechanism that R1 uses for system sections becomes the prompt-injection guard for user input.

**Secondary reference**: `restored-src/src/utils/api.ts` — CC does not formally wrap user input but does enforce a structural boundary by always emitting the user content as a separate `messages[i]` object. KOSMOS goes one step further because citizen-pasted content is the highest prompt-injection risk class (forwarded forms, screenshots-as-text, instruction-shaped notices); the wrap is a defence-in-depth layer over message separation.

**Constitution mapping**: Principle II — Fail-Closed Security. The wrap strengthens prompt-injection defence; it does not relax any auth or permission default.

**Rationale**: (a) Citizens routinely paste content that contains heading-like text (`## Available tools`, `<system>...`) — without a structural wrap the model has no anchor to know where citizen text ends and instructions begin. (b) The wrap is a single string-format change; cost is essentially zero. (c) Static repository tests (`grep`-based) can assert presence trivially.

**Alternatives considered**:
- *No wrap; rely on `messages[].role == "user"` separation.* Rejected — model attention does not respect the conceptual `role` boundary as strongly as it respects an explicit XML hook, especially for Opus 4.7 which is documented to interpret prompts more literally (Anthropic guide §"More literal instruction following").
- *Wrap with sentinel string (`---BEGIN CITIZEN UTTERANCE---`).* Rejected — sentinel strings are not as deterministically parseable for the model as XML tags, and they collide with citizen-pasted content that may itself contain dashes.

---

## 4. R4 — `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker + cache-prefix hash

**Decision**: Insert the literal string `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` between the static prefix (R1 sections) and the dynamic suffix (R2 assembler output). The OTEL `kosmos.prompt.hash` attribute (Spec 026) hashes only the prefix up to the boundary marker (exclusive). Cache prefix invariant: across two turns of the same session with an unchanged tool inventory, the prefix bytes (and thus the hash) are byte-identical.

**Primary reference**: `restored-src/src/constants/prompts.ts:572-575` — CC emits `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` only when `shouldUseGlobalCacheScope()` returns true. The Anthropic Messages API `cache_control` blocks read up to that boundary, allowing the static prefix to share a cache prefix across turns while dynamic suffixes (env info, memory, etc.) recompute without invalidating the prefix hash.

**Secondary reference**: Anthropic prompt-engineering guide — the same guide that documents prompt caching at the Messages API level. Spec 026 is the existing KOSMOS prompt-cache infrastructure (manifest SHA-256 + `kosmos.prompt.hash` OTEL attribute). The R4 work is the *correctness* layer over that infrastructure: today the hash includes the entire system text including the dynamic suffix, which mathematically cannot be byte-stable across turns once any dynamic injector fires. R4 makes the hash semantically meaningful for the first time.

**Constitution mapping**: Principle I — Context Assembly row "Claude Code reconstructed (context assembly) primary, Anthropic docs (prompt caching) secondary" — both satisfied. Principle III — `PromptAssemblyContext` and `SystemPromptManifest` Pydantic v2 frozen.

**Rationale**: (a) Without the boundary marker the dynamic suffix cannot grow without invalidating the cache hash. (b) The literal string `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` is the same identifier CC uses, which means anyone reading the KOSMOS source with CC familiarity recognises it instantly (constitution Principle I — reference-driven). (c) Hashing only the prefix gives observability that *means* something — a hash mismatch across two same-session turns now indicates a real bug (probably an injector accidentally writing into the static prefix).

**Alternatives considered**:
- *Hash the full system text and accept that the hash flips per turn.* Rejected — that is what Spec 026 already does today; observation is meaningless and the symptom (no cache hits) is invisible.
- *Use a comment marker (`<!-- DYNAMIC_BOUNDARY -->`).* Rejected — Markdown comments are visible to the model and could be confused with citizen-pasted Markdown. CC's bare-string sentinel is the established pattern.

---

## 5. R5 — Excise developer-context injectors from the citizen TUI chat-request emit path

**Decision**: Remove `getSystemContext`, `getUserContext`, `appendSystemContext`, and `prependUserContext` from every callsite that participates in the citizen TUI `ChatRequestFrame` emit path. Specifically: `tui/src/utils/api.ts:438,450,492-493`, `tui/src/query.ts:443,627`, `tui/src/screens/REPL.tsx:2798,3035,5477`, `tui/src/main.tsx:201,209,239,1303,1309`, `tui/src/utils/queryContext.ts:70-71`. Keep the function definitions in `tui/src/context.ts:36-189` because `tui/src/tools/AgentTool/runAgent.ts:380-381` is the legitimate, in-module developer-context consumer (the agent tool itself is a developer construct, used inside its own module — it does not leak to citizen chat).

**Primary reference**: `restored-src/src/context.ts:36-189` is the CC original. Its purpose is to inject developer-domain situational awareness (cwd, git status, recent commits, CLAUDE.md content) into the system context. This is correct behaviour for CC because CC is a developer-domain harness. KOSMOS is a citizen-domain harness — the same payload becomes a privacy and framing leak (concretely observed in the Epic #2112 smoke run: "현재 `/Users/um-yunsang/KOSMOS/tui` 디렉토리에서 작업 중이며…").

**Secondary reference**: AGENTS.md "harness, not reimplementation" (memory `feedback_harness_not_reimplementation`) — KOSMOS preserves CC's UX and structure, but rewrites domain-bound modules. The dev-context injector is one such domain-bound module. The Pydantic AI / OpenAI Agents SDK / LangGraph harness study (`system-prompt-harness-comparison.md §3, §4, §6`) shows that none of the citizen-or-general-purpose harnesses inject host-machine context into the prompt — that pattern is unique to developer harnesses.

**Constitution mapping**: Principle V — Policy Alignment. PIPA "consent-based access" — citizens did not consent to having developer surveillance metadata folded into their conversation. Principle II — Fail-Closed: removing a non-citizen data source from a citizen flow is the most conservative move.

**Rationale**: (a) Without R5 the prompt redesign cannot ship — every R1 / R2 / R3 / R4 / R6 win is overwritten the moment the TUI prepends `gitStatus`. (b) The excision is surgical: keep the callee functions and the agent-tool callsite; cut the chat-request callsites. SC-4 grep audit makes the cut auditable.

**Alternatives considered**:
- *Make `getSystemContext` return `{}` in citizen mode and add a `mode` flag.* Rejected — adds a runtime branch where a deletion suffices; memory `feedback_no_stubs_remove_or_migrate` ("스텁 X. KOSMOS 미사용 기능은 import + call site 모두 제거"). Also: a runtime branch is something a future contributor could accidentally flip.
- *Delete the entire `context.ts` module.* Rejected — `tools/AgentTool/runAgent.ts` legitimately consumes it. Surgical excision is the right grain.

---

## 6. R6 — Per-tool trigger-phrase emission in `build_system_prompt_with_tools`

**Decision**: Strengthen `src/kosmos/llm/system_prompt_builder.py:30-80` `build_system_prompt_with_tools` so that the `## Available tools` block emits one extra line per tool — a one-sentence "trigger phrase" describing in citizen-readable Korean / English exactly when the model should call that tool. The phrase is sourced from the tool's `search_hint` field (existing Pydantic v2 field, already required by constitution Principle III) and a new `trigger_examples` field that lists 2–3 concrete Korean utterances the tool covers.

**Primary reference**: Anthropic prompt-engineering guide §"Tool use triggering" (cached at the tool-results path cited in spec.md) — verbatim quote: "Claude Opus 4.7 has a tendency to use tools less often than Claude Opus 4.6 and to use reasoning more. … For scenarios where you want more tool use, you can also adjust your prompt to explicitly instruct the model about when and how to properly use its tools. For instance, if you find that the model is not using your web search tools, clearly describe why and how it should." This is the single most directly cited intervention against under-triggering.

**Secondary reference**: `system-prompt-harness-comparison.md §10 R6` — the synthesis that the per-tool trigger phrase is "the single most impactful change to fix tool under-triggering on Opus-4.6+ models". Constitution Principle I — Tool System row "Pydantic AI (schema-driven registry) primary" — `search_hint` is already part of the schema-driven contract.

**Constitution mapping**: Principle III — `trigger_examples: list[str]` is a fully typed Pydantic v2 field. No `Any`. Principle IV — adapter changes are bounded to *adding* a field; no live-API surface change.

**Rationale**: (a) R1's `<tool_usage>` section gives a coarse list of trigger examples for the most common tools. R6 gives a *per-tool* trigger phrase that lives next to the tool's structured description in the inventory block, exactly where the model will read it during tool selection. (b) The `search_hint` field is already populated for every adapter (Spec 022 hard rule); reusing it is free. (c) The new `trigger_examples` field is an additive Pydantic field with a default of `[]`, so existing adapters that have not opted in continue to work without breakage.

**Alternatives considered**:
- *Leave the inventory block unchanged; rely on R1 `<tool_usage>` for trigger guidance.* Rejected — Anthropic guide explicitly says the tool description is the place to put trigger guidance, not a separate section. The model attends to text adjacent to the tool definition more strongly than text in a different section.
- *Generate trigger phrases via LLM at registry build time.* Rejected — non-determinism into a prompt that needs to be byte-stable for cache invariance (R4).

---

## 7. Deferred-item validation (Constitution Principle VI gate)

This subsection executes the Phase 0 gate from the `/speckit-plan` skill: scan spec.md for unregistered deferral patterns and confirm every "Deferred to Future Work" entry has a tracking-issue placeholder.

**Spec deferred-item table** (from `spec.md § Scope Boundaries & Deferred Items`):

| Item | Tracking Issue |
|------|----------------|
| Multi-language i18n (Korean / English / 日本語 dynamic switching) | `NEEDS TRACKING` |
| Output-style configuration surface (citizen accessibility) | `NEEDS TRACKING` |
| Prompt A/B evaluation harness with shadow-eval workflow | `NEEDS TRACKING` |
| Rich dynamic injectors for memdir consent and ministry-scope state | `NEEDS TRACKING` |

All four entries have `NEEDS TRACKING` markers; `/speckit-taskstoissues` will resolve them by creating placeholder issues (constitution Principle VI mechanism). No entry is missing the column.

**Free-text deferral-pattern scan** (greps over `specs/2152-system-prompt-redesign/spec.md`):

```text
- "separate epic"        — 0 matches outside the table
- "future epic"          — 0 matches
- "Phase 2+" / "P2+"     — only inside the deferred table cell ("P5+ (UI L2 follow-up)")
- "v2"                   — 0 matches
- "deferred to"          — only inside the deferred table cell ("Spec 026 P2 backlog")
- "later release"        — 0 matches
- "out of scope for v1"  — 0 matches
```

All deferral patterns are confined to the structured table and to the explicit "Out of Scope (Permanent)" bullet list. No prose-only deferrals found. **Constitution Principle VI gate: PASS.**

---

## 8. References summary table

| # | Source | Where it is cited in this Epic |
|---|---|---|
| 1 | `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:175-590` | R1 (sections), R2 (dynamic array), R4 (BOUNDARY marker) |
| 2 | `.references/claude-code-sourcemap/restored-src/src/constants/systemPromptSections.ts:1-68` | R2 (memoization framework — `systemPromptSection` vs `DANGEROUS_uncachedSystemPromptSection`) |
| 3 | `.references/claude-code-sourcemap/restored-src/src/utils/systemPrompt.ts:30-123` | Reference for 5-priority override hierarchy; KOSMOS does not implement coordinator/agent overrides in this Epic but the hierarchy informs how the new module will accept future overrides without redesign |
| 4 | `.references/claude-code-sourcemap/restored-src/src/context.ts:36-189` | R5 (CC original definition of the developer-context injector being excised from the citizen path) |
| 5 | Anthropic prompt-engineering official guide (cached at `~/.claude/projects/-Users-um-yunsang-KOSMOS/d2a7266a-45dc-478b-9a8c-7c21f2257281/tool-results/toolu_01AxMFGJ4MYWLbPLWbRt9qju.txt`) §"Tool use triggering" / §8.2 XML tags / §"More literal instruction following" / §"Response length and verbosity" | R1 (XML tags), R3 (citizen wrap), R4 (cache prefix), R6 (trigger phrase) |
| 6 | Pydantic AI core concepts — `@agent.system_prompt` decorator (https://pydantic.dev/docs/ai/core-concepts/agent/) | R2 (decorator surface) |
| 7 | `docs/research/system-prompt-harness-comparison.md` (PR #2151) | All R1–R6 (synthesis) |
| 8 | `.specify/memory/constitution.md` | Constitution Check gates I–VI |
| 9 | `docs/vision.md § Reference materials` | Cited in plan.md Constitution Check; mandatory per Principle I |
| 10 | `prompts/system_v1.md` (KOSMOS current) · `prompts/manifest.yaml` (Spec 026) · `src/kosmos/llm/system_prompt_builder.py:30-80` · `src/kosmos/ipc/stdio.py:552-571 + :1129-1230` · `tui/src/ipc/llmClient.ts:239-260` · `tui/src/context.ts:36-189` · `tui/src/utils/api.ts:438,450,492-493` · `tui/src/query.ts:443,627` · `tui/src/screens/REPL.tsx:2798,3035,5477` · `tui/src/main.tsx:201,209,239,1303,1309` · `tui/src/utils/queryContext.ts:70-71` · `tui/src/tools/AgentTool/runAgent.ts:380-381` (untouched) | KOSMOS code paths to modify or audit |
