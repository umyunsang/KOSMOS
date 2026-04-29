---
description: "Tasks for Epic ζ #2297 — Zeta E2E Smoke (TUI primitive wiring + citizen tax-return chain demonstration)"
---

# Tasks: Zeta E2E Smoke — TUI Primitive Wiring + Citizen Tax-Return Chain Demonstration

**Input**: Design documents from `/specs/2297-zeta-e2e-smoke/`
**Prerequisites**: spec.md ✅ · plan.md ✅ · research.md ✅ · data-model.md ✅ · contracts/ (4 files) ✅ · quickstart.md ✅
**Constitution Check**: PASS (all 6 principles green per `plan.md § Constitution Check`).
**Sub-issue budget**: 28 tasks ≤ 90 cap (Spec 287 reserve buffer applied).

**Format**: `[ID] [P?] [Story?] Description` — checkbox + Task ID + optional [P]arallel marker + optional [Story] label + action with file path.

**User stories** (from spec.md):
- **US1** (P1): Citizen tax-return chain renders receipt id end-to-end.
- **US2** (P2): All 15 mock adapters exercised at least once across the full scenario set.
- **US3** (P1): Sub-issue #2481 resolved — `tool_id ↔ family_hint` translation deterministic and auditable.
- **US4** (P3): `policy-mapping.md` cites international AX-gateway specs.
- **US5** (P3): 5 OPAQUE scenario docs explain hand-off.

**Independent test criteria**:
- US1: PTY log shows ≥3 `tool_call`/`tool_result` pairs + receipt-id regex match + `CHECKPOINTreceipt token observed` exactly once + Lead Opus Read verifies keyframe-3 PNG.
- US2: `pytest tests/integration/test_all_15_mocks_invoked.py` PASS — all 15 mocks logged ≥1 invocation.
- US3: `pytest tests/integration/test_tool_id_to_family_hint_translation.py` ≥9/10 PASS + unknown-tool_id case returns structured error.
- US4: `bash scripts/probe_policy_links.sh` exits 0; doc has ≥10 mapping rows.
- US5: `python scripts/check_scenario_docs.py` exits 0; 5 docs each ≥5 narrative steps + hand-off URL footer.

**Dispatch tree** (per `research.md § Decision 7`):
- Phase 0a (T003-T006) — sonnet-backend, ≤4 files
- Phase 0b (T007-T013) — sonnet-tui, ≤8 files
- Phase 1a (T014-T020) — sonnet-smoke, ≤14 files (10 fixtures + 4 scripts)
- Phase 1b (T021-T028) — Lead solo, 7 files

---

## Phase 1 — Setup (Lead solo, sequential)

- [X] T001 #2482 Verify η commit `1321f77` is on `main` and worktree is clean: run `git log --oneline | grep 1321f77` (MUST match) AND `git status --short` (MUST be empty other than `specs/2297-zeta-e2e-smoke/` work-in-progress files). Acceptance: both checks PASS.
- [X] T002 #2483 Verify backend registers 5 core tools at boot via `register_all_tools(registry, executor)` boot path; expected `len(registry.all_tools())` = 19 (16 KOROAD/KMA/HIRA/NMC/NFA119/MOHW + 3 new η primitives `verify`/`submit`/`subscribe`). Acceptance: registry total == 19, verify/submit/subscribe all present.

---

## Phase 2 — Foundational (Phase 0a, blocks US1 + US3, sonnet-backend dispatch unit)

**Goal**: Backend `_VerifyInputForLLM` accepts the LLM-emitted `{tool_id, params}` shape from `prompts/system_v1.md` v2 and translates to legacy `{family_hint, session_context}` via `@model_validator(mode="before")`. Sources canonical map from markdown at boot — no Python duplication.

