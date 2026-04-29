---

description: "Tasks — Epic η #2298 system prompt rewrite (infinite-spinner fix)"
---

# Tasks: System Prompt Rewrite — 4-Primitive Vocabulary + Citizen Chain Teaching

**Input**: Design documents from `/specs/2298-system-prompt-rewrite/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests required because spec.md FR-015 explicitly mandates `tests/integration/test_shadow_eval_citizen_chain_fixtures.py` and SC-002 / SC-001 require captured smoke artefacts.

**Organization**: Tasks grouped by user story (P1 / P2 / P3) per AGENTS.md. Lead Opus dispatches Sonnet teammates per task-group with ≤ 5 tasks / ≤ 10 file changes per teammate (AGENTS.md § Dispatch unit hard rule).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file + no dependencies on incomplete tasks → parallelizable
- **[Story]**: US1 (P1 modid chain), US2 (P2 5-family disambiguation), US3 (P3 lookup-only regression). Setup / Foundational / Polish: no story label
- File paths are absolute from worktree root (`/Users/um-yunsang/KOSMOS-w-2298/`)

## Path Conventions

Single-project monorepo. This Epic touches:
- `prompts/` (rewrite + manifest)
- `tests/fixtures/shadow_eval/citizen_chain/` (new fixture root)
- `tests/integration/` (new fixture loader test)
- `specs/2298-system-prompt-rewrite/` (smoke scripts + captured artefacts)

NO edits to `src/kosmos/**` or `tui/src/**` (FR-019 + AGENTS.md TUI no-change exemption).

---

## Phase 1: Setup (Pre-flight invariant verification)

**Purpose**: Confirm Epic ε infrastructure is intact before authoring the rewrite.

- [ ] T001 (#2447) Run pre-flight invariant check from `specs/2298-system-prompt-rewrite/quickstart.md § Step 1` and write the captured output to `specs/2298-system-prompt-rewrite/preflight-check.txt` (commit). The 5 checks: (a) `uv run pytest tests/integration/test_verify_module_dispatch.py -q` passes; (b) `uv run pytest tests/integration/test_e2e_citizen_taxreturn_chain.py::test_happy_chain_verify_lookup_submit -q` passes; (c) `grep -E '"(simple_auth_module|modid|kec|geumyung_module|any_id_sso)' src/kosmos/tools/registry.py | wc -l` returns 5; (d) the 11-arm AuthContext union check returns 11; (e) current `shasum -a 256 prompts/system_v1.md` matches the manifest entry. ABORT THE EPIC if any check fails — file an Epic ε regression issue and STOP.

---

## Phase 2: Foundational (Blocking prerequisites)

**Purpose**: Build the lint script, fixture schema, and test scaffold that every user story depends on.

**⚠️ CRITICAL**: No user story task may begin until Phase 2 is complete.

- [x] T002 (#2448) [P] Create `specs/2298-system-prompt-rewrite/scripts/lint-prompt.sh` (~40 LOC bash) implementing the 7 invariant checks from `contracts/system-prompt-section-grammar.md § 5` (top-level tag count = 4 each, XML well-formedness, 3 verbatim sentences, 4 nested tag presence, `digital_onepass` absence, 10 family literals presence, file size ≤ 8192 bytes). Make it executable (`chmod +x`) and exit non-zero on any violation with a descriptive message identifying the failed check.
- [x] T003 (#2449) [P] Create `tests/fixtures/shadow_eval/citizen_chain/_schema.py` (≤ 30 LOC) with the `ExpectedToolCall` and `CitizenChainFixture` Pydantic v2 models per `contracts/shadow-eval-fixture-schema.md § 2`. Use `ConfigDict(frozen=True, extra="forbid")`. Include the 5 `Literal` values for `name` and the regex pattern for `fixture_id`.
- [x] T004 (#2450) Create `tests/integration/test_shadow_eval_citizen_chain_fixtures.py` (≤ 80 LOC) per `contracts/shadow-eval-fixture-schema.md § 4` — parametrized fixture loader test that asserts each fixture loads without ValidationError, satisfies the cross-field invariants (verify ⇒ family_hint), respects the `_ACTIVE_FAMILIES` set, and asserts fixture count == 5. Test runs against the fixtures created in Phase 4 — at this stage the test file exists but the fixture dir is empty so the parametrize set is empty (test passes trivially) and `test_fixture_count_matches_epic_target` correctly fails — that's expected and documents the contract.

**Checkpoint**: Lint script runs, schema parses, test scaffolding compiles. Phase 3 may begin.

---

## Phase 3: User Story 1 — Citizen tax-return chain teaching (Priority: P1) 🎯 MVP

**Goal**: Rewrite `prompts/system_v1.md` so the LLM emits the canonical `verify(modid) → lookup(hometax_simplified) → submit(hometax_taxreturn)` chain in response to `내 종합소득세 신고해줘`. Confirm via Layer 4 vhs (visible receipt id) and Layer 2 PTY (CHECKPOINT marker) smoke.

**Independent Test**: Run the canonical Layer 4 + Layer 2 smoke against the rewritten prompt; SC-001 + SC-002 + SC-003 all pass.

### Implementation for User Story 1

- [x] T005 (#2451) [US1] Rewrite `prompts/system_v1.md` end-to-end per `contracts/system-prompt-section-grammar.md`. Preserve the 4 top-level XML tags `<role>` / `<core_rules>` / `<tool_usage>` / `<output_style>`. Inside `<tool_usage>` add 4 new nested tags in order — `<primitives>` (5-tool catalog), `<verify_families>` (10-row table per `contracts § 3.2`), `<verify_chain_pattern>` (worked example modid → hometax_simplified → hometax_taxreturn per `research.md § R-5` + `any_id_sso` exception note + no-coercion note), `<scope_grammar>` (BNF + comma-joined example). Keep the existing OPAQUE-forever fallback paragraph + `tool_calls` discipline sentence at the tail of `<tool_usage>` verbatim. Add 2 new `<core_rules>` bullets: AAL-default policy (FR-003) + `any_id_sso` exception cross-reference (FR-008). Total file size MUST stay ≤ 8 KB.
- [x] T006 (#2452) [US1] Recompute `prompts/manifest.yaml` SHA-256 entry for `system_v1` per `quickstart.md § Step 3` — `NEW_SHA="$(shasum -a 256 prompts/system_v1.md | awk '{print $1}')"` then patch via `yq -i` (or sed fallback). Confirm via assertion that the post-edit manifest entry equals the file's SHA byte-for-byte.
- [x] T007 (#2453) [US1] Run `bash specs/2298-system-prompt-rewrite/scripts/lint-prompt.sh prompts/system_v1.md` → must exit 0. If any check fails, iterate on T005 until all 7 invariants pass. Commit only after lint passes.
- [x] T008 (#2454) [US1] Run boot fail-closed verification: `uv run python -c "from pathlib import Path; from kosmos.context.prompt_loader import PromptLoader; PromptLoader(manifest_path=Path('prompts/manifest.yaml')); print('OK')"` → must print `OK` and exit 0. If `PromptRegistryError` raises, T006 was performed incorrectly — re-run.
- [X] T009 (#2455) [US1] Author `specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect` (~80 LOC) per `contracts/smoke-checkpoint-protocol.md § 1`. Spawns `bun run tui`, asserts `KOSMOS` banner, sends the citizen prompt, polls assistant_chunk frames for the receipt regex, emits `CHECKPOINTreceipt token observed\n` exactly once on first match, double-Ctrl-C exit. Tee output to `specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt`.
- [X] T010 (#2456) [US1] Author `specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape` (~30 LOC) per `contracts/smoke-checkpoint-protocol.md § 2`. `Output … .gif` directive, 3 `Screenshot` directives at boot+branding / input-accepted / post-submit-response stages, Sleep 12s before keyframe 3 (extend to 18s if LLM is slow in CI), final double Ctrl+C cleanup.
- [ ] T011 (#2457) [US1] Capture both smokes: run `expect specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect > specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt 2>&1` AND `vhs specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape`. Verify all 5 artefacts created (1 PTY .txt, 3 PNG keyframes, 1 .gif). Verify `grep -F 'CHECKPOINTreceipt token observed' specs/.../smoke-citizen-taxreturn-pty.txt` returns exactly 1 line (SC-002).
- [ ] T012 (#2458) [US1] **Lead Opus visual verification** — Read tool inspection of all 3 keyframe PNGs. Keyframe 1 must show `KOSMOS` banner; keyframe 2 must show the citizen Korean prompt in the input field; keyframe 3 MUST show text matching `접수번호[:\s]+hometax-2026-\d{2}-\d{2}-RX-[A-Z0-9]{5}` (SC-001). If keyframe 3 fails, increase the vhs Sleep duration (T010) and re-capture (T011). Document the verification result in a `specs/2298-system-prompt-rewrite/visual-verification.md` (which keyframe shows what + Lead Opus signature).

**Checkpoint**: At this point, US1 is fully functional. The infinite-spinner gate is closed. SC-001 + SC-002 + SC-003 + SC-005 + SC-008 PASS.

---

## Phase 4: User Story 2 — 5-Family Disambiguation (Priority: P2)

**Goal**: Add 5 shadow-eval fixtures so the LLM is verified to pick the correct `family_hint` for citizen prompts mapping to `simple_auth_module`, `modid`, `kec`, `geumyung_module`, and `any_id_sso`. The shadow-eval workflow runs and reports ≥ 80 % shadow-environment pass rate (SC-004).

**Independent Test**: Run `uv run pytest tests/integration/test_shadow_eval_citizen_chain_fixtures.py -q` and confirm 6 tests pass (5 parametrized + count check). Then push to a draft PR and confirm the `.github/workflows/shadow-eval.yml` run reports both `main` + `shadow` environments and the diff satisfies SC-004.

### Implementation for User Story 2

- [X] T013 (#2459) [P] [US2] Create `tests/fixtures/shadow_eval/citizen_chain/modid.json` per `contracts/shadow-eval-fixture-schema.md § 3.1`. fixture_id `modid_taxreturn_canonical`, citizen_prompt `내 종합소득세 신고해줘`, expected verify call with `family_hint=modid`, expected_family_hint `modid`, notes referencing the 2-scope `scope_list` requirement.
- [X] T014 (#2460) [P] [US2] Create `tests/fixtures/shadow_eval/citizen_chain/simple_auth_module.json` per `contracts/shadow-eval-fixture-schema.md § 3.2`. fixture_id `simple_auth_gov24_minwon`, citizen_prompt `정부24 민원 하나 신청해줘`, expected verify call with `family_hint=simple_auth_module`. Notes explicitly call out the AAL2-vs-AAL3 disambiguation against `modid`.
- [X] T015 (#2461) [P] [US2] Create `tests/fixtures/shadow_eval/citizen_chain/kec.json` per `contracts § 3.3`. fixture_id `kec_corporate_registration`, citizen_prompt `사업자 등록증 발급해줘`, expected `family_hint=kec`.
- [X] T016 (#2462) [P] [US2] Create `tests/fixtures/shadow_eval/citizen_chain/geumyung_module.json` per `contracts § 3.4`. fixture_id `geumyung_credit_lookup`, citizen_prompt `내 신용정보 조회해줘`, expected `family_hint=geumyung_module`. Notes explicitly distinguish from `mydata` (broader) and `modid` (identity not finance).
- [X] T017 (#2463) [P] [US2] Create `tests/fixtures/shadow_eval/citizen_chain/any_id_sso.json` per `contracts § 3.5`. fixture_id `any_id_sso_login`, citizen_prompt `다른 정부 사이트 SSO 로그인 좀`, expected `family_hint=any_id_sso`. Notes call out the `IdentityAssertion`-only behavior + no-submit-chain rule.
- [X] T018 (#2464) [US2] Run `uv run pytest tests/integration/test_shadow_eval_citizen_chain_fixtures.py -q` (depends on T013–T017 + T003 + T004) → must report 6 tests pass (5 parametrized + 1 count check). All 5 fixtures load without ValidationError, all satisfy verify ⇒ family_hint cross-field invariant, count == 5.

**Checkpoint**: SC-004 fixture infrastructure ready. Shadow-eval workflow auto-discovers the 5 fixtures on PR push.

---

## Phase 5: User Story 3 — Lookup-only Regression (Priority: P3)

**Goal**: Verify that the rewritten prompt does NOT regress the 8 existing lookup-only fixtures (KMA × 2, HIRA × 1, NMC × 1, KOROAD × 1, MOHW × 1, location-resolve × 1, no-tool fallback × 1). The shadow-eval workflow's lookup-only pass rate must equal or exceed its `main` HEAD baseline.

**Independent Test**: Inspect the shadow-eval workflow output on the PR — `_existing_lookup_only/` fixtures must show no shadow-environment regression vs `main`.

### Implementation for User Story 3

- [X] T019 (#2465) [US3] Manual regression check — run any 2 representative lookup-only fixtures (e.g., `weather_basic.json` and `hospital_search.json`) through a local mock LLM harness if available, OR document that the regression check defers to the GitHub Actions shadow-eval workflow. Either way, write the manual-or-deferred note in `specs/2298-system-prompt-rewrite/regression-check.md` along with which 2 fixtures were sampled (or which workflow run will be the source-of-truth).
- [X] T020 (#2466) [US3] Inspect existing `specs/2112-dead-anthropic-models/smoke-scenario-{1,4,5}-*.png` keyframes via Lead Opus Read tool to confirm visual continuity — the citizen-greeting flow + lookup-result rendering should match the rewritten prompt's expected output structure (since `<output_style>` is unchanged). Document any visual differences in `regression-check.md`.

**Checkpoint**: All 3 user stories pass independently. SC-006 (lookup-only no-regression) verifiable via shadow-eval CI.

---

## Phase 6: Polish & PR Lifecycle

**Purpose**: Pytest sweep, PR creation, CI monitoring, Codex review handling.

- [ ] T021 (#2467) Run full pytest sweep: `uv run pytest --tb=no -q > /tmp/pytest-2298-final.log 2>&1; tail -10 /tmp/pytest-2298-final.log`. Must show pass count ≥ baseline from T001. No new failures introduced. The 6 new tests from Phase 2 + Phase 4 contribute to the new pass count.
- [ ] T022 (#2468) Verify zero new dependencies: `git diff main..HEAD -- pyproject.toml tui/package.json` produces no `+` lines under any `dependencies` block (SC-007).
- [ ] T023 (#2469) Verify TUI no-change: `git diff main..HEAD -- tui/src/` produces 0 lines (FR-019).
- [ ] T024 (#2470) Stage + commit all artefacts. One commit per logical group: (a) `feat(2298): rewrite system_v1 — 4-primitive vocabulary + citizen chain teaching` covers `prompts/`, `tests/fixtures/`, `tests/integration/`; (b) `docs(2298): smoke artefacts + verification notes` covers `specs/2298-system-prompt-rewrite/scripts/` + captured PNG/GIF/PTY/MD files; (c) optional separate `chore(2298): preflight check log` for the T001 captured output. Push to `origin 2298-system-prompt-rewrite`.
- [ ] T025 (#2471) Open PR with `gh pr create --title "feat(2298): system prompt rewrite — infinite-spinner fix" --body @<heredoc>` per `quickstart.md § Step 8` template. PR body MUST cite (a) all canonical references from spec.md header (FR-020); (b) all 5 verification artefacts; (c) `Closes #2298` ONLY (no Task sub-issue closes per AGENTS.md PR closing rule); (d) the 6 deferred items deliberately scoped out. Do NOT use `--draft`.
- [ ] T026 (#2472) Monitor CI to completion: `gh pr checks --watch --interval 10` until all checks `completed`. Required green: `shadow-eval` (SC-004), `prompt-manifest-integrity` (SC-003), pytest. After every push, also verify `gh pr view --json reviewDecision` reports Copilot Gate `completed` (per AGENTS.md § Copilot Review Gate); if stuck `in_progress` 2+ min, re-request Copilot review via GraphQL or instruct user to add `copilot-review-bypass` label.
- [ ] T027 (#2473) Read every Codex review comment via `gh api repos/umyunsang/KOSMOS/pulls/<N>/comments --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'`. P2 = fix immediately + push + reply. P1 (architecture mismatch) = create deferred sub-issue + back-fill spec.md `Deferred to Future Work` table + reply with the deferred issue link. Repeat the loop until Codex returns 0 outstanding P1/P2 OR all P1s have a deferred-issue ack.
- [ ] T028 (#2474) Final acceptance verification — re-run T011 + T012 (Layer 2 + Layer 4 smokes) on the PR's final HEAD AFTER all Codex fixes land. Update the PR body with the new artefact paths if they changed. Confirm SC-001 / SC-002 / SC-003 / SC-005 / SC-008 still pass on the post-Codex HEAD.

**Checkpoint**: Epic η ready for merge. SC-009 (Codex clean + Copilot completed + shadow-eval success + manifest integrity success) PASS.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (T001)**: Pre-flight — no dependencies; must run first.
- **Phase 2 (T002–T004)**: Depends on T001. T002–T003 are [P]; T004 depends on T003 (imports `_schema.py`).
- **Phase 3 (T005–T012)**: Depends on Phase 2. Internal order: T005 → T006 → T007 → T008 (sequential — same file `prompts/`); T009 + T010 [P]; T011 depends on T009 + T010; T012 depends on T011.
- **Phase 4 (T013–T018)**: Depends on Phase 2 (T003 + T004). T013–T017 all [P] (different files). T018 depends on T013–T017.
- **Phase 5 (T019–T020)**: Depends on Phase 3 completion (rewritten prompt exists). T019 + T020 are [P].
- **Phase 6 (T021–T028)**: Sequential. T021 + T022 + T023 are pre-PR checks; T024 → T025 → T026 → T027 → T028 strictly sequential (push → PR → CI → Codex → re-verify).

### User Story Dependencies

- **US1 (P1)**: Independent. Must complete before US2 + US3 because the rewritten prompt is the input both stories test against.
- **US2 (P2)**: Depends on US1's prompt rewrite (T005). Fixture authoring (T013–T017) parallel internally.
- **US3 (P3)**: Depends on US1's prompt rewrite. Independent of US2.

### Parallel Opportunities

**Within Phase 2**: T002 ∥ T003 (T004 depends on T003).

**Within Phase 3**: After T005–T008 (sequential prompt + manifest), T009 ∥ T010 (different files), then T011 depends on both.

**Within Phase 4**: T013 ∥ T014 ∥ T015 ∥ T016 ∥ T017 (5 different fixture files, all [P]) — single Sonnet teammate handles all 5 (still ≤ 5 task / ≤ 10 file rule satisfied).

**Within Phase 5**: T019 ∥ T020.

---

## Lead Opus Dispatch Tree (commit to `dispatch-tree.md`)

```text
Phase 1 Setup (T001):              Lead solo
Phase 2 Foundational (T002–T004):  sonnet-foundational    (T002 + T003 ∥, then T004)
Phase 3 US1 (T005–T012):           sonnet-us1             (T005–T008 seq, T009 ∥ T010, T011 → T012)
Phase 4 US2 (T013–T018):           sonnet-us2             (T013–T017 ∥, then T018)
Phase 5 US3 (T019–T020):           sonnet-us3             (T019 ∥ T020)  [parallel with US2]
Phase 6 Polish (T021–T028):        Lead solo (push/PR/CI/Codex sequential)
```

Sonnet teammates do code + tests + WIP commit + tasks.md `[X]`. Lead Opus owns push/PR/CI/Codex. Per AGENTS.md § Layer 2 parallelism, US2 + US3 may run concurrently after US1 completes — but US3 is small (2 tasks) so Lead may absorb it solo if a teammate slot is unavailable.

---

## Parallel Example: User Story 2

```bash
# Single sonnet-us2 teammate authors all 5 fixtures in one task-group:
Task: "Create modid.json + simple_auth_module.json + kec.json + geumyung_module.json + any_id_sso.json fixtures per contracts/shadow-eval-fixture-schema.md § 3.1–3.5; then run pytest test_shadow_eval_citizen_chain_fixtures.py and confirm 6 tests pass."
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 (T001 pre-flight — Lead solo)
2. Phase 2 (T002–T004 foundational — sonnet-foundational)
3. Phase 3 US1 (T005–T012 prompt rewrite + smoke — sonnet-us1)
4. **STOP and VALIDATE**: SC-001 + SC-002 + SC-003 PASS independently. Demo the modid chain.
5. Optionally ship as MVP if US2 + US3 are deferred.

### Incremental Delivery

After US1 lands and the infinite-spinner gate closes, US2 broadens family coverage (lower risk, additive), and US3 verifies regression. Both are post-MVP polish.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task → user story.
- Pre-commit grep suite (`lint-prompt.sh`) is mandatory before T024.
- Vhs Sleep duration in T010 may need extension; document the actual Sleep used in `visual-verification.md` (T012).
- AGENTS.md § Codex Gate: every push triggers re-review; T026 includes the 2-min wait + bypass-label fallback.
- Total task count: **28** — within the 90-task budget (62 slots headroom). No consolidation required.
- Zero source-code (`src/kosmos/**` / `tui/src/**`) edits planned. Any task that drifts into source code is a scope violation — escalate to Lead Opus.
