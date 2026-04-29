# Implementation Plan: System Prompt Rewrite — 4-Primitive Vocabulary + Citizen Chain Teaching

**Branch**: `2298-system-prompt-rewrite` | **Date**: 2026-04-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2298-system-prompt-rewrite/spec.md`

## Summary

The current `prompts/system_v1.md` line 14 hard-locks the LLM to two callable tools (`resolve_location` + `lookup`). After Epic ε #2296 wired the verify/submit/subscribe primitives + 5 new verify-module mocks, the LLM cannot start any citizen OPAQUE-domain chain because it does not know `verify`, `submit`, or `subscribe` exist — producing the post-ε infinite "Hatching… / Boogieing…" spinner whenever a citizen submits requests like `내 종합소득세 신고해줘`. This Epic rewrites `prompts/system_v1.md` to teach the LLM (a) the **4 reserved primitives + `resolve_location` = 5 callable tools**, (b) the **10 active verify families** + canonical AAL hint per family, (c) the **citizen verify→lookup→submit chain pattern** with a worked modid → hometax-simplified → hometax-taxreturn example, (d) the **delegation token vocabulary** (scope grammar `<verb>:<adapter_family>.<action>`, comma-joined multi-scope, bilingual `purpose_ko/en`). The rewrite preserves all Spec 2152 XML scaffolding tags, all Spec 035/2295 citizen-data carry-forward rules, and the Spec 026 manifest fail-closed boot guard. Five new shadow-eval fixtures cover the 5 Epic ε families; the existing 8 lookup-only fixtures must regress 0. A vhs Layer 4 visual smoke + PTY Layer 2 expect smoke verify the chain end-to-end on the rewritten prompt.

**Technical approach**: Single-file Markdown rewrite + manifest YAML SHA-256 update + 5 shadow-eval fixture additions + 2 smoke scripts + 1 PTY log. **No Python/TS source edits in this Epic** — `tui/src/**` and `src/kosmos/**` are read-only inputs. The schema-level gap (FamilyHint Literal + VerifyOutput.result discriminator each missing the 5 Epic ε families) is explicitly deferred to Epic ζ #2297 per spec.md § Deferred Items — the verify dispatcher takes plain `str` so prompt-only teaching functions correctly without Literal expansion.

## Technical Context

**Language/Version**: Python 3.12+ (backend, no edits this Epic) · TypeScript 5.6+ on Bun v1.2.x (TUI, no edits this Epic). Markdown 1.0.1 + YAML 1.2 for the rewritten prompt + manifest.

**Primary Dependencies**: All existing — `pydantic >= 2.13` (PromptManifest schema, no change), `pydantic-settings >= 2.0` (env catalog, no change), `pytest` + `pytest-asyncio` (existing test stack for shadow-eval fixture loader), stdlib `hashlib` (SHA-256 recompute via `shasum -a 256` shell tool), stdlib `xml.etree.ElementTree` (SC-005 XML well-formedness check). **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR-018 + SC-007).

**Storage**: N/A. The rewritten `prompts/system_v1.md` is loaded into the existing `PromptLoader` immutable in-memory cache at process boot (Spec 026, unchanged). The `prompts/manifest.yaml` SHA-256 entry is the only persistent contract recomputed. No database, no new on-disk schema. Consent ledger writes (US1 chain) reuse the existing `~/.kosmos/memdir/user/consent/<YYYY-MM-DD>.jsonl` Spec 035 surface.

**Testing**: `uv run pytest tests/integration/test_e2e_citizen_taxreturn_chain.py` for chain assertions (existing); `uv run pytest tests/integration/test_verify_module_dispatch.py` for the 6 dispatch tests (existing); a new fixture loader test at `tests/integration/test_shadow_eval_citizen_chain_fixtures.py` for the 5 new fixtures (created this Epic); `bash specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect` for PTY Layer 2 (created this Epic); `vhs specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape` for Layer 4 (created this Epic).

**Target Platform**: macOS 14+ (developer / user) · Linux (CI). The vhs binary version requirement is ≥ 0.11 (per AGENTS.md § Layer 4 — `Screenshot` directive support).

**Project Type**: Single-project monorepo with TUI subtree. This Epic touches only `prompts/`, `tests/fixtures/`, and `specs/2298-system-prompt-rewrite/` paths.

**Performance Goals**: The rewritten prompt MUST stay within FriendliAI K-EXAONE prompt-cache budget. Current `system_v1.md` is 28 lines / ~2 KB; expansion budget +50 lines / +4 KB to ~6 KB total. Hard ceiling: 8 KB (10 % cushion under the existing prompt-cache TTL break-even). Spec 026's `kosmos.prompt.hash` OTEL attribute will reflect the new SHA-256 on every assistant turn.

**Constraints**: System prompt must be deterministic (no Jinja-style templating beyond the existing `{platform_name}` substitution at line 2). The rewrite MUST NOT introduce new template variables. The rewrite MUST NOT touch any other file under `prompts/` (`compact_v1.md` and `session_guidance_v1.md` are out of scope — their SHA-256 entries in `manifest.yaml` are not edited).

**Scale/Scope**: ~50 LOC delta in `prompts/system_v1.md` (28 → ~80 lines). 1 LOC delta in `prompts/manifest.yaml` (SHA-256 hex). 5 new fixture files (~20 LOC each). 1 vhs `.tape` (~30 LOC). 1 expect script (~50 LOC). 1 PTY log (auto-generated, ~50–200 lines). Total spec dir delta: ~9 files, ~200 LOC.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| **I. Reference-Driven Development** | Every rewrite section maps to a concrete reference (CC restored-src is irrelevant for prompt content; primary references are Spec 2152 + Spec 026 + Spec 2296 contracts + Spec 031 verify primitive + Spec 035 consent ledger). Mapping documented in research.md § R-1. | PASS |
| **II. Fail-Closed Security** | Rewrite cites agency policy (each verify family lists its real-domain reference per FR-002); no KOSMOS-invented permission classifications introduced; OPAQUE-forever fallback preserved (FR-011); `<PermissionRequest>` pipeline untouched (no TUI changes). | PASS |
| **III. Pydantic v2 Strict Typing** | No new tool I/O schemas authored this Epic. Existing schemas (`VerifyInput`, `VerifyOutput`) noted for deferred expansion in Epic ζ. Shadow-eval fixtures use Pydantic v2 schema authored at `tests/fixtures/shadow_eval/citizen_chain/_schema.py` (new file, ≤30 LOC). | PASS |
| **IV. Government API Compliance** | No live `data.go.kr` calls in tests (PTY smoke runs against Mock adapters only); no hardcoded keys; existing `KOSMOS_*` env catalog unchanged. | PASS |
| **V. Policy Alignment** | Citizen chain teaching directly serves Principle 8 (single conversational window) + Principle 9 (Open API integration). Principle 5 (no paper, consent-based) is upheld by the unchanged Spec 035 consent ledger writes during the chain. | PASS |
| **VI. Deferred Work Accountability** | spec.md § "Scope Boundaries & Deferred Items" lists 6 deferred items; all have target Epic/Phase. 5 carry "NEEDS TRACKING" — to be resolved by `/speckit-taskstoissues`. The `FamilyHint` / `VerifyOutput` schema gap is explicitly deferred to Epic ζ #2297. | PASS |

**Verdict**: All 6 principles PASS pre-research. No violations require justification in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/2298-system-prompt-rewrite/
├── spec.md                                    # COMPLETE (172 lines)
├── plan.md                                    # THIS FILE
├── research.md                                # Phase 0 output (NEXT)
├── data-model.md                              # Phase 1 output
├── quickstart.md                              # Phase 1 output
├── contracts/
│   ├── system-prompt-section-grammar.md       # Phase 1 output — XML tag invariants + new sections
│   ├── shadow-eval-fixture-schema.md          # Phase 1 output — fixture file format + loader contract
│   └── smoke-checkpoint-protocol.md           # Phase 1 output — PTY CHECKPOINT marker + receipt regex
├── scripts/
│   ├── smoke-citizen-taxreturn.tape           # Phase 3 (US1 implementation) — vhs Layer 4
│   └── smoke-citizen-taxreturn.expect         # Phase 3 — PTY Layer 2
├── smoke-citizen-taxreturn-pty.txt            # Phase 5 — captured PTY log (gitignored? no — committed per AGENTS.md)
├── smoke-citizen-taxreturn-keyframe-1.png     # Phase 5 — boot+branding
├── smoke-citizen-taxreturn-keyframe-2.png     # Phase 5 — input-accepted
├── smoke-citizen-taxreturn-keyframe-3.png     # Phase 5 — receipt rendered
├── smoke-citizen-taxreturn.gif                # Phase 5 — animation companion
└── tasks.md                                   # /speckit-tasks output (NEXT)
```

### Source Code (repository root)

```text
prompts/
├── system_v1.md             # REWRITE TARGET (28 → ~80 lines)
└── manifest.yaml            # 1-line SHA-256 update for system_v1 entry

tests/
├── fixtures/
│   └── shadow_eval/
│       └── citizen_chain/
│           ├── _schema.py                       # NEW — fixture Pydantic v2 schema
│           ├── simple_auth_module.json          # NEW — citizen prompt + expected verify call
│           ├── modid.json                       # NEW
│           ├── kec.json                         # NEW
│           ├── geumyung_module.json             # NEW
│           ├── any_id_sso.json                  # NEW
│           └── _existing_lookup_only/           # EXISTING (regression set, not edited)
│               ├── weather_basic.json
│               ├── hospital_search.json
│               └── ... (8 fixtures total)
└── integration/
    ├── test_e2e_citizen_taxreturn_chain.py      # EXISTING (unchanged)
    ├── test_verify_module_dispatch.py           # EXISTING (unchanged)
    └── test_shadow_eval_citizen_chain_fixtures.py  # NEW — fixture loader + schema validation
```

**Structure Decision**: Single-project monorepo. The Epic touches three top-level directories — `prompts/`, `tests/fixtures/`, `specs/2298-system-prompt-rewrite/` — plus one new test module under `tests/integration/`. No `src/kosmos/**` edits, no `tui/src/**` edits.

## Complexity Tracking

> No constitution violations. Section intentionally empty.

---

## Phase 0 — Research output

See [`research.md`](./research.md) for:
- R-1 Reference mapping (5 references → 6 design decisions)
- R-2 Reused-not-built audit (PromptLoader, shadow-eval workflow, vhs Screenshot directive — all existing)
- R-3 Schema gap analysis (FamilyHint Literal vs dispatcher signature — why prompt-only Epic is sufficient)
- R-4 AAL tier reference table (10 families × canonical tier per agency policy)
- R-5 Worked-example chain selection (why modid → hometax-simplified → hometax-taxreturn is the canonical demo)
- R-6 Deferred item validation (6 items × tracking status)
- R-7 Constraint validation (prompt size budget, manifest hash recompute path, no-new-deps proof)

## Phase 1 — Design output

See [`data-model.md`](./data-model.md) for the 5 Pydantic v2 entities (system prompt section model, shadow-eval fixture model, AAL tier reference, manifest entry, smoke checkpoint marker).

See [`contracts/system-prompt-section-grammar.md`](./contracts/system-prompt-section-grammar.md) for the XML-tag invariants and the new `<verify_chain_pattern>` nested tag specification.

See [`contracts/shadow-eval-fixture-schema.md`](./contracts/shadow-eval-fixture-schema.md) for the fixture file format + loader contract.

See [`contracts/smoke-checkpoint-protocol.md`](./contracts/smoke-checkpoint-protocol.md) for the PTY CHECKPOINT marker emission protocol + receipt regex.

See [`quickstart.md`](./quickstart.md) for the first-task contributor walkthrough.
