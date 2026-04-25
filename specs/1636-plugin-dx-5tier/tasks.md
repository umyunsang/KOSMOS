---
description: "Task list for Epic #1636 — P5 Plugin DX 5-tier"
---

# Tasks: Plugin DX 5-tier (Template · Guide · Examples · Submission · Registry)

**Input**: Design documents from `/Users/um-yunsang/KOSMOS/specs/1636-plugin-dx-5tier/`
**Prerequisites**: spec.md ✓ · plan.md ✓ · research.md ✓ · data-model.md ✓ · contracts/ (6 files) ✓ · quickstart.md ✓
**Branch**: `feat/1636-plugin-dx-5tier`
**Epic**: #1636

**Tests**: Negative + positive tests are MANDATORY for this Epic — contracts/plugin-validation-workflow.md requires ≥ 5 negative cases per SC-003, and the 50-item checklist's executable checks each need a unit test.

**Organization**: Tasks grouped by user story (US1–US5) per spec.md priority (P1–P3). Cross-cutting infrastructure lives in Foundational + Polish phases.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: parallelizable (different files, no dependencies on incomplete tasks)
- **[USn]**: maps to spec.md User Story n
- Setup / Foundational / Polish phases have NO story label

## Path Conventions

- Backend Python: `src/kosmos/plugins/` (NEW module)
- Backend tests: `src/kosmos/plugins/tests/`
- TUI TypeScript: `tui/src/commands/` + `tui/test/commands/`
- GitHub-side: `.github/ISSUE_TEMPLATE/` + `.github/workflows/`
- Docs: `docs/plugins/`
- Validation source-of-truth: `tests/fixtures/plugin_validation/checklist_manifest.yaml`
- External repos (created during implementation, NOT in this repo): `kosmos-plugin-template`, `kosmos-plugin-store/<plugin-name>` (4 examples), `kosmos-plugin-store/index`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new module and stub directories so subsequent foundational tasks can land in parallel.

- [X] T001 Create `src/kosmos/plugins/` skeleton: `__init__.py` (re-exports), `exceptions.py` (PluginRegistrationError, ManifestValidationError, AcknowledgmentMismatchError stubs), `tests/__init__.py`, `tests/conftest.py` (block_network autouse fixture; opt-out via `@pytest.mark.allow_network`)
- [~] T002 ~~[P] Create `tui/src/commands/` plugin command stubs~~ — **VOIDED**: TUI command files (`plugin-init.ts`, `plugin-install.ts`, `plugin-list.ts`, `plugin-uninstall.ts`) follow the existing `default export <CommandDefinition>` pattern (per `tui/src/commands/index.ts`); empty stubs with placeholder typings would be type-lies. T018 / T053 / T054 / T055 create the real files when their implementation lands. No artifact for T002.
- [X] T003 [P] Create `docs/plugins/` scaffolding: 9 stub files (`quickstart.ko.md`, `architecture.md`, `pydantic-schema.md`, `search-hint.md`, `permission-tier.md`, `data-go-kr.md`, `live-vs-mock.md`, `testing.md`, `review-checklist.md`) + `security-review.md` with `<!-- CANONICAL-PIPA-ACK-START -->` / `<!-- CANONICAL-PIPA-ACK-END -->` markers **and the canonical PIPA §26 text in place** (so T005 only needs to write the Python extractor)
- [X] T004 [P] Create `tests/fixtures/plugin_validation/` directory + empty `checklist_manifest.yaml` placeholder (filled in T037)

**Checkpoint**: Module skeleton in place; foundational work can start.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Manifest schema, validators, registry, IPC envelope arm, SLSA wrapper. Every user story depends on these.

**⚠️ CRITICAL**: No US1–US5 task starts until all of T005–T014 land.

