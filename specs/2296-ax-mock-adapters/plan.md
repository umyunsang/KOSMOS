# Implementation Plan: AX-Infrastructure Mock Adapters & Adapter-Manifest IPC Sync

**Branch**: `2296-ax-mock-adapters` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2296-ax-mock-adapters/spec.md`

## Summary

Ship 10 Mock adapters that mirror the LLM-callable secure-wrapping channels Korea's national AX policy stack (국가인공지능전략위원회 행동계획 2026-2028 + 공공AX + 범정부 AI 공통기반) is mandating, plus the `DelegationToken` / `DelegationContext` schema that captures the OID4VP-style envelope those channels are expected to issue. Piggyback Codex P1 #2395 by emitting an `adapter_manifest_sync` IPC frame at backend boot so the TS-side primitive `validateInput` can resolve any backend adapter ID (not just the 14 internal TS tools) and populate the citation slot from the agency-published policy URL.

**Technical approach**: Extend the existing per-primitive sub-registry pattern (`kosmos.primitives.{verify,submit,subscribe}._ADAPTER_REGISTRY` from Spec 031) with the new `mock_*_module_*` adapters; introduce one new `IPCFrame` arm (`AdapterManifestSyncFrame`) in `kosmos.ipc.frame_schema` reusing the Spec 032 envelope; cache the synced manifest in a new TS-side `tui/src/services/api/adapterManifest.ts` module; modify the four `*Primitive.validateInput` methods to consult the cached manifest before falling back to `context.options.tools.find`. Audit ledger gains three new event kinds appended to the existing Spec 035 consent JSONL (`delegation_issued/used/revoked`).

## Technical Context

**Language/Version**: Python 3.12+ (backend baseline, no version bump) · TypeScript 5.6+ on Bun v1.2.x (TUI, existing Spec 287 stack)
**Primary Dependencies**:
- Python: `pydantic >= 2.13` (frozen models, discriminated union — existing); `pydantic-settings >= 2.0` (env catalog — existing); `httpx >= 0.27` (carry-over, no new use); `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans — existing); `pytest` + `pytest-asyncio` (existing test stack)
- TypeScript: `ink`, `react`, `@inkjs/ui`, `string-width`, `zod ^3.23` (resolves to 3.25.76, ships `zod/v4` namespace — existing); `@modelcontextprotocol/sdk` (existing). **Zero new runtime deps** (AGENTS.md hard rule + spec FR-023).
**Storage**:
- In-memory at runtime: per-primitive `_ADAPTER_REGISTRY` (Spec 031), main `ToolRegistry` (Spec 022), TS-side adapter-manifest cache (new, ephemeral)
- Append-only on disk: Spec 035 consent ledger at `~/.kosmos/memdir/user/consent/` gains `delegation_*` event kinds; session JSONL transcripts at `~/.kosmos/memdir/user/sessions/` (Spec 027 unchanged)
- No new schemas on disk
**Testing**: `uv run pytest` (Python — happy + error per adapter, IPC frame round-trip, registry-wide transparency scan, scope-violation regression); `bun test` (TS — manifest cache + primitive validateInput resolution + cold-boot race); PTY scenario via `expect` (Layer 2); vhs `.tape` with three Screenshot keyframes (Layer 4 mandate)
**Target Platform**: Single-user terminal (KOSMOS TUI); Python backend speaks JSONL frames over stdio to TS-side TUI process
**Project Type**: Multi-package monorepo (Python backend + TypeScript TUI sibling)
**Performance Goals**:
- US1 end-to-end chain (verify → lookup → submit) under 30 seconds wall-clock on developer machine (SC-001)
- Manifest sync frame ≤ 4 KB on the wire for the current 28-adapter target
- `validateInput` lookup against synced manifest under 5 ms (in-memory map)
**Constraints**:
- Zero new runtime dependencies (FR-023, AGENTS.md hard rule, SC-008)
- All new source text English; Korean only in domain-data fields (FR-024)
- IPC frame variant MUST be a NEW arm (Spec 032 ring-buffer replay invariant)
- Each Mock adapter MUST cite an agency-published policy URL — no KOSMOS-invented classifications (FR-025, Constitution § II)
- Mock backend for PTY smoke is a real Python process speaking JSONL — NOT `KOSMOS_BACKEND_CMD=sleep 60` (FR-021, closes Codex P1 PTY-coverage gap)
**Scale/Scope**:
- Adapter count target after merge: ≈ 20 distinct Mock adapter surfaces across four sub-registries (10 verify + 5 submit + 3 subscribe + 2 lookup) plus 14 main-ToolRegistry entries (12 Live + 2 MVP-surface). Manifest frame size scales linearly; chunking deferred (see spec § Deferred Items).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|---|---|---|
| **I. Reference-Driven Development** | ✅ PASS | Each design decision maps to a concrete reference (see Reference Mapping table below). DelegationToken envelope mirrors OID4VP draft 21 + Singapore Myinfo (`delegation-flow-design.md § 3.1, 5.6`). IPC frame variant follows Spec 032 + restored-src CC pattern. Per-primitive sub-registry pattern is Spec 031 prior art. |
| **II. Fail-Closed Security** | ✅ PASS | Every Mock adapter MUST cite agency-published policy URL in `_policy_authority` (FR-025). No KOSMOS-invented classifications. The `mock_verify_module_any_id_sso` returns identity-only, NOT a delegation token (per `delegation-flow-design.md § 2.2` constraint). Cold-boot manifest race fails closed (FR-019). Token expiry/scope/session violations all fail closed (FR-009/010/011). |
| **III. Pydantic v2 Strict Typing** | ✅ PASS | New `DelegationToken`, `DelegationContext`, `AdapterManifestEntry`, `AdapterManifestFrame` are frozen Pydantic v2 models. Existing per-primitive context types (`MobileIdContext`, etc.) extend with frozen fields — no `Any` introduced. |
| **IV. Government API Compliance** | ✅ PASS | All 10 new adapters are Mock — no live `data.go.kr` calls. Existing `rate_limit_per_minute` field on `AdapterRegistration` carries through (verify_mobile_id.py:34 reference). Happy + error path tests required per FR-006. No hardcoded credentials. |
| **V. Policy Alignment** | ✅ PASS | KOSMOS = "client-side reference implementation for Korea's national AX infrastructure" framing aligns with Principle 8 (single conversational window) and Principle 9 (Open API/OpenMCP). The `_policy_authority` transparency field is the visible artefact for Public AI Impact Assessment 과제 54. |
| **VI. Deferred Work Accountability** | ✅ PASS | Spec § "Scope Boundaries & Deferred Items" populated with 6 entries: 2 cite tracking issues (#2297, #2298), 4 marked NEEDS TRACKING for `/speckit-taskstoissues`. No free-text "future epic" references in spec prose. |

**Reference Mapping** (mandatory per Constitution § I):

| Decision | Primary reference | Secondary reference |
|---|---|---|
| 5-primitive harness preserved (lookup/submit/verify/subscribe + resolve_location) | Spec 031 (Five-Primitive Harness) | Spec 022 (MVP Main-Tool) |
| Per-primitive `_ADAPTER_REGISTRY` pattern for new mock adapters | Spec 031 prior art (`kosmos.tools.mock.__init__.py` 6 verify + 2 submit + 3 subscribe) | Pydantic AI schema-driven registry |
| `DelegationToken` shape (vp_jwt, delegation_token, scope, expires_at, issuer_did) | OID4VP draft 21 (`delegation-flow-design.md § 5.6`) | Singapore Myinfo + APEX (`delegation-flow-design.md § 3.1`) |
| Six transparency fields contract | `delegation-flow-design.md § 12.7` (3rd correction final canonical) | Estonia X-Road audit-by-design pattern |
| New `IPCFrame` arm for adapter manifest | Spec 032 (envelope hardening, 20-arm union) | restored-src CC tool registry sync pattern |
| TS-side primitive `validateInput` two-tier resolution (synced manifest first, then internal-tools fallback) | Spec 2294 (5-primitive align with CC Tool.ts) — same `validateInput` signature | restored-src `getAllBaseTools()` |
| Audit ledger `delegation_*` event kinds | Spec 035 (onboarding-brand-port consent JSONL) — same append-only path | Constitution § II fail-closed |
| Mock-fixture backend for PTY smoke | `feedback_pr_pre_merge_interactive_test` + `feedback_vhs_tui_smoke` (auto-memory) | AGENTS.md § TUI verification (vhs Layer 4 mandate) |

## Project Structure

### Documentation (this feature)

```text
specs/2296-ax-mock-adapters/
├── plan.md                     # This file
├── research.md                 # Phase 0 output — registry/architecture discoveries + reference mapping
├── data-model.md               # Phase 1 output — DelegationToken, AdapterManifestFrame, AuditLedgerEvent
├── quickstart.md               # Phase 1 output — citizen-facing US1 chain run instructions
├── checklists/
│   └── requirements.md         # Spec quality checklist (already created)
├── contracts/
│   ├── ipc-adapter-manifest-frame.md     # New IPC arm contract
│   ├── mock-adapter-response-shape.md    # Six transparency fields + delegation token consumption
│   └── delegation-token-envelope.md      # DelegationToken/Context envelope schema
├── spec.md                     # Spec (already authored)
└── tasks.md                    # Phase 2 output — created by /speckit-tasks (NOT by this command)
```

### Source Code (repository root)

```text
src/kosmos/
├── primitives/
│   ├── delegation.py                   # NEW — DelegationToken + DelegationContext (FR-007/008)
│   ├── verify.py                       # MODIFY — extend per-family context types with transparency fields
│   ├── submit.py                       # MODIFY — accept DelegationContext, enforce scope/expiry/session (FR-009/010/011)
│   └── subscribe.py                    # unchanged for this Epic
├── tools/
│   ├── mock/
│   │   ├── __init__.py                                          # MODIFY — add 10 new imports, drop digital_onepass
│   │   ├── verify_digital_onepass.py                            # DELETE (FR-004)
│   │   ├── verify_module_simple_auth.py                         # NEW (FR-001)
│   │   ├── verify_module_modid.py                               # NEW (FR-001)
│   │   ├── verify_module_kec.py                                 # NEW (FR-001)
│   │   ├── verify_module_geumyung.py                            # NEW (FR-001)
│   │   ├── verify_module_any_id_sso.py                          # NEW (FR-001) — identity-only, NO delegation token
│   │   ├── submit_module_hometax_taxreturn.py                   # NEW (FR-002)
│   │   ├── submit_module_gov24_minwon.py                        # NEW (FR-002)
│   │   ├── submit_module_public_mydata_action.py                # NEW (FR-002)
│   │   ├── lookup_module_hometax_simplified.py                  # NEW (FR-003) — main ToolRegistry GovAPITool
│   │   └── lookup_module_gov24_certificate.py                   # NEW (FR-003) — main ToolRegistry GovAPITool
│   ├── register_all.py                                          # MODIFY — import kosmos.tools.mock for production registry boot
│   └── transparency.py                                          # NEW — six-field stamping helper used by every Mock adapter
├── ipc/
│   ├── frame_schema.py                                          # MODIFY — add AdapterManifestSyncFrame + extend IPCFrame union (20→21 arms)
│   └── adapter_manifest_emitter.py                              # NEW — backend-side boot emitter walking ToolRegistry + sub-registries
└── memdir/
    └── consent_ledger.py                                        # MODIFY — three new event-kind helpers (delegation_issued/used/revoked)

tui/src/
├── services/api/
│   └── adapterManifest.ts                                       # NEW — ephemeral cache + replace-on-frame logic (FR-016)
├── tools/
│   ├── LookupPrimitive/LookupPrimitive.ts                       # MODIFY — validateInput two-tier resolution (FR-017/018)
│   ├── SubmitPrimitive/SubmitPrimitive.ts                       # MODIFY — same
│   ├── VerifyPrimitive/VerifyPrimitive.ts                       # MODIFY — same
│   ├── SubscribePrimitive/SubscribePrimitive.ts                 # MODIFY — same
│   └── shared/primitiveCitation.ts                              # MODIFY — accept manifest-derived citation slot

tests/
├── unit/
│   ├── primitives/
│   │   ├── test_delegation_token.py                             # NEW — scope/expiry/session invariants (FR-009/010/011)
│   │   ├── test_verify_module_*.py (5 files)                    # NEW — happy + error per new mock
│   │   └── test_submit_module_*.py (3 files)                    # NEW — same
│   ├── ipc/
│   │   └── test_adapter_manifest_sync_frame.py                  # NEW — frame round-trip + 21-arm union
│   └── tools/
│       ├── test_lookup_module_hometax_simplified.py             # NEW
│       ├── test_lookup_module_gov24_certificate.py              # NEW
│       └── test_mock_transparency_scan.py                       # NEW — registry-wide six-field assertion (FR-006)
└── integration/
    ├── test_e2e_citizen_taxreturn_chain.py                      # NEW — US1 acceptance (verify→lookup→submit)
    └── test_codex_p1_adapter_resolution.py                      # NEW — US2 (real backend adapter ID resolves end-to-end)

tui/tests/
├── adapterManifest.test.ts                                      # NEW — cache replace + cold-boot race (FR-019)
├── primitive/
│   ├── lookup-validation-fallback.test.ts                       # NEW — synced manifest → internal-tools fallback chain
│   └── submit-citation-from-manifest.test.ts                    # NEW — citation slot populated from manifest URL

specs/2296-ax-mock-adapters/scripts/
├── smoke-citizen-taxreturn.expect                               # NEW — Layer 2 PTY scenario (FR-021)
└── smoke-citizen-taxreturn.tape                                 # NEW — Layer 4 vhs tape with 3 Screenshot keyframes (FR-022)
```

**Structure Decision**: Multi-package monorepo (Python backend `src/kosmos/` + TS TUI `tui/src/`). New code lives in three locations matching the existing layering: (a) Python adapter implementations under `src/kosmos/tools/mock/` extending the Spec 031 sub-registry pattern; (b) Python IPC frame variant in `src/kosmos/ipc/frame_schema.py` extending the 20-arm union; (c) TS adapter-manifest cache + four primitive `validateInput` modifications under `tui/src/`. Tests parallel each layer.

## Reference Mapping & Reuse Plan

This Epic is small in code but high in invariant preservation. The Phase 0 research surfaced one major correction to the spec's count math (see `research.md § Decision 1`); the cleanest plan-time response is to update SC-003 in the spec to reflect the actual sub-registry architecture before `/speckit-analyze`. Reuse plan:

- **Spec 031 sub-registry pattern**: Five new verify mocks call `register_verify_adapter("family", invoke)` exactly like `verify_mobile_id.py:61`. Three new submit mocks call `register_submit_adapter()`. Two new lookup mocks register with the main `ToolRegistry` via `AdapterRegistration` (lookup adapters are GovAPITools, not per-primitive sub-adapters).
- **Spec 032 IPC envelope**: New `AdapterManifestSyncFrame` extends `_BaseFrame`, gets a `kind: Literal["adapter_manifest_sync"]` discriminator, joins the `IPCFrame` union at `frame_schema.py:964` (between `PluginOpFrame` and the closing bracket → 21 arms total).
- **Spec 035 consent ledger**: Three new event kinds (`delegation_issued`, `delegation_used`, `delegation_revoked`) get a typed Pydantic union member; the JSONL append path is unchanged.
- **Spec 022 ToolRegistry + BM25**: Two new lookup mock adapters get bilingual `search_hint` (Korean + English). BM25 index rebuilt at boot, no new infrastructure.
- **Spec 2294 primitive shape contract**: `validateInput` signature unchanged; only the resolution body modified.

## Complexity Tracking

> No constitution gates failed. No complexity to track.

The two minor architectural extensions — one new IPC frame arm and one helper function for transparency-field stamping — sit cleanly inside existing patterns. Adding the new frame arm preserves Spec 032's discriminated-union replay invariant because all 21 arms remain ordered and discriminator-tagged.

## Phase 0: Outline & Research — completed

See [research.md](./research.md) for the resolved unknowns. Key decisions:

1. **Mock-count reconciliation**: The spec's "27 = 12 Live + 15 Mock" arithmetic does not survive Phase 0 because per-primitive sub-registries hold most mocks (not the main `ToolRegistry`). Correction folded into spec SC-003 amendment (this plan triggers a minor spec edit before `/speckit-analyze`).
2. **Mock catalog: ADD alongside, do NOT delete existing 5 verify mocks**: Existing 5 verify mocks (after onepass deletion) keep their tool IDs and gain transparency fields per FR-005 retrofit. New 5 mocks ship under the `mock_verify_module_*` prefix to make the AX-channel-reference framing visible in the ID.
3. **IPC frame: NEW arm, NOT extend existing**: Confirmed. Adding a new arm preserves the Spec 032 ring-buffer replay invariant; extending an existing arm would break correlation-id ordering.
4. **Mock-fixture backend pattern for PTY smoke**: Spawn a real Python process via `KOSMOS_BACKEND_CMD=python -m kosmos.ipc.demo.mock_backend` (new module). The process speaks the same JSONL frames the production backend speaks, but with deterministic mock fixtures for the US1 chain.
5. **Deferred-item validation**: All 6 entries in the spec's deferred-items table either have a tracking issue (#2297, #2298) or are flagged `NEEDS TRACKING` for `/speckit-taskstoissues`. No untracked deferrals remain.

## Phase 1: Design & Contracts — completed

See [data-model.md](./data-model.md), [contracts/](./contracts/), and [quickstart.md](./quickstart.md). Summary:

- **data-model.md**: Five entities formalised — `DelegationToken`, `DelegationContext`, `AdapterManifestEntry`, `AdapterManifestFrame`, `DelegationLedgerEvent` (union of `delegation_issued/used/revoked`).
- **contracts/ipc-adapter-manifest-frame.md**: Full `AdapterManifestSyncFrame` JSON shape + invariants + 21-arm union impact.
- **contracts/mock-adapter-response-shape.md**: Six transparency fields' types, allowed values, retrofit checklist for existing 5 verify mocks.
- **contracts/delegation-token-envelope.md**: Token issuance/consumption invariants.
- **quickstart.md**: Citizen-facing run-through of the US1 chain, including expected ledger-line shapes and the precise `expect` command sequence.

Agent context (`CLAUDE.md` Active Technologies block) updated below by this command.
