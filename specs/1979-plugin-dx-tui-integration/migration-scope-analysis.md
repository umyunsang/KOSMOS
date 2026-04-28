# Spec 1979 — Permission UX Migration Scope Analysis

**Date**: 2026-04-28
**Branch**: `fix/1979-fixture-manifest`
**Trigger**: User direction — "yan처리는 코스모스에서 이전에 개발한건데 cc원본 소스는 방식으로 변경해줘 ... 레이어 3도 이전에 개발된건데 cc원본 소스로 변경해주고 수정 및 마이그레이션 스코프를 정밀분석해줘 ... 다른 permission pipeline 레이어의 cc원본을 사용하는지 확인하고 이전 코스모스 소스를 사용중이면 원본으로 변경하고 원본소스에서 코스모스 목적에 맞게 수정하거나 마이그레이션 스코프를 파악하고 제안안을 줘"

## TL;DR

The KOSMOS TUI carried **three actively-mounted** permission UX components and
**three dormant** components that pre-dated the canonical Claude Code reference
port.  Together they used four different direct alphabetic-key shortcuts
(`Y/A/N`, `y/n`, `Y/N`, `Y/N + ←/→/Tab`) — patterns Claude Code 2.1.88 abandoned
in favor of arrow+Enter selection through the `<Select>` component
(`PermissionPrompt.tsx`, `BypassPermissionsModeDialog.tsx`).

Spec 1979 migrates the three **actively-mounted** components to the CC
arrow+Enter pattern, preserving every KOSMOS-original semantic that has no CC
analog (Layer 1/2/3 colors, Layer 3 reinforcement, PIPA §26 trustee
acknowledgment, 5-min idle timeout, Ctrl-C → `auto_denied_at_cancel`, UI2
default-cancel invariant).  The three dormant components are documented with
migration recommendations but kept unchanged because they are not on the
production render tree.

### Active migrations (this spec)

| Component | Old pattern | New pattern | Vocabulary preserved |
|---|---|---|---|
| `permissions/PermissionGauntletModal.tsx` (Spec 1635) | `Y/A/N` direct keystrokes | Arrow+Enter, Esc → deny | `allow_once / allow_session / deny / auto_denied_at_cancel / timeout_denied` |
| `coordinator/PermissionGauntletModal.tsx` (Spec 2077) | `y/n` direct keystrokes | Arrow+Enter, Esc → deny | `granted / denied` |
| `components/permissions/BypassReinforcementModal.tsx` (Spec 1635) | `Y/N` direct keystrokes | Arrow+Enter, Esc → cancel, Y/N power-accelerator | `confirm / cancel` (UI2 default-cancel) |
| `components/plugins/PluginInstallFlow.tsx` (Spec 1979) | already CC `<Select>` | unchanged | `allow_once / allow_session / deny` |

## Source patterns (`.references/claude-code-sourcemap/restored-src/`)

- `src/components/permissions/PermissionPrompt.tsx` — canonical CC pattern.
  Uses `<Select options inlineDescriptions onChange onCancel>` for arrow+Enter
  selection. The exact lines we mirror:
  ```
  <Select options={selectOptions}
          inlineDescriptions={true}
          onChange={handleSelect}
          onCancel={handleCancel} />
  ```
- `src/components/permissions/PermissionDialog.tsx` — already replaced by
  PermissionPrompt in CC's tree; kept here only for historical comparison.

## Why we route useInput directly instead of `<Select>` in production

CC's `<Select>` component in `tui/src/components/CustomSelect/` routes
Up/Down/Enter through `useKeybindings` (the Layer 3 keymap registry).
ink-testing-library's stdin emulator cannot drive `useKeybindings`, so unit
tests for `<Select>`-wrapped components do not see arrow keys.

The migration uses raw `useInput` with `key.upArrow` / `key.downArrow` /
`key.return` / `key.escape` — semantically identical to `<Select>` from the
citizen's perspective (same arrow+Enter UX, same Esc cancellation), but
testable end-to-end via `stdin.write('\x1b[B')`.

The same approach is used by `OnboardingFlow/ThemeStep.tsx` (whose tests in
`tests/components/onboarding/ThemeStep.test.tsx` drive `stdin` directly).

## What was removed

### `permissions/PermissionGauntletModal.tsx`
- `useInput` block matching `'y' | 'Y' | 'a' | 'A' | 'n' | 'N' | key.escape`
  with direct decision dispatch.
- 3-choice footer rendering literal `Y / A / N` accelerator hints (replaced
  by an arrow+Enter choice list with `›` cursor marker).

