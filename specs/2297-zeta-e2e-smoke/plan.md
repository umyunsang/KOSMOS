# Implementation Plan: Zeta E2E Smoke — TUI Primitive Wiring + Citizen Tax-Return Chain Demonstration

**Branch**: `2297-zeta-e2e-smoke` | **Date**: 2026-04-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2297-zeta-e2e-smoke/spec.md`

## Summary

Land the citizen tax-return delegation chain end-to-end (verify → lookup → submit → 접수번호) as the first visible KOSMOS AX-infrastructure demo. Phase 0 closes two parallel gaps: (a) **the citizen-blocker** — backend `_VerifyInputForLLM` accepts the LLM-taught `{tool_id, params}` shape via a `@model_validator(mode="before")` pre-validator that translates to the dispatcher's `{family_hint, session_context}` legacy shape, with the canonical 10-row map sourced at process boot from `prompts/system_v1.md` `<verify_families>` block (no Python duplication, FR-022-safe); (b) **the parallel correctness gap** — TUI `Lookup/Verify/Submit/SubscribePrimitive.call()` stubs are replaced with a real IPC `tool_call`/`tool_result` dispatcher that uses a TUI-side `_pending_calls` future-registry mirroring the backend pattern. Phase 1 captures the citizen tax-return chain via Layer 2 PTY + Layer 4 vhs (3+ keyframe PNG) artefacts, adds a TUI-mediated integration test, exercises all 15 mock adapters, and authors `docs/research/policy-mapping.md` (KOSMOS↔Singapore APEX/Estonia X-Road/EU EUDI/Japan マイナポータル) plus 5 OPAQUE scenario docs.

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing baseline; no version bump) · TypeScript 5.6+ on Bun v1.2.x (TUI, existing Spec 287 stack; no version bump).
**Primary Dependencies**: `pydantic >= 2.13` (frozen models + `@model_validator(mode="before")` for FR-008a) · `pydantic-settings >= 2.0` (env catalog: `KOSMOS_TUI_PRIMITIVE_TIMEOUT_MS` for FR-006) · `httpx >= 0.27` (existing) · `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (existing — `kosmos.tui.primitive.timeout` span attribute, FR-006) · `pytest` + `pytest-asyncio` (existing test stack) · TS side: existing `ink`, `react`, `@inkjs/ui`, `string-width`, `zod ^3.23`, `@modelcontextprotocol/sdk`, Bun stdlib + `crypto.randomUUID()`. **Zero new runtime dependencies** — AGENTS.md hard rule + spec FR-023 + SC-007.
**Storage**: N/A at runtime. The 10-row canonical `tool_id ↔ family_hint` map is read once at backend boot from `prompts/system_v1.md` (already loaded by `PromptLoader`) into an in-memory frozen dict — no separate persistence. TUI-side `_pending_calls` future-registry is in-memory only, lifetime = chat-request turn.
**Testing**: `pytest tests/integration/test_tui_primitive_dispatch_e2e.py` (TUI-mediated chain via stdin/stdout pipes against spawned `bun run tui`, ≤80 LOC) · `pytest tests/integration/test_tool_id_to_family_hint_translation.py` (10 parametrised cases per canonical family + 1 unknown-tool_id case) · `pytest tests/integration/test_all_15_mocks_invoked.py` (full battery) · `pytest tests/unit/test_verify_canonical_map_parser.py` (markdown parser regression) · `bun test tui/src/tools/_shared/dispatchPrimitive.test.ts` (TUI dispatcher unit) · Layer 2 PTY (`expect`) · Layer 4 vhs (`charm-vhs ≥ 0.11`).
**Target Platform**: macOS Darwin 25 + Linux x86_64 (existing CI matrix). Terminal-only (Ink + Bun stdio JSONL bridge to Python backend).
**Project Type**: KOSMOS hybrid — Python backend (`src/kosmos/`) + TUI (`tui/`). This Epic touches both.
**Performance Goals**: TUI primitive `call()` IPC round-trip p95 < 200ms for in-memory mocks (FR-006 timeout default 30s applies only to genuinely-stuck dispatches). Citizen-facing E2E chain p95 ≤ 90s (3 LLM turns × ~25s ceiling per FriendliAI Tier 1 latency).
**Constraints**: `prompts/**` immutable on this branch (FR-022, Spec 026 manifest hash gate). No new runtime deps (FR-023). All TUI changes pass `bun typecheck` + `bun test` + `bun run tui` boot smoke (FR-024). All Python changes pass `ruff format/check` + `mypy` + `pytest` (FR-025).
**Scale/Scope**: 15 mock adapters · 10 verify families · 3 primitive call() bodies + 1 subscribe (with subscription lifetime caveat) · 1 shared dispatcher helper · 1 backend pre-validator · 1 markdown parser · 5 narrative docs · 1 mapping doc · 4 smoke harnesses (.expect, .tape, 3 png keyframes).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|---|---|---|
| I. Reference-Driven Development | ✅ | Every design decision maps to a primary reference: TUI dispatcher pattern → CC `restored-src/services/tools/toolExecution.ts:1207` (Tool.call invocation site, byte-identical signature preserved) + AutoGen mailbox (Spec 027 Future-registry pattern). Backend pre-validator → Pydantic v2 `@model_validator(mode="before")` (Pydantic AI reference, Tool System layer). Smoke methodology → AGENTS.md § TUI verification methodology Layers 0–4 (canonical). Policy mapping doc references — Singapore APEX / X-Road / EUDI / マイナポータル — all cited with stable URLs in `docs/research/policy-mapping.md`. |
| II. Fail-Closed Security | ✅ | Unknown `tool_id` raises `ValueError` (FR-008a + FR-010), the LLM continuation gets a typed error envelope, no silent mistranslation. No new permission classifications introduced. The verify mock adapters retain their existing AAL hints + agency-citation policy unchanged. |
| III. Pydantic v2 Strict Typing | ✅ | `_VerifyInputForLLM` extension uses `@model_validator(mode="before")` with strict typing — no `Any`. The `tool_id` field is added as `str | None = Field(default=None, ...)` so the schema published to the LLM lists `tool_id` as the canonical field. The TUI-side `dispatchPrimitive.ts` helper uses Zod for tool_call/tool_result envelope validation. |
| IV. Government API Compliance | ✅ | All chain dispatch is mock-only (FR-021 deterministic seed under CI). No live `data.go.kr` calls. Receipt fixture format `hometax-YYYY-MM-DD-RX-XXXXX` is documented in the existing `mock_submit_module_hometax_taxreturn` adapter. |
| V. Policy Alignment | ✅ | The chain demonstrates Korea AI Action Plan Principle 8 (single conversational window for cross-ministry citizen services — verify→lookup→submit spans modid + hometax) + Principle 9 (Open API and OpenMCP for public service integration — KOSMOS as the AX-infrastructure client-side reference). No paper submission required (Principle 5). |
| VI. Deferred Work Accountability | ✅ | All 7 items in spec.md "Deferred to Future Work" table. Sub-issue #2481 closure documented (FR-026). 5 η-deferred sub-issues (#2475-#2479) explicitly excluded. |

