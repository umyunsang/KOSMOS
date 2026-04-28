# AGENTS.md — KOSMOS

> Entry point for AI coding agents. Imported by `CLAUDE.md`. Keep under 120 lines. Long-form details live under `docs/`.

## What KOSMOS is

A conversational multi-agent platform that **migrates the Claude Code harness** (tool loop, permission gauntlet, context assembly, TUI) from the developer domain to the Korean public-service domain. It orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. Student portfolio project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

## **CORE THESIS — the unit of work**

**KOSMOS = CC-original harness + 2 swaps:** (a) LLM = K-EXAONE on FriendliAI; (b) tool surface = Korean public-service domain access. Everything else is byte-identical with `.references/claude-code-sourcemap/restored-src/`.

**KOSMOS is a browser substitute, not a protocol pioneer.** Anthropic Claude for Computer Use / OpenAI Operator / Google Project Mariner — but for Korean government domains, in Korean, on the citizen's behalf. Existing agency systems (hometax.go.kr, gov.kr, 간편인증, 모바일신분증, 공동/금융인증서) are **never asked to change**. The LLM navigates the same web/mobile UX that a citizen would use today.

**The unit of work is wrapping one agency's domain-access flow as one tool and registering it.** "Domain-access flow" is broad — it can be a REST API call (data.go.kr public datasets), a browser-automation sequence (hometax form fill via Playwright), or a mobile-companion handshake (KOMSCO 모바일신분증 push + biometric).

```
┌──────────────────────────────────────────────────────────────────┐
│  Each agency's API endpoint (KOROAD / KMA / HIRA / NMC / NFA /   │
│  MOHW / MFDS / 정부24 / CBS / data.go.kr / ...)                   │
│       │                                                           │
│       ▼                                                           │
│  Wrapped as a `GovAPITool` Pydantic adapter under                 │
│  src/kosmos/tools/<ministry>/<endpoint>.py                        │
│       │                                                           │
│       ▼                                                           │
│  Registered into ToolRegistry at boot via `register(reg, exec)`   │
│       │                                                           │
│       ▼                                                           │
│  LLM (K-EXAONE) discovers via BM25 + native function calling      │
│       │                                                           │
│       ▼                                                           │
│  Citizen gets a Korean-language response                          │
└──────────────────────────────────────────────────────────────────┘
```

- **Public REST API + we have the data.go.kr key** → wrap as **Live tool** (real HTTP call).
- **REST API exists but we have no credential** (학부생 권한 한계) → wrap as **Mock tool** (fixture replay, byte/shape-mirror per public spec).
- **No REST API (only web/mobile UX)** — 홈택스 신고, 정부24 민원 제출 등 → wrap as **browser-automation tool** (Playwright-driven) or **Mock tool** that mirrors the *web UX surface* (form fields, session cookies, 접수번호 shape). The citizen still does authentication on their phone (간편인증 push, 모바일신분증 biometric) — KOSMOS just drives the form filling and submission afterwards.
- **Live navigation requires production credentials we lack** → ship as **Mock** with `_mode: "mock"` + `_existing_system: true` + `_real_navigation_url` transparency fields. Live mode is a Phase 2 (post-graduation / partnership / startup).

**KOSMOS does not invent permission policy.** Each adapter cites the agency's own published policy via `real_classification_url`. Permission UX uses CC's canonical `<PermissionRequest>` pipeline — no KOSMOS-invented `permission_tier`, `pipa_class`, `auth_level`, `dontAsk` mode, or PIPA §15(2) `ConsentDecision` 4-tuple.

