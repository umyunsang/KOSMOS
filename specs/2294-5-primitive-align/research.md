# Phase 0 Research: 5-Primitive Align with CC Tool.ts Interface

**Feature**: 2294-5-primitive-align | **Date**: 2026-04-29

This document satisfies AGENTS.md "Reference source rule" — every Phase 0 design decision is mapped to a concrete file:line reference in the constitutional source set.

## R-1 — `Tool<In, Out>` is already byte-identical-ported into KOSMOS

**Decision**: The KOSMOS file `tui/src/Tool.ts` (792 LOC) is **byte-identical** to `.references/claude-code-sourcemap/restored-src/src/Tool.ts` (792 LOC). The Epic-γ goal "verbatim alignment with CC Tool.ts interface" is therefore **already met at the type-system level**. The actual implementation gap is at the **primitive instance layer** — the four primitives consume a partial subset of the contract `ToolDef<In, Out>` exposes.

**Rationale**: Verified by `wc -l` parity, `grep` confirmation that `tui/src/Tool.ts` exports the same surface as the CC counterpart at the same line numbers (`Tool<>` at 362, `isMcp?` at 436, `validateInput?` at 489, `renderToolResultMessage?` at 566, `ToolDef<>` at 721, `buildTool` at 783). The reconstructed CC file under `.references/` and the KOSMOS port live in the same import path tree (`src/Tool.ts`); the import path of `tui/src/tools/LookupPrimitive/LookupPrimitive.ts` line 15 (`import { buildTool, type ToolDef } from '../../Tool.js'`) routes to the byte-identical contract.

**Implication for the spec**: FR-001's "9-member surface" is enforced by the **type system already** for any code that types against `ToolDef<In, Out>`. The new boot-time runtime guard (FR-008) is therefore a **belt-and-suspenders defense**: it catches `model_construct`-style bypass (e.g., a plugin author who casts via `as ToolDef<...>` to dodge TypeScript) and gives a Korean diagnostic instead of a runtime `undefined is not a function` deep in the LLM dispatch path.

**Alternatives considered**:
- _Re-port `Tool.ts` from `.references/`_: rejected — already done; would be a no-op.
- _Forking the contract into a KOSMOS-specific superset_: rejected — violates Constitution § I (Reference-Driven Development) and the AGENTS.md core thesis ("CC + 2 swaps only").

**Reference**: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :362–783; `tui/src/Tool.ts` :362–783.

## R-2 — The real gap: 3 missing optional members on every primitive

**Decision**: Each primitive currently implements `name`, `searchHint`, `maxResultSizeChars`, `inputSchema`, `outputSchema`, `isEnabled`, `isConcurrencySafe`, `isReadOnly`, `description`, `prompt`, `mapToolResultToToolResultBlockParam`, `renderToolUseMessage`, `call`. Each one omits the three optional Tool members the spec calls out: `validateInput?`, `renderToolResultMessage?`, and the explicit `isMcp` flag (defaults to `undefined`/falsy under the current shape).

**Rationale**: Verified by reading `tui/src/tools/LookupPrimitive/LookupPrimitive.ts` (145 LOC) and confirmed by file-size parity with the other three primitives (132 / 129 / 135 LOC) — each one was created from the same template at Epic #1634 P3 commit (P3 MVP stub note in line 9 comment). Adding `validateInput` is the architectural keystone: it is the canonical place for adapter-resolution + BM25 hint resolution + fail-closed `tool_id` rejection per CC's `Tool.ts` :489 contract ("Determines if input is structurally valid before any side effects"). Adding `renderToolResultMessage` is the keystone for citizen-facing Korean rendering; the current `renderToolUseMessage` only displays the call, not the result.

**Implication for design**: The four primitive files grow by roughly 70–120 LOC each (validateInput body, renderToolResultMessage body, isMcp = false constant). Total stays well under the SC-006 1500-net-LOC budget once the boot guard and three test files are added.

**Alternatives considered**:
- _Make validateInput a no-op pass-through and let `call` handle adapter resolution_: rejected — that puts the BM25 hint discovery (Spec 022) inside the side-effecting code path, so a bad `tool_id` would only error after IPC dispatch instead of failing at the validation phase. CC's `Tool.ts` line 489 comment is explicit that `validateInput` MUST run before any side effects.
- _Implement `renderToolResultMessage` as an inline string in `call`'s yielded envelope_: rejected — `call` already yields the structured `PrimitiveOutput` envelope (FR-011, must stay envelope-stable). The renderer must be a separate callable so the TUI can re-render on `Ctrl-O` expand/collapse without re-dispatching.

**Reference**: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :489 (validateInput contract), :566 (renderToolResultMessage contract), :436 (isMcp contract); `.references/claude-code-sourcemap/restored-src/src/tools/AgentTool/AgentTool.tsx` :1–1397 (full reference implementation pattern).

## R-3 — The boot guard is a separate module, not inlined

