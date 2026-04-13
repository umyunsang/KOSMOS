# Feature Specification: CLI & TUI Interface

**Feature Branch**: `feat/011-cli-tui-interface`
**Created**: 2026-04-13
**Status**: Draft
**Input**: Epic #11 — CLI & TUI Interface (Ink + React)

## Overview & Context

This epic delivers the citizen-facing conversational interface for KOSMOS. The TUI is the primary way citizens interact with the platform: they type natural-language questions and receive answers backed by live government data, rendered in a terminal with streaming output, tool progress indicators, and permission consent prompts.

### Two-phase approach

The work is split into two deliberate phases with distinct technology stacks and goals:

**Phase A — Rapid Prototype (Python: typer + rich)**. A minimal CLI shell that wires directly into the existing Python backend (`QueryEngine`, `ToolRegistry`, `PermissionPipeline`, `ContextBuilder`). Purpose: validate the end-to-end conversation loop (Scenario 1 from `vision.md`) as fast as possible, with zero IPC overhead. This is a throwaway scaffold, not the final deliverable. Target: ~1,500 LOC Python.

**Phase B — Full TUI (TypeScript: Ink + Bun)**. The real deliverable. Forks Claude Code's Ink + React 19 architecture: REPL screen, message rendering, permission dialogs, progress indicators, status line, double-buffered rendering. Communicates with the Python backend via stdio JSON-RPC (JSONL over stdin/stdout). Target: ~5,000 LOC TypeScript. This is Phase 1 stretch / Phase 2 territory.

### Integration surface

The TUI consumes the backend through `QueryEngine.run(user_message)`, which yields an `AsyncIterator[QueryEvent]`. The five event types the TUI must handle:

| Event type | Payload | TUI rendering action |
|---|---|---|
| `text_delta` | `content: str` | Append text to streaming assistant message |
| `tool_use` | `tool_name`, `tool_call_id`, `arguments` | Show spinner with tool name |
| `tool_result` | `ToolResult` (success/error, data) | Replace spinner with result summary |
| `usage_update` | `TokenUsage` | Update status bar counters |
| `stop` | `StopReason`, `stop_message` | Finalize turn, display stop reason if abnormal |

For Phase A (rapid prototype), the TUI imports `QueryEngine` directly as a Python library. For Phase B (Ink TUI), a thin JSON-RPC bridge process translates between TypeScript stdin/stdout and the Python async generator.

---

## User Stories

### User Story 1 — REPL Conversation Loop (Priority: P0)

A citizen launches KOSMOS, sees a welcome banner with usage guidance, types a question, and receives a streamed answer. They can ask follow-up questions in the same session, with the engine maintaining conversation context across turns.

**Why P0**: Without the REPL loop, nothing else functions. This is the skeleton that every other story builds on.

**Acceptance Scenarios**:

1. **Given** a citizen launches `kosmos` (or `python -m kosmos.cli`), **When** the process starts, **Then** they see a welcome banner including the KOSMOS version, a brief description, and an input prompt within 2 seconds.
2. **Given** a citizen at the input prompt, **When** they type a question and press Enter, **Then** the assistant response streams to the terminal character-by-character (not blocked until completion).
3. **Given** a citizen has completed one turn, **When** they type a follow-up question referencing earlier context, **Then** the engine produces a contextually relevant answer demonstrating conversation history is maintained.
4. **Given** a citizen types an empty string or whitespace only, **When** they press Enter, **Then** the prompt redisplays without sending a message to the engine.

---

### User Story 2 — Streaming Response Display (Priority: P0)

As the LLM generates its response, text appears incrementally in the terminal. The citizen sees output growing in real-time rather than waiting for a complete response.

**Why P0**: Streaming is the difference between "instant-feeling" and "frozen terminal". Every modern conversational CLI streams.

**Acceptance Scenarios**:

1. **Given** the engine yields `text_delta` events, **When** the TUI receives them, **Then** each delta is appended to the display buffer and rendered to stdout immediately (latency under 50ms from event receipt to screen update).
2. **Given** a multi-paragraph response, **When** the response contains markdown elements (headers, lists, bold, code blocks), **Then** they are rendered with appropriate terminal formatting (rich markup in Phase A; custom Ink components in Phase B).
3. **Given** a response containing Korean text mixed with English, **When** rendered, **Then** character widths are calculated correctly using full-width CJK character accounting, and text does not overflow or misalign in the terminal.
4. **Given** the engine yields a `stop` event with `StopReason.end_turn` or `task_complete`, **When** the response finishes, **Then** the input prompt reappears and the cursor is positioned for the next question.

