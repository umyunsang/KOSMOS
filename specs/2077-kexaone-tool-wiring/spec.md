# Feature Specification: K-EXAONE Tool Wiring (CC Reference Migration)

**Feature Branch**: `2077-kexaone-tool-wiring`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "K-EXAONE tool wiring (CC reference migration): TUI ChatRequestFrame.tools 가 비어 있고 backend system prompt 에 도구 시그니처 inject 가 없어서 K-EXAONE 이 KOSMOS-등록 도구 (lookup/resolve_location/submit/subscribe/verify primitive 5종 + MVP-7 보조) 를 모르고 CC 학습 데이터 도구 (Read/Glob/Bash 등) 를 hallucinate 한다. 본 epic 은 (1) TUI Tool object pool 을 ToolDefinition[] 으로 직렬화해 ChatRequestFrame.tools 에 spread, (2) backend 가 system prompt 에 Available tools 섹션 자동 inject + frame.tools 빈 경우 ToolRegistry.export_core_tools_openai() fallback, (3) 5-primitive 화이트리스트를 primitives 카탈로그 single-source-of-truth 로 마이그레이션, (4) tool_call frame 을 SystemMessage 가 아닌 CC-style stream_event{tool_use content_block} 으로 paint 해서 AssistantToolUseMessage 가 native 렌더, (5) tool_result frame 을 user-role tool_result content block 으로 transcript 에 합류시켜 다음 turn LLM context 에 진입, (6) 자동 거부되던 permission_request frame 을 PermissionGauntletModal 실 modal 로 wire — 이 6 변경으로 K-EXAONE hallucination 0 회 + multi-turn agentic loop closure (citizen prompt → tool_use box → tool_result envelope → 자연어 응답) 를 보장한다."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen receives accurate answer grounded in real public-service data (Priority: P1)

A citizen opens the KOSMOS terminal interface, types a Korean public-service question (e.g., "강남구 근처 24시간 응급실 알려주세요"), and within seconds receives a natural-language answer that is grounded in real government data — not fabricated. The agent autonomously selects the appropriate KOSMOS-registered tool, calls it, observes the result, and synthesizes the final answer.

**Why this priority**: Without this, KOSMOS fails its core mission. The agent currently invents tool names (e.g., `Read`, `Glob`, `Bash`) it learned from Claude Code training data, none of which exist in KOSMOS. The citizen sees neither tool execution nor a useful answer — only a hallucinated transcript. Fixing this is the platform's table-stakes correctness.

**Independent Test**: A citizen prompt that requires a public-service lookup ("강남구 응급실") completes end-to-end: tool invocation → tool result → natural-language answer paint, with zero references to tools the platform does not register.

**Acceptance Scenarios**:

1. **Given** the agent has just started a session, **When** the citizen asks "강남구 근처 24시간 응급실 알려주세요", **Then** the agent invokes one of the registered KOSMOS tools (e.g., a hospital-search lookup), receives a tool result envelope, and emits a final assistant message that incorporates that result.
2. **Given** the agent receives a citizen prompt that does not require a tool, **When** the model decides to answer directly, **Then** the conversation completes in one turn with no tool invocation and no spurious tool-call output.
3. **Given** the agent emits a tool name that does not exist in the platform's inventory, **When** the backend processes the model output, **Then** the platform returns a structured "unknown tool" error back to the model in the next turn so it can correct itself, instead of either silently dropping the call or executing an unrelated tool.

---

### User Story 2 — Citizen sees a transparent record of every tool the agent uses (Priority: P2)

While the agent works on a citizen's request, the citizen watches each tool invocation appear in the conversation transcript as a distinct, persistent record: which tool was called, what arguments it received, and what envelope of data it returned. The record looks the same whether the agent calls one tool or chains several across multiple turns.

**Why this priority**: Trust in a public-service AI requires that the citizen can audit every action the agent took on their behalf. Without transparent tool rendering, the agent looks like a black box that occasionally produces an answer. With it, citizens — and the auditor reviewing a session log — can verify each step.

**Independent Test**: After the citizen's prompt completes, the transcript shows a stable, scrollable record of every tool invocation and every tool result, structured in a way that survives session save/resume.

**Acceptance Scenarios**:

