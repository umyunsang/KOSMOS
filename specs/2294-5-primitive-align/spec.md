# Feature Specification: 5-Primitive Align with Claude Code Tool.ts Interface

**Feature Branch**: `2294-5-primitive-align`
**Created**: 2026-04-29
**Status**: Draft
**Input**: Epic γ #2294 (Initiative #2290) — Refactor 4 KOSMOS primitives (`LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, `SubscribePrimitive`) to follow Claude Code's `Tool` interface verbatim. Surface adapter `real_domain_policy` citation through CC's `FallbackPermissionRequest`. Acceptance: ToolRegistry boots cleanly with all 4 primitives + 18 adapters; PTY smoke "의정부 응급실 알려줘" round-trips through `lookup` → `resolve_location` → `nmc_emergency_search` and renders Korean output.

**Authoritative references** (cited by every downstream artefact):

1. `.references/claude-code-sourcemap/restored-src/src/Tool.ts` — canonical `Tool<In, Out>` interface (792 LOC).
2. `.references/claude-code-sourcemap/restored-src/src/tools/AgentTool/AgentTool.tsx` — reference Tool implementation pattern (1397 LOC).
3. `specs/1979-plugin-dx-tui-integration/cc-source-migration-plan.md` § Phase γ (lines 175–214) — KOSMOS-specific migration guidance.
4. `docs/vision.md` § L1-C Main-Verb Abstraction.
5. `docs/requirements/kosmos-migration-tree.md` § L1-C — primitive contract (envelope, routing, permission gating).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen looks up emergency-room information by natural language (Priority: P1)

A citizen in 의정부 asks the KOSMOS TUI for the nearest emergency room. The LLM determines that this requires the `lookup` primitive in `fetch` mode against the NMC emergency-search adapter, after first calling `resolve_location` to convert the colloquial place name into a structured location. KOSMOS surfaces a permission prompt that cites the NMC's published policy URL (no KOSMOS-invented language), the citizen approves, and the result is rendered in Korean inside the TUI conversation pane.

**Why this priority**: This is the canonical citizen-facing read-only flow. Lookup is the most-used primitive (per Spec 022 BM25 telemetry), and emergency-medicine is the lowest-friction OPAQUE-free domain in KOSMOS's adapter inventory. If this single journey works end-to-end with the new Tool-shape, the entire L1-A harness × L1-B tool surface contract is proven for read-only domains.

**Independent Test**: Capture a PTY transcript (`expect`/`script`) of `bun run tui` started in the worktree, send the natural-language query, observe the permission prompt rendering with the NMC citation URL, approve, and assert that the Korean adapter response is printed before Ctrl-C exit. The text log must be greppable for the citation URL string and the adapter result envelope's `_mode` field. No live `data.go.kr` call is required — Mock fixtures cover the round-trip in CI.

**Acceptance Scenarios**:

1. **Given** the TUI is at the REPL prompt with `KOSMOS_LLM_API_KEY` configured, **When** the citizen types `의정부 응급실 알려줘`, **Then** the LLM emits a function call to `lookup` (mode=`fetch`, tool_id=`nmc_emergency_search`) preceded by a `resolve_location` call, the TUI displays a permission prompt sourced from `FallbackPermissionRequest`, the prompt body shows the NMC `real_classification_url` verbatim, and after approval the adapter result is rendered in Korean.
2. **Given** the same flow, **When** the citizen denies the permission prompt, **Then** the primitive's `call` returns a structured `PermissionDeniedError` envelope, the LLM is told the call was refused, and no adapter HTTP request is initiated.
3. **Given** an adapter without `real_domain_policy.real_classification_url`, **When** the primitive needs to render its permission prompt, **Then** the prompt visually flags the missing citation as a registry-validation error rather than fabricating placeholder text.

---

### User Story 2 — ToolRegistry validates new primitive shape at boot (Priority: P1)

When the KOSMOS Python backend (or TUI in dev mode) boots, the ToolRegistry must verify that all 4 primitives (`lookup`, `submit`, `verify`, `subscribe`) plus the 18 currently registered adapters expose the full Tool-interface surface (`name`, `description`, `inputSchema`, `isReadOnly`, `isMcp`, `validateInput`, `call`, `renderToolUseMessage`, `renderToolResultMessage`). Any registration that omits a required member fails fast with a Korean-readable diagnostic.

