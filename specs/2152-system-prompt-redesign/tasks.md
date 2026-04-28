---

description: "Task list for KOSMOS System Prompt Redesign (Epic #2152)"
---

# Tasks: KOSMOS System Prompt Redesign (Epic #2152)

**Input**: Design documents from `/specs/2152-system-prompt-redesign/`
**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: TDD-style — every code task is paired with the test file that asserts it. Test files are listed alongside source-file tasks (not as separate phases) because the per-contract invariants (I-A1..I-A7, I-B1..I-B6, I-C1..I-C6) are the test specifications.

**Organization**: Tasks are grouped by **implementation phase** (P1..P5 from `plan.md`) so the build order is unambiguous. Each task carries a `[USx]` story label mapping it back to the user stories in `spec.md`. Setup and Foundational phases come first; Polish comes last.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1..US6) mapping to `spec.md` user stories
- All file paths are absolute repository paths

## Path Conventions

KOSMOS is a polyglot harness with two long-lived top-level source trees:
- **Backend** (Python 3.12+): `src/kosmos/`, `tests/` at repo root
- **TUI** (TypeScript on Bun v1.2.x): `tui/src/`, `tui/src/__tests__/`
- **Prompts**: `prompts/` (canonical Markdown + SHA-256 manifest)
- **Specs**: `specs/2152-system-prompt-redesign/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working environment, capture parity baselines, and prepare the smoke-harness scaffolding.

- [ ] T001 Confirm current branch is `feat/2152-system-prompt-redesign` and `git status` is clean before starting any code work (memory `feedback_check_references_first`).
- [ ] T002 [P] Snapshot test-parity baseline: run `bun test` and `uv run pytest -q` once on the freshly checked-out branch and record the pass counts in `specs/2152-system-prompt-redesign/notes-parity-baseline.txt` (used to gate SC-5 at the end of P5).
- [ ] T003 [P] Snapshot dependency baseline: record `git diff main -- pyproject.toml package.json tui/package.json` (must be empty at this point) into `specs/2152-system-prompt-redesign/notes-deps-baseline.txt` (used to gate SC-6).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tiny pre-flight items every later phase depends on. KOSMOS already has the long-lived modules touched by this Epic — there is no schema, no migration, no new framework wiring needed before P1 can start.

- [ ] T004 Create the smoke-harness directory `specs/2152-system-prompt-redesign/scripts/` so per-scenario expect scripts can land throughout P5 without a directory race.
- [ ] T005 Audit `tui/src/tools/AgentTool/runAgent.ts:380-381` — confirm the `getUserContext` / `getSystemContext` callsite there is the **legitimate developer-tool path** that R5 must NOT touch (research.md §5; preserves agent-tool functionality).

**Checkpoint**: Foundation confirmed — P1 can begin.

---

## Phase 3: P1 — R1 (XML-tagged static prompt) + R6 (per-tool trigger phrases)

**Goal**: Replace the 5-paragraph `prompts/system_v1.md` with a 4-section XML-tagged citizen-services prompt, and strengthen the tool-inventory block to emit a per-tool trigger phrase. This is the highest-impact / lowest-risk phase — single-file rewrites with strong test invariants.

**Independent Test**: `prompts/system_v1.md` contains all four XML tag pairs (SC-2). `build_system_prompt_with_tools(base, tools)` emits `**Trigger**:` line per tool (I-B2). Empty-tools call still byte-identical to `base` (I-B1, FR-015).

### R1 — Static prompt rewrite

- [ ] T006 [US1] [US2] [US3] [US6] Rewrite `prompts/system_v1.md` as four XML-tagged sections (`<role>`, `<core_rules>`, `<tool_usage>`, `<output_style>`) with citizen-domain Korean prose; remove the `{platform_name}` and `{language}` placeholders that the current loader does not actually substitute (FR-001, FR-002, FR-011, SC-2).
- [ ] T007 [US1] [US2] [US3] [US6] Update `prompts/manifest.yaml` `system_v1` SHA-256 to match the new file content (FR-013; Spec 026 invariant). Verify by re-loading via `PromptLoader` in `uv run python -c "..."` smoke.
- [ ] T008 [P] [US1] [US2] [US3] [US6] Add `tests/llm/test_prompt_loader_xml_tags.py` asserting all four required XML tag pairs are present in the loaded `system_v1` text (SC-2; supports I-A4 in P4).

### R6 — Per-tool trigger-phrase emission

- [ ] T009 [US1] [US2] Add a `trigger_examples: list[str] = Field(default_factory=list, max_length=5)` Pydantic v2 field on the existing tool-adapter base schema in `src/kosmos/tools/_base.py` (data-model §4; backward-compatible additive field).
- [ ] T010 [US1] [US2] Extend `src/kosmos/llm/system_prompt_builder.py:30-80` `build_system_prompt_with_tools` to emit the `**Trigger**:` line per tool between description and `**Parameters**:`, sourcing the sentence from the tool's `search_hint` and the example utterances from `trigger_examples` (FR-003, FR-004; contract `system-prompt-builder.md` I-B2..I-B6).
- [ ] T011 [P] [US1] [US2] Extend `tests/llm/test_system_prompt_builder.py` with cases I-B1 (empty-tools no-op, FR-015), I-B2 (trigger line present per tool), I-B3 (no `— 예:` clause when examples empty), I-B4 (examples wrapped in double quotes), I-B5 (deterministic output), I-B6 (base prefix unchanged).
- [ ] T012 [P] [US1] Author `trigger_examples` for the meta-tool surface — `lookup` and `resolve_location` adapters in `src/kosmos/tools/lookup.py` and `src/kosmos/tools/resolve_location.py` (or wherever the registered `GovAPITool` instances live for these two tools).
- [ ] T013 [P] [US2] Author `trigger_examples` for the six KMA forecast adapters in `src/kosmos/tools/kma/`.
- [ ] T014 [P] [US1] [US2] Author `trigger_examples` for the HIRA hospital adapter, the NMC emergency adapter, and the NFA119 adapter (medical / emergency cluster).
- [ ] T015 [P] [US1] [US2] Author `trigger_examples` for the two KOROAD adapters and the MOHW welfare adapter.

**Checkpoint**: P1 complete — `prompts/system_v1.md` is XML-tagged and the system-prompt builder emits per-tool trigger phrases. SC-2 verifiable; tool-call rate not yet improved (depends on P3+P4 wiring).

---

## Phase 4: P2 — R5 (Excise developer-context injectors from the citizen TUI chat-request emit path)

**Goal**: Remove `getSystemContext` / `getUserContext` / `appendSystemContext` / `prependUserContext` from every TUI callsite that participates in citizen `ChatRequestFrame` emission. Keep the function definitions in `tui/src/context.ts` (the agent-tool path in `tools/AgentTool/runAgent.ts` is the legitimate consumer).

**Independent Test**: SC-4 — `git grep -E 'getSystemContext|appendSystemContext|prependUserContext|getUserContext' tui/src/ | grep -v __tests__ | grep -v _cc_reference` returns zero lines outside `tools/AgentTool/runAgent.ts`. Smoke replies contain no path / branch / commit text.

- [ ] T016 [US3] Drop `appendSystemContext` and `prependUserContext` from the chat-request emit codepath in `tui/src/utils/api.ts` (lines 438, 450, 492-493 today). Keep their internal definitions if they are still consumed by `runAgent.ts`; otherwise delete them (memory `feedback_no_stubs_remove_or_migrate`). FR-010, SC-4.
- [ ] T017 [US3] Drop the `Promise.all([getUserContext(), getSystemContext()])` block from `tui/src/utils/queryContext.ts:70-71` for any code path reachable from the citizen chat-request emit path. FR-010, SC-4.
- [ ] T018 [US3] Remove the `appendSystemContext(systemPrompt, systemContext)` and `prependUserContext(messagesForQuery, userContext)` callsites from `tui/src/query.ts:443,627` for the citizen chat-request emit path. FR-010, SC-4.
- [ ] T019 [US3] Remove the `Promise.all` `getSystemContext` / `getUserContext` calls from `tui/src/screens/REPL.tsx:2798,3035,5477` for the citizen chat-request emit path. FR-010, SC-4.
- [ ] T020 [US3] Remove the `void getSystemContext()` and `void getUserContext()` prefetch calls from `tui/src/main.tsx:201,209,239,1303,1309` (these warm the citizen-irrelevant context cache at app boot). FR-010, SC-4.
- [ ] T021 [P] [US3] Audit `tui/src/interactiveHelpers.tsx:151` (`void getSystemContext()`) and `tui/src/utils/analyzeContext.ts:279` — apply excision if the callsite participates in the citizen chat-request path; preserve if it is a developer-tool path. Document the verdict inline as a brief code comment if preserved (rule from memory `feedback_no_stubs_remove_or_migrate`).
- [ ] T022 [P] [US3] Add `tui/src/__tests__/chatRequestEmit.test.ts` asserting that an emitted `ChatRequestFrame` carries no `gitStatus`, `cwd`, `claudeMd`, or `currentDate` payload anywhere in `frame.system` or any `frame.messages[].content` value. (SC-4, supports I-C5.)
- [ ] T023 [P] [US3] Add a `tui/src/__tests__/devContextAudit.test.ts` static-grep style test that runs the SC-4 audit command via Bun's child-process API and asserts zero matches outside `__tests__/` and `_cc_reference/` (CI guard).

**Checkpoint**: P2 complete — citizen chat requests no longer carry developer surveillance metadata. SC-4 verifiable.

---

## Phase 5: P3 — R3 (Citizen utterance envelope) + R4 (BOUNDARY marker + static-prefix-only hash)

**Goal**: Wrap each citizen user message in `<citizen_request>` XML tags at the chat-request boundary (R3). Insert the literal `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker and rewire `kosmos.prompt.hash` to hash only the static prefix up to the marker (R4). The R4 wiring is initially inline in `stdio.py`; P4 refactors it into the new `prompt_assembler` module.

