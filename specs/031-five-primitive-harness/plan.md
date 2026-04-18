# Implementation Plan: Five-Primitive Harness Redesign

**Branch**: `031-five-primitive-harness` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/031-five-primitive-harness/spec.md`

## Summary

Collapse the KOSMOS main tool surface to **5 domain-agnostic primitives** — `lookup`, `resolve_location`, `submit`, `subscribe`, `verify` — mirroring Claude Code's always-loaded 5-tool philosophy (`Grep` / `Read` / `Glob` / `Bash` / `Edit`). `submit` absorbs the rejected 8-verb writers (pay / issue_certificate / submit_application / reserve_slot / check_eligibility) under one envelope `{tool_id, params}`. `verify` publishes the 18 ratified Korean `published_tier` labels across 6 authentication families (`gongdong_injeungseo`, `geumyung_injeungseo`, `ganpyeon_injeung`, `digital_onepass`, `mobile_id`, `mydata`) with `nist_aal_hint` as advisory secondary axis. `subscribe` unifies 3GPP CBS broadcast + REST polling + RSS 2.0 under one `AsyncIterator`, deliberately with no inbound webhook. `lookup` / `resolve_location` remain byte-identical to Spec 022. Ministry knowledge is confined to `src/kosmos/tools/<ministry>/<adapter>.py`. KOSMOS operates no CA / HSM / VC issuer — `verify` delegates exclusively to external Korean national infrastructure (harness-not-reimplementation). Mock scope is 6 mirror-able systems in `docs/mock/`; 3 OPAQUE journeys live in `docs/scenarios/` only.

**Primary migration source**: `.references/claude-code-sourcemap/restored-src/src/tools/{GrepTool,FileReadTool,GlobTool,BashTool}.ts` + `restored-src/src/services/{oauth,SessionMemory}/` (Constitution §I; see [research.md](./research.md) §1).

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no version bump).
**Primary Dependencies**: `pydantic >= 2.13` (frozen models + discriminated unions, existing), `pydantic-settings >= 2.0` (env catalog, existing), `httpx >= 0.27` (async HTTP for REST-pull adapters, existing), `opentelemetry-sdk` / `opentelemetry-semantic-conventions` (OTEL emission from Spec 021, existing), `pytest` + `pytest-asyncio` (existing). Stdlib `asyncio` / `uuid` / `hashlib` / `datetime` / `pathlib` for SubscriptionHandle lifetime + transaction_id derivation. **No new runtime dependencies** — AGENTS.md hard rule (SC-008).
**Storage**: N/A at this spec layer. `AdapterRegistration` lives in in-memory registry (rebuilt at process boot from `kosmos.tools.*` module imports). `ToolCallAuditRecord` persistence is Spec 024 territory (out of scope here). `SubscriptionHandle` state is session-lifetime in-memory; CBS event de-dup and RSS `guid` cache are per-handle only.
**Testing**: `uv run pytest` (existing). Contract tests under `tests/unit/primitives/{submit,subscribe,verify}/`; integration tests under `tests/integration/` exercising discriminated-union dispatch + `published_tier` enforcement; docs-lint tests in `tests/test_mock_scenario_split.py` enforcing `docs/mock/` = 6 subdirs and `docs/scenarios/` = 3 journeys. `@pytest.mark.live` gated live-API tests MUST NOT run in CI (AGENTS.md).
**Target Platform**: Linux / macOS developer workstations + GitHub-hosted Ubuntu CI runners (Python 3.12). No platform-specific constructs introduced.
**Project Type**: Single Python package (`src/kosmos/`) + docs + tests. `tools/` subtree extended with 5-primitive surface; no new top-level layout decisions.
**Performance Goals**: Primitive dispatch overhead ≤ 5 ms p95 excluding adapter work (consistent with Spec 022 baseline). `subscribe` backpressure threshold per-handle ≥ 64 pending events before structured `SubscriptionBackpressureDrop` emission.
**Constraints**: Fail-closed defaults (Constitution §II): `requires_auth=True`, `is_personal_data=True`, `is_concurrency_safe=False`, `cache_ttl_seconds=0`. No `Any` in I/O schemas (Constitution §III). 18-label `published_tier` enum is closed in v1; extensions require spec amendment. `verify` holds no signing keys; all family variants carry only `external_session_ref` (opaque handle).
**Scale/Scope**: 5 primitives · 6 authentication families · 18 published_tier labels · 4 preserved Spec 022 adapters + N new `submit` / `subscribe` / `verify` adapters (shipped incrementally post-v1 per Deferred Items). Mock docs = 6 systems; scenario docs = 3 OPAQUE journeys.

## Constitution Check

Evaluated against `.specify/memory/constitution.md` v1.1.1. All six principles pass — no justified violations.

| Principle | Evaluation |
|---|---|
| **I. Reference-Driven Development** | PASS. Every primitive mapped to `restored-src/src/tools/*.ts` or `restored-src/src/services/*/` in [research.md §1](./research.md#1-reference-map). `subscribe` + `verify` escalations to secondary refs (AutoGen mailbox / OpenAI Agents SDK) documented with rationale. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | PASS. `AdapterRegistration` defaults: `requires_auth=True`, `is_personal_data=True`, `is_concurrency_safe=False`, `cache_ttl_seconds=0`. `verify.family_mismatch` → structured error; coercion prohibited (FR-010). FR-038 PII invariant preserved from `registry.py`. |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | PASS. All I/O schemas in [data-model.md](./data-model.md) use `ConfigDict(frozen=True, extra="forbid")` + discriminated unions. `params: dict[str, object]` on main surface is NOT `Any` (adapter owns typed model). `search_hint` required on every adapter (Constitution §III). |
| **IV. Government API Compliance** | PASS. Spec 022 adapters preserved unchanged (FR-018). New `subscribe` REST-pull adapters will carry `rate_limit_per_minute`. No live `data.go.kr` calls in CI — fixture-only mocks. |
| **V. Policy Alignment** | PASS. Principle 8 (single conversational window) reinforced by primitive-purity; Principle 9 (Open API / OpenMCP) compatible — each primitive has a JSON Schema export under `contracts/`. PIPA 7-step gauntlet unchanged; dual-axis `(published_tier_minimum, nist_aal_hint)` sharpens the identity-verification step. |
| **VI. Deferred Work Accountability** | PASS. 9 items in spec §Scope Boundaries; 7 carry `NEEDS TRACKING` and will be backfilled by `/speckit-taskstoissues`. No free-text "future phase" references without table entries. |

**Gate verdict**: PASS (both pre-research and post-design).

## Project Structure

### Documentation (this feature)

```
specs/031-five-primitive-harness/
├── plan.md                              # This file
├── research.md                          # Phase 0 — reference map + 18-label ratification + mock/scenario split
├── data-model.md                        # Phase 1 — Pydantic v2 schemas for all 5 primitives + AdapterRegistration
├── quickstart.md                        # Phase 1 — contributor onboarding, smoke-test checklist
├── contracts/                           # Phase 1 — JSON Schema Draft 2020-12 exports
│   ├── README.md
│   ├── submit.input.schema.json
│   ├── submit.output.schema.json
│   ├── subscribe.input.schema.json
│   ├── subscribe.output.schema.json
│   ├── verify.input.schema.json
│   ├── verify.output.schema.json
│   └── adapter_registration.schema.json
├── checklists/                          # Pre-existing requirement-quality checklists
└── tasks.md                             # Phase 2 output — created by /speckit-tasks (NOT by this command)
```

`lookup` / `resolve_location` contracts are preserved byte-identical from [`specs/022-mvp-main-tool/contracts/`](../../022-mvp-main-tool/contracts/) per FR-016 / FR-017; no copy under Spec 031 — contracts/README.md links to Spec 022.

### Source Code (repository root)

```
src/kosmos/
├── primitives/                          # NEW — 5-primitive surface
│   ├── __init__.py                      # exports lookup, resolve_location, submit, subscribe, verify
│   ├── submit.py                        # SubmitInput / SubmitOutput + dispatcher
│   ├── subscribe.py                     # SubscribeInput / SubscriptionHandle + modality muxer
│   ├── verify.py                        # VerifyInput / AuthContext discriminated union + family dispatcher
│   └── (lookup.py + resolve_location.py re-exported from existing Spec 022 modules)
├── tools/
│   ├── registry.py                      # EXISTING — extended with AdapterRegistration.primitive + published_tier_minimum + nist_aal_hint
│   ├── koroad/ · kma/ · hira/ · nmc/    # EXISTING — 4 Spec 022 adapters preserved unchanged (FR-018)
│   └── mock/                            # NEW parallel tree for mock adapters
│       ├── data_go_kr/
│       ├── omnione/
│       ├── barocert/
│       ├── mydata/
│       ├── npki_crypto/
│       └── cbs/
└── security/
    └── v12_dual_axis.py                 # NEW — AdapterRegistration post-init backstop enforcing FR-030 on/after v1.2 GA

