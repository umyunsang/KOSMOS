# Research — Epic G · Utils 잔존 정리 (Phase 0)

**Date**: 2026-05-03
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Mandatory Reference Mapping (Constitution Principle I)

Per `docs/vision.md § Reference materials` + Constitution v1.1.1 § I, every design decision in this Epic maps to a primary reference:

| Decision Surface | Layer (Constitution Table) | Primary Reference | Mapped Path | Rationale |
|---|---|---|---|---|
| `sessionTitle.ts` PORT (byte-copy) | Query Engine | `.references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts` (CC 2.1.88, 129 LOC) | byte-copy with swap-1 line-2 import resolution | CC reconstructed source is the canonical Haiku-title implementation; UMMAYA preserves the JSDoc + prompt verbatim |
| `sessionTitle.ts` swap-1 wire | Query Engine secondary | `tui/src/services/api/claude.ts:3270` `queryHaiku` (Spec 2521 byte-copy bridge) | replace `queryHaiku` import resolution only | UMMAYA already has a stable `queryHaiku` that re-routes to FriendliAI K-EXAONE via `getSmallFastModel()` (Spec 2112 K-EXAONE alias) |
| `dateTimeParser.ts` PORT (byte-copy) | Query Engine | `.references/.../utils/mcp/dateTimeParser.ts` (CC 2.1.88, 121 LOC) | byte-copy with swap-1 line-1 import resolution | CC system prompt verbatim (English source per AGENTS.md hard rule); only swap-1 differs |
| Korean fixture mock pattern | TUI testing | `bun:test` + manual `queryHaiku` stub | inject mock via `bun:test`'s `mock.module()` | Existing pattern in `tui/src/services/api/__tests__/` (no new test framework) |
| `yoloClassifier.ts` Path B 분리 | Permission Pipeline | OpenAI Agents SDK guardrail pipeline + CC permission model (`utils/permissions/yoloClassifier.ts`) — note CC source for this file's interior is Anthropic-only and intentionally not re-introduced (Spec 1633 deletion stands); Path B follows Spec 2295 PR #2364 commit c6747dd | extract inline-stub from `permissions.ts:103-145` into sibling module; preserve CC import shape | Constitution § I "Adapt patterns to UMMAYA's domain — do not copy line-for-line" — UMMAYA preserves the auto-mode no-op behavior shipped in Spec 1633, restores CC import structure |
| ADR-009 authoring | (governance) | `docs/adr/ADR-001` ~ `ADR-008` template structure | follow Status / Context / Decision / Consequences / Future trigger 5-section pattern | Existing ADRs in repo establish the format authority |

**Escalation log**: None. All 4 items resolve at primary reference layer; no secondary reference escalation needed.

## R-1 — sessionTitle.ts PORT Strategy

**Decision**: Byte-copy CC `.references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts` (129 LOC) into `tui/src/utils/sessionTitle.ts` with **exactly two** swap-1 deviations:

1. Line 1 JSDoc block: append the SWAP attribution line `// SWAP/llm-swap(2643): queryHaiku target = K-EXAONE via FriendliAI (Spec 2521 byte-copy bridge).` immediately before the first `import` statement (preserves CC line numbering for diff hygiene).
2. Line 18 (CC) `import { queryHaiku } from '../services/api/claude.js'` — already CC-correct; no change needed (UMMAYA preserves the same path via Spec 2521 byte-copy of `services/api/claude.ts`).

**Rationale**: CC's `sessionTitle.ts` calls `queryHaiku` from `../services/api/claude.js`, which UMMAYA has byte-copied (Spec 2521 commit 9d559b9). The function signature in UMMAYA (`tui/src/services/api/claude.ts:3270`) is signature-identical: `(systemPrompt, userPrompt, outputFormat, signal, options) → Promise<AssistantMessage>`. The only UMMAYA-side detail is that `getSmallFastModel()` (line 3307) returns the K-EXAONE alias per Spec 2112 — opaque to `sessionTitle.ts`.

**Alternatives considered**:

