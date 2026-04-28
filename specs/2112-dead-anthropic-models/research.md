# Phase 0 Research: P1 Dead Anthropic Model Matrix Removal

**Branch**: `2112-dead-anthropic-models` | **Date**: 2026-04-28
**Author**: Lead (Opus, claude-opus-4-7)
**Reference materials consulted**:
- `.specify/memory/constitution.md` (Principles I, VI especially)
- `docs/vision.md § Reference materials` (Reference matrix; this epic is a deletion-driven sweep, not a porting exercise)
- `docs/requirements/kosmos-migration-tree.md § L1-A.A1, A3, A4 + Execution Phase`
- `AGENTS.md § Hard rules + Stack`
- 5 deep-research sources captured below

## Reference matrix (Constitution Principle I)

| Layer | Primary reference | Secondary reference | Used in this epic? |
|---|---|---|---|
| Query Engine | Claude Agent SDK | Claude Code reconstructed | Indirectly — `LLMClient` is the binding query engine surface; this epic does not touch `client.py` |
| Tool System | Pydantic AI | Claude Agent SDK | No — no tool changes |
| Permission Pipeline | OpenAI Agents SDK | Claude Code reconstructed | No |
| Agent Swarms | AutoGen | Anthropic Cookbook | No |
| Context Assembly | Claude Code reconstructed | Anthropic docs | No |
| Error Recovery | OpenAI Agents SDK | Claude Agent SDK | No — preserved by FR-014 |
| TUI | Ink + Gemini CLI | Claude Code reconstructed | **Yes** — primary surface |

**Per memory `feedback_cc_source_migration_pattern`**: this epic is *deletion-driven*. We are removing CC-derived code that has no KOSMOS analogue under the single-fixed FriendliAI provider invariant. We do not introduce new CC-ported code. CC sourcemap line citations (R4 below) document which CC lines are dead under KOSMOS's invariants.

---

## R1 · Hugging Face — `LGAI-EXAONE/K-EXAONE-236B-A23B`

**Source**: https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B (fetched 2026-04-28)

| Fact | Value |
|---|---|
| Context window | **262 144 tokens (256K)**. Hybrid attention pattern: 12 × (3 sliding-window + 1 global). Sliding window size 128 tokens. |
| Recommended `max_new_tokens` | reasoning mode = **16 384** · non-reasoning = **1 024** |
| Recommended sampling | **`temperature=1.0, top_p=0.95, presence_penalty=0.0`** — model card: *"We strongly recommend …"* |
| `enable_thinking` default | **True** (reasoning ON). Toggle to `False` for latency-sensitive use. |
| Tool/function-calling | OpenAI-style + HuggingFace JSON schema. vLLM `--tool-call-parser hermes`. |
| Architecture | MoE. Total 236B (234B w/o emb), Active 23B, 128 experts, 8 activated, 1 shared. |
| Tokenizer | `LGAI-EXAONE/K-EXAONE-236B-A23B`, vocab **153 600** (SuperBPE 150k base, +30 % token efficiency). |
| FriendliAI status | Free Serverless API until **Feb 12 2026**. |

**Decision**: KOSMOS already wires every recommended sampling default at `src/kosmos/llm/client.py:161-164` (non-streaming) and `:288-291` (streaming) — `temperature=1.0, top_p=0.95, presence_penalty=0.0, max_tokens=1024`. ✅ matches HF recommendation for non-reasoning mode (`max_tokens=1024`). FR-013 preserves these. No code change required at the Python layer.

**Rationale**: KOSMOS Spec 022 + 014 + 019 (`spec/wave-1`) and Epic #2077 (commit 692d1c3) all converged on these constants. Re-tuning is out of scope for P1.

**Alternatives considered**:
- Reduce `session_budget` from 1 000 000 → 262 144 (HF context limit). **Rejected**: `config.py:42-48` docstring confirms `session_budget` is per-session aggregate across multiple turns, not per-call max — matches the HF context limit per turn (1024 default). No drift.

---

## R2 · FriendliAI Serverless Endpoints catalog

**Sources** (fetched 2026-04-28):
- https://docs.friendli.ai/guides/serverless_endpoints/models — **404** (path migrated)
- https://friendli.ai/docs/sdk/integrations/openai — **200** (partial; OpenAI integration page)
- https://friendli.ai/model/LGAI-EXAONE/K-EXAONE-236B-A23B — referenced from HF card §8

