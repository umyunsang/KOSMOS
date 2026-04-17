# Phase 0 Research: Tool Template Security Spec V6

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-04-17

## Purpose

Resolve all Technical-Context unknowns and map every V6 design decision to a concrete reference per Constitution §I. This research also validates the deferred-item section of `spec.md` against Constitution §VI.

## Reference Source Mapping (Constitution §I — MANDATORY)

Each V6 design decision is traced to a concrete reference source. Primary references come from `docs/vision.md § Reference materials` and existing KOSMOS code that established the pattern we are extending.

### Decision 1 — Validator mechanism for FR-039 (model-layer V6 enforcement)

**Decision**: Extend the existing `@model_validator(mode="after")` chain in `GovAPITool._validate_security_invariants` (`src/kosmos/tools/models.py:166-238`) with a V6 block that checks `auth_type` ↔ `auth_level` against a module-level canonical mapping constant.

**Rationale**:
- Pydantic v2 `@model_validator(mode="after")` is the pattern V1–V5 already use on the same model. Consistency with the existing chain means a single place to audit all cross-field invariants, a single error-path for authors, and zero new imports.
- `mode="after"` guarantees the validator sees coerced field types (`auth_type: Literal[...]`, `auth_level: AALLevel`), so the V6 check is a pure set-membership test with no re-parsing.
- Returning `self` at chain end preserves the V1–V5 return contract; V6 is a pure additive block.

**Alternatives considered**:
- `mode="before"` validator — rejected: operates on raw input dict, would require re-implementing the Literal/Enum coercion that V1–V5 rely on.
- Separate standalone validator function — rejected: fragments the security-invariant chain and makes a future FR-048 fail-closed-on-unknown-enum harder to co-locate.
- Field-level `@field_validator` — rejected: cannot inspect two fields simultaneously.

**Primary reference**: Pydantic AI (`docs/vision.md § Reference materials` — Tool System row, primary reference). Pydantic AI's schema-driven registry established the convention of model-layer cross-field validation as the first line of defense.
**Secondary reference**: Existing V1–V5 code at `src/kosmos/tools/models.py:166-238` — the exact pattern V6 extends.

### Decision 2 — Registry backstop mechanism for FR-042 (registration-layer V6 enforcement)

**Decision**: Add a V6 check inside `ToolRegistry.register()` (`src/kosmos/tools/registry.py:26-79`) that mirrors the existing V3 FR-038 backstop block. The check: lookup `tool.auth_type` in the canonical mapping module constant; if `tool.auth_level` is not in the allowed set, log a structured error and raise `RegistrationError` with a V6-specific message distinct from the pydantic `ValueError`.