- **Reimplement from scratch using UMMAYA-native LLM path**: Rejected. Violates CORE THESIS "byte-identical default". Spec 2521 explicitly chose byte-copy for exactly this reason.
- **Skip the SWAP comment**: Rejected. Audit replays (Spec 2292 / Initiative #2636) need to identify swap-1 deviations grep-able; comment marker is the agreed convention.

**Verification**: `diff .references/.../sessionTitle.ts tui/src/utils/sessionTitle.ts` MUST yield ≤ 1 hunk (the SWAP comment line). All 4 acceptance scenarios in spec US1 testable via `bun test` with mocked `queryHaiku`.

## R-2 — dateTimeParser.ts PORT Strategy

**Decision**: Byte-copy CC `.references/.../utils/mcp/dateTimeParser.ts` (121 LOC) into `tui/src/utils/mcp/dateTimeParser.ts` with **exactly one** swap-1 deviation:

1. Append SWAP comment line (same convention as R-1) before the first `import` statement.

**Rationale**: CC's `dateTimeParser.ts` already imports `queryHaiku` from the relative `../../services/api/claude.js` path. No CC-side identifier needs to be swapped. The system prompt is in English (per CC original) — AGENTS.md § "All source text in English" is preserved unchanged.

**Korean fixture mock pattern**:

```ts
// tui/src/utils/mcp/__tests__/dateTimeParser.test.ts
import { test, expect, mock } from 'bun:test'

mock.module('../../services/api/claude.js', () => ({
  queryHaiku: async ({ userPrompt }: { userPrompt: string }) => {
    if (userPrompt.includes('내일 오후 3시')) {
      return { message: { content: [{ type: 'text', text: '2026-05-04T15:00:00+09:00' }] } }
    }
    if (userPrompt.includes('다음주 월요일 오전 9시')) {
      return { message: { content: [{ type: 'text', text: '2026-05-11T09:00:00+09:00' }] } }
    }
    if (userPrompt.includes('다음주 월요일')) {
      return { message: { content: [{ type: 'text', text: '2026-05-11' }] } }
    }
    return { message: { content: [{ type: 'text', text: 'INVALID' }] } }
  },
}))
```

**Alternatives considered**:

- **Use snapshot tests instead of behavior assertions**: Rejected. Snapshot tests can mask intent regressions; explicit `{success: true, value: 'YYYY-MM-DD'}` assertion is unambiguous.
- **Test against real K-EXAONE in `@pytest.mark.live` style**: Rejected. AGENTS.md hard rule extends "no live API in CI" to LLM calls; live verification belongs in quickstart.md SC-007 manual measurement.

**`elicitationValidation.ts` migration**: lines 10-19 inline stub block deleted; replaced with `import { parseNaturalLanguageDateTime, looksLikeISO8601 } from './dateTimeParser.js'`. Local `DateParseResult` type alias removed (CC's `DateTimeParseResult` is exported from `dateTimeParser.ts`).

## R-3 — Path B Precedent Applicability

**Decision**: Apply Spec 2295 PR #2364 commit c6747dd "Path B" pattern to extract `permissions.ts:103-145` inline stub into sibling `yoloClassifier.ts` module.

**Path B precedent details** (re-read 2026-05-03 from `git log c6747dd`):

- Original problem (Spec 2295): UMMAYA-invented permission fields (`pipa_class`, `auth_level`, etc.) needed removal but Spec 024/025/1636 had referencing dead fields.
- Path A (rejected): pure deletion → invariant breakage.
- Path B (selected): introduce `AdapterRealDomainPolicy` derivation table model (frozen, extra="forbid", 4 fields) + `computed_field` backward-compat shims on adapter metadata. Caller-side (`registry.py`, `routing_index.py`, etc.) updated to consume the new policy surface.

**Mapping to Epic G US3**:

| Path B Element (Spec 2295) | Analog in this Epic |
|---|---|
| `AdapterRealDomainPolicy` Pydantic frozen model | `YoloClassifierResult` TypeScript type alias (matches CC shape) |
| `computed_field` backward-compat shims | `classifyYoloAction` returning `{unavailable: true, shouldBlock: false}` no-op (callers see same shape, UMMAYA-side classifier is silent) |
| Caller-side updates (`registry.py`, etc.) | `permissions.ts` import line replacement (CC import shape restored) |
| Migration log (`adapter-migration-log.md`) | This Epic's `data-model.md` documents the type-shape contract |

**Why Path B (not Path A — pure deletion)**:

- Path A would require deleting `classifyYoloAction` callsites in `permissions.ts:applyPermissionUpdate`/`applyPermissionUpdates`/etc. → larger blast radius, risks unrelated regressions.
- Path B preserves callsite shape; only the import line + sibling module change. Single-Sonnet-teammate-safe (≤ 10 file changes per AGENTS.md).

**Alternatives considered**:

- **Move stub into a test fixture module**: Rejected. Stub is production code (UMMAYA auto-mode = no-op is a runtime contract per Spec 1633), not a test artifact.
- **Use TypeScript `declare module` ambient stub**: Rejected. Adds tsconfig coupling; sibling `.ts` file is simpler.

## R-4 — ADR-009 Template Authority

**Decision**: Author `docs/adr/ADR-009-secureStorage-drop.md` following the 5-section pattern observed in existing ADR-001 ~ ADR-008.

**Existing ADR template inspection** (2026-05-03):

- ADR-001-geocoding-provider.md → Status / Context / Decision / Consequences / (no explicit Future trigger)
- ADR-004-claude-code-sourcemap-port.md → 5 sections incl. revisitation triggers
- ADR-008-plugin-store-org-and-vendored-slsa-verifier.md → 5 sections incl. SLSA verifier upgrade trigger

**Selected template**: 5 sections with explicit "Future trigger" — best matches ADR-004 / ADR-008 (the most recent ADRs that document re-evaluation conditions, mirroring this Epic's "trigger when multi-tenant key arrives" decision shape).

**Rationale**: ADR-009 is a DROP-with-trigger ADR. The Future trigger section is the load-bearing element — without it, the ADR becomes a one-way nullification rather than a deferred decision. Cross-referencing from `decisions.md § S9 Utils` and `scope-S9-utils.md § P0-2~6` per FR-020 ensures the trigger is discoverable from the audit doc tree.

**Alternatives considered**:

- **Inline DROP justification in `decisions.md` only (no ADR file)**: Rejected. ADR is the canonical "decision lives forever" surface; `decisions.md` is the audit-decision summary table. The two layers serve different purposes (audit-time vs. architecture-time).
- **Use Status: Accepted vs. Status: Deferred**: Selected `Status: Accepted` for the DROP itself (the decision "do not implement secureStorage now" is firmly accepted), with the trigger condition documented separately. Deferred status would suggest ambiguity that does not exist.

## R-5 — UMMAYA `queryHaiku` Surface Verification

**Decision**: Confirm UMMAYA `tui/src/services/api/claude.ts:3270` `queryHaiku` is callable with the signature CC's `sessionTitle.ts` and `dateTimeParser.ts` expect.

**Verification** (2026-05-03 grep in worktree):

```ts
// tui/src/services/api/claude.ts:3270
export async function queryHaiku({
  systemPrompt = asSystemPrompt([]),
  userPrompt,
  outputFormat,
  signal,
  options,
}: {
  systemPrompt: SystemPrompt
  userPrompt: string
  outputFormat?: BetaJSONOutputFormat
  signal: AbortSignal
  options: HaikuOptions
}): Promise<AssistantMessage>
```

CC's call sites (sessionTitle.ts:87, dateTimeParser.ts:68) pass exactly this shape. Internally `queryHaiku` calls `queryModelWithoutStreaming` with `getSmallFastModel()` — which returns the K-EXAONE alias per Spec 2112 (`tui/src/utils/model/model.ts:179` `getDefaultHaikuModel`). swap-1 wiring is implicit and complete.

**Implication**: No `services/api/claude.ts` edit needed. Both PORT files just resolve their `queryHaiku` import naturally.

## R-6 — Deferred Items Validation (Constitution Principle VI)

**Spec.md § Scope Boundaries inspection** (2026-05-03):

- "Out of Scope (Permanent)" section: 4 items, no NEEDS TRACKING (permanent exclusions).
- "Deferred to Future Work" table: 5 items, 1 with `#2637` (Epic A in-flight), 4 with `NEEDS TRACKING` (will be resolved by `/speckit-taskstoissues`).

**Spec.md grep for unregistered deferral patterns**:

```
$ grep -n "separate epic\|future epic\|Phase [2-9]\|v2\|deferred to\|later release\|out of scope" specs/2643-utils-residue/spec.md
```

Results (manually inspected):
- Phrase "Phase 5 후속" in deferred table row 5 → registered ✓
- Phrase "UI L2 Phase 4 후속" in deferred table row 3 → registered ✓
- Phrase "TBD (다중 부처 키 등장 시)" in deferred table row 2 → registered with explicit trigger ✓
- All other matches are within the deferred table itself (legitimate references) or in the "Out of Scope (Permanent)" section.

**Result**: PASS. No unregistered deferrals. No constitution Principle VI violations.

## Summary of Phase 0 Findings

| Finding | Status |
|---|---|
| All 4 surface PORT/ADR strategies decided + cited to primary reference | ✓ |
| Korean fixture mock pattern selected (no new test deps) | ✓ |
| Path B precedent re-validated and mapped 1:1 to US3 | ✓ |
| ADR-009 template authority established | ✓ |
| UMMAYA `queryHaiku` API surface verified compatible | ✓ |
| Deferred items table compliant with Constitution VI | ✓ |
| Zero new runtime dependencies confirmed | ✓ |
| No NEEDS CLARIFICATION markers remaining | ✓ |

Phase 0 complete. Proceed to Phase 1 design artifacts.