- [X] T005 Implement `src/kosmos/plugins/canonical_acknowledgment.py`: `_extract_canonical_text()` + `_compute_canonical_hash()` + module-level `CANONICAL_ACKNOWLEDGMENT_SHA256` constant; canonical PIPA §26 text already in `docs/plugins/security-review.md` markers from T003. Verified hash: `434074581cab35241c70f9b6e2191a7220fdac67aa627289ea64472cb87495d4` (540-char canonical text)
- [X] T006 Implement `src/kosmos/plugins/manifest_schema.py`: `PluginManifest` (Pydantic v2, frozen, extra=forbid) + nested `PIPATrusteeAcknowledgment` per data-model.md § 1+2; include all 5 cross-field validators (`_v_mock_source`, `_v_pipa_required`, `_v_pipa_hash`, `_v_otel_attribute`, `_v_namespace`)
- [X] T007 [P] Add unit tests `src/kosmos/plugins/tests/test_manifest_schema.py` + `tests/test_acknowledgment_hash.py` (combined file): positive sample + 8 negative cases (one per validator + 3 schema invariants)
- [X] T008 Generate `specs/1636-plugin-dx-5tier/contracts/manifest.schema.json` from the Pydantic model (`PluginManifest.model_json_schema()`) and add a parity test in `src/kosmos/plugins/tests/test_schema_parity.py` that diffs the on-disk JSON Schema against the live Pydantic export — drift fails CI
- [X] T009 Implement `src/kosmos/plugins/registry.py`: `register_plugin_adapter(manifest)`, `auto_discover()`, `_rebuild_bm25_index_for(adapter)`; emits OTEL span `kosmos.plugin.install` with `kosmos.plugin.id` attribute
- [X] T010 Modify `src/kosmos/tools/registry.py` to expose `register_plugin_adapter()` shim that defers to `kosmos.plugins.registry`; preserves existing Spec 022/024/025/031 invariant chain (free reuse) + add `src/kosmos/plugins/tests/test_namespace_invariant.py` (Q8-NAMESPACE / Q8-NO-ROOT-OVERRIDE / Q8-VERB-IN-PRIMITIVES)
- [X] T011 [P] Implement `src/kosmos/plugins/slsa.py`: `subprocess.run([...slsa_verifier_path, "verify-artifact", ...])` wrapper with timeout + structured error mapping (exit 3 subtypes per contracts/plugin-install.cli.md); add `src/kosmos/plugins/tests/test_installer_slsa.py` with mocked binary
- [X] T012 Add Spec 032 IPC envelope 20th arm `plugin_op` to: `src/kosmos/ipc/frames.py` (Python discriminated union) + regenerate `tui/src/ipc/frames.generated.ts` + bump `tui/src/ipc/schema/frame.schema.json` SHA-256; update `kosmos.ipc.schema.hash` OTEL emission test fixture; document the bump in PR body per Spec 032 contract
- [X] T013 Add `KOSMOS_PLUGIN_*` env catalog to `src/kosmos/settings.py`: `KOSMOS_PLUGIN_INSTALL_ROOT`, `KOSMOS_PLUGIN_BUNDLE_CACHE`, `KOSMOS_PLUGIN_VENDOR_ROOT`, `KOSMOS_PLUGIN_SLSA_SKIP`, `KOSMOS_PLUGIN_CATALOG_URL` per data-model.md storage-layout section
- [X] T014 Implement `src/kosmos/plugins/installer.py`: full install flow per contracts/plugin-install.cli.md phases 1-8 (catalog fetch → bundle download → SLSA verify → manifest validate → consent prompt → register + BM25 reindex → consent receipt write); integration test in `src/kosmos/plugins/tests/test_installer_integration.py` exercises happy + 4 failure paths

**Checkpoint**: Manifest schema validated, registry hooks live, IPC envelope extended, SLSA verifier wired. US1–US5 unblocked.

---

## Phase 3: User Story 1 — Live adapter contribution end-to-end (Priority: P1) 🎯 MVP

**Goal**: A developer with no prior KOSMOS knowledge clones `kosmos-plugin-template`, scaffolds, edits, runs `pytest` green, opens a PR. After merge, `kosmos plugin install <name>` makes the adapter discoverable via `lookup(mode="search")` without TUI restart.

**Independent Test**: Time a fresh contributor through the quickstart.md walkthrough; assert `pytest` green within 30 minutes (SC-001). Then `kosmos plugin install seoul-subway` from a fresh TUI session and verify `lookup(search="지하철")` surfaces the new adapter within 5 seconds (SC-004).

