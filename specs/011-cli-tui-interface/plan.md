# Implementation Plan: CLI & TUI Interface (Phase A — Python Rapid Prototype)

**Branch**: `feat/011-cli-tui-interface` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Epic #11 — CLI & TUI Interface (Ink + React)

---

## Summary

Phase A delivers a Python-based rapid prototype CLI that validates the end-to-end citizen conversation loop (Scenario 1 from `vision.md`) as fast as possible. The CLI is a thin consumer of the existing backend APIs: `QueryEngine.run()` yields `AsyncIterator[QueryEvent]`, and the CLI renders those events through a Rich-based display pipeline. No new backend abstractions are introduced.

The CLI adds three new dependencies (`typer`, `rich`, `prompt-toolkit`) and a single new sub-package `src/kosmos/cli/`. It targets approximately 1,500 LOC of Python. Phase B (Ink + Bun TypeScript TUI) is explicitly deferred.

---

## Technical Context

**Language/Version**: Python 3.12+
**New Dependencies**: `typer>=0.12` (CLI framework), `rich>=13.0` (terminal rendering), `prompt-toolkit>=3.0` (input editing, history, Korean IME)
**Existing Dependencies Consumed**: `httpx>=0.27`, `pydantic>=2.0`, `pydantic-settings>=2.0`
**Storage**: N/A — in-memory session state only; no persistence across process restarts
**Testing**: `uv run pytest` — unit tests for renderer, permissions, REPL; integration test with mock LLM; no live API calls
**Target Platform**: macOS (developer), Linux (CI); terminals supporting ANSI + UTF-8
**Project Type**: Application sub-package (`src/kosmos/cli/`) consumed by `python -m kosmos.cli`
**Constraints**: No `print()` in backend modules (per AGENTS.md); all terminal output through Rich rendering pipeline. English source text; Korean user-facing strings are Korean domain data (permitted exception).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Notes |
|---|---|---|
| I -- Reference-Driven Development | PASS | Design decisions mapped to sources in `docs/vision.md` Reference materials. See Phase 0 below. |
| II -- Fail-Closed Security | PASS | CLI layer does not introduce new security surfaces. Permission pipeline runs inside `QueryEngine`; CLI only renders outcomes. Consent prompt scaffold displays pipeline decisions, does not override them. |
| III -- Pydantic v2 Strict Typing | PASS | CLI config uses `pydantic-settings`. CLI-specific models (`SessionState`, `SlashCommand`) are Pydantic v2 frozen models. No `Any` in I/O. |
| IV -- Government API Compliance | PASS | CLI does not call `data.go.kr` directly. All API interaction flows through `QueryEngine` -> `ToolExecutor` -> adapters. No hardcoded keys; `KOSMOS_` prefix on all env vars. |
| V -- Policy Alignment | PASS | CLI implements the "single conversational window" (Principle 8) by surfacing cross-ministry tool results in one session. Consent prompts scaffold Principle 5 (consent-based data access). |
| Dev Standards | PASS | `stdlib logging` in CLI internals; Rich for terminal output (allowed per ruff `T20` exception on `src/kosmos/cli/**`). `uv + pyproject.toml`. English source text. |

**Dependency Justification**: Three new dependencies (`typer`, `rich`, `prompt-toolkit`) are pure Python, widely adopted, and CLI-layer only. `typer` and `rich` are already listed in `pyproject.toml` dependencies. `prompt-toolkit` will be added. All three are justified by this spec-driven PR per AGENTS.md.

---

## Phase 0 -- Research

### Primary references consulted

