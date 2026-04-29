# Phase 1 Data Model: 5-Primitive Align with CC Tool.ts Interface

**Feature**: 2294-5-primitive-align | **Date**: 2026-04-29

This document records every entity touched by Epic γ, its source-of-truth file, and the fields it must expose so that the boot guard (Story 2) and the citation snapshot (Story 3) can verify behaviour. **No new persistent state** is introduced — every entity is in-memory or already declared in an earlier spec.

## E1 — `Tool<In, Out>` (CC contract; unchanged)

**Source-of-truth**: `tui/src/Tool.ts` :362–720 (byte-identical port of `.references/claude-code-sourcemap/restored-src/src/Tool.ts`).

The 9-member contract that every primitive (and every adapter that registers as a `Tool`) implements:

| Member | Type | Required by Spec | CC line | Purpose |
|---|---|---|---|---|
| `name` | `string` | FR-001 | 363 | Stable LLM-visible identifier (e.g. `"lookup"`). |
| `description` | `() => Promise<string>` | FR-001 + FR-002 | 376 | Citizen-facing Korean string returned to LLM. |
| `inputSchema` | `ZodSchema<In>` | FR-001 + FR-003 | 387 | Discriminated-union zod schema for primitive input. |
| `isReadOnly` | `() => boolean` | FR-001 | 421 | True for `lookup`/`verify`; false for `submit`/`subscribe`. |
| `isMcp` | `boolean` | FR-001 (newly required) | 436 | False for native primitives; reserved `true` for community plugins routed via MCP (out of scope for this Epic, see deferred). |
| `validateInput` | `(input, context) => Promise<ValidationResult>` | FR-001 + FR-004 (newly required) | 489 | Resolves adapter via in-memory ToolRegistry; returns `{result: true}` or `{result: false, message, errorCode}`. |
| `call` | `(input, context) => AsyncGenerator<Out>` | FR-001 + FR-005 | 530 | Yields envelope-stable `PrimitiveOutput`. |
| `renderToolUseMessage` | `(input, context) => ReactNode` | FR-001 | 552 | Renders the call announcement in TUI. |
| `renderToolResultMessage` | `(output, context) => ReactNode` | FR-001 (newly required) | 566 | Renders adapter-result in citizen-facing Korean. |

**Cardinality**: exactly 22 instances at boot — 4 primitives + 18 adapters, all conforming to the same 9-member contract.

**Validation rules**:
- All 9 members must be non-undefined at boot (enforced by `verifyBootRegistry`).
- `name` must be unique across the registry.
- `isMcp` is **explicit** — `undefined` is rejected by the boot guard (per spec FR-001 and Constitution § II fail-closed).

## E2 — `PrimitiveInput` / `PrimitiveOutput` (cross-layer envelope; unchanged)

**Source-of-truth**: `src/kosmos/primitives/__init__.py` (Python, Pydantic v2). TS-side mirror in zod under each primitive's `inputSchema` / `outputSchema`.

**Lookup primitive shape** (from existing `LookupPrimitive.ts` :22–71, retained verbatim):

```ts
input  = { mode: 'search', query, primitive_filter?, top_k? }
       | { mode: 'fetch',  tool_id, params }
output = { ok: true, result: unknown }
       | { ok: false, error: { kind, message } }
```