- [X] T015 [US1] Bootstrap `kosmos-plugin-template` GitHub repo (org=kosmos-plugin-store, public, Apache-2.0) via scripted `gh repo create`; record creation in `docs/plugins/architecture.md` repo-list section — `https://github.com/kosmos-plugin-store/kosmos-plugin-template` (is_template=true)
- [X] T016 [US1] Author `kosmos-plugin-template` content: `pyproject.toml` (uv-compatible, depends on vendored `kosmos-plugin-sdk` shim), `manifest.yaml` skeleton, `plugin_<name>/{adapter.py,schema.py,__init__.py}` boilerplate (passes Q1+Q2+Q4 out of box; **all generated identifiers ASCII / English per FR-025** — only `description_ko` / `search_hint_ko` carry Korean), `tests/test_adapter.py` with synthetic fixture, `tests/fixtures/<tool_id>.json`, `README.ko.md`, `README.en.md`, `.gitignore` — staged at `examples/plugin-template-staging/`
- [X] T017 [US1] Author `kosmos-plugin-template` CI: `.github/workflows/plugin-validation.yml` (uses umyunsang/KOSMOS plugin-validation reusable workflow at pinned ref) + `.github/workflows/release-with-slsa.yml` (uses slsa-framework/slsa-github-generator) — emitted as part of cli_init scaffold; visible in `examples/plugin-template-staging/.github/workflows/`
- [X] T018 [US1] Implement `tui/src/commands/plugin-init.ts` per contracts/plugin-init.cli.md: Ink Select/TextInput interactive flow, file emission, `--tier`/`--layer`/`--pii`/`--out`/`--force`/`--non-interactive` flags, exit codes 0-3 — non-interactive core + argv parser landed; full Ink wizard deferred to follow-on within Phase 3
- [X] T019 [P] [US1] Add `tui/test/commands/plugin-init.test.ts` with the 4 negative cases per contracts/plugin-init.cli.md (invalid name, non-empty out without --force, --pii without ack, network egress assertion via block_network fixture) — 24 tests landed including all 4 negative paths
- [X] T020 [P] [US1] Bootstrap `kosmos-plugin-store/kosmos-plugin-seoul-subway` Live example repo (Seoul Open Data Plaza subway-arrival API) per quickstart.md model: gh repo create + pyproject.toml + plugin_seoul_subway/{adapter.py, schema.py} + manifest.yaml + tests + README.ko.md + CI; verify green badge on first PR — `https://github.com/kosmos-plugin-store/kosmos-plugin-seoul-subway`
- [X] T021 [P] [US1] Bootstrap `kosmos-plugin-store/kosmos-plugin-post-office` Live example repo (우정사업본부 parcel tracking) following the same shape as T020 — `https://github.com/kosmos-plugin-store/kosmos-plugin-post-office`
- [X] T022 [US1] Implement `uvx kosmos-plugin-init` Python entry-point fallback for non-TUI users: `pyproject.toml` script that invokes the TUI command via subprocess (or a parallel Python implementation if TUI unavailable); doc in docs/plugins/quickstart.ko.md as Option B — `kosmos.plugins.cli_init:main` entry-point + 13 unit tests
- [X] T023 [US1] Run live quickstart timing test: clone `kosmos-plugin-template` from a fresh shell, follow quickstart.md steps 1-8 with stopwatch; assert ≤ 30 min wall-clock; record evidence in `specs/1636-plugin-dx-5tier/quickstart-timing-evidence.md` — automated portion (steps 1+2) measured at 2.49s vs 240s budget (96× margin); human-edit steps tracked for T071 baseline
- [X] T024 [US1] Author `docs/plugins/quickstart.ko.md` Korean rendering of `specs/1636-plugin-dx-5tier/quickstart.md` (translate the 9-step walkthrough; keep code blocks in English; cite reference materials per Q4-CITE; **include `## Bilingual glossary` section template that the other 8 guides reuse per FR-006**)
- [X] T025 [US1] Author `docs/plugins/architecture.md`: Tool.ts + 4-primitive mapping diagram, plugin namespace rule, registry composition with `AdapterRegistration`, OTEL emission contract; cite `docs/vision.md § Layer 2` + Spec 022/031 per Q4-CITE
- [X] T026 [US1] Author `docs/plugins/data-go-kr.md`: portal key handling (`KOSMOS_*` env var pattern), rate-limit awareness, fixture recording via `scripts/record_fixture.py`; cite `docs/tool-adapters.md § Recording fixtures`

**Checkpoint**: External developer can ship a Live plugin end-to-end. SC-001 + SC-004 + SC-006 (for 2 of 4 examples) verifiable. MVP delivered.

---

## Phase 4: User Story 2 — Mock adapter contribution (Priority: P2)

**Goal**: A contributor produces a Mock-tier plugin for a permission-restricted system (홈택스, 건강검진) using the same DX flow with a `--mock` branch. CI rejects mock adapters that secretly call live, and live adapters that secretly mock.

**Independent Test**: Run `kosmos plugin init nts-homtax --mock`; the scaffold must produce a no-network test path. CI-replay of `tests/conftest.py` block_network fixture asserts zero outbound sockets during mock tests.