| Fact | Value |
|---|---|
| Chat-completions base URL | `https://api.friendli.ai/serverless/v1` |
| Endpoint path | `POST /chat/completions` |
| OpenAI-compat features | streaming (`stream=True`), function calling (`tools`, `tool_choice="auto"`), `logprobs`+`top_logprobs`, `stream_options.include_usage` |
| EXAONE-specific knob | `chat_template_kwargs.enable_thinking` (forwarded to vLLM tokenizer) |
| Model ID string | `LGAI-EXAONE/K-EXAONE-236B-A23B` (matches HF repo path) |

**Decision**: KOSMOS's existing `src/kosmos/llm/{config.py,client.py}` already mirrors all of these — `config.py:32` base URL, `:37` model ID, `client.py:237,444` `POST /chat/completions`, `client.py:858` `chat_template_kwargs.enable_thinking`. ✅ no change required.

**Rationale**: This research artefact serves as documentation that the FriendliAI surface KOSMOS targets is the OpenAI-compat endpoint, NOT a proprietary endpoint. The `[ANT-ONLY]` rate-limit mock (`mockRateLimits.ts`) targets Anthropic-shaped headers (`anthropic-ratelimit-unified-*`) which FriendliAI does not emit — confirming the file's deletion is correct (FR-002).

---

## R3 · FriendliAI rate-limit policy + KOSMOS Spec 019 hardening

**Sources**:
- https://docs.friendli.ai/guides/serverless_endpoints/rate-limits — **404**
- https://friendli.ai/docs/guides/serverless_endpoints/rate-limits — **404**
- https://friendli.ai/pricing — **200** (no public Tier 1 RPM/TPM disclosure)
- KOSMOS memory `project_friendli_tier_wait` (2026-04-15) — Tier 1 = **60 RPM** confirmed
- `specs/019-phase1-hardening/` artifact

**KOSMOS Spec 019 hardening** (citation: `src/kosmos/llm/client.py`):

| Concern | Implementation | Lines |
|---|---|---|
| Retry-After-first backoff | `_compute_rate_limit_delay` honours `Retry-After` header before exponential | `client.py:893-915` |
| Per-session concurrency gate | `asyncio.Semaphore(1)` acquired around each provider call | `client.py:134, 236, 442` |
| Pre-stream 429 handling | non-streaming retry loop | `client.py:226-280` |
| Streaming 429 + mid-stream SSE 429 | streaming retry loop with `_is_rate_limit_envelope` | `client.py:411-613` + `:698-728` |
| Mid-stream SSE 429 detector | `_is_rate_limit_envelope(line)` keys: `error.status==429`, `error.code in {"429","rate_limit","rate_limited"}`, `error.type in {…}` | `client.py:699-728` |
| Headers honoured | `Retry-After` only (`_has_retry_after`) | `client.py:885-891` |

**Decision**: KOSMOS already has FriendliAI-shaped rate-limit handling at the Python layer. The TUI-side `mockRateLimits.ts` Anthropic header schema (`anthropic-ratelimit-unified-status`, `anthropic-ratelimit-unified-reset`, etc., 12+ keys) maps to **nothing on FriendliAI** — there is no equivalent unified header set. Both the mock and its caller (`rateLimitMocking.ts`) are `[ANT-ONLY]` — eligible for full removal in P1; no FriendliAI-shaped TUI replacement is required.

**Rationale**: Production rate-limit envelopes are handled by `LLMClient._is_rate_limit_envelope` at the Python client layer (FR-014 preservation). Citizen-facing UI does not need to mock provider-shaped 429 envelopes — it only needs to render error text correctly when 429 propagates from the Python backend.

**Alternatives considered**:
- Migrate `mockRateLimits.ts` to FriendliAI-shaped envelope. **Rejected**: no current test depends on a TS-side mock; deferring to P5+ "Testing infrastructure" (spec § Deferred table row 4) is the right call.

---

## R4 · CC source-map model-selection lines

KOSMOS imports its agentic loop architecture from CC 2.1.88. Reference mirror at `src/kosmos/llm/_cc_reference/` (read-only, research-use, Apache-2.0 upstream).

