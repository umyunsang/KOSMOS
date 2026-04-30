---
description: "Task list for Spec 2521 — LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration"
---

# Tasks: LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration

**Input**: Design documents from `/specs/2521-llm-swap-cc-rebuild/`
**Prerequisites**: spec.md ✓, plan.md ✓, research.md ✓, data-model.md ✓, contracts/parity-audit-cli.md ✓, parity-matrix.md ✓

**Organization**: Tasks grouped by user story (US1 / US2 / US3 / US4) per spec.md priorities (P1 / P1 / P2 / P3). Each task cites the spec FR + the parity-matrix row it touches.

## Path Conventions

- TUI: `tui/src/` (Bun + Ink + React)
- Backend: `src/kosmos/` (Python 3.12+)
- CC source-of-truth: `.references/claude-code-sourcemap/restored-src/` (read-only)
- Spec deliverables: `specs/2521-llm-swap-cc-rebuild/`
- Audit + replay scripts: `scripts/llm_swap_parity_audit.sh`, `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh`

## Task Budget

Total: 56 tasks (well under 90-cap per AGENTS.md sub-issue policy). No consolidation overruns flagged.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold audit + replay infrastructure that all user stories consume.

- [ ] T001 Capture baseline SHA-256 of `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` and `.references/claude-code-sourcemap/restored-src/src/QueryEngine.ts`; record in `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` File-level rows. Cites FR-002.
- [ ] T002 [P] Capture current KOSMOS file SHA-256 baselines (`tui/src/services/api/claude.ts`, `tui/src/ipc/llmClient.ts`, `src/kosmos/llm/client.py`, `src/kosmos/ipc/stdio.py`) into `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` File-level rows under "current state SHA". Cites FR-001.
- [ ] T003 Scaffold `scripts/llm_swap_parity_audit.sh` with arg parsing (`--json`, `--strict`, `--verbose`), POSIX shell shebang, dependency probes (`sha256sum` ↔ `shasum -a 256`, `git`, `awk`, `grep`). Output stub Markdown matching `contracts/parity-audit-cli.md`. Cites FR-004.
- [ ] T004 [P] Scaffold `tui/tests/ipc/thinking-delta-render.test.tsx` with `ink-testing-library` import + mount harness (no assertions yet). Cites FR-001 + plan § Phase 1 R-5.
- [ ] T005 [P] Scaffold `tests/llm/test_reasoning_content_forwarding.py` with `pytest-asyncio` fixture + httpx mock skeleton (no assertions yet). Cites FR-007.
- [ ] T006 [P] Scaffold `tests/integration/test_thinking_channel_e2e.py` with simulated FriendliAI SSE replay harness skeleton. Cites FR-008.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish parity-matrix baseline + retroactively label the 2026-05-01 fixes so byte-copy doesn't lose them.

⚠️ CRITICAL: No user story work can begin until this phase is complete.

- [ ] T007 Document the four 2026-05-01 fixes in `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` Swap commit log section: (a) `_ensure_tool_registry` lazy-init in `src/kosmos/ipc/stdio.py`; (b) `<turn_order>` section in `prompts/system_v1.md` + manifest SHA-256 update; (c) `enable_thinking=true` default in `src/kosmos/llm/client.py:858`; (d) partial `chunk.thinking` plumbing in `tui/src/ipc/llmClient.ts` + `tui/src/ipc/llmTypes.ts`. Each entry classified per the four SWAP categories. Cites FR-003 + FR-010 + FR-011.
- [ ] T008 Enumerate the CC stream-event channels at `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1980-2295` into `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` Stream-event channel rows. Each row has CC line, event kind/subtype, intended KOSMOS handler (TBD). Cites FR-002 + plan § Phase 0 R-2.
- [ ] T009 Update `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` Procedure-B per-handler rows with current handler positions in `tui/src/ipc/llmClient.ts`, `src/kosmos/llm/client.py`, `src/kosmos/ipc/stdio.py`. Cites FR-005.

**Checkpoint**: Phase 1 + 2 complete; parity-matrix has full skeleton + retro-labeled 2026-05-01 fixes. User story implementation can begin.

---

## Phase 3: User Story 1 — Citizen sees model reasoning live (Priority: P1) 🎯 MVP

**Goal**: Citizen running `bun run tui` sees `∴ Thinking` dim-italic lines render before/between tool calls when K-EXAONE is in `enable_thinking=true` mode.