- [X] T003 #2484 [P] Create new module `src/kosmos/tools/verify_canonical_map.py` per `data-model.md § 2`: exports `resolve_family(tool_id) -> str | None` and `get_canonical_map() -> Mapping[str, str]`; lazy `lru_cache`d loader parses `<verify_families>` markdown block from `prompts/system_v1.md` (path resolved via `KOSMOS_PROMPTS_DIR` env, fallback to `<repo_root>/prompts`); raises `RuntimeError` on <10 entries (FR-008b). Acceptance: `python -c "from kosmos.tools.verify_canonical_map import get_canonical_map; print(len(get_canonical_map()))"` prints `10`.
- [X] T004 #2485 [P] Create unit test `tests/unit/test_verify_canonical_map_parser.py` per `data-model.md § 2` validation rules: assert ≥10 entries, assert all 10 canonical keys present (`mock_verify_module_modid`, `mock_verify_module_kec`, `mock_verify_module_geumyung`, `mock_verify_module_simple_auth`, `mock_verify_module_any_id_sso`, `mock_verify_gongdong_injeungseo`, `mock_verify_geumyung_injeungseo`, `mock_verify_ganpyeon_injeung`, `mock_verify_mobile_id`, `mock_verify_mydata`), assert family_hint values match (FR-008b regression). Acceptance: `uv run pytest tests/unit/test_verify_canonical_map_parser.py -v` PASS.
- [X] T005 #2486 Extend `src/kosmos/tools/mvp_surface.py:243` `_VerifyInputForLLM` per `contracts/verify-input-shape.md` I-V1 through I-V8: add `tool_id: str | None` and `params: dict[str, object] | None` LLM-visible fields; preserve legacy `family_hint`/`session_context`; add `@model_validator(mode="before")` that translates `tool_id`→`family_hint` via `verify_canonical_map.resolve_family(...)` and packs `params`→`session_context`; raises `ValueError("unknown verify tool_id: <value>")` on unknown tool_id (FR-008a/8b/10). Acceptance: `uv run mypy src/kosmos/tools/mvp_surface.py` PASS + `uv run ruff check src/kosmos/tools/` PASS.

**Phase 2 Checkpoint**: Phase 0a complete. Phase 3 (US3 test) and Phase 4 (US1 TUI work) may now proceed in parallel.

---

## Phase 3 — User Story 3 — `tool_id` ↔ `family_hint` translation deterministic (P1)

**Story goal**: Sub-issue #2481 resolved. The translation occurs at the backend boundary deterministically; unknown `tool_id` produces structured error; canonical map drift impossible by construction.

**Independent test criterion**: `pytest tests/integration/test_tool_id_to_family_hint_translation.py -v` reports ≥9/10 PASS for the canonical-map cases + 1 PASS for the unknown-`tool_id` case.

- [X] T006 #2487 [P] [US3] Create integration test `tests/integration/test_tool_id_to_family_hint_translation.py` per spec.md US3 acceptance scenarios + `contracts/verify-input-shape.md` I-V1/I-V2/I-V3/I-V5: 10 parametrised cases (one per canonical family, asserting that `_VerifyInputForLLM.model_validate({"tool_id": "...", "params": {...}})` produces the expected `family_hint` AND preserves `tool_id`/`params`); 1 legacy-shape case (asserts back-compat); 1 unknown-`tool_id` case (asserts `ValueError`); 1 idempotency case (asserts double-validation no-op). Acceptance: `uv run pytest tests/integration/test_tool_id_to_family_hint_translation.py -v` ≥12 PASS / 0 FAIL.

**Phase 3 Checkpoint**: US3 independently testable now. US3 closure depends on US1's PTY smoke confirming the translation is exercised end-to-end.

---

## Phase 4 — User Story 1 — Citizen tax-return chain renders receipt id (P1, sonnet-tui dispatch unit)

**Story goal**: Land the verify→lookup→submit chain with a citizen-visible `접수번호: hometax-YYYY-MM-DD-RX-XXXXX` rendered.

**Independent test criterion**: 4 verifications on the same head — (a) PTY log contains receipt regex × 1 + `CHECKPOINTreceipt token observed` × 1, (b) Lead Opus Read confirms keyframe-3 PNG shows receipt, (c) `pytest test_tui_primitive_dispatch_e2e.py` PASS, (d) `pytest test_tool_id_to_family_hint_translation.py` PASS.

