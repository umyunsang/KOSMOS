# Implementation Plan: LLM Swap-Surface — Strict CC Byte-Copy + Bounded Swap Migration

**Branch**: `2521-llm-swap-cc-rebuild` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2521-llm-swap-cc-rebuild/spec.md`

## Summary

Rebuild the 4-file LLM swap surface (`tui/src/services/api/claude.ts`, `tui/src/ipc/llmClient.ts`, `src/ummaya/llm/client.py`, `src/ummaya/ipc/stdio.py`) using strict CC byte-copy + bounded-swap methodology. Replace the prior audit-and-fix approach with: (Step A) byte-copy CC source for Procedure-A files, SHA-256 verified; (Step B) labeled swap commits in 4 categories only (`SWAP/llm-provider`, `SWAP/tool-domain`, `SWAP/anti-anthropic-1p`, `SWAP/identifier-rename`); (Step C) UMMAYA-only files cite CC analog references per handler; (Step D) reproducibility via `replay_rebuild.sh` + drift-prevention via `llm_swap_parity_audit.sh` CI gate.

Primary user-visible deliverable: K-EXAONE's `reasoning_content` channel renders as `∴ Thinking` in the live REPL view (currently silently dropped at `tui/src/ipc/llmClient.ts`). Primary systemic deliverable: any future swap-surface modification requires a labeled swap commit; silent feature drops become structurally impossible.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x (TUI layer, existing Spec 287 stack — no bump); Python 3.12+ (backend, existing baseline — no bump).

**Primary Dependencies**: All existing — `ink`, `react`, `@inkjs/ui`, `string-width`, `zod ^3.23` (TS side); `pydantic >= 2.13`, `pydantic-settings >= 2.0`, `httpx >= 0.27`, `opentelemetry-sdk`, `opentelemetry-semantic-conventions`, `pytest`, `pytest-asyncio` (Python side). **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR-012). One stdlib usage: `hashlib` for SHA-256 byte-copy verification.

**Storage**: N/A — in-memory only. Spec 026 prompt manifest SHA-256 already stored in `prompts/manifest.yaml`; rebuild keeps manifest in sync.

**Testing**: `bun test` for TUI (existing stack + new `ink-testing-library` Layer 1b assertion for `AssistantThinkingMessage` rendering); `uv run pytest` for backend (existing stack + new `tests/llm/test_reasoning_content_forwarding.py` + `tests/integration/test_thinking_channel_e2e.py`); new shell-based parity audit `scripts/llm_swap_parity_audit.sh` (POSIX bash + `sha256sum` + `git diff`).

**Target Platform**: macOS / Linux terminals (existing UMMAYA — Bun-supported).

**Project Type**: Web-app style — backend (Python over stdio JSONL IPC) + frontend (TUI Bun + Ink + React).

**Performance Goals**: First-token latency unchanged for `enable_thinking=false` path; with `enable_thinking=true` (new default) reasoning trace streams alongside content but does NOT block final-answer first-token. CC's streaming pattern is preserved byte-identical.

**Constraints**: AGENTS.md hard rules — no new runtime deps; fail-closed defaults; 100% Pydantic v2 strict typing (no `Any` in I/O schemas); `UMMAYA_`-prefixed env vars only; English source text (Korean only for domain data); never `--no-verify`; conventional commits.

**Scale/Scope**: 4 LLM-bridge files (~6000 lines combined). 1 Procedure-A (byte-copy + bounded swap, ~3419 lines from CC). 3 Procedure-B (UMMAYA-only Python + IPC adapter, behavior-mirror with citations). Approximately 50-80 swap commits expected across the 4 files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Justification |
|---|---|---|
| **I. Reference-Driven Development** | ✅ PASS | The methodology IS reference-driven by definition. Step A byte-copies from `.references/claude-code-sourcemap/restored-src/`. Every Step B/C diff cites CC reference lines. `parity-matrix.md` is the reference catalog. |
| **II. Fail-Closed Security** | ✅ PASS | No UMMAYA-invented permission classifications introduced or reintroduced. CC `<PermissionRequest>` pipeline preserved byte-identical via byte-copy. The just-applied `_ensure_tool_registry` fix preserves the existing fail-closed registry boot via `SystemExit(78)` on validation failure. |
| **III. Pydantic v2 Strict Typing** | ✅ PASS | `UmmayaThinkingDelta` already added to `tui/src/ipc/llmTypes.ts` extending the existing `UmmayaContentBlockDelta` discriminated union. New regression tests use Pydantic models for SSE simulation. No `Any` introduced. |
| **IV. Government API Compliance** | N/A | This Epic does not touch tool adapters. |
| **V. Policy Alignment** | N/A | Not a permission/policy feature. |
| **VI. Deferred Work Accountability** | ✅ PASS | 7 deferred items tracked in spec's "Deferred to Future Work" table, all marked NEEDS TRACKING for resolution by `/speckit-taskstoissues`. No "separate epic" / "future phase" prose without table entries. |

**Gate result**: PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/2521-llm-swap-cc-rebuild/
├── plan.md                    # This file
├── spec.md                    # Feature specification (revised methodology)
├── research.md                # Phase 0 — reference mapping + research findings
├── data-model.md              # Phase 1 — entities (CCSourceFile, UMMAYATargetFile, SwapCommit, ParityAuditOutcome)
├── quickstart.md              # Phase 1 — replay_rebuild.sh usage + parity audit invocation
├── parity-matrix.md           # Canonical per-file CC↔UMMAYA mapping (populated incrementally during /speckit-implement)
├── contracts/
│   └── parity-audit-cli.md    # CLI contract for scripts/llm_swap_parity_audit.sh
├── checklists/
│   └── requirements.md        # Spec-quality validation
├── scripts/
│   └── replay_rebuild.sh      # Phase 1 stub — replay byte-copy + swap commits
└── tasks.md                   # Phase 2 — generated by /speckit-tasks
```