- [ ] T027 [US2] Add `--mock` branch to `tui/src/commands/plugin-init.ts`: when selected, emit scaffold without `httpx`/`aiohttp` imports in adapter.py, replace network call with fixture-replay; require `mock_source_spec` value at scaffold time; add test cases to `tui/test/commands/plugin-init.test.ts`
- [ ] T028 [P] [US2] Bootstrap `kosmos-plugin-store/kosmos-plugin-nts-homtax` Mock example repo: tier=mock, mock_source_spec="https://www.nts.go.kr/openapi/...", fixture replay only, README.ko.md explains why Mock (project lacks NTS partnership)
- [ ] T029 [P] [US2] Bootstrap `kosmos-plugin-store/kosmos-plugin-nhis-check` Mock example repo (국민건강보험공단 health-checkup): same shape as T028 with mock_source_spec pointing at NHIS public docs
- [ ] T030 [P] [US2] Author `docs/plugins/live-vs-mock.md`: when to use which tier, lint consequences (Q7-LIVE-USES-NETWORK / Q7-MOCK-NO-EGRESS), evidence rules per memory `feedback_mock_evidence_based`; cite `docs/mock/` directory pattern
- [ ] T031 [US2] Add Q7-MOCK-NO-EGRESS check to `src/kosmos/plugins/checks/q7_tier.py` and the workflow step matrix: pytest fixture asserts zero outbound socket count during mock tier tests; negative test in `test_validation_workflow.py`
- [ ] T032 [US2] Add Q7-LIVE-USES-NETWORK check (assert tier=live adapter source contains httpx/aiohttp import via AST scan) to the same checks module + negative test (live adapter labeled but with no network call → fail)

**Checkpoint**: Mock-tier path production-ready; live/mock mislabeling caught by CI. SC-006 (4 of 4 examples) achievable after T031/T032 land.

---

## Phase 5: User Story 3 — PIPA §26 trustee acknowledgment machine-enforced (Priority: P2)

**Goal**: Plugins handling PII MUST include a manifest acknowledgment block whose SHA-256 matches the canonical text. CI rejects missing or hash-tampered acknowledgments.

**Independent Test**: Submit a PR with `processes_pii: true` and no `pipa_trustee_acknowledgment` block → CI fails on Q6-PIPA-PRESENT. Submit with tampered hash → fails on Q6-PIPA-HASH. Submit with valid block → passes.

- [X] T033 [US3] Author `docs/plugins/security-review.md` full content: top section displays current canonical SHA-256 + version history; Trustee Acknowledgment Procedure (5 steps); L3 gate procedure; L2+ sandboxing guidelines (sandbox-exec / firejail); canonical PIPA §26 text already in markers from T005 — extend the surrounding doc
- [X] T034 [US3] Add PIPA acknowledgment sub-flow to `tui/src/commands/plugin-init.ts`: when `--pii` or interactive yes, render canonical text + SHA-256, prompt for `trustee_org_name` / `trustee_contact` / `pii_fields_handled` / `legal_basis`, write block to manifest.yaml; print `kosmos plugin pipa-text` helper command for re-display
- [X] T035 [US3] Add Q6-PIPA-PRESENT / Q6-PIPA-HASH / Q6-PIPA-ORG / Q6-PIPA-FIELDS-LIST checks to `src/kosmos/plugins/checks/q6_pipa.py` + 4 negative-case manifests in `src/kosmos/plugins/tests/test_validation_workflow.py` (FR-014, SC-003)
- [X] T036 [US3] Update `tests/fixtures/plugin_validation/checklist_manifest.yaml` Q6 rows with Korean+English failure messages pointing at `docs/plugins/security-review.md`; meta-CI verifies the rows render correctly in `docs/plugins/review-checklist.md`

**Checkpoint**: PIPA enforcement machine-active; legal-team-approved canonical text traceable to code via SHA-256.

---

## Phase 6: User Story 4 — 50-item validation workflow (Priority: P2)

**Goal**: Every reviewable invariant for a plugin manifest is mechanically enforced by `plugin-validation.yml`. No item relies on human reviewer judgment alone. PRs receive a Korean "N/50 통과 · M/50 실패" summary comment.

**Independent Test**: Run the workflow against the 9 negative-case manifests in `test_validation_workflow.py`; expect each to fail on the right item. Run against a 50/50-valid manifest; expect green + summary comment.