- [X] T007 #2488 [P] [US1] Create `tui/src/tools/_shared/pendingCallRegistry.ts` per `data-model.md § 3` + `contracts/tui-primitive-dispatcher.md` I-D4: class `PendingCallRegistry` with `register/resolve/reject/has/size/clear`; throws on duplicate `callId`; idempotent resolve. Acceptance: file created with full TS interface; `bun typecheck` PASS.
- [X] T008 #2489 [P] [US1] Create `tui/src/tools/_shared/dispatchPrimitive.ts` + `dispatchPrimitive.test.ts` per `data-model.md § 4` + `contracts/tui-primitive-dispatcher.md` I-D2/I-D3/I-D6/I-D7/I-D10: shared helper signature `dispatchPrimitive<O>(opts) -> Promise<ToolResult<O>>`; mints UUIDv7 callId; constructs ToolCallFrame; registers pending call with FR-006 timeout (default 30s, `KOSMOS_TUI_PRIMITIVE_TIMEOUT_MS` override); sends via bridge; awaits resolution; OTEL `kosmos.tui.primitive.timeout` attribute on timeout; passthrough error envelope. bun unit test covers ≥5 scenarios from I-D10. Acceptance: `bun test src/tools/_shared/dispatchPrimitive.test.ts` PASS.
- [X] T009 #2490 [P] [US1] Replace stub `call()` body in `tui/src/tools/LookupPrimitive/LookupPrimitive.ts:319-330` per `contracts/tui-primitive-dispatcher.md` I-D1: invoke `dispatchPrimitive({primitive: 'lookup', args: input, context, ...})`; return resolved result. Preserve existing `validateInput` adapter resolution + `kosmosCitations` context attachment (no regression to lookup-only path per US1 AC4 / FR-001). Acceptance: `bun typecheck` PASS + `bun test` no regression vs `main`.
- [X] T010 #2491 [P] [US1] Replace stub `call()` body in `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts:248-263` per `contracts/tui-primitive-dispatcher.md` I-D1 + I-D8 + FR-002 + FR-009: invoke `dispatchPrimitive({primitive: 'verify', args: input, ...})` with **args forwarded verbatim** (NO `tool_id`→`family_hint` translation at TUI side; backend's pre-validator owns translation per FR-008). Acceptance: bun unit test asserts `frame.arguments.tool_id === input.tool_id` (no mutation, FR-009).
- [X] T011 #2492 [P] [US1] Replace stub `call()` body in `tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts:255-265` per `contracts/tui-primitive-dispatcher.md` I-D1 + FR-003: invoke `dispatchPrimitive({primitive: 'submit', args: input, ...})`; return resolved envelope. Acceptance: `bun typecheck` PASS + `bun test` no regression.
- [X] T012 #2493 [P] [US1] Replace stub `call()` body in `tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts` per `contracts/tui-primitive-dispatcher.md` I-D1 + I-D9 + FR-004: invoke `dispatchPrimitive({primitive: 'subscribe', args: input, ...})`; return first `tool_result` envelope as opened-acknowledgment (subsequent stream events deferred per spec.md Deferred Items). Acceptance: `bun typecheck` PASS + bun unit test for opened-ack behavior.
- [X] T013 #2494 [US1] Extend `tui/src/ipc/llmClient.ts:405` (after the existing `tool_call` arm) with a `tool_result` arm per `contracts/tui-primitive-dispatcher.md` I-D5: cast as `ToolResultFrame`, call `pendingCallRegistry.resolve(call_id, frame)`, log WARN if not found, do NOT yield SDK content_block event. Plumb the registry instance through `LLMClientOptions` (or per-session singleton accessor) so tests can inject. Acceptance: `bun typecheck` PASS + integration test in T017 verifies frame routing.
- [X] T014 #2495 [US1] Add `CHECKPOINTreceipt token observed` literal emit in TUI submit path (in `dispatchPrimitive.ts` or `SubmitPrimitive.ts`) gated on `KOSMOS_SMOKE_CHECKPOINTS=true` env per `contracts/pty-smoke-protocol.md` I-P2: when a submit `tool_result` envelope's `transaction_id` matches the receipt regex, write the literal string to `process.stderr.write` once per chain. Acceptance: bun unit test toggles env + asserts marker emitted exactly once for matching frame.
- [ ] T015 #2496 [US1] Author Layer 2 PTY driver `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect` per `contracts/pty-smoke-protocol.md` I-P1: timeout 90s, spawn `bun run tui`, expect KOSMOS branding, send `종합소득세 신고해줘\r`, expect receipt regex + checkpoint marker, log to `smoke-citizen-taxreturn-pty.txt`, exit cleanly. Acceptance: script syntactically valid (`expect -n smoke-citizen-taxreturn.expect` reports no syntax errors).
- [ ] T016 #2497 [US1] Author Layer 4 vhs tape `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape` per `contracts/vhs-keyframe-protocol.md` I-K1: emit `Output smoke-citizen-taxreturn.gif` + ≥3 `Screenshot` directives at boot/dispatch/receipt stages; total wall-clock ≤120s. Acceptance: `vhs --validate smoke-citizen-taxreturn.tape` reports no errors (or `vhs --help` if validate flag absent — manual visual review).
- [ ] T017 #2498 [US1] Create `tests/integration/test_tui_primitive_dispatch_e2e.py` per FR-016 + spec.md US1 AC1/AC2/AC3: ≤80 LOC pytest fixture spawning `bun run tui` subprocess, sending citizen prompt via stdin pipe, capturing stdout, asserting ≥3 `tool_call` markers + ≥3 `tool_result` markers + receipt-id regex match + 3 same-`delegation_token` ledger lines under `~/.kosmos/memdir/user/consent/<YYYY-MM-DD>.jsonl`. Acceptance: `uv run pytest tests/integration/test_tui_primitive_dispatch_e2e.py -v` PASS on a working tree where T003-T014 are merged.
- [ ] T018 #2499 [US1] **Lead-only task**: run the full smoke chain (`expect specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect` + `vhs specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape`) on a working tree where T003-T017 are merged; capture and commit `specs/2297-zeta-e2e-smoke/{smoke-citizen-taxreturn-pty.txt,smoke-citizen-taxreturn.gif,scripts/smoke-keyframe-{1-boot,2-dispatch,3-receipt}.png}`; **Lead Opus uses Read tool on `smoke-keyframe-3-receipt.png`** to visually confirm receipt-id text matches `접수번호: hometax-2026-\d\d-\d\d-RX-[A-Z0-9]{5}` per `contracts/vhs-keyframe-protocol.md` I-K3. Acceptance: PR description lists 6 artefacts + Lead's Read-tool visual confirmation note.

