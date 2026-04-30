# Quickstart — Epic ζ #2297 Operator Guide

**Audience**: Lead Opus + Sonnet teammates executing `/speckit-implement` for this Epic.
**Date**: 2026-04-30
**Branch**: `2297-zeta-e2e-smoke`
**Worktree**: `/Users/um-yunsang/KOSMOS-w-2297`

## Pre-flight checks

```bash
cd /Users/um-yunsang/KOSMOS-w-2297

# 1. Confirm η is on main
git log --oneline | grep 1321f77    # MUST show "feat(2298): system prompt rewrite + 5-tool LLM surface"

# 2. Confirm the registry has 5 core tools
uv run python -c "
from kosmos.tools.mvp_surface import register_mvp_surface
from kosmos.tools.registry import ToolRegistry
register_mvp_surface(ToolRegistry())
print(ToolRegistry().count())  # MUST show 19 (16 + 3 new from η)
"

# 3. Confirm prompts/manifest.yaml SHA matches main
git diff main -- prompts/    # MUST be empty (FR-022)

# 4. Confirm worktree is clean
git status --short
```

## Phase 0a — Backend schema (sonnet-backend, ≤4 files)

**Goal**: `_VerifyInputForLLM` accepts `{tool_id, params}` shape from LLM and translates to `{family_hint, session_context}`.

**Files to create**:
- `src/kosmos/tools/verify_canonical_map.py` (new) — see `data-model.md § 2`
- `tests/unit/test_verify_canonical_map_parser.py` (new) — assert ≥10 entries + canonical names

**Files to modify**:
- `src/kosmos/tools/mvp_surface.py:243` — extend `_VerifyInputForLLM` per `contracts/verify-input-shape.md` I-V1 through I-V8

**Files to add**:
- `tests/integration/test_tool_id_to_family_hint_translation.py` (new) — 10 parametrised cases per canonical family + 1 unknown-tool_id case (per User Story 3 acceptance scenarios)

**Verification command**:
```bash
uv run pytest tests/unit/test_verify_canonical_map_parser.py tests/integration/test_tool_id_to_family_hint_translation.py -v
uv run ruff format --check src/kosmos/tools/
uv run ruff check src/kosmos/tools/
uv run mypy src/kosmos/tools/mvp_surface.py src/kosmos/tools/verify_canonical_map.py
```

All MUST pass.

## Phase 0b — TUI dispatcher (sonnet-tui, ≤8 files)

**Goal**: 4 primitive `call()` bodies dispatch via real IPC instead of returning `{status: 'stub'}`.

**Files to create**:
- `tui/src/tools/_shared/dispatchPrimitive.ts` (new) — see `data-model.md § 4` + `contracts/tui-primitive-dispatcher.md`
- `tui/src/tools/_shared/pendingCallRegistry.ts` (new) — see `data-model.md § 3`
- `tui/src/tools/_shared/dispatchPrimitive.test.ts` (new) — bun test per I-D10

**Files to modify**:
- `tui/src/tools/LookupPrimitive/LookupPrimitive.ts:319-330` — replace stub `call()`
- `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts:248-263` — replace stub `call()` (NO translation per FR-009)
- `tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts:255-265` — replace stub `call()`
- `tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts` (verify line range during impl) — replace stub `call()`
- `tui/src/ipc/llmClient.ts:405` — add `tool_result` arm per `contracts/tui-primitive-dispatcher.md` I-D5

**Verification command**:
```bash
cd tui
bun typecheck                           # MUST pass with 0 errors
bun test src/tools/_shared/dispatchPrimitive.test.ts -v
bun test                                # full TUI test suite — no regressions vs main
bun run tui                             # interactive boot smoke — confirm KOSMOS banner renders
```

## Phase 1a — Smoke harness + integration tests + fixtures (sonnet-smoke, ≤14 files)

**Goal**: Capture E2E PTY + vhs artefacts; integration tests for FR-016 + FR-020.

**Files to create** (smoke harness):
- `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect` — see `contracts/pty-smoke-protocol.md` I-P1
- `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape` — see `contracts/vhs-keyframe-protocol.md` I-K1
- `specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh` — SC-009 link prober
- `specs/2297-zeta-e2e-smoke/scripts/check_scenario_docs.py` — SC-010 doc structure checker