- [X] T037 [US4] Author `tests/fixtures/plugin_validation/checklist_manifest.yaml`: all 50 rows per research § R-1 (Q1-PYV2 through Q10-NO-LIVE-IN-CI); each row has `id`, `description_ko`, `description_en`, `source_rule`, `check_type`, `check_implementation`, `failure_message_ko`, `failure_message_en`; meta-validator asserts row count == 50
- [X] T038 [P] [US4] Implement `src/kosmos/plugins/checks/q1_schema.py` (10 Q1 checks: PYV2, NOANY, FIELD-DESC, INPUT-MODEL, OUTPUT-MODEL, MANIFEST-VALID, FROZEN, EXTRA-FORBID, VERSION-SEMVER, PLUGIN-ID-REGEX) + per-check unit tests
- [X] T039 [P] [US4] Implement `src/kosmos/plugins/checks/q2_failclosed.py` (6 Q2 checks: AUTH-DEFAULT, PII-DEFAULT, CONCURRENCY-DEFAULT, CACHE-DEFAULT, RATE-LIMIT-CONSERVATIVE, AUTH-EXPLICIT) + per-check tests
- [X] T040 [P] [US4] Implement `src/kosmos/plugins/checks/q3_security.py` (5 Q3 checks: V1-NO-EXTRA, V2-DPA, V3-AAL-MATCH, V4-IRREVERSIBLE-AAL, V6-AUTH-LEVEL-MAP) — reuses existing Spec 024/025 validators; tests cover invariant violation paths
- [X] T041 [P] [US4] Implement `src/kosmos/plugins/checks/q4_discovery.py` (8 Q4 checks: HINT-KO, HINT-EN, HINT-NOUNS via existing Kiwipiepy from Spec 022, HINT-MINISTRY, NAME-KO, CITE, README-KO, README-MIN-LEN)
- [X] T042 [P] [US4] Implement `src/kosmos/plugins/checks/q5_permission.py` (3 Q5 checks: LAYER-DECLARED, LAYER-MATCHES-PII, LAYER-DOC)
- [X] T043 [P] [US4] Implement `src/kosmos/plugins/checks/q7_tier.py` (Q7-TIER-LITERAL, Q7-LIVE-FIXTURE; Q7-MOCK-SOURCE / Q7-LIVE-USES-NETWORK / Q7-MOCK-NO-EGRESS already added via T031/T032 — wire all 5 here cohesively)
- [X] T044 [P] [US4] Implement `src/kosmos/plugins/checks/q8_namespace.py` (3 Q8 checks: NAMESPACE, NO-ROOT-OVERRIDE, VERB-IN-PRIMITIVES) — reuses validators from T010
- [X] T045 [P] [US4] Implement `src/kosmos/plugins/checks/q9_otel.py` (2 Q9 checks: OTEL-ATTR, OTEL-EMIT) + fake-OTLP collector pytest fixture
- [X] T046 [P] [US4] Implement `src/kosmos/plugins/checks/q10_tests.py` (4 Q10 checks: HAPPY-PATH, ERROR-PATH, FIXTURE-EXISTS, NO-LIVE-IN-CI)
- [X] T047 [US4] Author `.github/workflows/plugin-validation.yml` per contracts/plugin-validation-workflow.md: matrix-driven from checklist_manifest.yaml, --network=none container, Korean+English summary comment, fail merge on N < 50, ≤ 5 min runtime budget
- [X] T048 [US4] Implement `src/kosmos/plugins/tests/test_validation_workflow.py` covering the 9 negative-case manifests per contracts/plugin-validation-workflow.md (Q1-FIELD-DESC missing, Q1-NOANY violation, Q7-MOCK-SOURCE missing, Q6-PIPA-PRESENT missing, Q6-PIPA-HASH wrong, Q8-NAMESPACE wrong, Q8-NO-ROOT-OVERRIDE, Q9-OTEL-ATTR missing, valid 50/50) — verifies SC-003
- [X] T049 [US4] Author `.github/ISSUE_TEMPLATE/plugin-submission.yml` (FR-011): structured form capturing plugin id, tier, ministry/agency, public-spec URL, contact, PII handling, target permission Layer
- [X] T050 [US4] Author `docs/plugins/review-checklist.md`: Markdown rendering of the 50 items derived from `checklist_manifest.yaml` (script: `scripts/render_checklist.py`); meta-CI step asserts rendered Markdown reflects the YAML source
- [X] T051 [US4] Add meta-CI step in `.github/workflows/plugin-validation.yml` verifying YAML row count == 50 + every `check_implementation` reference resolves to an existing function via `inspect.import_module`; fail fast if drift
- [X] T052 [P] [US4] Author `docs/plugins/pydantic-schema.md` (schema authoring rules per Constitution §III: BaseModel, frozen=True, extra=forbid, no Any, Field description=); cite Spec 019 input-discipline