**Independent Test**: SC-3 — `kosmos.prompt.hash` is byte-stable across two consecutive turns of the same session. Story 4 — citizen-pasted instruction-shaped text is wrapped in `<citizen_request>` and ignored as instructions.

### R3 — Citizen utterance envelope

- [ ] T024 [US4] Create `src/kosmos/ipc/citizen_request.py` exporting `wrap_citizen_request(text: str) -> str` per data-model §5 (empty-input no-op preserved for FR-015 spirit).
- [ ] T025 [US4] In `src/kosmos/ipc/stdio.py:_handle_chat_request` (around the `for m in frame.messages:` loop near line 1202), apply `wrap_citizen_request(m.content)` only when `m.role == "user"`; pass through unchanged for `tool` / `assistant` / `system` roles (FR-009; contract I-C3, I-C4, I-C6).
- [ ] T026 [P] [US4] Extend `tests/ipc/test_stdio_chat_request.py` with `test_user_messages_wrapped` (I-C3), `test_non_user_messages_not_wrapped` (I-C4), and `test_empty_user_no_wrap` (I-C6) cases.

### R4 — Boundary marker + static-prefix-only hash (inline plumbing; P4 refactors)

- [ ] T027 [US5] Add a module-level constant `_DYNAMIC_BOUNDARY_MARKER = "\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n"` in `src/kosmos/ipc/stdio.py` and append it to the assembled system text in `_handle_chat_request` immediately after `build_system_prompt_with_tools(...)` returns (FR-005; contract I-C1). The static prefix at this point ends with the marker; no dynamic suffix is appended yet (introduced in P4).
- [ ] T028 [US5] Add a small `_hash_static_prefix(text: str) -> str` helper that hashes the input up to (and including) the boundary marker via `hashlib.sha256(...).hexdigest()`; replace the existing OTEL `kosmos.prompt.hash` emission point in `_handle_chat_request` to set the attribute from this helper (FR-007; contract I-C2). The previous hash semantics (full-system-text hash) are retired.
- [ ] T029 [P] [US5] Extend `tests/ipc/test_stdio_chat_request.py` with `test_boundary_marker_in_system_message` (I-C1) and `test_prompt_hash_matches_prefix` (I-C2) cases.
- [ ] T030 [P] [US5] Add `test_prompt_hash_byte_stable_across_turns` to `tests/ipc/test_stdio_chat_request.py` — drive two `_handle_chat_request` invocations within one session with an unchanged tool inventory and assert hash equality (SC-3; I-C5).

