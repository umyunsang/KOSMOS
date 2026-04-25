# Quickstart — P4 · UI L2 Citizen Port

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-25

This is the citizen golden path: a fresh OS user opens KOSMOS for the first time, completes onboarding, runs a multi-ministry query, sees a Layer 2 permission prompt, and exports the conversation as PDF. Every step references the FRs it exercises, so this doc doubles as a manual smoke-test checklist for `/speckit-implement`.

> Run from repo root. Backend (Python) and TUI (Bun) run as one process via the existing `bun run tui` entry — no extra services to start.

## Prerequisites

```bash
# clean slate (so onboarding fires)
rm -rf ~/.kosmos/memdir/user/onboarding ~/.kosmos/memdir/user/preferences

# Bun + dependencies
cd tui && bun install            # installs pdf-to-img + pdf-lib once
```

## Step 1 — First launch fires the 5-step onboarding (FR-001..006)

```bash
cd /path/to/KOSMOS
bun run tui
```

**Expected**:

1. **Preflight** — Bun ≥ 1.2 ✓, terminal graphics protocol detected (Kitty / iTerm2 / none) ✓, `KOSMOS_*` env vars present ✓ (FR-001).
2. **Theme** — UFO mascot idle pose renders in body `#a78bfa` over background `#4c1d95` (FR-035).
3. **PIPA consent** — Screen displays the trustee notice; citizen presses `Y` (FR-006). A receipt is written via the Spec 033 IPC; the TUI shows `rcpt-<id>` in the toast (FR-018).
4. **Ministry scope** — Citizen toggles a subset of ministries (KOROAD / KMA / HIRA / NMC / etc.).
5. **Terminal setup** — Citizen toggles, e.g., `large_font = true` (FR-005). The change reflects in the next render frame (≤ 500 ms, SC-011) and `~/.kosmos/memdir/user/preferences/a11y.json` is written.

REPL appears with the WelcomeV2 block (proposal-iv `EmptyState`) + the `?  /  ⇧⇥ mode` footer.

## Step 2 — Re-run a single onboarding step (FR-003)

```text
> /onboarding ministry-scope
```

**Expected**: only step 4 replays. Other steps' `completed_at` is preserved (audit-friendly).

## Step 3 — Multi-ministry query triggers swarm + agent panel (FR-025..028)

```text
> 출산 보조금 신청 + 운전면허 갱신 + 주민등록 이전 한 번에 안내해줘
```

**Expected**:

- LLM plan emits `mentioned_ministries: ["MOHW","KNPA","MOIS"]` and `complexity_tag: "complex"`. `shouldActivateSwarm` returns `true` (3+ ministries OR complex — A+C union is intentional, FR-027).
- `proposal-iv` ActiveSwarm renders: `PhaseIndicator` + `SpinnerWithVerb` lines + per-ministry `ToolUseBlock` rows with primitive dot color (blue `lookup`, orange `submit`, red `verify`, green `subscribe`).
- Streaming chunks flow ≈ 20 tokens at a time (FR-008 / SC-002). No perceptible stutter.

```text
> /agents
```

**Expected**: 3-row agent panel shows current state per ministry agent (`idle / dispatched / running / waiting-permission / done`).

```text
> /agents --detail
```

**Expected**: same 3 rows + SLA remaining + health (green / amber / red) + rolling-avg response time (FR-026).

## Step 4 — Layer 2 permission prompt appears mid-flow (FR-015..018)

When the swarm's `MOHW` agent reaches the HIRA hospital lookup tool (Layer 2), the gauntlet modal appears.

**Expected**:

- Modal header: `⓶` orange (FR-016).
- Body: tool name, brief explanation, citizen impact line.
- Footer: `[Y 한번만 / A 세션 자동 / N 거부]` (FR-017).

Citizen presses `Y`.

**Expected**:

- Toast appears: `발급됨 rcpt-7d3a8f...` (FR-018).
- Tool call proceeds.
- `kosmos.ui.surface=permission_gauntlet` OTEL span attribute is emitted (FR-037).

## Step 5 — Inspect and revoke a receipt (FR-019..021)