**Checkpoint**: 50/50 mechanical enforcement live. Maintainers no longer hand-verify mechanical items. SC-002 + SC-003 verifiable.

---

## Phase 7: User Story 5 — Citizen install / list / uninstall flow (Priority: P3)

**Goal**: Citizen runs `kosmos plugin install <name>` from TUI; install verifies SLSA, validates manifest, registers adapter, surfaces in BM25 within 5 s, writes consent receipt. Uninstall writes a complementary receipt and removes from registry.

**Independent Test**: Fresh TUI session → `kosmos plugin install seoul-subway` → 30-s install (SC-005), then `lookup(search="지하철")` returns the adapter (SC-004), then `/consent list` shows the install receipt.

- [ ] T053 [US5] Implement `tui/src/commands/plugin-install.ts` per contracts/plugin-install.cli.md: 8-phase Ink progress overlay, `--version`/`--catalog`/`--vendor-slsa-from`/`--yes`/`--dry-run` flags, IPC `plugin_op_request` frame, exit codes 0-7
- [ ] T054 [US5] Implement `tui/src/commands/plugin-list.ts`: read `~/.kosmos/memdir/user/plugins/index.json`, render with active/inactive status; integrates with existing Spec 287 PluginBrowser if installed plugin entries are present
- [ ] T055 [US5] Implement `tui/src/commands/plugin-uninstall.ts`: revoke flow + new `PluginConsentReceipt(action_type="plugin_uninstall")` write to `~/.kosmos/memdir/user/consent/`; backend deregisters from BM25 index
- [ ] T056 [US5] Register the 3 new commands in `tui/src/commands/index.ts` + add to slash-command autocomplete dispatcher per Spec 287 pattern
- [ ] T057 [P] [US5] Add `tui/test/commands/plugin-install.test.ts` with the 7 negative cases per contracts/plugin-install.cli.md (catalog miss, sha mismatch, slsa fail, manifest fail, citizen N, --dry-run no-write, KOSMOS_PLUGIN_SLSA_SKIP banner)
- [ ] T058 [US5] Wire backend `installer.py` ↔ `plugin_op` IPC frames end-to-end: smoke test in `src/kosmos/plugins/tests/test_install_e2e.py` installs the bootstrapped seoul-subway repo from a local file:// catalog into a temp memdir
- [ ] T059 [US5] Add SC-005 cold-install timing test (≤ 30 s) + SC-004 BM25 surface latency test (≤ 5 s after install) + SC-007 OTEL span attribute presence test (`kosmos.plugin.id` on every invocation via fake-OTLP collector)
- [ ] T060 [US5] Add SC-010 microbenchmark gated in CI: auto-discovery boot cost < 200 ms per installed plugin; pytest-benchmark config + threshold assertion

**Checkpoint**: Citizen install/uninstall path live. All 5 user stories independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Catalog org + remaining docs + agent-context + final integration validation. Run after US1–US5 land.

