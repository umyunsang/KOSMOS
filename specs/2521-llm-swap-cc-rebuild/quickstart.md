# Quickstart: LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md)
**Date**: 2026-05-01

This document describes how to execute and verify the rebuild procedure.

## Prerequisites

- Clean working tree on `main` branch (or rebase target).
- `.references/claude-code-sourcemap/restored-src/` present (CC 2.1.88 source-of-truth).
- Bun 1.2.x + Python 3.12+ + uv installed.
- `KOSMOS_FRIENDLI_TOKEN` + `KOSMOS_DATA_GO_KR_API_KEY` set in `.env` for live smoke.

## Step 1 — Switch to rebuild branch

```sh
git checkout 2521-llm-swap-cc-rebuild
```

## Step 2 — Inspect the canonical parity matrix

```sh
$EDITOR specs/2521-llm-swap-cc-rebuild/parity-matrix.md
```

The matrix lists per file:
- `procedure` (A or B)
- `cc_source_path` or `cc_analog_path`
- byte-copy commit SHA
- subsequent swap commits with categories
- coverage of the CC stream-event channels

## Step 3 — Run the parity audit (CI gate)

```sh
scripts/llm_swap_parity_audit.sh
```

Expected output: `**Result**: ✅ PASS`. See `contracts/parity-audit-cli.md` for full output spec.

If FAIL: stdout names the failing file + reason (unjustified hunk / byte-copy mismatch / missing citation). The Epic is not mergeable until 0 failures.

## Step 4 — Replay the rebuild from clean main (optional, reproducibility check)

```sh
# In a scratch worktree, on a clean main:
git worktree add /tmp/2521-replay main
cd /tmp/2521-replay
specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh
git diff 2521-llm-swap-cc-rebuild
# Expected: empty diff (replay produces same tree as the branch)
```

Replay script applies, in order:
1. Step A byte-copy commits per Procedure-A file (using `cp <cc_source_path> <kosmos_path>` then `git commit -m "byte-copy(2521): import CC <path>"`)
2. Step B swap commits in their original order, each with their category-prefixed subject

## Step 5 — Verify the user-visible thinking display (Layer 4 vhs smoke)

```sh
pkill -f "bun.*tui|kosmos.*ipc" 2>/dev/null
find src/kosmos/ipc/__pycache__ src/kosmos/llm/__pycache__ -name '*.pyc' -delete 2>/dev/null

# Run vhs scenario
vhs specs/2521-llm-swap-cc-rebuild/scripts/smoke-thinking-render.tape

# Expected artifacts (vision-verified by Lead Opus):
ls specs/2521-llm-swap-cc-rebuild/
#   smoke-keyframe-1-boot.png
#   smoke-keyframe-2-thinking.png    ← MUST show "∴ Thinking" dim italic
#   smoke-keyframe-3-result.png
```

## Step 6 — Run regression tests

```sh
# Backend Python
uv run pytest tests/llm tests/integration tests/ipc -x

# TUI Bun
bun --cwd tui test
```

Expected: ≥1660 passed Python tests + bun test baseline green.

## Step 7 — Optional: spot-check individual swap categories

Inspect commits by category:

```sh
# llm-provider swaps (Anthropic SDK → KOSMOS IPC)
git log --oneline 2521-llm-swap-cc-rebuild --grep '^swap/llm-provider:'

# anti-anthropic-1p deletions
git log --oneline 2521-llm-swap-cc-rebuild --grep '^swap/anti-anthropic-1p:'

# identifier renames (brand tokens)
git log --oneline 2521-llm-swap-cc-rebuild --grep '^swap/identifier-rename:'

# tool-domain (CC dev tools → KOSMOS primitives) — likely 0 commits in this Epic
git log --oneline 2521-llm-swap-cc-rebuild --grep '^swap/tool-domain:'
```

## Troubleshooting

### Audit fails: byte-copy SHA mismatch

Cause: byte-copy commit was amended, or `.references/claude-code-sourcemap/restored-src/` changed.

Fix:
```sh
# Re-byte-copy from current CC source:
cp .references/claude-code-sourcemap/restored-src/src/services/api/claude.ts \
   tui/src/services/api/claude.ts
git add tui/src/services/api/claude.ts
git commit --amend --no-edit
# Re-apply swap commits via interactive rebase
git rebase -i <byte-copy-sha>
```

### Audit fails: unjustified hunk

Cause: a recent commit modified an in-scope file without a `swap/<category>:` subject prefix.

Fix:
```sh
git rebase -i HEAD~N
# Edit the offending commit's subject to start with `swap/<category>:`
# Add a `Refs: <cc-path>:<line-range>` line in the body
git rebase --continue
```

### Audit fails: missing CC citation in Procedure-B file

Cause: a function in a Procedure-B file (e.g., `src/kosmos/llm/client.py`) lacks `CC reference: ...` in its docstring.

Fix: add a comment like:
```python
def _stream_response(self, ...):
    """Stream chat completion response.

    CC reference: services/api/claude.ts:1980-2295 (streaming handler).
    Behavior-mirror: emits AssistantChunkFrame fields matching CC's
    content_block_delta event taxonomy.
    """
```

## What this Epic does NOT do

Per spec § Out of Scope:
- Does not modify backend tool adapters (Korean public APIs)
- Does not modify TUI components beyond IPC/streaming layer
- Does not switch LLM provider or model
- Does not apply this methodology project-wide (only the 4 LLM-bridge files)

For project-wide application of this methodology, see the NEEDS TRACKING entry in spec § Deferred to Future Work.