Submit / verify / subscribe envelopes follow the analogous discriminated-union pattern (existing — see each primitive's current file).

**Validation rules**:
- This Epic does NOT modify the envelope (FR-011). The TS zod schemas already match the backend Pydantic v2 models per Spec 1634 (`primitive-envelope.md § 2`).
- `validateInput` in this Epic operates on the same input shape — it does not re-shape the envelope.

## E3 — `AdapterRealDomainPolicy` (Epic δ output; consumed verbatim here)

**Source-of-truth**: `src/kosmos/tools/policy.py` — frozen Pydantic v2 model added by Epic δ in commit `c6747dd`.

Fields used by this Epic:

| Field | Type | Used by | Why |
|---|---|---|---|
| `real_classification_url` | `HttpUrl` (non-empty after Epic δ migration) | FR-007 + FR-009 | Rendered verbatim in `<PermissionRequest>` body as the policy citation. |
| `policy_authority` | `str` (non-empty) | FR-007 | Rendered as the citation byline (e.g., "출처: 보건복지부 응급의료 운영지침"). |
| `last_verified` | `date` | (informational) | Surfaces in audit ledger; not user-facing. |
| `citizen_facing_gate` | `Literal["public", "consent_required", "personal_id_required", ...]` (computed_field) | (informational) | Used by Spec 024/025/1636 invariants — derived by the policy_derivation table; this Epic only consumes, does not extend. |

**Validation rules**:
- Boot guard rejects any registered tool whose adapter manifest lacks a non-empty `real_classification_url` or `policy_authority` (spec FR-009).
- The other Epic δ-introduced fields (`citizen_facing_gate` derivation, `policy_derivation` table) are consumed read-only — not modified by this Epic.

## E4 — `ToolRegistry` (existing; behaviour extended)

**Source-of-truth**: `tui/src/services/toolRegistry/` (existing) + new `bootGuard.ts`.

| Field / method | New in this Epic? | Purpose |
|---|---|---|
| `register(tool: Tool<In, Out>)` | No | Existing registration entry point (called by primitive module-imports + Python adapter manifest IPC). |
| `lookup(name: string): Tool \| undefined` | No | Existing lookup — used by `validateInput` for adapter resolution. |
| `searchHints(query: string): RankedHit[]` | No | Existing BM25 retrieval (Spec 022). Now invoked from `LookupPrimitive.validateInput` when `mode === 'search'`. |
| `verifyBoot(): BootResult` | **YES — new** | Walks every registered tool, asserts 9-member shape + non-empty citation. Calls `bootGuard.verifyBootRegistry`. |

**State transitions**:
1. Process boot → `register()` called for 4 primitives (TS-side imports) + 18 adapters (Python manifest sync over IPC).
2. After last registration → `verifyBoot()` called once. On failure: process exits with code 1 + Korean diagnostic to stderr; no fallback.
3. Steady state → `lookup()` and `searchHints()` serve every primitive `validateInput` and BM25 search call.
4. No de-registration. No re-boot without process restart.

## E5 — `ToolPermissionContext` (CC type; passed through)

**Source-of-truth**: `tui/src/Tool.ts` :122–138 (already byte-identical CC port).

Carried unchanged into every primitive's `validateInput` + `call`. The new code only **populates** the citation fields (`real_classification_url`, `policy_authority`) on the existing `permissionContext` slot just before returning `{result: true}` from `validateInput` — it does not extend the type itself.

## Relationship diagram

```text
                          ┌──────────────────────┐
                          │  Tool<In, Out> (E1)  │
                          │  (tui/src/Tool.ts)   │
                          └──────────┬───────────┘
                                     │ implements
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
        ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
        │ LookupPrimitive │  │ SubmitPrimitive │  │  18 adapters    │
        │  + 3 missing    │  │  + 3 missing    │  │  (registered    │
        │  members        │  │  members        │  │   via Python    │
        │  added (E1)     │  │  added (E1)     │  │   manifest)     │
        └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                 │ validateInput     │ validateInput      │ validateInput
                 │ resolves via      │ resolves via       │ resolves via
                 ▼                   ▼                    ▼
                          ┌──────────────────────┐
                          │  ToolRegistry (E4)   │ ──► verifyBoot() ──► fail-closed if 9-member or citation missing
                          └──────────┬───────────┘
                                     │ adapter manifest carries
                                     ▼
                          ┌──────────────────────┐
                          │  AdapterRealDomain-  │
                          │  Policy (E3, Epic δ) │ ──► citation rendered in FallbackPermissionRequest
                          └──────────────────────┘
```

## Out-of-scope (per spec)

- The Python `PrimitiveInput`/`PrimitiveOutput` Pydantic schema (E2): unchanged.
- `AdapterRealDomainPolicy` (E3): consumed read-only; Epic δ owns its definition.
- `FallbackPermissionRequest` component: unchanged byte-identical CC port (Spec 2293).
- 18 adapter modules: not edited; only their registered metadata is consumed.
