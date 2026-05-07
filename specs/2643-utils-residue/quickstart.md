# Quickstart — Epic G · Utils 잔존 정리

**Date**: 2026-05-03

This document provides the verification chain (Layer 1a → 5) for Epic G plus the K-EXAONE retry budget measurement protocol cited in spec SC-007.

## Prerequisites

- Worktree at `/Users/um-yunsang/UMMAYA-w-2643/` checked out on branch `feat/2643-s9-utils-residue`.
- `bun install` complete in `tui/`.
- `uv sync` complete at repo root.
- `.env` populated with `FRIENDLI_TOKEN` (for SC-007 manual measurement only — never used in CI).

## Verification Chain (per AGENTS.md § TUI verification methodology)

### Layer 1a — Python `pytest`

```bash
cd /Users/um-yunsang/UMMAYA-w-2643
uv run pytest --quiet 2>&1 | tail -20
```

**Expected**: 3458 pass / 1 pre-existing fail (baseline match, no Python files modified by this Epic).

### Layer 1b — Ink snapshot / unit `bun test`

```bash
cd /Users/um-yunsang/UMMAYA-w-2643/tui
bun test 2>&1 | tail -30
```

**Expected delta vs main `9d559b9`**:
- 4+ new passing tests in `tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` (Korean fixtures).
- 1+ new passing test in `tui/src/utils/__tests__/sessionTitle.test.ts` (mocked `queryHaiku`).
- Permissions suite: 0 regression.
- Total ≥ 988 pass (983 baseline + 5 new), 1 pre-existing fail unchanged.

### Layer 2 — stdio JSONL probe

```bash
cd /Users/um-yunsang/UMMAYA-w-2643/tui
bun typecheck 2>&1 | tail -20
```

**Expected**: 0 errors. `cli/print.ts:156` import resolves (no "Cannot find module 'src/utils/sessionTitle.js'" error).

### Layer 3 — Interactive PTY text-log scenario

```bash
cd /Users/um-yunsang/UMMAYA-w-2643
scripts/tui-tmux-capture.sh \
  specs/2643-utils-residue/smoke-frames \
  specs/2643-utils-residue/scripts/smoke-session-title.sh
```

Scenario script (to be authored under `specs/2643-utils-residue/scripts/smoke-session-title.sh`):

1. Spawn `bun run tui --print < /dev/null` (SDK headless mode trigger).
2. Send a Korean chat input via stdin: `한강 다리 사고 확인 도와줘`.
3. `wait_for_pane '\$$ tool_registry: \d+ entries verified' 30`.
4. `wait_for_pane '한강' 90` (K-EXAONE response window, p95 ≤ 6 s; deadline 90 s for slow boot).
5. Capture pane snapshots: `snap-001-boot.txt`, `snap-002-input-sent.txt`, `snap-003-title-rendered.txt`.

### Layer 4 — vhs `.tape` visual scenario with PNG keyframes

To be authored at `specs/2643-utils-residue/scripts/smoke.tape`:

```vhs
Output specs/2643-utils-residue/smoke.gif
Set Width 1200
Set Height 800
Set Theme Dropbox

Type "bun run tui"
Enter
Sleep 4s
Screenshot specs/2643-utils-residue/smoke-keyframe-boot.png

Type "한강 다리 사고 확인 도와줘"
Enter
Sleep 1s
Screenshot specs/2643-utils-residue/smoke-keyframe-input.png

Sleep 8s
Screenshot specs/2643-utils-residue/smoke-keyframe-title-rendered.png

Ctrl+C
Ctrl+C
```

**Acceptance**: Lead Opus reads each PNG via Read tool; verifies (a) boot frame shows ToolRegistry banner, (b) input frame shows user message, (c) title frame shows the K-EXAONE-generated session title in the header bar.

### Layer 5 — tmux capture-pane (canonical replacement for asciinema-in-asciinema)

Same scenario as Layer 3 plus `frames/` dir from polled `tmux capture-pane -p`. Each snapshot named `snap-NNN-<label>.txt` plus `final.txt`. Lead Opus reads ALL frames (not just `final.txt`) per AGENTS.md anti-pattern #1 ("Final-state fallacy").

## SC-007 — K-EXAONE Retry Budget Measurement Protocol

**Goal**: Confirm `generateSessionTitle` p95 ≤ 6 s on FriendliAI Tier 1 (60 RPM) for 3 non-trivial Korean inputs.

**Measurement script** (`specs/2643-utils-residue/scripts/measure-session-title-latency.ts`):

```ts
import { generateSessionTitle } from 'src/utils/sessionTitle.js'
import { createAbortController } from 'src/utils/abortController.js'

const inputs = [
  '한강 다리에서 사고가 났어요. 어디로 신고해야 할지 알려주세요.',
  '내일 오후 3시에 강북삼성병원 응급실 예약 가능한지 확인해줘.',
  '서울 종로구 광화문 근처 미세먼지 농도가 어떤지 알려주세요.',
]

for (const description of inputs) {
  const ctl = createAbortController()
  const t0 = Date.now()
  const title = await generateSessionTitle(description, ctl.signal)
  const dt = Date.now() - t0
  console.log(JSON.stringify({ description, title, latencyMs: dt }))
}
```

**Run** (manual, never in CI):

```bash
cd /Users/um-yunsang/UMMAYA-w-2643/tui
bun run specs/2643-utils-residue/scripts/measure-session-title-latency.ts > specs/2643-utils-residue/sc-007-measurements.json
```

**Acceptance**: Sort `latencyMs` values, take p95 (or for n=3, the max). Verify ≤ 6000 ms. Document the exact 3 latency values + final p95 in `quickstart.md` after measurement.

**Measured values** (to be filled after implement phase):
- Input 1: ___ ms → title = ___
- Input 2: ___ ms → title = ___
- Input 3: ___ ms → title = ___
- p95 (max of 3): ___ ms → ✓ / ✗ vs 6000 ms target

## ADR-009 Acceptance

- [ ] `docs/adr/ADR-009-secureStorage-drop.md` exists.
- [ ] 5 sections present: Status / Context / Decision / Consequences / Future trigger.
- [ ] All 6 CC `secureStorage/` files enumerated with LOC totals (FR-018).
- [ ] Future trigger condition is measurable (FR-019).
- [ ] `decisions.md § S9 Utils` row 2 cross-references `ADR-009` (FR-020).
- [ ] `scope-S9-utils.md § P0-2~6` and `§ D2` cross-reference `ADR-009` (FR-020).

## Diff Audit (post-implementation)

```bash
cd /Users/um-yunsang/UMMAYA-w-2643
diff -u .references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts \
        tui/src/utils/sessionTitle.ts | head -20
diff -u .references/claude-code-sourcemap/restored-src/src/utils/mcp/dateTimeParser.ts \
        tui/src/utils/mcp/dateTimeParser.ts | head -20
diff -u .references/claude-code-sourcemap/restored-src/src/utils/permissions/permissions.ts \
        tui/src/utils/permissions/permissions.ts | wc -l
```

**Expected**:
- `sessionTitle.ts` diff ≤ 3 hunk lines (SWAP comment only).
- `dateTimeParser.ts` diff ≤ 3 hunk lines (SWAP comment only).
- `permissions.ts` diff ≤ 8 hunk lines total (FR-016).