**Decision**: The shape-and-citation guard lives at `tui/src/services/toolRegistry/bootGuard.ts` and is invoked by the existing registry construction path. It exposes one function `verifyBootRegistry(registry: ToolRegistry): BootResult` that walks every entry, asserts each one's `name`, `description`, `inputSchema`, `isReadOnly`, `isMcp`, `validateInput`, `call`, `renderToolUseMessage`, `renderToolResultMessage` are non-undefined (the 9 members from spec FR-001), and additionally asserts that any entry tagged `is_live` or `is_mock` has a non-empty `real_classification_url` from its `AdapterRealDomainPolicy` block. Failure produces a Korean diagnostic naming the offending tool id and the missing field, exits with code 1 in production and throws in test.

**Rationale**: Splitting the guard from the registry constructor is the minimum-diff way to make the guard unit-testable in isolation (Story 2's `registry-boot.test.ts` mounts a fake registry with deliberately broken entries). The CC equivalent of "registry validates its members at boot" lives in `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :721–792 (`buildTool`) — which only does compile-time enforcement; KOSMOS adds the runtime enforcement on top. This is a **KOSMOS extension** under Constitution § I "do not copy line-for-line; adapt patterns to KOSMOS's domain" — the rationale (plugin contributors via Spec 1636) is documented in the existing Spec 1636 acceptance bundle (50-item validation matrix Q9 plugin checks).

**Alternatives considered**:
- _Inline the assertions in the registry constructor_: rejected — breaks unit-test isolation and bloats the existing constructor with conditional branches.
- _Defer guard to first-use of each tool_: rejected — turns a fail-closed startup error into a runtime mid-conversation error, violating Constitution § II ("Fail-Closed Security").

**Reference**: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :721 (`ToolDef`), :783 (`buildTool`); existing Spec 1636 plugin-validation pattern under `tests/fixtures/plugin_validation/checklist_manifest.yaml` Q9 (precedent for boot-time fail-closed validation).

## R-4 — `validateInput` is the BM25 hint + adapter-resolution entry point

**Decision**: Move BM25 hint discovery (Spec 022) and adapter resolution from inside `call`'s side-effecting prelude into `validateInput`'s pure-function pass. `validateInput` returns `{result: false, message: <Korean diagnostic>, errorCode: <number>}` for unknown `tool_id`, restricted-mode misuse, or empty params; otherwise `{result: true}`. Adapter object is **not** carried across the boundary — `call` re-resolves from the same in-memory map (idempotent, ≤ 1 ms). This keeps the function-shape match with CC `Tool.ts` :489–494 verbatim.

**Rationale**: CC's `Tool.ts` :495 comment says "Determines if the user is asked for permission. Only called after validateInput() passes." — meaning `validateInput` is the **gate before** the permission prompt. Putting adapter resolution there means the permission prompt is built from the adapter's `real_classification_url` (FR-007) at the right moment; if validation fails, the LLM gets `AdapterNotFoundError` with no permission UI shown (spec edge-case "Adapter not in registry"). Re-resolving the adapter inside `call` is cheap (in-memory lookup) and avoids stuffing adapter handles across the validation/call boundary, which would complicate cancellation semantics.

**Alternatives considered**:
- _Pass adapter object across `validateInput → call`_: rejected — couples validation and dispatch, complicates cancellation, breaks parity with CC pattern (which keeps validateInput pure).
- _BM25 hint stays in `call`_: rejected — splits adapter-resolution logic across two surfaces; one fails fast (validation), the other fails only after permission prompt is shown, leading to confused user-facing error timing.

**Reference**: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :489–494 (validateInput contract); existing Spec 022 BM25 retrieval doc + `kosmos.tools.registry.ToolRegistry.lookup_adapter()`.

## R-5 — `renderToolResultMessage` is per-primitive Korean renderer; FallbackPermissionRequest is unchanged

**Decision**: Each primitive ships its own `renderToolResultMessage` that takes the structured `PrimitiveOutput` envelope and returns a `ReactNode` of Korean citizen-facing text (lookup → list rendering with adapter-name + result count + first-3-summary; submit → submission receipt id + ministry name; verify → verification status + cited authority; subscribe → handle id + cancel CTA). The CC `FallbackPermissionRequest` component is unchanged — it already renders the citation strings passed in via `permissionContext.citations`; the new code only sets that field with adapter-supplied content.

**Rationale**: CC's `Tool.ts` :566–582 says `renderToolResultMessage` and `userFacingName` are independent concerns from permission rendering. The spec's FR-006 forbids custom permission components — KOSMOS uses CC's `FallbackPermissionRequest` byte-identical (it lives at `tui/src/components/permissions/FallbackPermissionRequest.tsx`, ported in Spec 2293). Each primitive's `validateInput` populates the citation slot in the `ToolUseContext`'s `permissionContext` field; the Fallback component reads it and renders. No new component is introduced.

**Alternatives considered**:
- _One shared renderer for all 4 primitives_: rejected — citizen-facing Korean text differs structurally per primitive (lookup is read; submit is action; verify is yes/no; subscribe is handle). Forcing a single renderer either bloats it with `switch (mode)` or loses information.
- _Render into `call`'s yielded chunks instead of a separate function_: rejected — same reason as R-2: re-render must be cheap (Ctrl-O expand/collapse).

**Reference**: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :566–582 (renderToolResultMessage contract); `tui/src/components/permissions/FallbackPermissionRequest.tsx` (already ported byte-identical from CC); spec FR-006/FR-007.

## R-6 — PTY smoke pattern reuses Spec 1979 / 2293 / 2112 harness

**Decision**: PTY transcript captured with `expect`. Script lives at `specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.expect`; output text log at `specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt`. Optional `.gif` via vhs is companion-only (not LLM-greppable). Skeleton: spawn `bun run tui` → assert `KOSMOS` branding → send `의정부 응급실 알려줘\r` → wait 8 s → send `y` (permission accept) → wait 4 s → assert "응급실" + adapter result block in transcript → send `\003\003` → expect eof.

**Rationale**: Memory `feedback_vhs_tui_smoke` (text log primary) + `feedback_pr_pre_merge_interactive_test` (mandatory before PR) + the v6 handoff doc all converge on this pattern. Specs 1979, 2293, and 2112 use the same harness — no new tooling needed.

**Alternatives considered**:
- _vhs-only with .gif primary_: rejected — binary, not LLM-greppable, fails the memory rule.
- _Headless integration test (no PTY)_: rejected — wouldn't catch stale-import / dead JSX-path regressions per memory `feedback_pr_pre_merge_interactive_test`.

**Reference**: existing `specs/2293-ui-residue-cleanup/scripts/` + `specs/2112-dead-anthropic-models/scripts/` patterns; memory `feedback_vhs_tui_smoke` + `feedback_pr_pre_merge_interactive_test`.

## R-7 — Span-attribute parity is verifiable by snapshot

**Decision**: New test `tui/src/tools/__tests__/span-attribute-parity.test.ts` mounts a primitive, dispatches a synthetic `lookup(mode='fetch', tool_id='nmc_emergency_search', ...)` call, and snapshots the OTEL span's attribute set. Snapshot baseline is the pre-refactor span emitted from main `c6747dd`. SC-007 passes when post-refactor snapshot is byte-identical to baseline plus optionally the new `kosmos.adapter.real_classification_url` attribute (Epic δ extension introduced in commit `c6747dd`).

**Rationale**: Spec 021 OTEL infrastructure is stable; the only span-attribute drift risk is from the new adapter-citation extension. Snapshot test is the simplest safe verification.

**Alternatives considered**:
- _Manual span reading via Langfuse UI_: rejected — not reproducible in CI; out-of-band evidence.
- _Skip span verification, rely on bun test_: rejected — span attributes are part of L1-A's observability contract (Spec 021); a refactor that silently drops one is a regression.

**Reference**: Spec 021 OTEL attribute schema (`kosmos.tool.id`, `kosmos.tool.mode`, etc.); commit `c6747dd` (Epic δ — adds `kosmos.adapter.real_classification_url`).

## Deferred-Item Validation (Constitution § VI gate)

| Spec deferral | Tracking |
|---|---|
| 9 new Mock adapters (Singapore APEX style) + DelegationToken/Context schema | Linked to Epic ε #2296 (verified OPEN via gh GraphQL 2026-04-29 preflight). |
| End-to-end PTY scenario (`종합소득세 신고해줘` → verify(modid) → lookup(simplified) → submit(taxreturn)) | Linked to Epic ζ #2297 (verified OPEN). |
| `docs/research/policy-mapping.md` | Linked to Epic ζ #2297. |
| 5 OPAQUE hand-off scenario docs | Linked to Epic ζ #2297. |
| MCP-side primitive permission-UI downgrade pattern | Tagged `NEEDS TRACKING` — `/speckit-taskstoissues` will create a placeholder issue. |
| `prompts/system_v1.md` 5-primitive citizen-friendly tone update | Tagged `NEEDS TRACKING` — `/speckit-taskstoissues` placeholder. |
| Adapter `real_classification_url` real-policy verification (#2362) | Pre-existing Epic δ deferred; surfaces here only as a boot-gate failure if a still-unverified adapter remains. Linked. |

**Free-text deferral scan**: `grep -nE "separate epic|future phase|future epic|v2|out of scope for v1|deferred to" specs/2294-5-primitive-align/spec.md` returns matches only inside the Deferred Items table itself or the Out-of-Scope-Permanent block. **No untracked deferrals.**

**Constitution § VI gate**: PASS.

## Closed NEEDS-CLARIFICATION

None — every Technical Context field was filled deterministically from spec body + AGENTS.md hard rules + existing infrastructure references. Zero NEEDS-CLARIFICATION markers.