**Checkpoint**: P3 complete — citizen input is wrapped, BOUNDARY marker is in place, `kosmos.prompt.hash` is now meaningful. SC-3 verifiable.

---

## Phase 6: P4 — R2 (Dynamic-section assembler module)

**Goal**: Introduce `src/kosmos/llm/prompt_assembler.py` with the Pydantic-AI-style `system_prompt` decorator surface. Refactor `_handle_chat_request` to consume `PromptAssembler.build()` so the boundary marker, prefix hash, and dynamic-suffix path all live in one module instead of inline plumbing.

**Independent Test**: I-A1 (static-prefix byte stability across `dynamic_inputs`), I-A6 (build idempotent for same context), I-A7 (register dup-name handling). All P3 invariants (I-C1, I-C2, I-C5) continue to hold after refactor.

- [ ] T031 [US5] Create `src/kosmos/llm/prompt_assembler.py` containing: (a) the four Pydantic v2 frozen models `PromptSection`, `PromptAssemblyContext`, `SystemPromptManifest`, plus the `DynamicSectionFn` type alias (data-model §1, §2, §3, §6); (b) the `PromptAssembler` class with `__init__`, `register`, `build` methods; (c) the `system_prompt(assembler, name)` decorator helper; (d) a `PromptAssemblyError(ValueError)` exception class (contract `prompt-assembler.md` "Public surface" + "Error envelope"). FR-014.
- [ ] T032 [US5] Refactor `src/kosmos/ipc/stdio.py:_handle_chat_request` to instantiate `PromptAssembler` once at backend boot (alongside `_ensure_llm_client`), call `assembler.build(ctx)` per chat request, and read `manifest.static_prefix + manifest.dynamic_suffix` for the system message text and `manifest.prefix_hash` for the OTEL attribute. The inline `_DYNAMIC_BOUNDARY_MARKER` constant and `_hash_static_prefix` helper from P3 are removed; their behaviour is now centralised in `PromptAssembler.build()`.
- [ ] T033 [P] [US5] Create `tests/llm/test_prompt_assembler.py` covering all seven invariants I-A1 (static-prefix byte stability across `dynamic_inputs`), I-A2 (`prefix_hash == sha256(static_prefix)`), I-A3 (boundary marker present), I-A4 (XML tag presence), I-A5 (`None` return omitted without stray newline), I-A6 (build idempotent for same context), I-A7 (register dup-name handling) — see contract `prompt-assembler.md` "Invariants" table.
- [ ] T034 [P] [US5] Add `tui/src/__tests__/promptCacheStability.test.ts` asserting that two consecutive citizen chat requests against the assembled backend produce byte-identical `kosmos.prompt.hash` OTEL attribute values (SC-3 end-to-end coverage, complementing T030 unit-level coverage).