**Why this priority**: This is co-equal P1 with Story 1 because every other primitive flow depends on a clean registry boot. CC's runtime equivalent is `Tool.ts`'s implicit shape-check via TypeScript; KOSMOS adds an explicit boot-time guard so contributor plugins (Spec 1636 / 1979) can't silently ship a malformed primitive.

**Independent Test**: Run the existing TUI `bun test tui/src/tools/__tests__/registry-boot.test.ts` (newly added by this feature) which constructs the registry, asserts shape compliance for each of the 4 primitives + 18 adapters, and snapshots the diagnostic output for any deliberate-failure fixture.

**Acceptance Scenarios**:

1. **Given** all 4 primitives have been migrated to the new shape, **When** the registry boots, **Then** the boot log emits a single `tool_registry: 22 entries verified (4 primitives, 18 adapters)` line and exits with code 0.
2. **Given** a deliberately broken primitive missing `renderToolResultMessage`, **When** the registry boots in test mode, **Then** boot fails with a Korean diagnostic naming the offending tool and the missing field.

---

### User Story 3 — Adapter policy citation surfaces verbatim in permission UI (Priority: P2)

Every `<PermissionRequest>` rendered for a primitive call includes the adapter's published `real_classification_url` and `policy_authority` text fields exactly as the agency publishes them. KOSMOS does not paraphrase, summarize, or invent permission classifications.

**Why this priority**: This is the constitutional check that proves the "KOSMOS does not invent permission policy" rule (AGENTS.md § CORE THESIS) is enforced in code, not just in docs. P2 because it depends on Story 1's render plumbing being in place; once Story 1 ships the permission prompt path, Story 3 is a content-correctness check.

**Independent Test**: A snapshot test (`tui/src/tools/__tests__/permission-citation.test.ts`) walks every Live + Mock adapter and renders the permission prompt with a representative invocation; the snapshot must contain `real_classification_url` byte-for-byte and must NOT contain any of a known list of KOSMOS-invented phrases (e.g., "안전한 권한 등급", "본 시스템은…" — to be enumerated in the test fixture).

**Acceptance Scenarios**:

1. **Given** any registered adapter with `real_domain_policy` set, **When** that adapter's primitive renders a permission prompt, **Then** the rendered output contains the adapter's `real_classification_url` literal string and the `policy_authority` literal string.
2. **Given** an adapter where `real_domain_policy.real_classification_url` is the empty string, **When** the registry tries to register it, **Then** registration fails with a Korean diagnostic referencing the adapter id and the missing field.

---

### User Story 4 — `resolve_location` continues to behave as a `lookup` sub-mode (Priority: P3)

The `resolve_location` meta-tool (a geocoding helper that pre-resolves Korean place names) was integrated as a sub-mode of `lookup` in Spec 022. After the Tool-shape refactor it must still behave identically — same input shape, same output envelope, same routing, same observability spans.

**Why this priority**: Validation-only. No code change is expected; this is a regression boundary check.

**Independent Test**: An existing pytest (`tests/primitives/test_lookup_resolve_location.py`) runs unchanged and passes; the TUI snapshot for the lookup permission prompt for `resolve_location` matches the pre-refactor snapshot.

**Acceptance Scenarios**:

1. **Given** an LLM tool-call to `lookup(mode='fetch', tool_id='resolve_location', params={...})`, **When** the primitive routes the call, **Then** the routing target, OTEL span attributes, and output envelope shape are byte-identical to the pre-refactor baseline.

---

### Edge Cases