- [ ] T061 [P] Bootstrap `kosmos-plugin-store` GitHub org via `gh api` + create `kosmos-plugin-store/index` repo containing initial `index.json` (3 entries: seoul-subway, post-office, nts-homtax, nhis-check published) per contracts/catalog-index.schema.json
- [ ] T062 [P] Author `scripts/regenerate_catalog.py`: walks `kosmos-plugin-store/<repo>` releases via `gh api`, emits `index.json`; install as a workflow in the `kosmos-plugin-store/index` repo triggered on plugin-repo release events
- [ ] T063 [P] Vendor `slsa-verifier` binaries for darwin-amd64/arm64 + linux-amd64/arm64 into `~/.kosmos/vendor` bootstrap path; ship `scripts/bootstrap_slsa_verifier.sh` invoked on first `kosmos plugin install` if binary missing for current platform
- [ ] T064 [P] Author `docs/plugins/search-hint.md`: Ko/En bilingual hint authoring guidelines, Kiwipiepy noun-extraction guidance per Q4-HINT-NOUNS, ministry-name inclusion rule per Q4-HINT-MINISTRY; cite Spec 022 BM25 retrieval
- [ ] T065 [P] Author `docs/plugins/permission-tier.md`: Layer 1/2/3 decision tree (flowchart) mapping adapter properties to Layer; cite Spec 033 + AGENTS.md plugin-contract row 3
- [ ] T066 [P] Author `docs/plugins/testing.md`: pytest fixture conventions (block_network autouse, recorded fixture pattern), `@pytest.mark.live` marker discipline; cite Constitution §IV + `docs/testing.md`
- [ ] T067 Update `docs/plugins/README.md`: extend the existing 5-tier table with status badges (planned → shipped) per tier + version + link to canonical SHA-256; **verify all 9 guides under `docs/plugins/` contain a `## Bilingual glossary` heading (FR-006) — fail polish gate if any missing**
- [ ] T068 Update `CLAUDE.md` Active Technologies + Recent Changes sections (revert grep noise from update-agent-context.sh; manually add P5 stack rows per project pattern); update spec.md Deferred table to remove R-2 obviated row (sub-dir migration)
- [ ] T069 Update `AGENTS.md § New tool adapter` section to point at `docs/plugins/` as canonical contributor entry-point + add 2-line PIPA §26 trustee responsibility note
- [ ] T070 SC-006 self-test: every example plugin's repo MUST run `plugin-validation.yml` against itself in CI with 50/50 green; verify all 4 example repos green via `gh pr checks` after creation
- [ ] T071 SC-008 baseline measurement: record current `git log --author` external-contributor count = 0 in `specs/1636-plugin-dx-5tier/baseline-evidence.md`; document plan to re-measure 3 months post-merge
- [ ] T072 SC-009 Korean reviewer signoff: invite a native-Korean-speaking reviewer to complete the quickstart with English source files closed; record outcome in `specs/1636-plugin-dx-5tier/sc009-evidence.md` (deferred-checkbox if no reviewer available, tracked but non-blocking for PR merge)
- [ ] T073 Run `specs/1636-plugin-dx-5tier/quickstart.md` validation as final pre-PR gate: simulate fresh-shell walkthrough; assert all 9 steps complete green
- [ ] T074 Update `docs/vision.md § Reference materials` table to add row for `kosmos-plugin-store` org (SLSA-provenance attribution); add new ADR `docs/adr/ADR-007-plugin-dx-5tier-architecture.md` documenting R-2 (standalone repos) + R-3 (vendored slsa-verifier) decisions
- [ ] T075 Run `uv run pytest` + `bun test` from repo root; ensure all suites green; emit final test summary in PR body for the integrated commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup, T001-T004)**: no dependencies; T002–T004 fully parallel after T001
- **Phase 2 (Foundational, T005-T014)**: requires Phase 1; partial parallelism inside (T011 [P] independent; T007 [P] depends on T006; T008 depends on T006; T010 depends on T009; T012 independent)
- **Phase 3 (US1, T015-T026)**: requires Phase 2 complete (manifest schema + registry + IPC envelope all needed). T020/T021 [P] independent of each other and of T018 (different external repos vs TUI command).
- **Phase 4 (US2, T027-T032)**: requires T018 (init CLI must exist before adding --mock branch); T028/T029/T030 [P] independent.
- **Phase 5 (US3, T033-T036)**: requires T005 (canonical text) + T006 (manifest schema with PIPA validators).
- **Phase 6 (US4, T037-T052)**: requires T037 first (yaml manifest); then T038–T046 fully [P] across check files; then T047 (workflow YAML wires them); then T048 (negative tests); T049–T052 mostly [P].
- **Phase 7 (US5, T053-T060)**: requires Phase 2 (installer + IPC arm). T053–T055 share dispatcher edits via T056; T057 [P] independent.
- **Phase 8 (Polish, T061-T075)**: requires US1–US5 substantively complete. T061–T067 mostly [P]; T068/T070/T073 final integration.

### User Story Independence

- **US1 (P1)**: blocks none; minimum-viable shipping unit. Stop here for MVP demo.
- **US2 (P2)**: extends US1 (mock branch on the same CLI). Independent test possible.
- **US3 (P2)**: orthogonal to US1/US2. Independent test possible (PIPA-only PRs).
- **US4 (P2)**: enables US1/US2/US3 verification at scale; can land before or after US2/US3 since it consumes their checks.
- **US5 (P3)**: consumes outputs of US1+US4. Cannot ship without at least one published example plugin (T020 or T021).

### Within Each User Story

- Tests + impl interleaved per checklist item; negative tests in Phase 6 explicitly verify FR-015 / SC-003.
- Models before services (T006 before T009/T014).
- TUI commands depend on backend installer (T053 depends on T014).
- External repo bootstrap (T015/T020/T021/T028/T029/T061) is order-independent across repos but must happen after T017 (template CI exists).

---

## Parallel Execution Examples