| Decision Area | Source | Finding Applied |
|---|---|---|
| TUI component architecture | `ChinaSiro/claude-code-sourcemap` (TUI components, REPL screen, message rendering) | REPL loop structure: prompt -> engine.run() -> event dispatch -> render. Streaming text display via live update. Tool progress as inline spinners. |
| TUI rendering pipeline | `openedclaude/claude-reviews-claude` (TUI rendering, state management) | Renderer is a pure function from event -> terminal output. No intermediate state machine between events and display. Double-buffered rendering deferred to Phase B (Ink). |
| Ink + React terminal UI framework | `vadimdemedes/ink`, `google-gemini/gemini-cli` | Phase B reference only. Phase A uses Rich as the Python equivalent of Ink's rendering model: live displays, spinners, panels, markdown. |
| Permission consent prompts | Claude Agent SDK (permission types), `openedclaude/claude-reviews-claude` (permission model) | Consent prompt is a blocking Y/n prompt that gates tool execution. V1 permission pipeline treats `escalate` as `deny`, so the consent scaffold is forward-looking. |
| Event streaming model | Claude Agent SDK (async generator tool loop) | `QueryEngine.run()` yields `QueryEvent` discriminated union. CLI dispatches on `event.type` with a match statement. Same pattern as Claude Agent SDK's event loop. |
| Interrupt handling | `ultraworkers/claw-code` (runtime behavior, hook system) | Single Ctrl+C cancels async generator (raises `asyncio.CancelledError`). Double Ctrl+C within 1 second exits process with code 130. |
| CLI framework selection | Gemini CLI (TypeScript CLI entry), `typer` documentation | `typer` provides argument parsing, `--help`, and command routing. Thin wrapper over `click`. Entry point via `python -m kosmos.cli`. |
| Korean text rendering | `rich` documentation (`cell_len()`), `string-width` (npm, Phase B reference) | Rich handles CJK double-width characters natively via `cell_len()`. No custom width calculation needed for Phase A. |
| Configuration pattern | Existing `kosmos.llm.config.LLMClientConfig` (pydantic-settings) | CLI config follows the same pattern: `pydantic-settings` with `KOSMOS_CLI_*` prefixed env vars. |

### Existing backend code the CLI consumes

| Module | Import Path | What the CLI Uses |
|---|---|---|
| Query Engine | `kosmos.engine.QueryEngine` | `.run(user_message) -> AsyncIterator[QueryEvent]` -- the primary API |
| Engine Config | `kosmos.engine.QueryEngineConfig` | Session configuration (max_turns, context_window) |
| Events | `kosmos.engine.events.QueryEvent`, `StopReason` | Event type discrimination in renderer dispatch |
| Session Budget | `kosmos.engine.models.SessionBudget` | `QueryEngine.budget` property for status bar |
| Tool Registry | `kosmos.tools.registry.ToolRegistry` | `lookup(tool_id)` for Korean display names (`name_ko`) |
| Tool Executor | `kosmos.tools.executor.ToolExecutor` | Passed to `QueryEngine` constructor |
| Tool Models | `kosmos.tools.models.ToolResult` | Tool result rendering (success/error, data display) |
| LLM Client | `kosmos.llm.client.LLMClient` | Passed to `QueryEngine` constructor |
| LLM Config | `kosmos.llm.config.LLMClientConfig` | LLM client initialization |
| LLM Models | `kosmos.llm.models.TokenUsage` | Token usage display in status bar |
| Context Builder | `kosmos.context.builder.ContextBuilder` | Passed to `QueryEngine` constructor (optional) |
| Permissions | `kosmos.permissions.SessionContext` | Session setup for permission pipeline |
| Permission Pipeline | `kosmos.permissions.PermissionPipeline` | Passed to `QueryContext` for tool gating |

### Technical decisions resolved

1. **`prompt-toolkit` vs `input()`**: Use `prompt-toolkit`. It provides readline-style editing, persistent command history, and native Korean IME composition support. The incremental complexity over `input()` is justified by the UX improvement for a Korean-language product. `input()` with `readline` has known issues with multi-byte IME composition on macOS.

2. **Consent prompt approach for Phase A**: Implement the consent prompt UI scaffold wired to a mock escalation path. When the permission pipeline returns `escalate` (currently treated as `deny`), the CLI displays what the prompt would look like but respects the `deny` decision. This validates the UX flow without changing backend semantics.

