# Feature Specification: LLM Swap-Surface — Strict CC Byte-Copy + Bounded Swap Migration

**Feature Branch**: `2521-llm-swap-cc-rebuild`
**Created**: 2026-05-01
**Status**: Draft
**Input**: User directive 2026-05-01: "**모든 CC 원본 소스를 그대로 가져와서 일부 수정 + 일부 마이그레이션 으로 방식을 바꿔**" — replaces the prior audit-and-fix plan with strict byte-copy-first methodology aligned with AGENTS.md CORE THESIS ("KOSAX = CC-original harness + 2 swaps") and memory `feedback_cc_source_migration_pattern` ("CC 소스맵 복사 → 마이그레이션. 새로 작성 X").

## Methodology — what makes this Epic different

The prior approach was *audit-and-fix*: read current KOSAX state, find drift, patch. That approach repeatedly missed silent feature drops (3 found 2026-05-01). This Epic enforces a stricter procedure:

1. **Step A — Byte-copy phase**: For each in-scope file with a CC reference, the rebuild's *first* commit OVERWRITES the KOSAX file with the byte-identical CC source from `.references/claude-code-sourcemap/restored-src/`. This commit's diff is a pure CC byte-copy; SHA-256 of the resulting file MUST equal SHA-256 of the CC source.

2. **Step B — Bounded swap phase**: Subsequent commits apply *named, line-cited* swap modifications. Each swap commit's diff hunks are categorized:
   - **`SWAP/llm-provider`** — replaces an Anthropic SDK call site with a KOSAX IPC bridge call. Justification: AGENTS.md L1-A pillar "Single-fixed provider FriendliAI Serverless + K-EXAONE".
   - **`SWAP/tool-domain`** — replaces a CC dev-tool reference with a KOSAX public-API primitive reference. Justification: AGENTS.md L1-B pillar "Korean public-service tool surface".
   - **`SWAP/anti-anthropic-1p`** — removes claude.ai-specific 1P features (billing, OAuth, sync). Justification: AGENTS.md `feedback_kosax_scope_cc_plus_two_swaps` ("claude.ai 결제·sync·1P 텔레메트리만 제거 가능").
   - **`SWAP/identifier-rename`** — KOSAX / EXAONE / FriendliAI brand tokens replacing Claude / Anthropic / claude.ai. Justification: brand parity already audited in Spec 2292.
   - Any diff hunk that does NOT fit one of these four categories is by definition **drift** and MUST be reverted.

3. **Step C — KOSAX-only file behavior-mirror phase**: For files with NO direct CC source path (KOSAX-only adapter / backend Python files), Step A is replaced with a structural template derived from the closest CC analog. The file's runtime behavior MUST mirror the CC analog channel-for-channel; deliverable cites the CC analog's line ranges per handler.

4. **Step D — Parity audit reproducibility**: A new `scripts/llm_swap_parity_audit.sh` MUST verify Step A is reproducible — running the byte-copy procedure on a fresh checkout MUST produce identical SHA-256s. The audit also enumerates every Step B diff hunk and verifies each carries one of the four allowed swap categories.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen sees model reasoning live (Priority: P1)

The citizen runs `bun run tui`, asks "오늘 부산 날씨 어때?", and observes the model's reasoning steps surface in the terminal as `∴ Thinking` dim-italic lines BEFORE each tool call. After this Epic, the rendering chain is byte-equivalent to CC's because the streaming-handler portion of `tui/src/services/api/claude.ts` is byte-copied from CC.

**Why this priority**: Primary citizen-visible regression that triggered this Epic. Before fix: tool calls appear back-to-back with no thinking indicator despite K-EXAONE emitting 1098-byte reasoning trace per turn (verified by `probe_friendli_channels.py` 2026-05-01).

**Independent Test**: Run `bun run tui` → ask any tool-requiring question → assert ≥1 `∴ Thinking` line renders in live REPL view (Layer 3 PTY) AND a `thinking` content block exists on the assistant message (Layer 1b Ink snapshot via `ink-testing-library` `frames[]`).

**Acceptance Scenarios**:

1. **Given** `enable_thinking=true` (default per Spec 2521), **When** citizen sends a prompt requiring tool use, **Then** the TUI renders `∴ Thinking` line(s) before/between tool call rows
2. **Given** the streaming-handler in `tui/src/services/api/claude.ts` after this Epic, **When** the file is `diff`'d against CC's `services/api/claude.ts`, **Then** every diff hunk falls into one of the four allowed swap categories (`SWAP/llm-provider`, `SWAP/tool-domain`, `SWAP/anti-anthropic-1p`, `SWAP/identifier-rename`)
3. **Given** `KOSAX_K_EXAONE_THINKING=false`, **When** citizen sends a prompt, **Then** no thinking_delta frames arrive and no `∴ Thinking` renders (latency-optimized escape hatch preserved)

---

### User Story 2 — Every line of difference between KOSAX and CC is documented and justified (Priority: P1)

A future maintainer or reviewer can run `git diff` between any rebuilt file and its CC source, and every diff hunk has an associated commit message starting with `swap/<category>:` plus a CC reference line citation. NO unjustified drift exists. NO third-category diff (neither byte-copy nor a labeled swap) is permitted.

**Why this priority**: This is the systemic-prevention requirement that justifies the Epic vs. patching individual bugs. Without enforced byte-copy-first methodology, KOSAX keeps accruing silent drops at the swap-surface boundary.

**Independent Test**: `scripts/llm_swap_parity_audit.sh` enumerates every diff hunk between each rebuilt file and its CC source. Each hunk MUST be reachable from a `swap/<category>:` commit. Mismatches → exit 1 + diagnostic.

**Acceptance Scenarios**:

1. **Given** a fresh checkout, **When** `git log --oneline specs/2521-llm-swap-cc-rebuild/...` is read, **Then** the first rebuild commit per file is `byte-copy(2521): import CC services/api/claude.ts byte-identical` and the SHA-256 matches CC source
2. **Given** the parity audit script, **When** it runs on the rebuilt branch, **Then** exit code 0 and stdout shows: per file, byte-copy SHA match + every subsequent diff hunk classified swap-justified
3. **Given** a future PR introduces a non-swap diff, **When** the parity audit runs, **Then** exit code 1 + diagnostic naming the unjustified hunk
4. **Given** the audit baseline (Spec 2292), **When** the rebuild merges, **Then** the cleanup-needed entries that originate in the 4 in-scope files are resolved by either revert-to-CC-byte-identical or labeled swap

---

### User Story 3 — Rebuild procedure is reproducible from CC source-of-truth (Priority: P2)

A maintainer on a fresh clone can re-run the rebuild procedure (Step A byte-copy + Step B swap commits replayed) and produce the identical post-rebuild state. The procedure is documented as a script under `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh` for auditability.

**Why this priority**: Reproducibility is what distinguishes "byte-copy + swap" from "audit and patch". If the procedure can't be replayed, byte-copy was just a one-time event that decays into drift.

**Independent Test**: The replay script executed on a clean main branch produces a working tree byte-identical to the rebuild branch's working tree.

**Acceptance Scenarios**:

1. **Given** clean main + the replay script, **When** executed, **Then** working tree matches the rebuild branch byte-for-byte
2. **Given** an updated CC source-of-truth in a future `.references/claude-code-sourcemap/restored-src/` refresh, **When** the replay script is re-run, **Then** the rebuild auto-pulls new CC content + flags any swap commits that no longer apply cleanly (so KOSAX knows when to re-justify)

---

### User Story 4 — Spec 1633 dead-Anthropic cleanup is closed (Priority: P3)

Spec 1633 left 30 `cleanup-needed` entries in `specs/2292-cc-parity-audit/cc-parity-audit.md`. This Epic resolves each entry that falls within the 4 in-scope files via the strict byte-copy + swap procedure. Out-of-scope cleanup-needed entries get a tracking issue and stay deferred.

**Why this priority**: Bounded tail-end work. Doesn't gate the citizen-visible thinking fix.

**Independent Test**: `cleanup-needed` count for the 4 in-scope files drops from N to 0; remaining entries (in other files) get NEEDS-TRACKING follow-ups.

**Acceptance Scenarios**:

1. **Given** the audit baseline, **When** rebuild merges, **Then** cleanup-needed entries in the 4 in-scope files = 0

---

### Edge Cases