**Independent Test**: Layer 1b ink-testing-library snapshot AND Layer 3 PTY text-log + Layer 4 vhs PNG keyframe assert `∴ Thinking` glyph rendered (per spec.md US1 acceptance scenarios).

### Procedure-A — `tui/src/services/api/claude.ts` (byte-copy + bounded swap)

- [ ] T010 [US1] Step A byte-copy: overwrite `tui/src/services/api/claude.ts` with `cp .references/claude-code-sourcemap/restored-src/src/services/api/claude.ts tui/src/services/api/claude.ts`. Verify `sha256sum tui/src/services/api/claude.ts` equals SHA-256 captured in T001. Commit subject: `byte-copy(2521): import CC services/api/claude.ts byte-identical`. Update parity-matrix File-level row with byte-copy commit SHA. Cites FR-002 + SC-002.
- [ ] T011 [US1] Step B `SWAP/llm-provider`: Replace `@anthropic-ai/sdk` imports with KOSMOS-aliased imports from `tui/src/sdk-compat.ts`. Cohesion-merged sub-checklist:
  - import `Anthropic` types → import `Kosmos*` aliases from `sdk-compat.ts`
  - replace SDK call sites (`new Anthropic({...}).messages.stream(...)`) with calls to KOSMOS IPC adapter at `tui/src/ipc/llmClient.ts`
  - update API endpoint constants (any literal `api.anthropic.com` → no-op; FriendliAI lives behind the IPC bridge)
  - add `Refs: services/api/claude.ts:<line-range>` to commit body for each diff hunk
  Commit subject: `swap/llm-provider(2521): route claude.ts through KOSMOS IPC adapter`. Update parity-matrix Swap-commit log. Cites FR-002 + FR-006.
- [ ] T012 [US1] Step B `SWAP/anti-anthropic-1p`: Remove claude.ai 1P features that were byte-copied back by T010. Cohesion-merged sub-checklist (deletions only — replacement = none):
  - remove billing telemetry / API-key-balance fetches
  - remove claude.ai OAuth login / token refresh flows
  - remove `withOAuth(...)` wrappers around request calls (replace with bare passthrough; FriendliAI uses bearer token from env, no OAuth)
  - remove claude.ai-specific analytics events
  Commit subject: `swap/anti-anthropic-1p(2521): drop claude.ai 1P billing/OAuth/sync from claude.ts`. Update parity-matrix. Cites FR-006 + Spec 1633 closure.
- [ ] T013 [US1] Step B `SWAP/identifier-rename`: Replace Claude/Anthropic/claude.ai brand tokens with KOSMOS/EXAONE/FriendliAI tokens in `tui/src/services/api/claude.ts` (citizen-visible strings only — internal type names like `Anthropic` import paths stay sdk-compat-aliased per T011). Pure rename diff. Commit subject: `swap/identifier-rename(2521): KOSMOS brand tokens in claude.ts`. Update parity-matrix. Cites FR-006.
- [ ] T014 [US1] Verify post-swap behavior: run `bun --cwd tui test tests/ipc` — existing tests stay green. Run `bun --cwd tui run typecheck` — clean. If any failure surfaces, classify root cause as either swap-scope-creep (revert + redo) or byte-copy-regressed-feature (file follow-up under FR-007). Cites SC-005.

### Procedure-B — `tui/src/ipc/llmClient.ts` (citation-required)