1. **Given** the citizen sends a prompt that triggers a tool call, **When** the agent invokes the tool, **Then** the transcript permanently shows a tool-invocation record carrying the tool name, the arguments passed, and a stable identifier that links the invocation to its result.
2. **Given** a tool invocation has been recorded, **When** the tool finishes executing (success or failure), **Then** the transcript permanently shows a tool-result record linked by the same identifier, displaying the result envelope (or error reason).
3. **Given** the agent calls more than one tool in a single turn, **When** the turn completes, **Then** every invocation has its own transcript record and every record has a matching result record — no orphans.
4. **Given** the citizen saves the session and resumes it later, **When** the transcript is reloaded, **Then** every tool invocation and result from the prior turns is still present and pairs correctly.

---

### User Story 3 — Citizen explicitly approves or denies any irreversible action (Priority: P2)

When the agent is about to perform an irreversible action on the citizen's behalf (e.g., submitting a form to a government API, subscribing to an alert stream), the platform pauses execution and shows the citizen an interactive consent prompt. The citizen reviews what the agent wants to do, in plain Korean, and either grants or denies the action. The agent only proceeds if consent is granted.

**Why this priority**: KOSMOS's permission gauntlet (Spec 033) is the citizen's safety net against irreversible mistakes. Today, every gated request is silently auto-denied, which means submit-class primitives never run end-to-end. Without working consent, the platform cannot demonstrate any irreversible workflow at all.

**Independent Test**: A citizen prompt that triggers a gated primitive (e.g., "출생신고 서류 제출") opens an on-screen consent prompt that the citizen can confirm, after which the underlying tool actually runs.

**Acceptance Scenarios**:

1. **Given** the agent decides to invoke a gated primitive, **When** the platform receives the permission request, **Then** an interactive consent prompt appears within 1 second showing the action description, risk level, and a stable receipt identifier.
2. **Given** the consent prompt is open, **When** the citizen approves the action, **Then** the platform records the approval, dismisses the prompt, and the tool runs.
3. **Given** the consent prompt is open, **When** the citizen denies the action, **Then** the platform records the denial, dismisses the prompt, and the agent receives a structured denial result so it can adjust its plan.
4. **Given** the consent prompt is open, **When** the citizen takes no action for the configured timeout window, **Then** the platform records a timeout outcome and the agent receives a structured timeout result instead of hanging.

---

### Edge Cases

- The agent emits a tool name that is not in the active inventory (hallucination): backend rejects the invocation and returns an "unknown tool" error to the agent for next-turn correction; the citizen never sees a fabricated tool result.
- The agent emits a tool call with malformed arguments (invalid JSON, missing required fields): the platform returns a structured validation error to the agent; the citizen sees a tool-result record marked as "validation failed."
- The agent invokes more than one tool in a single turn: every invocation receives its own transcript record and its own result record; results return to the agent as a single batched context for the next turn.
- A tool execution exceeds its time budget: the platform marks the result as a timeout, returns it to the agent, and surfaces a timeout entry in the transcript.
- The citizen interrupts mid-tool-execution (Esc): the platform aborts the running tool, marks the result as cancelled, and the agent receives a cancellation result so it can wind down gracefully.
- The TUI sends a tool inventory that conflicts with the backend's authoritative registry (e.g., includes a tool the backend does not know): the backend ignores the unknown entries and proceeds with the intersection, logging the discrepancy for observability.
- The TUI sends an empty tool inventory (e.g., during early-session bootstrapping): the backend falls back to the registry-default inventory so the agent is never invoked with zero tools.
- The agent's response stream contains a tool_use block whose closing marker is dropped or arrives after the stream's terminal event: the platform treats the call as malformed and returns a structured error rather than executing partially.
- A second tool invocation arrives while the consent prompt for a prior invocation is still open: the second invocation queues in order and only opens its prompt after the prior decision is recorded.

## Requirements *(mandatory)*

### Functional Requirements

#### Tool inventory communication