### Source Code (repository root)

```text
# Backend Python (Procedure B — behavior-mirror with CC analog citations)
src/ummaya/
├── llm/
│   ├── client.py              # B-2: behavior-mirror CC services/api/claude.ts streaming, FriendliAI OpenAI SDK swap point
│   ├── config.py              # touched only for `enable_thinking=true` default justification (already applied 2026-05-01)
│   └── _cc_reference/         # READ-ONLY: CC source-of-truth excerpts cited by client.py docstrings
└── ipc/
    └── stdio.py               # B-3: behavior-mirror CC QueryEngine.ts agentic loop + IPC frame I/O

# TUI TypeScript / Bun (Procedure A + B)
tui/src/
├── services/api/
│   └── claude.ts              # A-1: Step A byte-copy from CC services/api/claude.ts + bounded swap commits
├── ipc/
│   ├── llmClient.ts           # B-1: UMMAYA-only IPC adapter; thin SDK-shim so claude.ts byte-copy stays valid
│   ├── llmTypes.ts            # UmmayaThinkingDelta added 2026-05-01 (preserved this Epic)
│   └── frames.generated.ts    # IPC schema (read-only; generated)
└── sdk-compat.ts              # UMMAYA Anthropic-SDK-shaped types (existing; consumed by claude.ts byte-copy)

# CC source-of-truth (read-only input)
.references/claude-code-sourcemap/restored-src/src/
├── services/api/
│   └── claude.ts              # 3419 lines — primary byte-copy source for tui/src/services/api/claude.ts
├── query.ts                   # agentic loop reference for stdio.py behavior-mirror
└── QueryEngine.ts             # streaming query engine reference

# Tests (new)
tests/
├── llm/
│   └── test_reasoning_content_forwarding.py   # FR-007 regression
└── integration/
    └── test_thinking_channel_e2e.py           # FR-009 end-to-end plumbing
tui/tests/ipc/
└── thinking-delta-render.test.tsx             # ink-testing-library Layer 1b — AssistantThinkingMessage renders

# Audit + replay
scripts/
└── llm_swap_parity_audit.sh   # FR-004 — CI gate; SHA + swap-category verification
```

**Structure Decision**: Web-app style with backend Python (`src/ummaya/`) + TUI Bun (`tui/src/`). The 4 in-scope files split 2-2 between backend and TUI. CC byte-copy targets live next to UMMAYA-only adapters in the TUI tree; backend Python files cite CC analogs via `_cc_reference/` markdown excerpts.

## Phase 0 Reference Mapping (per Constitution § I)

