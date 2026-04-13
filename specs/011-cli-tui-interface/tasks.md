# Tasks: CLI & TUI Interface (Phase A — Python Rapid Prototype)

**Input**: `specs/011-cli-tui-interface/` (spec.md, plan.md)
**Epic**: #11 — CLI & TUI Interface (Ink + React)
**Branch**: `feat/011-cli-tui-interface`

---

## Phase 1: Setup (Package Structure + Dependencies)

**Purpose**: Create the `src/kosmos/cli/` sub-package and `tests/cli/` directory,
add `prompt-toolkit` to dependencies, and establish shared test fixtures.
No source code yet — just the file system skeleton and dependency wiring.

- [ ] T001 [P] Create `src/kosmos/cli/__init__.py` with empty public export list and `src/kosmos/cli/py.typed` marker
  - Labels: `parallel-safe`, `size/S`
- [ ] T002 [P] Create `tests/cli/__init__.py` and `tests/cli/conftest.py` with shared fixtures (mock `QueryEngine`, mock `Console`, mock `ToolRegistry` with `lookup()` returning a tool with `name_ko`)
  - Labels: `parallel-safe`, `size/S`
- [ ] T003 Add `prompt-toolkit>=3.0` to `pyproject.toml` dependencies and add `[project.scripts]` entry `kosmos = "kosmos.cli.app:main"`
  - Labels: `size/S`

**Completion gate**: `src/kosmos/cli/` and `tests/cli/` exist as importable packages. `uv sync` succeeds with the new dependency. `uv run python -c "import kosmos.cli"` works.

---

## Phase 2: Config + Models

**Purpose**: Lay down CLIConfig (pydantic-settings) and SlashCommand (frozen Pydantic v2 model).
Every later phase depends on these types being present and correct.

- [ ] T004 Implement `CLIConfig` via pydantic-settings with `KOSMOS_CLI_*` prefixed env vars (`history_size: int = 1000`, `show_usage: bool = True`, `welcome_banner: bool = True`) in `src/kosmos/cli/config.py`
  - Labels: `size/S`
- [ ] T005 Implement `SlashCommand` frozen Pydantic v2 model with `name: str`, `description: str`, `aliases: tuple[str, ...] = ()` and `COMMANDS` registry dict mapping command names to `SlashCommand` instances (`/help`, `/new`, `/exit`, `/usage`) in `src/kosmos/cli/models.py`
  - Labels: `size/S`
- [ ] T006 [P] Write unit tests for `CLIConfig`: validate defaults, env var override via monkeypatch, `extra="ignore"` behavior in `tests/cli/test_config.py`
  - Labels: `parallel-safe`, `size/S`
- [ ] T007 [P] Write unit tests for `SlashCommand`: frozen constraint (assignment raises), construction, aliases lookup, `COMMANDS` registry completeness in `tests/cli/test_models.py`
  - Labels: `parallel-safe`, `size/S`

**Completion gate**: `uv run pytest tests/cli/test_config.py tests/cli/test_models.py` passes. `CLIConfig()` loads defaults without env vars set.

---

## Phase 3: Event Renderer

**Purpose**: Implement the Rich-based event rendering pipeline that converts `QueryEvent`
instances into terminal output. This is the core display module and the most complex
single file in the CLI package.

- [ ] T008 Implement `EventRenderer` class with `render(event: QueryEvent, console: Console) -> None` dispatch method and private `_render_text_delta()` handler that appends text to a buffer and prints raw text during streaming in `src/kosmos/cli/renderer.py`
  - Labels: `size/M`
- [ ] T009 Implement `_render_tool_use()` handler: display `rich.status.Status` spinner with tool's Korean name (`name_ko` from `ToolRegistry.lookup()`) and `_render_tool_result()` handler: replace spinner with `rich.panel.Panel` showing success/error summary in `src/kosmos/cli/renderer.py`
  - Labels: `size/M`
- [ ] T010 Implement `_render_usage_update()` handler: buffer token counts for turn-end summary, and `_render_stop()` handler: re-render complete message with `rich.markdown.Markdown`, display citizen-friendly stop reason messages for each `StopReason` variant, show usage summary in `src/kosmos/cli/renderer.py`
  - Labels: `size/M`
- [ ] T011 [P] Write unit tests for `EventRenderer`: construct mock `QueryEvent` instances for each type, verify renderer produces expected output using `Console(file=io.StringIO())` for capture — test `text_delta` streaming (5 deltas + stop = complete text), `tool_use` + `tool_result` pair, each `StopReason` variant maps to human-readable message, Korean text renders without exceptions in `tests/cli/test_renderer.py`
  - Labels: `parallel-safe`, `size/M`

