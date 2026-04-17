---
description: "Task list for Epic #468 — Secrets & Config: Infisical OIDC + 12-Factor + KOSMOS_* registry"
---

# Tasks: Secrets & Config — Infisical OIDC + 12-Factor + KOSMOS_* Registry

**Input**: Design documents from `/specs/026-secrets-infisical-oidc/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/
**Epic**: #468 · **Branch**: `feat/468-secrets-config` · **Worktree**: `/Users/um-yunsang/KOSMOS-468`

**Tests**: TDD requested. Guard tests are written BEFORE guard implementation (spec §FR-001..008 + NFR-001, SC-006).

**Organization**: Tasks are grouped by user story (US1 = P1 guard, US2 = P2 registry+audits, US3 = P3 Infisical+CI) to enable independent implementation and MVP-first delivery.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: `[US1]` / `[US2]` / `[US3]` maps to spec.md user stories
- Every task includes exact file paths

## Path Conventions

- Single-project layout (Python package under `src/kosmos/`)
- New files in this Epic: `src/kosmos/config/`, `tests/config/`, `docs/configuration.md`, `scripts/audit-env-registry.py`, `scripts/audit-secrets.sh`
- Edits: `src/kosmos/cli/app.py`, `.env.example`, `.github/workflows/ci.yml`, `docs/design/mvp-tools.md:642`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new `kosmos.config` Python package and matching test package — minimal scaffolding that unblocks all user stories.

- [ ] T001 [P] Create `src/kosmos/config/__init__.py` (empty module init) and `tests/config/__init__.py` (empty test-package init) per plan.md §Project Structure. No logic — these are package markers so subsequent tasks can import `from kosmos.config import guard` and pytest can collect `tests/config/test_guard.py`. Confirm the two files exist with `ls -la src/kosmos/config/ tests/config/`.

**Checkpoint**: `kosmos.config` package importable; `tests/config` is a valid pytest collection root.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None beyond Phase 1. This is a configuration-only Epic — no database schema, no middleware, no authn. User-story work begins immediately after Phase 1.

*No foundational tasks. Proceed to Phase 3.*

---

## Phase 3: User Story 1 — Fail-fast startup guard (Priority: P1) 🎯 MVP

**Goal**: A contributor with an empty `.env` sees a single-line remediation message within 100 ms instead of silent tool-call degradation (regression guard for #458).

**Independent Test**: Run CLI with all required vars unset → exit 78 within 100 ms, `stderr` contains exactly one line listing every missing var + `docs/configuration.md` URL. Verified by `tests/config/test_guard.py` matrix T-G01..T-G10.

### Tests for User Story 1 (TDD — write FIRST, must FAIL before T003) ⚠️

- [ ] T002 [P] [US1] Write failing unit tests in `tests/config/test_guard.py` covering the 10-scenario matrix from `contracts/guard.md §Test matrix`:
  - T-G01: empty env → exit 78, all `required_in ⊇ {dev}` vars listed, `env=dev` tag
  - T-G02: all required set → returns `None`, no stderr
  - T-G03: `KOSMOS_ENV=prod` + `LANGFUSE_PUBLIC_KEY` missing → `LANGFUSE_PUBLIC_KEY` in list
  - T-G04: flip `KOSMOS_ENV=dev` on same missing-langfuse state → passes
  - T-G05: whitespace-only `KOSMOS_KAKAO_API_KEY` → treated as missing
  - T-G06: unknown `KOSMOS_ENV=staging` → dev fall-through (no prod-only vars demanded)
  - T-G07: 100 ms budget on all-missing path (`time.monotonic()` assertion < 0.1 s)
  - T-G08: missing-list ordering determinism (same input twice → identical message)
  - T-G09: guard does NOT write `.env` (post-call mtime unchanged if file present)
  - T-G10: guard emits no OTel spans
  
  Use `monkeypatch.setenv` / `monkeypatch.delenv` + `capsys` for stderr capture. Import from `kosmos.config.guard` (module does not yet exist — tests MUST fail at collection or first call). Stderr grammar assertions use exact string from `contracts/guard.md §stderr grammar`. No stub `guard.py` — the package init from T001 is enough for the import to fail with `AttributeError` or `ImportError`, which is the expected TDD signal.

### Implementation for User Story 1

- [ ] T003 [US1] Implement `src/kosmos/config/guard.py` per `contracts/guard.md §Public surface`. Create: `Env = Literal["dev", "ci", "prod"]`; dataclasses `RequiredVar`, `GuardDiagnostic` (both `frozen=True, slots=True`); module-level `_REQUIRED_VARS: Final[tuple[RequiredVar, ...]]` seeded from `data-model.md §Registry table` — at minimum the dev-required `KOSMOS_FRIENDLI_TOKEN`, `KOSMOS_KAKAO_API_KEY`, `KOSMOS_DATA_GO_KR_API_KEY`, plus prod-conditional `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `KOSMOS_OTEL_ENDPOINT`; functions `current_env()`, `check_required()` (pure, no I/O), `verify_startup()` (CLI wrapper; writes single stderr line via `print(..., file=sys.stderr)`, then `sys.exit(78)`). Stdlib-only: `os`, `sys`, `dataclasses`, `typing`. No logging, no OTel, no file I/O. Hard-code `doc_url = "https://github.com/umyunsang/KOSMOS/blob/main/docs/configuration.md"`. All 10 T002 tests MUST pass after this task.