Each rebuild design decision maps to a concrete reference per the AGENTS.md hard rule "Phase 0 must consult `docs/vision.md § Reference materials`":

| Design Decision | Primary Reference | Secondary Reference |
|---|---|---|
| Byte-copy + bounded swap procedure | `docs/vision.md § Reference materials`: Claude Code sourcemap (ChinaSiro/claude-code-sourcemap) — UMMAYA's primary migration source | AGENTS.md `feedback_cc_source_migration_pattern` memory: "CC 소스맵 복사 → 마이그레이션. 새로 작성 X." |
| Streaming handler (text + thinking + tool_use channels) | CC `services/api/claude.ts:1980-2295` (content_block_start/delta/stop, message_start/delta/stop) | Anthropic SDK official docs (RawMessageStreamEvent shape) |
| Agentic loop (per-turn message_id, tool dispatch, role=tool injection) | CC `QueryEngine.ts` + `query.ts:120-410` (yieldMissingToolResultBlocks pattern) | AGENTS.md L1-A pillar (CC agentic loop preserved 1:1) |
| FriendliAI OpenAI-compatible SDK swap point | FriendliAI docs (verified 2026-05-01: `parallel_tool_calls`, `chat_template_kwargs.enable_thinking`) | OpenAI Agents SDK retry matrix (constitution § I Layer 6) |
| Anthropic-SDK-shaped types in UMMAYA | UMMAYA `tui/src/sdk-compat.ts` (already exposes Ummaya*-aliased SDK shapes) | Spec 1633 dead-code-friendli-migration audit |
| `<PermissionRequest>` byte-identical port | CC `tools/PermissionRequest/` (constitution § II) | Spec 1979 cc-source-scope-audit (1531 byte-identical files) |
| Spec 026 prompt SHA-256 boot guard | `prompts/manifest.yaml` + Spec 026 deliverable | Constitution § VI (deferred-work accountability extends to manifest drift) |
| Reasoning channel separation (`reasoning_content` → `thinking_delta`) | K-EXAONE-236B-A23B model card (HuggingFace) — `enable_thinking=True` default | FriendliAI vLLM `--reasoning-parser deepseek_v3` flag |
| `ink-testing-library` Layer 1b regression test | `docs/testing.md § Layer 1b` (added 2026-05-01) | `tui/tests/ink/renderer-double-buffer.test.tsx` (existing in-tree pattern) |

## Phase 1 Artifacts

The following files will be generated by this `/speckit-plan` invocation immediately after gate evaluation:

- `research.md` — Phase 0 research findings + reference mapping above + deferred-item validation
- `data-model.md` — entity schemas (CCSourceFile / UMMAYATargetFile / SwapCommit / ParityAuditOutcome / StreamEventChannel)
- `contracts/parity-audit-cli.md` — `scripts/llm_swap_parity_audit.sh` CLI contract: invocation form, exit codes, stdout/stderr formats
- `quickstart.md` — replay procedure + audit invocation + per-file rebuild walkthrough
- `parity-matrix.md` — empty per-file table skeletons (rows populated during `/speckit-implement`)
- `scripts/replay_rebuild.sh` — stub script that lists planned commands (replaced with real implementation during T0xx tasks)

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Step A byte-copy is destructive (overwrites current UMMAYA state) | Methodology requires byte-equivalence baseline before swap commits — silent drops only become structurally impossible if Step A is verifiable via SHA-256 | "Audit and patch in place" was tried (Spec 1633) and produced 30 cleanup-needed entries + 3 silent feature drops discovered 2026-05-01 |
| 4 explicit swap categories (vs. free-form swap commits) | Bounded categories enable the audit script to verify every diff hunk; free-form invites "swap creep" where unjustified diffs hide as legitimate-looking refactors | "Trust commit messages without categorical classification" allows post-hoc rationalization; categorical taxonomy is auditable |
| Step B retroactively labels existing 2026-05-01 fixes (`_ensure_tool_registry` register, `<turn_order>` prompt, `enable_thinking=true` default, partial `chunk.thinking` plumbing) | The fixes ARE legitimate swap modifications; without retroactive labeling they would appear as drift after byte-copy reverts to CC state | "Drop the fixes and start clean from CC" loses the user-visible thinking display + breaks empty_registry fix; not acceptable |
