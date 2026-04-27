# Data Model: P1 Dead Anthropic Model Matrix Removal

**Branch**: `2112-dead-anthropic-models` | **Date**: 2026-04-28
**Note**: This is a *deletion-driven* epic. There are no new schema entities, no migrations, no on-disk state changes. The "data model" here documents (a) the canonical truth-value entities that must be **preserved** by FR-012/013/014/015, (b) the entities that are **deleted**, and (c) the transitions caller-files undergo.

## 1. Preserved entities (truth values — FR-012/013/014/015)

### 1.1 `LLMClientConfig` — Python source-of-truth

**Location**: `src/kosmos/llm/config.py:10-91`
**Type**: `pydantic_settings.BaseSettings`
**Status**: PRESERVED (read-only to this epic)

| Field | Default | Env var | Validator |
|---|---|---|---|
| `token: SecretStr` | `...` (required) | `KOSMOS_FRIENDLI_TOKEN` | `token_must_not_be_empty` |
| `base_url: AnyHttpUrl` | `https://api.friendli.ai/serverless/v1` | `KOSMOS_FRIENDLI_BASE_URL` | (built-in URL) |
| `model: str` | `LGAI-EXAONE/K-EXAONE-236B-A23B` | `KOSMOS_FRIENDLI_MODEL` | (string) |
| `session_budget: int` | `1_000_000` | `KOSMOS_LLM_SESSION_BUDGET` | `session_budget_must_be_positive` |
| `timeout: float` | `60.0` | (no env) | `timeout_must_be_positive` |
| `max_retries: int` | `3` | (no env) | `max_retries_must_be_non_negative` |

**Invariant**: After this epic, `LLMClientConfig.model` remains the **only Python-side declaration** of the K-EXAONE model identifier. No new literal is introduced.

### 1.2 `LLMClient` sampling defaults — preserved by FR-013

**Location**: `src/kosmos/llm/client.py:155-166` (non-streaming) and `:282-293` (streaming)

| Parameter | Value | HF recommendation match |
|---|---|---|
| `temperature` | `1.0` | ✅ K-EXAONE 236B-A23B model card |
| `top_p` | `0.95` | ✅ |
| `presence_penalty` | `0.0` | ✅ |
| `max_tokens` | `1024` | ✅ non-reasoning mode |

### 1.3 `LLMClient` rate-limit retry — preserved by FR-014

**Location**: `src/kosmos/llm/client.py:226-280, 411-613, 698-728, 877-915`

| Component | Behaviour |
|---|---|
| `RetryPolicy` (frozen dataclass `:60-72`) | `max_attempts=5, base_seconds=1.0, cap_seconds=60.0, jitter_ratio=0.2, respect_retry_after=True` |
| `_complete_with_retry` (`:226-280`) | Pre-stream 429 detection + Retry-After-first backoff |
| `_stream_with_retry` (`:411-613`) | Pre-stream 429 + mid-stream SSE 429 detection + Retry-After-first backoff |
| `_is_rate_limit_envelope` (`:698-728`) | SSE-line JSON keys: `error.status==429`, `error.code in {"429","rate_limit","rate_limited"}`, `error.type in {"rate_limit","rate_limited"}` |
| `_compute_rate_limit_delay` (`:893-915`) | Honour `Retry-After` if `respect_retry_after`, else exponential backoff with jitter |
| Per-session concurrency gate | `asyncio.Semaphore(1)` at `:134, 236, 442` |

### 1.4 `enable_thinking` toggle — preserved by FR-015

**Location**: `src/kosmos/llm/client.py:838-844, 854-858`

| Component | Value |
|---|---|
| Env var | `KOSMOS_K_EXAONE_THINKING ∈ {true, 1, yes}` (default `false`) |
| Payload field | `chat_template_kwargs.enable_thinking: bool` |
| Default | `False` for citizen latency (sub-10s vs 60-180s reasoning trace) |

### 1.5 TS source-of-truth — `tui/src/utils/model/model.ts`

| Function | Lines | Returns |
|---|---|---|
| `getDefaultMainLoopModelSetting()` | `:178-180` | `'LGAI-EXAONE/K-EXAONE-236B-A23B'` (anchor) |
| `getDefaultMainLoopModel()` | `:186-188` | `'LGAI-EXAONE/K-EXAONE-236B-A23B' as ModelName` (anchor) |

**Invariant**: After this epic, these two functions remain the **only TypeScript-side declaration** of the K-EXAONE model identifier (FR-012).

---

## 2. Deleted entities

### 2.1 File-level deletions

| File | Pre-change LOC | Status |
|---|---|---|
| `tui/src/services/mockRateLimits.ts` | 882 | **DELETED** (FR-002) |
| `tui/src/services/rateLimitMocking.ts` | ~222 | **DELETED** (FR-003) |

### 2.2 Function-level deletions / collapses inside `tui/src/utils/model/model.ts`

