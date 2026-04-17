# Feature Specification: Tool Template Security Spec V6 — `auth_type` ↔ `auth_level` consistency invariant

**Feature Branch**: `025-tool-security-v6`
**Created**: 2026-04-17
**Status**: Draft
**Input**: User description: "Spec-024 V6: close the defense-in-depth gap where `auth_type` can be inconsistent with `auth_level`, so no future adapter passes V1–V5 yet is anonymously callable through `PermissionPipeline.dispatch()`."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Tool construction rejects inconsistent auth triples (Priority: P1)

An adapter author adds a new government-API tool to KOSMOS. When the author sets a combination such as `auth_type="public"` with `auth_level="AAL2"` (or any other pair outside the canonical mapping), tool construction fails immediately with a validation error that names the offending field pair and lists the allowed values. The author cannot accidentally land a tool whose transport-layer auth posture disagrees with its assurance level.

**Why this priority**: This is the core defensive invariant the Epic exists to add. Without it, a future adapter with `public + AAL2 + requires_auth=True` passes V1–V5 but is anonymously callable through the legacy `PermissionPipeline.dispatch()` path, which derives its access tier from `auth_type` alone. Every other deliverable (registry backstop, spec doc, tests) depends on this invariant being enforced at the earliest possible point.

**Independent Test**: Construct a `GovAPITool` with each disallowed `(auth_type, auth_level)` pair — construction must raise at model-validation time with a message identifying both fields and the allowed levels for that `auth_type`. Construct a tool with each compliant pair — construction must succeed. No other KOSMOS subsystem needs to be involved.

**Acceptance Scenarios**:

1. **Given** an adapter author instantiates a `GovAPITool` with `auth_type="public"` and `auth_level="AAL2"`, **When** model validation runs, **Then** construction raises with an error naming both fields and the allowed auth-level set for `auth_type="public"`.
2. **Given** an adapter author instantiates a `GovAPITool` with `auth_type="api_key"` and `auth_level="public"`, **When** model validation runs, **Then** construction raises with an equivalent pair-level error.
3. **Given** an adapter author instantiates a `GovAPITool` with `auth_type="public"` and `auth_level="AAL1"`, **When** model validation runs, **Then** construction succeeds (this is the approved MVP-meta-tool combination).
4. **Given** any of the existing production adapters (KOROAD / KMA / HIRA / NMC / `resolve_location` / `lookup`) is reconstructed from its current configuration, **When** model validation runs, **Then** every adapter passes V6 with no code changes.

---

### User Story 2 — Registry backstop rejects pydantic-bypass misconfigurations (Priority: P2)

A tool object reaches `ToolRegistry.register()` after being constructed via a pydantic bypass (for example `GovAPITool.model_construct(...)` or `object.__setattr__` on a post-construction instance) with a disallowed `(auth_type, auth_level)` pair. Registration fails with a distinct, registry-originated error, preventing the misconfigured tool from ever being discoverable by the orchestrator.

**Why this priority**: V6 at the pydantic layer is the first line of defense, but `model_construct` and direct attribute mutation exist. The V3 FR-038 pattern already established the "independent backstop at registration" convention for analogous invariants; V6 must match that pattern so the defense is layered rather than single-point.

**Independent Test**: Build a tool instance via pydantic bypass with a disallowed pair, hand it to `registry.register()`, and verify the registry raises with an error traceable to the backstop (not to pydantic). Build a bypassed instance with a compliant pair and verify registration succeeds.

**Acceptance Scenarios**:

1. **Given** a tool object constructed via `model_construct` with `auth_type="public"` and `auth_level="AAL3"`, **When** `registry.register(tool)` is called, **Then** registration raises with a registry-originated error identifying the V6 violation.
2. **Given** a tool object whose `auth_level` was mutated post-construction via `object.__setattr__` into a disallowed pair, **When** `registry.register(tool)` is called, **Then** registration raises with the same class of error.
3. **Given** a tool object constructed via `model_construct` with a compliant pair, **When** `registry.register(tool)` is called, **Then** registration succeeds.

---

### User Story 3 — Security spec document v1.1 publishes the V6 matrix with worked examples (Priority: P3)

An auditor, ministry reviewer, or future adapter author reads `docs/security/tool-template-security-spec-v1.md`. They find a V6 section that (a) states the canonical `auth_type → allowed auth_levels` mapping as a matrix, (b) includes a worked example showing that `auth_type="public" + auth_level="AAL1" + requires_auth=True` is an approved compliant combination (not an exception), (c) documents the defense-in-depth rationale referencing the `PermissionPipeline.dispatch()` access-tier derivation path. The reader can verify the invariant from the document alone without reading source code.