**Checkpoint**: P4 complete — assembler module is the single source-of-truth for static-prefix assembly; BOUNDARY marker, hash, and dynamic-suffix wiring all centralised. P3 invariants reaffirmed under the refactored code path.

---

## Phase 7: P5 — End-to-end citizen smoke + SC audits

**Goal**: Capture the five citizen smoke scenarios as text logs and run the six success-criterion audits. This phase produces the artefacts the integration PR cites and the verification grep commands the spec lists.

**Independent Test**: SC-1 (≥ 3 of 5 trigger tool), SC-3 (hash byte-stable), SC-4 (zero dev-context grep matches), SC-5 (test parity), SC-6 (zero new runtime deps).

- [ ] T035 Create `specs/2152-system-prompt-redesign/scripts/run_smoke.sh` — an `expect`-driven harness that launches `bun run tui` and feeds each of the five citizen scenarios (Story 1: "강남역 어디야?"; Story 2: "오늘 서울 날씨 알려줘"; Emergency: "근처 응급실 알려줘"; KOROAD: "어린이 보호구역 사고 다발"; Greeting: "안녕") in sequence, capturing each session as `smoke-scenario-{1..5}-*.txt` and writing the aggregated transcript to `smoke.txt` (memory `feedback_vhs_tui_smoke`).
- [ ] T036 Run `scripts/run_smoke.sh` against the assembled backend; commit `smoke.txt` and the five per-scenario logs into `specs/2152-system-prompt-redesign/`.
- [ ] T037 SC-1 audit — run `grep -c 'tool_use\|tool_call' specs/2152-system-prompt-redesign/smoke.txt` and confirm value is ≥ 3. Record the audit command + result in `specs/2152-system-prompt-redesign/notes-sc-audits.md` (new file).
- [ ] T038 SC-3 audit — extract `kosmos.prompt.hash` from the OTEL trace captured during T036 (Spec 028 OTLP collector if running, or by adding a temporary debug-print only inside the smoke harness wrapper) and assert turn-1 == turn-2 in the `notes-sc-audits.md`.
- [ ] T039 SC-4 audit — run `git grep -E 'getSystemContext|appendSystemContext|prependUserContext|getUserContext' tui/src/ | grep -v __tests__ | grep -v _cc_reference` and confirm zero matches. Run a second grep for `gitStatus|/.* directory|cwd` over the chat-request emit codepath imports. Record both in `notes-sc-audits.md`.
- [ ] T040 SC-5 audit — run `bun test --bail=false` and `uv run pytest -q` on the branch; confirm pass counts ≥ baseline captured in T002. Record diff in `notes-sc-audits.md`.
- [ ] T041 SC-6 audit — run `git diff main -- pyproject.toml package.json tui/package.json` and confirm zero net additions to any dependency block. Record output in `notes-sc-audits.md`.

