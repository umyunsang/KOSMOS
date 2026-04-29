# Contract: Primitive Shape (9-Member ToolDef)

**Feature**: 2294-5-primitive-align | **Date**: 2026-04-29
**Audience**: Sonnet teammates implementing one of `tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive/`.

This document is the **per-primitive specification** every Sonnet teammate must satisfy. Read it together with `research.md § R-2/R-4/R-5` and `data-model.md § E1`.

## Pre-condition

Before any code edit:

- `tui/src/Tool.ts` is **byte-identical** to `.references/claude-code-sourcemap/restored-src/src/Tool.ts`. Do not modify it.
- `tui/src/components/permissions/FallbackPermissionRequest.tsx` is **byte-identical** to the CC counterpart. Do not modify it.

## Required members on every primitive

| Member | Status | Acceptance |
|---|---|---|
| `name` | already present | unchanged |
| `searchHint` | already present | unchanged |
| `maxResultSizeChars` | already present | unchanged |
| `inputSchema` | already present | unchanged shape — keeps backend Pydantic envelope parity (FR-011) |
| `outputSchema` | already present | unchanged |
| `isEnabled()` | already present | unchanged |
| `isConcurrencySafe()` | already present | unchanged |
| `isReadOnly()` | already present | unchanged (true for `lookup`/`verify`; false for `submit`/`subscribe`) |
| `description()` | tighten Korean | citizen-facing Korean string suitable for direct LLM display; ≤ 240 chars |
| `prompt()` | already present | unchanged unless Korean tone needs nudge — keep terse |
| `mapToolResultToToolResultBlockParam` | already present | unchanged |
| `renderToolUseMessage()` | already present | unchanged |
| `call()` | already present | **unchanged envelope** — adapter resolution moves to validateInput; call re-resolves in O(1) |
| **`isMcp`** | **NEW** | literal `false` for native primitives |
| **`validateInput()`** | **NEW** | see § validateInput contract below |
| **`renderToolResultMessage()`** | **NEW** | see § renderToolResultMessage contract below |

## `validateInput()` contract

**Signature** (per `tui/src/Tool.ts` :489):

```ts
async validateInput(input: In, context: ToolUseContext): Promise<ValidationResult>
```

**Pre-conditions**:
- `input` has already passed zod schema validation (caller-side).
- `context.permissionContext` is a fresh empty-ish `ToolPermissionContext` (per `getEmptyToolPermissionContext`).

**Steps** (canonical, per primitive):

1. Resolve `input.tool_id` (or for lookup `mode==='search'`: skip resolution, no adapter required) against `context.options.tools` registry via `ToolRegistry.lookup()`.
2. If unknown:
   - Return `{result: false, message: "도구 '<id>'을(를) 찾을 수 없습니다.", errorCode: <ENUM>}`.
   - Do NOT throw. Do NOT log.
3. If known:
   - Read adapter's `real_domain_policy.real_classification_url` and `policy_authority`.
   - If either is empty, return `{result: false, message: "도구 '<id>'에 정책 인용 정보가 없어 호출할 수 없습니다.", errorCode: <ENUM>}` — fail closed.
   - Otherwise, populate `context.permissionContext.citations` (or equivalent slot — see `FallbackPermissionRequest.tsx` for the exact field name; do not invent a new field) with the verbatim citation strings.
   - Return `{result: true}`.

**Post-conditions**:
- No side effects (no IPC calls, no permission prompt, no telemetry emit beyond the existing validation span).
- Adapter object is **not** carried across the boundary; `call` re-resolves.

**Error codes**: enumerate as a const-literal union shared across primitives (`AdapterNotFound`, `CitationMissing`, `RestrictedMode`). Live in `tui/src/tools/shared/primitiveCitation.ts` (new helper module).

## `renderToolResultMessage()` contract

**Signature** (per `tui/src/Tool.ts` :566):

```ts
renderToolResultMessage(output: Out, context: ToolUseContext): ReactNode
```

**Steps** (per primitive):

| Primitive | Render shape |
|---|---|
| `LookupPrimitive` | If `output.ok === true`: render adapter name + result count + first-3 summary lines. If `mode==='search'`: render ranked-hit list. If `output.ok === false`: render `output.error.message` in citizen-friendly Korean. |
| `SubmitPrimitive` | If `output.ok === true`: render submission receipt id + ministry name + Korean status text. If `false`: render error message + agency hand-off URL where applicable. |
| `VerifyPrimitive` | If `output.ok === true`: render verification status (verified / pending / failed) + cited authority. If `false`: render rejection reason. |
| `SubscribePrimitive` | If `output.ok === true`: render handle id + cancel CTA + Korean explanation of what was subscribed. If `false`: render error. |

**Non-functional**:
- Return `null` is never acceptable for primitive results (parity with CC; see `Tool.ts` :566 + `AgentTool.tsx` :873).
- Use only `ink`/`react`/`@inkjs/ui` primitives. No new component imports.

## `isMcp` contract

Literal `false` on all 4 primitives. The `true` branch is reserved for community plugins routed via `@modelcontextprotocol/sdk` (Spec 1636 plugin DX); a separate Epic owns that wiring.

## Out-of-scope

- Modifying `inputSchema` / `outputSchema` in any way that changes the IPC envelope (forbidden by FR-011).
- Adding new prompt tokens to `prompt.ts` beyond Korean-tone nudges already covered by `description()`.
- Touching the registry construction site outside of the new boot-guard hook.

## Verification (per primitive)

After implementing, the Sonnet teammate verifies locally:

```bash
cd tui
bun typecheck                                              # 0 errors
bun test src/tools/<Name>Primitive                         # primitive's own tests pass
bun test src/tools/__tests__/registry-boot.test.ts         # boot guard accepts this primitive
bun test src/tools/__tests__/permission-citation.test.ts   # citation surfaces correctly
```

If all four pass, the WIP commit can be made. Lead Opus handles push + PR + CI.