```text
> /consent list
```

**Expected**: table renders all session receipts in reverse chronological order, columns: `rcpt-<id> | layer | tool | decision | timestamp`.

```text
> /consent revoke rcpt-7d3a8f...
```

**Expected**:

- Confirmation modal appears.
- Citizen presses `Y`.
- `revoked_at` is appended to the ledger via Spec 033 IPC (FR-007 + FR-020).
- Toast: `철회 완료`.

```text
> /consent revoke rcpt-7d3a8f...
```

**Expected**: Idempotent — toast says `이미 철회됨`. No new ledger entry (FR-021).

## Step 6 — Bypass-permissions reinforcement (FR-022)

Press `Shift+Tab`. The permission mode cycles through `default → acceptEdits → bypassPermissions`.

**Expected on `bypassPermissions` entry**:

- Reinforcement modal: "이 모드는 모든 권한 모달을 우회합니다. 계속 진행하시겠습니까?".
- Citizen presses `N`.
- Mode reverts to `acceptEdits`. No bypass applied.

## Step 7 — Markdown table + PDF inline (FR-010, FR-011)

Trigger a tool call that returns a markdown table + a PDF attachment (e.g., HIRA hospital list with a downloadable directory PDF).

**Expected**:

- Table renders identically to CC `MarkdownTable.tsx` (FR-011).
- On Kitty / iTerm2: PDF first page renders inline as PNG (FR-010 path A).
- On other terminals: OS `open` invoked, citizen sees fallback line `📄 PDF 열기 시도 중…` (FR-010 path B).
- On headless SSH (no graphics, no `open`): text fallback `📄 <path> · 1.2 MB · sha256:abc…` is shown (Edge case in spec.md).

## Step 8 — Long answer expand/collapse (FR-009)

When the answer overflows the viewport, the response block shows a `Ctrl-O로 펼치기` hint.

Press `Ctrl-O`. The block expands to full size. Press `Ctrl-O` again. It collapses.

## Step 9 — Slash autocomplete (FR-014)

Type `/`. Within 100 ms (SC-005) the dropdown shows all visible commands grouped by prefix match. Highlighted match + inline preview matches CC's `ContextSuggestions` shape.

## Step 10 — Help, config, plugins (FR-029..031)

```text
> /help
```

**Expected**: 4 groups — Session / Permission / Tool / Storage. Every slash command appears in exactly one group.

```text
> /config
```

**Expected**: overlay opens; non-secret settings are inline-editable. Selecting a `.env` secret opens a separate isolated editor (FR-030).

```text
> /plugins
```

**Expected**: browser opens. Active plugins show `⏺`, inactive show `○`. Press `Space` to toggle, `i` for detail, `r` to remove, `a` to enter the marketplace (the marketplace destination is deferred to P5 — see spec.md deferred-items row 6; the keybinding is wired here).

## Step 11 — Export current conversation (FR-032)

```text
> /export
```

**Expected**:

- Progress overlay renders.
- A PDF is written to `~/Downloads/kosmos-export-<timestamp>.pdf` (or platform default).
- Open the PDF. Verify it contains: conversation transcript, every tool call + result, every permission receipt with ID. Verify it does NOT contain any `traceId=` / `spanId=` / `pluginInternal:` markers (FR-032 / SC-012).

## Step 12 — History search (FR-033)

```text
> /history --date 2026-04-01..2026-04-25 --layer 2
```

**Expected**: only sessions in the date window that triggered ≥ 1 Layer 2 receipt. Filters compose with AND semantics.

## Step 13 — Language fallback (FR-004)

```text
> /lang en
```

**Expected**: every modal, toast, error envelope, and aria label switches to English on the next render frame. `/help` headers become `Session / Permission / Tool / Storage`.

## Smoke pass criteria

Steps 1–13 complete with no crashes, no missed FRs, and no unexpected network egress. `lsof -p $(pgrep -f 'bun.*tui')` shows only the existing localhost OTLP collector connection (Spec 028) — SC-008 confirmed.

If any step fails, the implementation is incomplete; do not claim epic done.