**Authority for this thesis:**
- `specs/1979-plugin-dx-tui-integration/domain-harness-design.md` — 16-domain research matrix, 5-point mock fidelity grade, citation URLs.
- `specs/1979-plugin-dx-tui-integration/cc-source-migration-plan.md` — file-by-file migration path from CC original.
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md` — delegation flow research; **§11 carries the corrected browser-substitute architecture** (the canonical interpretation; §5-§9 were a misread that has been superseded).

**Canonical sources** (cite all three in every spec and PR):
- `docs/vision.md` — thesis + six-layer design. Claude Code is the first reference for any unclear design decision.
- `docs/requirements/kosmos-migration-tree.md` — L1 pillars A/B/C · UI L2 decisions · brand · P0–P6 phase sequencing. **Approved 2026-04-24.**
- `.references/claude-code-sourcemap/restored-src/` — Claude Code 2.1.88 source-of-truth for byte-identical components (research-only, never modify).

## L1 pillars (canonical)

- **L1-A LLM Harness** — Single-fixed provider `FriendliAI Serverless + K-EXAONE` (`LGAI-EXAONE/EXAONE-4.0-32B`). CC agentic loop preserved 1:1 (byte-identical with CC restored-src). Native EXAONE function calling. `prompts/system_v1.md` + compaction + prompt cache. Sessions in `~/.kosmos/memdir/user/sessions/` JSONL. 4-tier OTEL, zero external egress.
- **L1-B Tool System** — Each Korean agency API wrapped as one `GovAPITool` adapter, registered into `ToolRegistry` at boot. **Live** when we have the data.go.kr key; **Mock** when we don't (fixture replay, byte/shape-mirror per public spec). **OPAQUE** domains (홈택스 신고, 정부24-submit, 모바일ID 발급, KEC/yessign 서명, mydata-live) are never wrapped — LLM hands off via `docs/scenarios/`. Discovery via BM25 + dense `lookup`. Permission UX uses CC `<PermissionRequest>` with adapter's `real_classification_url` citation; **no KOSMOS-invented permission classification**.
- **L1-C Main-Verb Abstraction** — Four reserved primitives (`lookup · submit · verify · subscribe`) with shared `PrimitiveInput/Output` envelope. System prompt exposes primitive signatures only; BM25 surfaces adapters dynamically. Each adapter declares its real-domain policy by citation, not invention.

## Execution phases

P0 Baseline Runnable (#1632 merged) → P1 Dead-code + P2 Anthropic→FriendliAI (#1633 in progress) → P3 Tool-system wiring → P4 UI L2 → P5 Plugin DX → P6 Docs + smoke. Phase sequencing is canonical; spec PRs cite their phase.

## Stack

**Backend**: Python 3.12+ · FriendliAI Serverless (OpenAI-compatible) for K-EXAONE · `httpx` (async) · `pydantic` v2 · `pytest` + `pytest-asyncio` · `uv` + `pyproject.toml` · Apache-2.0.
**TUI**: Ink (React for CLIs) + Bun · TypeScript. Ref: Gemini CLI (Apache-2.0) + Claude Code reconstructed architecture.
Stack changes require an ADR under `docs/adr/`.

## Hard rules (never violate)

- All source text in English. Korean domain data is the only exception.
- Env vars prefixed `KOSMOS_`. Never commit `.env` or `secrets/`.
- Stdlib `logging` only; no `print()` outside CLI output layer.
- Pydantic v2 for all tool I/O. Never `Any`.
- Never call live `data.go.kr` APIs from CI tests.
- Never add a dependency outside a spec-driven PR.
- Never `--force` push `main`, `--no-verify`, or bypass signing.
- Never create `requirements.txt`, `setup.py`, or `Pipfile`.
- Never commit a file larger than 1 MB without asking.
- Never introduce Go or Rust. TypeScript is allowed only for the TUI layer (Ink + Bun).

## Issue hierarchy

`Initiative` → `Epic` → `Task` (Sub-Issues API, not body mentions). Initiatives/Epics: manual. Tasks: ONLY from `/speckit-taskstoissues`. Labels: `initiative`, `epic`, `agent-ready`, `needs-spec`, `parallel-safe`, `blocked`, `size/{S,M,L}`, plus layer labels.

**Issue tracking = GraphQL only.** Any enumeration of open epics, dependency/sub-issue graph walks, state-transition checks, or tracking-driven recommendations MUST go through `gh api graphql` with explicit field selection of the Sub-Issues API v2 connections (`issue.subIssues` / `issue.parent`, plus `pageInfo.hasNextPage` pagination). Do NOT use `trackedIssues` / `trackedInIssues` — those are the legacy body-mention task-list connection and return empty for issues linked via the "Convert to sub-issue" UI or `addSubIssue` mutation. `gh issue list/view` and REST `repos/.../issues` drop pages, miss Sub-Issues API edges, and hide projectV2 status — they are allowed ONLY for human-readable one-off glances, never as the basis for a tracking claim.

## Spec-driven workflow

Non-trivial features use [GitHub Spec Kit](https://github.com/github/spec-kit):

1. Create/verify **Epic** issue (label: `epic`)
2. `/speckit-specify` → `specs/NNN-slug/spec.md` → human review
3. `/speckit-plan` → `plan.md` → **read `docs/vision.md § Reference materials`** → human review
4. `/speckit-tasks` → `tasks.md` → human review
5. `/speckit-analyze` → constitution compliance check
6. `/speckit-taskstoissues` → create Task issues → link as sub-issues of Epic
7. `/speckit-implement` → Agent Teams parallel execution
8. PR with `Closes #EPIC` only (not Task sub-issues) → monitor CI → close Task sub-issues after merge

Small fixes (typos, one-line bugs, docs-only) skip the cycle.

