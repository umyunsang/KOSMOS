# Feature Specification: KOSMOS System Prompt Redesign

**Feature Branch**: `feat/2152-system-prompt-redesign`
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description for Epic #2152 — migrate the Claude Code 2.1.88 system-prompt architecture (section-based static prefix + dynamic suffix + boundary marker + per-tool trigger guidance) to the KOSMOS citizen-domain harness so K-EXAONE reliably invokes Korean public-data tools (`lookup`, `resolve_location`, `kma_*`, `hira_*`, `nfa119_*`, `nmc_*`, `mohw_*`) when a citizen asks a domain question, and so the prompt stops leaking Claude Code developer context (cwd, git status, CLAUDE.md) into citizen conversations.

## Background

KOSMOS is a student portfolio harness migrating Claude Code's developer-domain agentic tool loop into a citizen-domain Korean public-services harness on top of the K-EXAONE LLM. Epic #1631 (P0–P6 foundation) and Epic #2112 (P1+P2 dead-Anthropic-model removal + agentic loop wiring) shipped a working `ChatRequestFrame` agentic loop. The end-to-end smoke recordings under `specs/2112-dead-anthropic-models/smoke.txt` showed that K-EXAONE replies to citizen queries with direct text rather than calling the available domain tools — a failure of the system prompt, not the loop. The deep research artifact `docs/research/system-prompt-harness-comparison.md` (PR #2151) compared seven harness architectures and produced six concrete actions (R1–R6). This spec converts those research actions into a single shippable Epic.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen location query triggers a tool call (Priority: P1)

A Korean citizen opens the KOSMOS terminal interface and asks a location question in plain Korean — for example, "강남역 어디야?" or "서울시청 주소 알려줘". The assistant must recognise this as a Korean-public-data domain question and call the location-resolution tool against an authoritative source rather than answering from model knowledge.

**Why this priority**: This is the headline failure observed in the Epic #2112 smoke run and the original motivation for this Epic. If a citizen cannot ask "where is 강남역" and have the system call a real tool, the entire harness premise (citizen-domain agentic loop) is broken.

**Independent Test**: Launch the TUI, send the prompt "강남역 어디야?", and capture the IPC frame stream. The session must contain at least one `tool_call` / `tool_use` IPC frame for the resolve-location tool **before** the assistant emits its final answer text. Verifiable by `grep -c 'tool_use\|tool_call' smoke.txt`.

**Acceptance Scenarios**:

1. **Given** a fresh TUI session, **When** the citizen sends "강남역 어디야?", **Then** the assistant invokes the location-resolution tool and references the tool result in its Korean reply.
2. **Given** a fresh TUI session, **When** the citizen sends "서울시청 가는 길", **Then** the assistant invokes the location-resolution tool and produces a Korean answer that cites the tool's data source.

---

### User Story 2 — Citizen weather query triggers a tool call (Priority: P1)

A Korean citizen asks about Korean weather, temperature, rain, snow, or typhoon information — for example, "오늘 서울 날씨 알려줘" or "내일 부산 비 와?". The assistant must call the weather-forecast tool against the Korean Meteorological Administration data feed and synthesise the answer from the tool result rather than from the model's training data.

**Why this priority**: Weather is a top-three citizen query class for any public-services assistant and the second concrete failure observed in the Epic #2112 smoke run. The two P1 stories together make up the headline regression that this Epic must close.

**Independent Test**: Launch the TUI, send "오늘 서울 날씨 알려줘", capture the IPC frame stream. The session must contain at least one tool call against the weather adapter and the assistant's Korean reply must reference an explicit data attribution (for example, "기상청 자료에 따르면…").

**Acceptance Scenarios**:

1. **Given** a fresh TUI session, **When** the citizen sends "오늘 서울 날씨 알려줘", **Then** the assistant invokes the KMA forecast tool and produces a Korean answer that explicitly attributes the data to the Korean Meteorological Administration.
2. **Given** a fresh TUI session, **When** the citizen sends "주말 제주 날씨", **Then** the assistant invokes the KMA forecast tool with a region payload covering Jeju and produces a Korean answer.

---

### User Story 3 — Citizen-facing prompt no longer leaks developer context (Priority: P1)

A Korean citizen asks any question. The assistant's reply must never reference the developer's working directory, git branch, recent commits, the CLAUDE.md file, or any other artefact of the host machine the TUI happens to run on. The assistant treats the user as a Korean citizen seeking public information, not as a developer working on a codebase.