- **Permission timeout**: User does not respond to the `<PermissionRequest>` within the `KOSMOS_PERMISSION_TIMEOUT` window — the primitive's `call` resolves to a structured timeout envelope and the LLM is informed; behaviour matches CC's `Tool.ts` cancellation pattern.
- **Adapter not in registry**: LLM emits a `lookup(tool_id='unknown_adapter')` call — the primitive's `validateInput` returns a structured `AdapterNotFoundError` and the LLM receives the error directly without a permission prompt being shown.
- **Backend IPC mid-call disconnect**: The Python backend dies during a primitive `call` — the TUI's IPC layer (Spec 032) yields a connection-lost frame, the primitive's async iterator surfaces a `BackendDisconnectedError` envelope, and the TUI displays a Korean reconnect message.
- **Two primitive calls in parallel from the same LLM turn**: EXAONE function-calling supports parallel tool-call arrays — both primitive `call`s must be re-entrant; one's permission prompt does not block the other's `validateInput`. (Behaviour parity with CC `AgentTool.tsx` parallel dispatch.)
- **MCP-side primitive (future)**: A community plugin (Spec 1636) registers a custom primitive via MCP — the registry must accept it because its `isMcp` returns `true`, and the permission UI must downgrade to the MCP-default citation pattern (out of scope for this Epic; documented as deferred).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The TUI MUST expose `LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, and `SubscribePrimitive` as `Tool<In, Out>` instances whose surface includes all of the following members defined in `.references/claude-code-sourcemap/restored-src/src/Tool.ts`: `name`, `description()`, `inputSchema`, `isReadOnly()`, `isMcp`, `validateInput()`, `call()`, `renderToolUseMessage()`, `renderToolResultMessage()`. Any member missing on any of the 4 primitives is a P0 defect.
- **FR-002**: Each primitive's `description()` MUST return a citizen-facing Korean string suitable for direct display in the LLM's tool-selection prompt. Source comments and identifiers remain English (per AGENTS.md hard rule).
- **FR-003**: Each primitive's `inputSchema` MUST be a `zod` schema (already in `tui/package.json`; no new dependency) that mirrors the existing `PrimitiveInput` envelope structure (`mode`, `tool_id`, `params`) so that the JSON-schema export to EXAONE function-calling remains shape-identical to the pre-refactor baseline.
- **FR-004**: Each primitive's `validateInput()` MUST resolve the `tool_id` against the in-memory adapter registry, returning a structured `AdapterNotFoundError` envelope (no exception throw) when the adapter is unknown. BM25 hint resolution from Spec 022 stays in `validateInput`'s code path.
- **FR-005**: Each primitive's `call()` MUST be an async generator yielding the same `PrimitiveOutput` envelope shape that the Python backend currently emits over IPC (Spec 032), so that the backend's `src/kosmos/primitives/{lookup,submit,verify,subscribe}.py` modules are unchanged by this refactor.
- **FR-006**: The TUI MUST render the permission UI for every primitive `call()` through Claude Code's `FallbackPermissionRequest` component (`tui/src/components/permissions/FallbackPermissionRequest.tsx`, byte-identical to CC). Custom KOSMOS-invented permission components are forbidden.
- **FR-007**: The permission prompt body for any adapter-routed primitive call MUST include the adapter's `real_domain_policy.real_classification_url` field and `policy_authority` field as literal strings, with no KOSMOS paraphrasing, summarization, or grade labels.
- **FR-008**: The ToolRegistry boot path MUST verify, at process start, that every registered tool (4 primitives + 18 adapters) exposes the full Tool-interface surface from FR-001. Boot MUST fail closed with a Korean diagnostic if any tool is malformed.
- **FR-009**: The ToolRegistry boot path MUST verify that every adapter with `is_live=true` or `is_mock=true` has a non-empty `real_domain_policy.real_classification_url`. Boot MUST fail closed with a Korean diagnostic naming the offending adapter id when this rule is violated.
- **FR-010**: The `resolve_location` meta-tool MUST remain accessible exclusively through `lookup(mode='fetch', tool_id='resolve_location', params={...})`. No standalone primitive registration for `resolve_location` is permitted.
- **FR-011**: The Python backend's `PrimitiveInput` and `PrimitiveOutput` Pydantic v2 models MUST NOT be modified by this Epic. Cross-layer envelope stability is what allows the TS-side refactor to land without backend coordination.
- **FR-012**: BM25 search hint resolution and EXAONE function-calling round-trip behaviour MUST be preserved with zero observable change in OTEL span attributes (`kosmos.tool.id`, `kosmos.tool.mode`, `kosmos.adapter.real_classification_url`).
- **FR-013**: A PTY interactive smoke transcript MUST be captured under `specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.expect` + `specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt` as a precondition to PR merge, per `feedback_pr_pre_merge_interactive_test`. The transcript MUST exercise Story 1's full happy path.
- **FR-014**: No new runtime dependency may be introduced in either `pyproject.toml` or `tui/package.json` (AGENTS.md hard rule). The refactor uses existing `zod`, `ink`, `react`, and `@inkjs/ui`.
- **FR-015**: All source code text (identifiers, comments, log messages emitted to STDERR) MUST be English. Korean is reserved for `description()` strings, `llm_description` metadata, and citizen-facing TUI messages.

### Key Entities *(include if feature involves data)*

- **`Tool<In, Out>` (existing CC interface, byte-identical port)**: A 9-member contract — `name: string`, `description: () => string`, `inputSchema: ZodSchema<In>`, `isReadOnly: () => boolean`, `isMcp: boolean`, `validateInput: (input, context) => Promise<ValidationResult>`, `call: (input, context) => AsyncGenerator<Out>`, `renderToolUseMessage: (input, context) => ReactNode`, `renderToolResultMessage: (output, context) => ReactNode`. Source-of-truth: `.references/claude-code-sourcemap/restored-src/src/Tool.ts`.
- **`PrimitiveInput` / `PrimitiveOutput` envelopes (existing, unchanged)**: The cross-layer contract between the TS primitive's `call()` and the Python backend's primitive module. Fields: `mode` (search/fetch for lookup; submit/cancel for submit; verify/refresh for verify; subscribe/unsubscribe for subscribe), `tool_id` (adapter id), `params` (free-form arbitrary JSON validated by adapter's own schema). Source-of-truth: `src/kosmos/primitives/__init__.py`.
- **`AdapterRealDomainPolicy` (existing from Epic δ #2295)**: A frozen Pydantic v2 model carrying `real_classification_url: str`, `policy_authority: str`, `last_verified: date`, plus computed-field `citizen_facing_gate` derivation used by Spec 024/025/1636 invariants. Source-of-truth: `src/kosmos/tools/policy.py` (added in commit `c6747dd`).
- **`PermissionRequest` UI (existing CC component, byte-identical port)**: The React component that renders the [Y once / A session-auto / N deny] prompt with receipt-id display. Primitive-specific extension is purely declarative — primitive provides citation strings via metadata; component layout stays unchanged. Source-of-truth: `tui/src/components/permissions/FallbackPermissionRequest.tsx`.
- **`ToolRegistry` (existing, behaviour extended)**: An in-memory map rebuilt at process boot from `kosmos.tools.*` module imports plus `tui/src/tools/*Primitive` registrations. New behaviour added by this Epic: shape verification + citation-presence verification at boot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The PTY smoke transcript for Story 1 (`의정부 응급실 알려줘`) reaches the Korean adapter response within 8 seconds wall-clock from prompt submission, on a developer laptop with FriendliAI Tier 1 quota and a warm prompt cache. Transcript is committed to the spec directory.
- **SC-002**: ToolRegistry boot completes in ≤ 200 ms with all 22 registrations verified (4 primitives + 18 adapters) on the same laptop class.
- **SC-003**: 100% of adapter-routed permission prompts rendered during the test suite contain a verbatim `real_classification_url` substring; 0% contain any string from the KOSMOS-invented-phrase blocklist enumerated in `tui/src/tools/__tests__/permission-citation.test.ts`.
- **SC-004**: `bun typecheck` reports 0 errors after the refactor against `tsconfig.json`'s existing `tui/src/**` scope.
- **SC-005**: `bun test` and `uv run pytest` introduce 0 NEW failures versus the main-branch baseline at commit `c6747dd` (1 pre-existing snapshot failure + 1 pre-existing pytest failure are acknowledged and unchanged).
- **SC-006**: The diff for the 4 primitive files (`tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive/`) plus the registry boot guard plus the new tests is ≤ 1500 net LOC. Anything larger indicates accidental scope creep into Epic ε or ζ territory.
- **SC-007**: The OTEL span attribute set emitted for a primitive call (`kosmos.tool.id`, `kosmos.tool.mode`, `kosmos.adapter.real_classification_url`, plus the existing GenAI / Tool / Permission span families from Spec 021) is identical to the pre-refactor baseline — verified by a span-attribute snapshot test.

## Assumptions

- The Python backend's `src/kosmos/primitives/{lookup,submit,verify,subscribe}.py` modules already emit a stable `PrimitiveOutput` envelope over the Spec 032 IPC channel and do not require coordination changes for this Epic.
- The 18 currently-registered adapters all carry an `AdapterRealDomainPolicy` field after Epic δ #2295 (commit `c6747dd`); 19 adapters were migrated, 1 may remain in the Epic δ deferred-issue #2362 pile, but Story 2 / FR-009 will surface that mismatch on first boot if it exists.
- `FallbackPermissionRequest` from CC is already present byte-identical under `tui/src/components/permissions/` per Spec 2293's residue-cleanup work; the primitive layer only needs to consume it, not port it.
- EXAONE function-calling JSON-schema export (the path that turns the primitive's `inputSchema` into the OpenAI-compat `tools[]` array) is already wired through Spec 1978's ChatRequestFrame; no protocol change required.
- The PTY smoke harness (`expect`/`script`) is the same one used by Specs 1979, 2293 and 2112; no new tooling needs to be installed.
- A "1 pre-existing snapshot failure" + "1 pre-existing pytest failure" baseline is acknowledged at `c6747dd` per memory `feedback_pr_pre_merge_interactive_test` and the v6 handoff doc.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Backend Python primitive logic changes** — the Python `src/kosmos/primitives/{lookup,submit,verify,subscribe}.py` modules are part of L1-A's stable IPC contract (Spec 032) and are not modified by a TS-side interface refactor. Permanent boundary, not a deferral.
- **Adapter business-logic edits** — the 18 adapters' actual API-call code is owned by their respective domain Epics (KOROAD / KMA / HIRA / NMC / etc.). This Epic only consumes their registered metadata.
- **System-prompt updates encouraging primitive use** — that is `cc-source-migration-plan` Phase ζ and is intentionally a separate optional Epic so that prompt drift does not delay the shape refactor.
- **Plugin DX SDK changes** — the Spec 1636 / 1979 plugin contributor SDK exposes `Tool<In, Out>` already as the contract; community plugins will benefit from the registry-shape verification automatically without SDK changes.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| 9 new Mock adapters mirroring the AX-infrastructure callable channels (Singapore APEX-style) plus the `DelegationToken`/`DelegationContext` schema | Net-new adapter inventory; orthogonal to the primitive shape refactor | Epic ε #2296 | #2296 |
| End-to-end PTY scenario for the full delegation flow (`종합소득세 신고해줘` → `verify(modid)` → `lookup(simplified)` → `submit(taxreturn)`) | Requires Epic ε's new submit/verify Mock adapters to exist before E2E can be captured | Epic ζ #2297 | #2297 |
| `docs/research/policy-mapping.md` — KOSMOS adapter ↔ international gateway-spec mapping table (APEX / X-Road / EUDI / マイナポータル) | Documentation deliverable spanning the full L1-B inventory; better written after Epic ε ships its adapters | Epic ζ #2297 | #2297 |
| `docs/scenarios/{hometax-tax-filing, gov24-minwon-submit, mobile-id-issuance, kec-yessign-signing, mydata-live}.md` OPAQUE hand-off scenarios | Narrative scenario docs for OPAQUE-forever domains; depend on submit/verify primitive shape stability + Epic ε's verify_modid mock | Epic ζ #2297 | #2297 |
| MCP-side primitive permission-UI downgrade pattern | Edge case for community plugin primitives that route through MCP rather than native registration; out of P3 scope | Phase 5 plugin DX follow-up | #2392 |
| `prompts/system_v1.md` 5-primitive citizen-friendly tone update | Optional Phase ζ from `cc-source-migration-plan`; gated on shadow-eval results from Spec 026 to avoid prompt-drift regressions | Phase ζ (optional) | #2393 |
| Resolution of Epic δ deferred adapter `real_classification_url` real-policy verification (#2362) | Pre-existing deferred sub-issue from Epic δ; surfaces here only as a boot-gate failure if a still-unverified adapter remains | Epic δ deferred | #2362 |