**Checkpoint**: P5 complete — all six success criteria evidenced by committed audit notes + smoke logs. The PR body cites `notes-sc-audits.md`.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation closure and PR readiness. No code changes here.

- [ ] T042 [P] Update `MEMORY.md` with a new entry pointing at this Epic's research artefact closure (one-line index entry; do NOT hand-edit MEMORY content per CLAUDE.md note about auto-maintenance — instead, save new memory file via the agent's auto-memory system noting the Epic completion if and only if a future-relevant insight emerged during implementation).
- [ ] T043 [P] If P3 or P4 added any developer-facing behaviour worth documenting (e.g., a new `KOSMOS_*` env var, a new prompt section), add a short note to `docs/conventions.md` or open a doc-only follow-up; otherwise mark this task as a no-op and move on.
- [ ] T044 Open the integrated PR: `gh pr create` with title `feat(2152): system prompt redesign — XML sections + boundary marker + dev-context excision + per-tool triggers`, body lists the six SC audit results from `notes-sc-audits.md`, footer is `Closes #2152` only (memory `feedback_pr_closing_refs`).
- [ ] T045 Monitor CI to completion (`gh pr checks --watch --interval 10`) and process Codex inline review comments via `gh api repos/umyunsang/KOSMOS/pulls/<N>/comments --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'` (memory `feedback_codex_reviewer`). Apply or reply-defer each P1/P2/P3 comment.
- [ ] T046 Verify Copilot review gate transitions to `completed` after every push (memory `feedback_copilot_gate_race`); if stuck `in_progress` 2+ minutes, re-request via GraphQL `requestReviewsByLogin`. Final fallback: ask user to add `copilot-review-bypass` label.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** → no dependencies; can start immediately.
- **Phase 2 Foundational** → depends on Phase 1.
- **Phase 3 P1 R1+R6** → depends on Phase 2. R1 prompt rewrite (T006/T007) blocks T008; T009 blocks T010; T010 blocks T011; T012-T015 are parallel-safe within R6 once T009 is in (they all touch separate adapter files).
- **Phase 4 P2 R5** → can start in parallel with Phase 3 (different files, different domains). T016-T020 are sequential per file, but T016 vs T017 vs T018 vs T019 vs T020 are independent (different files) — fine to parallelise.
- **Phase 5 P3 R3+R4** → depends on Phase 3 (R6 emission must be in place so the assembled prompt is what the test expects) and Phase 4 (excision must be done so the smoke run does not regenerate dev-context noise).
- **Phase 6 P4 R2** → depends on Phase 5 (refactors P3's inline plumbing into the assembler module).
- **Phase 7 P5 E2E + audits** → depends on Phase 6 (the assembled backend must be the production code path for the smoke run to be meaningful).
- **Phase 8 Polish + PR** → depends on Phase 7.

### User-Story Coverage

- **US1** (location query → tool) — covered by P1 R6 (trigger phrases for `resolve_location` + `lookup`) and verified at SC-1 in P5.
- **US2** (weather query → tool) — covered by P1 R6 (trigger phrases for KMA adapters) and verified at SC-1 in P5.
- **US3** (no dev-context leak) — covered by P2 R5 and verified at SC-4 in P5.
- **US4** (prompt-injection wrap) — covered by P3 R3 and verified by I-C3/I-C4/I-C6 unit tests.
- **US5** (cache stable) — covered by P3 R4 inline plumbing then P4 R2 module refactor; verified at SC-3 in P5.
- **US6** (Korean + citation) — covered by P1 R1 prompt rewrite; verified by smoke transcript inspection in P5.

### Parallel Opportunities

- T002, T003 are parallel-safe within Phase 1.
- T012, T013, T014, T015 are parallel-safe within R6 (different adapter files).
- T016, T017, T018, T019, T020 are parallel-safe within R5 (different TUI files).
- T021, T022, T023 are parallel-safe (audit + tests, different files).
- T026, T029, T030 are parallel-safe (test extensions on the same file but distinct cases — collapse into a single PR commit).
- T033, T034 are parallel-safe (Python tests vs TUI tests, different toolchains).
- T037 through T041 are sequential **only** because they all read from the same `notes-sc-audits.md`; they could be parallelised by writing one section per audit and merging.

---

## Implementation Strategy

### MVP gate: end of P3

After P3 ships, the citizen chat path emits a wrapped `<citizen_request>`, the system prompt has XML-tagged sections plus per-tool trigger phrases, and the developer-context leak is closed. SC-1, SC-2, SC-4 are verifiable at this point — that is enough to demonstrate the regression closure. P4 + P5 are the structural polish (assembler module + audited evidence) that ship in the same PR.

### Incremental within-Epic delivery

Within this single integrated PR (memory `feedback_integrated_pr_only`):

1. P1 R1+R6 → static prompt + tool inventory upgraded. Internal milestone.
2. P2 R5 → developer context excised. Internal milestone.
3. P3 R3+R4 → wrap + boundary inline. **MVP gate** — SC-1/2/4 measurable.
4. P4 R2 → assembler module refactor.
5. P5 → smoke + audits → PR body assembly.

Each phase is committed locally (memory `feedback_integrated_pr_only` says one PR — but multiple commits inside that PR are encouraged for review-grain).

### Parallel-team strategy (single contributor in this Epic)

This Epic is being executed by one contributor; the [P] markers indicate where future contributors could parallelise but are not required. Sequential execution by phase remains the recommended path.

---

## Notes

- Total task count: **46** (T001..T046). Well under the 90-task sub-issue cap (memory `feedback_subissue_100_cap`); the remaining 44 slots reserve room for `[Deferred]` placeholders generated by `/speckit-taskstoissues` for the four Deferred to Future Work entries in `spec.md`, plus mid-cycle additions.
- Every code task names (a) the contract invariant (I-Ax / I-Bx / I-Cx) or spec FR/SC it satisfies, (b) the source-file path it touches, and (c) the test file that asserts the change.
- `[P]` is used liberally because most tasks touch independent files; cohesion-merge has already been applied (e.g., `wrap_citizen_request` create + integrate are two tasks because they live in different files; the four I-B test cases collapse into one extension task on `test_system_prompt_builder.py`).
- Commit cadence: one commit per task, conventional-commit message format, no `Co-Authored-By` (memory `feedback_co_author`). Commit body cites `Refs #2152`.
- Memory references applied throughout: `feedback_check_references_first`, `feedback_no_stubs_remove_or_migrate`, `feedback_vhs_tui_smoke`, `feedback_integrated_pr_only`, `feedback_co_author`, `feedback_pr_closing_refs`, `feedback_codex_reviewer`, `feedback_copilot_gate_race`, `feedback_subissue_100_cap`.
- The four `Deferred to Future Work` entries from `spec.md` will be materialised as placeholder issues by `/speckit-taskstoissues`; this `tasks.md` does NOT include any task for them.