- **CC source contains Anthropic OAuth code that KOSAX doesn't use**: byte-copy keeps the OAuth code as-is (it's dead in KOSAX but byte-identical with CC, so no drift). Runtime behavior diverges only at the LLM-provider swap point.
- **CC source imports `@anthropic-ai/sdk`**: this is a `SWAP/llm-provider` swap point. The KOSAX-side replacement is the IPC bridge in `tui/src/ipc/llmClient.ts` exposing an Anthropic-SDK-shaped interface (already exists in `tui/src/sdk-compat.ts` Kosax*-aliased types).
- **CC's `services/api/claude.ts` references `claude-3-5-sonnet` etc. model IDs**: this is `SWAP/identifier-rename` — replace with `LGAI-EXAONE/K-EXAONE-236B-A23B`. Each rename is a one-line diff with citation.
- **Streaming handler emits `signature_delta` (Anthropic-only thinking signature)**: byte-copy preserves the handler. Runtime behavior: K-EXAONE never emits the channel so the handler is dead (verified by `probe_friendli_channels.py`). No change needed; documenting in parity-matrix as `byte-copied, runtime-dead-on-K-EXAONE`.
- **KOSAX-only file (no CC source path)**: Step A is replaced with a structural template derived from CC analog. Each handler in the KOSAX-only file MUST cite the CC analog's line range in its docstring.
- **CC byte-copy reintroduces a previously-removed feature** (e.g., a CC function that KOSAX deleted as dead): the byte-copy reinstates the function, then a Step B `SWAP/anti-anthropic-1p` commit may re-delete it WITH justification. The justification trail makes the deletion auditable; "silent omission" is no longer possible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each of the 4 in-scope files MUST be classified into one of two procedures:
  - **A**: has direct CC source path → Step A (byte-copy) + Step B (bounded swaps)
  - **B**: KOSAX-only file → Step C (behavior-mirror with CC analog citation per handler)
  Mapping table:

  | KOSAX file | Procedure | CC source / analog | Notes |
  |---|---|---|---|
  | `tui/src/services/api/claude.ts` | A | `services/api/claude.ts` | direct byte-copy possible |
  | `tui/src/ipc/llmClient.ts` | B | `services/api/claude.ts:1980-2295` (streaming handler portion) + `query.ts` | KOSAX-only IPC adapter; thin shim that exposes Anthropic-SDK-shaped interface so claude.ts byte-copy stays valid |
  | `src/kosax/llm/client.py` | B | `services/api/claude.ts` (whole file as analog) | KOSAX-only Python; behavior-mirror with FriendliAI OpenAI SDK |
  | `src/kosax/ipc/stdio.py` | B | `QueryEngine.ts` agentic loop | KOSAX-only Python IPC server; behavior-mirror per-turn loop semantics |