---

### User Story 3 — Tool Execution Progress (Priority: P1)

When the engine dispatches tool calls to government APIs, the citizen sees what is happening: which APIs are being queried, whether they succeeded or failed, and a summary of the results.

**Why P1**: Without progress indicators, the terminal appears frozen during API calls. Citizens will think KOSMOS crashed.

**Acceptance Scenarios**:

1. **Given** the engine yields a `tool_use` event, **When** the TUI receives it, **Then** a spinner is displayed with the tool's Korean display name (e.g., `[...] 교통사고정보 조회 중`).
2. **Given** a `tool_result` event with `success=True`, **When** the TUI receives it, **Then** the spinner is replaced with a success indicator and a one-line summary of the result data.
3. **Given** a `tool_result` event with `success=False`, **When** the TUI receives it, **Then** the spinner is replaced with an error indicator showing `error_type` and the human-readable `error` message.
4. **Given** multiple concurrent tool calls (e.g., KOROAD + KMA), **When** both are in flight simultaneously, **Then** the TUI shows separate spinners for each tool, updating them independently as results arrive.
5. **Given** a `usage_update` event, **When** the TUI receives it, **Then** the status line updates with current token usage (e.g., `tokens: 1,234 / 128,000`).

---

### User Story 4 — Error Display and Recovery Guidance (Priority: P1)

When the engine encounters errors (API failures, budget exhaustion, unrecoverable problems), the citizen sees a clear, actionable message rather than a stack trace or silent failure.

**Why P1**: Government service users are not developers. Error messages must be citizen-friendly and guide them to alternatives.

**Acceptance Scenarios**:

1. **Given** a `stop` event with `StopReason.api_budget_exceeded`, **When** the TUI renders it, **Then** the citizen sees a message explaining the session limit was reached and suggesting they start a new session.
2. **Given** a `stop` event with `StopReason.error_unrecoverable`, **When** the TUI renders it, **Then** the citizen sees the `stop_message` text and guidance to contact a human service channel (e.g., government call center 110).
3. **Given** a `stop` event with `StopReason.needs_authentication`, **When** the TUI renders it, **Then** the citizen sees a message explaining that identity verification is required and what steps to take.
4. **Given** the Python backend process crashes or the IPC connection drops (Phase B only), **When** the TUI detects the failure, **Then** it displays a connection error message and exits gracefully rather than hanging.

---

### User Story 5 — Permission Consent Prompts (Priority: P1)

When the permission pipeline encounters an `escalate` decision or a tool requires provider-specific consent, the TUI prompts the citizen to approve or deny the action before proceeding.

**Why P1**: The permission pipeline (Layer 3) has an `escalate` verdict reserved for human-in-the-loop approval. The TUI must support this flow even though v1 permission pipeline treats `escalate` as `deny`. The scaffold must exist for Phase 2.

**Acceptance Scenarios**:

1. **Given** a permission check that requires citizen consent (e.g., accessing personal data from a new provider), **When** the engine yields a consent request event, **Then** the TUI displays the tool name, the provider, what data will be accessed, and `[Y/n]` prompt.
2. **Given** the citizen approves the consent prompt, **When** they type `y` or press Enter (default approve), **Then** the engine proceeds with the tool call.
3. **Given** the citizen denies the consent prompt, **When** they type `n`, **Then** the engine receives a denial and the LLM is informed the tool call was rejected, allowing it to explain alternatives.
4. **Given** a bypass-immune permission (e.g., another citizen's personal records), **When** the tool call is denied by the pipeline, **Then** the TUI displays the denial reason without offering an override option.

---

### User Story 6 — Session Management (Priority: P2)

A citizen can start a new session, see a session identifier for support reference, and cleanly exit the session. Session history is maintained in memory for the duration of the process.

**Why P2**: Essential for usability but not blocking the core conversation loop.

**Acceptance Scenarios**:

1. **Given** a citizen starts KOSMOS, **When** the session initializes, **Then** a unique session ID is generated and displayed in the welcome banner (e.g., `Session: abc123`).
2. **Given** a citizen types `/new` or an equivalent command, **When** the command is processed, **Then** the current session state is discarded, a new `QueryEngine` instance is created, and a new session ID is displayed.
3. **Given** a citizen types `/exit`, `exit`, or `quit`, **When** the command is processed, **Then** the process exits with code 0 after printing a farewell message.
4. **Given** a citizen types `/help`, **When** the command is processed, **Then** a list of available slash commands and usage guidance is displayed.

---

### User Story 7 — Interrupt Handling (Priority: P1)

A citizen can press Ctrl+C to cancel an in-progress operation. A single Ctrl+C cancels the current turn; a double Ctrl+C (within 1 second) exits the process entirely.

**Why P1**: Without interrupt handling, citizens have no way to stop a runaway API call or exit cleanly.

**Acceptance Scenarios**:

1. **Given** the engine is mid-turn (streaming response or waiting for tool results), **When** the citizen presses Ctrl+C once, **Then** the current turn is cancelled via async generator cancellation, any in-flight API calls are aborted, and the input prompt reappears.
2. **Given** the engine yielded a partial response before cancellation, **When** the turn is cancelled, **Then** the partial response remains visible and a `[cancelled]` indicator is appended.
3. **Given** the citizen presses Ctrl+C twice within 1 second, **When** the second signal arrives, **Then** the process exits immediately with code 130 (standard SIGINT exit).
4. **Given** the citizen is at the idle input prompt (no operation in progress), **When** they press Ctrl+C once, **Then** the input line is cleared and the prompt redisplays (same behavior as standard shells).

---

### User Story 8 — Korean Text and CJK Layout (Priority: P2)

Korean text renders correctly in the terminal: proper character widths, no alignment corruption from mixing half-width ASCII and full-width Hangul, and correct line wrapping.

**Why P2**: Correct rendering is table stakes for a Korean-language product, but the conversation loop works even with minor alignment issues.

**Acceptance Scenarios**:

1. **Given** a response containing Korean text, **When** rendered, **Then** each Hangul character occupies 2 terminal columns (verified by string-width equivalent logic).
2. **Given** a table-like display (e.g., tool result summary), **When** columns contain mixed Korean and English text, **Then** columns are aligned correctly using CJK-aware width calculation.
3. **Given** a terminal width of 80 columns, **When** a line containing Korean text approaches the width limit, **Then** line wrapping occurs at a character boundary (never splitting a Hangul syllable).

---

## API Design

### Phase A: Direct Python integration

No IPC needed. The CLI module imports `QueryEngine` directly:

```
kosmos/
  cli/
    __init__.py
    app.py           # typer application, entry point
    repl.py          # REPL loop: prompt -> engine.run() -> render events
    renderer.py      # rich-based event rendering (streaming, spinners, errors)
    models.py        # CLI-specific models (SlashCommand, SessionState)
    config.py        # KOSMOS_CLI_* env vars via pydantic-settings
```

Entry point: `python -m kosmos.cli` or `kosmos` (via pyproject.toml `[project.scripts]`).

**REPL loop pseudocode**:

```python
async def repl_loop(engine: QueryEngine) -> None:
    while True:
        user_input = prompt()          # rich Prompt or input()
        if is_slash_command(user_input):
            handle_command(user_input)
            continue
        if not user_input.strip():
            continue
        async for event in engine.run(user_input):
            render_event(event)        # dispatch to renderer
```

**Renderer dispatch**:

```python
def render_event(event: QueryEvent) -> None:
    match event.type:
        case "text_delta":
            console.print(event.content, end="")
        case "tool_use":
            start_spinner(event.tool_name)
        case "tool_result":
            stop_spinner(event.tool_result)
        case "usage_update":
            update_status_bar(event.usage)
        case "stop":
            render_stop(event.stop_reason, event.stop_message)
```

### Phase B: IPC protocol (stdio JSON-RPC)

The Ink TUI spawns the Python backend as a child process. Communication is JSONL (one JSON object per line) over stdin/stdout.

**Protocol**: JSON-RPC 2.0 subset (request/response + notifications).

**Methods**:

| Method | Direction | Description |
|---|---|---|
| `session.create` | TUI -> Backend | Create a new session, returns `session_id` |
| `session.destroy` | TUI -> Backend | Tear down session and release resources |
| `query.run` | TUI -> Backend | Start a turn; backend streams events as notifications |
| `query.cancel` | TUI -> Backend | Cancel in-progress turn |
| `permission.respond` | TUI -> Backend | Citizen response to consent prompt |

**Notifications (backend -> TUI)**:

| Method | Payload | Maps to |
|---|---|---|
| `event.text_delta` | `{content: string}` | `QueryEvent(type="text_delta")` |
| `event.tool_use` | `{tool_name, tool_call_id, arguments}` | `QueryEvent(type="tool_use")` |
| `event.tool_result` | `{tool_id, success, data?, error?}` | `QueryEvent(type="tool_result")` |
| `event.usage_update` | `{prompt_tokens, completion_tokens, total_tokens}` | `QueryEvent(type="usage_update")` |
| `event.stop` | `{stop_reason, stop_message?}` | `QueryEvent(type="stop")` |
| `event.permission_request` | `{tool_id, provider, description}` | Permission consent needed |

**Wire format example**:

```jsonl
{"jsonrpc":"2.0","method":"query.run","params":{"message":"서울 강남구 교통사고 현황"},"id":1}
{"jsonrpc":"2.0","method":"event.text_delta","params":{"content":"강남구 교통사고"}}
{"jsonrpc":"2.0","method":"event.tool_use","params":{"tool_name":"koroad_accident_search","tool_call_id":"tc_01"}}
{"jsonrpc":"2.0","method":"event.tool_result","params":{"tool_id":"koroad_accident_search","success":true,"data":{"total":42}}}
{"jsonrpc":"2.0","method":"event.text_delta","params":{"content":"를 조회한 결과..."}}
{"jsonrpc":"2.0","method":"event.stop","params":{"stop_reason":"end_turn"}}
{"jsonrpc":"2.0","result":{"status":"ok"},"id":1}
```

### Phase B: Component hierarchy (Ink)

```
tui/
  src/
    index.tsx              # Entry point, Bun.spawn() for Python backend
    app.tsx                # Root <App> component
    screens/
      repl.tsx             # Main REPL screen (messages + input + status)
      welcome.tsx          # Welcome screen with banner
    components/
      messages.tsx         # Virtualized message list
      message.tsx          # Single message (citizen/assistant/system)
      prompt-input.tsx     # Text input with readline fallback
      tool-progress.tsx    # Spinner + tool name during execution
      tool-result.tsx      # Formatted tool result display
      permission-dialog.tsx # Y/n consent prompt
      status-line.tsx      # Bottom bar: session, tokens, turn count
      error-display.tsx    # Formatted error with guidance
      markdown.tsx         # Streaming markdown renderer
    hooks/
      use-backend.ts       # JSON-RPC IPC hook (spawn, send, receive)
      use-session.ts       # Session state management
      use-store.ts         # 35-line store pattern (useSyncExternalStore)
      use-interrupt.ts     # Ctrl+C signal handling
      use-korean-input.ts  # Korean IME workaround (readline fallback)
    store/
      index.ts             # AppState type + createStore()
      actions.ts           # State update actions
    ipc/
      protocol.ts          # JSON-RPC types and serialization
      bridge.ts            # stdin/stdout JSONL transport
    lib/
      cjk-width.ts         # CJK character width calculation
      format.ts            # Number formatting, Korean text utilities
    config.ts              # KOSMOS_* env var loading
```

### State shape (Phase B)

```typescript
interface AppState {
  // Session
  sessionId: string | null;
  backendStatus: "starting" | "ready" | "error" | "stopped";

  // Conversation
  messages: Message[];
  isStreaming: boolean;
  currentStreamContent: string;

  // Tool execution
  activeTools: Map<string, ToolProgress>;

  // Permission
  pendingPermission: PermissionRequest | null;

  // Budget
  tokensUsed: number;
  tokensBudget: number;
  turnsUsed: number;
  turnsBudget: number;

  // UI
  terminalWidth: number;
  terminalHeight: number;
}
```

---

## Non-Goals for V1 Rapid Prototype (Phase A)

The following are explicitly out of scope for the Phase A rapid prototype. They are deferred to Phase B or later:

1. **Full Ink + React TUI** — Phase A uses typer + rich (Python). The TypeScript TUI is Phase B.
2. **IPC / JSON-RPC bridge** — Phase A imports `QueryEngine` directly. No child process.
3. **Virtual scrolling** — Phase A relies on the terminal's native scroll buffer.
4. **Double-buffered rendering** — Phase A uses rich's default rendering (adequate for a prototype).
5. **Themes and color customization** — Hardcoded color scheme only.
6. **Multi-agent UI** — No swarm visualization. Phase A shows only the single-engine conversation.
7. **Session persistence to disk** — Sessions are in-memory only. No save/resume across process restarts.
8. **Markdown streaming renderer (custom)** — Phase A uses rich's built-in Markdown rendering per completed message, not per-delta streaming Markdown.
9. **Accessibility (screen reader support)** — Deferred; Phase A targets sighted terminal users.
10. **Mouse interaction** — Keyboard-only interface.
11. **Korean IME workaround** — Phase A uses Python's `input()` or `prompt_toolkit`, which handle IME natively. The IME issue is Ink-specific.

---

## Dependencies

### Phase A (Rapid Prototype)

| Dependency | Version | Purpose | Already in project? |
|---|---|---|---|
| `typer` | >=0.12 | CLI argument parsing, command routing | No (new) |
| `rich` | >=13.0 | Terminal formatting, spinners, markdown, tables | No (new) |
| `prompt_toolkit` | >=3.0 | Input editing, history, Korean IME support | No (new, optional) |

All three are pure Python, widely used, and add no native compilation requirement.

### Phase B (Ink TUI)

| Dependency | Version | Purpose | Already in project? |
|---|---|---|---|
| `ink` | >=5.0 | React terminal UI framework | No (new) |
| `react` | >=19.0 | Component model | No (new) |
| `@inkjs/ui` | >=2.0 | TextInput, Spinner, Select components | No (new) |
| `string-width` | >=7.0 | CJK character width calculation | No (new) |
| `bun` | >=1.1 | Runtime + bundler + test runner | No (new) |
| `typescript` | >=5.5 | Type system | No (new) |

### Backend dependencies (already exist)

| Module | Import path | What the TUI uses |
|---|---|---|
| Query Engine | `kosmos.engine.engine.QueryEngine` | `.run(user_message) -> AsyncIterator[QueryEvent]` |
| Events | `kosmos.engine.events.QueryEvent`, `StopReason` | Event type discrimination |
| Tool models | `kosmos.tools.models.ToolResult`, `GovAPITool` | Tool result rendering |
| LLM models | `kosmos.llm.models.TokenUsage` | Usage display |
| Config | `kosmos.engine.config.QueryEngineConfig` | Engine configuration |
| Context builder | `kosmos.context.builder.ContextBuilder` | System prompt assembly |
| Tool registry | `kosmos.tools.registry.ToolRegistry` | Tool lookup for display names |
| Tool executor | `kosmos.tools.executor.ToolExecutor` | Passed to QueryEngine |
| Permission models | `kosmos.permissions.models.SessionContext` | Session setup |
| LLM client | `kosmos.llm.client.LLMClient` | Passed to QueryEngine |

---

## Risks and Open Questions

### R1: Korean IME in Ink (Phase B only, High risk)

**Problem**: Korean Input Method Editor (IME) composition does not work in Ink's custom stdin handling. This is a known unsolved issue across multiple Ink-based projects (Claude Code #19207, Gemini CLI #3014). Intermediate composition states (e.g., combining jamo into a syllable block) are not rendered correctly.

**Mitigation**: Use a readline-based input fallback for Phase B. Instead of Ink's `<TextInput>`, spawn a separate readline prompt that captures the full composed line and sends it to the Ink process. This sacrifices inline editing UX but guarantees correct Korean input.

**Decision needed**: Accept the readline fallback, or invest in patching Ink's stdin handling upstream?

### R2: Process lifecycle management (Phase B, Medium risk)

**Problem**: The Ink TUI spawns the Python backend as a child process via `Bun.spawn()`. Graceful shutdown requires coordinating three signals: citizen Ctrl+C, Ink process exit, and Python process termination. Edge cases include the Python process crashing mid-turn, the citizen force-killing the TUI, and zombie process cleanup.

**Mitigation**: Implement a process supervisor in the `use-backend` hook: SIGTERM on TUI exit, readiness probe on startup (wait for `session.create` response within 5 seconds), and a watchdog timer that detects backend unresponsiveness (no heartbeat for 10 seconds).

### R3: Streaming Markdown rendering (Phase A, Low risk)

**Problem**: `text_delta` events arrive as raw character chunks, not complete Markdown. Rich's `Markdown` class expects a complete string. Rendering Markdown per-delta requires either buffering until a logical break or implementing a streaming Markdown parser.

**Mitigation for Phase A**: Buffer deltas and render the complete message with rich Markdown only after the `stop` event. During streaming, display raw text. This is acceptable for a prototype.

**Mitigation for Phase B**: Implement a streaming Markdown renderer in Ink that incrementally parses and renders as deltas arrive (similar to Claude Code's approach).

### R4: Terminal width and CJK column calculation (Phase A+B, Low risk)

**Problem**: Accurate column width is needed for proper alignment. Korean characters are 2 columns wide, but some edge cases (emoji, combining characters) are tricky.

**Mitigation**: In Phase A, use `rich`'s built-in `cell_len()` which handles CJK. In Phase B, use `string-width` (npm), which is the standard solution for this in the Node/Bun ecosystem.

### R5: Dependency addition requires spec-driven PR (Low risk)

**Problem**: `AGENTS.md` hard rule: "Never add a dependency outside a spec-driven PR." Adding `typer`, `rich`, and `prompt_toolkit` constitutes new dependencies.

**Mitigation**: This spec serves as the justification. All three libraries are well-maintained, widely adopted, pure Python, and introduce no security concern. They are CLI-layer only and do not affect the backend.

### R6: Stack change ADR requirement (Phase B, Medium risk)

**Problem**: Introducing Bun + TypeScript + Ink is a stack change. `AGENTS.md` requires an ADR for stack changes.

**Mitigation**: An ADR will be written as the first task of Phase B, before any TypeScript code is written. The decision was already documented in `AGENTS.md` ("TypeScript is allowed only for the TUI layer") and `docs/vision.md` (reference table includes Ink, Gemini CLI, @inkjs/ui), so the ADR formalizes an existing agreement.

### Open Questions

1. **prompt_toolkit vs builtin input()**: Is `prompt_toolkit` worth the dependency for Phase A, or is Python's built-in `input()` with `readline` sufficient? The tradeoff: `prompt_toolkit` adds history, auto-complete, and better Korean IME support, but is another dependency.

2. **Consent prompt flow for Phase A**: The permission pipeline currently treats `escalate` as `deny`. Should Phase A implement the consent prompt UI anyway (wired to a mock escalation path), or should we skip consent prompts entirely in Phase A and just display the denial?

3. **Phase B entry point**: Should the full Ink TUI be a separate npm package under `tui/` at the repo root, or a subdirectory under `src/`? The Ink TUI has its own dependency tree (package.json), so a top-level `tui/` directory seems cleaner.

4. **Backend startup time**: The Python backend imports several modules and initializes the tool registry. How long does cold start take? If it exceeds 2 seconds, the TUI should show a loading indicator during backend initialization.

---

## Success Criteria

### Phase A (Rapid Prototype)

- **SC-A1**: Citizen can complete Scenario 1 from `vision.md` ("Route safety") end-to-end in a single session: ask about road safety, see KOROAD and KMA tool calls with progress indicators, receive a synthesized answer.
- **SC-A2**: Streaming text display has perceptible character-by-character output (not batched).
- **SC-A3**: Ctrl+C cancels a mid-turn operation and returns to the prompt within 1 second.
- **SC-A4**: All error stop reasons display citizen-friendly messages (no stack traces in normal operation).
- **SC-A5**: Korean text renders without alignment corruption in terminals 80 columns or wider.
- **SC-A6**: The CLI starts and displays the welcome banner within 3 seconds on a cold start.

### Phase B (Ink TUI)

- **SC-B1**: All Phase A success criteria hold.
- **SC-B2**: IPC bridge handles 100+ events per second without dropped messages or display lag.
- **SC-B3**: Backend crash is detected and reported to the citizen within 5 seconds.
- **SC-B4**: Double Ctrl+C exits the process (both TUI and backend) within 500ms.
- **SC-B5**: Korean IME input works via readline fallback (complete syllable composition before submission).

---

## Assumptions

- The Query Engine (Epic #5, completed) provides a stable `AsyncIterator[QueryEvent]` interface.
- The Tool System (Epic #6, completed) provides `ToolRegistry` with `lookup()` and `search()`, and `ToolExecutor` with `dispatch()`.
- The Permission Pipeline (Epic #8, completed) provides `PermissionPipeline.run()` returning `PermissionStepResult` with `allow`/`deny`/`escalate` decisions.
- The Context Assembly (Epic #9, completed) provides `ContextBuilder.build_system_message()` and `build_assembled_context()`.
- The LLM Client (Epic #4, completed) provides `LLMClient` with async streaming via FriendliAI Serverless.
- API adapters (Epic #7, completed) for KOROAD and KMA are registered and functional.
- The target terminal environment supports ANSI escape codes and Unicode (UTF-8). Windows Terminal, iTerm2, and standard Linux terminals all qualify.
- `uv` is the package manager. No `requirements.txt` or `setup.py`.
