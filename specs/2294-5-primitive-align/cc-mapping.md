# CC Source Mapping — Epic γ (T002 output)

**Created**: 2026-04-29 | **For**: every Sonnet teammate working on T006-T020

This document is the **single starting reference** for the 4 primitive migrations. It inlines the exact CC `Tool<>` signature so teammates do not need to read the upstream files (which are research-use-only and live outside the worktree at `/Users/um-yunsang/KOSMOS/.references/claude-code-sourcemap/restored-src/`). Per `feedback_cc_source_migration_pattern`, teammates copy from CC and adapt to KOSMOS — never write from scratch.

## Source-of-truth mapping (1:1)

| KOSMOS file | CC reference (research-use only) | Status |
|---|---|---|
| `tui/src/Tool.ts` :362–720 | `.references/claude-code-sourcemap/restored-src/src/Tool.ts` :362–720 | byte-identical port (792 LOC). DO NOT edit. |
| `tui/src/components/permissions/FallbackPermissionRequest.tsx` | `.references/claude-code-sourcemap/restored-src/src/components/permissions/FallbackPermissionRequest.tsx` | byte-identical port. DO NOT edit. |
| `tui/src/tools/AgentTool/AgentTool.tsx` (KOSMOS port) | `.references/claude-code-sourcemap/restored-src/src/tools/AgentTool/AgentTool.tsx` (1397 LOC) | reference implementation pattern of all 9 members |

## CC `Tool<Input, Output, P>` signature (inlined verbatim from `Tool.ts` :362–600)

```ts
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  // ---- Identity ----
  readonly name: string                                   // line 456
  aliases?: string[]                                      // line 371
  searchHint?: string                                     // line 378  (3-10 word phrase, no period)

  // ---- Schema ----
  readonly inputSchema: Input                             // line 394
  readonly inputJSONSchema?: ToolInputJSONSchema          // line 397  (MCP only)
  outputSchema?: z.ZodType<unknown>                       // line 400
  inputsEquivalent?(a, b): boolean                        // line 401

  // ---- Behaviour flags ----
  isConcurrencySafe(input): boolean                       // line 402
  isEnabled(): boolean                                    // line 403
  isReadOnly(input): boolean                              // line 404  (NOTE: takes input!)
  isDestructive?(input): boolean                          // line 406
  interruptBehavior?(): 'cancel' | 'block'                // line 416
  isSearchOrReadCommand?(input): {isSearch, isRead, isList?}  // line 429
  isOpenWorld?(input): boolean                            // line 434
  requiresUserInteraction?(): boolean                     // line 435
  isMcp?: boolean                                         // line 436
  isLsp?: boolean                                         // line 437
  readonly shouldDefer?: boolean                          // line 442
  readonly alwaysLoad?: boolean                           // line 449
  mcpInfo?: {serverName, toolName}                        // line 455
  readonly strict?: boolean                               // line 472
  maxResultSizeChars: number                              // line 466

  // ---- Lifecycle (the canonical flow) ----
  backfillObservableInput?(input): void                   // line 481
  validateInput?(input, context): Promise<ValidationResult>  // line 489  ← Epic γ KEYSTONE
  checkPermissions(input, context): Promise<PermissionResult>  // line 500
  getPath?(input): string                                 // line 506
  preparePermissionMatcher?(input): Promise<(pattern) => boolean>  // line 514
  prompt(options): Promise<string>                        // line 518
  description(input, options): Promise<string>            // line 386  ← Korean text for primitive
  call(args, context, canUseTool, parentMessage, onProgress?): Promise<ToolResult<Output>>  // line 379

  // ---- Render (TUI surface) ----
  userFacingName(input): string                           // line 524
  userFacingNameBackgroundColor?(input): keyof Theme | undefined  // line 525
  isTransparentWrapper?(): boolean                        // line 533
  getToolUseSummary?(input): string | null                // line 539
  getActivityDescription?(input): string | null           // line 546
  toAutoClassifierInput(input): unknown                   // line 556
  mapToolResultToToolResultBlockParam(content, toolUseID): ToolResultBlockParam  // line 557
  renderToolResultMessage?(content, progressMessages, options): React.ReactNode  // line 566  ← Epic γ KEYSTONE
  // renderToolUseMessage signature lives later in Tool.ts (~line 620+) — already implemented in all 4 primitives.
}
```

## ValidationResult discriminator (`Tool.ts` :95–101, already in `tui/src/Tool.ts`)

