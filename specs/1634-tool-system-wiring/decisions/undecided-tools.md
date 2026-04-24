# Undecided TUI Tools — Per-Tool Disposition (Epic #1634 T027a / FR-029)

**Date**: 2026-04-25
**Decision authority**: Spec 1634 /speckit-implement Phase 3 T027a
**Canonical reference**: docs/requirements/kosmos-migration-tree.md § L1-C C6

---

## Existence check

Two tools listed in FR-019 — `MonitorTool` and `WorkflowTool` — do not exist as
directories under `tui/src/tools/` in the current codebase. They were not ported
from CC 2.1.88 during P0 and have no code to evaluate. Their decisions are recorded
as `delete-in-followup` with the rationale that there is nothing to register and
nothing to defer; they are tracked under #1757 to confirm no stray import references
remain.

The `ScheduleCronTool` directory is the housing for three related tools:
`CronCreate`, `CronDelete`, and `CronList` (gated behind `feature('AGENT_TRIGGERS')`).
These are treated as a family below.

---

## Summary table

| Tool | Decision | Target | Rationale (one sentence) |
|---|---|---|---|
| TodoWriteTool | delete-in-followup | #1757 | Developer-session task-tracking mechanism with no citizen-facing utility; replaced by in-session LLM reasoning within the KOSMOS citizen harness. |
| ToolSearchTool | delete-in-followup | #1757 | Deferred-schema-loading mechanism for CC's large dev-tool surface; redundant once the closed 13-tool set eliminates the deferred-tool pattern entirely. |
| AskUserQuestionTool | defer-to-P4 | #1635 | Structured multi-choice UI interaction belongs to P4 UI L2; the TUI rendering contract (UI-B B.6 autocomplete + modal) must be designed before this tool can be citizen-safe. |
| SleepTool | delete-in-followup | #1757 | Designed for developer harnesses waiting on shell processes or prompt-cache expiry; no citizen workflow requires explicit harness sleep. |
| MonitorTool | delete-in-followup | #1757 | Tool directory does not exist in the codebase; no code to register, defer, or migrate. |
| WorkflowTool | delete-in-followup | #1757 | Tool directory does not exist in the codebase; no code to register, defer, or migrate. |
| CronCreate (ScheduleCronTool) | defer-to-P4 | #1635 | Citizen-facing scheduled reminders are a valid Phase-2 auxiliary (UI-E E area pattern), but the UI-D ministry-agent swarm design (#1635) must stabilize before cron scheduling is exposed as LLM-visible. |
| CronDelete (ScheduleCronTool) | defer-to-P4 | #1635 | Companion cancel tool to CronCreate; deferred with it as an inseparable pair. |
| CronList (ScheduleCronTool) | defer-to-P4 | #1635 | Companion list tool to CronCreate; deferred with it as an inseparable pair. |
| TaskCreateTool | defer-to-P4 | #1635 | Core to the UI-D ministry-agent swarm workflow (multi-agent task ledger); P3 wires `AgentTool` as `Task` primitive stub and P4 introduces the full swarm coordination surface. |
| TaskGetTool | defer-to-P4 | #1635 | Part of the agent-swarm task ledger alongside TaskCreate; deferred as an inseparable coordination family. |
| TaskListTool | defer-to-P4 | #1635 | Part of the agent-swarm task ledger alongside TaskCreate; deferred as an inseparable coordination family. |
| TaskStopTool | defer-to-P4 | #1635 | Terminates background tasks in the agent-swarm context; deferred with the rest of the Task-* family. |
| TaskUpdateTool | defer-to-P4 | #1635 | Mutates task state in the agent-swarm ledger; deferred with the Task-* family as an inseparable coordination unit. |
| TeamCreateTool | defer-to-P4 | #1635 | Creates the multi-agent team context defined by UI-D ministry-agent swarm design; P4 is the correct home for swarm coordination primitives. |
| TeamDeleteTool | defer-to-P4 | #1635 | Companion cleanup tool to TeamCreate; deferred with it as part of the swarm lifecycle pair. |

---

## Per-tool detail

### TodoWriteTool

