# Phase 0 Research: LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Date**: 2026-05-01

## Reference Mapping (Constitution § I — mandatory)

Every design decision in this Epic traces to a concrete reference. Per `docs/vision.md § Reference materials` and AGENTS.md hard rule.

### R-1 — Methodology choice: CC byte-copy + bounded swap (vs. audit-and-fix)

**Decision**: Use strict CC byte-copy as the rebuild's first commit per Procedure-A file, then layer bounded swap commits with categorical labels.

**Rationale**:
- AGENTS.md CORE THESIS: "KOSAX = CC-original harness + 2 swaps". The thesis explicitly calls for byte-equivalence except at the 2 swap points. Audit-and-fix drifts away from the thesis with each unlabeled change.
- Memory `feedback_cc_source_migration_pattern`: "CC 소스맵 복사 → 마이그레이션. 새로 작성 X." This memory was already documenting the right pattern; this Epic enforces it.
- Memory `feedback_no_stubs_remove_or_migrate`: "CC 잔재의 누락 모듈은 스텁 X. KOSAX 미사용 기능은 import + call site 모두 제거, 사용 기능은 KOSAX 등가물로 마이그레이션". Stubs and half-states are forbidden.
- Empirical evidence (2026-05-01): 3 silent feature drops were found in supposedly-stable swap-surface files (`_ensure_tool_registry`, `<turn_order>`, `chunk.thinking`). Audit-and-fix found them only because user testing surfaced symptoms; an unknown number of similar drops are still latent.

**Alternatives considered**:
- Audit-and-fix patch on top of current KOSAX state — rejected because it caused the problem this Epic solves (silent drops accumulate; review is per-PR, not per-file-against-baseline).
- Full file rewrite from scratch ignoring CC — rejected because it violates AGENTS.md CORE THESIS and discards the byte-identical inheritance KOSAX already has on 1531 files.
- Multi-model split architecture (separate reasoning + execution models) — evaluated 2026-05-01 against EXAONE-Deep / EXAONE-4.5-33B, rejected per spec § Out of Scope.

### R-2 — Streaming handler (text + thinking + tool_use)

**Decision**: Byte-copy CC `services/api/claude.ts:1980-2295` into `tui/src/services/api/claude.ts`. Replace `@anthropic-ai/sdk` import with KOSAX's IPC adapter via `tui/src/sdk-compat.ts` (already exposes `KosaxRawMessageStreamEvent` etc.).

**Rationale**:
- `tui/src/sdk-compat.ts` ALREADY mimics the Anthropic SDK shape (verified 2026-05-01: `KosaxContentBlockParam`, `KosaxRawMessageStreamEvent`, `KosaxUsage`, etc. all exist). The byte-copy of claude.ts can reference these instead of `@anthropic-ai/sdk` with a minimal `SWAP/llm-provider` diff at the import line.
- `KosaxThinkingDelta` was added to `llmTypes.ts` 2026-05-01 to extend the discriminated union — this stays as a `SWAP/llm-provider` diff (KOSAX-only type for K-EXAONE reasoning channel).
- CC's streaming handler structure (message_start → content_block_start → content_block_delta* → content_block_stop → message_delta → message_stop) is universal across providers; the byte-copy preserves it; only the input adapter changes.

**Alternatives considered**:
- Maintain `tui/src/ipc/llmClient.ts` as the standalone re-implementation — rejected because the streaming-handler logic in claude.ts and the duplicated logic in llmClient.ts is a known drift hotspot (3 silent drops originated here).
- Drop sdk-compat aliases and use Anthropic SDK directly with FriendliAI's OpenAI-compat shim — rejected because FriendliAI's OpenAI-compat does not match Anthropic's stream event taxonomy (Anthropic uses `content_block_*`; OpenAI uses `delta.content`/`delta.tool_calls`). The KOSAX-side adapter is necessary.

### R-3 — Agentic loop (per-turn message_id, tool dispatch, role=tool injection)

**Decision**: Behavior-mirror CC `QueryEngine.ts` + `query.ts:120-410` in `src/kosax/ipc/stdio.py:_handle_chat_request`. Each handler in stdio.py cites the CC analog's line range.

**Rationale**:
- CC's `QueryEngine.ts` is the canonical agentic loop reference per AGENTS.md L1-A. It establishes: (a) per-turn `message_id`, (b) structured `tool_calls` dispatch, (c) `role="tool"` message injection between turns, (d) max_turns termination, (e) thinking blocks NEVER fed back to LLM (filtered).
- `stdio.py` is KOSAX-only (no direct CC equivalent because KOSAX uses stdio JSONL IPC, not direct SDK calls). Procedure B applies.
- The just-applied `_ensure_tool_registry` lazy-init (2026-05-01) is a `SWAP/llm-provider` diff — it adapts CC's "registry assumed populated at SDK construction" to KOSAX's "registry populated lazily on first IPC dispatch".