| File:line | Concern | KOSMOS migration mapping |
|---|---|---|
| `_cc_reference/api.ts:33-35` | imports `roughTokenCountEstimation` from `services/tokenEstimation.ts` | KOSMOS keeps the equivalent module live (no change) |
| `_cc_reference/api.ts:50-53` | imports `getAPIProvider`, `isFirstPartyAnthropicBaseUrl` from `model/providers.ts` | Provider selection is dead in KOSMOS (single-fixed FriendliAI per `kosmos-migration-tree.md § L1-A.A1`) — `providers.ts` cleanup deferred to P2 |
| `tui/src/utils/model/model.ts:178-188` | `getDefaultMainLoopModelSetting()` and `getDefaultMainLoopModel()` already short-circuit to `'LGAI-EXAONE/K-EXAONE-236B-A23B'` | ✅ Anchor — single source of truth for KOSMOS model ID. P1 must ensure this is the only branch leading to a model string. |
| `tui/src/utils/model/model.ts:38-49` | `getSmallFastModel()` and `isNonCustomOpusModel()` resolve via `getModelStrings()` | Rewrite to constant K-EXAONE branch; prune unreachable Opus/Sonnet/Haiku branches. |
| `tui/src/utils/model/model.ts:197-279` | `firstPartyNameToCanonical(name)` — string-match dispatcher across `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku` (15+ branches) | All branches reachable only when a non-K-EXAONE model name flows in — but KOSMOS forces `K-EXAONE-236B-A23B` at every entrypoint. **15+ branches dead.** P1: collapse to `name.includes('K-EXAONE') ? 'k-exaone' : name as ModelShortName`. |
| `tui/src/utils/model/modelOptions.ts:20-32` | imports `getDefaultSonnetModel`, `getDefaultOpusModel`, `getDefaultHaikuModel` from `./model.js` | Need to remove these imports + the helper exports once external callers are pruned (FR-006 caller-reach rule). |
| `tui/src/services/mockRateLimits.ts:1` | file header `// Mock rate limits for testing [ANT-ONLY]` | Tree-shaken out for non-ant builds (`bun:bundle feature()`). KOSMOS is non-ant by definition. Delete file + paired `rateLimitMocking.ts`. |

**Decision**: This is a *deletion-driven* migration, not a CC port. Per memory `feedback_cc_source_migration_pattern`, when there is no analogue under KOSMOS's invariants, the CC code is *deleted*, not adapted. The CC sourcemap stays at `src/kosmos/llm/_cc_reference/` as a research-use reference; this epic does not modify it.

**Rationale**: Constitution Principle I requires every design decision to trace to a concrete reference source — and this *deletion* decision traces to `kosmos-migration-tree.md § L1-A.A1` (single-fixed FriendliAI) which makes Anthropic name-pattern dispatch unreachable code by definition.

---

## R5 · Current KOSMOS LLM client truth values (single source-of-truth)

**Sources**: read directly from repo on 2026-04-28.

| File:line | Constant | Value | FR preserving it |
|---|---|---|---|
| `src/kosmos/llm/config.py:32` | `base_url` default | `https://api.friendli.ai/serverless/v1` | FR-012 |
| `src/kosmos/llm/config.py:37` | `model` default | `LGAI-EXAONE/K-EXAONE-236B-A23B` | FR-012 |
| `src/kosmos/llm/config.py:48` | `session_budget` | `1_000_000` | (out of scope) |
| `src/kosmos/llm/client.py:161-164` | sampling defaults (non-streaming) | `temperature=1.0, top_p=0.95, presence_penalty=0.0, max_tokens=1024` | FR-013 |
| `src/kosmos/llm/client.py:288-291` | sampling defaults (streaming) | `temperature=1.0, top_p=0.95, presence_penalty=0.0, max_tokens=1024` | FR-013 |
| `src/kosmos/llm/client.py:838-844` | `enable_thinking` env | `KOSMOS_K_EXAONE_THINKING ∈ {true,1,yes}` (default `false`) | FR-015 |
| `src/kosmos/llm/client.py:854-858` | payload field | `chat_template_kwargs.enable_thinking` | FR-015 |
| `tui/src/utils/model/model.ts:179` | `getDefaultMainLoopModelSetting()` | `'LGAI-EXAONE/K-EXAONE-236B-A23B'` | FR-004, FR-012 |
| `tui/src/utils/model/model.ts:187` | `getDefaultMainLoopModel()` | `'LGAI-EXAONE/K-EXAONE-236B-A23B' as ModelName` | FR-004, FR-012 |
| `tui/src/components/LogoV2/LogoV2.tsx:45` | imports `renderModelSetting` | derives from the two functions above (no hardcoded label) | FR-012 |