- **Current behavior**: Maintains a developer in-session todo list (pending / in_progress / completed states) to help the LLM track multi-step coding work and signal progress to the developer user. Explicitly scoped to "coding session."
- **Citizen relevance**: None. Citizens interact with KOSMOS to query public services — they do not manage LLM-internal task lists. Progress tracking in the citizen harness is surfaced through the conversation transcript and `subscribe` handle status, not an internal todo ledger. The tool description is saturated with "coding" context that would confuse K-EXAONE about its citizen role.
- **Decision**: delete-in-followup
- **Target Epic**: #1757
- **Rationale**: Developer coding-session task tracker with no citizen-harness equivalent; removing it from `getAllBaseTools()` in P3 and its directory in the post-P3 cleanup epic (#1757) is the correct outcome.

---

### ToolSearchTool

- **Current behavior**: Loads full JSON Schema definitions for "deferred" tools on demand, allowing CC to ship a large dev-tool surface without bloating the initial context window. Contains a complex gate against `feature('KAIROS')` and GrowthBook flags.
- **Citizen relevance**: None. The KOSMOS closed-13 tool surface (FR-020) eliminates the deferred-tool pattern: all LLM-visible tools ship fully specified in the initial context. ToolSearchTool only makes sense when the tool count is large enough to require lazy schema loading, which the P3 closed set explicitly avoids.
- **Decision**: delete-in-followup
- **Target Epic**: #1757
- **Rationale**: Deferred-schema loading mechanism for a large CC dev-tool surface; structurally redundant with the closed 13-tool set that P3 establishes.

---

### AskUserQuestionTool

- **Current behavior**: Presents structured multiple-choice questions with optional visual previews (ASCII or HTML); supports single-select and multi-select. Used by the LLM to clarify ambiguity or gather preferences during execution.
- **Citizen relevance**: High in principle — citizens may need to choose between hospitals, permit types, or agency branches. However, the TUI rendering shape (UI-B B.6 slash-command autocomplete + modal, UI-C C.2 consent modal) must be finalized before a citizen-safe multiple-choice widget can be exposed. Premature registration risks the LLM surfacing raw JSON option arrays instead of a rendered picker.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Citizen utility is real, but the TUI rendering contract for interactive choice UI belongs to P4 UI L2; wiring without that contract produces a broken citizen UX.

---

### SleepTool

- **Current behavior**: Blocks the harness for a specified duration, intended for "wait for something" scenarios in developer workflows (shell process waits, prompt-cache expiry management, periodic `<tick>` check-ins).
- **Citizen relevance**: None. Citizens are not scheduling harness waits; they issue requests and receive responses. The `subscribe` primitive covers the conceptually related "wait for event" pattern in a citizen-appropriate form. The sleep mechanism references `<tick>` prompts and prompt-cache API cost optimization — internal harness details a citizen should never encounter.
- **Decision**: delete-in-followup
- **Target Epic**: #1757
- **Rationale**: Developer harness timing utility with no citizen use case; `subscribe` covers the "await event" pattern correctly.

---

### MonitorTool

- **Current behavior**: Directory `tui/src/tools/MonitorTool/` does not exist in the KOSMOS codebase. The tool was listed in FR-019 as undecided but was not ported from CC 2.1.88 during P0.
- **Citizen relevance**: Cannot evaluate — no code exists.
- **Decision**: delete-in-followup
- **Target Epic**: #1757
- **Rationale**: Tool directory is absent; #1757 should confirm no stray import references remain and close the item.

---

### WorkflowTool

- **Current behavior**: Directory `tui/src/tools/WorkflowTool/` does not exist in the KOSMOS codebase. Same situation as MonitorTool.
- **Citizen relevance**: Cannot evaluate — no code exists.
- **Decision**: delete-in-followup
- **Target Epic**: #1757
- **Rationale**: Tool directory is absent; #1757 should confirm no stray import references remain and close the item.

---

### CronCreate / CronDelete / CronList (ScheduleCronTool family)

- **Current behavior** (shared): Three tools gated behind `feature('AGENT_TRIGGERS')` and a GrowthBook kill switch. CronCreate schedules prompts at future times (one-shot or recurring cron); CronDelete cancels a scheduled job; CronList enumerates active jobs. Jobs are session-only or durable (persisted to `.claude/scheduled_tasks.json`).
- **Citizen relevance** (shared): Legitimate Phase-2 potential — a citizen might ask KOSMOS to remind them of a permit renewal deadline or send a daily traffic-hazard summary. However, the durable-cron path writes to `.claude/` (a CC-specific path that conflicts with the KOSMOS `~/.kosmos/memdir/` session convention) and the cron lifecycle must be scoped within the ministry-agent swarm design (UI-D). The tool description also references internal scheduler implementation details that should not be LLM-visible to citizens in this form.
- **Decision**: defer-to-P4 (all three)
- **Target Epic**: #1635
- **Rationale**: Citizen-schedulable reminders are a valid capability but belong in P4 UI-D ministry-agent context; the durable-cron path must be migrated from `.claude/` to `~/.kosmos/memdir/` and the tool descriptions must be rewritten for citizen-primary Korean context before these tools can be registered.

---

### TaskCreateTool

- **Current behavior**: Creates structured tasks in a shared task ledger for multi-agent swarm coordination. Designed for leader agents to decompose work and assign items to teammates.
- **Citizen relevance**: Not directly citizen-facing, but is the foundation of the UI-D ministry-agent swarm (where the KOSMOS coordinator spawns sub-agents per ministry). Needs the swarm design to stabilize in P4 before the task schema can be adapted to KOSMOS's `~/.kosmos/memdir/` storage and Korean-primary UX context.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Core to UI-D ministry-agent swarm coordination; P3's `AgentTool` → `Task` primitive stub is the correct P3 boundary, with full swarm task ledger landing in P4.

---

### TaskGetTool

- **Current behavior**: Retrieves a single task by ID from the shared ledger, including full description, status, and dependency graph (blockedBy / blocks).
- **Citizen relevance**: Internal swarm coordination tool; citizens never directly call TaskGet. Part of the Task-* coordination family.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Inseparable from the Task-* swarm coordination family; deferred with the rest.

---

### TaskListTool

- **Current behavior**: Returns a summary of all tasks in the shared ledger filtered by status, owner, and blockedBy state; includes teammate workflow instructions when swarms are enabled.
- **Citizen relevance**: Internal swarm coordination tool; citizens see task progress through the conversation transcript, not by calling TaskList directly.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Inseparable from the Task-* swarm coordination family; deferred with the rest.

---

### TaskStopTool

- **Current behavior**: Terminates a named background task by `task_id`; maintains backward compatibility with the deprecated `KillShell` alias. Checks that the task is in `running` state before stopping it.
- **Citizen relevance**: Relevant only when background tasks are running (which requires the swarm / cron infrastructure to be wired). Has no citizen utility until the Task-* family is registered in P4.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Depends on the background-task infrastructure introduced with the Task-* swarm family; deferred as a lifecycle companion.

---

### TaskUpdateTool

- **Current behavior**: Updates task status, subject, description, owner, dependencies, and metadata within the shared swarm task ledger. The primary mutation tool for the agent-swarm coordination loop.
- **Citizen relevance**: Internal swarm coordination tool used by sub-agents, not citizens. Core to the UI-D multi-agent workflow.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Inseparable from the Task-* swarm coordination family; deferred with the rest.

---

### TeamCreateTool

- **Current behavior**: Creates a named team with a 1:1 task list, writes a config.json to `~/.claude/teams/{name}/` and tasks directory to `~/.claude/tasks/{name}/`. Designed for the swarm lead to bootstrap multi-agent coordination.
- **Citizen relevance**: Foundational to the UI-D ministry-agent swarm (one team per multi-ministry request), but the storage path (`~/.claude/`) conflicts with KOSMOS's `~/.kosmos/memdir/` convention and the tool description is entirely developer-oriented. Must be migrated and rewritten before citizen-facing use.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Ministry-agent swarm bootstrap tool; storage path and UX must be migrated to KOSMOS conventions in P4 before this can be registered.

---

### TeamDeleteTool

- **Current behavior**: Removes a team's directory tree (`~/.claude/teams/` and `~/.claude/tasks/`) after all team members have shut down.
- **Citizen relevance**: Lifecycle cleanup companion to TeamCreate; same concerns apply.
- **Decision**: defer-to-P4
- **Target Epic**: #1635
- **Rationale**: Inseparable lifecycle companion to TeamCreate; deferred with it as a pair.

---

## Tools registered in getAllBaseTools() after P3

None of the 14 tools evaluated here are registered in `getAllBaseTools()` after P3 ships.
The P3 closed LLM-visible surface is exactly the 13 tools listed in
`specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 1`.

---

## Deferred tools — registration note

Tools decided as `defer-to-P4` are REMOVED from `getAllBaseTools()` in Epic #1634 P3
(they are not LLM-visible post-P3), but their directory and source code remain intact.
Re-registration in P4 (#1635) is an explicit action requiring a spec update, not a
silent default. Affected tools:

- AskUserQuestionTool → #1635 (UI-B/UI-C rendering contract required first)
- CronCreate, CronDelete, CronList → #1635 (storage path migration + Korean UX rewrite)
- TaskCreateTool, TaskGetTool, TaskListTool, TaskStopTool, TaskUpdateTool → #1635 (swarm coordination family)
- TeamCreateTool, TeamDeleteTool → #1635 (storage path migration required)

---

## Tools deleted in followup

Tools decided as `delete-in-followup` are tracked under #1757 (FR-013 residual harness
cleanup). For MonitorTool and WorkflowTool specifically, #1757 should verify there are
no stray import references before closing.

- TodoWriteTool → delete directory + verify zero importers
- ToolSearchTool → delete directory + verify `isDeferredTool` / `formatDeferredToolLine` helpers are no longer called from any retained path
- SleepTool → delete directory + verify zero importers
- MonitorTool → confirm directory absence + grep for any stray imports
- WorkflowTool → confirm directory absence + grep for any stray imports
