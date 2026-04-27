# Deferred-marker convention — Epic #2112

**Canonical annotation**: `// [Deferred to P2 — issue #2147]` (TS) · `# [Deferred to P2 — issue #2147]` (Python — N/A in this Epic)

**Anchor issue**: [#2147](https://github.com/umyunsang/KOSMOS/issues/2147) — `[Deferred] services/api/claude.ts Anthropic SDK invocation removal (P2)`.

This is the primary P2 anchor because `services/api/claude.ts` is the file that keeps the alias chain alive in P1; removing it removes the need for the aliased helpers in this Epic.

## Where this marker MUST appear

Per `specs/2112-dead-anthropic-models/tasks.md`:

| Task | Location | Helper / construct |
|---|---|---|
| T009 | `tui/src/utils/model/model.ts:197-279` | `firstPartyNameToCanonical(name)` (collapsed body) |
| T010 | `tui/src/utils/model/model.ts:178-188` (or wherever the helpers live post-edit) | `getDefaultSonnetModel`, `getDefaultOpusModel`, `getDefaultHaikuModel` (thin K-EXAONE aliases) |

## Format examples

**TS function-level annotation**:

```ts
// [Deferred to P2 — issue #2147]: thin alias preserved for services/api/claude.ts import-graph stability.
// Remove together with services/api/claude.ts in Phase P2 (Anthropic → FriendliAI auth/OAuth).
export function getDefaultSonnetModel(): ModelName {
  return getDefaultMainLoopModel()
}
```

**TS in-body annotation**:

```ts
export function firstPartyNameToCanonical(name: ModelName): ModelShortName {
  // [Deferred to P2 — issue #2147]: collapsed Anthropic name-pattern dispatch.
  // P1 fail-safe: K-EXAONE detection only; Anthropic patterns return as-is for the legacy callers
  // in services/api/claude.ts, which are themselves removed in P2.
  return name.toLowerCase().includes('k-exaone') ? 'k-exaone' as ModelShortName : name as ModelShortName
}
```

## Audit hook

Contract C11 of `contracts/audit-contract.md` greps for `[Deferred to P2` near the helper definition; missing annotation = FAIL.
