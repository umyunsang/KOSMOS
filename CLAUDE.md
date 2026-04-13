# CLAUDE.md

This project's agent instructions live in [`AGENTS.md`](./AGENTS.md). Read that file first.

@AGENTS.md

## Claude Code-specific notes

- **Spec Kit skills**: `/speckit-*` slash commands under `.claude/skills/`. Use for every non-trivial feature.
- **Auto memory**: Observations go to `MEMORY.md` (auto-maintained). Do not hand-edit.
- **Model**: Opus (Lead/planning), Sonnet (Teammates/implementation). `effortLevel: high`.
- **Agent Teams**: Enabled. At `/speckit-implement`, spawn Teammates (Sonnet) for parallel task execution. See `AGENTS.md § Agent Teams` for rules.
- **TodoWrite**: In-session task tracking only during `/speckit-implement`. Do not persist to disk.

## Active Technologies
- Python 3.12+ + httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config) (spec/wave-1)
- N/A (in-memory session state only) (spec/wave-1)
- Python 3.12+ + pydantic >=2.0 (models + validation) (spec/wave-1)
- N/A (in-memory registry) (spec/wave-1)
- Python 3.12+ + pytest, pytest-asyncio, httpx (mock targets), pydantic v2 (existing) (013-scenario1-e2e-route-safety)
- N/A (in-memory test state only) (013-scenario1-e2e-route-safety)
- Python 3.12+ + httpx >=0.27, pydantic >=2.0, pydantic-settings >=2.0 (014-phase1-live-validation)

## Recent Changes
- spec/wave-1: Added Python 3.12+ + httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config)