**Why this priority**: The spec document is the governance artifact that external reviewers consult. Code-only enforcement does not satisfy the ministry-readiness bar described in Spec-024 V1. P3 because it depends on P1 + P2 being in place before the document can describe them accurately.

**Independent Test**: Open the updated spec document. Confirm: V6 section exists, the canonical matrix is present as a table, the `public + AAL1 + requires_auth=True` combination is explicitly documented as compliant, and the `PermissionPipeline.dispatch()` rationale is stated.

**Acceptance Scenarios**:

1. **Given** a reviewer opens `docs/security/tool-template-security-spec-v1.md`, **When** they search for "V6", **Then** they find a section titled "V6: auth_type ↔ auth_level consistency".
2. **Given** the V6 section, **When** the reviewer reads the canonical mapping, **Then** it appears as a matrix/table enumerating every `(auth_type, auth_level)` pair as allowed or disallowed.
3. **Given** the V6 section, **When** the reviewer searches for `resolve_location` or `lookup`, **Then** a worked example documents `auth_type="public" + auth_level="AAL1" + requires_auth=True` as approved (not as an exception or carve-out).
4. **Given** the V6 section, **When** the reviewer looks for rationale, **Then** the document explains why V5 alone is insufficient, specifically naming the `PermissionPipeline.dispatch()` path that derives access tier from `auth_type`.

---

### Edge Cases

- **Pydantic bypass with compliant pair**: A tool constructed via `model_construct` with a compliant `(auth_type, auth_level)` pair must register successfully — the backstop must not become a blanket deny-all for bypassed instances.
- **Unknown `auth_type` value**: If a future enumeration value is added to `auth_type` without a corresponding V6 mapping entry, V6 must fail closed (reject construction) rather than silently allowing arbitrary `auth_level` values.
- **Unknown `auth_level` value**: Same as above for `auth_level` — fail closed.
- **V5 ↔ V6 interaction**: `auth_level="public"` is allowed only when `auth_type="public"` (per V6) and `requires_auth=False` (per V5). Both invariants must be enforced; neither subsumes the other.
- **Multiple validators raising**: If an instance violates both V5 and V6, at least one clear error must surface to the author; the system is permitted to short-circuit on whichever validator runs first, but the error must still be actionable.
- **Registry scan of all existing adapters**: The verification that "no existing adapter regresses" must be executable as a deterministic test, not a manual check.

## Requirements *(mandatory)*

### Functional Requirements

Requirement numbering continues from the V1 spec (which defined FR-001 through FR-038). New V6 requirements begin at FR-039.

- **FR-039**: The `GovAPITool` model MUST enforce an `auth_type` ↔ `auth_level` canonical-mapping invariant at model-validation time, rejecting any instance whose `auth_level` is not in the allowed set for its `auth_type`.
- **FR-040**: The canonical mapping MUST be:
  - `auth_type == "public"` ⇒ `auth_level ∈ {"public", "AAL1"}`
  - `auth_type == "api_key"` ⇒ `auth_level ∈ {"AAL1", "AAL2", "AAL3"}`
  - `auth_type == "oauth"` ⇒ `auth_level ∈ {"AAL1", "AAL2", "AAL3"}`
- **FR-041**: The V6 validation error message MUST name both offending fields (`auth_type` and `auth_level`) and explicitly list the allowed `auth_level` set for the given `auth_type`, so the adapter author can fix the configuration without consulting source code.
- **FR-042**: `ToolRegistry.register()` MUST independently re-validate the V6 canonical mapping before accepting a tool, using a check that does not rely on the pydantic model validator having run. The backstop MUST reject tool objects constructed via pydantic bypass (`model_construct`, `object.__setattr__`) that violate the mapping.
- **FR-043**: The registry-backstop rejection MUST raise an error that is distinguishable (in type or message) from the pydantic validator rejection, so observability and debugging can identify which defense layer triggered.
- **FR-044**: Every existing production tool adapter (KOROAD, KMA, HIRA, NMC, `resolve_location`, `lookup`, and any other adapter registered in `ToolRegistry` as of the baseline commit) MUST pass V6 without configuration changes. A registry-wide scan test MUST verify this and MUST run as part of the standard `pytest` suite.
- **FR-045**: Test coverage MUST include (a) at least one positive case for every compliant `(auth_type, auth_level)` pair, (b) at least one negative case per `auth_type` covering a disallowed `auth_level`, (c) at least one registry-backstop negative case exercising pydantic bypass.
- **FR-046**: The security spec document (`docs/security/tool-template-security-spec-v1.md`) MUST be updated to spec version **v1.1** (or via a clearly labeled v1 amendment) adding a V6 section that includes: the canonical mapping as a matrix/table, a worked example explicitly documenting `auth_type="public" + auth_level="AAL1" + requires_auth=True` as approved (not as an exception), and a rationale paragraph naming the `PermissionPipeline.dispatch()` access-tier derivation as the reason V5 alone is insufficient.
- **FR-047**: V6 MUST run alongside (not replace) V1–V5. V5 (`auth_level=="public"` ⇔ `requires_auth==False`) remains in force unchanged.
- **FR-048**: If `auth_type` takes any value not listed in FR-040's mapping, V6 MUST fail closed (reject construction) rather than defaulting to allow. The same fail-closed rule applies to unknown `auth_level` values.