**Gate decision**: PASS. No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/2297-zeta-e2e-smoke/
├── plan.md              # This file
├── spec.md              # Feature specification (already authored)
├── research.md          # Phase 0 output — root-cause analysis + architecture decisions
├── data-model.md        # Phase 1 output — entity schemas (TS + Python)
├── quickstart.md        # Phase 1 output — Lead Opus operator guide
├── contracts/
│   ├── verify-input-shape.md          # FR-008a/8b/9/10 contract
│   ├── tui-primitive-dispatcher.md    # FR-001-FR-007 contract
│   ├── pty-smoke-protocol.md          # FR-011/13/14/15 contract
│   └── vhs-keyframe-protocol.md       # FR-012 contract
├── checklists/
│   └── requirements.md  # Already authored
├── scripts/
│   ├── smoke-citizen-taxreturn.expect # FR-011
│   ├── smoke-citizen-taxreturn.tape   # FR-012
│   ├── probe_policy_links.sh          # SC-009
│   └── check_scenario_docs.py         # SC-010
├── smoke-citizen-taxreturn-pty.txt    # FR-011 captured artefact
├── smoke-keyframe-1-boot.png          # FR-012 captured keyframe
├── smoke-keyframe-2-dispatch.png      # FR-012 captured keyframe
├── smoke-keyframe-3-receipt.png       # FR-012 captured keyframe
├── smoke-citizen-taxreturn.gif        # FR-012 animated artefact
├── tasks.md             # /speckit-tasks output (Phase 2)
└── dispatch-tree.md     # AGENTS.md § Agent Teams Sonnet teammate dispatch tree
```

### Source Code (repository root)

```text
KOSMOS/
├── src/kosmos/
│   ├── tools/
│   │   └── mvp_surface.py                     # MODIFY — extend _VerifyInputForLLM with @model_validator(mode="before") (FR-008a)
│   ├── tools/verify_canonical_map.py          # NEW — parses prompts/system_v1.md <verify_families> block at boot (FR-008b)
│   └── ipc/stdio.py                           # READ-ONLY — _dispatch_primitive uses the new schema indirectly via mvp_surface registration; no edits in stdio
├── tui/src/
│   ├── tools/
│   │   ├── _shared/
│   │   │   ├── dispatchPrimitive.ts           # NEW — shared IPC tool_call/tool_result dispatcher (FR-005)
│   │   │   ├── pendingCallRegistry.ts         # NEW — TUI-side futures registry (FR-001-FR-004 backing)
│   │   │   └── dispatchPrimitive.test.ts      # NEW — bun test unit
│   │   ├── LookupPrimitive/LookupPrimitive.ts # MODIFY — replace stub call() (FR-001)
│   │   ├── VerifyPrimitive/VerifyPrimitive.ts # MODIFY — replace stub call() (FR-002 + FR-009 — forward shape unchanged)
│   │   ├── SubmitPrimitive/SubmitPrimitive.ts # MODIFY — replace stub call() (FR-003)
│   │   └── SubscribePrimitive/SubscribePrimitive.ts # MODIFY — replace stub call() (FR-004)
│   └── ipc/llmClient.ts                       # MODIFY — add tool_result frame route to pendingCallRegistry (FR-001-FR-004 wiring)
├── tests/
│   ├── unit/
│   │   └── test_verify_canonical_map_parser.py    # NEW — FR-008b regression
│   ├── integration/
│   │   ├── test_tui_primitive_dispatch_e2e.py     # NEW — FR-016 + FR-014/15
│   │   ├── test_tool_id_to_family_hint_translation.py  # NEW — US3 (10 parametrised + 1 unknown)
│   │   └── test_all_15_mocks_invoked.py            # NEW — FR-020 + SC-004
│   └── fixtures/
│       └── citizen_chains/                         # NEW — 10 fixture JSON files (FR-019)
│           ├── modid.json
│           ├── kec.json
│           ├── geumyung_module.json
│           ├── simple_auth_module.json
│           ├── any_id_sso.json
│           ├── gongdong_injeungseo.json
│           ├── geumyung_injeungseo.json
│           ├── ganpyeon_injeung.json
│           ├── mobile_id.json
│           └── mydata.json
└── docs/
    ├── research/
    │   └── policy-mapping.md                       # NEW — FR-017 + SC-009
    └── scenarios/
        ├── hometax-tax-filing.md                   # NEW — FR-018 + SC-010
        ├── gov24-minwon-submit.md                  # NEW — FR-018 + SC-010
        ├── mobile-id-issuance.md                   # NEW — FR-018 + SC-010
        ├── kec-yessign-signing.md                  # NEW — FR-018 + SC-010
        └── mydata-live.md                          # NEW — FR-018 + SC-010