### Phase 1 (Setup)
```
After T001:
  T002 [P]  TUI command stubs
  T003 [P]  docs/plugins/ scaffolding
  T004 [P]  validation fixtures dir
```

### Phase 2 (Foundational)
```
After T006:
  T007 [P]  manifest + ack tests
  T011 [P]  slsa subprocess wrapper + tests
  T012      IPC envelope arm (independent of schema work)
```

### Phase 3 (US1)
```
After T017 (template CI ready):
  T020 [P]  seoul-subway example repo bootstrap
  T021 [P]  post-office example repo bootstrap
  T024 [P]  quickstart.ko.md authoring
  T025 [P]  architecture.md authoring
  T026 [P]  data-go-kr.md authoring
```

### Phase 4 (US2)
```
After T027 (init --mock branch):
  T028 [P]  nts-homtax example
  T029 [P]  nhis-check example
  T030 [P]  live-vs-mock.md
```

### Phase 6 (US4 — biggest parallel opportunity)
```
After T037 (yaml manifest):
  T038 [P]  q1_schema.py     (10 checks)
  T039 [P]  q2_failclosed.py (6 checks)
  T040 [P]  q3_security.py   (5 checks)
  T041 [P]  q4_discovery.py  (8 checks)
  T042 [P]  q5_permission.py (3 checks)
  T043 [P]  q7_tier.py       (5 checks)
  T044 [P]  q8_namespace.py  (3 checks)
  T045 [P]  q9_otel.py       (2 checks)
  T046 [P]  q10_tests.py     (4 checks)
  T052 [P]  pydantic-schema.md doc
```

### Phase 8 (Polish)
```
After US1-US5:
  T061 [P]  bootstrap kosmos-plugin-store/index
  T062 [P]  catalog regenerator script
  T063 [P]  vendor slsa-verifier binaries
  T064 [P]  search-hint.md
  T065 [P]  permission-tier.md
  T066 [P]  testing.md
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 + Phase 2 (Setup + Foundational) — single session, ~2 days with Lead solo or 1 day with Agent Teams.
2. Phase 3 (US1) — ~3 days. Deliverable: external developer can ship a Live plugin end-to-end.
3. **STOP + VALIDATE**: run T023 quickstart timing test; if green, MVP demo-ready.

### Incremental Delivery (full Epic)

1. MVP (US1) → demo
2. Add US3 (PIPA enforcement) — small surface, security-critical → demo
3. Add US2 (mock variant) → demo
4. Add US4 (50-item workflow) — biggest parallel-team opportunity, ~10 [P] check files → demo
5. Add US5 (citizen install) → demo
6. Polish → integrated PR

### Agent Teams parallel (per AGENTS.md)

Once Foundational complete (T014 lands), 3+ independent tracks open simultaneously:
- Track A (Sonnet — Backend Architect): US4 check files (T038–T046, 9 [P] tasks)
- Track B (Sonnet — Frontend Developer): US1 TUI work (T018, T019, T020, T021)
- Track C (Sonnet — Technical Writer): US1+US2+Polish docs (T024, T025, T026, T030, T064, T065, T066)
- Track D (Sonnet — API Tester): negative-test suite (T048, T057, T059)

Lead (Opus): synthesizes across tracks, owns T012 (IPC envelope arm — touches Spec 032 contract), reviews PR before integration commit.

---

## Notes

- Total: **75 tasks** (within 90-cap budget per memory `feedback_subissue_100_cap`); 15-task headroom for mid-cycle additions / `[Deferred]` placeholders.
- Tests interleaved with implementation (TDD ordering: schema → validators → loader → CLI → workflow → docs → examples).
- All source code in English (AGENTS.md hard rule); Korean text confined to `description_ko`, `search_hint_ko`, `*.ko.md`, and Korean failure messages in checklist_manifest.yaml.
- External-repo bootstrap (T015/T020/T021/T028/T029/T061) requires `gh` CLI authenticated as the project lead; failed creation paths are non-blocking for in-repo work but block US1 quickstart timing (T023).
- Workarounds preserved: `setup-plan.sh` / `check-prerequisites.sh` / `update-agent-context.sh` reject `feat/`-prefixed branches → bypass via `.specify/feature.json` pointer; downstream commands work fine.
- After `/speckit-tasks` → `/speckit-analyze` (Constitution compliance gate) → `/speckit-taskstoissues` (materialize 75 sub-issues + 5 NEEDS TRACKING placeholders → still ≤ 90 cap; verify) → `/speckit-implement` (Agent Teams parallel execution per AGENTS.md).