### Key Entities

- **GovAPITool** — the pydantic model representing a single government-API tool adapter. Owns `auth_type`, `auth_level`, `requires_auth`, and related security metadata. V6 extends its model-validator chain.
- **ToolRegistry** — the in-memory registry that gates registration. Hosts the V6 backstop that runs at `register()` time independently of pydantic.
- **Canonical Auth Mapping** — the published `auth_type → allowed auth_levels` relation. Lives as code (the validator) and as documentation (the spec document matrix); both surfaces must agree.
- **Spec Document (v1.1)** — `docs/security/tool-template-security-spec-v1.md`, the externally reviewable governance artifact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing production tool adapters pass V6 with no configuration changes, verified by a deterministic registry-scan test in the standard `pytest` suite.
- **SC-002**: 100% of disallowed `(auth_type, auth_level)` pairs attempted at construction time raise a clear validation error that names both offending fields and lists the allowed set.
- **SC-003**: 100% of pydantic-bypass attempts (`model_construct` or `object.__setattr__`) at registration time with a disallowed pair are rejected by the registry backstop.
- **SC-004**: An external reviewer reading only the updated spec document can (a) enumerate every allowed `(auth_type, auth_level)` pair, (b) identify the approved MVP-meta-tool combination, (c) explain why V5 alone is insufficient, without reading any source code.
- **SC-005**: Zero defense-in-depth regressions introduced — V1–V5 validators, V5 biconditional, and `executor.invoke()` `requires_auth` gating continue to behave identically after V6 lands, verified by the existing test suite passing unchanged.
- **SC-006**: Future adapter PRs cannot merge with a disallowed `(auth_type, auth_level)` pair — CI fails at the construction/registration test gate before code review.

## Assumptions

- V1–V5 validators from Epic #612 / PR #653 remain in place; V6 is additive, not replacement.
- V5 biconditional (`auth_level=="public"` ⇔ `requires_auth==False`) stays unchanged and continues to be enforced.
- `executor.invoke()` already gates on `requires_auth` correctly (verified in Epic #654 problem statement).
- All existing production adapters already satisfy the FR-040 canonical mapping; this will be verified during implementation by the registry-scan test before the validator is enabled in strict mode.
- The spec document structure established in v1 (sections per invariant) accommodates a V6 section append without restructuring v1–v5 content.
- `auth_type` enumeration values in scope are `{"public", "api_key", "oauth"}`. If a future `auth_type` value is added, the mapping in FR-040 must be extended in the same PR that introduces the new value (enforced by FR-048's fail-closed rule).
- `auth_level` enumeration values in scope are `{"public", "AAL1", "AAL2", "AAL3"}`, matching the V1 spec.

## Dependencies

- **Baseline**: Spec-024 V1 (Epic #612, merged in PR #653) — V6 extends its validator chain.
- **Parent Epic**: #654.
- **Parent Initiative**: #462 (Infrastructure — LLM-Agent Production-Grade Operations).
- **Source trigger**: Codex review P1 finding on PR #653.
- **No new runtime dependencies** — implementation reuses the existing pydantic v2 and `pytest` stack.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Changes to `executor.invoke()`** — this runtime path is already correct (gates on `requires_auth`). Altering it is not needed to close the V6 gap and would risk regressing an existing correct path. Permanently out of scope for this feature.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `PermissionPipeline.dispatch()` refactor to read `requires_auth` directly (instead of deriving from `auth_type` via `_AUTH_TYPE_TO_ACCESS_TIER`) | V6 makes the input configuration safe regardless of which runtime path dispatches it. The pipeline-path refactor is a larger behavioral change and belongs in its own Epic. | Pipeline Auth Consolidation (future Epic) | #673 |
| Unification of `PermissionPipeline.dispatch()` and `executor.invoke()` into a single auth-gate code path | Larger architectural refactor; out of scope for this defense-in-depth hardening. | Pipeline Auth Consolidation (future Epic) | #674 |
| TUI work | Unrelated presentation layer; tracked separately. | TUI Epic | #287 |
| Agent Swarm Core orchestrator changes | Unrelated orchestrator Epic; no interaction with V6. | Agent Swarm Core Epic | #576 |
| Additional government-API tool adapters | Unrelated to the V6 invariant; new adapters will simply be required to pass V6 like any other tool. | Ongoing adapter Epics | #579, #643 |
