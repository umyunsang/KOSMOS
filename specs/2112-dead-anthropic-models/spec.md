# Feature Specification: P1 Dead Anthropic Model Matrix Removal

**Feature Branch**: `2112-dead-anthropic-models`
**Epic**: [#2112](https://github.com/umyunsang/KOSMOS/issues/2112)
**Phase**: P1 (per `docs/requirements/kosmos-migration-tree.md § Execution Phase`)
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description: "KOSMOS Phase P1: remove dead Anthropic model ID matrix (~235 refs across `tui/src/utils/model/modelOptions.ts` 146, `tui/src/utils/model/model.ts` 81, `tui/src/services/mockRateLimits.ts` 88) and migrate every model lookup to the canonical `LGAI-EXAONE/K-EXAONE-236B-A23B` single-branch path established at `tui/src/utils/model/model.ts:179,187` and `src/kosmos/llm/config.py:37`."

**Canonical references**:
- `docs/vision.md § 3` — Claude Code reference thesis (six-layer harness)
- `docs/requirements/kosmos-migration-tree.md § L1-A.A1` — single-fixed FriendliAI provider
- `docs/requirements/kosmos-migration-tree.md § L1-A.A3` — native EXAONE function calling
- `docs/requirements/kosmos-migration-tree.md § L1-A.A4` — context, prompts, compaction
- `docs/requirements/kosmos-migration-tree.md § Execution Phase` — `P1 · Dead code elimination — ant-only · feature() · migration · telemetry`
- `AGENTS.md § Hard rules` — zero new runtime dependencies invariant

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen sees no Anthropic-shaped model selection (Priority: P1)

A KOSMOS citizen launches the TUI and asks a Korean public-service question. Behind the scenes the harness must resolve "the model" to exactly one identifier — `LGAI-EXAONE/K-EXAONE-236B-A23B` — without ever touching dead Anthropic name-pattern dispatch tables. The citizen never observes Sonnet/Opus/Haiku model selection language, never sees Anthropic-shaped rate-limit errors, never receives a "claude-3-..." model identifier in any error message or session metadata.

**Why this priority**: This is the entire feature. The TUI today still walks Anthropic name-pattern dispatch tables (15+ branches in `firstPartyNameToCanonical`) and ships an `[ANT-ONLY]` rate-limit mock fixture (`mockRateLimits.ts`) that refers to header schemas the upstream FriendliAI provider does not emit. Every byte of that dead matrix is a maintenance liability and a future production-incident risk if a model-selection branch ever fires.

**Independent Test**: A reviewer can run `rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' tui/src/utils/model/ tui/src/services/mockRateLimits.ts tui/src/services/rateLimitMocking.ts` after the change ships and observe **zero hits**. They can run `bun run tui`, send "Hi" → observe a Korean reply paint, send "강남역 어디?" → observe a `lookup` primitive call followed by a synthesised reply, with no model-selection prompt and no Anthropic-shaped error.

**Acceptance Scenarios**:

1. **Given** a fresh KOSMOS install with `KOSMOS_FRIENDLI_TOKEN` set, **When** the citizen launches `bun run tui` and types "Hi", **Then** the model resolution path produces exactly the string `LGAI-EXAONE/K-EXAONE-236B-A23B` and the citizen receives a Korean-language reply with no model-selection language anywhere in the transcript.
2. **Given** the same fresh install, **When** the citizen types "강남역 어디?" and the LLM elects to call the `lookup` primitive, **Then** the tool round-trip completes, the synthesised reply paints, and no Anthropic-shaped error envelope (no `anthropic-ratelimit-unified-*` headers, no Sonnet/Opus/Haiku decision branch) appears in observability traces.
3. **Given** a developer running the post-change repo, **When** they execute the regex audit `rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' tui/src/utils/model/ tui/src/services/mockRateLimits.ts tui/src/services/rateLimitMocking.ts`, **Then** the command exits with zero matches.
4. **Given** a developer running the post-change repo, **When** they execute `bun test` and `uv run pytest`, **Then** the suites report no fewer than 984 passing TS tests and 437 passing Python tests respectively (the Epic #2077 baseline as of commit 692d1c3).

---

### User Story 2 — Maintainer reads a model-selection path that has one branch (Priority: P2)

A KOSMOS maintainer opens `tui/src/utils/model/model.ts` to extend it for a future feature (e.g. adding a second harness model in P5+). They see exactly one model-resolution path that returns the K-EXAONE constant; they do not have to read 15+ Anthropic name-pattern branches to understand "which branch fires today."

**Why this priority**: Reduces cognitive load and eliminates the risk of a future maintainer modifying the wrong branch. Quality-of-life improvement that follows from User Story 1's deletions.

**Independent Test**: A reviewer can `wc -l tui/src/utils/model/model.ts` after the change and observe a meaningful reduction (target: ≥40% line reduction in the file, from 598 to ≤360 lines). They can read `firstPartyNameToCanonical` and confirm it contains at most one canonical-name return path.

**Acceptance Scenarios**:

1. **Given** the post-change `tui/src/utils/model/model.ts`, **When** a maintainer reads the `firstPartyNameToCanonical` function (or its replacement), **Then** the function body contains a single canonical-name return path keyed on K-EXAONE detection, with no claude-opus/claude-sonnet/claude-haiku/claude-3 branches.
2. **Given** the post-change `tui/src/utils/model/modelOptions.ts`, **When** a maintainer reads the file, **Then** model-option construction does not depend on Anthropic-specific defaults helpers (`getDefaultSonnetModel`/`getDefaultOpusModel`/`getDefaultHaikuModel`) — these helpers are either removed or collapsed into a single thin alias to the K-EXAONE main-loop default.

---

### User Story 3 — Auditor verifies zero new runtime dependencies (Priority: P2)

A reviewer (Codex automated review or human) inspects the diff and confirms that AGENTS.md's hard rule "Never add a dependency outside a spec-driven PR" is honoured: this Epic's PR introduces zero new keys in `tui/package.json` `dependencies` / `devDependencies` and zero new entries in `pyproject.toml` `dependencies`.

**Why this priority**: AGENTS.md hard rule. A dependency-only sweep is fast to audit and protects supply-chain hygiene. Required for PR merge.

**Independent Test**: A reviewer runs `git diff main...HEAD -- tui/package.json pyproject.toml` and observes either no diff in the dependency sections, or only a strictly-decreasing diff (removals allowed; additions forbidden).

**Acceptance Scenarios**:

1. **Given** the integrated PR, **When** a reviewer runs `git diff main...HEAD -- tui/package.json`, **Then** there is no addition under the `dependencies` or `devDependencies` keys.
2. **Given** the integrated PR, **When** a reviewer runs `git diff main...HEAD -- pyproject.toml`, **Then** there is no addition under the `dependencies` array.
3. **Given** the integrated PR, **When** a reviewer reviews `tui/bun.lock` and `uv.lock` diffs, **Then** any change is attributable solely to existing pinned-version churn, not a new package addition.

---

### Edge Cases

- **What happens when a non-K-EXAONE model name flows in (e.g. via stale `~/.claude/settings.json` or a `KOSMOS_FRIENDLI_MODEL` env override pointing to a typo)?**
  - The collapsed `firstPartyNameToCanonical` MUST fail-safe: short-circuit to a `'k-exaone'` short-name (or equivalent) rather than throw. The session continues using the configured-model identifier without crashing the TUI.
- **What happens when a developer running an internal `[ANT-ONLY]` build path tries to call into `mockRateLimits.ts` after this Epic ships?**
  - The file is removed entirely. Any reachable caller (the only one in scope is `tui/src/services/rateLimitMocking.ts`, also `[ANT-ONLY]`) is removed in the same commit. Any future re-introduction of a rate-limit mock must be FriendliAI-shaped, not Anthropic-shaped, and must arrive through a fresh spec.
- **How does the system handle a session-continue (`--continue`) where the prior session JSONL recorded an Anthropic model name?**
  - Session-replay treats the recorded model name as advisory metadata, never as a routing decision. On replay, the live LLM client always re-resolves to the canonical K-EXAONE identifier from `LLMClientConfig.model` (validated by `pydantic`).
- **What happens if upstream KOSMOS adds a P5 model-selection feature later?**
  - The single K-EXAONE branch becomes a single-element switch. New models get appended as new switch arms in a future spec. P1's invariant: "today, there is exactly one model" — this remains true until a future spec changes it.
- **How does observability (OTEL `gen_ai.request.model`) behave?**
  - The `gen_ai.request.model` span attribute always carries `LGAI-EXAONE/K-EXAONE-236B-A23B` (set at `src/kosmos/llm/client.py:346` from `self._config.model`). No code path emits an Anthropic model name to OTEL.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST NOT contain any reference (regex match: `claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic`, case-insensitive) inside any file under `tui/src/utils/model/` after this change ships, including code, comments, type definitions, and string literals.
- **FR-002**: The system MUST NOT contain the file `tui/src/services/mockRateLimits.ts` after this change ships.
- **FR-003**: The system MUST NOT contain the file `tui/src/services/rateLimitMocking.ts` after this change ships (paired `[ANT-ONLY]` sole caller of `mockRateLimits.ts`).
- **FR-004**: Every model-selection code path in the TUI layer MUST resolve to the single string `LGAI-EXAONE/K-EXAONE-236B-A23B` when called with no override, sourced from a single declared constant location (`tui/src/utils/model/model.ts:179,187`).
- **FR-005**: The function `firstPartyNameToCanonical(name: ModelName)` (or its replacement) MUST contain at most one canonical-name return path, fail-safe to `'k-exaone'` (or equivalent K-EXAONE short-name) for any non-K-EXAONE input.
- **FR-006**: The functions `getDefaultSonnetModel()`, `getDefaultOpusModel()`, `getDefaultHaikuModel()` (currently exported from `tui/src/utils/model/model.ts`) MUST either be removed entirely OR be reduced to a thin alias returning `getDefaultMainLoopModel()`. The choice between removal and aliasing is bounded by call-site reach: if all callers are inside the SC-1 audit perimeter (`tui/src/utils/model/` ∪ the two removed services files), the helpers MUST be removed; if any caller is outside the perimeter (e.g. inside `tui/src/services/api/claude.ts` which is deferred to P2), the helpers MUST be aliased and annotated with a `[Deferred to P2]` comment that links the follow-up issue.
- **FR-007**: The Anthropic header schema declared in `mockRateLimits.ts` (`anthropic-ratelimit-unified-status`, `anthropic-ratelimit-unified-reset`, `anthropic-ratelimit-unified-representative-claim`, etc., 12+ header keys per the file's `MockHeaders` type) MUST NOT be reintroduced anywhere in the codebase by this change. FriendliAI rate-limit handling lives at the Python `LLMClient` layer (`src/kosmos/llm/client.py:226-280, 411-613`) and requires no TUI-side mock fixture.
- **FR-008**: All `[ANT-ONLY]` markers (`USER_TYPE === 'ant'`, `[ANT-ONLY]` comment headers) found inside the three target files MUST be removed together with the surrounding dead branches. Outside the target files, `[ANT-ONLY]` markers remain untouched (deferred to a separate sweep).
- **FR-009**: The change MUST NOT introduce any new key under `dependencies` or `devDependencies` in `tui/package.json`, and MUST NOT introduce any new dependency entry in `pyproject.toml`.
- **FR-010**: After this change, executing `bun test` from the `tui/` directory MUST report no fewer than 984 passing tests; executing `uv run pytest` from the repo root MUST report no fewer than 437 passing tests. (Baselines from Epic #2077 commit 692d1c3.)
- **FR-011**: After this change, executing `bun run tui` MUST allow a citizen to (a) send "Hi" and observe a Korean-language reply paint, (b) send "강남역 어디?" and observe a `lookup` primitive call followed by a synthesised reply paint. Both flows must complete with no Anthropic-shaped error envelope and no model-selection prompt.
- **FR-012**: All KOSMOS canonical model-related literals MUST remain centralised in their existing source-of-truth locations: `src/kosmos/llm/config.py:37` (Python `LLMClientConfig.model` default), `tui/src/utils/model/model.ts:179` (`getDefaultMainLoopModelSetting`), `tui/src/utils/model/model.ts:187` (`getDefaultMainLoopModel`). This change MUST NOT introduce a new K-EXAONE literal at any other location.
- **FR-013**: The change MUST preserve all KOSMOS-canonical sampling defaults declared at `src/kosmos/llm/client.py:161-164,288-291` (`temperature=1.0, top_p=0.95, presence_penalty=0.0, max_tokens=1024`), per the K-EXAONE 236B-A23B HuggingFace model card recommendation.
- **FR-014**: The change MUST preserve the FriendliAI rate-limit handling at `src/kosmos/llm/client.py:226-280` (non-streaming retry loop), `:411-613` (streaming retry loop), and `:698-728` (`_is_rate_limit_envelope` SSE detector). No change to retry semantics is permitted in this Epic.
- **FR-015**: The change MUST preserve the K-EXAONE thinking-mode env toggle (`KOSMOS_K_EXAONE_THINKING`) at `src/kosmos/llm/client.py:838-844` and the `chat_template_kwargs.enable_thinking` payload field at `:854-858`.

### Key Entities

- **K-EXAONE canonical identifier**: The literal string `LGAI-EXAONE/K-EXAONE-236B-A23B` representing the only LLM model KOSMOS targets in Phase P1. Source-of-truth: `src/kosmos/llm/config.py:37` (Python) and `tui/src/utils/model/model.ts:179,187` (TypeScript). All other locations referencing "the model" MUST resolve through these.
- **Model lookup path**: Any function or expression in the TUI layer that, given a possibly-empty user override, returns a model identifier. Today this includes `getDefaultMainLoopModel()`, `getDefaultMainLoopModelSetting()`, `getSmallFastModel()`, `firstPartyNameToCanonical()`, `getDefaultSonnetModel()`, `getDefaultOpusModel()`, `getDefaultHaikuModel()`, and `isNonCustomOpusModel()` (`tui/src/utils/model/model.ts`). After this change, every such path collapses to the K-EXAONE constant or a fail-safe equivalent.
- **`[ANT-ONLY]` dead-code marker**: A code-comment + bundler convention (`// [ANT-ONLY]` plus `bun:bundle feature()` gates) that strips internal Anthropic dogfood logic from non-ant builds. The two services files in scope (`mockRateLimits.ts`, `rateLimitMocking.ts`) carry this marker and are stripped in production today; this Epic finishes the job by deleting their source.
- **Anthropic rate-limit header schema**: The 12+ header keys declared as `MockHeaders` in `tui/src/services/mockRateLimits.ts:12-41` (`anthropic-ratelimit-unified-status`, `anthropic-ratelimit-unified-reset`, `anthropic-ratelimit-unified-representative-claim`, `anthropic-ratelimit-unified-overage-status`, …). The provider KOSMOS targets (FriendliAI) does not emit these headers, so the schema has no production analogue and is removed wholesale.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A code-search audit covering `tui/src/utils/model/`, `tui/src/services/mockRateLimits.ts`, and `tui/src/services/rateLimitMocking.ts` returns **zero matches** for the case-insensitive regex `claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic`. (After this Epic ships, the latter two files do not exist, so the audit reduces to `tui/src/utils/model/` only.)
- **SC-002**: Tracing every external caller of model-selection helpers (the 9 caller files identified in Phase 0 research: `tui/src/memdir/findRelevantMemories.ts`, `tui/src/utils/attachments.ts`, `tui/src/utils/model/model.ts`, `tui/src/utils/model/agent.ts`, `tui/src/utils/model/modelOptions.ts`, `tui/src/commands/insights.ts`, `tui/src/services/tokenEstimation.ts`, `tui/src/services/api/claude.ts`, `tui/src/components/messages/AssistantTextMessage.tsx`) confirms each caller resolves to a single K-EXAONE constant — either by direct import of the canonical default or via a thin alias that itself returns the canonical default.
- **SC-003**: A citizen smoke run via `bun run tui` completes two scenarios without Anthropic-shaped errors: (a) "Hi" → Korean-language reply paint within 30 seconds; (b) "강남역 어디?" → `lookup` primitive call → synthesised reply paint within 60 seconds.
- **SC-004**: `bun test` (run from `tui/`) reports ≥ 984 passing tests and `uv run pytest` (run from repo root) reports ≥ 437 passing tests after the change ships, matching or exceeding the Epic #2077 baseline (commit `692d1c3`).
- **SC-005**: `git diff main...HEAD -- tui/package.json pyproject.toml` shows zero additions under `dependencies` / `devDependencies` (TS) and zero additions under the `dependencies` array (Python). Lockfile churn (`tui/bun.lock`, `uv.lock`) is allowed only when attributable to existing pinned-version pulls, not to a new package.
- **SC-006**: Total LOC in the three source-of-truth target files (`tui/src/utils/model/modelOptions.ts`, `tui/src/utils/model/model.ts`, `tui/src/services/mockRateLimits.ts` (latter deleted, counts 0)) drops by **≥ 40 %** vs. the pre-change baseline (pre-change total: 539 + 598 + 882 ≈ 2 019 lines; target: ≤ 1 211 lines remaining across `modelOptions.ts` + `model.ts` only). Drop is dominated by file deletions.

## Assumptions

- The KOSMOS project remains single-fixed on FriendliAI Serverless + `LGAI-EXAONE/K-EXAONE-236B-A23B` for the duration of Phase P1, per `docs/requirements/kosmos-migration-tree.md § L1-A.A1`. Any future move to a multi-model harness is a separate spec under Phase P5+.
- The FriendliAI Tier 1 entitlement (60 RPM) confirmed on 2026-04-15 (memory `project_friendli_tier_wait`) remains active. No tier change is anticipated during P1 implementation.
- The `services/api/claude.ts` Anthropic SDK invocation path remains alive but unreached at runtime — KOSMOS already routes citizen prompts through the Python `LLMClient`. P1 does not delete this surface (deferred to P2) but treats it as a dependency boundary: P1 may keep aliased helpers (`getDefaultSonnetModel`, etc.) alive purely to satisfy `claude.ts`'s import graph until P2 deletes the file.
- The OAuth + subscription-tier helpers (`isClaudeAISubscriber`, `isMaxSubscriber`, `isTeamPremiumSubscriber`) referenced from `modelOptions.ts:4-7` remain unchanged in P1. Their callers' behaviour does not need to be preserved — only their imports do, since the OAuth code is itself targeted for P2 removal.
- Codex inline review (per AGENTS.md § Code review, deprecated `§ Copilot Review Gate`) is the merge gate; any inline `[P1]`/`[P2]`/`[P3]` severity badge must be addressed or formally deferred with a sub-issue before merge.
- `bun test` and `uv run pytest` baselines (984 / 437) are sourced from Epic #2077 closure at commit `692d1c3` (2026-04-27) and represent the highest passing counts on `main` as of spec authoring.
- The Phase 0 deep-research deliverable (`/tmp/kosmos-p1-research/phase0-deep-research.md` during this conversation; copied into `specs/2112-dead-anthropic-models/research.md` during planning) is the binding research artefact for `/speckit-plan`.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **`claude.ai` subscription tier restoration** — KOSMOS does not and will not honour Anthropic subscription tiers (`pro`, `max`, `team_premium`, `claude_ai`). The migration tree (`docs/requirements/kosmos-migration-tree.md § L1-A.A1`) commits to a single-fixed FriendliAI provider; there is no upstream tier system to mirror.
- **Anthropic SDK shape restoration** — The KOSMOS harness is a port of Claude Code's tool-loop architecture, not its Anthropic SDK callsite. The Python `LLMClient` (`src/kosmos/llm/client.py`) is the binding LLM call surface; the leftover `tui/src/services/api/claude.ts` Anthropic SDK file is dead at runtime and removed in P2, not restored in any future P1 spec.
- **Reintroducing an `[ANT-ONLY]` rate-limit mock fixture** — `mockRateLimits.ts` and its caller are deleted permanently. Any future need for a rate-limit mock must be FriendliAI-shaped (per `LLMClient._is_rate_limit_envelope` contract) and must arrive via a fresh spec.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Removal of OAuth + subscription-tier helpers (`isClaudeAISubscriber`, `isMaxSubscriber`, `isTeamPremiumSubscriber`) and their callers in `modelOptions.ts` | Coupled to a full OAuth client removal (`auth.ts`, `oauth/client.ts`) which is a self-contained Epic with its own auth-flow regression risk | P2 — Anthropic → FriendliAI auth/OAuth | [#2146](https://github.com/umyunsang/KOSMOS/issues/2146) |
| Removal of `tui/src/services/api/claude.ts` Anthropic SDK invocation path and its `firstPartyNameToCanonical` callers (and consequently the deletion of any aliased helpers preserved in P1 for import-graph stability) | Anthropic SDK callsite removal is itself a multi-file Epic touching `services/api/claude.ts` (≈ 800 LOC), `services/api/withRetry.ts`, `services/api/errorUtils.ts`, `services/api/promptCacheBreakDetection.ts`. P1 stays scoped to the 3 stated files. | P2 — Anthropic → FriendliAI auth/OAuth | [#2147](https://github.com/umyunsang/KOSMOS/issues/2147) |
| Removal of product-name cosmetic strings (e.g. `Clawd` mascot, brand text in onboarding/help/footer) and migration to KOSMOS UFO mascot text | Cosmetic, user-facing; needs design approval and a small UI pass; safe to ship after the harness is fully FriendliAI-shaped | P3 — Brand cosmetics | [#2148](https://github.com/umyunsang/KOSMOS/issues/2148) |
| Reintroducing a FriendliAI-shaped rate-limit mock fixture for testing developer-facing 429 envelopes (separate from the `[ANT-ONLY]` `mockRateLimits.ts` deleted in this Epic) | Not currently required by any test; would be additive future infrastructure when developers need to exercise FriendliAI 429 paths in TS unit tests rather than via Python integration tests | P5+ — Testing infrastructure | [#2149](https://github.com/umyunsang/KOSMOS/issues/2149) |
| Auditing `[ANT-ONLY]` markers outside the three target files (e.g. in `LogoV2.tsx:2`, in scattered `feature()` gates) and pruning the residue | Out of P1's stated scope (3-file boundary). A separate dead-code sweep Epic should follow Phase 1633's closure. | P1.5 / P2 — Wider dead-code sweep | [#2150](https://github.com/umyunsang/KOSMOS/issues/2150) |
