# KOSMOS — Platform Vision

> This document is the canonical architectural vision for KOSMOS. It is the single source of truth for *what we are trying to build* and *why*. Specs under `specs/` describe how to build individual features; this document describes the whole.
>
> Any spec, ADR, or implementation decision must align with this vision. If a later insight contradicts it, update this file in the same pull request.

## The ambition

Turn the 5,000+ fragmented public APIs on `data.go.kr` into a single conversational interface where a citizen can ask a natural-language question and get an answer backed by live government data — across ministries, across topics, in one session.

```
Citizen:  "내일 부산에서 서울 가는데, 안전한 경로 추천해줘"
KOSMOS:   fuses KOROAD accident data + KMA weather alerts + road-risk index
          → "경부고속도로 대전-천안 구간 위험 등급, 안개 주의보.
             중부내륙 우회를 추천합니다."

Citizen:  "아이가 열이 나는데 근처 야간 응급실 어디야?"
KOSMOS:   fuses 119 emergency service API + HIRA hospital info
          → location-ranked available ERs with current wait times

Citizen:  "출산 보조금 신청하고 싶은데"
KOSMOS:   Ministry of Welfare eligibility API + Gov24 application API
          → eligibility check, required documents, online submission guide
```

The citizen does not learn which ministry runs which API. KOSMOS does the routing.

## Inspiration and reference sources

KOSMOS adapts architectural patterns from the conversational AI agent ecosystem to the Korean public-service domain. We actively reference all available sources — open-source repos, official documentation, reconstructed architecture analyses, and leaked-source review documents — to build the best possible implementation.

### Reference materials

| Source | License / Type | What we adapt |
|---|---|---|
| Claude Agent SDK (`anthropics/claude-agent-sdk-python`) | MIT | Async generator tool loop, permission types, agent definitions, context management |
| OpenAI Agents SDK (`openai/openai-agents-python`) | MIT | Guardrail pipeline, retry matrix with composable policies, agent handoff patterns |
| Pydantic AI (`pydantic/pydantic-ai`) | MIT | Schema-driven tool registry, graph-based state machine, Pydantic v2 message assembly |
| AutoGen (`microsoft/autogen`) | MIT | AgentRuntime mailbox IPC, InterventionHandler for permission interception, cooperative cancellation |
| Anthropic Cookbook (`anthropic-cookbook`) | MIT | Orchestrator-workers pattern, multi-agent coordination examples |
| Anthropic, OpenAI official documentation | Public | Tool use protocols, prompt caching, context window management |
| Ink (`vadimdemedes/ink`) | MIT | React-based terminal UI framework — Claude Code's TUI framework |
| Gemini CLI (`google-gemini/gemini-cli`) | Apache-2.0 | Full Ink + React + Yoga TUI implementation, component hierarchy, hooks, themes |
| Claude Code sourcemap (`ChinaSiro/claude-code-sourcemap`) | Reconstructed | Tool loop internals, permission model, context assembly, TUI component structure |
| Claude Reviews Claude (`openedclaude/claude-reviews-claude`) | Analysis | Detailed architectural review, state management, rendering pipeline, design rationale |
| Claw Code (`ultraworkers/claw-code`) | Harness/Fork | Leaked source repackaged as harness — runtime behavior, hook system, tool execution flow |
| PublicDataReader (`WooilJeong/PublicDataReader`) | MIT | Korean `data.go.kr` API wire format ground truth — auth patterns, XML/JSON response normalization, inconsistent field names across ministries |
| "Don't Break the Cache" (arXiv 2601.06007) | Open access | Empirical prompt caching study: dynamic tool results at end preserve cache prefix, 41–80% cost cut in 30–50+ tool-call sessions |
| NeMo Guardrails (`NVIDIA/NeMo-Guardrails`) | Apache-2.0 | Colang 2.0 declarative tool-call validation rails — whitelist-of-approved-actions model, auditable policy language for PIPA compliance |
| Google ADK (`google/adk-python`) | Apache-2.0 | Runner-level plugin pattern for centralized permission enforcement, reflect-and-retry tool failure handling |
| LangGraph (`langchain-ai/langgraph`) | MIT | `RetryPolicy` per-node exponential backoff, `ToolNode(handle_tool_errors=True)` — Pydantic `ValidationError` fail-closed lesson at tool boundary |
| Mastra (`mastra-ai/mastra`) | Apache-2.0 | TypeScript agent framework — typed tool workflow graphs with loops, branching, human-in-the-loop; Phase 2 TUI layer reference |
| Korean Public APIs index (`yybmion/public-apis-4Kr`) | MIT | Curated `data.go.kr` API discovery index with auth type annotations — tool registry `search_hint` population |

