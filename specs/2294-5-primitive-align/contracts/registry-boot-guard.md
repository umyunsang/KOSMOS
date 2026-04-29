# Contract: ToolRegistry Boot Guard

**Feature**: 2294-5-primitive-align | **Date**: 2026-04-29
**Audience**: Sonnet teammate implementing `tui/src/services/toolRegistry/bootGuard.ts` and `tui/src/tools/__tests__/registry-boot.test.ts`.

## Purpose

Provide a single fail-closed entry point that runs once at process boot and verifies:

1. Every registered `Tool` exposes the 9-member contract from spec FR-001.
2. Every adapter-routed `Tool` carries a non-empty `real_classification_url` and `policy_authority` from `AdapterRealDomainPolicy` (spec FR-009).

Failure halts the process with a Korean diagnostic and exit code 1; success emits a single OTEL-tagged log line.

## Function signature

```ts
// tui/src/services/toolRegistry/bootGuard.ts
import type { Tool } from '../../Tool.js'

export type BootResult =
  | { ok: true; entries: number; primitives: number; adapters: number; durationMs: number }
  | { ok: false; offendingTool: string; missingFields: string[]; diagnostic: string }

export function verifyBootRegistry(
  registry: ReadonlyMap<string, Tool<unknown, unknown>>,
): BootResult
```

## Behaviour

1. **Walk every entry** in registration order (deterministic for snapshot tests).
2. **For each entry, assert non-undefined** on the 9 members:
   - `name`, `description`, `inputSchema`, `isReadOnly`, `isMcp`, `validateInput`, `call`, `renderToolUseMessage`, `renderToolResultMessage`.
3. **Function-vs-property check**: `description`, `isReadOnly`, `validateInput`, `call`, `renderToolUseMessage`, `renderToolResultMessage` must be functions; `isMcp` must be a boolean (not undefined); `inputSchema` must satisfy `instanceof ZodType` or have `_def` set.
4. **For adapter-routed entries** (those whose tool object carries `real_domain_policy` metadata):
   - `real_domain_policy.real_classification_url` must be a non-empty string starting with `http`.
   - `real_domain_policy.policy_authority` must be a non-empty string.
5. **On any failure**: return `{ ok: false, offendingTool: <name>, missingFields: [...], diagnostic: <Korean message naming both> }`. Caller exits with code 1.
6. **On success**: return `{ ok: true, entries: 22, primitives: 4, adapters: 18, durationMs: <observed> }`. Caller emits one OTEL-tagged line and continues.

## Diagnostic format

Korean diagnostic for the `offendingTool` failure case:

```text
[KOSMOS][bootGuard] 도구 '<tool_id>' 등록 검증 실패. 누락 필드: <missingFields.join(', ')>.
KOSMOS는 9-member ToolDef 계약을 준수하는 도구만 부팅 시점에 받아들입니다.
참조: specs/2294-5-primitive-align/contracts/primitive-shape.md
```

Korean diagnostic for missing citation:

```text
[KOSMOS][bootGuard] 어댑터 '<tool_id>'에 real_classification_url 또는 policy_authority가 비어 있습니다.
KOSMOS는 정책 인용을 발명하지 않습니다 — 기관이 공개한 URL이 필수입니다.
참조: docs/security/tool-template-security-spec-v1.md, AGENTS.md § CORE THESIS
```

## Test plan (`registry-boot.test.ts`)

The test file lives at `tui/src/tools/__tests__/registry-boot.test.ts` and covers:

| Case | Expected |
|---|---|
| Real registry boot | `{ ok: true, entries: 22, primitives: 4, adapters: 18 }`, durationMs ≤ 200. |
| Synthetic registry with a primitive missing `renderToolResultMessage` | `{ ok: false, offendingTool: 'lookup', missingFields: ['renderToolResultMessage'] }`, diagnostic contains the Korean string. |
| Synthetic registry with an adapter missing `real_classification_url` | `{ ok: false, offendingTool: '<adapter_id>', missingFields: ['real_classification_url'] }`. |
| Synthetic registry where one tool has `isMcp: undefined` | `{ ok: false, missingFields: ['isMcp'] }` — explicit boolean is required. |

## Performance budget

`durationMs ≤ 200` for 22-entry walk on a developer laptop (spec SC-002). Implementation note: a single forEach with early return on first failure stays well under this budget; the budget exists to flag accidental N² loops or synchronous IPC calls inserted into the guard.

## Non-goals

- The guard does NOT validate `inputSchema` / `outputSchema` *content* (zod handles that). It only checks presence.
- The guard does NOT call any tool's `validateInput` or `call`. It is structural-only.
- The guard does NOT emit a Langfuse span (Spec 021 covers tool-call spans, not registry-boot spans).

## Integration point

Inside the existing registry construction path (caller located by Lead Opus during /speckit-tasks dispatch design):

```ts
// after all register() calls have completed
const result = verifyBootRegistry(toolRegistry.entries())
if (!result.ok) {
  console.error(result.diagnostic)
  process.exit(1)
}
console.log(
  `tool_registry: ${result.entries} entries verified ` +
  `(${result.primitives} primitives, ${result.adapters} adapters) in ${result.durationMs}ms`,
)
```

The Sonnet teammate inserts this snippet at the existing boot site; the teammate does NOT redesign the boot pipeline.
