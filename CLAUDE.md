# CLAUDE.md

This project's agent instructions live in [`AGENTS.md`](./AGENTS.md). Read that file first.

@AGENTS.md

## Claude Code-specific notes

- **Spec Kit skills**: `/speckit-*` slash commands under `.claude/skills/`. Use for every non-trivial feature.
- **Auto memory**: Observations go to `MEMORY.md` (auto-maintained). Do not hand-edit.
- **Model**: Opus (Lead/planning), Sonnet (Teammates/implementation). `effortLevel: high`.
- **Agent Teams**: Enabled. At `/speckit-implement`, spawn Teammates (Sonnet) for parallel task execution. See `AGENTS.md § Agent Teams` for rules.
- **TodoWrite**: In-session task tracking only during `/speckit-implement`. Do not persist to disk.