**Phase 4 Checkpoint**: US1 (the demo headline) is shipped. US3 closes via T006 + T018 transitive verification.

---

## Phase 5 — User Story 2 — All 15 mock adapters exercised (P2)

**Story goal**: 10 verify families + 5 non-verify mocks each get ≥1 invocation across the full battery.

**Independent test criterion**: `pytest tests/integration/test_all_15_mocks_invoked.py -v` PASS.

- [ ] T019 #2500 [P] [US2] Create 10-fixture battery `tests/fixtures/citizen_chains/{modid,kec,geumyung_module,simple_auth_module,any_id_sso,gongdong_injeungseo,geumyung_injeungseo,ganpyeon_injeung,mobile_id,mydata}.json` per `data-model.md § 6` schema (FR-019): each fixture pairs citizen_prompt with expected first_tool_call (canonical-map enforced) + expected_chain_completes_with_receipt + expected_mock_invocations ordered list. The `any_id_sso.json` fixture has `expected_chain_completes_with_receipt: false` (IdentityAssertion only, per US2 AC3 + system prompt Exception clause). Acceptance: 10 JSON files validated; each fixture's `family_hint` matches the canonical map's value for its `tool_id`.
- [ ] T020 #2501 [P] [US2] Create `tests/integration/test_all_15_mocks_invoked.py` per FR-020 + SC-004: load all 10 fixtures, drive each through the TUI (or directly through the backend dispatcher for speed), capture per-mock invocation counts via the consent-ledger jsonl + adapter-side counters; assert all 15 mock adapters (10 verify + 2 submit + 2 lookup OPAQUE-prefill + 1 subscribe) appear ≥1 in the aggregate. Acceptance: `uv run pytest tests/integration/test_all_15_mocks_invoked.py -v` PASS.

**Phase 5 Checkpoint**: US2 independently testable; US2 PASS implies the 5-tool surface is fully callable end-to-end.

---

## Phase 6 — User Story 4 — Policy mapping doc (P3, Lead solo)

**Story goal**: Publication-quality artefact citing Singapore APEX / Estonia X-Road / EU EUDI / Japan マイナポータル with stable URLs.

**Independent test criterion**: `bash specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh` exits 0 + manual review confirms ≥10 mapping rows.