- [ ] T004 [US1] Wire `verify_startup()` into `src/kosmos/cli/app.py:main()` between `load_repo_dotenv()` and `setup_tracing()` per `research.md §R1`. Import `from kosmos.config.guard import verify_startup` and insert a single call `verify_startup()` after the `.env` merge and before any tracing/LLM-client/tool-loop code. Add one integration test `tests/config/test_cli_wiring.py::test_guard_runs_before_tracing` using `monkeypatch` to assert call-order invariant (stub `setup_tracing` and `verify_startup`, assert guard invoked first). Do NOT edit `kosmos.cli.config.CLIConfig` or `_dotenv.py` — guard is additive.

**Checkpoint**: User Story 1 fully functional. `uv run pytest tests/config/` green. Empty-env CLI invocation exits 78 < 100 ms with the mandated single-line stderr message. SC-006 met.

---

## Phase 4: User Story 2 — Canonical env-var registry + drift audits (Priority: P2)

**Goal**: `docs/configuration.md` becomes the single human-facing truth for every `KOSMOS_*` variable; `scripts/audit-env-registry.py` + `scripts/audit-secrets.sh` lock the registry to the code so drift fails CI.

**Independent Test**: `uv run python scripts/audit-env-registry.py --json | jq .verdict` prints `"clean"`; `./scripts/audit-secrets.sh` exits 0 on current `ci.yml`. Adding an undocumented `KOSMOS_FOO` to any `src/*.py` flips audit to `drift`/exit 1.

### Implementation for User Story 2

*All four tasks below are parallelisable — they touch disjoint files and share only the registry schema (finalised in `data-model.md`).*

- [ ] T005 [P] [US2] Write `docs/configuration.md` per `data-model.md §Registry table schema` + `§Full registry surface`. Sections: (1) Overview — 12-Factor rationale + `KOSMOS_` prefix rule + `LANGFUSE_*` sole exception, (2) Quick reference table with exact 6-column header `| Variable | Required | Default | Range | Consumed by | Source doc |`, populated with all 17 `KOSMOS_*` vars from `spec.md §FR-012` + 2 `LANGFUSE_*` + `KOSMOS_OTEL_ENDPOINT` + the `KOSMOS_<TOOL_ID>_API_KEY` override-family row + deprecated `KOSMOS_API_KEY` row, (3) "How to add a variable" runbook (3-file change: registry + `.env.example` + consumer module; optionally `_REQUIRED_VARS` in guard) per FR-017, (4) Infisical migration operator runbook per FR-033 (project creation, OIDC identity registration, GH repo trust binding, env-slug mapping, rotation flow) — no real token values, all placeholders `<redacted>`, (5) Rollback procedure per FR-036 (`git revert <ci.yml commit>`, restore GH Secrets from Infisical export, 15-min SLO). Use `<redacted>` placeholders throughout. Anchor `#infisical-rate-limit` referenced by `contracts/ci-workflow.md §Failure handling`.

- [ ] T006 [P] [US2] Write `scripts/audit-env-registry.py` per `contracts/audit-env-registry.md`. CLI flags `--json`, `--repo-root`, `--registry`. Stdlib-only (`argparse`, `re`, `pathlib`, `json`, `sys`). Scan `src/**/*.py` + `.github/workflows/ci.yml` + `.env.example` with `_NAME_RE = re.compile(r"\bKOSMOS_[A-Z][A-Z0-9_]*\b")` + `_LANGFUSE_RE`. Parse `docs/configuration.md` table via the literal-header approach from the contract §Parsing contract. Detect 4 finding classes: `in_code_not_in_registry`, `in_registry_not_in_code`, `prefix_violations`, `override_family_unmatched`. Emit JSON matching `contracts/audit-env-registry.md §Drift report shape` (`schema_version`, `verdict`, `scan_stats`, `findings`). Exit codes 0/1/2. Add self-test fixtures `tests/scripts/test_audit_env_registry.py` covering matrix T-AR01..T-AR07 (7 cases) including performance budget (10 s wall-clock on full repo, NFR-006). Make the script executable (`chmod +x`) and add the `# SPDX-License-Identifier: Apache-2.0` header.