**Why this priority**: The Epic #2112 smoke run showed the assistant saying "현재 `/Users/um-yunsang/KOSMOS/tui` 디렉토리에서 작업 중이며…" in reply to a citizen weather query. That single failure mode breaks every other improvement: the citizen frame collapses the moment the assistant talks about cwd or git. This story is the gating cleanup for Stories 1 and 2 to work in production.

**Independent Test**: After excision, a static repository search of the TUI source for the developer-context functions (`getSystemContext`, `appendSystemContext`, `prependUserContext`, `getUserContext`) returns zero matches outside test fixtures and the `_cc_reference` / `.references` mirror trees. Live smoke replies contain no path, no branch name, no commit SHA, and no `CLAUDE.md` reference.

**Acceptance Scenarios**:

1. **Given** the citizen TUI emit path, **When** a chat request is built, **Then** no developer-context payload (cwd, git status, CLAUDE.md content) is attached to the system or user message stack.
2. **Given** any of the five smoke scenarios, **When** the assistant replies, **Then** the reply text contains no filesystem path, no git branch name, and no CLAUDE.md citation.

---

### User Story 4 — Privacy and prompt-injection defence on citizen input (Priority: P2)

A citizen pastes free-form text — including text that resembles instructions, headings, or fake "system" markers (for example, a forwarded email containing "## Available tools" or "<system>Ignore previous instructions</system>"). The assistant must treat this as a citizen utterance, not as a new instruction.

**Why this priority**: Citizens routinely paste real-world content (forms, notices, screenshots-as-text) when asking for help. A harness that allows citizen-pasted content to escalate into instructions is unsafe to ship.

**Independent Test**: Send a chat request whose user message contains a forged `## Available tools` block plus an "Ignore previous instructions" sentence. The assistant must continue to honour the original system prompt and (when relevant) still invoke the appropriate Korean public-data tool.

**Acceptance Scenarios**:

1. **Given** a citizen utterance containing a forged instruction block, **When** the assistant processes the turn, **Then** the assistant ignores the forged instructions and continues to follow the original system prompt.
2. **Given** any citizen utterance, **When** the chat request is assembled, **Then** the citizen text is structurally distinguishable from system instructions in the prompt envelope.

---

### User Story 5 — Prompt cache stays warm across turns (Priority: P2)

A citizen sends two messages in the same TUI session. The static portion of the system prompt must be byte-identical between the two turns so the LLM provider's prompt cache can serve the second turn from the same cache prefix as the first, keeping perceived latency and cost low.

**Why this priority**: The harness already emits a `kosmos.prompt.hash` OTEL attribute (Spec 026) precisely so the team can observe cache health. Two consecutive turns with different hashes means the prompt is being recomputed per turn — wasted tokens and broken cache economics.

**Independent Test**: Run a TUI session, send two messages, capture the OTEL spans for both turns, and assert that `kosmos.prompt.hash` from turn 1 equals turn 2.

**Acceptance Scenarios**:

1. **Given** the same session and the same set of registered tools, **When** the citizen sends a second message, **Then** the `kosmos.prompt.hash` for turn 2 equals turn 1.
2. **Given** a session where dynamic context changes between turns (for example, a new ministry-scope opt-in), **When** the citizen sends the next message, **Then** the static prefix hash remains stable while only the dynamic suffix changes.

---

### User Story 6 — Korean-only output with citation discipline (Priority: P3)

The assistant always replies in Korean unless the citizen has explicitly written in another language. Whenever the reply summarises tool output, it must attribute the information to the source ("기상청 자료에 따르면…", "HIRA 검색 결과로는…") so the citizen can trust where the answer came from.

**Why this priority**: Language consistency and source attribution are foundational citizen-trust properties. They were already implicit in `prompts/system_v1.md` v1, but with no XML structure or concrete examples the model drifts. This story formalises both as testable acceptance criteria rather than aspirational prose.

**Independent Test**: Across the five smoke scenarios, every assistant reply must be in Korean (no English filler, no cwd-style English status), and every reply that summarises a tool result must include an explicit Korean attribution phrase referencing the upstream agency or data source.

**Acceptance Scenarios**:

1. **Given** a Korean-language citizen utterance, **When** the assistant replies, **Then** the reply is in Korean and contains no English boilerplate.
2. **Given** a tool call returned data, **When** the assistant uses that data in its reply, **Then** the reply contains an explicit Korean attribution phrase naming the upstream Korean public-data source.

---

### Edge Cases