**Alternatives considered**:
- Direct byte-copy of QueryEngine.ts — rejected because QueryEngine.ts uses Anthropic SDK message types deeply embedded; behavior-mirror with citations is appropriate for a different I/O shape.

### R-4 — FriendliAI OpenAI-compatible SDK swap point

**Decision**: `src/kosax/llm/client.py` is KOSAX-only Procedure-B. It calls FriendliAI's OpenAI-compatible chat-completions endpoint. The streaming response is normalized to AssistantChunkFrame fields (`delta` for content, `thinking` for reasoning_content, `tool_calls` for tool dispatch).

**Rationale**:
- AGENTS.md L1-A: "Single-fixed provider FriendliAI Serverless + K-EXAONE (LGAI-EXAONE/K-EXAONE-236B-A23B)". Provider locked.
- Empirical verification 2026-05-01: `parallel_tool_calls=True` default, `chat_template_kwargs.enable_thinking` honored, `delta.reasoning_content` separated from `delta.content`. FriendliAI's OpenAI-compat is the right swap target.
- The reasoning_content forwarding (already implemented at `src/kosax/llm/client.py:788-802`) emits `thinking_delta` events that mirror Anthropic's content_block_delta thinking shape.

**Alternatives considered**:
- Use Anthropic-style API mock layer — rejected because it adds translation overhead and obscures the real provider behavior; OpenAI-compat is the canonical FriendliAI surface.

### R-5 — `ink-testing-library` Layer 1b regression test

**Decision**: New test `tui/tests/ipc/thinking-delta-render.test.tsx` uses `ink-testing-library` to mount `Message` containing a `{ type: 'thinking', thinking: <text> }` content block; asserts `frames.at(-1)` contains `∴ Thinking` glyph.

**Rationale**:
- `docs/testing.md § Layer 1b` (added 2026-05-01) documents this layer as gating for TUI-changing PRs.
- KOSAX already uses `ink-testing-library` v4 (`tui/package.json` `^4.0.0`); existing tests at `tui/tests/ink/renderer-double-buffer.test.tsx` provide the in-tree pattern.

**Alternatives considered**:
- Bun snapshot test against the rendered Markdown — rejected because the `∴` glyph is dim+italic ANSI; ink-testing-library's `frames` array preserves ANSI escapes correctly.

### R-6 — Spec 026 prompt SHA-256 boot guard

**Decision**: `prompts/system_v1.md` `<turn_order>` section (added 2026-05-01) is preserved or strengthened by this Epic; `prompts/manifest.yaml` SHA-256 stays in sync via SC-010 CI verification.

**Rationale**:
- Spec 026 boot guard (`PromptLoader._verify_sha256`) fail-closes if manifest hash != actual file hash. The 2026-05-01 prompt edit already updated the hash from `c49f384...` to `da2adc2a...`; further prompt edits this Epic would re-run that update.

## Deferred Items Validation (Constitution § VI gate)

Per spec.md "Scope Boundaries & Deferred Items" section: 7 items listed in the Deferred to Future Work table. Each:
- Has `Reason for Deferral` documented
- Has `Target Epic/Phase` named
- Has `Tracking Issue` set to `NEEDS TRACKING` (resolved by `/speckit-taskstoissues`)

Spec.md scanned for unregistered deferral patterns (`separate epic`, `future epic`, `Phase [2+]`, `v2`, `deferred to`, `later release`, `out of scope for v1`):
- All matches in spec.md are inside the table OR inside justification text immediately citing the table — no orphan deferrals.
- Phase 0 validation: **PASS**.

## Open Questions

None — all NEEDS CLARIFICATION resolved during spec authoring (verified by `/speckit-specify` validation: 0 markers).

## Constitutional Re-Check (post-research)

| Principle | Status |
|---|---|
| I. Reference-Driven | ✅ All 6 design decisions mapped to references above |
| II. Fail-Closed | ✅ Byte-copy preserves `<PermissionRequest>` byte-identical; no new classifications |
| III. Pydantic v2 | ✅ All new types (`KosaxThinkingDelta`, regression test fixtures) follow strict typing |
| IV. Government API | N/A |
| V. Policy Alignment | N/A |
| VI. Deferred Work | ✅ 7 items tracked; no orphan prose |

**Phase 0 gate: PASS — proceed to Phase 1 (Design & Contracts).**