```

**Structure Decision**: Hybrid Python backend + TUI subtree. The new files cluster into 4 logical groups:
1. **Backend schema fix** (Phase 0a, 1 sonnet teammate, ≤3 files): `src/kosmos/tools/mvp_surface.py` (modify) + `src/kosmos/tools/verify_canonical_map.py` (new) + `tests/unit/test_verify_canonical_map_parser.py` (new) + `tests/integration/test_tool_id_to_family_hint_translation.py` (new).
2. **TUI dispatcher wiring** (Phase 0b, 1 sonnet teammate, ≤8 files): `tui/src/tools/_shared/{dispatchPrimitive,pendingCallRegistry}.ts` (new) + 4 primitive `.ts` modify + `tui/src/ipc/llmClient.ts` modify + 1 unit test.
3. **Smoke harness + integration tests** (Phase 1a, 1 sonnet teammate, ≤7 files): 2 scripts (`.expect` + `.tape`) + 2 integration tests + 10-fixture battery.
4. **Docs** (Phase 1b, Lead solo, ≤6 files): policy-mapping.md + 5 OPAQUE scenario docs.

This matches AGENTS.md § Agent Teams Sonnet teammate dispatch unit (≤5 task / ≤10 file). Detailed dispatch tree lives in `dispatch-tree.md` (authored at `/speckit-implement` time per Lead workflow).

## Complexity Tracking

> No Constitution Check violations. This section is empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | (n/a)      | (n/a)                                |