**Files to capture** (PTY + vhs run on a working tree after Phase 0a + 0b complete):
- `specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt` — Layer 2 capture
- `specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-{1-boot,2-dispatch,3-receipt}.png` — Layer 4 keyframes
- `specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn.gif` — Layer 4 animated

**Files to create** (integration tests):
- `tests/integration/test_tui_primitive_dispatch_e2e.py` (new) — per FR-016, ≤80 LOC
- `tests/integration/test_all_15_mocks_invoked.py` (new) — per FR-020 + SC-004
- `tests/fixtures/citizen_chains/<family>.json` (new × 10) — per FR-019

**Verification command**:
```bash
# After Phase 0a + 0b complete:
expect specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect
grep -c 'tool_call' specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt   # ≥3
grep -c 'tool_result' specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt # ≥3
grep -oE '접수번호: hometax-2026-[0-9]{2}-[0-9]{2}-RX-[A-Z0-9]{5}' \
   specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt | wc -l            # =1
grep -c 'CHECKPOINTreceipt token observed' \
   specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt                    # =1

vhs specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape
ls specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-*.png | wc -l               # ≥3

uv run pytest tests/integration/test_tui_primitive_dispatch_e2e.py \
              tests/integration/test_all_15_mocks_invoked.py -v
```

All MUST pass.

## Phase 1b — Docs (Lead solo, 6 files)

**Goal**: `policy-mapping.md` + 5 OPAQUE scenario docs.

**Files to create**:
- `docs/research/policy-mapping.md` — per `data-model.md § 8` + FR-017
- `docs/scenarios/hometax-tax-filing.md` — per `data-model.md § 9` + FR-018
- `docs/scenarios/gov24-minwon-submit.md` — per FR-018
- `docs/scenarios/mobile-id-issuance.md` — per FR-018
- `docs/scenarios/kec-yessign-signing.md` — per FR-018
- `docs/scenarios/mydata-live.md` — per FR-018

**Verification command**:
```bash
bash specs/2297-zeta-e2e-smoke/scripts/probe_policy_links.sh                    # exit 0
uv run python specs/2297-zeta-e2e-smoke/scripts/check_scenario_docs.py          # exit 0
```

## Lead push checklist (final gate)

Before `git push`:

```bash
# 1. All Python tests pass
uv run pytest -q

# 2. All TS tests pass
cd tui && bun test
bun typecheck
cd ..

# 3. Lint+type
uv run ruff format --check
uv run ruff check
uv run mypy src/kosmos

# 4. Smoke artefacts present (FR-012 + SC-012)
ls specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect \
   specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt \
   specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape \
   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-1-boot.png \
   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-2-dispatch.png \
   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-3-receipt.png

# 5. Manifest hash invariant (FR-022)
git diff main -- prompts/    # MUST be empty

# 6. No new runtime deps (FR-023)
git diff main -- pyproject.toml tui/package.json    # NO new entries under [project.dependencies] or "dependencies"

# 7. Lead Opus visual verification of keyframe-3 (SC-002)
# Use Read tool on smoke-keyframe-3-receipt.png — confirm receipt id visible

# 8. PR title MUST start lowercase (memory: feedback_pr_title_lowercase)
# Suggested: "feat(2297): zeta E2E smoke — TUI primitive wiring + citizen tax-return chain"
```

## Auto-merge gates

- ✅ CI green (pytest + bun test + bun typecheck + ruff + mypy)
- ✅ Codex inline comments addressed (zero P1 unresolved)
- ✅ Copilot review gate `completed` (per AGENTS.md § Copilot Review Gate)

## Sub-issue closure

After merge:
```bash
gh api graphql -f query='
mutation { closeIssue(input: {issueId: "<#2481_node_id>"}) { issue { state } } }
'
# Or simpler: gh issue close 2481 --comment "Closed by PR <N> (Epic ζ #2297 merge)"
```

Per AGENTS.md § PR closing rule, the PR body lists `Closes #2297` only — Task sub-issues close after merge via Sub-Issues API graph traversal.
