# KOSMOS Constitution

## Core Principles

### I. Reference-Driven Development

Every design decision MUST trace to a concrete reference source. All sources listed in `docs/vision.md § Reference materials` are valid, including open-source repos, official documentation, reconstructed architecture analyses, and leaked-source review documents.

**Primary migration source (project-wide)**: `.references/claude-code-sourcemap/restored-src/src/` — Claude Code 2.1.88, 1,884 .ts/.tsx files, research-use reconstruction from `@anthropic-ai/claude-code` v2.1.88 source map. Per AGENTS.md, KOSMOS migrates the Claude Code harness (tool loop, permission gauntlet, context assembly, TUI, and the related coordinator/commands/services/context layers) to the Korean public-service domain. Before authoring any new module at any layer, check restored-src for the corresponding construct first; only escalate to the secondary references below when restored-src does not cover the need (document the escalation in `research.md`). The rewrite boundary is narrow: `services/api/` (→ KOSMOS Python backend over stdio JSONL), `tools/*` (→ thin renderers over KOSMOS's 5-primitive surface), and net-new domain layers Claude Code does not have (Korean IME, public-API adapters, PIPA permission extensions, Spec 027 swarm mailbox). Files lifted from restored-src MUST carry a header citing the upstream path + version `2.1.88` + research-use notice; per-layer `NOTICE` declares Anthropic attribution.

**Mandatory reference mapping** — every `/speckit-plan` Phase 0 Research MUST read `docs/vision.md` and map each design decision to one of these sources:

| Layer | Primary reference | Secondary reference |
|---|---|---|
| Query Engine | Claude Agent SDK (async generator loop) | Claude Code reconstructed (tool loop internals) |
| Tool System | Pydantic AI (schema-driven registry) | Claude Agent SDK (tool definitions) |
| Permission Pipeline | OpenAI Agents SDK (guardrail pipeline) | Claude Code reconstructed (permission model) |
| Agent Swarms | AutoGen (AgentRuntime mailbox IPC) | Anthropic Cookbook (orchestrator-workers) |
| Context Assembly | Claude Code reconstructed (context assembly) | Anthropic docs (prompt caching) |
| Error Recovery | OpenAI Agents SDK (retry matrix) | Claude Agent SDK (error handling) |
| TUI | Ink + Gemini CLI (React terminal UI) | Claude Code reconstructed (TUI components) |

**Encouraged**: actively study reconstructed source repositories (`ChinaSiro/claude-code-sourcemap`), architecture review documents (`openedclaude/claude-reviews-claude`), and harness implementations (`ultraworkers/claw-code`) to understand internal patterns. Adapt patterns to KOSMOS's domain — do not copy line-for-line.

### II. Fail-Closed Security (NON-NEGOTIABLE)

Every tool adapter and API integration MUST default to the most restrictive setting:

- `requires_auth = True` (not False)
- `is_personal_data = True` (not False)
- `is_concurrency_safe = False` (not True)
- `cache_ttl_seconds = 0` (no caching by default)

New adapters created by contributors or agents cannot accidentally expose personal-data APIs as public. The only way to relax a default is an explicit, reviewed override.

Permission pipeline bypass-immune checks MUST NOT be overridable by any mode, including automation, admin, or testing shortcuts. These checks include: querying another citizen's records, accessing medical records without consent, and write actions without required identity verification.

### III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)

All tool inputs and outputs MUST use Pydantic v2 models. The `Any` type is forbidden in all I/O schemas. Every tool adapter MUST include:

- `input_schema`: Pydantic model for request parameters
- `output_schema`: Pydantic model for response data
- `search_hint`: bilingual Korean + English discovery keywords

### IV. Government API Compliance

- NEVER call live `data.go.kr` APIs from CI tests; use recorded fixtures only.
- Every adapter MUST track daily per-key quota via `rate_limit_per_minute` and `usage_tracker`.
- Happy-path AND error-path tests are required for every adapter.
- No hardcoded API keys; all credentials via `KOSMOS_`-prefixed environment variables.

### V. Policy Alignment

KOSMOS aligns with the Korea AI Action Plan (2026-2028), specifically:

- **Principle 8**: single conversational window for cross-ministry citizen services
- **Principle 9**: Open API and OpenMCP for public service integration
- **Principle 5**: no paper submission required; consent-based data access

The permission pipeline implements the Public AI Impact Assessment (과제 54) requirements: algorithmic bias prevention, explainability, personal data protection, and abuse prevention.

PIPA (Personal Information Protection Act, 개인정보보호법) governs all citizen data handling. Every data flow involving personal identifiers MUST pass through the 7-step permission gauntlet.

### VI. Deferred Work Accountability

Every scope exclusion or deferral MUST be explicitly tracked:

- All deferred items MUST appear in the spec's "Scope Boundaries & Deferred Items" section
- Each deferred item MUST reference a GitHub issue (Epic or Task) by the end of the speckit cycle
- `/speckit-analyze` MUST flag untracked deferrals as CRITICAL
- Free-text references to "separate epic", "future phase", or "v2" without a corresponding entry in the Deferred Items table are constitution violations
- `/speckit-taskstoissues` creates placeholder issues for any "NEEDS TRACKING" markers and back-fills the spec with the issue number

This prevents "ghost work" — deferred items that exist only in spec prose but have no tracking issue, leading to orphaned features that are never implemented.

## Development Standards

- Python 3.12+, stdlib `logging` only (no `print()` outside CLI layer)
- `uv` + `pyproject.toml` for dependency management (never `requirements.txt`)
- Conventional Commits; branches: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`
- `uv run pytest` before every commit; `@pytest.mark.live` for real API tests (skipped in CI)
- English source text only; Korean domain data is the sole exception

## Issue and Spec Workflow

- Initiative and Epic issues are created manually before any spec work.
- `/speckit-specify` is triggered by an existing Epic issue (label: `epic`).
- `/speckit-plan` Phase 0 Research MUST consult `docs/vision.md § Reference materials` for architectural patterns.
- `/speckit-analyze` MUST verify constitution compliance before implementation.
- Task issues are created ONLY via `/speckit-taskstoissues` from a reviewed `tasks.md`.
- After task issue creation, each task issue MUST be linked as a sub-issue of its parent Epic using the GitHub Sub-Issues API.
- PRs MUST include `Closes #N` referencing the Task issue number.

## Governance

This constitution supersedes individual spec decisions. Any spec conflicting with these principles is a blocker — open an issue before proceeding. Amendments require an ADR under `docs/adr/` and user approval.

**Version**: 1.1.1 | **Ratified**: 2026-04-12 | **Last Amended**: 2026-04-19