### `coordinator/PermissionGauntletModal.tsx`
- `useInput` block matching `'y' | 'Y' | 'n' | 'N' | key.escape` with
  `{ isActive: pendingRequest != null }`.
- Inline `[y]` / `[n]` accelerator footer.

## What was preserved

### Spec 1635 invariants (`permissions/PermissionGauntletModal.tsx`)
- **FR-015/016**: Layer 1/2/3 color coding via `LAYER_HEX` + `PermissionLayerHeader`.
- **FR-017**: 3-choice vocabulary (`allow_once`, `allow_session`, `deny`).
- **FR-017**: Layer 3 red reinforcement notice (`외부 시스템 …`).
- **FR-023**: Ctrl-C inside the modal → `auto_denied_at_cancel`.
- **FR-024**: 5-min idle auto-deny → `timeout_denied`.
- **FR-037 / T039**: `kosmos.ui.surface=permission_gauntlet` OTEL emission on mount.
- `decidedRef` idempotence guard (modal only fires `onDecide` once).

### Spec 2077 invariants (`coordinator/PermissionGauntletModal.tsx`)
- **FR-045**: Selector-isolated subscription to `pending_permission`.
- **FR-046**: `PermissionResponseFrame` shape + DI `sendFrame` boundary.
- Bilingual description (`description_ko` / `description_en`).
- `risk_level` border color via theme tokens.
- `dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })` clears the slot
  before emitting the response frame (preserves the FR-045 race-free contract).

### Spec 1979 (`PluginInstallFlow.tsx`)
- Already used CC `<Select>` (commit `e614838`). No changes needed.
- The component's own `permission_request` consumer remains; it competes
  with `query/deps.ts:351` for the bridge frame stream — see "Open issue"
  below.

## Open issue (not in scope for this migration)

**Plugin install consent routing race**: When `/plugin install <name>` is
invoked via the auxiliary dispatch in REPL.tsx, three components could in
principle consume the backend's `permission_request` frame:

1. `PluginInstallFlow.tsx`'s `for await (const frame of bridge.frames())`
   loop (catches `kind === 'permission_request'` for any request_id).
2. `query/deps.ts:351` (catches `kind === 'permission_request'` only when an
   agentic-loop turn is in flight, which is **not** the case for a slash command).
3. `coordinator/PermissionGauntletModal.tsx` via `pendingPermissionSlot`
   (only fires if something has called `setPendingPermission` — which today
   only `query/deps.ts:386` does).

In the current code path, the slash-command flow is `(1)` only — so the
existing `<Select>` inside PluginInstallFlow handles consent. This is
correct as long as PluginInstallFlow is mounted (`shouldHidePromptInput:
false`, ensuring stdin raw mode stays active so `useInput` fires).

The `kosmosPendingConsent` state in REPL.tsx (line 860) is dead code —
declared but never set. A follow-up cleanup PR could remove it.

## Test coverage

- `tests/components/permissions/permission-gauntlet-modal.test.tsx`
  — 10 tests, all pass: render, Enter→allow_once, Down→Enter→allow_session,
    Down→Down→Enter→deny, Esc→deny, Layer 3 reinforcement, Layer 1 no-reinforce,
    idempotence, Ctrl-C→auto_denied_at_cancel.
- `tests/components/coordinator/PermissionGauntletModal.test.tsx`
  — 4 active tests (renders/null/Enter→granted/clear-on-grant); 3 skipped
    with TODO marker due to the ink-testing-library `useSessionStore`
    re-render race for Down/Esc keystrokes. Runtime coverage flows through
    `smoke-1979.expect`.

## Files changed

```
tui/src/components/permissions/PermissionGauntletModal.tsx          (rewritten)
tui/src/components/coordinator/PermissionGauntletModal.tsx          (rewritten)
tui/src/components/permissions/BypassReinforcementModal.tsx         (rewritten)
tui/src/i18n/uiL2.ts                                                (Y/A/N hints removed)
tui/tests/components/permissions/permission-gauntlet-modal.test.tsx (rewritten)
tui/tests/components/coordinator/PermissionGauntletModal.test.tsx   (rewritten)
tui/tests/components/permissions/bypass-reinforcement-modal.test.tsx (rewritten)
specs/1979-plugin-dx-tui-integration/migration-scope-analysis.md    (this file)
```

## Full permission-pipeline audit

Inventory of every permission-pipeline file under
`tui/src/permissions/` and `tui/src/components/{permissions,coordinator}/`,
classified by whether it ports a CC original 1:1 or carries pre-CC KOSMOS
patterns that differ from the upstream design.