- [ ] T007 [P] [US2] Write `scripts/audit-secrets.sh` per `contracts/audit-secrets.md`. POSIX-portable bash (shellcheck clean, `shellcheck -x` zero warnings). `_SCANNED_FILES=('.github/workflows/ci.yml')` — out-of-scope `docker.yml` / `shadow-eval.yml` / `build-manifest.yml` MUST NOT be scanned (owned by #467). Encode 6 denylist regexes from §Forbidden patterns. Allowlist `${{ secrets.GITHUB_TOKEN }}` and `${{ secrets.INFISICAL_CLIENT_ID }}` (only if no paired `INFISICAL_CLIENT_SECRET`). Suppress comment lines (`^\s*#`) and `uses:` action-reference lines. Emit stderr violations sorted by `(file, line_number)`. Exit 0/1/2. Add `tests/scripts/test_audit_secrets.sh.bats` or `.py` harness covering matrix T-AS01..T-AS08 (8 cases) using fixture workflow files. Header line: `# SPDX-License-Identifier: Apache-2.0`. Make executable (`chmod +x`).

- [ ] T008 [P] [US2] Regenerate `.env.example` (overwrite) per `spec.md §FR-018..019` + `research.md §R6`. Format: dotenv (`KOSMOS_X=<redacted>`, no `export` prefix) — matches `src/kosmos/_dotenv.py` parser. Every required + conditional-required variable from the registry (T005) MUST appear with `<redacted>` value and a single trailing comment `# consumed by <module path>`. No real secret formats (no hex-looking placeholders). Preserve file header comment block explaining `<redacted>` convention + pointer to `docs/configuration.md`. Do NOT write to `.env` (symlink — AGENTS.md hard rule + spec FR-042).

**Checkpoint**: US2 fully functional. `./scripts/audit-secrets.sh && uv run python scripts/audit-env-registry.py --json | jq -e '.verdict == "clean"'` exits 0. SC-003, SC-005, SC-007 met.

---

## Phase 5: User Story 3 — OIDC-federated CI replaces long-lived GitHub Secrets (Priority: P3)

**Goal**: No long-lived `KOSMOS_*` secret lives in `.github/workflows/ci.yml` or GitHub Settings → Secrets. Rotating any token = one-click Infisical operation, zero code change.

**Independent Test**: Grep of `ci.yml` for `tokens|api_key|secret` (excluding `infisical`) returns zero matches; rotate `KOSMOS_FRIENDLI_TOKEN` in Infisical dashboard → next CI run green with no commit (SC-001, SC-002, SC-004).

### Implementation for User Story 3

- [ ] T009 [US3] Edit `.github/workflows/ci.yml` per `contracts/ci-workflow.md`. (a) Add job-level `permissions: { id-token: write, contents: read }` to every job that needs `KOSMOS_*` secrets. (b) Insert the Infisical step from §Required workflow block: `uses: Infisical/secrets-action@v1` with `method: oidc`, `client-id: ${{ vars.INFISICAL_CLIENT_ID }}`, hard-coded `project-id: <KOSMOS project UUID>` (placeholder `<redacted>` — real UUID injected by operator during setup per T005 runbook), `env-slug: test`, `secret-path: '/'`, `export-type: env`. Step positioned BEFORE any `uv run pytest` / application-import step. (c) **FR-050 typo fix**: replace every occurrence of `KOSMOS_DATA_GO_KR_KEY` with `KOSMOS_DATA_GO_KR_API_KEY` (line 53 at time of spec; verify final location). Remove the hard-coded `test-placeholder` fallback for that variable — Infisical now injects the real test-env value. (d) Remove any remaining long-lived `${{ secrets.KOSMOS_* }}` / `${{ secrets.FRIENDLI_* }}` / `${{ secrets.LANGFUSE_* }}` references. Keep `${{ secrets.GITHUB_TOKEN }}` (short-lived, scoped) where needed. Preserve existing triggers, concurrency, and matrix config.

- [ ] T010 [US3] Wire both audit scripts into `.github/workflows/ci.yml` as pre-test gates per `contracts/ci-workflow.md §Pre-test gates`. Insert two steps BEFORE the Infisical step (they must run even if Infisical is misconfigured): (1) `- name: Secrets audit / run: ./scripts/audit-secrets.sh`, (2) `- name: Env registry drift check / run: uv run python scripts/audit-env-registry.py --json`. Non-zero exit from either step fails the job. Ensure `actions/checkout@v4` runs before these steps (scripts need repo contents) but no Python/uv setup needed for the bash script; `audit-env-registry.py` runs via `uv run` so `astral-sh/setup-uv@v3` must precede it.

**Checkpoint**: US3 fully functional. Grep gate SC-001 passes; rotation SC-002 verified via dry-run (edit Infisical → re-run CI); live suite SC-004 green. CI pre-test gates enforce FR-024, FR-025.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: One-line typo defect fix (FR-051) and end-to-end Epic validation.

- [ ] T011 [P] Fix `docs/design/mvp-tools.md:642` per `spec.md §FR-051` + Defects Fixed table. Replace the stale `KOSMOS_KAKAO_REST_KEY` reference with the canonical `KOSMOS_KAKAO_API_KEY`. Use `Grep` to verify no other `KOSMOS_KAKAO_REST_KEY` occurrence survives anywhere under `docs/` (FR-052); if any additional hits surface, include them in the same commit as a single atomic find-and-replace. Do NOT touch `docs/tool-adapters.md` unless the grep surfaces a stale hit there (per Lead constraint — typo-fix-only access to that file).

- [ ] T012 End-to-end Epic validation per `quickstart.md` + `spec.md §Success Criteria`. Execute locally and record results:
  - **SC-006**: Empty `.env` smoke — temporarily rename `.env` (it's a symlink — use `mv .env .env.tmp` NOT rewrite), invoke `uv run kosmos --help`, confirm exit 78 < 100 ms + single-line stderr matching guard grammar, restore `.env.tmp → .env`.
  - **SC-002**: Rotation dry-run — document in PR description that operator must (1) edit `KOSMOS_FRIENDLI_TOKEN` in Infisical dashboard, (2) `gh run rerun <last-CI-id>`, (3) verify green. Cannot fully automate without Infisical write access during CI.
  - **SC-004**: Live-suite via OIDC — confirm `.github/workflows/ci.yml` CI run invokes `@pytest.mark.live` tests and they pass with Infisical-injected tokens (verified post-merge; pre-merge just confirms the Infisical step is correctly positioned).
  - **SC-001**: `grep -r "tokens\|api_key\|secret" .github/workflows/ci.yml | grep -v -i infisical` returns zero matches.
  - **SC-003**: Both audit scripts exit 0 locally. 
  - **SC-007**: Cold-read `docs/configuration.md`; confirm a new contributor can answer "what vars do I need + where do I get them" in ≤ 1 page.
  - **SC-008**: Rollback runbook reviewed — confirm `git revert` + `.env` restore path achievable in < 15 min.
  - **NFR-001**: Run `tests/config/test_guard.py::test_hundred_ms_budget` 3× to confirm stable < 100 ms.
  
  Report all results in a single section at the top of the PR body below `Closes #468`.

- [ ] T013 Final Epic completion report per `/remote-control` Lead format. Produce a single structured message covering: (a) spec/plan/tasks paths, (b) Task issue numbers created by `/speckit-taskstoissues`, (c) cross-Epic contract summary (#458 / #507 / #501 / #467 / #465), (d) registry variable count (expected ~20 rows: 17 `KOSMOS_*` + 2 `LANGFUSE_*` + override-family + deprecated), (e) manual operator-side steps the user must execute (create Infisical project, register OIDC identity, populate `INFISICAL_CLIENT_ID` as repo variable, seed Infisical `test` env with tokens), (f) deferred-items ledger status. This task closes the Epic's Spec Kit cycle; implementation proceeds via `/speckit-implement` after user approval.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — T001 runs immediately.
- **Phase 2 (Foundational)**: Empty — no blocking work.
- **Phase 3 (US1 — P1 guard, MVP)**: Depends only on Phase 1. MVP increment — ship after T004.
- **Phase 4 (US2 — P2 registry+audits)**: Depends only on Phase 1. Independent of US1 (registry schema is the only shared artefact — finalised in `data-model.md` during planning).
- **Phase 5 (US3 — P3 Infisical+CI)**: Depends on Phase 4 — audit scripts (T006, T007) must exist before CI wires them in (T010); registry runbook (T005) must document Infisical project before CI references it (T009).
- **Phase 6 (Polish)**: Depends on all prior phases for e2e validation; T011 is independent of everything.

### Task-level Dependencies

```
T001 ──┬─→ T002 ──→ T003 ──→ T004              (Group A — US1 guard, serial TDD)
       │
       ├─→ T005 ┐
       ├─→ T006 ├─→ (parallel within US2)       (Group B — US2 registry+audits, 4-way parallel)
       ├─→ T007 ┤
       └─→ T008 ┘
                 │
                 ├─→ T009 ──→ T010             (Group C — US3 Infisical+CI, serial)
                 │
                 ├─→ T011                       (Group D1 — typo fix, independent)
                 │
                 └─→ T012 ──→ T013              (Group D2 — e2e validation + report)
```

### Parallel Opportunities

- **T001** runs alone (scaffolding).
- **T002** parallel-safe once T001 done (test file is independent of other test files).
- **T005, T006, T007, T008** all four run in parallel after T001 — Group B is the widest parallel opportunity (4 Sonnet Teammates).
- **T011** runs in parallel with any other task (single-line edit to an otherwise-untouched file).
- **T012, T013** serial at the end.
- Groups A and B can run in parallel (different files, no test-collection conflicts).
- Group C waits for Group B (audit scripts must exist before CI wires them).

### MVP cut

If schedule pressure forces a scope cut, **Phase 1 + Phase 3 (T001–T004) alone** ship the full #458 regression guard (SC-006). US2 and US3 are strictly additive.

---

## Parallel Example: Phase 4 (US2 Registry + Audits)

```bash
# Launch all four US2 tasks as Sonnet Teammates after T001 completes:
Task: "T005 Write docs/configuration.md registry (6-column table, 20 rows, runbooks)"
Task: "T006 Write scripts/audit-env-registry.py + self-tests (T-AR01..07)"
Task: "T007 Write scripts/audit-secrets.sh + shellcheck-clean tests (T-AS01..08)"
Task: "T008 Regenerate .env.example from registry (<redacted> placeholders, FR-042 no .env touch)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001).
2. Complete Phase 3 (T002 → T003 → T004) — strict TDD order.
3. **STOP and VALIDATE**: `uv run pytest tests/config/` green; manual empty-env smoke test confirms SC-006.
4. Ship if registry work is deprioritised — #458 regression is guarded.

### Incremental Delivery

1. Phase 1 → Phase 3 (MVP = guard): ship + verify SC-006.
2. Phase 4 (registry + audits): ship + verify SC-003, SC-005, SC-007. Independent of future Phase 5.
3. Phase 5 (Infisical migration): ship + verify SC-001, SC-002, SC-004.
4. Phase 6 (polish + e2e): typo fix, full SC validation, completion report.

### Parallel Team Strategy

With 4 Sonnet Teammates active at `/speckit-implement`:
1. Lead completes T001 solo (scaffolding is trivial, serial).
2. Teammate A takes Group A (T002 → T003 → T004).
3. Teammates B/C/D/E take Group B (T005, T006, T007, T008) in parallel — each own distinct file(s).
4. After Group B wraps, the freest Teammate picks up Group C (T009 → T010).
5. Lead merges polish tasks (T011, T012, T013) at the end.

---

## Notes

- **[P] tasks**: different files, no dependencies on in-progress tasks.
- **[US1/US2/US3]**: maps task → spec user story for traceability.
- **TDD discipline**: T002 MUST fail before T003 begins. Enforced by running `uv run pytest tests/config/test_guard.py` between tasks and verifying `ImportError` / `AttributeError` / assertion failures.
- **Sonnet-sized**: every task ≤ `size/M`. T005 (registry doc) is the largest single-file artefact; if it exceeds `size/M` during authoring, split the runbook subsections into a sibling task — but do NOT split the 6-column table.
- **Constitution compliance**: Principles I (reference-driven), II (fail-closed guard), III (stdlib logging), V (Pydantic v2 preserved), VI (deferred items ledger) all verified during `/speckit-plan`. No new violations introduced by the task list.
- **AGENTS.md hard-rule reminders**: (1) no new dependency, (2) no `.env` write, (3) `KOSMOS_` prefix + `LANGFUSE_*` sole exception, (4) `Closes #468` only in PR body (never Task sub-issues), (5) no token values anywhere — `<redacted>` only.
- **Forbidden file surface** (must not touch): `.env` symlink, `docker/`, `.devcontainer/`, `prompts/`, `src/kosmos/safety/`, `.github/workflows/docker.yml`, `.github/workflows/shadow-eval.yml`, sibling worktrees `KOSMOS-467`, `KOSMOS-585`, `KOSMOS-466`.
- **Commit after each task or logical group**. Conventional Commits; no `--no-verify`.
- **PR close rule**: body uses `Closes #468` only. Task sub-issues closed after merge via `gh api`.