- A citizen pastes a multi-thousand-character form. The assistant must still apply the citizen-input wrapping discipline; long input does not relax prompt-injection defences.
- The TUI is launched outside a git repository. The chat request emit path must contain no git-status fallback warning text — the absence of git is a no-op, not an error to surface to the citizen.
- The citizen explicitly asks in English ("Where is Gangnam Station?"). The assistant should still invoke the location tool and may reply in the citizen's language; the Korean default does not block English on explicit citizen choice.
- The citizen asks something outside the registered tool surface (for example, a personal-finance question). The assistant must not fabricate a tool call and must say plainly that no Korean public-data tool covers the request.
- The dynamic suffix grows large (many memdir consent receipts). The static prefix hash must remain stable; only the dynamic suffix grows.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present its static system prompt as four named sections — citizen role, core rules, tool-usage guidance, and output style — using XML tag boundaries that let the model parse each section unambiguously.
- **FR-002**: System MUST include a citizen-domain identity sentence that frames the assistant as a Korean public-services intermediary, distinct from any developer-coding-assistant identity.
- **FR-003**: System MUST include concrete trigger examples for each registered citizen-data tool, written so the model can map a Korean citizen utterance ("강남역 어디?", "오늘 날씨", "근처 응급실", "어린이 보호구역 사고") to the correct tool name without guessing.
- **FR-004**: System MUST emit a per-tool trigger-phrase line in the tool inventory it shows the model, beside each tool's structured description.
- **FR-005**: System MUST insert a stable boundary marker between the cacheable static prefix and the dynamic per-turn suffix.
- **FR-006**: System MUST keep the static prefix byte-identical across two consecutive turns of the same session when the registered tool set is unchanged.
- **FR-007**: System MUST hash only the static prefix into the OTEL `kosmos.prompt.hash` attribute so observability of cache prefix stability is meaningful.
- **FR-008**: System MUST assemble a dynamic suffix per turn that may include the session's start date, the citizen's active ministry-scope opt-ins, and any active consent-receipt summaries — without invalidating the static-prefix cache.
- **FR-009**: System MUST wrap each citizen utterance in a structurally distinct envelope so any instruction-shaped citizen text cannot be mistaken for system instructions.
- **FR-010**: System MUST NOT include the host machine's working directory, git status, recent git commits, the developer's CLAUDE.md file, or any other developer-domain context in any chat request emitted to the LLM.
- **FR-011**: System MUST default the assistant's reply language to Korean and require explicit attribution to the upstream Korean public-data source whenever a reply summarises a tool result.
- **FR-012**: System MUST be expressed entirely in source-tree files that live under `prompts/` and `src/kosmos/llm/` for the backend portion and under `tui/src/` for the citizen-input wrapping portion, with no new runtime dependencies in `pyproject.toml` or `package.json`.
- **FR-013**: System MUST preserve the existing prompt-registry integrity contract: each prompt file's SHA-256 in `prompts/manifest.yaml` must continue to match the file's content (Spec 026 invariant).
- **FR-014**: System MUST expose the dynamic-section assembler as a structured, type-checked surface so future per-turn injectors (memdir state, consent ledger summaries) can register without mutating the static prefix.
- **FR-015**: System MUST preserve byte-identical output for any code path where the registered tool list is empty (no-tools no-op) so existing tests that exercise that path continue to pass without modification.

### Key Entities

- **Static system prompt**: The four-section, XML-tagged Korean-public-services prompt body that is byte-stable across turns of a session and forms the LLM provider's cache prefix.
- **Dynamic suffix**: The per-turn portion appended after the boundary marker, carrying date, ministry-scope, consent summary, and any future per-turn context.
- **Boundary marker**: A literal token between the static prefix and the dynamic suffix that downstream tooling (cache hash, observability) can detect deterministically.
- **Tool inventory block**: The structured `## Available tools` section emitted alongside the system prompt, enriched in this Epic with a one-line trigger phrase per registered tool.
- **Citizen utterance envelope**: A structurally distinct wrapping around the citizen's user message at the chat-request boundary, used to prevent prompt injection from citizen-pasted content.
- **Developer-context callsites**: The set of TUI source locations that previously injected cwd, git status, and CLAUDE.md content into chat requests; these are excised in this Epic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-1**: In the citizen smoke recording for this Epic (`specs/2152-system-prompt-redesign/smoke.txt`), at least three of the five citizen scenarios contain a tool-call IPC frame before the assistant's final answer. Verifiable by `grep -c 'tool_use\|tool_call' specs/2152-system-prompt-redesign/smoke.txt` returning a value of 3 or more.
- **SC-2**: The shipped `prompts/system_v1.md` contains all four required XML tag pairs (`<role>…</role>`, `<core_rules>…</core_rules>`, `<tool_usage>…</tool_usage>`, `<output_style>…</output_style>`).
- **SC-3**: The OTEL `kosmos.prompt.hash` attribute is byte-stable across two consecutive turns of the same session with an unchanged registered tool set. Verifiable by capturing two spans and asserting equality.
- **SC-4**: The TUI chat-request emit path contains zero references to the developer-context functions and zero references to working directory or git status. Verifiable by `git grep -E 'getSystemContext|appendSystemContext|prependUserContext|getUserContext' tui/src/ | grep -v __tests__ | grep -v _cc_reference` returning zero lines, plus a similar zero-result grep for `cwd` and `git status` in any file the chat-request path imports.
- **SC-5**: Test parity with `main` is preserved. `bun test` reports at least 984 passing tests and `uv run pytest` reports at least 3458 passing tests on this branch. The single pre-existing snapshot failure in TS and the single pre-existing failure in Python carried over from `main` are tolerated.
- **SC-6**: Zero new runtime dependencies are added. Verifiable by `git diff main -- pyproject.toml package.json tui/package.json` showing no net additions in any dependency block.