tests/
├── unit/
│   ├── primitives/
│   │   ├── submit/test_dispatch.py      # Envelope purity + AdapterNotFoundError path
│   │   ├── subscribe/test_muxer.py      # 3-modality routing + lifetime boundedness
│   │   └── verify/test_discriminator.py # 6-family coercion-free dispatch
│   ├── security/test_v12_dual_axis.py   # FR-030 backstop
│   └── registry/test_tool_id_collision.py  # FR-020
├── integration/
│   ├── test_submit_published_tier_gate.py  # SC-005
│   └── test_subscribe_lifetime_expiry.py   # FR-014
├── lint/
│   ├── test_no_legacy_verbs.py          # SC-010
│   └── test_submit_banned_words.py      # SC-002
└── test_mock_scenario_split.py          # SC-004

docs/
├── mock/                                # NEW — exactly 6 subdirs (stubbed; content build-out deferred per spec §Deferred Items)
│   ├── data_go_kr/{README.md, fixtures/, adapters/}
│   ├── omnione/
│   ├── barocert/
│   ├── mydata/
│   ├── npki_crypto/
│   └── cbs/
├── scenarios/                           # NEW — exactly 3 OPAQUE journey docs (stubbed)
│   ├── gov24_submission.md
│   ├── kec_xml_signature.md
│   └── npki_portal_session.md
└── security/
    └── tool-template-security-spec-v1.md  # EXISTING — v1.2 bump deferred to a follow-up PR per spec §Deferred Items (NEEDS TRACKING)
```

**Structure Decision**: Single-project layout. The `src/kosmos/primitives/` directory is the only net-new top-level addition. `tools/` gains the `mock/` subtree; all existing Spec 022 adapters keep their paths. `docs/mock/` and `docs/scenarios/` are new documentation roots enforced by `tests/test_mock_scenario_split.py`. No `backend/` + `frontend/` split — TUI Epic #287 is tracked separately and does not share this spec's layout.

## Complexity Tracking

No Constitution violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
