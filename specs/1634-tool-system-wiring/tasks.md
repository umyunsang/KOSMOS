# Tasks: P3 · Tool System Wiring (4 Primitives + Python stdio MCP)

**Epic**: #1634 | **Phase**: P3 | **Feature dir**: `/Users/um-yunsang/KOSMOS/specs/1634-tool-system-wiring/`
**Inputs**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [quickstart.md](./quickstart.md) · [contracts/](./contracts/)
**Tests**: required for US3 governance gate (CI-critical); OPTIONAL for the rest (TDD per task author's judgment).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallel-safe — different files, no dependencies on incomplete tasks
- **[Story]**: which user story this task belongs to (US1 / US2 / US3 / US4) — omitted for Setup / Foundational / Polish
- Every task has an absolute file path in `/Users/um-yunsang/KOSMOS/...`

## Task count budget

**Total**: 44 tasks (≤ 90 Epic budget per `feedback_subissue_100_cap`; ≤ 80 soft warning — PASS with headroom). Count includes T010b (composite removal — FR-027) and T027a (undecided tools classification — FR-029) added during `/speckit-analyze` remediation.

---

## Phase 1: Setup

**Purpose**: Baseline verification before touching the code.

- [X] T001 Confirm `uv sync && bun install` are clean in `/Users/um-yunsang/KOSMOS/`; record `uv run pytest` + `bun test` pre-change baseline results (test count, pass/fail, duration) in a local scratch note for end-of-epic regression comparison — baseline: 3240 tests collected; `scratch/baseline-T001.md`
- [X] T002 [P] Snapshot the pre-P3 LLM-visible tool list by booting `bun run tui` once and capturing the MCP `tools/list` frame (or equivalent bridge.ts tool-registry dump) to a local scratch file for end-of-epic diff — captured as directory-tree snapshot: `scratch/tui-tools-pre-T002.txt` (46 entries); interactive boot skipped (autonomous mode)
- [X] T003 [P] `grep -rn "provider" src/kosmos/tools/**/*.py` — produce the exact 15-adapter provider→ministry migration target list and save to `/Users/um-yunsang/KOSMOS/specs/1634-tool-system-wiring/scratch-migration-list.md` (gitignored scratch file, used by T014 + T015 teammates) — captured: `scratch/migration-list-T003.txt` (17 provider= hits)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: schema + helper + routing-index substrate that every user story depends on. **No US work may start until this phase is complete.**

- [X] T004 [P] Add `Ministry` Literal alias (`KOROAD`, `KMA`, `NMC`, `HIRA`, `NFA`, `MOHW`, `MOLIT`, `MOIS`, `KEC`, `MFDS`, `GOV24`, `OTHER`) at top of `/Users/um-yunsang/KOSMOS/src/kosmos/tools/models.py` per data-model.md § 1.2
- [X] T005 [P] Add new `adapter_mode: Literal["live","mock"] = "live"` field on `GovAPITool` in `/Users/um-yunsang/KOSMOS/src/kosmos/tools/models.py` per data-model.md § 1.3; update docstring per data-model.md; no default change for any other field
- [X] T006 Rename `GovAPITool.provider: str` → `ministry: Ministry` (required, no default) in `/Users/um-yunsang/KOSMOS/src/kosmos/tools/models.py` per data-model.md § 1.1; update field docstring per data-model.md — depends on T004
- [X] T007 [P] Create `/Users/um-yunsang/KOSMOS/src/kosmos/tools/permissions.py` implementing `compute_permission_tier(auth_level, is_irreversible) -> Literal[1,2,3]` per data-model.md § 3 exactly
- [X] T008 [P] Create `/Users/um-yunsang/KOSMOS/src/kosmos/tools/routing_index.py` implementing `RoutingIndex` Pydantic model, `RoutingValidationError`, and `build_routing_index()` per data-model.md § 4 enforcing invariants 1/4/5 with the exact failure-message format in contracts/routing-consistency.md § 2
- [X] T009 [US-shared] Migrate all 14 live adapters under `/Users/um-yunsang/KOSMOS/src/kosmos/tools/{koroad,kma,hira,nmc,nfa}/*.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/ssis/welfare_eligibility_search.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/resolve_location.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/lookup.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/mvp_surface.py` (post-composite-removal count; see T010b): (a) rename `provider=...` → `ministry=...` using the closed enum (note: `ssis/welfare_eligibility_search` maps to `MOHW`), (b) populate `primitive=` per data-model.md § 1.4 table for the 10 currently-None adapters — depends on T004, T005, T006
- [X] T010 Migrate all 11 mock adapters under `/Users/um-yunsang/KOSMOS/src/kosmos/tools/mock/verify_{digital_onepass,ganpyeon_injeung,geumyung_injeungseo,gongdong_injeungseo,mobile_id,mydata}.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/mock/data_go_kr/{fines_pay,rest_pull_tick,rss_notices}.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/mock/mydata/welfare_application.py` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/mock/cbs/disaster_feed.py`: (a) rename provider→ministry, (b) add explicit `adapter_mode="mock"`, (c) confirm `primitive` already set per Spec 031 — depends on T004, T005, T006
- [X] T010b Delete the composite adapter per FR-027: `rm -rf /Users/um-yunsang/KOSMOS/src/kosmos/tools/composite/`; remove the `from kosmos.tools.composite.road_risk_score import register as reg_risk` import + its registration call from `/Users/um-yunsang/KOSMOS/src/kosmos/tools/register_all.py`; update any test fixtures under `/Users/um-yunsang/KOSMOS/tests/` that reference `road_risk_score` — depends on T009 (sequenced after live-adapter migration to avoid merge conflicts in register_all.py)
- [X] T011 Wire `/Users/um-yunsang/KOSMOS/src/kosmos/tools/register_all.py` to call `build_routing_index()` at end of registration and `raise SystemExit(78)` on `RoutingValidationError` per contracts/routing-consistency.md § 5 — depends on T008, T009, T010, T010b
- [X] T012 [P] Unit test `compute_permission_tier()` totality (every `auth_level` × `is_irreversible` combination) in `/Users/um-yunsang/KOSMOS/tests/tools/test_permissions.py` — depends on T007
- [X] T013 [P] Unit test `build_routing_index()` invariants 1/4/5 with fixture adapters (primitive=None, duplicate tool_id, unknown auth_level) in `/Users/um-yunsang/KOSMOS/tests/tools/test_routing_index.py` — depends on T008

**Checkpoint**: `uv run pytest tests/tools/test_permissions.py tests/tools/test_routing_index.py` PASSES. Full registry (`register_all.py`) boots without SystemExit(78). Foundation ready — US work may begin in parallel.

---

## Phase 3: User Story 1 — Citizen lookup end-to-end (Priority: P1) 🎯 MVP

**Goal**: A citizen asks for an emergency hospital; LLM uses `lookup` through the full MCP bridge → primitive wrapper → Python adapter stack; zero CC dev tools visible; closed auxiliary set present.

**Independent Test**: Launch `bun run tui`; ask "근처 응급실 알려줘"; verify MCP `tools/list` returns exactly the 13-tool closed set; verify `lookup(mode=search)` + `lookup(mode=fetch)` trace ends with a hospital result.

### MCP bridge (cross-cutting within US1)

- [X] T014 [US1] Create `/Users/um-yunsang/KOSMOS/src/kosmos/ipc/mcp_server.py` — stdio-MCP server stub wrapping existing `stdio.py` per contracts/mcp-bridge.md § 2 handshake + § 3 tool-call envelope + § 4 reuse contract (no re-implementation of Spec 032 concerns) — depends on T011
- [X] T015 [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/ipc/mcp.ts` — stdio-MCP client reusing `bridge.ts` for transport; implements `initialize` handshake + `tools/list` discovery + `tools/call` routing per contracts/mcp-bridge.md § 2–3 — depends on T014

### Primitive wrappers (parallel)

- [X] T016 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/primitive/lookup.ts` — dispatcher forwarding `{mode, query, primitive_filter, top_k}` (search) and `{mode, tool_id, params}` (fetch) per contracts/primitive-envelope.md § 2 via `mcp.ts` to Python `kosmos.tools.lookup`
- [X] T017 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/primitive/submit.ts` — dispatcher forwarding `{tool_id, params}` per contracts/primitive-envelope.md § 3 to `kosmos.primitives.submit` (Spec 031 existing)
- [X] T018 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/primitive/verify.ts` — dispatcher forwarding `{tool_id, params}` per contracts/primitive-envelope.md § 4 to `kosmos.primitives.verify` (Spec 031 existing)
- [X] T019 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/primitive/subscribe.ts` — dispatcher forwarding `{tool_id, params, lifetime_hint}` per contracts/primitive-envelope.md § 5 to `kosmos.primitives.subscribe` (Spec 031 existing)

### CC dev tool deletion (parallel batch)

- [~] T020 [P] [US1] Delete CC dev tool directories batch 1 (filesystem mutation tools): `rm -rf /Users/um-yunsang/KOSMOS/tui/src/tools/{BashTool,FileEditTool,FileReadTool,FileWriteTool,GlobTool,GrepTool,NotebookEditTool}` — verify with `ls`
- [~] T021 [P] [US1] Delete CC dev tool directories batch 2 (shell + mode tools): `rm -rf /Users/um-yunsang/KOSMOS/tui/src/tools/{PowerShellTool,LSPTool,REPLTool,ConfigTool,EnterWorktreeTool,ExitWorktreeTool,EnterPlanModeTool,ExitPlanModeTool}` — verify with `ls`
- [X] T022 [US1] Remove imports + references to deleted CC dev tools from `/Users/um-yunsang/KOSMOS/tui/src/tools/index.ts` (or equivalent TUI tool dispatcher init file — confirm actual path during T022) — depends on T020, T021

### Auxiliary tools — new (parallel)

- [X] T023 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/TranslateTool/` with `input_schema` (`text`, `source_lang: Lang`, `target_lang: Lang`) + `output_schema` (`text`) + bilingual search_hint per contracts/primitive-envelope.md § 6; delegates to FriendliAI EXAONE via the existing LLM call path (no new dep)
- [X] T024 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/CalculatorTool/` with restricted-grammar expression parser using stdlib `decimal`+`math` equivalents + output `{result: Decimal, kind}` per contracts/primitive-envelope.md § 6
- [X] T025 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/DateParserTool/` using stdlib `datetime`+`zoneinfo` with `Asia/Seoul` default tz + output `{iso8601, interpreted_text}` per contracts/primitive-envelope.md § 6
- [X] T026 [P] [US1] Create `/Users/um-yunsang/KOSMOS/tui/src/tools/ExportPDFTool/` using existing `pdf-to-img` WASM (UI-B B.3) + Memdir USER tier scoped output path per contracts/primitive-envelope.md § 6

### Auxiliary tool — AgentTool rewire

- [X] T027 [US1] Rewire `/Users/um-yunsang/KOSMOS/tui/src/tools/AgentTool/` as `Task` primitive backing: delete the 4 built-in agent files (`claudeCodeGuideAgent.ts`, `exploreAgent.ts`, `planAgent.ts`, `verificationAgent.ts`), remove their registrations from `built-in/` index, and update `AgentTool.tsx` to surface generic agent dispatch only

### Registry closure

- [X] T027a [US1] Resolve FR-019/FR-029 undecided tools: for each of the 13 tools (`TodoWriteTool`, `ToolSearchTool`, `AskUserQuestionTool`, `SleepTool`, `MonitorTool`, `WorkflowTool`, `ScheduleCronTool`, `Task{Create,Get,List,Stop,Update}Tool`, `Team{Create,Delete}Tool`), make a concrete per-tool decision — kept-and-rewired / deferred-to-Epic-N / deleted — and record the decision matrix in `/Users/um-yunsang/KOSMOS/specs/1634-tool-system-wiring/decisions/undecided-tools.md` (new file); for "deleted" decisions, remove the directory in this task; for "deferred" decisions, add a row to spec.md Deferred Items table with target Epic — depends on T022 (dispatcher file path known)
- [X] T028 [US1] Register the 4 new aux tools (T023–T026) + 4 primitive wrappers (T016–T019) + 5 retained CC aux tools (WebFetch, WebSearch, Brief, MCP, AgentTool-as-Task) into the TUI tool dispatcher so the MCP `tools/list` response matches the 13-tool closed set in contracts/primitive-envelope.md § 1, plus any tools kept-and-rewired from T027a — depends on T016–T019, T022, T023–T027, T027a
- [X] T029 [US1] Integration test: full `lookup` end-to-end (search then fetch) against `hira_hospital_search` with recorded fixture in `/Users/um-yunsang/KOSMOS/tests/integration/test_lookup_e2e.py` — verifies MCP handshake, tool list closure, search result shape, fetch result shape — depends on T015, T016, T028

**Checkpoint**: `bun run tui` boots, LLM receives exactly 13 tools, hospital lookup completes end-to-end. US1 is an independently shippable MVP slice.

---

## Phase 4: User Story 2 — Submit primitive + permission gauntlet (Priority: P2)

**Goal**: A citizen's `submit` call flows through the permission modal (Spec 033) and produces an audit-ledger receipt.

**Independent Test**: Trigger a mock `submit`-mode adapter (e.g., `mock/verify_digital_onepass`); permission modal appears; receipt ID is displayed; audit ledger records `primitive="submit"` + `tool_id` separately.

- [X] T030 [US2] Integration test: `submit` end-to-end with consent + receipt ID surfaced in transcript + audit ledger entry inspected in `/Users/um-yunsang/KOSMOS/tests/integration/test_submit_e2e.py` — depends on T017, T028
- [X] T031 [US2] Integration test: `submit` with denial → LLM receives structured refusal + no adapter call + no audit ledger entry in `/Users/um-yunsang/KOSMOS/tests/integration/test_submit_denial.py` — depends on T017, T028
- [X] T032 [US2] Verify audit ledger schema (Spec 024) records `primitive` and resolved adapter `tool_id` as distinct fields, not concatenated; add assertion in `/Users/um-yunsang/KOSMOS/tests/integration/test_submit_audit_shape.py` — depends on T030

**Checkpoint**: US2 shippable alongside US1 as a full citizen-consent → action → receipt flow.

---

## Phase 5: User Story 3 — Routing governance gate (Priority: P3)

**Goal**: Boot + CI fail closed if any adapter is misconfigured; CI grep guard prevents CC dev tool resurrection.

**Independent Test**: Inject an adapter with `primitive=None`; boot fails with `SystemExit(78)`; CI `test_routing_consistency.py` fails naming the offending adapter.

- [X] T033 [US3] Create `/Users/um-yunsang/KOSMOS/tests/tools/test_routing_consistency.py` covering all 6 invariants + 4 CI checks per contracts/routing-consistency.md § 2–3 **plus a composite-pattern detector per FR-028** (reject any registered adapter whose module imports another adapter's `_call`/`register` function) using the live registry + fixture-injected failures; failure-message format MUST match contract exactly — depends on T011
- [X] T034 [US3] Add CI grep guard check inside `test_routing_consistency.py` (check 8) — scans `/Users/um-yunsang/KOSMOS/src/kosmos/tools/register_all.py` + TUI tool dispatcher file (path confirmed in T022) for any of the 16 CC dev tool names listed in contracts/primitive-envelope.md § 7; fail-closed if found — depends on T022, T033
- [X] T035 [US3] Add CI tool-list closure snapshot check inside `test_routing_consistency.py` (check 7) — asserts the TUI-registered tool set equals the 13-entry closed set in contracts/primitive-envelope.md § 1; fails with diff on mismatch — depends on T028, T033

**Checkpoint**: `uv run pytest tests/tools/test_routing_consistency.py` is green and becomes the canonical governance gate for all future P4/P5 work.

---

## Phase 6: User Story 4 — Subscribe handle lifecycle (Priority: P3)

**Goal**: `subscribe` produces a session-bound handle; revocation via `/consent revoke` invalidates it.

**Independent Test**: Issue `subscribe` against a mock weather-alert adapter; handle ID surfaces in transcript + audit ledger; `/consent revoke rcpt-<id>` invalidates the handle.

- [X] T036 [US4] Integration test: `subscribe` handle creation + audit-ledger entry in `/Users/um-yunsang/KOSMOS/tests/integration/test_subscribe_e2e.py` — depends on T019, T028
- [X] T037 [US4] Integration test: `subscribe` handle revocation via `/consent revoke rcpt-<id>` + follow-up `subscribe` confirms handle invalid in `/Users/um-yunsang/KOSMOS/tests/integration/test_subscribe_revoke.py` — depends on T036

**Checkpoint**: all four primitives exercised end-to-end. P3 functionally complete.

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: full-suite verification, manual E2E per SC-007, integrated PR prep.

- [X] T038 [P] Run `uv run pytest` full suite; confirm zero regressions vs T001 baseline; record duration delta
- [~] T039 [P] Run `bun test` full suite; confirm zero regressions vs T001 baseline
- [X] T040 Verify OTEL spans per contracts/mcp-bridge.md § 4.3: `kosmos.mcp.handshake_ms`, `kosmos.mcp.tool_call_id`, `kosmos.mcp.protocol_version` attributes flow to local Langfuse (Spec 028); **additionally assert SC-004 performance budget**: `kosmos.mcp.handshake_ms < 500` on cold-start and `< 100` on warm (second consecutive boot); capture both values in the test output — add assertion in `/Users/um-yunsang/KOSMOS/tests/integration/test_mcp_otel_spans.py`
- [~] T041 Manual E2E for SC-007: launch `bun run tui`, execute the User Story 1 hospital-lookup flow end-to-end, capture the session transcript (or screenshot if terminal graphics), attach to integrated PR description per `feedback_integrated_pr_only`
- [X] T042 Prepare integrated PR from `feat/1634-tool-system-wiring`: PR body `Closes #1634` only (never sub-issues per `feedback_pr_closing_refs`); commit message follows Conventional Commits `feat(1634): ...`; no Co-Authored-By Claude footer per `feedback_co_author`; PR description cites migration tree P3 + Spec 031 + Spec 025 v6 + Spec 032

---

## Dependency Graph

```
Setup (T001–T003) ─────────────────────┐
                                        │
Foundational (T004–T013)                │
  T004 (Ministry) ─┬─→ T006 (rename)    │
  T005 (adapter_mode) ───→ T009, T010   │
  T006 ───→ T009, T010                  │
  T004 ───→ T009, T010                  │
  T007 ─→ T012 (unit test)              │
  T008 ─→ T013 (unit test)              │
  T009 + T010 + T008 ─→ T011 (wire boot) │
                                        │
US1 (T014–T029) [MVP] ──────────────────┤
  T011 ─→ T014 (MCP server)             │
  T014 ─→ T015 (MCP client)             │
  T015 + T016 + T017 + T018 + T019 ─→   │
    T028 (registry closure) ←──         │
    T020 + T021 ─→ T022                 │
    T023–T027                           │
  T028 + T015 + T016 ─→ T029            │
                                        │
US2 (T030–T032) ─→ depends on T017, T028│
US3 (T033–T035) ─→ depends on T011, T022, T028, T033
US4 (T036–T037) ─→ depends on T019, T028│
                                        │
Polish (T038–T042) ─→ all prior         │
```

**Parallel opportunities**:
- T004 [P] + T005 [P] + T007 [P] + T008 [P] run concurrently (different files, no shared state) — Foundational kick-off.
- T012 [P] + T013 [P] run concurrently after their respective helpers land.
- T016 [P] + T017 [P] + T018 [P] + T019 [P] — all four primitive wrappers in different files.
- T020 [P] + T021 [P] + T023 [P] + T024 [P] + T025 [P] + T026 [P] — deletion batches + new aux tool directories.
- T038 [P] + T039 [P] — full test-suite runs are independent.

**Sequential bottlenecks** (cannot parallelize):
- T006 (rename) blocks T009 + T010 — whole-registry migration needs the renamed field.
- T011 (wire boot) blocks everything downstream — fail-closed gate must be live before any primitive dispatch test.
- T028 (registry closure) is the fan-in point for US1 → US2 / US3 / US4.

---

## Implementation strategy

### MVP scope (ship US1 alone if crunch hits)

US1 alone delivers a citizen-visible harness — LLM sees the closed tool surface, can issue `lookup(mode=search)` + `lookup(mode=fetch)` end-to-end to Korean public APIs. This is the load-bearing deliverable of P3. US2/US3/US4 extend it but US1 on its own is a defensible ship.

### Agent Team assignment (at `/speckit-implement`)

| Track | Tasks | Teammate model |
|---|---|---|
| Python schema + foundational | T004–T013 | Backend Architect (Sonnet) |
| MCP bridge (Python + TS) | T014, T015 | Backend Architect (Sonnet) |
| Primitive wrappers | T016–T019 | Frontend Developer (Sonnet) — parallel |
| CC dev tool deletion | T020–T022 | Minimal Change Engineer (Sonnet) — parallel |
| New auxiliary tools | T023–T026 | Frontend Developer (Sonnet) — parallel |
| AgentTool rewire | T027 | Frontend Developer (Sonnet) |
| Registry closure + US1 integration | T028–T029 | Backend Architect (Sonnet) |
| US2 submit integration | T030–T032 | API Tester (Sonnet) |
| US3 governance gate | T033–T035 | API Tester (Sonnet) |
| US4 subscribe integration | T036–T037 | API Tester (Sonnet) |
| Polish + PR | T038–T042 | Lead (Opus) solo |

Opus Lead retains T042 (PR prep) and code review of the integration points (T011, T014, T028, T033) per AGENTS.md Lead/Teammate split.

### Integrated PR policy

Single PR from `feat/1634-tool-system-wiring` to `main`, body `Closes #1634` (never Task sub-issues per `feedback_pr_closing_refs`). No per-task PRs (`feedback_integrated_pr_only`). Task sub-issues close *after* PR merge via GraphQL.

---

## Validation checklist

- [x] Every task has checkbox `- [ ]`, task ID (T001–T042 + T010b + T027a = 44 total), [P] where applicable, [Story] label on US tasks, absolute file path
- [x] Total count = 44 (≤ 80 soft warning; ≤ 90 hard cap per `feedback_subissue_100_cap`)
- [x] All 4 user stories represented with independent tests
- [x] Foundational phase precedes all US phases
- [x] Parallel opportunities marked aggressively (19 [P] tasks — 43% of total)
- [x] Dependencies explicit per data-model.md + contracts/
- [x] No [NEEDS CLARIFICATION] markers in any task
- [x] Polish phase includes SC-007 manual verification + full-suite regression
- [x] Constitution § VI: no "future" / "separate epic" references outside the Deferred table (verified across all artifacts post-`/speckit-analyze` remediation)
- [x] FR-019/FR-027/FR-028/FR-029 all covered by T010b + T027a + T033 composite detector

## Notes

- T001–T003 are scratch/baseline tasks that produce local artifacts; these are not committed and do not create sub-issues.
- T009 and T010 are the largest mechanical tasks (15 + 6 file migrations). They can be further subdivided per-ministry if a teammate prefers smaller commits, but the *issue* count stays at 2 to preserve sub-issue budget.
- `[Deferred]` slot reservation: 10 slots remain in the sub-issue budget for mid-cycle additions or placeholder Tasks for the 3 `NEEDS TRACKING` items in spec.md's Deferred Items table that `/speckit-taskstoissues` will materialize.