**Rationale**:
- V3 FR-038 (landed in PR #653) already established the "independent backstop at registration" convention for analogous invariants — see `src/kosmos/tools/registry.py:39-79` for the three existing FR-038 checks, each guarded against `model_construct` bypass. V6 must match this structural pattern so auditors see a uniform defense-in-depth layout across all security invariants.
- Raising `RegistrationError` (not `ValueError`) satisfies FR-043 (distinguishable from pydantic error) and matches what the other backstops already do, so observability / log-pattern matching stays stable.
- The backstop re-reads `tool.auth_type` and `tool.auth_level` directly from the instance, which is exactly what the FR-038 `is_personal_data` + `auth_level` check does two lines above; this defeats `model_construct` and `object.__setattr__` bypasses that the pydantic validator would miss.

**Alternatives considered**:
- Skip the backstop; trust the pydantic validator alone — rejected: explicitly disallowed by the user-provided constraint "Registry backstop is mandatory" and by Constitution §II (fail-closed; no bypass-able checks).
- Place the backstop in `ToolExecutor.invoke()` instead — rejected: the threat model is "misconfigured tool reaches the orchestrator", and `ToolRegistry.register()` is the earliest chokepoint before the orchestrator can discover it. Moving the check later would allow the tool to be listed by `registry.search()` before being rejected.
- Use an assert or a private helper — rejected: asserts are stripped in `-O` mode; Constitution §II requires bypass-immune enforcement.

**Primary reference**: V3 FR-038 implementation at `src/kosmos/tools/registry.py:39-79` — the prescribed code-pattern reference.
**Secondary reference**: Spec-024 V1 data-model §1 invariants doc (`docs/security/tool-template-security-spec-v1.md`) — establishes the two-layer-defense mental model that V6 extends.

### Decision 3 — Documentation update strategy for FR-046 (spec v1.1 amendment)

**Decision**: Append a new section titled "V6: auth_type ↔ auth_level consistency" to `docs/security/tool-template-security-spec-v1.md`, bumping the document version to v1.1. Append — not restructure — because v1's section-per-invariant convention accommodates the new section without disturbing V1–V5 content. The new section contains (a) a canonical mapping matrix table, (b) a worked `public + AAL1 + requires_auth=True` example explicitly labeled as approved (not an exception), (c) a rationale paragraph naming `PermissionPipeline.dispatch()` as the reason V5 alone is insufficient.

**Rationale**:
- Spec-024 V1 (Epic #612, merged in PR #653) established the document structure: one section per invariant (V1, V2, V3, V4, V5). V6 follows the same section shape for consistency — auditors familiar with V1–V5 can locate V6 without re-reading the entire document.
- v1.1 (semver patch) signals additive content with no breaking reinterpretation of V1–V5 — matches actual code behavior (V1–V5 unchanged per FR-047).
- A matrix table is the format ministry reviewers expect for allow-list contracts; mirrors the `TOOL_MIN_AAL` table in `src/kosmos/security/audit.py`.

**Alternatives considered**:
- Create `docs/security/tool-template-security-spec-v2.md` — rejected: the change is additive, not a major revision; duplicating the document splits reviewer attention.
- Inline the matrix in code docstring only — rejected: violates the "governance artifact must be externally reviewable without reading source" principle (SC-004).
- Describe the rule in prose without a matrix — rejected: ministry-readiness bar (Spec-024 V1) requires the allow-list to be unambiguous and machine-auditable.

**Primary reference**: `docs/security/tool-template-security-spec-v1.md` existing V1–V5 section structure — the document layout V6 must match.
**Secondary reference**: `docs/vision.md § Reference materials` — Claude Code reconstructed (tool-metadata gating pattern) is the upstream mental model for "metadata-declared authorization governed at ingestion time".

### Decision 4 — Test layout for FR-044, FR-045 (coverage of positive/negative + bypass + registry-wide scan)

**Decision**: Split V6 tests across the two existing test files that the spec constraint names:
- `tests/tools/test_gov_api_tool_extensions.py`: positive tests (one per compliant `(auth_type, auth_level)` pair — 2 for `public`, 3 for `api_key`, 3 for `oauth`) and negative tests (one per disallowed pair). Error messages asserted to contain both field names and the allowed set per FR-041.
- `tests/tools/test_registry_invariant.py`: (a) backstop positive + negative tests using `GovAPITool.model_construct(...)` to bypass pydantic; (b) a registry-wide scan test that iterates over the production-registry factory and asserts every adapter's `(auth_type, auth_level)` is in the canonical mapping.

**Rationale**:
- Co-locates V6 tests with V1–V5 tests in the same two modules — matches the existing layout and simplifies future audits ("find all security-invariant tests" = `rg V[1-9] tests/tools/test_*`).
- `model_construct` is the documented pydantic v2 bypass surface and matches the V3 FR-038 backstop test pattern already in place.
- The registry-wide scan test is deterministic (no randomness, no network) and runs in the default `pytest` suite per FR-044. It uses the real production-registry factory so it automatically covers any future adapter without requiring per-adapter test updates.

**Alternatives considered**:
- Property-based testing (Hypothesis) over all `(auth_type, auth_level)` pairs — rejected: introduces a new dev dependency for a 4 × 3 = 12-pair domain that enumerates cheaply.
- Parametrized test matrix — feasible and preferred; will use `@pytest.mark.parametrize` to enumerate pairs without duplication.
- Separate V6-only test file — rejected: violates the constraint "tests live in the two named files".

**Primary reference**: Existing V1–V5 tests in `tests/tools/test_gov_api_tool_extensions.py` and FR-038 backstop test in `tests/tools/test_registry_invariant.py` — the layout V6 must match.
**Secondary reference**: pytest parametrization docs (no new dependency).

### Decision 5 — Canonical mapping location (module constant vs inline)

**Decision**: Declare the canonical `auth_type → frozenset[auth_level]` mapping as a module-level constant in `src/kosmos/tools/models.py` (colocated with the `_validate_security_invariants` method that consumes it). Import and reuse the same constant in `src/kosmos/tools/registry.py` for the backstop.

**Rationale**:
- Single source of truth — validator and backstop MUST check the identical mapping, or they can drift (Constitution §II violation risk).
- `frozenset` is immutable (prevents accidental mutation at runtime) and hashable (negligible lookup cost).
- Module-level constant mirrors how `TOOL_MIN_AAL` (V3 SoT) is declared in `src/kosmos/security/audit.py` — a known-good precedent in this codebase.

**Alternatives considered**:
- Duplicate the mapping in both files — rejected: drift risk.
- Put the mapping in `src/kosmos/security/audit.py` — considered; rejected because V6 is a model-layer invariant about adapter metadata, not a runtime audit constant like `TOOL_MIN_AAL`. The constant's natural home is next to the validator that enforces it.
- Config file / YAML — rejected: no runtime configurability needed; hard-coding matches the "spec document is authoritative" principle.

**Primary reference**: `TOOL_MIN_AAL` module-level constant at `src/kosmos/security/audit.py` — the single-source-of-truth precedent pattern.

### Decision 6 — Error message format for FR-041, FR-043

**Decision**:
- **Validator (pydantic)** error: `ValueError("V6 violation (FR-039/FR-040): tool {self.id!r} declares auth_type={self.auth_type!r} with auth_level={self.auth_level!r}; auth_type={self.auth_type!r} permits auth_level in {sorted(allowed)!r}.")`
- **Backstop (registry)** error: `RegistrationError(tool.id, "V6 violation (FR-042): declares auth_type={...!r} with auth_level={...!r}; permitted auth_levels are {...!r}. (registry backstop — bypass via model_construct detected)")`

The two messages share the "V6 violation" prefix for log grep-ability but differ in the explicit "registry backstop" tail, satisfying FR-043 (distinguishable) while satisfying FR-041 (both fields + allowed set named in both layers).

**Rationale**:
- Matches the exact message shape V1–V5 use (`f"V{N} violation (FR-...): tool {self.id!r} ..."`) so authors see a familiar format.
- The "(registry backstop — bypass via model_construct detected)" tail is the exact telemetry signal observability needs to distinguish layer-1 vs layer-2 rejections in production logs.
- `sorted(allowed)` ensures deterministic error-message ordering for test stability.

**Primary reference**: V1–V5 error-message format at `src/kosmos/tools/models.py:184-237` — the layout V6 must match.

## Deferred Items Validation (Constitution §VI — MANDATORY)

Scanned `spec.md § Scope Boundaries & Deferred Items` and full spec body per Principle VI requirements.

### Table entries — status

| Item | Tracking Issue (spec) | Validation status |
|------|----------------------|-------------------|
| `PermissionPipeline.dispatch()` refactor | NEEDS TRACKING | FLAG — will be resolved by `/speckit-taskstoissues` creating a placeholder issue |
| `dispatch()` ↔ `executor.invoke()` path unification | NEEDS TRACKING | FLAG — will be resolved by `/speckit-taskstoissues` |
| TUI work | #287 | PASS — issue exists and is tracked |
| Agent Swarm Core orchestrator changes | #576 | PASS — issue exists and is tracked |
| Additional government-API tool adapters | #579, #643 | PASS — both issues exist and are tracked |

### Full-text scan for unregistered deferrals

Patterns searched: "separate epic", "future epic", "Phase [2+]", "v2", "deferred to", "later release", "out of scope for v1".

Results:
- **"separate epic"** — appears 2× in `spec.md`; both occurrences refer to the `PermissionPipeline.dispatch()` refactor and are represented in the table (entry 1). PASS.
- **"future epic" / "future Epic"** — appears 2× in `spec.md`; both in `Target Epic/Phase` column of the table itself. PASS.
- **"v2"** — 0 matches.
- **"deferred to"** — 0 matches outside the mandatory section header.
- **"later release"** — 0 matches.
- **"out of scope"** — appears multiple times; all occurrences either inside the mandatory Out-of-Scope subsection or as part of the Epic #654 context summary. PASS.
- **"Phase 2+"** — 0 matches.

**Verdict**: No unregistered deferrals. Two `NEEDS TRACKING` markers will be resolved downstream by `/speckit-taskstoissues` per the standard workflow. Constitution §VI gate PASS.

## Resolved Unknowns

No `NEEDS CLARIFICATION` markers in the Technical Context. All design decisions were pre-decided by Epic #654 and the user-provided plan prompt; this research document maps each decision to its reference and records the rejected alternatives for audit.

## Next Phase

Proceed to Phase 1 (Design & Contracts): author `data-model.md` (canonical mapping table + error contract), `contracts/v6-error-contract.md` (validator + backstop error-shape contracts), and `quickstart.md` (adapter-author onboarding for V6). Run `update-agent-context.sh claude` to refresh `CLAUDE.md` active-technologies.