```ts
export type ValidationResult =
  | { result: true }
  | {
      result: false
      message: string         // Korean diagnostic for the user-facing surface
      errorCode: number       // numeric — see below for KOSMOS allocation
    }
```

## KOSMOS `PrimitiveErrorCode` allocation (T003 introduces this in `tui/src/tools/shared/primitiveCitation.ts`)

```ts
export const PrimitiveErrorCode = {
  AdapterNotFound:  1001,
  CitationMissing:  1002,
  RestrictedMode:   1003,
} as const

export type PrimitiveErrorCode = typeof PrimitiveErrorCode[keyof typeof PrimitiveErrorCode]
```

## What each primitive's `validateInput` MUST do (canonical 5-step recipe)

```ts
async validateInput(
  input: PrimitiveInput,
  context: ToolUseContext,
): Promise<ValidationResult> {
  // 1. SEARCH MODE escape (Lookup only — Submit/Verify/Subscribe always have a tool_id)
  if (input.mode === 'search') {
    return { result: true }                       // BM25 hint resolution happens later in call()
  }

  // 2. Resolve adapter
  const adapter = context.options.tools.find(t => t.name === input.tool_id)
  if (!adapter) {
    return {
      result: false,
      message: `도구 '${input.tool_id}'을(를) 찾을 수 없습니다.`,
      errorCode: PrimitiveErrorCode.AdapterNotFound,
    }
  }

  // 3. Read citation (fail-closed if either field empty)
  const citation = extractCitation(adapter)
  if (!citation.real_classification_url || !citation.policy_authority) {
    return {
      result: false,
      message: `도구 '${input.tool_id}'에 정책 인용 정보가 없어 호출할 수 없습니다.`,
      errorCode: PrimitiveErrorCode.CitationMissing,
    }
  }

  // 4. Populate the permission-context citation slot (read by FallbackPermissionRequest)
  //    Use the existing slot from the CC port — do NOT invent a new field.
  //    See FallbackPermissionRequest.tsx for the exact field name.
  ;(context as MutableForCitation).permissionContext = {
    ...context.permissionContext,
    citations: [citation],   // exact field name verified in FallbackPermissionRequest.tsx
  }

  // 5. Pass
  return { result: true }
}
```

> **Note on field name in step 4**: The Sonnet teammate must verify the exact slot name (`citations`, `policyContext`, `realDomainPolicy`, …) by reading `tui/src/components/permissions/FallbackPermissionRequest.tsx` once at the start of T006. CC's port lives at the byte-identical path and was committed earlier in Spec 2293. If the slot does not exist, the teammate widens the `ToolPermissionContext` type minimally (still no new dependency) and pipes it through — but only if necessary; reusing an existing slot is preferred.

## What each primitive's `renderToolResultMessage` MUST do

| Primitive | On `output.ok === true` | On `output.ok === false` |
|---|---|---|
| Lookup | `<Box>` with adapter-name + result count + first-3 summary lines (mode='fetch'); ranked-hit list (mode='search'). | Korean error message in citizen-friendly tone. |
| Submit | Submission receipt id + ministry name + Korean status text + agency hand-off URL when applicable. | Error message + agency hand-off URL when applicable. |
| Verify | Verification status (verified / pending / failed) + cited authority. | Rejection reason. |
| Subscribe | Handle id + cancel CTA + Korean explanation of what was subscribed. | Error message. |

Use only `ink` / `react` / `@inkjs/ui` primitives — **no new imports**.

## isMcp value

Literal `false` on all 4 primitives (Epic γ scope; `true` is reserved for community plugin primitives via `@modelcontextprotocol/sdk` — Spec 1636 / deferred #2392).

## Out of scope for any primitive task

- `inputSchema` / `outputSchema` shape changes (envelope stability — FR-011).
- `prompt()` body rewrite — only Korean tone tightening of the existing string.
- `call()` body rewrite — only re-resolve the adapter via `ToolRegistry.lookup` (cheap, idempotent) and yield the existing `PrimitiveOutput` envelope.
- `FallbackPermissionRequest.tsx` — byte-identical CC port; do not modify.
- `tui/src/Tool.ts` — byte-identical CC port; do not modify.

## Verification per primitive

```bash
cd tui
bun typecheck                                                 # 0 errors
bun test src/tools/<Name>Primitive                            # primitive tests pass
bun test src/tools/__tests__/registry-boot.test.ts            # boot guard accepts (after Phase 4)
bun test src/tools/__tests__/permission-citation.test.ts      # citation surfaces correctly (after Phase 5)
```

If all four pass, the WIP commit can be made. Lead Opus handles push + PR + CI.