3. **Streaming Markdown rendering**: Phase A buffers `text_delta` events and displays raw text during streaming. After the `stop` event, the complete message is re-rendered with Rich Markdown formatting. This avoids the complexity of a streaming Markdown parser while preserving the streaming feel.

4. **Status bar approach**: Use Rich's `Status` context manager for spinners and Rich's `Console` for inline status updates. No persistent status bar in Phase A (deferred to Phase B's Ink status-line component). Token usage is printed as a one-line summary after each turn.

---

## Architecture

### Module structure: `src/kosmos/cli/`

```
src/kosmos/cli/
+-- __init__.py           # Public exports: create_app()
+-- __main__.py           # Entry point: python -m kosmos.cli
+-- app.py                # typer application, command routing
+-- config.py             # CLIConfig: KOSMOS_CLI_* env vars via pydantic-settings
+-- models.py             # SlashCommand, SessionState (frozen Pydantic v2 models)
+-- repl.py               # REPL loop: prompt -> engine.run() -> render events
+-- renderer.py           # Rich-based event rendering (streaming, spinners, errors)
+-- permissions.py        # Consent prompt handler (rich.prompt Y/n)
```

### Class responsibilities

**`CLIConfig`** (pydantic-settings):
- `KOSMOS_CLI_HISTORY_SIZE: int = 1000` -- prompt history depth
- `KOSMOS_CLI_THEME: str = "default"` -- reserved for future theming
- `KOSMOS_CLI_SHOW_USAGE: bool = True` -- show token usage after each turn
- `KOSMOS_CLI_WELCOME_BANNER: bool = True` -- show welcome banner on start

**`SessionState`** (dataclass, mutable):
- `session_id: str` -- UUID for this session
- `engine: QueryEngine` -- the active engine instance
- `turn_count: int` -- local turn counter (mirrors engine state)
- `is_streaming: bool` -- whether a turn is in progress (for interrupt handling)

**`EventRenderer`** (stateless class):
- `render(event: QueryEvent, console: Console) -> None` -- main dispatch
- Private methods for each event type: `_render_text_delta`, `_render_tool_use`, `_render_tool_result`, `_render_usage_update`, `_render_stop`
- Uses Rich's `Live` display for streaming text, `Status` for spinners, `Panel` for tool results, `Markdown` for final message formatting

**`REPLLoop`** (async):
- Owns the prompt-toolkit session (history, key bindings)
- Slash command routing: `/help`, `/new`, `/exit`, `/usage`
- Interrupt handling: single Ctrl+C -> cancel turn, double Ctrl+C -> exit
- Main loop: `prompt -> validate -> engine.run() -> render events -> repeat`

**`ConsentPromptHandler`**:
- `prompt(tool_name: str, provider: str, description: str) -> bool` -- display consent prompt, return citizen decision
- Uses `rich.prompt.Confirm` for Y/n interaction
- Forward-looking scaffold: v1 permission pipeline treats `escalate` as `deny`, so this is exercised only in test/demo mode

### Integration flow

```
__main__.py
  -> app.py (typer CLI entry)
    -> create QueryEngine(llm_client, registry, executor, config, context_builder)
    -> create SessionState(session_id, engine)
    -> REPLLoop(session_state, renderer, console).run()
      -> prompt_toolkit input
      -> engine.run(user_input) -> AsyncIterator[QueryEvent]
        -> EventRenderer.render(event, console) for each event
      -> loop
```

### Dependency direction

```
cli/ -> engine/  (QueryEngine, QueryEvent, StopReason, SessionBudget)
cli/ -> tools/   (ToolRegistry.lookup for display names, ToolResult for rendering)
cli/ -> llm/     (LLMClient, LLMClientConfig, TokenUsage)
cli/ -> context/ (ContextBuilder)
cli/ -> permissions/ (PermissionPipeline, SessionContext)
```

The CLI imports from all backend layers but nothing imports from CLI. This is correct: the CLI is a leaf package with no downstream consumers.

---

## Data Model

### CLI-specific models (`cli/models.py`)

```python
class SlashCommand(BaseModel):
    """Definition of a CLI slash command."""
    model_config = ConfigDict(frozen=True)

    name: str           # e.g. "/help"
    description: str    # e.g. "Show available commands"
    aliases: tuple[str, ...] = ()  # e.g. ("exit", "quit") for /exit
```

### CLI configuration (`cli/config.py`)

```python
class CLIConfig(BaseSettings):
    """CLI-specific settings loaded from KOSMOS_CLI_* environment variables."""
    model_config = SettingsConfigDict(
        env_prefix="KOSMOS_CLI_",
        case_sensitive=False,
        extra="ignore",
    )

    history_size: int = 1000
    show_usage: bool = True
    welcome_banner: bool = True
```

---

## File Structure

### Documentation

```
specs/011-cli-tui-interface/
+-- spec.md           # Approved specification (input)
+-- plan.md           # This file
+-- tasks.md          # Generated by /speckit-tasks (not yet created)
```

### Source code

```
src/kosmos/cli/
+-- __init__.py       # Public exports
+-- __main__.py       # Entry point: python -m kosmos.cli
+-- app.py            # typer application and command routing
+-- config.py         # CLIConfig (pydantic-settings)
+-- models.py         # SlashCommand and other CLI models
+-- repl.py           # REPL loop with prompt-toolkit
+-- renderer.py       # Rich-based QueryEvent rendering
+-- permissions.py    # Consent prompt handler

tests/cli/
+-- __init__.py
+-- test_config.py
+-- test_models.py
+-- test_renderer.py
+-- test_permissions.py
+-- test_repl.py
+-- test_integration.py
```

### Modified files

```
pyproject.toml        # Add prompt-toolkit>=3.0 to dependencies;
                      # Add [project.scripts] kosmos = "kosmos.cli.app:main"
```

---

## Implementation Phases

### Phase 1 -- Foundation (Models + Config + Package Skeleton)

**Goal**: Establish the `src/kosmos/cli/` sub-package with configuration, data models, and a minimal `__main__.py` that prints a welcome banner and exits.

**Files**:
- `src/kosmos/cli/__init__.py` -- export `CLIConfig`, `create_app`
- `src/kosmos/cli/config.py` -- `CLIConfig` via pydantic-settings (`KOSMOS_CLI_*` env vars)
- `src/kosmos/cli/models.py` -- `SlashCommand` frozen Pydantic model
- `src/kosmos/cli/__main__.py` -- minimal entry point: import and call `main()`
- `src/kosmos/cli/app.py` -- `typer.Typer()` app with `main()` command (prints banner, exits)
- `pyproject.toml` -- add `prompt-toolkit>=3.0` to dependencies; add `[project.scripts]` entry

**Tests**:
- `tests/cli/__init__.py`
- `tests/cli/test_config.py` -- validate defaults, env var override, frozen config
- `tests/cli/test_models.py` -- validate SlashCommand construction, frozen constraint

**Completion gate**: `python -m kosmos.cli --help` works. `uv run pytest tests/cli/test_config.py tests/cli/test_models.py` passes.

### Phase 2 -- Event Renderer

**Goal**: Implement the Rich-based event rendering pipeline that converts `QueryEvent` instances into terminal output. This is the core display module.

**Files**:
- `src/kosmos/cli/renderer.py` -- `EventRenderer` class with dispatch method:
  - `text_delta` -- append text to a `rich.live.Live` display buffer; render raw text during streaming
  - `tool_use` -- display `rich.status.Status` spinner with tool's Korean name (`name_ko` from `ToolRegistry.lookup()`)
  - `tool_result` -- replace spinner with `rich.panel.Panel` showing success/error summary
  - `usage_update` -- buffer token counts; display as one-line summary at turn end
  - `stop` -- finalize: re-render complete message with `rich.markdown.Markdown`; display stop reason if abnormal; show usage summary

**Tests**:
- `tests/cli/test_renderer.py`:
  - Construct mock `QueryEvent` instances for each type
  - Verify renderer produces expected Rich renderables (use `rich.console.Console(file=io.StringIO())` for capture)
  - Test `text_delta` streaming: 5 deltas followed by `stop` -> complete text is present in output
  - Test `tool_use` + `tool_result` pair: spinner starts and stops
  - Test `stop` with each `StopReason` variant: verify citizen-friendly messages (no stack traces)
  - Test Korean text rendering: verify no exceptions on Hangul content

**Completion gate**: All renderer tests pass. Each `StopReason` maps to a human-readable message.

### Phase 3 -- Permission Prompt Handler

**Goal**: Implement the consent prompt scaffold for citizen approval of tool execution. Wired to mock escalation in v1.

**Files**:
- `src/kosmos/cli/permissions.py` -- `ConsentPromptHandler`:
  - `prompt(tool_name: str, provider: str, description: str) -> bool` -- Rich-formatted consent display with `[Y/n]` prompt
  - Displays: tool name (Korean), provider, what data will be accessed
  - Default: approve (Enter = yes)
  - Bypass-immune denials: display denial reason without offering override

**Tests**:
- `tests/cli/test_permissions.py`:
  - Mock stdin to test approve (y, Y, Enter) and deny (n, N) paths
  - Verify output includes tool name and provider
  - Verify bypass-immune denial displays reason without prompt

**Completion gate**: Consent prompt tests pass. Handler integrates with `PermissionDecision.escalate`.

### Phase 4 -- REPL Loop

**Goal**: Implement the main interactive REPL loop that ties together prompt input, engine execution, event rendering, and interrupt handling.

**Files**:
- `src/kosmos/cli/repl.py` -- `REPLLoop` class:
  - Constructor: accepts `QueryEngine`, `ToolRegistry` (for display names), `Console`, `CLIConfig`
  - `async run()` -- main loop:
    1. Display welcome banner with session ID and version
    2. Prompt citizen input via `prompt_toolkit.PromptSession`
    3. Handle slash commands: `/help`, `/new`, `/exit`, `/usage`
    4. Skip empty/whitespace input
    5. Call `engine.run(user_input)` and render events via `EventRenderer`
    6. Repeat
  - Interrupt handling:
    - Single Ctrl+C during streaming -> cancel async generator (`aclose()`), append `[cancelled]`, re-prompt
    - Double Ctrl+C within 1 second -> `sys.exit(130)`
    - Ctrl+C at idle prompt -> clear input line, re-prompt
  - Session management:
    - `/new` -- create new `QueryEngine` instance, reset session ID
    - `/exit` (aliases: `exit`, `quit`) -- farewell message, `sys.exit(0)`
    - `/help` -- display available commands with descriptions
    - `/usage` -- display current `SessionBudget` snapshot

- `src/kosmos/cli/app.py` -- update `main()` to:
  1. Load `CLIConfig`
  2. Initialize `LLMClient`, `ToolRegistry`, `ToolExecutor`, `ContextBuilder`
  3. Register tool adapters (KOROAD, KMA)
  4. Create `QueryEngine`
  5. Launch `REPLLoop` via `asyncio.run()`

**Tests**:
- `tests/cli/test_repl.py`:
  - Mock `QueryEngine.run()` to yield predetermined event sequences
  - Test slash command routing: `/help` displays commands, `/exit` calls `sys.exit(0)`
  - Test empty input skipping
  - Test interrupt handling: mock signal delivery, verify generator cancellation
  - Test `/new` creates fresh engine instance
  - Test `/usage` displays budget snapshot

**Completion gate**: All REPL tests pass. `python -m kosmos.cli` starts and accepts input (manual verification with mock engine).

### Phase 5 -- Integration

**Goal**: Wire the CLI to the full backend stack and verify end-to-end conversation flow with mock LLM.

**Files**:
- `tests/cli/test_integration.py`:
  - Full integration test: mock LLM (via `respx`) + recorded tool fixtures -> complete Scenario 1 flow
  - Verify: welcome banner -> citizen question -> tool_use spinner -> tool_result panel -> streamed answer -> stop -> re-prompt
  - Verify: multi-turn conversation maintains context
  - Verify: error stop reasons display citizen-friendly messages
  - Verify: budget exhaustion displays appropriate message

- `src/kosmos/cli/app.py` -- finalize factory function:
  - `create_session()` -> constructs all dependencies and returns `REPLLoop`
  - Handle `ConfigurationError` from `LLMClient` with user-friendly message (e.g., "Set KOSMOS_FRIENDLI_TOKEN")

**Completion gate**: Integration test passes. Manual test of Scenario 1 with mock backend completes successfully.

### Phase 6 -- Quality

**Goal**: Ensure type safety, lint compliance, and test coverage meet project standards.

**Checks**:
- `uv run mypy src/kosmos/cli/` -- strict mode, no errors
- `uv run ruff check src/kosmos/cli/` -- no violations (note: T20 suppressed for CLI layer per `pyproject.toml`)
- `uv run ruff format --check src/kosmos/cli/` -- formatting compliant
- `uv run pytest tests/cli/ --cov=src/kosmos/cli --cov-report=term-missing` -- coverage >= 80%
- `uv run pytest` -- full test suite green (no regressions in engine, llm, tools, context, permissions)

**Completion gate**: All quality checks pass. No regressions in existing test suites.

---

## Reference Source Mapping

Every design decision traces to a concrete source in `docs/vision.md` Reference materials per Constitution Principle I.

| Decision | Source | Evidence |
|---|---|---|
| REPL loop: prompt -> engine.run() -> dispatch events -> render | Claude Agent SDK (async generator tool loop); `ChinaSiro/claude-code-sourcemap` (TUI REPL) | CLI consumes `QueryEngine.run() -> AsyncIterator[QueryEvent]` identically to how Claude Agent SDK consumers iterate the agent loop |
| Event renderer as pure dispatch on `QueryEvent.type` | `openedclaude/claude-reviews-claude` (rendering pipeline) | Renderer has no state machine; each event is rendered independently via match dispatch. Same pattern as Claude Code's message renderer. |
| Rich-based terminal rendering (spinners, panels, markdown, live display) | `vadimdemedes/ink` (adapted to Python via Rich); `google-gemini/gemini-cli` (component hierarchy) | Rich provides Python equivalents of Ink's rendering primitives: `Live` = streaming, `Status` = spinner, `Panel` = bordered result display, `Markdown` = markdown rendering |
| Consent prompt scaffold for permission escalation | Claude Agent SDK (permission types); `openedclaude/claude-reviews-claude` (permission model) | Y/n prompt gates tool execution. V1 treats `escalate` as `deny`; scaffold validates the UX for Phase 2 human-in-the-loop |
| Single Ctrl+C cancels turn, double Ctrl+C exits | `ultraworkers/claw-code` (runtime behavior); `google-gemini/gemini-cli` (interrupt handling) | Standard CLI interrupt pattern. `asyncio.CancelledError` propagation cancels the async generator cleanly. |
| CLI config via `pydantic-settings` with `KOSMOS_CLI_*` prefix | Existing `kosmos.llm.config.LLMClientConfig` pattern | Same pattern as LLM config; consistent across all KOSMOS configuration |
| Frozen Pydantic v2 models for CLI data types | Constitution Principle III; `pydantic/pydantic-ai` schema-driven pattern | `SlashCommand` uses `ConfigDict(frozen=True)`. No `Any` in I/O schemas. |
| `prompt-toolkit` for input with Korean IME support | `google-gemini/gemini-cli` (readline fallback for Korean input) | Phase A uses `prompt-toolkit` (Python's readline alternative) which handles CJK IME natively, avoiding the IME issues that plague Ink's `<TextInput>` |
| Tool display names from `ToolRegistry.lookup().name_ko` | `docs/vision.md` Layer 2 (tool registry, bilingual search hints) | Korean display name (`name_ko`) on each `GovAPITool` is the citizen-facing label used in spinner text |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rich `Live` display + `prompt-toolkit` input conflict on stdout | Medium | High | `Live` display is used only during engine turns (streaming). Prompt input is collected only when engine is idle. The two never overlap. If conflicts arise, fall back to simple `console.print()` without `Live`. |
| `prompt-toolkit` Korean IME issues on specific terminals | Low | Medium | `prompt-toolkit` handles IME composition natively on macOS and Linux. If issues arise, fall back to `input()` with `readline`. Test on iTerm2, Terminal.app, and standard Linux terminal. |
| `asyncio.CancelledError` not propagated cleanly through `QueryEngine.run()` | Medium | Medium | `QueryEngine.run()` wraps the `query()` generator in try/except; `CancelledError` is re-raised by default in Python 3.12+. Test with explicit cancellation in integration tests. If needed, add explicit `CancelledError` handling in `QueryEngine.run()` to yield `StopReason.cancelled`. |
| Cold start time exceeds 3 seconds (SC-A6) | Low | Low | Backend imports are lazy where possible. `LLMClient` does not make network calls until `complete()` / `stream()` is called. Tool adapter registration is in-memory. Profile with `time python -m kosmos.cli --help` in Phase 6. |
| Phase B (Ink TUI) requires rewriting rendering logic | Expected | Low | Phase A rendering is intentionally in a single `renderer.py` file. The rendering logic maps 1:1 to Ink components (spinner -> `<Spinner>`, panel -> `<Box>`, markdown -> `<Markdown>`). The mapping is documented but no code is shared between Phase A and Phase B. |
| `typer` version conflict: `pyproject.toml` lists `typer>=0.24.1` but spec says `>=0.12` | Low | Low | Both version constraints are satisfied by typer 0.24.1+. The `pyproject.toml` constraint is stricter and takes precedence. No change needed. |

---

## Non-Goals (Phase A)

These are explicitly out of scope. See spec.md Non-Goals section for full list.

1. **Ink + React TUI** -- Phase B, separate epic
2. **IPC / JSON-RPC bridge** -- Phase B
3. **Virtual scrolling** -- terminal native scroll buffer
4. **Double-buffered rendering** -- Rich default rendering
5. **Themes and color customization** -- hardcoded colors
6. **Session persistence to disk** -- in-memory only
7. **Streaming Markdown parser** -- buffer and re-render on `stop`
8. **Mouse interaction** -- keyboard only
9. **Multi-agent swarm UI** -- single engine only

---

## Success Criteria Mapping

| Criterion | Phase | Validation |
|---|---|---|
| SC-A1: Scenario 1 end-to-end (route safety) | Phase 5 | Integration test with mock LLM + recorded KOROAD/KMA fixtures |
| SC-A2: Streaming character-by-character output | Phase 2 | Renderer test: multiple `text_delta` events rendered incrementally |
| SC-A3: Ctrl+C cancels mid-turn within 1 second | Phase 4 | REPL test: mock engine running, signal delivered, generator cancelled |
| SC-A4: Error stop reasons display citizen-friendly messages | Phase 2 | Renderer test: each `StopReason` variant -> human-readable output |
| SC-A5: Korean text renders without alignment corruption | Phase 2 | Renderer test: Hangul content renders without exceptions; manual verification on 80-column terminal |
| SC-A6: CLI starts within 3 seconds | Phase 6 | Profiling in quality phase; `time python -m kosmos.cli --help` |

---

## Project Structure (final)

### Documentation

```
specs/011-cli-tui-interface/
+-- spec.md
+-- plan.md           # This file
+-- tasks.md          # /speckit-tasks output (not yet created)
```

### Source code layout

```
src/kosmos/cli/
+-- __init__.py
+-- __main__.py
+-- app.py
+-- config.py
+-- models.py
+-- repl.py
+-- renderer.py
+-- permissions.py

tests/cli/
+-- __init__.py
+-- test_config.py
+-- test_models.py
+-- test_renderer.py
+-- test_permissions.py
+-- test_repl.py
+-- test_integration.py
```

### Modified files

```
pyproject.toml        # Add prompt-toolkit>=3.0; add [project.scripts] entry
```