- **FR-002**: Step A byte-copy commits MUST produce a file SHA-256 equal to the CC source SHA-256. The first rebuild commit per Procedure-A file IS the byte-copy.
- **FR-003**: Every Step B / Step C diff hunk MUST be classified into one of the four allowed swap categories: `SWAP/llm-provider`, `SWAP/tool-domain`, `SWAP/anti-anthropic-1p`, `SWAP/identifier-rename`. Commit messages prefix with `swap/<category>:`.
- **FR-004**: A new audit script `scripts/llm_swap_parity_audit.sh` MUST verify both byte-copy SHAs (FR-002) and swap-category coverage (FR-003). Script exits 1 + diagnostic naming any unjustified diff.
- **FR-005**: For Procedure-B files, every handler / function in the KOSAX-only file MUST cite its CC analog reference (file + line range) in its docstring or comment. The audit script verifies citations exist (grep for `CC reference:` token).
- **FR-006**: The KOSAX-only IPC adapter `tui/src/ipc/llmClient.ts` MUST expose an Anthropic-SDK-shaped interface (KosaxRawMessageStreamEvent / KosaxContentBlockParam etc. already in `tui/src/sdk-compat.ts`) so that `tui/src/services/api/claude.ts` byte-copy remains valid — the only diff at the call site is import path swap.
- **FR-007**: `src/kosax/llm/client.py` MUST forward FriendliAI `delta.reasoning_content` to `AssistantChunkFrame.thinking` for ALL streaming chat completions. Behavior-mirror with CC's claude.ts thinking_delta handling. Regression test `tests/llm/test_reasoning_content_forwarding.py` MUST guard.
- **FR-008**: `src/kosax/ipc/stdio.py` agentic loop MUST behavior-mirror CC `QueryEngine.ts` per-turn pattern: fresh `message_id` per turn, structured `tool_calls` dispatch, `role="tool"` message injection, max_turns termination via `KOSAX_AGENTIC_LOOP_MAX_TURNS`. The `_ensure_tool_registry` lazy-init fix (applied 2026-05-01) MUST remain.
- **FR-009**: A new test `tests/integration/test_thinking_channel_e2e.py` MUST verify the full plumbing: simulated FriendliAI SSE → KOSAX LLMClient `thinking_delta` → backend `AssistantChunkFrame.thinking` → IPC bridge → TUI llmClient.ts `content_block_delta { type: 'thinking_delta' }` → assistant message contains `{ type: 'thinking' }` block → Ink snapshot of `AssistantThinkingMessage` rendered.
- **FR-010**: `KOSAX_K_EXAONE_THINKING` env default MUST remain `true` (Spec 2521 set; model card recommendation); `=false` override remains as escape hatch.
- **FR-011**: `prompts/system_v1.md` `<turn_order>` section (added 2026-05-01) MUST be preserved; `prompts/manifest.yaml` SHA-256 MUST be kept in sync (Spec 026 boot guard).
- **FR-012**: Zero new runtime dependencies (AGENTS.md hard rule).
- **FR-013**: A replay script `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh` MUST reproduce the rebuild procedure on clean main: byte-copy + swap commits applied in order produce identical post-rebuild state.

### Key Entities

- **CCSourceFile**: A file under `.references/claude-code-sourcemap/restored-src/` treated as read-only source-of-truth. Has `path`, `sha256`, `line_count`.
- **KOSAXTargetFile**: A file in the rebuild scope. Has `path`, `procedure` ∈ {A, B}, `cc_source_path` (or null), `cc_analog_path` (for Procedure B).
- **SwapCommit**: A git commit on the rebuild branch. Has `category` ∈ {`SWAP/llm-provider`, `SWAP/tool-domain`, `SWAP/anti-anthropic-1p`, `SWAP/identifier-rename`}, `cc_reference_lines` (line range citation), `kosax_target_lines`, `justification` (free text).
- **ParityAuditOutcome**: emitted by `scripts/llm_swap_parity_audit.sh`. Per file: `byte_copy_sha_match` ∈ {true, false}, `unjustified_hunks: List[DiffHunk]`, `missing_cc_citations: List[Function]`. Exit 0 only when ALL files: byte_copy_sha_match=true AND unjustified_hunks=[] AND missing_cc_citations=[].

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Citizen running "오늘 부산 날씨 어때?" sees ≥1 `∴ Thinking` line render in the live REPL view between the user prompt and the first tool call. Verified via Layer 3 PTY text-log + Layer 4 vhs PNG keyframe (Lead Opus reads keyframe to confirm dim-italic `∴ Thinking` glyph).
- **SC-002**: For each Procedure-A file, SHA-256 of the byte-copy commit's KOSAX file equals SHA-256 of the corresponding CC source file. Recorded in `parity-matrix.md`.
- **SC-003**: For each Procedure-A file, every diff hunk between the post-rebuild KOSAX state and the CC source falls into one of the four allowed swap categories. `scripts/llm_swap_parity_audit.sh` exits 0.
- **SC-004**: For each Procedure-B file, every handler / function has a `CC reference: <path>:<line_range>` citation in its docstring or comment.
- **SC-005**: `uv run pytest` baseline tests stay green: ≥1660 passed, 0 new failures introduced. `bun test` baseline stays green.
- **SC-006**: User-reported flow regression (verbose narration in content channel + tool calls bunched without thinking display) NOT observed in TUI live view after rebuild.
- **SC-007**: `cleanup-needed` count in Spec 2292 audit drops to 0 for the 4 in-scope files. Out-of-scope entries get tracking issues.
- **SC-008**: Test `test_thinking_channel_e2e.py` (FR-009) PASS.
- **SC-009**: No new runtime dependency (FR-012 verified by `git diff pyproject.toml tui/package.json`).
- **SC-010**: `prompts/manifest.yaml` system_v1.md SHA-256 matches the actual file (Spec 026 boot guard).
- **SC-011**: `scripts/replay_rebuild.sh` (FR-013) reproduces the rebuild branch from clean main: post-replay working tree byte-equal to rebuild branch.