**Completion gate**: All renderer tests pass. Each `StopReason` maps to a citizen-friendly message (no stack traces). `text_delta` streaming produces incremental output.

---

## Phase 4: Permission Prompt Handler

**Purpose**: Implement the consent prompt scaffold for citizen approval of tool execution.
Wired to mock escalation path in v1 (permission pipeline treats `escalate` as `deny`).

- [ ] T012 Implement `ConsentPromptHandler` with `prompt(tool_name: str, provider: str, description: str) -> bool` using `rich.prompt.Confirm` for Y/n interaction, and `display_denial(tool_name: str, reason: str) -> None` for bypass-immune denials in `src/kosmos/cli/permissions.py`
  - Labels: `size/S`
- [ ] T013 [P] Write unit tests for `ConsentPromptHandler`: mock stdin to test approve (y, Y, Enter default) and deny (n, N) paths, verify output includes tool name and provider, verify `display_denial()` shows reason without offering override in `tests/cli/test_permissions.py`
  - Labels: `parallel-safe`, `size/S`

**Completion gate**: Consent prompt tests pass. Handler correctly returns `True`/`False` based on citizen input.

---

## Phase 5: REPL Loop

**Purpose**: Implement the main interactive REPL loop that ties together prompt input,
engine execution, event rendering, and interrupt handling. This is the orchestrator
that connects all other modules.

- [ ] T014 Implement `REPLLoop` class skeleton in `src/kosmos/cli/repl.py`: constructor accepting `QueryEngine`, `ToolRegistry`, `Console`, `CLIConfig`, `EventRenderer`; `async run()` method with welcome banner display (session ID, version) and main prompt loop via `prompt_toolkit.PromptSession`
  - Labels: `size/M`
- [ ] T015 Implement slash command routing in `REPLLoop`: `/help` displays available commands with descriptions, `/exit` (aliases: `exit`, `quit`) prints farewell and calls `sys.exit(0)`, `/new` creates fresh `QueryEngine` instance with new session ID, `/usage` displays current `SessionBudget` snapshot; skip empty/whitespace input in `src/kosmos/cli/repl.py`
  - Labels: `size/M`
- [ ] T016 Implement interrupt handling in `REPLLoop`: single Ctrl+C during streaming cancels async generator via `aclose()` and appends `[cancelled]` indicator, double Ctrl+C within 1 second calls `sys.exit(130)`, Ctrl+C at idle prompt clears input and re-prompts in `src/kosmos/cli/repl.py`
  - Labels: `size/M`
- [ ] T017 [P] Write unit tests for `REPLLoop`: mock `QueryEngine.run()` to yield predetermined event sequences, test slash command routing (`/help` output, `/exit` calls `sys.exit`), test empty input skipping, test `/new` creates fresh engine, test `/usage` displays budget, test interrupt handling with mock signal delivery verifying generator cancellation in `tests/cli/test_repl.py`
  - Labels: `parallel-safe`, `size/L`

**Completion gate**: All REPL tests pass. `REPLLoop` correctly dispatches slash commands and renders engine events.

---

## Phase 6: Entry Point + Integration

**Purpose**: Wire the CLI to the full backend stack via `__main__.py` and `app.py`,
then verify end-to-end conversation flow with mock LLM.

- [ ] T018 Implement `src/kosmos/cli/__main__.py` with `python -m kosmos.cli` entry point that calls `main()` from `app.py`
  - Labels: `size/S`
- [ ] T019 Implement `main()` in `src/kosmos/cli/app.py`: typer app with `--version` flag, load `CLIConfig`, initialize `LLMClient`, `ToolRegistry`, `ToolExecutor`, `ContextBuilder`, `PermissionPipeline`, register tool adapters, create `QueryEngine`, launch `REPLLoop` via `asyncio.run()`; handle `ConfigurationError` with user-friendly message (e.g., "Set KOSMOS_FRIENDLI_TOKEN")
  - Labels: `size/M`
- [ ] T020 Update `src/kosmos/cli/__init__.py` to export `CLIConfig`, `EventRenderer`, `REPLLoop`, `ConsentPromptHandler`, `create_app` (if applicable)
  - Labels: `size/S`
- [ ] T021 [P] Write integration test in `tests/cli/test_integration.py`: mock LLM (via `respx`) + recorded tool fixtures -> complete Scenario 1 flow; verify welcome banner -> citizen question -> `tool_use` spinner -> `tool_result` panel -> streamed answer -> stop -> re-prompt; verify multi-turn conversation maintains context; verify error stop reasons display citizen-friendly messages; verify budget exhaustion displays appropriate message
  - Labels: `parallel-safe`, `size/L`