- [ ] T015 [P] [US1] Verify the 2026-05-01 partial `chunk.thinking` plumbing in `tui/src/ipc/llmClient.ts` is preserved across T010-T013 (claude.ts byte-copy + swaps). If T010 reintroduced an old llmClient.ts dependency, repair via `SWAP/llm-provider` follow-up commit. Cites FR-002.
- [ ] T016 [P] [US1] Add `CC reference: services/api/claude.ts:<line-range>` citation comments to every handler in `tui/src/ipc/llmClient.ts`: AssistantChunkFrame branch (text + thinking), ToolCallFrame branch (input_json_delta), ToolResultFrame branch, ErrorFrame branch, BackpressureSignalFrame branch, message_start/stop emission. Each handler must cite the closest CC analog line range. Cites FR-005 + SC-004.
- [ ] T017 [P] [US1] Add `// SKIPPED — KOSMOS-N/A: <reason>` comments in `tui/src/ipc/llmClient.ts` for each CC-stream-event channel KOSMOS does not handle: `signature_delta` (K-EXAONE doesn't emit), `citations_delta` (KOSMOS uses tool_result envelopes), `connector_text_delta` (Anthropic-only), `server_tool_use` (KOSMOS uses IPC primitive bridge). One SKIPPED comment per channel. Cites FR-002.

### Procedure-B — `src/kosmos/llm/client.py` (citation-required)

- [ ] T018 [P] [US1] Add `CC reference: services/api/claude.ts:1980-2295` citation block to `_stream_response` docstring in `src/kosmos/llm/client.py`. Document the FriendliAI OpenAI-compat → AssistantChunkFrame mapping. Cite reasoning_content branch (line 788) explicitly to `services/api/claude.ts:2148`. Cites FR-005 + FR-007.
- [ ] T019 [US1] Implement `tests/llm/test_reasoning_content_forwarding.py` (scaffolded T005): mock FriendliAI SSE with `delta.reasoning_content` payload; assert `_stream_response` yields `StreamEvent(type="thinking_delta", thinking=<text>)`. Cites FR-007 + SC-007.

### Procedure-B — `src/kosmos/ipc/stdio.py` (citation-required)

- [ ] T020 [P] [US1] Add `CC reference: QueryEngine.ts (whole) + query.ts:120-410` citation block to `_handle_chat_request` in `src/kosmos/ipc/stdio.py`. Document the per-turn agentic-loop pattern: fresh `message_id`, structured `tool_calls` dispatch, `role="tool"` injection, max_turns termination. Cites FR-005 + FR-008.
- [ ] T021 [P] [US1] Add `CC reference: services/tools/toolOrchestration.ts:19-72 (runTools)` citation to `_dispatch_primitive` in `src/kosmos/ipc/stdio.py`. Note the partition policy divergence (KOSMOS = all-parallel via `asyncio.gather`; CC = partitioned by `concurrencySafe`). Cites FR-005 + Deferred Item "partitioning".
- [ ] T022 [P] [US1] Add `CC reference: (no direct CC analog — KOSMOS-only IPC adaptation)` annotation to `_ensure_tool_registry` in `src/kosmos/ipc/stdio.py`. Document the `SWAP/llm-provider` justification: CC assumes registry populated at SDK construction; KOSMOS populates lazily on first IPC dispatch via `register_all_tools`. Cites FR-005.

### End-to-end thinking channel test

- [ ] T023 [US1] Implement `tests/integration/test_thinking_channel_e2e.py` (scaffolded T006): drive a full chain — synthetic FriendliAI SSE → `LLMClient._stream_response` → `AssistantChunkFrame.thinking` → IPC bridge → `tui/src/ipc/llmClient.ts` `content_block_delta { type: 'thinking_delta' }` → assistant message `content[]` contains `{ type: 'thinking', thinking: <concatenated text> }`. Cites FR-008 + SC-007.

### Layer 1b Ink-testing-library + Layer 4 vhs verification

- [ ] T024 [US1] Implement `tui/tests/ipc/thinking-delta-render.test.tsx` (scaffolded T004): mount `Message` with thinking content block; assert `frames.at(-1)` contains `∴ Thinking` glyph (collapsed mode) AND `Box paddingLeft={2}` Markdown rendering (verbose mode). Cites FR-001 + SC-001.
- [ ] T025 [US1] Run Layer 4 vhs scenario: `vhs specs/2521-llm-swap-cc-rebuild/scripts/smoke-thinking-render.tape` (the .tape file authored in this task). Capture 3 PNG keyframes (boot / thinking-visible / final-result). Lead Opus visually verifies via Read tool. Cites SC-001.

**Checkpoint US1**: Citizen-visible thinking rendering deliverable complete. MVP ready to ship if scope tightens.

---

## Phase 4: User Story 2 — Every diff documented and justified (Priority: P1)

**Goal**: `scripts/llm_swap_parity_audit.sh` enumerates every diff hunk between rebuilt files and CC source; each hunk traces to a `swap/<category>:` commit OR explicit skip comment.

**Independent Test**: Audit script exits 0 on rebuilt branch; introducing an unjustified diff makes it exit 1 with diagnostic.

- [ ] T026 [US2] Implement `scripts/llm_swap_parity_audit.sh` byte-copy SHA verification (Procedure-A files): parse parity-matrix Step-A commit SHAs; for each, run `git show <byte-copy-sha>:<kosmos-path> | sha256sum`; compare with CC source SHA. Mismatch → mark `byte_copy_sha_match=false` + add to outcome. Cites FR-004.
- [ ] T027 [US2] Implement audit script swap-commit category verification: walk `git log --oneline 2521-llm-swap-cc-rebuild`; classify each commit by subject prefix (`byte-copy`, `swap/llm-provider`, `swap/tool-domain`, `swap/anti-anthropic-1p`, `swap/identifier-rename`); reject any subject not matching the allowed set. Cites FR-004.
- [ ] T028 [US2] Implement audit script unjustified-hunk detection: compute `git diff <byte-copy-sha>..HEAD -- <kosmos-path>` per Procedure-A file; for each hunk, find the SwapCommit that introduced it (via `git log -p --follow`). Hunks not owned by any SwapCommit → add to `unjustified_hunks`. Cites FR-004.
- [ ] T029 [US2] Implement audit script Procedure-B citation verification: for each of `tui/src/ipc/llmClient.ts`, `src/kosmos/llm/client.py`, `src/kosmos/ipc/stdio.py`, grep for functions/methods (regex per language); for each, verify presence of `CC reference:\s+\S+:\d+(-\d+)?` pattern within the function body or docstring. Missing → add to `missing_cc_citations`. Cites FR-005.
- [ ] T030 [US2] Implement audit script CC stream-event channel enumeration: parse `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1980-2295` via `awk`/`grep` extracting `case '...'` blocks; for each channel, verify either KOSMOS handler OR `// SKIPPED — KOSMOS-N/A:` comment exists. Cites FR-002.
- [ ] T031 [US2] Implement audit script `--json` output mode matching `contracts/parity-audit-cli.md` schema. Cites FR-004.
- [ ] T032 [US2] Implement audit script `--strict` flag (treat warnings as failures) and `--verbose` flag (print classification details). Cites FR-004.
- [ ] T033 [US2] Add `scripts/llm_swap_parity_audit.sh` invocation to `.github/workflows/` as a CI step that runs on PRs touching the 4 in-scope files OR `parity-matrix.md` OR `.references/claude-code-sourcemap/restored-src/`. Cites FR-009 + SC-003.
- [ ] T034 [US2] Author negative tests for the audit script: introduce a deliberate unjustified hunk, assert exit 1; revert + introduce a missing citation, assert exit 1; revert + introduce a malformed swap commit subject, assert exit 1. Tests live as a shell test file `scripts/test_llm_swap_parity_audit.sh`. Cites SC-003.

**Checkpoint US2**: Audit infrastructure operational. Future swap-surface modifications require labeled commits — silent drops structurally impossible.

---

## Phase 5: User Story 3 — Rebuild procedure reproducibility (Priority: P2)

**Goal**: `replay_rebuild.sh` on clean main reproduces the rebuild branch's working tree byte-for-byte.

**Independent Test**: Worktree on clean main + replay script → `git diff 2521-llm-swap-cc-rebuild` is empty.

- [ ] T035 [US3] Replace `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh` stub with full implementation: parse parity-matrix Swap-commit log; for each Procedure-A file, run byte-copy step (cp + commit); cherry-pick each swap commit by SHA in original order; verify post-replay `git diff` empty. Cites FR-013 + SC-011.
- [ ] T036 [US3] Add replay-script self-test: in CI (or pre-merge gate), run replay on a scratch worktree; compare resulting commit SHAs (or tree hashes) with the rebuild branch. Cites SC-011.
- [ ] T037 [US3] Document replay refresh handling in `specs/2521-llm-swap-cc-rebuild/quickstart.md` § Troubleshooting: when CC source-of-truth refreshes, what to do. Cites FR-013 + spec § Deferred Items "CC source-of-truth refresh handling".

**Checkpoint US3**: Rebuild is reproducible. Procedure decays into "audit-and-patch" only if replay script breaks (which the self-test catches).

---

## Phase 6: User Story 4 — Spec 1633 cleanup-needed within scope closed (Priority: P3)

**Goal**: All Spec 2292 `cleanup-needed` entries that fall within the 4 in-scope files resolve via byte-copy revert OR labeled swap OR delete.

**Independent Test**: `cleanup-needed` count for the 4 in-scope files = 0 in updated `specs/2292-cc-parity-audit/cc-parity-audit.md`.

- [ ] T038 [P] [US4] Read `specs/2292-cc-parity-audit/cc-parity-audit.md`; extract every `cleanup-needed` entry whose `kosmos_path` matches one of the 4 in-scope files. Record list in `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` "Cleanup-needed inflight" section. Cites FR-007 + SC-006.
- [ ] T039 [US4] For each in-scope cleanup-needed entry, classify as: (a) `byte-copy reverted it already` (no further action), (b) `requires labeled swap` (add a swap commit per FR-003), or (c) `requires deletion under SWAP/anti-anthropic-1p`. Apply remediation. Cites FR-007 + SC-006.
- [ ] T040 [US4] Update `specs/2292-cc-parity-audit/cc-parity-audit.md` modified-files table: change `Cleanup-needed` → `Legitimate` for each resolved row; add citation to the swap commit that resolved it. Cites SC-006.
- [ ] T041 [P] [US4] For any cleanup-needed entry that does NOT fall in the 4 in-scope files, add a NEEDS-TRACKING follow-up issue stub in spec § Deferred to Future Work. Cites Constitution § VI.

**Checkpoint US4**: Spec 1633 closure for the LLM swap surface complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification + parity-matrix population + CI check + smoke artifacts.

- [ ] T042 Populate `specs/2521-llm-swap-cc-rebuild/parity-matrix.md` Stream-event channel rows fully — every (TBD) replaced with concrete KOSMOS handler path (file:line) or skip reason. Verify alignment with audit-script enumeration step from T030. Cites FR-003 + SC-002.
- [ ] T043 Populate `parity-matrix.md` Procedure-B per-handler rows fully — every (TBD) replaced with verified `CC reference:` citation present in the actual handler code (cross-checked against T029 audit-script citation grep). Cites FR-005 + SC-004.
- [ ] T044 [P] Update `prompts/manifest.yaml` SHA-256 if `prompts/system_v1.md` was modified during this Epic; verify Spec 026 boot guard still passes (`uv run python -c "from kosmos.context.prompt_loader import PromptLoader; PromptLoader(...)"` succeeds). Cites FR-011 + SC-010.
- [ ] T045 [P] Run `uv run pytest` baseline tests; verify ≥1660 passed, 0 new failures. Cites SC-005.
- [ ] T046 [P] Run `bun --cwd tui test`; verify baseline green. Cites SC-005.
- [ ] T047 Run `git diff main -- pyproject.toml tui/package.json`; verify zero new dependency additions (FR-012 / AGENTS.md hard rule). Cites SC-008.
- [ ] T048 Run `scripts/llm_swap_parity_audit.sh --strict` final time; assert exit 0 with full PASS report. Capture stdout into `specs/2521-llm-swap-cc-rebuild/parity-audit-final-report.md` for PR description. Cites SC-003.
- [ ] T049 Reproduce user-reported flow regression test: `bun --cwd tui run tui` → "오늘 부산 날씨 어때?" → assert NO verbose narration in `●` content blocks before tool calls AND assert `∴ Thinking` line(s) render. Layer 3 PTY log committed to `specs/2521-llm-swap-cc-rebuild/smoke-busan-weather-pty.txt` + Layer 4 vhs PNG keyframes. Cites SC-001 + SC-006.
- [ ] T050 [P] Author PR description draft at `specs/2521-llm-swap-cc-rebuild/pr-description.md` referencing: byte-copy SHA verification, swap-commit log, parity-matrix, audit script PASS, regression test deliverables. PR body MUST include `Closes #<EPIC-NUMBER>` (EPIC issue number resolved by `/speckit-taskstoissues`). Cites Constitution § VI + AGENTS.md PR closing rule.

---

## Dependencies

```text
Phase 1 (Setup, T001-T006)
  └─> Phase 2 (Foundational, T007-T009) [parity-matrix populated]
        └─> Phase 3 US1 (T010-T025) [Procedure-A claude.ts + Procedure-B citations + thinking smoke]
              ├─> Phase 4 US2 (T026-T034) [audit script + CI]
              │     └─> Phase 5 US3 (T035-T037) [replay script]
              │           └─> Phase 7 Polish (T042-T050)
              └─> Phase 6 US4 (T038-T041) [Spec 1633 cleanup, parallel with US2/US3]
                    └─> Phase 7 Polish (T042-T050)
```

**MVP scope** (US1 only): T001-T009 + T010-T025 (~25 tasks). Delivers citizen-visible thinking rendering with retroactive labeling. Audit/replay/cleanup may be split into a follow-up PR if scope tightens (NOT a true deferral — all 7 user stories remain in this Epic per spec § Out of Scope; only PR-slicing is optional).

## Parallel Execution Examples

### Phase 1 Setup (T001-T006)
```text
T001 (parity-matrix CC SHA baseline) - solo (writes parity-matrix.md)
T002 [P] (current KOSMOS SHA baseline) - parallel with T003-T006
T003 (audit script scaffold) - solo (writes scripts/llm_swap_parity_audit.sh)
T004 [P] (ink-testing-library scaffold) - parallel
T005 [P] (pytest reasoning_content scaffold) - parallel
T006 [P] (pytest thinking_channel_e2e scaffold) - parallel
```

### Phase 3 US1 — Procedure-A swap commits (T010-T013)
```text
T010 (byte-copy) - solo (overwrites claude.ts)
T011 (SWAP/llm-provider) - sequential after T010 (modifies claude.ts)
T012 (SWAP/anti-anthropic-1p) - sequential after T011
T013 (SWAP/identifier-rename) - sequential after T012
T014 (verify post-swap) - sequential after T013
```

### Phase 3 US1 — Procedure-B citations (T015-T022)
```text
T015 [P] (llmClient.ts thinking preservation check)
T016 [P] (llmClient.ts CC citations) - parallel with T015 if different functions
T017 [P] (llmClient.ts SKIPPED comments)
T018 [P] (client.py CC citations)
T019 (client.py reasoning_content forwarding test) - sequential after T018
T020 [P] (stdio.py CC citations for _handle_chat_request)
T021 [P] (stdio.py CC citations for _dispatch_primitive)
T022 [P] (stdio.py annotation for _ensure_tool_registry)
```

### Phase 6 US4 — cleanup remediation (T038-T041)
```text
T038 [P] (extract in-scope cleanup-needed entries)
T039 (apply remediation) - sequential after T038
T040 (update Spec 2292 audit doc) - sequential after T039
T041 [P] (out-of-scope tracking issues)
```

## Implementation Strategy

**Lead Opus (this Epic)** drives the dispatch tree. Per AGENTS.md "Dispatch unit (NON-NEGOTIABLE)", each Sonnet teammate gets ≤ 5 tasks AND ≤ 10 file changes.

Suggested teammate splits (filed at /speckit-implement):
- **sonnet-foundational** (T001-T009): scaffolding, parity-matrix population, baseline SHA capture
- **sonnet-procedure-a** (T010-T014): claude.ts byte-copy + 3 swap commits + verify
- **sonnet-procedure-b-tui** (T015-T017): llmClient.ts citations + SKIPPED comments
- **sonnet-procedure-b-py** (T018-T023): client.py + stdio.py citations + tests
- **sonnet-tui-tests** (T024-T025): ink-testing-library + vhs smoke
- **sonnet-audit** (T026-T034): full parity audit script + CI
- **sonnet-replay** (T035-T037): replay script + self-test
- **sonnet-cleanup** (T038-T041): Spec 2292 closure
- **Lead Opus solo** (T042-T050): polish + PR description + final audit + commit/push/CI/Codex

**Dispatch tree** committed to `specs/2521-llm-swap-cc-rebuild/dispatch-tree.md` per AGENTS.md § Agent Teams during /speckit-implement.

## Notes

- **Task budget audit**: 50 tasks generated, well under the 90-cap. No consolidation overruns.
- **MVP delivery path**: T001-T025 = US1 = citizen-visible thinking rendering. Can ship as standalone PR if needed.
- **Constitution compliance**: every task cites at least one FR or SC. Deferred items remain in spec § Deferred (7 NEEDS TRACKING entries).
- **No new runtime deps**: T026-T034 audit script uses POSIX shell + stdlib; T024 uses existing `ink-testing-library` v4; T019/T023 use existing `pytest-asyncio` + `httpx`.
- **2026-05-01 prior fixes**: retroactively labeled in T007 per the four SWAP categories. Byte-copy of claude.ts in T010 may regress some — T014 verifies + T011-T013 reapply via labeled swap commits.