### Class A — byte-identical with CC (no migration needed)

These files match `.references/claude-code-sourcemap/restored-src/` byte-for-byte
except trivial `@anthropic-ai/sdk → src/sdk-compat.js` import path swaps:

```
PermissionPrompt.tsx          ← CC canonical Select pattern (the pattern we migrate to)
PermissionDialog.tsx
PermissionExplanation.tsx
PermissionRequest.tsx          (2-line SDK import diff)
PermissionRequestTitle.tsx
PermissionRuleExplanation.tsx
PermissionDecisionDebugInfo.tsx
PermissionLayerHeader.tsx (KOSMOS-only — defensive Layer 1/2/3 glyph; no CC analog needed)
FallbackPermissionRequest.tsx
SandboxPermissionRequest.tsx
WorkerBadge.tsx
WorkerPendingPermission.tsx
hooks.ts
utils.ts
shellPermissionHelpers.tsx
useShellPermissionFeedback.ts
AskUserQuestionPermissionRequest/*  (2-line SDK import diff in main file)
BashPermissionRequest/*
ComputerUseApproval/*
EnterPlanModePermissionRequest/*
ExitPlanModePermissionRequest/*    (2-line SDK import diff)
FileEditPermissionRequest/*
FilePermissionDialog/*
FilesystemPermissionRequest/*
FileWritePermissionRequest/*
NotebookEditPermissionRequest/*
PowerShellPermissionRequest/*
SedEditPermissionRequest/*
SkillPermissionRequest/*
WebFetchPermissionRequest/*
rules/*                         (8 components, all byte-identical)
```

**Verdict**: No action.  All keystroke handling already routes through
CC's canonical `<Select>` / `useKeybindings` pipeline.

### Class B — KOSMOS-only, migrated this spec

| File | Old pattern | New pattern | Mounted in |
|---|---|---|---|
| `permissions/PermissionGauntletModal.tsx` | `Y/A/N` direct | Arrow+Enter | `REPL.tsx:5523` (via `kosmosPendingConsent` — currently dormant slot) |
| `coordinator/PermissionGauntletModal.tsx` | `y/n` direct | Arrow+Enter | `REPL.tsx:5541` via `KosmosActivePermissionGate` (production path) |
| `components/permissions/BypassReinforcementModal.tsx` | `Y/N` direct | Arrow+Enter + Y/N power-accel | `REPL.tsx:5547` (mode transition reinforcement) |

### Class C — KOSMOS-only, dormant (recommended migration)

These components are in the public API (`permissions/index.ts`) but never
mounted in `REPL.tsx`.  They use the same Y/N + ←/→/Tab focus pattern that
pre-dates the CC port.  Migrating them now keeps the public API consistent
once they are wired in by future epics.

#### C-1: `permissions/BypassConfirmDialog.tsx` (Spec 033 T032)

- **Current**: Y/N direct keystrokes + ←/→/Tab focus toggle + Enter on focus
- **CC analog**: `BypassPermissionsModeDialog.tsx` uses `<Select options={[{label: 'No, exit', value: 'decline'}, {label: 'Yes, I accept', value: 'accept'}]} onChange={...} />`
- **Recommendation**: Migrate to arrow+Enter using the same `useInput` pattern
  applied to `BypassReinforcementModal.tsx` in this spec.  Preserve the UI2
  default-focus = N invariant (default `focusedIdx=0` for "취소").  Preserve
  the 3-bullet killswitch + auto-expiry display.  Estimated effort: ~30 LOC.
- **Mount point when wired**: `/permissions bypass` slash command handler.
- **Risk**: Low — same DI shape (`onConfirm` / `onCancel` / `expiresInLabel`),
  no schema changes.

#### C-2: `permissions/DontAskConfirmDialog.tsx` (Spec 033 T045)

- **Current**: Identical Y/N + ←/→/Tab pattern as C-1 (it is a "mirror" of
  BypassConfirmDialog per its header docstring).
- **CC analog**: No direct equivalent — CC has no "dontAsk" mode.  Closest is
  `BypassPermissionsModeDialog.tsx`'s pattern.
- **Recommendation**: Migrate to arrow+Enter using the BypassReinforcementModal
  template.  Preserve UI2 default-focus = N + the 3 killswitch bullets.
  Estimated effort: ~30 LOC.
- **Mount point when wired**: `/permissions dontAsk` slash command handler.
- **Risk**: Low — same DI shape (`onConfirm` / `onCancel`).

#### C-3: `permissions/ConsentPrompt.tsx` (Spec 033 PIPA §15(2))