- [ ] T022 [P] Write manual test checklist as comments in `tests/cli/test_integration.py`: launch `python -m kosmos.cli`, verify welcome banner within 3 seconds, type question, observe streaming, press Ctrl+C mid-turn, verify `/help`, `/new`, `/exit` commands
  - Labels: `parallel-safe`, `size/S`

**Completion gate**: Integration test passes. `python -m kosmos.cli --help` works. `python -m kosmos.cli --version` prints version.

---

## Phase 7: Quality

**Purpose**: Ensure type safety, lint compliance, and test coverage meet project standards.
No new functionality — quality gates only.

- [ ] T023 [P] Run `uv run mypy src/kosmos/cli/` strict mode — fix all type errors
  - Labels: `parallel-safe`, `size/S`
- [ ] T024 [P] Run `uv run ruff check src/kosmos/cli/` and `uv run ruff format --check src/kosmos/cli/` — fix all violations (T20 suppressed per `pyproject.toml` per-file-ignores)
  - Labels: `parallel-safe`, `size/S`
- [ ] T025 [P] Run `uv run pytest tests/cli/ --cov=src/kosmos/cli --cov-report=term-missing` — verify coverage >= 80%; identify and fill gaps if below threshold
  - Labels: `parallel-safe`, `size/S`
- [ ] T026 Run `uv run pytest` (full test suite) — verify no regressions in engine, llm, tools, context, permissions test suites
  - Labels: `size/S`

**Completion gate**: All quality checks pass. `mypy` strict clean. `ruff` clean. Coverage >= 80%. Full test suite green (no regressions).

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Config + Models) ← blocks everything below
            ├── Phase 3 (Event Renderer)
            │       └── Phase 5 (REPL Loop)        ← depends on renderer
            ├── Phase 4 (Permission Prompt)
            │       └── Phase 5 (REPL Loop)        ← depends on permissions
            └── Phase 5 (REPL Loop)                ← depends on models, renderer, permissions
                    └── Phase 6 (Entry Point)      ← depends on REPL loop
                            └── Phase 7 (Quality)  ← depends on all code complete
```

### Within-Phase Parallelism

Tasks marked `[P]` within the same phase touch different files and can run simultaneously:

- **Phase 1**: T001 and T002 are independent directories — parallel
- **Phase 2**: T006 and T007 are both test files — parallel with T004–T005 implementation
- **Phase 3**: T011 test file is parallel with T008–T010 implementation (once implementation complete)
- **Phase 4**: T013 test file is parallel with T012 implementation
- **Phase 5**: T017 test file is parallel with T014–T016 implementation (once implementation complete)
- **Phase 6**: T021, T022 are parallel with each other (different concerns in same file)
- **Phase 7**: T023, T024, T025 are all parallel (independent quality checks)

### Cross-Phase Parallelism

Once Phase 2 is complete, Phase 3 (Event Renderer) and Phase 4 (Permission Prompt)
can start in parallel — they touch different files (`renderer.py` vs `permissions.py`).
Phase 5 (REPL Loop) must wait for both Phase 3 and Phase 4 to complete because the
REPL loop imports and orchestrates both the renderer and the permission handler.

---

## Task Count Summary

| Phase | Tasks | Parallel-eligible | Files touched |
|-------|-------|-------------------|---------------|
| Phase 1: Setup | 3 | 2 | `__init__.py`, `conftest.py`, `pyproject.toml` |
| Phase 2: Config + Models | 4 | 2 | `config.py`, `models.py`, `test_config.py`, `test_models.py` |
| Phase 3: Event Renderer | 4 | 1 | `renderer.py`, `test_renderer.py` |
| Phase 4: Permission Prompt | 2 | 1 | `permissions.py`, `test_permissions.py` |
| Phase 5: REPL Loop | 4 | 1 | `repl.py`, `test_repl.py` |
| Phase 6: Entry Point | 5 | 2 | `__main__.py`, `app.py`, `__init__.py`, `test_integration.py` |
| Phase 7: Quality | 4 | 3 | All `src/kosmos/cli/` and `tests/cli/` files |
| **Total** | **26** | **12** | — |

- **Total tasks**: 26
- **Parallel-eligible**: 12 (marked `[P]`)
- **Sequential-only**: 14
- **New source files**: 7 (`cli/__init__.py`, `__main__.py`, `app.py`, `config.py`, `models.py`, `repl.py`, `renderer.py`, `permissions.py`)
- **Modified files**: 1 (`pyproject.toml`)
- **New test files**: 7 (`tests/cli/__init__.py`, `conftest.py`, `test_config.py`, `test_models.py`, `test_renderer.py`, `test_permissions.py`, `test_repl.py`, `test_integration.py`)