**Decision**: K-EXAONE label is already centralised in 3 files. P1 deletion **must not introduce a new source of truth** — keep `model.ts:179,187` and `config.py:37` as the only literals (FR-012).

**Rationale**: Single-source-of-truth invariant minimises future rename risk and matches the canonical-references pattern in `kosmos-migration-tree.md`.

---

## Phase 0 deferred-items validation (Constitution Principle VI)

Read from `spec.md § Scope Boundaries & Deferred Items`:

### Out of Scope (Permanent) — 3 items
1. ✅ `claude.ai` subscription tier restoration — permanent invariant traced to `kosmos-migration-tree.md § L1-A.A1`.
2. ✅ Anthropic SDK shape restoration — permanent invariant traced to `kosmos-migration-tree.md § L1-A.A1`.
3. ✅ Reintroducing `[ANT-ONLY]` rate-limit mock — permanent (any new mock must be FriendliAI-shaped, fresh spec).

### Deferred to Future Work — 5 items, all `Tracking Issue: NEEDS TRACKING`

| # | Item | Target Phase | Tracking |
|---|---|---|---|
| 1 | OAuth + subscription-tier helpers removal | P2 | NEEDS TRACKING |
| 2 | `services/api/claude.ts` Anthropic SDK invocation removal | P2 | NEEDS TRACKING |
| 3 | Product-name cosmetic strings migration | P3 | NEEDS TRACKING |
| 4 | FriendliAI-shaped rate-limit mock fixture (TS) | P5+ | NEEDS TRACKING |
| 5 | Wider `[ANT-ONLY]` marker sweep outside 3 target files | P1.5 / P2 | NEEDS TRACKING |

All 5 will be resolved by `/speckit-taskstoissues` per Constitution Principle VI.

### Free-text scan for unregistered deferral patterns

Scanned `spec.md` for: "separate epic", "future epic", "Phase [2+]", "v2", "deferred to", "later release", "out of scope for v1".

| Match | Location | Registered? |
|---|---|---|
| "deferred to P2" | spec.md FR-006 | ✅ Yes — registered as Deferred row 1 + 2 |
| "Phase 2 / P2 / P3" | spec.md § Deferred table headers | ✅ Yes — used as the table's `Target Epic/Phase` column |
| "future spec" | spec.md § Out of Scope (Permanent) row 3 | ✅ Yes — traced to permanent boundary |
| "deferred to a separate sweep" | spec.md FR-008 | ✅ Yes — registered as Deferred row 5 |

**Result**: All free-text deferral patterns have corresponding entries in the structured table. **No constitution Principle VI violations.**

---

## Summary — research outputs feeding Phase 1

1. **No code-side decision left as NEEDS CLARIFICATION** — all spec FRs are traced to evidence in R1–R5.
2. **Caller-reach rule for FR-006**: Phase 0 grep identified 9 caller files of `firstPartyNameToCanonical`/`getDefault{Sonnet,Opus,Haiku}Model`:
   - inside SC-1 perimeter (`tui/src/utils/model/`): `model.ts`, `agent.ts`, `modelOptions.ts`, `modelCapabilities.ts` → can remove helpers directly
   - outside SC-1 perimeter: `memdir/findRelevantMemories.ts`, `utils/attachments.ts`, `commands/insights.ts`, `services/tokenEstimation.ts`, `services/api/claude.ts`, `components/messages/AssistantTextMessage.tsx` → keep helpers as **thin K-EXAONE-returning aliases** with `[Deferred to P2]` annotations
3. **Deletion budget**: target ≥ 40 % LOC reduction in the 3 source-of-truth files (SC-006). Pre-change total = 539 + 598 + 882 = 2 019 LOC. Target ≤ 1 211 LOC remaining. Achievable because `mockRateLimits.ts` (882) + `rateLimitMocking.ts` (~222) delete entirely; `model.ts` collapses ~150 LOC of `firstPartyNameToCanonical`; `modelOptions.ts` loses claude-3 / sonnet / opus / haiku option entries.
4. **Validation matrix** (data-model.md §3) maps each FR → audit command → expected output.
5. **Quickstart** (quickstart.md) exposes the audit recipe so Codex / human reviewers can verify SC-001..SC-006 in ≤ 5 minutes.