| Function | Pre-change behaviour | Post-change behaviour | FR |
|---|---|---|---|
| `firstPartyNameToCanonical(name)` (`:197-279`) | 15+ if-branches matching `claude-opus-*`, `claude-sonnet-*`, `claude-haiku-*`, `claude-3-*` patterns | Single fail-safe: `name.includes('K-EXAONE') ? 'k-exaone' : (name as ModelShortName)` | FR-005 |
| `getDefaultSonnetModel()` | returns Anthropic Sonnet model ID | Either deleted, or thin alias → `getDefaultMainLoopModel()` per caller-reach rule | FR-006 |
| `getDefaultOpusModel()` | returns Anthropic Opus model ID | Either deleted, or thin alias → `getDefaultMainLoopModel()` per caller-reach rule | FR-006 |
| `getDefaultHaikuModel()` | returns Anthropic Haiku model ID | Either deleted, or thin alias → `getDefaultMainLoopModel()` per caller-reach rule | FR-006 |
| `getSmallFastModel()` (`:38-40`) | reads `ANTHROPIC_SMALL_FAST_MODEL` env, falls back to `getDefaultHaikuModel()` | Returns `getDefaultMainLoopModel()` (no env path) | FR-001/004 |
| `isNonCustomOpusModel(model)` (`:42-49`) | checks `model === modelStrings.opus40 \|\| ... \|\| opus46` | Returns `false` (no Opus model exists in KOSMOS) — or removed if no callers | FR-001 |

### 2.3 Type-level deletions inside `tui/src/services/mockRateLimits.ts` (entire file)

| Type | Lines | Status |
|---|---|---|
| `MockHeaders` (12+ Anthropic header keys) | `:12-41` | **DELETED** with file |
| `MockHeaderKey` | `:43-58` | **DELETED** with file |
| `MockScenario` (20+ scenarios) | `:60-80` | **DELETED** with file |
| `ExceededLimit` | `:92-95` | **DELETED** with file |

### 2.4 Sibling files inside `tui/src/utils/model/` — *may* require editing

These are NOT in the user's stated 3 target files but appear in Phase 0 grep with Anthropic refs. They are **discretionary edits** under the FR-006 caller-reach rule:

| File | Anthropic refs | Likely edit |
|---|---|---|
| `aliases.ts` | model aliases (`opus`, `sonnet`, `haiku`) | trim to `default` alias only |
| `modelAllowlist.ts` | allowed model regexes | reduce to K-EXAONE only |
| `modelCapabilities.ts` | capability lookup | single K-EXAONE branch |
| `modelStrings.ts` | named string lookups | reduce to K-EXAONE constants |
| `modelSupportOverrides.ts` | per-model overrides | empty / K-EXAONE only |
| `deprecation.ts` | claude-3-* deprecation table | empty / removed |
| `configs.ts` | per-model config matrix | K-EXAONE only |
| `bedrock.ts` | AWS Bedrock provider | preserved (out of scope) |
| `agent.ts` | uses `getDefault*Model` helpers | switch to `getDefaultMainLoopModel()` |
| `validateModel.ts` | validates model name | accept K-EXAONE only |
| `providers.ts` | `getAPIProvider`, `isFirstPartyAnthropicBaseUrl` | preserved (P2 boundary) |
| `check1mAccess.ts` | 1M context check (Anthropic-specific) | preserved (P2 boundary, callers external) |
| `contextWindowUpgradeCheck.ts` | upgrade prompt | preserved (P2 boundary) |

**Decision**: Edit aggressively when SC-1 regex 0-hit requires it. Defer edits when callers cross the P2 boundary (`services/api/claude.ts`, OAuth helpers).

---

## 3. Caller-file transitions (FR-006 caller-reach rule)

The 9 external caller files of `firstPartyNameToCanonical` / `getDefault{Sonnet,Opus,Haiku}Model` (Phase 0 grep) get classified by SC-1 perimeter membership:

### Inside SC-1 perimeter (`tui/src/utils/model/`)

| Caller | Helpers used | Edit |
|---|---|---|
| `tui/src/utils/model/model.ts` (self) | self-references | collapse / inline |
| `tui/src/utils/model/agent.ts` | `getDefault*Model` | switch to `getDefaultMainLoopModel()` |
| `tui/src/utils/model/modelOptions.ts` | `getDefault*Model`, `firstPartyNameToCanonical` (transitive) | replace with K-EXAONE constant; remove Anthropic option entries |
| `tui/src/utils/model/modelCapabilities.ts` | `getDefault*Model` | switch to `getDefaultMainLoopModel()` |

### Outside SC-1 perimeter (P2 boundary)