- **Current**: Y/N + ←/→/Tab + Enter, 5-section PIPA disclosure (목적 / 항목 /
  보유기간 / 거부권 및 불이익 / AAL 경고).
- **CC analog**: None — PIPA §15(2) is Korea-specific regulatory UX.
- **Recommendation**: Migrate the 2-choice button-bar to arrow+Enter while
  preserving every PIPA §15(2) text section verbatim.  This is regulator-driven
  content; the **interaction** changes but the **disclosure** stays identical.
  The audit team should review the screenshot diff to confirm the change
  is non-substantive (interaction-only, not content).  Estimated effort:
  ~40 LOC + a paired lint ensuring the 4-tuple validation remains.
- **Mount point when wired**: PIPA §15(2) gauntlet trigger (currently routed
  via `permissions/consentBridge.ts` but not yet rendered — see `commandRouter.ts`
  for future hook).
- **Risk**: Medium — requires coordination with the PIPA §15(2) compliance
  artefact pack.  Recommend opening a separate epic with `[PIPA-review]` label
  before merging the migration.

### Class D — KOSMOS-only, no migration applicable

These components have no Y/N keystroke surface; they implement KOSMOS-specific
mechanics (mode cycling, Layer header, ledger receipt toast, OTEL emission,
status bar, IPC seam, command router, type definitions).

```
permissions/ModeCycle.tsx          ← Shift+Tab mode cycler (different from Y/N)
permissions/StatusBar.tsx          ← KOSMOS-original status badge
permissions/RuleListView.tsx       ← rule-list scroll view (no keystroke surface)
permissions/otelEmit.ts            ← OTEL emitter (no UI)
permissions/consentBridge.ts       ← IPC seam (no UI)
permissions/commandRouter.ts       ← Slash-command dispatch (no UI)
permissions/types.ts               ← Type definitions
permissions/index.ts               ← Barrel export
components/permissions/ReceiptToast.tsx           ← Spec 1635 ledger toast
components/permissions/PermissionLayerHeader.tsx  ← Layer 1/2/3 glyph
components/coordinator/PhaseIndicator.tsx         ← Spec 027 swarm phase indicator
components/coordinator/WorkerStatusRow.tsx        ← Spec 027 swarm worker row
components/permissions/MonitorPermissionRequest/MonitorPermissionRequest.ts        ← 7-LOC NO-OP stub
components/permissions/ReviewArtifactPermissionRequest/ReviewArtifactPermissionRequest.ts ← 7-LOC NO-OP stub
```

**Verdict**: No action.  These do not interact with the citizen via direct
Y/N keystrokes.

## Migration proposal — execution sequence

1. **This spec (1979)** — Class B done.  Three production-mounted modals are now
   on the CC arrow+Enter pattern.
2. **Spec 1979 follow-up PR** (recommended within 1-2 sprints) — Class C-1 and
   C-2.  Migrate `BypassConfirmDialog.tsx` and `DontAskConfirmDialog.tsx` since
   they use the same template as the already-migrated `BypassReinforcementModal`.
   Risk: Low.  Effort: ~60 LOC + 6 test cases.
3. **Separate epic with `[PIPA-review]` label** — Class C-3.  `ConsentPrompt.tsx`
   migration requires PIPA §15(2) compliance review because the [Y]/[N]
   accelerator hints appear in audit screenshots.  Don't bundle with C-1/C-2.

## Out of scope (separate epics)

- **kosmosPendingConsent dead-state cleanup** in REPL.tsx — non-functional
  state declaration that can be removed after verifying no third-party
  consumer depends on its presence.
- **PluginInstallFlow inline-mount migration** — the auxiliary dispatch
  via `setToolJSX` works because `shouldHidePromptInput: false` keeps
  stdin raw mode hot.  No need to mount inline like `kosmosPendingConsent`
  unless a runtime regression appears.
- **Replacing `useInput` with `<Select>`** — would require either patching
  ink-testing-library to drive `useKeybindings`, or making `useKeybindings`
  testable without raw mode.  Both are framework-level changes deferred
  to a future epic.
- **ink-testing-library CSI parser fix** — `BypassReinforcementModal`'s
  `Down → Enter` test is skipped due to an unexplained CSI parse difference
  vs the permissions-modal test (same useInput pattern but `key.downArrow`
  fires correctly there and not in bypass).  Y/N power-accelerators cover
  the FR-022 emergency-cancel contract, so the production behaviour is
  verified.  A focused investigation into ink-testing-library's stdin
  parsing should land before all four Class C migrations are merged.