**Reference source rule**: Every `/speckit-plan` Phase 0 must consult `.specify/memory/constitution.md` and `docs/vision.md § Reference materials`. Map each design decision to a concrete reference.
**Task-to-issue rule**: Tasks ONLY from `/speckit-taskstoissues`. Link as sub-issues of Epic via `gh api`. Code: `docs/conventions.md § Task linking`.
**PR close rule**: `Closes #EPIC` only — never Task sub-issues (GitHub fails at 50+). Close sub-issues after merge. Code: `docs/conventions.md § PR closing`.

## Agent Teams

- Lead (Opus): planning, spec authoring, code review, synthesis.
- Teammates (Sonnet): implementation, tests, refactoring — spawned at `/speckit-implement`.
- 3+ independent tasks → parallel Agent Teams. 1-2 tasks → Lead solo.

| Role | Agent | Model |
|------|-------|-------|
| Architecture | Software Architect | Opus |
| Backend | Backend Architect | Sonnet |
| CLI/Frontend | Frontend Developer | Sonnet |
| Tests | API Tester | Sonnet |
| Code review | Code Reviewer | Opus |
| Security | Security Engineer | Sonnet |
| Docs | Technical Writer | Sonnet |

## Commits, branches, PRs

Conventional Commits. Branches: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`. PRs for code; direct `main` commits only for `docs:` / `chore:` touching no source. Full details: `docs/conventions.md`.

## Code review

After every push, read inline review comments left by **Codex** (`chatgpt-codex-connector[bot]`) on the PR and address them:

```bash
gh api repos/umyunsang/KOSMOS/pulls/<N>/comments \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'
```

Codex flags issues with severity badges (P1/P2/P3). Fix or defer each with a reply. Codex auto-reviews on every push — no manual trigger needed.

## New tool adapter — the canonical work unit

Wrap one agency API endpoint as one `GovAPITool` adapter. Reference: `src/kosmos/tools/koroad/koroad_accident_search.py`.

**Required**: Pydantic v2 I/O · fail-closed defaults · Korean + English `search_hint` · `llm_description` (Korean primary) · recorded fixture · happy-path + error-path test · no hardcoded keys · **`real_classification_url` citing the agency's own published policy** · `last_verified` ISO date.

**Forbidden in adapter metadata**: `pipa_class`, `auth_level`, `permission_tier`, `is_personal_data`, `dpa_reference`, `is_irreversible` — these were KOSMOS-invented classifications, removed in Spec 1979. Use `real_classification_url` instead.

**Decision tree** for any new agency API:
1. Is the API public on data.go.kr or the agency's dev portal? → **Live tool**.
2. Public spec exists but credentials require licence (마이데이터, 모바일ID 등)? → **Mock tool** with shape-mirror per spec PDF.
3. No public spec for the operation (홈택스 신고, 정부24 민원 제출, KEC/yessign 서명)? → **No tool**. Add `docs/scenarios/<domain>.md` so LLM can hand off the citizen.

Full checklist: `docs/tool-adapters.md`. External plugin contributors: `docs/plugins/quickstart.ko.md` + `docs/plugins/security-review.md` (PIPA §26 trustee acknowledgment SHA-256).

**External plugin contributors** (kosmos-plugin-store/`<repo>`): start at [`docs/plugins/quickstart.ko.md`](./docs/plugins/quickstart.ko.md). 50-item validation workflow (Q1-Q10) enforces all rules; PIPA §26 trustee acknowledgment SHA-256 must match canonical hash in [`docs/plugins/security-review.md`](./docs/plugins/security-review.md) when `processes_pii: true`.

## Testing
`uv run pytest` before every commit. Live-API tests marked `@pytest.mark.live`, skipped by default. Full guide: `docs/testing.md`.

## TUI verification (LLM-readable smoke)
"작동 확인" / "정상 동작" / "검증" requests on TUI changes MUST run interactively under PTY — never code-grep alone (memory `feedback_runtime_verification`). Use a layered approach: (1) **stdio JSONL probe** bypasses the TUI for backend baseline, (2) **expect/script/asciinema** captures the full pty session as a text log LLMs can grep (memory `feedback_vhs_tui_smoke`), (3) **vhs `.tape`** produces the gif/mp4 for human visual review only (binary, not LLM-readable). Mismatches between layers identify which layer regressed. Full methodology + recipes: [`docs/testing.md § TUI verification methodology`](./docs/testing.md#tui-verification-methodology).

## Do not touch
`.specify/`, `.claude/skills/` (Spec Kit) · `LICENSE` (Apache-2.0, ADR required) · `docs/vision.md` layer names (ADR required) · `.env`, `secrets/` (never commit).

## Conflict resolution
Rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. When stuck, open a GitHub Discussion rather than guessing.
