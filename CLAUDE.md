# CLAUDE.md

This project's agent instructions live in [`AGENTS.md`](./AGENTS.md). Read that file first.

@AGENTS.md

## Claude Code-specific notes

- **Spec Kit skills**: The `/speckit-*` slash commands are installed under `.claude/skills/`. Use them for every non-trivial feature per the workflow in `AGENTS.md`.
- **Auto memory**: Auto-learned observations go into `MEMORY.md` (created on first write). Do not manually edit that file — it is maintained by Claude.
- **TodoWrite**: Use for in-session task tracking when executing `/speckit-implement`. Do not persist todos to disk.
- **Model**: Prefer Opus or Sonnet 4.5+ for spec authoring and planning. Haiku is acceptable for single-task implementation steps inside `/speckit-implement`.