- **FR-001**: System MUST publish the active tool inventory to the language model on every conversation turn, so the model knows which tools it is permitted to call.
- **FR-002**: System MUST surface the inventory in two coherent forms — a structured tool-definition list and an inline catalog visible inside the system prompt — so models that consult either form receive the same answer.
- **FR-003**: System MUST source the inventory from a single authoritative registry; no part of the platform may maintain a separate, hardcoded enumeration of permitted tools.
- **FR-004**: System MUST provide a fallback inventory when the conversation initiator does not supply one, so the agent is never invoked with an empty tool list.
- **FR-005**: System MUST refuse to execute any tool name that is not in the active inventory and MUST return a structured "unknown tool" error to the model in the next turn.

#### Transparent tool rendering

- **FR-006**: System MUST render every tool invocation as a persistent, transcript-native record carrying the tool name, the arguments passed, and a stable identifier that pairs invocation to result.
- **FR-007**: System MUST render every tool result as a persistent, transcript-native record linked to the originating invocation by the stable identifier from FR-006.
- **FR-008**: System MUST preserve every tool-invocation and tool-result record across session save and resume.
- **FR-009**: System MUST guarantee one-to-one pairing between invocations and results for every successfully completed turn — no orphan invocations and no orphan results — and surface unpaired records as visible errors.

#### Multi-turn closure

- **FR-010**: System MUST include the prior turn's tool results in the model's context for the next turn so the model can reason over them.
- **FR-011**: System MUST support a configurable maximum number of agentic turns within a single citizen prompt and MUST stop the loop deterministically when the limit is reached.
- **FR-012**: System MUST preserve the platform's existing rate-limit and retry behavior across the agentic loop so multi-turn invocations do not exhaust the upstream model provider's quota.

#### Interactive consent

- **FR-013**: For every gated primitive invocation, System MUST present an interactive consent prompt to the citizen before the tool runs.
- **FR-014**: The consent prompt MUST display the action description in Korean (primary) with English fallback, the risk level, and a stable receipt identifier.
- **FR-015**: System MUST cancel the underlying tool invocation when the citizen denies consent and MUST return a structured denial result to the agent.
- **FR-016**: System MUST proceed with the tool invocation when the citizen grants consent and MUST emit the consent receipt to the audit ledger.
- **FR-017**: System MUST treat consent inactivity beyond the configured timeout as a timeout outcome and return a structured timeout result to the agent instead of hanging.
- **FR-018**: While a consent prompt is open, System MUST queue subsequent invocations in arrival order and MUST NOT open a second prompt until the prior decision is recorded.

#### Observability and operational continuity

- **FR-019**: System MUST preserve every existing observability span on the tool path (tool-call, tool-result, permission-request, permission-decision, audit receipt) including all current attribute keys.
- **FR-020**: System MUST not introduce any runtime dependency outside the project's existing dependency manifest.

### Key Entities