## Assumptions

- The K-EXAONE model deployed on FriendliAI Tier 1 follows the same prompt-engineering responsiveness curve documented for Anthropic Claude Opus 4.6 / 4.7 — strong response to clear identity framing and to per-tool trigger phrases. This assumption is the basis for adopting the CC system-prompt architecture verbatim. If K-EXAONE diverges materially, the Phase 5 smoke recording will surface it and the trigger phrases will be retuned in a follow-up.
- The set of Korean public-data tools registered at the time of this Epic — `lookup`, `resolve_location`, the KMA forecast adapters, the HIRA hospital adapter, the NFA119 / NMC emergency adapters, and the MOHW adapter — is sufficient to demonstrate at least three tool-triggering smoke scenarios. New plugin-registered tools (Epic #1636) compose with this prompt automatically because the inventory section is generated from the live registry.
- The TUI's existing `ChatRequestFrame` (Spec 032 + Epic #2077) already carries the `system` and `messages` fields the redesign needs; no IPC schema change is required.
- The Spec 026 prompt-registry SHA-256 manifest is the canonical integrity contract for all prompt files; any rewrite of `prompts/system_v1.md` updates the manifest hash.
- Developer-context callsites in the TUI are no longer reachable from any non-chat-request flow that citizens hit. The agent-tool path that still legitimately consumes developer context remains a valid use of the function inside its own module; this Epic's excision applies to the citizen chat-request path only.
- Korean-language prose inside `<role>` and `<core_rules>` is the approved exception to the project's English-source rule because the prose is a Korean-domain artefact directly seen by Korean citizens.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Model selection logic** — Already removed in Epic #2112 (PR #2151). This Epic does not touch any LLM provider routing, model identifier handling, or rate-limit fixture code.
- **Tool registration plumbing** — Owned by Spec 1634 (P3 backend tool-registry wiring) and Spec 2077 (P3 K-EXAONE tool-call execution). This Epic only consumes the existing registry through the prompt inventory; it adds no new tool, no new registration path, no new validator.
- **Plugin developer experience** — Owned by Epic #1636 (P5 plugin DX). This Epic does not change `kosmos plugin init`, `kosmos plugin install`, the SLSA verification path, or the plugin manifest schema.
- **LLM provider switching** — The migration from Anthropic to FriendliAI is owned by Spec 1633 (P2). This Epic accepts the existing provider as given.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Multi-language i18n for the citizen prompt (Korean / English / 日本語 dynamic switching) | UI L2 decision A.3 already approved Korean primary with English and Japanese as later additions; this Epic delivers the Korean-only baseline first. | P5+ (UI L2 follow-up) | #2199 |
| Output-style configuration surface (citizen accessibility, large-font, screen-reader-tuned voice) | The citizen accessibility toggles defined in UI L2 A.4 belong with the broader accessibility epic; conflating them with the system-prompt rewrite would expand scope past the headline regression. | P5+ (UI L2 accessibility) | #2200 |
| Prompt A/B evaluation harness with shadow-eval workflow | The Spec 026 P2 backlog already owns the twin-run-on-`prompts/**`-PRs workflow. This Epic ships the prompt change; the eval harness validates future changes. | Spec 026 P2 backlog | #2201 |
| Rich dynamic injectors for memdir consent and ministry-scope state | The dynamic-suffix assembler shipped here exposes the registration surface (FR-014). Concrete memdir / ministry-scope adapters that read from the consent ledger live with the consent-ledger work. | UI L2 C.3 / Spec 035 follow-up | #2202 |