## Assumptions

- The CC source-of-truth at `.references/claude-code-sourcemap/restored-src/` is stable for the duration of this Epic. If a refresh occurs, the rebuild's byte-copy SHAs would change — the replay script (FR-013) detects this and re-runs.
- KOSAX-only adapter `tui/src/ipc/llmClient.ts` already exposes Anthropic-SDK-shaped types via `tui/src/sdk-compat.ts`. Verified — types like `KosaxRawMessageStreamEvent`, `KosaxContentBlockParam` exist and structurally match Anthropic's SDK shapes. The byte-copy of `claude.ts` will reference these instead of `@anthropic-ai/sdk`, which is a `SWAP/llm-provider` diff hunk.
- FriendliAI continues to honor `chat_template_kwargs.enable_thinking` (verified 2026-05-01: false → 0 reasoning bytes; true → 1098 reasoning bytes).
- K-EXAONE-236B-A23B remains the model (AGENTS.md L1-A pillar; switch evaluated 2026-05-01 against EXAONE-4.5-33B and EXAONE-Deep, K-EXAONE wins on τ²-Bench).
- The just-applied fixes 2026-05-01 — `_ensure_tool_registry` register, `<turn_order>` prompt section, `enable_thinking=true` default, partial `chunk.thinking` plumbing — are folded into Step B / Step C swap commits with retroactive justification per category.
- Initiative #2290 remains parent. This Epic is filed as a child Epic of #2290 referencing the CORE THESIS pillar.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Backend tool adapter rebuild** — the OTHER swap surface (Korean public API caller). Owned by Initiative #2290 phases P3-P6.
- **TUI component rebuild beyond the IPC/streaming layer** — UI L2 work (Spec 1635 successors) not modified.
- **Switching LLM provider or model variant** — fixed per AGENTS.md L1-A and 2026-05-01 model evaluation.
- **Multi-model split architecture** — evaluated 2026-05-01, rejected.
- **Project-wide byte-copy + swap re-application** — this Epic applies the methodology only to the 4 LLM-bridge files. The other ~218 modified KOSAX files (per Spec 2292 audit) keep their existing classification.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Apply Step A byte-copy + Step B swap methodology to the remaining ~218 modified KOSAX files | Sized too large for this Epic; this Epic establishes the methodology + the audit script + the replay script, future Epics apply per-file | Successor Epics under Initiative #2290 | #2571 |
| `tui/src/services/api/claude.ts` function-by-function audit BEYOND the byte-copy + swap step | The byte-copy guarantees parity at file granularity; per-function review is a finer audit deferred unless a regression surfaces | Successor Epic | #2572 |
| `citations_delta` / `connector_text_delta` / `server_tool_use` / `signature_delta` channel handlers | Byte-copy restores them all; runtime is dead because K-EXAONE doesn't emit these channels. No KOSAX-side action needed unless a future feature uses them. | N/A — `byte-copied, runtime-dead-on-K-EXAONE` documented in parity-matrix | #2573 (activated only if KOSAX adopts these features) |
| Parallel/serial tool dispatch partitioning (CC `runTools` `partitionToolCalls` with `concurrencySafe`) | Byte-copy restores CC's partition logic; KOSAX's primitives are read-only-equivalent so the partition policy is benign on the citizen surface | Future Epic when KOSAX adds first write-side primitive that requires sequencing | #2574 |
| Adapter manifest race fix (`Adapter manifest not yet synced`) | Surfaced 2026-05-01 smoke. The race lives in TUI `LookupPrimitive.validateInput`, upstream of the rebuild scope. | UI L2 successor Epic | #2575 |
| CC source-of-truth refresh handling (when `.references/claude-code-sourcemap/restored-src/` is updated to a newer CC release) | Replay script (FR-013) detects + flags but does not auto-resolve. Manual review of swap commits required. | Future maintenance Epic | #2576 |