- **Tool inventory**: The authoritative collection of tools the agent is permitted to invoke during a session. Each entry carries a name, a human-readable description, an argument schema, an authority/risk classification, and a stable identifier. The platform exposes this collection both as a structured payload (for the model's tool-use channel) and as text inside the system prompt.
- **Tool invocation record**: An immutable transcript entry identifying a single tool call by name, arguments, and a stable identifier. Lives alongside the agent's natural-language output in the same conversation transcript.
- **Tool result record**: An immutable transcript entry pairing a single tool result envelope to its originating invocation by stable identifier. Carries success or error status and the result payload.
- **Consent decision**: An immutable record of a citizen's response (granted/denied/timeout) to a single gated invocation, identified by the receipt identifier shown in the consent prompt and durable in the audit ledger.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a fresh session starts, K-EXAONE invokes only tools the platform actually registers — zero invocations of tool names from outside the active inventory across a 50-prompt scripted regression.
- **SC-002**: For a citizen prompt that requires one tool ("강남구 24시간 응급실"), the citizen sees the tool-invocation record, the tool-result record, and the final natural-language answer all paint within 30 seconds of pressing Enter (FriendliAI Tier 1 baseline, no rate-limit retry).
- **SC-003**: For a citizen prompt that triggers a gated primitive ("출생신고 서류 제출"), the consent prompt appears within 1 second of the agent's decision, and the tool either runs or is cancelled within 1 second of the citizen's input.
- **SC-004**: A multi-turn agentic conversation (4–5 turns of tool-use → tool-result → next-turn) completes inside the upstream provider's per-minute request budget with zero rate-limit-induced failures on the citizen's screen.
- **SC-005**: All existing observability spans on the tool path remain emitted with no missing attribute keys after the change, verified by trace replay across a regression session.
- **SC-006**: The change ships with zero new runtime dependencies in the project's dependency manifest (AGENTS.md hard rule).
- **SC-007**: A first-time citizen, given only the prompt "강남구 응급실 알려주세요", reaches a useful answer without retry on at least 95% of attempts in a 20-attempt rehearsal.
- **SC-008**: Session save and resume preserves 100% of tool-invocation and tool-result transcript records across sessions of up to 50 turns.

## Assumptions

- The five primitive surface (`lookup`, `resolve_location`, `submit`, `subscribe`, `verify`) plus the MVP-7 auxiliary tools are stable and continue to be the only LLM-visible roots, per `docs/requirements/kosmos-migration-tree.md § L1-C.C6/C7`.
- The platform's existing reference implementation of Claude Code's streaming + agentic loop (`src/kosmos/llm/_cc_reference/claude.ts`) is the canonical migration source for any unclear behavioral question, per `feedback_cc_source_migration_pattern`.
- The interactive consent prompt component is already mounted in the terminal screen (verified at `tui/src/screens/REPL.tsx:5275-5277`); this epic only wires the request/response flow through it.
- The upstream model provider's free-tier rate budget (FriendliAI Tier 1, 60 RPM) is sufficient for typical citizen prompts that take 4–5 agentic turns, per `project_friendli_tier_wait`.
- The platform's existing IPC frame catalogue (Spec 032 envelope: `chat_request`, `assistant_chunk`, `tool_call`, `tool_result`, `permission_request`, `permission_response`) is sufficient; no new frame arms are added by this epic.
- The platform's session store (`useSessionStore`) can be extended with a pending-permission slot without breaking existing consumers.
- The system prompt template (`prompts/system_v1.md`) currently carries no tool-list section; the epic appends the dynamically generated catalog there.
- Korean is the primary language for citizen-facing copy; English is the fallback per `docs/requirements/kosmos-migration-tree.md § UI-A.A.3`.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Composite / macro tool combinations** — explicitly removed by `docs/requirements/kosmos-migration-tree.md § L1-B.B6`. The model chains primitives instead of invoking platform-side macros.
- **Hardcoded tool whitelists outside the registry** — the registry is the single source of truth (see FR-003); duplicate enumerations are forbidden.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Plugin-tier tool discovery in citizen sessions | Plugin DX TUI integration is a separate, parallel epic that requires plugin_op dispatcher + 8-phase progress emit | Epic #1979 (Plugin DX TUI integration) | #1979 |
| Adapter-level Spec 033 Layer 2/3 receipt issuance and audit-ledger persistence | This epic wires the modal but defers ledger work to the broader permission-v2 effort | Permission v2 epic (post-Initiative #1631) | #2105 |
| `lookup` mode split (search vs fetch BM25 routing) | Out of scope for tool wiring; touches retrieval pipeline | Spec 022 follow-up | #2106 |
| `subscribe` primitive long-lived stream behavior | This epic delivers a proof-of-concept only; full subscription lifecycle is its own concern | Future subscribe-stream epic | #2107 |
| Agent swarm coordinator/worker spawn over IPC | Multi-agent coordination is a separate parallel epic with its own architectural questions | Epic #1980 (Agent Swarm TUI integration) | #1980 |
| Onboarding / help / config / history-search UI rendering of the upgraded tool transcript | UI L2 work for these surfaces lives in the citizen-port epic; this epic only delivers the paint chain | Spec 1635 (P4 UI L2 citizen port) follow-ups | #2108 |
| Inline-XML `<tool_call>` legacy parser removal | Not all upstream models emit native function-call channels yet; the legacy parser stays until they do | Future LLM-protocol cleanup epic | #2109 |
| MVP-7 auxiliary client-side execution wiring (Calculator, WebFetch, WebSearch, Translate, DateParser, ExportPDF, Brief) | Routing the LLM-emitted `tool_call` for non-primitives through TUI's `runTools` and back to the backend as a `tool_result` frame requires a separate dispatch path; this epic exposes only the five primitives as LLM-visible to honour FR-003's single-source rule and avoid `unknown_tool` regressions during the wire-up window | Future MVP-7 dispatch epic | NEEDS TRACKING |
