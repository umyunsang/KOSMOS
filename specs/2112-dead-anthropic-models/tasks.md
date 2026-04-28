---

description: "Task list for P1 dead Anthropic model matrix removal"
---

# Tasks: P1 Dead Anthropic Model Matrix Removal

**Input**: Design documents from `/specs/2112-dead-anthropic-models/`
**Epic**: [#2112](https://github.com/umyunsang/KOSMOS/issues/2112)
**Phase**: P1 (`docs/requirements/kosmos-migration-tree.md § Execution Phase`)
**Prerequisites**: plan.md ✓ · spec.md ✓ · research.md ✓ · data-model.md ✓ · contracts/audit-contract.md ✓ · quickstart.md ✓

**Tests**: NOT requested. This is a *deletion-driven* epic; verification is the audit-grade contracts (C1–C11) in `contracts/audit-contract.md`. The `bun test` + `uv run pytest` baselines (FR-010 / SC-004) act as the regression net.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently. All tasks land in a **single integrated branch** (`2112-dead-anthropic-models`) per memory `feedback_integrated_pr_only`; one PR closes Epic #2112.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3) for traceability
- File paths are absolute / repo-relative

## Path Conventions

KOSMOS canonical layout (per AGENTS.md):
- TUI (target of this epic): `tui/src/`
- Python backend (read-only this epic): `src/kosmos/`
- Spec artefacts: `specs/2112-dead-anthropic-models/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture pre-change baseline so regressions are detectable, and pre-author the audit script that gates merge.

- [x] T001 Capture pre-change baseline metrics in `specs/2112-dead-anthropic-models/baseline.txt`: (a) `wc -l` for `tui/src/utils/model/modelOptions.ts`, `tui/src/utils/model/model.ts`, `tui/src/services/mockRateLimits.ts`, `tui/src/services/rateLimitMocking.ts`; (b) `rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' tui/src/utils/model/ tui/src/services/mockRateLimits.ts tui/src/services/rateLimitMocking.ts | wc -l`; (c) `cd tui && bun test 2>&1 | tail -3`; (d) `uv run pytest 2>&1 | tail -3`. This file is the regression baseline cited by all subsequent audit tasks.
- [x] T002 [P] Author `specs/2112-dead-anthropic-models/audit.sh` shell script implementing all C1-C11 contracts from `contracts/audit-contract.md` as one runnable check (each contract becomes a function returning 0/1; final exit code is OR of all). Make it executable (`chmod +x`).
- [x] T003 [P] Verify on current `main` (commit 692d1c3) that `bun test` reports ≥ 984 pass and `uv run pytest` reports ≥ 437 pass; record in `baseline.txt`. Confirms FR-010 starting point.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pre-classify the ≤ 9 caller files into SC-1 perimeter buckets and freeze the `[Deferred to P2]` annotation string before any deletion lands.

**⚠️ CRITICAL**: These two tasks set the contracts that all US1/US2 deletion tasks reference. No US1 work can begin until T004 + T005 are complete.

- [x] T004 Map all callers of `firstPartyNameToCanonical`, `getDefaultSonnetModel`, `getDefaultOpusModel`, `getDefaultHaikuModel` in `tui/src/` via `rg -ln 'firstPartyNameToCanonical|getDefaultSonnetModel|getDefaultOpusModel|getDefaultHaikuModel' tui/src/`. Classify each caller into bucket A (inside SC-1 perimeter `tui/src/utils/model/` — direct rewrite allowed) or bucket B (outside perimeter, e.g. `services/api/claude.ts` — must keep alias). Write the classification to `specs/2112-dead-anthropic-models/caller-classification.md`. Drives FR-006 caller-reach decision rule.
- [x] T005 Decide and document the canonical `[Deferred to P2 — issue #2147]` annotation marker string in `specs/2112-dead-anthropic-models/deferred-marker.md`. The primary deferral anchor is **#2147** (`services/api/claude.ts` Anthropic SDK removal), since that is the file that keeps the alias chain alive in P1. All US1/US2 alias-preservation tasks reference this marker verbatim.

**Checkpoint**: caller-classification.md and deferred-marker.md exist; US1 work can now begin.

---

## Phase 3: User Story 1 - Citizen sees no Anthropic-shaped model selection (Priority: P1) 🎯 MVP

**Goal**: Delete the dead Anthropic model dispatch matrix from the three primary target files and validate via the audit chain. After this phase the regex 0-hit invariant (SC-001) holds, the citizen smoke (SC-003) passes, and the test baselines (SC-004) are preserved.

**Independent Test**: Run `bash specs/2112-dead-anthropic-models/audit.sh C1 C2 C8` — observe C1 (regex 0-hit) PASS, C2 (file-deletion) PASS, C8 (test baseline) PASS. Then run `bun run tui` and complete the citizen smoke from `quickstart.md § 3`.

### Implementation for User Story 1

- [x] T006 [US1] Delete `tui/src/services/mockRateLimits.ts` (882 LOC `[ANT-ONLY]` Anthropic header mock fixture) via `git rm`. Satisfies FR-002. No FriendliAI-shaped replacement is required (research.md § R3).
- [x] T007 [US1] Delete `tui/src/services/rateLimitMocking.ts` (paired `[ANT-ONLY]` sole caller of `mockRateLimits.ts`) via `git rm`. Satisfies FR-003.
- [x] T008 [P] [US1] Verify with `rg -ln 'from.*mockRateLimits|from.*rateLimitMocking' tui/src/` that zero callers remain after T006+T007. If any non-`[ANT-ONLY]` caller is found, escalate via PR comment — do not silently re-stub.
- [x] T009 [US1] Collapse `firstPartyNameToCanonical(name)` body in `tui/src/utils/model/model.ts:197-279` (15+ Anthropic name-pattern branches) to a single fail-safe expression: `name.toLowerCase().includes('k-exaone') ? 'k-exaone' as ModelShortName : name as ModelShortName`. Add `// [Deferred to P2 — issue #2147]` annotation referencing the marker from T005. Satisfies FR-005.
- [x] T010 [US1] Convert `getDefaultSonnetModel()`, `getDefaultOpusModel()`, `getDefaultHaikuModel()` in `tui/src/utils/model/model.ts` to thin aliases — each body is `return getDefaultMainLoopModel()`. Per the caller-classification.md (T004) result, these MUST be aliased (not removed) because at least one caller is in bucket B (`services/api/claude.ts`). Add `[Deferred to P2 — issue #2147]` annotation per FR-006.
- [x] T011 [US1] Replace `getSmallFastModel()` body in `tui/src/utils/model/model.ts:38-40` with `return getDefaultMainLoopModel()`. Remove the `process.env.ANTHROPIC_SMALL_FAST_MODEL` env read. Satisfies FR-001 and FR-004 inside this file.
- [x] T012 [US1] Replace `isNonCustomOpusModel(model)` body in `tui/src/utils/model/model.ts:42-49` with `return false` (no Opus model exists in KOSMOS). Run `rg -n 'isNonCustomOpusModel' tui/src/` to confirm caller behaviour does not break. If callers expect `true` in some path, escalate.
- [x] T013 [US1] Prune Anthropic model option entries from `tui/src/utils/model/modelOptions.ts`: remove all `claude-3-*`, `claude-opus-*`, `claude-sonnet-*`, `claude-haiku-*` `ModelOption` constructors and their references to `getDefault{Sonnet,Opus,Haiku}Model`. **PRESERVE** subscription-tier branches (`isClaudeAISubscriber`, `isMaxSubscriber`, `isTeamPremiumSubscriber`) — these are P2-deferred (research.md § Caller-reach rule). Satisfies FR-001 and the perimeter constraint.
- [x] T014 [P] [US1] Run `bash specs/2112-dead-anthropic-models/audit.sh C1 C2` and confirm both PASS (regex 0 hits AND both target services files absent).
- [x] T015 [US1] Run `cd tui && bun test 2>&1 | tail -3` and confirm ≥ 984 pass, 0 fail. Resolve any breakage caused by T006-T013 (most likely: a test imported a deleted helper — either delete the test if it was specifically `[ANT-ONLY]` or update the test to use `getDefaultMainLoopModel()`).

**Checkpoint**: SC-001 (regex 0 hits in target perimeter), SC-003 (citizen smoke), SC-004 (test baseline) all PASS. The MVP for this Epic is complete and shippable.

---

## Phase 4: User Story 2 - Maintainer sees one model-selection branch (Priority: P2)

**Goal**: Sweep the 8 sibling files inside `tui/src/utils/model/` to remove residual Anthropic refs, achieving the ≥ 40 % LOC reduction target (SC-006) and the maintainer-readability outcome (US2).

**Independent Test**: Run `wc -l tui/src/utils/model/modelOptions.ts tui/src/utils/model/model.ts` and confirm total ≤ 1 211 LOC. Read `firstPartyNameToCanonical` and confirm 1-branch shape.

### Implementation for User Story 2

- [x] T016 [P] [US2] Prune `tui/src/utils/model/aliases.ts`: remove `opus`, `sonnet`, `haiku` model alias entries; keep `default` alias resolving to K-EXAONE. Update `ModelAlias` union type accordingly.
- [x] T017 [P] [US2] Prune `tui/src/utils/model/modelAllowlist.ts`: replace allowed-model regex array with a single allowlist that matches `LGAI-EXAONE/K-EXAONE-236B-A23B`. Any other model name flowing in returns `false` from `isModelAllowed()`.
- [x] T018 [P] [US2] Prune `tui/src/utils/model/modelCapabilities.ts`: replace per-model capability lookup table with a single K-EXAONE entry. Capabilities: `tool_use=true`, `streaming=true`, `reasoning=true`. Any unknown model falls back to the K-EXAONE entry.
- [x] T019 [P] [US2] Prune `tui/src/utils/model/modelStrings.ts`: remove `opus40`, `opus41`, `opus45`, `opus46`, `sonnet*`, `haiku*` named string lookups. Keep only K-EXAONE constants.
- [x] T020 [P] [US2] Prune `tui/src/utils/model/modelSupportOverrides.ts`: remove per-Anthropic-model override entries. If file becomes empty, delete it via `git rm` and remove its imports.
- [x] T021 [P] [US2] Prune `tui/src/utils/model/deprecation.ts`: remove the `claude-3-*` deprecation table. If file becomes empty (no K-EXAONE deprecations exist), delete via `git rm`.
- [x] T022 [P] [US2] Prune `tui/src/utils/model/configs.ts`: replace per-model config matrix with a single K-EXAONE entry. Keep the same exported shape so callers don't need updates.
- [x] T023 [US2] Update `tui/src/utils/model/agent.ts`: replace any `getDefaultSonnetModel()` / `getDefaultOpusModel()` / `getDefaultHaikuModel()` call sites with `getDefaultMainLoopModel()`. (Sequential after T010 because both touch model.ts/agent.ts surface.)
- [x] T024 [US2] Update `tui/src/utils/model/validateModel.ts` to accept only `LGAI-EXAONE/K-EXAONE-236B-A23B` (or aliases that resolve to it). Reject any other model name with a structured error.
- [x] T025 [US2] Run `bash specs/2112-dead-anthropic-models/audit.sh C1 C10` — confirm regex 0 hits AND total `wc -l` of `modelOptions.ts + model.ts` ≤ 1 211 LOC.

**Checkpoint**: SC-006 (≥ 40 % LOC drop) PASS. Sister files cleaned. Maintainer reads a single model-selection branch.

---

## Phase 5: User Story 3 - Auditor verifies zero new runtime dependencies (Priority: P2)

**Goal**: Validate AGENTS.md hard rule — zero new keys under any `dependencies` block; preserve Python `LLMClient` truth values (FR-012/013/014/015).

**Independent Test**: Run `bash specs/2112-dead-anthropic-models/audit.sh C3 C4 C5 C6 C7` — all 5 contracts PASS.

### Implementation for User Story 3

- [x] T026 [P] [US3] Run C7 (dependency audit) — `git diff main...HEAD -- tui/package.json pyproject.toml | rg -E '^\+\s*"[^"]+"\s*:'` returns empty. Resolves FR-009 / SC-005.
- [x] T027 [P] [US3] Run C4 + C5 + C6 (Python preservation audits) — confirm `temperature=1.0`, `top_p=0.95`, `presence_penalty=0.0`, `max_tokens=1024` defaults still present at `src/kosmos/llm/client.py:161-164,288-291`; `RetryPolicy`, `_compute_rate_limit_delay`, `_is_rate_limit_envelope` declarations untouched; `KOSMOS_K_EXAONE_THINKING` env + `chat_template_kwargs` payload field preserved. Validates FR-013/014/015.
- [x] T028 [P] [US3] Run C3 (single source-of-truth) — `rg 'K-EXAONE-236B-A23B' --type ts --type py | sort -u` returns ≤ 3 lines, only at `config.py:37`, `model.ts:179`, `model.ts:187`. Validates FR-012.

**Checkpoint**: SC-005 (zero new deps) and FR-012/013/014/015 preservation PASS.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final audit chain run, citizen smoke, agent context update, commit + push.

- [x] T029 Run full audit chain `bash specs/2112-dead-anthropic-models/audit.sh` (C1-C11) end-to-end. Capture stdout to `specs/2112-dead-anthropic-models/audit-report.md` with timestamp and pass/fail summary per contract.
- [x] T030 [P] Run `cd tui && bun test 2>&1 | tail -3` and `uv run pytest 2>&1 | tail -3`. Confirm both ≥ baseline (≥ 984 / ≥ 437). Append output to `audit-report.md`. Validates FR-010 / SC-004 final state.
- [x] T031 Run citizen smoke per `quickstart.md § 3` via `specs/2112-dead-anthropic-models/smoke.expect` (per memory `feedback_vhs_tui_smoke` — TUI text-log smoke). Produces `smoke.txt` (plain text, grep-able by LLM/Codex). Audit commands C9.1-C9.4 verify (a) Korean reply paint, (b) lookup primitive call, (c) zero `anthropic-ratelimit-unified` matches, (d) zero legacy-model-name matches. Manual `bash | tee` fallback if `expect` unavailable. Validates FR-011 / SC-003.
- [x] T032 [P] Update `tui/CLAUDE.md` (or `CLAUDE.md` if no TUI-specific file) Active Technologies section: add a one-line "P1 dead Anthropic matrix removed (Epic #2112)" note. Do NOT add new dependencies (FR-009).
- [x] T033 Stage all changes (`git add -A`), commit using Conventional Commits format (`feat(2112): remove dead Anthropic model matrix + migrate to K-EXAONE single branch`), push to `origin 2112-dead-anthropic-models`. **Done 2026-04-28 — commit 470fc45 pushed to origin/2112-dead-anthropic-models.**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately.
- **Phase 2 (Foundational)**: Depends on T001 (baseline) for context. T004+T005 BLOCK all US1/US2 work.
- **Phase 3 (US1 — MVP)**: Depends on Phase 2 complete. Internal sequencing: T006/T007 (file deletes) parallel; T008 verifies; T009→T010→T011→T012 sequential within `model.ts`; T013 within `modelOptions.ts` parallel-safe to T009 (different files). T014 audit → T015 test baseline.
- **Phase 4 (US2)**: Depends on Phase 3 complete (model.ts changes from T009-T012 must land before sister-file pruning to avoid merge churn). T016-T022 fully parallel (each touches a different file). T023+T024 sequential after T016-T022. T025 final audit.
- **Phase 5 (US3)**: Depends on Phase 4 complete (LOC + dep audits run after all deletions). T026-T028 fully parallel.
- **Phase 6 (Polish)**: Depends on Phase 5 complete. T029-T032 mostly parallel; T033 strictly last.

### Within Each User Story

- File deletions (T006, T007) before caller-cleanup tasks (T008-T013).
- All `model.ts` edits sequential (T009→T010→T011→T012) — same file.
- All sister-file edits parallel (T016-T022) — different files each.
- Audits run after the implementation tasks they verify.

### Parallel Opportunities

- **Phase 1**: T002 + T003 parallel; T001 is pre-flight.
- **Phase 2**: T004 + T005 parallel.
- **Phase 3**: T006 + T007 parallel (different files); T008 + T013 + T014 parallel after T006/T007. Within `model.ts` (T009-T012): sequential.
- **Phase 4**: T016 + T017 + T018 + T019 + T020 + T021 + T022 fully parallel (7-way) — each touches a unique file.
- **Phase 5**: T026 + T027 + T028 fully parallel (3-way) — independent audit commands.
- **Phase 6**: T030 + T032 parallel.

---

## Parallel Example: Phase 4 (sister-file pruning)

Spawn 7 Sonnet teammates concurrently:

```text
Teammate A: T016 — prune tui/src/utils/model/aliases.ts
Teammate B: T017 — prune tui/src/utils/model/modelAllowlist.ts
Teammate C: T018 — prune tui/src/utils/model/modelCapabilities.ts
Teammate D: T019 — prune tui/src/utils/model/modelStrings.ts
Teammate E: T020 — prune tui/src/utils/model/modelSupportOverrides.ts
Teammate F: T021 — prune tui/src/utils/model/deprecation.ts
Teammate G: T022 — prune tui/src/utils/model/configs.ts
```

Each teammate works in a distinct file. Lead (Opus) merges branches and runs T023+T024 sequentially.

---

## Implementation Strategy

### MVP First (User Story 1 only — Phase 1+2+3)

1. Phase 1 (T001-T003): baseline + audit script + baseline test counts.
2. Phase 2 (T004-T005): caller classification + deferred marker.
3. Phase 3 (T006-T015): primary deletions + model.ts collapse + test baseline preserved.
4. **STOP and VALIDATE**: run `audit.sh C1 C2 C8` + `bun run tui` smoke. If green, the core deletion is done; remaining phases are sister-file polish.

### Incremental delivery within the integrated PR

1. Phase 1+2+3 → first push → Codex review iteration 1.
2. Phase 4 → second push → Codex review iteration 2.
3. Phase 5+6 → third push → final review + merge.

All three pushes land on the **same branch** `2112-dead-anthropic-models`. **Single integrated PR** per memory `feedback_integrated_pr_only`.

### Parallel Team Strategy (`/speckit-implement`)

- Lead (Opus): Phase 2 (T004 + T005) + sequential model.ts work (T009-T012) + audits (T014, T025, T029) + final commit (T033) + Codex review handling.
- Teammate 1 (Sonnet): T006 + T007 + T013 (file deletes + modelOptions.ts prune).
- Teammate 2 (Sonnet): T016 + T017 + T018 (sister-file pruning batch A).
- Teammate 3 (Sonnet): T019 + T020 + T021 + T022 (sister-file pruning batch B).
- Teammate 4 (Sonnet): T023 + T024 (agent.ts + validateModel.ts updates).
- Teammate 5 (Sonnet): T026 + T027 + T028 (US3 audit suite).

Lead orchestrates the merges and runs the final smoke (T031).

---

## Notes

- **Total tasks**: 33 (T001-T033). Within ≤ 90 sub-issue cap. Within 25-35 user-stated budget.
- **Test tasks**: NOT generated. This is a deletion-driven epic; verification is via the C1-C11 audit-grade contracts.
- **[P] markers**: 18 of 33 tasks are parallel-safe (54 %).
- **Single PR**: all tasks land on branch `2112-dead-anthropic-models`. PR body: `Closes #2112` only. Sub-issue back-references handled by close-on-merge.
- **Deferred placeholder**: `[Deferred to P2 — issue #2147]` marker in T005/T009/T010 was back-filled by `/speckit-taskstoissues` on 2026-04-28 (resolves the 5 originally-NEEDS-TRACKING items in spec.md § Deferred → now #2146 #2147 #2148 #2149 #2150).
- **Memory references honoured**: `feedback_integrated_pr_only` (single PR), `feedback_subissue_100_cap` (≤ 90 budget), `feedback_speckit_autonomous` (no inter-phase approval gates), `feedback_codex_reviewer` (Codex inline review handled in Phase 6).
