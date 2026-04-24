# Phase 0 Research — P1+P2 · Dead code + Anthropic→FriendliAI migration

**Feature**: [spec.md](./spec.md)
**Branch**: `1633-dead-code-friendli-migration`
**Date**: 2026-04-24

## Scope of this research

Resolve the 9 PLAN-PHASE-0 items flagged in the spec's Deferred Items table and surface any late-discovery facts that must adjust the spec's FR set before `/speckit-tasks`. All decisions below are grounded in (a) source reads of `.references/claude-code-sourcemap/restored-src/src/` + `tui/src/` + `src/kosmos/llm/`, (b) FriendliAI public docs (2026-04-24), and (c) Canonical tree `docs/requirements/kosmos-migration-tree.md § L1-A`.

## Decision 1 — Model ID final form

**Decision**: `LGAI-EXAONE/K-EXAONE-236B-A23B`

**Rationale**:
- Canonical tree `docs/requirements/kosmos-migration-tree.md § L1-A A1` pins **"K-EXAONE 단일 고정"** — the K-EXAONE brand. `K-EXAONE-236B-A23B` is the literal K-EXAONE release; `EXAONE-4.0-32B` belongs to a different brand family (EXAONE 4.0), not K-EXAONE. Brand-name alignment with the tree's normative language dominates unrelated generation-novelty arguments.
- FriendliAI provides **exclusive Day-0 support** for `K-EXAONE-236B-A23B` (https://friendli.ai/blog/k-exaone-on-serverless · https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-236B-A23B). LG AI Research + FriendliAI partnership flagship → highest operational confidence on Serverless.
- `src/kosmos/llm/config.py:37` **already uses** `LGAI-EXAONE/K-EXAONE-236B-A23B` as its default, set before this Epic. Retaining it avoids otherwise-unnecessary Python config churn and preserves the baseline that Spec 019/020/021 live-validation work already exercised.
- MoE architecture (236B total params / A23B = ~23B activated per token) yields **~23B-dense-equivalent inference compute** — comparable cost/latency to a 32B dense model, while the 236B parameter pool serves quality on longer-tail civil-affairs queries where rare-domain knowledge matters.
- FriendliAI public pricing for `K-EXAONE-236B-A23B` is $0.2 / 1 M input, $0.1 / 1 M cached input, $0.8 / 1 M output — the cached-input tier is what makes Decision 3 (keep `promptCacheBreakDetection.ts`) viable.

**Alternatives considered**:
- `LGAI-EXAONE/EXAONE-4.0-32B` — 32B dense, hybrid attention + QK-Reorder-Norm, 131 K context, open-weight on Hugging Face, agentic tool use. **Rejected**: (a) brand-name mismatch against canonical tree "K-EXAONE" pinning; (b) Epic body previously referenced this ID in error (see "Epic body correction" below — corrected during this plan cycle after Epic-author reconfirmation); (c) no compelling citizen-UX delta that overcomes (a) and (b).
- `LGAI-EXAONE/EXAONE-4.0.1-32B` — minor release on Hugging Face. **Rejected** for the same brand-alignment reason.
- `KOSMOS_FRIENDLI_MODEL` env-var-driven multi-model switching. **Rejected** — violates canonical tree's "단일 고정" directive (L1-A A1).

**Epic body correction (executed during Phase 0)**:
- `docs/requirements/epic-p1-p2-llm.md` and Epic #1633 body originally stated `Model ID = LGAI-EXAONE/EXAONE-4.0-32B`. The Epic author reconfirmed intent against (a) canonical tree brand pinning, (b) existing Python config default, (c) FriendliAI Day-0 support status and directed a correction to `LGAI-EXAONE/K-EXAONE-236B-A23B`. Both the Epic body and the doc are updated in the same commit as this research file.

**Spec/code adjustments this forces**:
- **`src/kosmos/llm/config.py:37` — NO change** (default already `"LGAI-EXAONE/K-EXAONE-236B-A23B"`).
- spec.md FR-011 path correction (see Decision 12 / Finding B) — unrelated to model ID, still required.

## Decision 2 — `filesApi.ts` keep-or-delete

**Decision**: **Delete** `tui/src/services/api/filesApi.ts` and all its import sites.

**Rationale**:
- File header comment: "This module provides functionality to download and upload files to **Anthropic Public Files API**." Uses `ANTHROPIC_BASE_URL` env var, `files-api-2025-04-14` beta header, and `api.anthropic.com` as fallback. 100 % Anthropic-specific.
- FriendliAI Serverless public OpenAPI overview (https://friendli.ai/docs/openapi/serverless) does not document any `/v1/files` endpoint. The overview lists chat-completions, completions, tokenization, and audio-transcriptions; no file-management endpoints.
- Citizen flows defined in `docs/vision.md` do not require session-startup file attachments — those are a Claude Code developer-UX feature.

**Alternatives considered**:
- **Keep + rewire to FriendliAI Files**: rejected because no public Files API surface is documented on Serverless.
- **Keep as a no-op stub**: rejected — dead-code-retention contradicts Epic P1 intent.
- **Migrate to Python backend** (upload via Python httpx to FriendliAI Files if available): rejected as out of scope for this Epic. If a future feature (e.g., OCR upload) needs files, it will be introduced via a new Epic.

**Callsite impact** (from `grep -rln 'filesApi' tui/src`):
- `main.tsx`, `context.ts`, `commands.ts`, `QueryEngine.ts`, `setup.ts`, tool files (`NotebookEditTool.ts`, `FileWriteTool.ts`, `FileEditTool.ts`, `PowerShellTool/pathValidation.ts`, `GlobTool.ts`) — total 10 files reference `filesApi`. These are **CC developer-tool paths** that the P3 tool-system rewrite will either delete or replace with KOSMOS primitives. For this Epic, stub out the import sites with no-op equivalents (an empty `{}` returns) so the tool files keep compiling until P3.

## Decision 3 — `promptCacheBreakDetection.ts` keep-or-delete

**Decision**: **Keep and rewire** to read FriendliAI's `prompt_tokens_details.cached_tokens`.

**Rationale**:
- FriendliAI public pricing for `K-EXAONE-236B-A23B` and `EXAONE-4.0-32B` explicitly lists **cached input tokens** as a separate billing tier (cached input @ $0.1 / 1 M vs regular input @ $0.2 / 1 M for K-EXAONE). This is a hard signal that FriendliAI exposes cache-hit metadata.
- FriendliAI dedicated chat-completions docs (https://friendli.ai/docs/openapi/dedicated/inference/chat-completions) document `prompt_tokens_details.cached_tokens` in the response `usage` field — OpenAI-compatible schema.
- `promptCacheBreakDetection.ts` in CC detects cache-hit discontinuities (large cached-token drop between turns) to avoid prefix-breakage — a useful signal that is provider-agnostic once the field name is correct.

**Alternatives considered**:
- **Delete**: rejected because cache metrics are useful for the KOSMOS OTEL observability layer (Spec 021) and for FP&A cost tracking.
- **Move to Python backend only**: plan-level detail — Python `LLMClient` already parses `usage`; TUI's detection module adds a UX signal (warn when cache breaks, reducing citizen-visible latency spikes). Kept in TS as UX utility.

## Decision 4 — Spec 032 frame envelope LLM packing strategy

**Decision**: **Reuse existing `UserInputFrame` + `AssistantChunkFrame` + `ToolCallFrame` + `ToolResultFrame`** from `tui/src/ipc/frames.generated.ts`. **No new frame kinds.** No Spec 032 amendment required.

**Rationale**:
- `frames.generated.ts:51` already defines `Role = 'tui' | 'backend' | 'tool' | 'llm' | 'notification'`. The `llm` role is specifically reserved for backend-originated LLM frames.
- `AssistantChunkFrame` (kind `'assistant_chunk'`) already carries `{ message_id, delta, done }` — a streaming-token NDJSON shape that maps 1-to-1 to FriendliAI's OpenAI-compatible SSE chunk (`choices[].delta.content`).
- `UserInputFrame` carries `{ text }` — maps to the single user turn forwarded to Python backend.
- `ToolCallFrame` / `ToolResultFrame` carry the function-call leg — FriendliAI OpenAI-compat tool-call shape.
- `ErrorFrame`, `BackpressureSignalFrame`, `ResumeRequest/Response/Rejected` already handle the out-of-band signals.

**Alternatives considered**:
- **Option A (add `role=llm, kind=stream_delta`)**: rejected — would require Spec 032 schema regeneration. `AssistantChunkFrame` already does this role.
- **Option B (new `LLMRequestFrame` + `LLMResponseFrame`)**: rejected — adds frame kinds Spec 032 does not define, violates the "rewrite boundary" (Constitution Principle I) by forcing Spec 032 amendment.
- **Option C (pack full LLM response into `ToolResultFrame`)**: rejected — ToolResult is for adapter output, not LLM turns. Semantic abuse.

**Implication for plan**: The TS-side `LLMClient` (Decision 5) constructs `UserInputFrame` outbound, consumes a stream of `AssistantChunkFrame` + `ToolCallFrame` inbound, and emits the Spec 032 trailer on `done=true`. No frame-schema change.

## Decision 5 — TS `LLMClient` design

**Decision**: New file `tui/src/ipc/llmClient.ts`. Exports a class `LLMClient` whose surface emulates the `@anthropic-ai/sdk` `Messages.create` streaming generator that `QueryEngine.ts:2` + `query.ts:5` consume as **type-only** imports (the SDK is never constructed in TS — the port was type-surface only).

**Shape to emulate** (extracted from CC 2.1.88 `QueryEngine.ts:2`):
```ts
async function* stream(params: BetaMessageStreamParams):
  AsyncGenerator<BetaRawMessageStreamEvent, void, void>
```
and the resolved usage/stop-reason trailers.

**Responsibilities of `tui/src/ipc/llmClient.ts`**:
1. Accept `{ system, messages, tools, model, max_tokens }` from QueryEngine.
2. Serialize to a Spec 032 `UserInputFrame` (system prompt in metadata, messages in payload) and push via `bridge.ts`.
3. Consume Python-backend-originated `AssistantChunkFrame` + `ToolCallFrame` stream and yield `BetaRawMessageStreamEvent`-shaped events (type translation layer, not a protocol change).
4. Finalize on `done=true` trailer; surface `ErrorFrame` as thrown error.
5. Emit OTEL `gen_ai.client.invoke` span with `gen_ai.system=friendli_exaone`, `gen_ai.request.model=LGAI-EXAONE/K-EXAONE-236B-A23B`, `kosmos.prompt.hash=<sha256>`.

**KOSMOS type replacement**:
- Define `tui/src/ipc/llmTypes.ts` with `KosmosMessageStreamParams`, `KosmosRawMessageStreamEvent`, `KosmosContentBlockParam`, `KosmosTextBlockParam` as structural supersets of the Anthropic SDK types currently imported. This lets us delete `@anthropic-ai/sdk` imports without rewriting QueryEngine's control flow.

**Alternatives considered**:
- **Direct FriendliAI HTTPS call from TS**: rejected — violates `docs/vision.md § L1-A A1` + rewrite boundary ("services/api/* only goes over stdio to Python backend").
- **Full protocol rewrite of QueryEngine**: rejected — out of scope. Epic body explicitly says "keep agentic loop, rewire client instantiation."
- **Reuse Python backend's `LLMClient` via subprocess invocation per request**: rejected — Spec 032 stdio persistence is the correct transport.

## Decision 6 — Error code mapping matrix

Anthropic-specific error codes (from `tui/src/services/api/errors.ts` CC reference) → KOSMOS envelope (LLM · Tool · Network) via FriendliAI HTTP + stdio IPC transport signals:

| Anthropic code | HTTP | FriendliAI equivalent | KOSMOS envelope | Retry? |
|---|---|---|---|---|
| `invalid_request_error` | 400 | 400 / same JSON body | `ErrorFrame(class=llm, code=invalid_request)` | No |
| `authentication_error` | 401 | 401 (missing `FRIENDLI_API_KEY`) | `ErrorFrame(class=llm, code=auth)` | No; fail-closed at boot |
| `permission_error` | 403 | 403 | `ErrorFrame(class=llm, code=permission)` | No |
| `not_found_error` | 404 | 404 (model ID unknown) | `ErrorFrame(class=llm, code=not_found)` | No |
| `request_too_large` | 413 | 413 (context window exceeded) | `ErrorFrame(class=llm, code=too_large)` | No; surface to user |
| `rate_limit_error` | 429 | 429 + `Retry-After` header | `BackpressureSignal(kind=llm_rate_limit, retry_after_ms)` | Yes — Spec 019 backoff |
| `api_error` / `overloaded_error` | 500 / 529 | 5xx | `ErrorFrame(class=network, code=upstream)` | Yes — exponential backoff, max 3 |
| (stdio IPC transport error) | — | — | `ErrorFrame(class=network, code=ipc_transport)` | Yes — Spec 032 resume path |

**Rationale**: FriendliAI follows OpenAI HTTP-status conventions (confirmed via their OpenAPI schema referencing `/v1/chat/completions`). Spec 019 already defined the 429 backoff strategy; this matrix extends it to non-retryable codes without inventing new retry semantics.

**Spec 032 touchpoint**: `BackpressureSignal(kind=llm_rate_limit)` is already enumerated in Spec 032 Story 2; no schema change.

## Decision 7 — `withRetry.ts` retry policy

**Decision**: Retry targets = `{ 429, 500, 502, 503, 504 }`. Max attempts = 3. Backoff = exponential (1s, 2s, 4s) with `Retry-After` header override when present. Consistent with `src/kosmos/llm/client.py` Python-side retry.

**Rationale**:
- Python `LLMClient` (already deployed) uses per-session semaphore + exponential backoff + Retry-After override (Spec 019/020 heritage).
- TS `withRetry.ts` currently handles CC-specific codes (401, 529); strip those.
- 401 is now non-retryable (bad `FRIENDLI_API_KEY` = fail-closed).
- 529 (Anthropic "overloaded") maps to generic 5xx.

**Alternatives considered**:
- **Delete TS `withRetry.ts` and rely solely on Python-side retry**: rejected — the TS-side retry protects against transient `bridge.ts` / stdio flaps (IPC transport), which Python doesn't see.

## Decision 8 — OTEL span placement

**Decision**: Emit `gen_ai.client.invoke` span at `tui/src/ipc/llmClient.ts` outbound entry (per-LLM-call), with attributes:

| Attribute | Source | Notes |
|---|---|---|
| `gen_ai.system` | constant `"friendli_exaone"` | GenAI semconv v1.40 |
| `gen_ai.request.model` | `LGAI-EXAONE/K-EXAONE-236B-A23B` | Decision 1 |
| `gen_ai.operation.name` | `"chat"` | constant |
| `gen_ai.usage.input_tokens` | from `AssistantChunkFrame` final trailer | populated on done |
| `gen_ai.usage.output_tokens` | from final trailer | populated on done |
| `kosmos.prompt.hash` | SHA-256 of `prompts/system_v1.md` | **required by SC-008** (Spec 026) |
| `kosmos.correlation_id` | `envelope.correlation_id` | Spec 032 correlation |
| `kosmos.transaction_id` | `envelope.transaction_id` | Spec 032, may be null for streaming |

Python backend (`src/kosmos/llm/client.py`) already emits these same attributes on its side — we get dual-emission (TS + Python) naturally joined by `correlation_id` at the OTEL collector.

**Rationale**:
- Spec 021 already defined the semconv; this spec just wires the TS emission point.
- Spec 026 already defines `kosmos.prompt.hash`; `PromptLoader` is the Python authority and forwards the hash via IPC metadata (see Decision 9).

**Alternatives considered**:
- Emit at `QueryEngine.ts` agentic-loop entry: rejected — would double-count tool calls and shift semantics from "one LLM invoke" to "one conversation turn."

## Decision 9 — Slash command registry cleanup

**Decision**: Delete `/login` and `/logout` slash commands entirely. Update:
- `tui/src/commands/login/login.tsx` — delete.
- `tui/src/commands/logout/logout.tsx` — delete.
- `tui/src/commands.ts` — remove from registry list.
- `tui/src/commands/help.tsx` — remove help entries.
- `tui/src/screens/REPL.tsx` — remove autocomplete entries if hard-coded.
- Onboarding Step-5 (`terminal-setup` per Spec 035 UI-A) — no login step; directly instructs citizen to `export FRIENDLI_API_KEY=...`.

**Rationale**:
- No KOSMOS user-facing account concept exists — FRIENDLI_API_KEY is env-var only, held by the user.
- Spec 035 onboarding flow ends with `terminal-setup` (preflight → theme → pipa-consent → ministry-scope → terminal-setup); there's no Anthropic-style OAuth handshake.
- Retaining no-op `/login` / `/logout` confuses citizens.

**Alternatives considered**:
- **Keep `/login` as a help-only stub**: rejected — "login" has no meaning in the KOSMOS model.
- **Rename to `/account`**: rejected — no account surface exists.

## Late-discovery findings

These are facts discovered during Phase 0 that require spec.md or plan adjustments beyond the original PLAN-PHASE-0 list:

### Finding A — `services/services/` path prefix is incorrect

Epic body `docs/requirements/epic-p1-p2-llm.md` uses paths like `tui/src/services/services/analytics/`, `tui/src/services/services/api/claude.ts`, etc. **The real repo layout uses single `services/`** — `tui/src/services/analytics/`, `tui/src/services/api/claude.ts`.

**All FR file paths in spec.md that begin with `services/services/` must be normalized to `services/`** at `/speckit-tasks` time. This is a mechanical substitution, not a scope change. Listed here so the ambiguity does not surface as a disagreement during task generation.

### Finding B — `getDefaultMainLoopModel()` real location

Epic body / spec FR-011 says `tui/src/utils/model/antModels.ts::getDefaultMainLoopModel()`. Real definition is at `tui/src/utils/model/model.ts:206` (antModels.ts defines the Ant-only override override type, not the default getter).

**Correction for tasks**: target `model.ts:206` for the `LGAI-EXAONE/K-EXAONE-236B-A23B` return-value rewire; delete `antModels.ts` entirely (Ant-only GrowthBook override is dead code under P1).

### Finding C — Additional dead-code files beyond Epic body

Files not named in Epic body but belonging to the same dead-code groups:
- `tui/src/services/claudeAiLimitsHook.ts` — hook sibling of `claudeAiLimits.ts`; same dead-code class, delete together (FR-014 scope extension).
- `tui/src/constants/betas.ts` — constant-side counterpart of `utils/betas.ts`; both carry Anthropic beta-header codes, delete both (FR-013 scope extension).
- `tui/src/services/analytics/growthbook.ts` referenced from `tui/src/utils/model/antModels.ts:1` — follow-on deletion after antModels removal.

### Finding D — 137 `@anthropic-ai/sdk` import sites

Initial `grep -c '@anthropic-ai/sdk' tui/src` returned **137** imports across ~30 files. A significant fraction are **type-only imports** (`import type {...}` from `@anthropic-ai/sdk/resources/*`). The TS LLMClient in Decision 5 replaces these with KOSMOS-scoped types in `tui/src/ipc/llmTypes.ts`. The mechanical substitution is ~137 edits × 1 line each plus 1 new KOSMOS types file.

## Deferred Items validation (Constitution Principle VI gate)

Spec `Scope Boundaries & Deferred Items` table has 8 rows. Review:

| Row | Tracking Issue | Status |
|---|---|---|
| Tool system (P3) | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — Epic #1634 placeholder |
| UI component port (P4) | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — Epic #1635 placeholder |
| Plugin DX (P5) | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — Epic #1636 placeholder |
| docs/api (P6) | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — Epic #1637 placeholder |
| `filesApi.ts` compatibility | `PLAN-PHASE-0` | ✅ **Resolved here (Decision 2): delete** |
| `promptCacheBreakDetection.ts` support | `PLAN-PHASE-0` | ✅ **Resolved here (Decision 3): keep + rewire** |
| Citizen quota policy | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — separate Initiative placeholder |
| Anthropic MCP reintroduction | `NEEDS TRACKING` | Resolved at `/speckit-taskstoissues` — follow-on MCP Epic placeholder |

**Ghost-work scan**: `grep` over spec.md for "future", "separate epic", "v2", "후속", "phase 2" returned zero hits outside the Deferred Items table (verified 2026-04-24 after FR-014/FR-015 tightening commit `2af3f83`).

**Gate result**: ✅ **PASS**.

## Summary of artifact-level actions

This research produces the following downstream outputs (tracked in plan.md Phase 1):

1. **Code edits (TS)**: ~137 `@anthropic-ai/sdk` imports removed; new `tui/src/ipc/llmClient.ts` + `llmTypes.ts`; `tui/src/utils/model/model.ts:206` return-value change; ~50 file deletions; `/login`·`/logout` slash commands removed.
2. **Code edits (Python)**: none — `src/kosmos/llm/config.py:37` default is already `LGAI-EXAONE/K-EXAONE-236B-A23B` (matches Decision 1).
3. **Tests**: regression tests for each FR (grep-based invariants); US1 end-to-end test harness (mocked Python backend responding with fake `AssistantChunkFrame` stream).
4. **Docs (in-Epic)**: `data-model.md` (frame envelope LLM usage), `contracts/llm-client.md` (TS LLMClient interface + IPC frame contract), `quickstart.md` (fresh-clone → first-K-EXAONE-token flow).
5. **Docs (post-merge)**: none — Tree propagation PR #1652 already covers README/CLAUDE/AGENTS.

## References

- `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` — CC 2.1.88 baseline for `claude.ts` rewire target
- `.references/claude-code-sourcemap/restored-src/src/QueryEngine.ts:2` — Anthropic SDK type import site (reference for emulation)
- `tui/src/ipc/envelope.ts` + `frames.generated.ts` — Spec 032 envelope definitions
- `src/kosmos/llm/client.py` + `config.py` — Python backend FriendliAI implementation (target for Spec 032 IPC bridging)
- `docs/vision.md § 28-44` — thesis (CC is first reference)
- `docs/requirements/kosmos-migration-tree.md § L1-A` — canonical LLM-layer decisions (A1-A7)
- `docs/requirements/epic-p1-p2-llm.md` — Epic body scope
- `.specify/memory/constitution.md` — Principles I · II · III · VI
- Spec 019 (LLM 429 resilience) — retry semantics
- Spec 021 (OTEL observability) — GenAI semconv
- Spec 026 (Prompt Registry) — PromptLoader + `kosmos.prompt.hash`
- Spec 032 (IPC stdio hardening) — envelope + role=llm + `AssistantChunkFrame`
- Spec 035 (Onboarding) — 5-step flow terminating at `terminal-setup`
- FriendliAI announcement 2025-10: https://friendli.ai/blog/lg-ai-research-partnership-exaone-4.0
- FriendliAI model page: https://friendli.ai/suite/~/serverless-endpoints/LGAI-EXAONE/K-EXAONE-236B-A23B/overview
- FriendliAI K-EXAONE page (cached-input pricing reference): https://friendli.ai/blog/k-exaone-on-serverless
- FriendliAI dedicated chat-completions (usage field reference): https://friendli.ai/docs/openapi/dedicated/inference/chat-completions