- [X] T021 #2502 [P] [US4] Author `docs/research/policy-mapping.md` per `data-model.md § 8` + FR-017 + spec.md US4 acceptance scenarios: bilingual ko-primary / en-fallback title; 1-2 paragraph thesis linking AGENTS.md § CORE THESIS to the four international analogs; single canonical mapping table with 4 foreign-spec columns + ≥10 KOSMOS-adapter rows; citations footnote with stable canonical URLs (each agency's own spec, not third-party blogs); each cited URL returns 2xx/3xx within 5s. Acceptance: `markdownlint docs/research/policy-mapping.md` PASS + table has ≥10 rows.
- [X] T022 #2503 [P] [US4] Author `specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh` per SC-009: bash script that grep-extracts URLs from `docs/research/policy-mapping.md`, runs `curl -s -o /dev/null -w "%{http_code}\n" -L --max-time 5 <url>` for each, exits 0 iff all return 200/2xx/3xx. Acceptance: `bash specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh` exits 0.

---

## Phase 7 — User Story 5 — 5 OPAQUE scenario docs (P3, Lead solo)

**Story goal**: Per AGENTS.md § L1-B B3, every OPAQUE-forever family has a narrative scenario doc.

**Independent test criterion**: `python specs/2297-zeta-e2e-smoke/scripts/check_scenario_docs.py` exits 0.

- [X] T023 #2504 [P] [US5] Author `docs/scenarios/hometax-tax-filing.md` per `data-model.md § 9` + FR-018: Korean-primary title; "Why no adapter" thesis (1-2 sentences); numbered citizen narrative ≥5 steps (citizen action → TUI message → hand-off URL → return path → confirmation); footer `## Hand-off URL` listing `https://www.hometax.go.kr/`. Acceptance: file structure validates.
- [X] T024 #2505 [P] [US5] Author `docs/scenarios/gov24-minwon-submit.md` per FR-018 (same structure as T023; Hand-off URL = `https://www.gov.kr/`). Acceptance: file structure validates.
- [X] T025 #2506 [P] [US5] Author `docs/scenarios/mobile-id-issuance.md` per FR-018 (same structure; Hand-off URL = the official 모바일 신분증 발급 portal — verify exact URL during authoring). Acceptance: file structure validates.
- [X] T026 #2507 [P] [US5] Author `docs/scenarios/kec-yessign-signing.md` per FR-018 (same structure; Hand-off URL = KEC / yessign canonical signing portal — verify exact URL during authoring). Acceptance: file structure validates.
- [X] T027 #2508 [P] [US5] Author `docs/scenarios/mydata-live.md` per FR-018 (same structure; Hand-off URL = KFTC MyData consent portal). Acceptance: file structure validates.
- [X] T028 #2509 [US5] Author `specs/2297-zeta-e2e-smoke/scripts/check_scenario_docs.py` per SC-010: Python stdlib-only script that walks `docs/scenarios/{hometax-tax-filing,gov24-minwon-submit,mobile-id-issuance,kec-yessign-signing,mydata-live}.md`, asserts each has Korean-primary title + "Why no adapter" section + ≥5 numbered narrative steps + `## Hand-off URL` footer. Acceptance: `uv run python specs/2297-zeta-e2e-smoke/scripts/check_scenario_docs.py` exits 0 for all 5 files.

---

## Phase 8 — Polish (Lead solo, sequential, FINAL gate)

- [ ] T029 #2510 Final lint + typecheck + test passes: `uv run ruff format --check && uv run ruff check && uv run mypy src/kosmos && uv run pytest -q && cd tui && bun typecheck && bun test`. **All MUST pass with 0 errors / 0 regressions vs `main`.** Confirm `git diff main -- prompts/` is empty (FR-022) and `git diff main -- pyproject.toml tui/package.json` shows no new runtime deps (FR-023). Acceptance: all 6 commands green; zero diffs in invariant files.

---

## Dependencies

```text
T001 ──▶ T002 ──┬──▶ T003 [P] ──┐
                ├──▶ T004 [P] ──┼──▶ T005 ──┬──▶ T006 [P] (US3)
                │               │           ├──▶ T007 [P] (US1)
                │               │           ├──▶ T008 [P] (US1)
                │               │           ├──▶ T009-T012 [P × 4] (US1)
                │               │           └──▶ T013 (US1)
                │               │                  │
                │               │                  └──▶ T014 ──▶ T015, T016 [P] ──▶ T017 ──▶ T018
                │               │                                                              │
                │               │                  └──▶ T019 [P] (US2) ──▶ T020 (US2)
                │               │                                                              │
                │               │                  └──▶ T021, T022 [P] (US4)
                │               │                  └──▶ T023-T027 [P × 5] (US5) ──▶ T028 (US5)
                │               │                                                              │
                │               │                                                              ▼
                │               │                                                            T029
```