### What is original to KOSMOS

The patterns above are general-purpose. KOSMOS's contribution is adapting them to the government public-service domain, which introduces constraints absent from coding agents:

- **Bilingual tool discovery** over 5,000+ heterogeneous government APIs with inconsistent schemas
- **Bypass-immune permission pipeline** for citizen PII protection (governed by Korea's PIPA, not developer convenience)
- **Multi-ministry agent coordination** where dependency ordering is dictated by law (e.g., residence transfer must precede vehicle registration)
- **Prompt cache partitioning** for cost-efficient government AI services (taxpayer-funded budget constraints)
- **Fail-closed API adapters** where the safe default is deny, not allow

## Six-layer architecture

KOSMOS is built around six architectural layers, each adapting a pattern family into the public-service domain.

| # | Layer | Role | Pattern family |
|---|---|---|---|
| 1 | **Query Engine** | The `while(True)` tool loop that resolves a civil-affairs request | Async generator state machine |
| 2 | **Tool System** | Registry and factory for `data.go.kr` API adapters | Schema-driven tool modules |
| 3 | **Permission Pipeline** | Citizen authentication and personal-data protection gate | Multi-step bypass-immune gauntlet |
| 4 | **Agent Swarms** | Ministry-specialist agents coordinated by an orchestrator | Mailbox IPC + coordinator synthesis |
| 5 | **Context Assembly** | The 3-tier context the LLM sees each turn | System + memory + attachments |
| 6 | **Error Recovery** | Resilience against public API outages, rate limits, maintenance | `withRetry`-style error matrix |

The rest of this document walks each layer in detail.

---

## Layer 1 — Query Engine

The query engine is the heartbeat of a KOSMOS session. It runs an async generator loop that does not terminate until the citizen's request is resolved or unrecoverably blocked.

### Loop skeleton

```
async generator query(session):
    while True:
        1. Pre-process: load citizen context → compress prior turns
                         → identify relevant ministries
        2. Call LLM: intent analysis + task decomposition
        3. Post-process: execute selected public API tools,
                         parse results, handle errors
        4. Decide: more info needed (tool_use) or civil-affairs
                   resolved (end_turn)
```

### Three design decisions carried over

**Async generators as the communication protocol.** No callbacks, no event buses. The loop `yield`s progress events; the caller applies backpressure by consuming at its own rate; cancellation propagates naturally when the consumer stops. A citizen pressing "cancel" must abort every in-flight API call — async generator cancellation gets this right without extra machinery.

**Mutable conversation history plus immutable per-call snapshots.** The conversation list is mutated in place as tools append results, but each LLM call receives an immutable copy. This is the single most important trick for keeping the prompt cache alive as the session grows. Without it, every tool response invalidates the cache and costs multiply.

**Multi-stage preprocessing pipeline.** Before each LLM call, the loop runs compression passes: tool-result budget, snip, microcompact, collapse, autocompact. A citizen doing residence transfer + vehicle address change + health insurance update in one session will blow the context window fast without this pipeline.

### Query state

```
QueryState:
    citizen_session       # auth level, profile, consent flags
    messages              # mutable conversation history
    active_agents         # currently spawned ministry workers
    usage_tracker         # per-API call budget and rate-limit accounting
    pending_api_calls     # in-flight tool invocations
    resolved_tasks        # completed civil-affairs sub-goals
```

### Termination conditions

```
StopReason:
    task_complete           # civil-affairs resolved
    needs_citizen_input     # awaiting clarification
    needs_authentication    # identity verification required
    api_budget_exceeded     # daily quota hit
    error_unrecoverable     # no fallback path
```

### Cost accounting as a first-class concern

Every LLM call and every public API call is debited against a session budget. `data.go.kr` APIs have daily per-key quotas; the engine tracks remaining quota per API and can substitute cached results or alternative APIs when approaching the limit. Observability hooks (OpenTelemetry-style counters) emit metrics for model tokens, cache hits, and per-ministry call counts.

---

## Layer 2 — Tool System

Each public API is wrapped as a **tool module** with a schema-driven registration and fail-closed defaults.

### Tool definition shape

```
GovAPITool:
    id                        # "koroad_accident_info"
    name_ko                   # "교통사고정보"
    provider                  # "도로교통공단"
    category                  # ["교통", "안전"]
    endpoint                  # API URL
    auth_type                 # public | api_key | oauth
    input_schema              # Pydantic model
    output_schema             # Pydantic model
    requires_auth             # default True
    is_concurrency_safe       # default False
    is_personal_data          # default True
    cache_ttl_seconds         # default 0
    rate_limit_per_minute     # default 10
    search_hint               # Korean + English discovery keywords
```

New adapters declare only the fields that deviate from the conservative defaults. This fail-closed posture means a new contributor adding an adapter cannot accidentally expose a personal-data-handling API as public.

### Prompt cache partitioning

The tool registry orders tools into two partitions: **core tools** (always loaded, stable across sessions) form the prompt prefix, and **situational tools** (discovered on demand via tool search) form the suffix. Because the prefix is stable, its tokens remain cache-hit across sessions, dramatically lowering the amortized cost of the system prompt.

When a citizen switches from a transport question to a welfare question, the core tool schemas stay cached; only the welfare-specific tools incur a fresh encoding cost.

### Lazy tool discovery

With potentially 5,000+ public APIs, shipping every schema in the prompt is infeasible. The system keeps a small core set (roughly 15 high-frequency tools) always loaded, and exposes a `search_tools(query)` meta-tool that finds additional tools by `search_hint` keywords.

```
Citizen:  "출산 보조금 신청하고 싶어요"
LLM:      search_tools("출산 보조금 복지부")
          → discovers ministry-of-welfare childbirth subsidy API
LLM:      calls the discovered tool
```

---

## Layer 3 — Permission Pipeline

Public data is not the same as unconstrained data. Citizens' personal information flows through KOSMOS and must be gated.

### Multi-step gauntlet

Every tool invocation passes through a sequence of checks:

1. **Configuration rules** — per-API access tier (public, authenticated, restricted)
2. **Intent analysis** — does the natural-language request justify this tool?
3. **Parameter inspection** — do the arguments contain personal identifiers the citizen is not entitled to query?
4. **Citizen authentication** — is the required identity verification level in place?
5. **Ministry terms-of-use** — has the citizen consented to this ministry's data usage terms?
6. **Sandboxed execution** — the API call runs in an isolated context with no ambient credentials
7. **Audit log** — every call is logged with timestamp, citizen id, API, parameters, and outcome

### Bypass-immune steps

Certain checks **cannot be overridden** by any mode, including automation or administrator bypass modes. These include: querying another citizen's personal records, accessing medical records without explicit consent, and writing actions (application, modification, cancellation) without the identity verification level they require. A future "YOLO mode" must still respect these walls.

### Classifier separation of concerns

When LLM-based classifiers are used for intent risk assessment, they see **only the proposed tool calls and their arguments** — never the assistant's own justifying text. This prevents the model from talking the classifier into approving an action by writing convincing prose.

### Refusal circuit breaker

If the same session triggers a configurable number of consecutive refusals, KOSMOS stops retrying and routes the citizen to a human channel (call center or in-person service). This avoids infinite loops where the agent keeps trying variations of a disallowed action.

---

## Layer 4 — Agent Swarms

For multi-ministry requests, a single monolithic agent is insufficient. KOSMOS uses a coordinator-and-workers swarm.

### Mailbox IPC

Workers and the coordinator communicate through a durable message mailbox rather than in-process callbacks. Initial implementation uses a file-based mailbox for simplicity; production scaling can migrate to a message queue (Redis Streams or similar) while keeping the same interface.

Why a mailbox: cross-process communication, crash resilience (messages persist), trivial debugging (inspect the mailbox contents directly), and no service discovery or daemon orchestration needed at small scale.

### Coordinator workflow

The coordinator is not a task dispatcher — it is a **synthesis engine**. Its workflow is always `Research → Synthesis → Implementation → Verification`:

```
Citizen: "이사 준비 중인데, 전입신고랑 자동차 주소변경이랑
         건강보험 주소변경 다 해야 하는데"

Coordinator:
  Research (parallel workers):
    ├─ Civil affairs agent → Gov24 residence transfer requirements
    ├─ Transport agent     → vehicle registration address change
    └─ Welfare agent       → health insurance address change

  Synthesis (coordinator, never delegated):
    "All three require residence transfer to happen first.
     After that, vehicle and health insurance can run in parallel."

  Implementation:
    Step 1: residence transfer (sequential — prerequisite)
    Step 2: vehicle + health insurance (parallel — independent)

  Verification (parallel):
    └─ confirm each transaction succeeded
```

The coordinator owns synthesis. Workers return raw findings; the coordinator integrates them into a plan.

### Permission delegation across agents

When a worker needs a permission its caller did not grant (for example, the transport agent needs the citizen's digital certificate for a vehicle address change), it sends a `permission_request` message up to the coordinator. The coordinator asks the citizen, receives the credential, and returns a `permission_response`. The worker then proceeds. Permissions never flow laterally between workers.

---

## Layer 5 — Context Assembly

The LLM sees a layered context on every turn.

### Memory tiers

```
1. System   — platform-wide policies (one file, applies to everyone)
2. Region   — region-specific rules (e.g., Busan ordinances)
3. Citizen  — the authenticated citizen's profile (age, residence, family)
4. Session  — what has been established in this conversation
5. Auto     — prior civil-affairs history (auto-memorized patterns)
```

Memory files support conditional activation. A rule block for senior-welfare APIs can be gated on `age >= 65` so younger citizens never see those tools, reducing prompt surface and avoiding irrelevant suggestions.

### Per-turn attachments

Each turn the loop collects fresh dynamic context with a short timeout budget:

- Current authentication level and expiry
- In-flight civil-affairs state (what tools were called last turn)
- Relevant benefit programs derived from the citizen profile
- Live API health monitor (what is currently under maintenance)
- Session-scoped call count and remaining quota

### Reminder cadence

Long sessions drift. Every N turns the loop injects a reminder: unfinished tasks, authentication expiry warning, suggested related services. This keeps the model oriented without requiring the citizen to repeat themselves.

---

## Layer 6 — Error Recovery

Public APIs fail in predictable ways. The engine routes each failure class to a specific recovery strategy.

```
Public API call → error?
  ├── 429 Rate limited      → exponential backoff (base 1s, cap 60s)
  ├── 503 Maintenance       → search for alternative API → else advise citizen
  ├── 401 Auth expired      → refresh token, retry once
  ├── Timeout               → retry ×3, fall back to cached result
  ├── Data inconsistency    → cross-verify with a second ministry API
  └── Hard failure          → graceful message + in-person service guidance
```

**Foreground vs background distinction.** A citizen actively waiting on a response is a foreground query — aggressive retry is appropriate. A background batch (statistics refresh, auto-memory cleanup) is not worth extending an API outage for; it fails fast.

---

## Citizen scenarios (design targets)

KOSMOS success means the following conversations work end-to-end on a real citizen's day:

1. **Route safety** — "오늘 서울 가는 길 안전해?" → combines KOROAD + KMA + road risk → actionable recommendation
2. **Emergency care** — "아이가 열이 나는데 근처 야간 응급실 어디야?" → 119 + HIRA → ranked available ERs
3. **Childbirth benefits** — "출산 보조금 신청하고 싶은데" → MOHW eligibility + Gov24 application guide
4. **Residence transfer** — "이사 준비 중이야" → Gov24 + vehicle registration + health insurance coordinated
5. **Disaster response** — "우리 동네 호우경보 떴는데 뭐 준비해야 돼?" → KMA + NEMA + local government notices

These are the acceptance tests. If the platform cannot complete them, the vision is not met.

## Roadmap

- **Phase 1 — Prototype** — FriendliAI Serverless + 10 high-value APIs + single query engine + CLI. Scenario 1 working end-to-end.
- **Phase 2 — Swarm** — Ministry-specialist agents, mailbox IPC, multi-API synthesis. Scenarios 1–3 working.
- **Phase 3 — Production** — Full permission pipeline, identity verification, audit logging, all scenarios working, public beta.

## Code scope estimates

Approximate implementation sizes per layer, for rough planning only:

| Layer | Estimate |
|---|---|
| Query Engine | ~5,000 lines |
| Tool System | ~2,000 lines + N adapters |
| Permission Pipeline | ~6,000 lines |
| Agent Swarms | ~8,000 lines |
| Context Assembly | ~5,000 lines |
| Error Recovery | ~3,000 lines |

Total target: ~30,000 lines for the platform core, plus adapter modules.

---

## Non-goals

- KOSMOS is not a general-purpose coding agent. It does not edit files or run shell commands in a developer workspace.
- KOSMOS is not a government-endorsed service. It consumes public data but makes no claim of official authority.
- KOSMOS is not a chat wrapper around a single API. A chat wrapper would not need six architectural layers.

## How this document evolves

This file is expected to change as we learn. Rules of change:

1. Any change that alters a layer's contract must also update `AGENTS.md` and any dependent spec in the same pull request.
2. The six-layer breakdown is load-bearing. Do not collapse or rename layers without an ADR.
3. Additions are easier than changes. If in doubt, add a new sub-section rather than rewriting an existing one.