| Caller | Helpers used | Edit (FR-006 rule: keep aliases) |
|---|---|---|
| `tui/src/memdir/findRelevantMemories.ts` | `firstPartyNameToCanonical` | leave call site unchanged; helper becomes thin K-EXAONE alias |
| `tui/src/utils/attachments.ts` | `firstPartyNameToCanonical` | leave call site unchanged |
| `tui/src/commands/insights.ts` | `firstPartyNameToCanonical` | leave call site unchanged |
| `tui/src/services/tokenEstimation.ts` | `firstPartyNameToCanonical` | leave call site unchanged |
| `tui/src/services/api/claude.ts` | `firstPartyNameToCanonical`, `getDefault*Model` | leave call site unchanged (P2-deferred file) |
| `tui/src/components/messages/AssistantTextMessage.tsx` | `firstPartyNameToCanonical` | leave call site unchanged |

**FR-006 caller-reach rule resolution**: Because at least one caller (`services/api/claude.ts`) is outside the SC-1 perimeter, the helpers `getDefaultSonnetModel`, `getDefaultOpusModel`, `getDefaultHaikuModel`, and `firstPartyNameToCanonical` MUST be **kept as thin aliases** returning `getDefaultMainLoopModel()` / `'k-exaone'`. Each alias body MUST carry a `// [Deferred to P2 — issue #NNN]` comment with the GitHub issue number once `/speckit-taskstoissues` resolves the NEEDS TRACKING marker.

---

## 4. Validation matrix (FR ↔ audit command ↔ expected output)

| FR | Audit command | Expected output |
|---|---|---|
| FR-001 | `rg -n -i 'claude-3\|claude-opus\|claude-sonnet\|claude-haiku\|"sonnet"\|"opus"\|"haiku"\|anthropic' tui/src/utils/model/` | 0 matches |
| FR-002 | `test -f tui/src/services/mockRateLimits.ts` | exit 1 (file not found) |
| FR-003 | `test -f tui/src/services/rateLimitMocking.ts` | exit 1 (file not found) |
| FR-004 | `bun -e "import {getDefaultMainLoopModel} from './tui/src/utils/model/model.ts'; console.log(getDefaultMainLoopModel())"` | `LGAI-EXAONE/K-EXAONE-236B-A23B` |
| FR-005 | unit test on `firstPartyNameToCanonical` with random non-K-EXAONE input | returns short-name without throw |
| FR-006 | manual review: each `getDefault{Sonnet,Opus,Haiku}Model` body contains `[Deferred to P2 — issue #...]` comment | comment present |
| FR-007 | `rg 'anthropic-ratelimit-unified' tui/` | 0 matches |
| FR-008 | `rg '\[ANT-ONLY\]\|USER_TYPE === ['\"]ant['\"]' tui/src/utils/model/ tui/src/services/mockRateLimits.ts tui/src/services/rateLimitMocking.ts` | 0 matches (latter two files don't exist) |
| FR-009 | `git diff main...HEAD -- tui/package.json pyproject.toml` (look for added `dependencies` keys) | 0 additions |
| FR-010 | `cd tui && bun test` and `uv run pytest` | ≥ 984 / ≥ 437 pass |
| FR-011 | `bun run tui` smoke (manual or scripted PTY) | both flows complete |
| FR-012 | `rg "K-EXAONE-236B-A23B" --type ts --type py` | only at `model.ts:179,187` and `config.py:37` |
| FR-013 | `rg "temperature: float = 1\.0" src/kosmos/llm/client.py` | matches at `:161` and `:288` |
| FR-014 | `rg "RetryPolicy\|_compute_rate_limit_delay\|_is_rate_limit_envelope" src/kosmos/llm/client.py` | unchanged from baseline |
| FR-015 | `rg "KOSMOS_K_EXAONE_THINKING\|chat_template_kwargs" src/kosmos/llm/client.py` | unchanged from baseline |

---

## 5. State transitions

There is exactly one state transition: **before deletion** → **after deletion**. No runtime state machine. No async transitions. The Python `LLMClient` runtime behaviour is bit-identical pre- and post-change.

```
[BEFORE]                                              [AFTER]
─────────                                              ─────────
mockRateLimits.ts (882 LOC)        ─delete→            (does not exist)
rateLimitMocking.ts (~222 LOC)     ─delete→            (does not exist)
model.ts (598 LOC)                 ─prune→             ≤ ~360 LOC
modelOptions.ts (539 LOC)          ─prune→             ≤ ~280 LOC
firstPartyNameToCanonical 15+      ─collapse→          1-branch fail-safe
getDefault{Sonnet,Opus,Haiku}      ─alias→             return getDefaultMainLoopModel()
[ANT-ONLY] markers in 3 files      ─delete→            absent
Anthropic header schema            ─delete→            absent
src/kosmos/llm/{config,client}.py  ─unchanged→         (FR-012/013/014/015 preserve)
```

Total LOC reduction estimate: 2 019 + ~222 = 2 241 → ~640 = **−1 601 LOC** (≥ 70 % drop), well above SC-006's ≥ 40 % target.