Phase 0a (T003-T005) parallel-safe with Phase 0b (T007-T013) — no shared files.
Phase 1a (T015-T020) depends on T005 (backend) AND T013 (TUI dispatcher) merged.
Phase 1b (T021-T028) parallel-safe with Phase 1a — Lead solo for citation accuracy.

---

## Parallel Execution Examples

**Phase 2 burst** (sonnet-backend dispatches T003+T004 in parallel):
```text
[parallel] T003 verify_canonical_map.py + T004 test_verify_canonical_map_parser.py
[sequential] T005 _VerifyInputForLLM extension (depends on T003)
```

**Phase 4 burst** (sonnet-tui dispatches T007-T012 in parallel):
```text
[parallel] T007 pendingCallRegistry.ts + T008 dispatchPrimitive.ts + T009-T012 four primitive call() bodies
[sequential] T013 llmClient.ts tool_result arm (depends on T007 + T008)
[sequential] T014 CHECKPOINT marker (depends on T013)
```

**Phase 7 burst** (Lead solo dispatches T023-T027 in parallel):
```text
[parallel] T023+T024+T025+T026+T027 — 5 OPAQUE scenario docs (different files)
[sequential] T028 check_scenario_docs.py (depends on T023-T027)
```

---

## Implementation Strategy

**MVP scope** = Phase 1 + Phase 2 + Phase 3 + Phase 4 (T001-T018). This delivers the demo headline (citizen tax-return chain renders receipt id end-to-end) and resolves Sub-issue #2481.

**Incremental delivery**:
- After T018 (MVP): demo is functional; PR can land if Phase 5/6/7 are deferred to a follow-up Epic. (Not preferred — see "Required for Epic ζ closure" below.)
- After T020: US2 closes (full mock surface validated).
- After T022: US4 closes (policy mapping artefact ships).
- After T028: US5 closes (5 OPAQUE scenario docs ship).
- After T029: Epic ζ ready for merge.

**Required for Epic ζ closure**: T001-T029 ALL complete. Spec.md acceptance criteria SC-001 through SC-012 all measured.

**Sub-issue #2481 closure**: T006 PASS implies the translation invariant holds; T018 PASS confirms the chain exercises it; #2481 closes after merge per FR-026 + AGENTS.md § PR closing rule.

---

## Notes

- Sub-issue budget: 28 tasks ≤ 90 cap (Spec 287 reserve). No consolidation needed.
- AGENTS.md § Agent Teams ≤5 task / ≤10 file dispatch unit budget per teammate respected:
  - sonnet-backend: T003-T005 = 3 tasks, 4 files.
  - sonnet-tui: T007-T014 = 8 tasks, 8 files (within budget when T009-T012 dispatched as a single 4-file group).
  - sonnet-smoke: T015-T020 = 6 tasks, ≤14 files (10 fixtures + 4 scripts/tests).
  - Lead solo: T001-T002 + T018 + T021-T028 + T029 = 12 tasks (Lead is the dispatcher, not a teammate; budget does not apply).
- Constitution Check: PASS (all 6 principles green, see `plan.md § Constitution Check`).
- FR coverage: all 26 FR mapped (FR-001→T009, FR-002→T010, FR-003→T011, FR-004→T012, FR-005→T008, FR-006→T008, FR-007→T008+T013, FR-008/8a/8b→T003+T005, FR-009→T010, FR-010→T005+T006, FR-011→T015, FR-012→T016+T018, FR-013→T014, FR-014→T015+T017, FR-015→T015+T017+T018, FR-016→T017, FR-017→T021, FR-018→T023-T027, FR-019→T019, FR-020→T020, FR-021→(implicit in T011/T015/T018 — deterministic seed under CI), FR-022→T029, FR-023→T029, FR-024→T029, FR-025→T029, FR-026→T029).
- SC coverage: all 12 SC mapped (SC-001→T015+T017, SC-002→T018, SC-003→T006, SC-004→T020, SC-005→T017, SC-006→T029, SC-007→T029, SC-008→T029, SC-009→T022, SC-010→T028, SC-011→T029, SC-012→T029).
