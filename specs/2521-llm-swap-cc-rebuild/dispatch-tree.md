# Dispatch Tree — Spec 2521 LLM Swap-Surface Rebuild

**Lead**: Opus (this session) — drives all spec/plan/audit/PR work + sonnet review.
**Teammates**: Sonnet (`backend-architect`, `frontend-developer`, `api-tester`, `code-reviewer`) — implementation only per AGENTS.md hard rule (≤5 tasks AND ≤10 file changes per teammate).

## Phase plan

```text
Phase 1+2 — Setup + Foundational (T001-T009)
   Lead Opus solo (scaffolding: parity-matrix SHA capture + script skeletons + retroactive labels)

Phase 3 — US1 Citizen sees thinking (T010-T025) ── 4 parallel teammates
   ├─ sonnet-procedure-a    (T010-T014)  ← claude.ts byte-copy + 3 swaps + verify
   ├─ sonnet-procedure-b-tui (T015-T017)  ← llmClient.ts citations + SKIPPED comments
   ├─ sonnet-procedure-b-py  (T018-T023)  ← client.py + stdio.py citations + e2e tests
   └─ sonnet-tui-tests       (T024-T025)  ← ink-testing-library + vhs smoke

Phase 4 — US2 Audit script (T026-T034) ── single team after Phase 3
   sonnet-audit (T026-T034)  ← parity audit script + CI integration

Phase 5 — US3 Replay (T035-T037) ── single team after Phase 4
   sonnet-replay (T035-T037)

Phase 6 — US4 Cleanup (T038-T041) ── parallel-safe with Phase 5
   sonnet-cleanup (T038-T041)

Phase 7 — Polish (T042-T050)
   Lead Opus solo (parity-matrix final populate + PR description + final audit)
```

## Sonnet teammate contracts

Each teammate brief stays ≤30 lines per AGENTS.md. Long instructions reference `specs/2521-llm-swap-cc-rebuild/quickstart.md` or `parity-matrix.md`.

### sonnet-procedure-a (T010-T014, 5 tasks, ~5 file changes — claude.ts only)

Brief: Apply Step A byte-copy + 3 Step B swap commits to `tui/src/services/api/claude.ts`. Each commit subject prefixed `byte-copy(2521):` or `swap/<category>(2521):` per parity-matrix.md taxonomy. Verify post-swap `bun --cwd tui run typecheck` clean + existing tests stay green. NO scope creep — any non-swap diff is drift and must be reverted.

### sonnet-procedure-b-tui (T015-T017, 3 tasks, 1 file)

Brief: Add `CC reference: services/api/claude.ts:<line-range>` citations to every handler in `tui/src/ipc/llmClient.ts`. Add `// SKIPPED — KOSMOS-N/A: <reason>` comments for the 4 channels K-EXAONE doesn't emit. NO functional changes — only comment additions.

### sonnet-procedure-b-py (T018-T023, 6 tasks — split if needed; for now Lead may collapse)

Brief: Add `CC reference:` citations to `_stream_response` (client.py), `_handle_chat_request` / `_dispatch_primitive` / `_ensure_tool_registry` (stdio.py). Implement 2 regression tests (`test_reasoning_content_forwarding.py` + `test_thinking_channel_e2e.py`). All citations cite real CC line ranges from `.references/claude-code-sourcemap/restored-src/`.

### sonnet-tui-tests (T024-T025, 2 tasks)

Brief: Implement `tui/tests/ipc/thinking-delta-render.test.tsx` using `ink-testing-library` v4. Author + run vhs scenario `specs/2521-llm-swap-cc-rebuild/scripts/smoke-thinking-render.tape` capturing 3 PNG keyframes. Assert `∴ Thinking` glyph visible in keyframe 2.

### sonnet-audit (T026-T034, 9 tasks — collapse to ≤5 per AGENTS.md)

Brief: Implement full `scripts/llm_swap_parity_audit.sh` per `contracts/parity-audit-cli.md`: SHA verification + swap-category verification + unjustified-hunk detection + Procedure-B citation grep + CC stream-event enumeration. Add CI integration. Author negative tests.

### sonnet-replay (T035-T037, 3 tasks)

Brief: Replace `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh` stub with full implementation: byte-copy step + swap-commit cherry-pick. Add CI self-test. Document refresh handling in quickstart.md.

### sonnet-cleanup (T038-T041, 4 tasks)

Brief: Audit `specs/2292-cc-parity-audit/cc-parity-audit.md` cleanup-needed entries that fall in the 4 in-scope files. Apply remediation per FR-007. Update Spec 2292 audit doc + add NEEDS-TRACKING follow-ups for out-of-scope entries.

## Dispatch rules (AGENTS.md hard)

- **Sonnet teammates DO NOT push / create PR / monitor CI / reply to Codex** — those stay with Lead Opus
- Each teammate produces a WIP commit + marks tasks.md `[X]` for completed tasks
- Lead serializes through teammates' results, runs final tests, pushes, opens PR
- If a teammate's diff exceeds 10 file changes, Lead splits into a new sub-team

## MVP boundary

T001-T025 (Phases 1+2+3) = US1 = citizen-visible thinking display. If session time runs short, Lead can ship MVP as standalone PR + queue Phases 4-7 as follow-up Epics.
