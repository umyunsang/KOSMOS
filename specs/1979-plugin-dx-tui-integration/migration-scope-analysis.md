# Spec 1979 — Permission UX Migration Scope Analysis

**Date**: 2026-04-28
**Branch**: `fix/1979-fixture-manifest`
**Trigger**: User direction — "yan처리는 코스모스에서 이전에 개발한건데 cc원본 소스는 방식으로 변경해줘 ... 레이어 3도 이전에 개발된건데 cc원본 소스로 변경해주고 수정 및 마이그레이션 스코프를 정밀분석해줘"

## TL;DR

The KOSMOS TUI carried two parallel permission UX implementations that pre-dated
the canonical Claude Code reference port. Both used direct alphabetic-key
shortcuts (`Y/A/N` and `y/n`) — a pattern Claude Code 2.1.88 abandoned in favor
of arrow+Enter selection through the `<Select>` component (`PermissionPrompt.tsx`).

Spec 1979 migrates **both** components to the CC arrow+Enter pattern while
preserving the KOSMOS-original semantics that have no CC analog (Layer 1/2/3
color coding, Layer 3 reinforcement notice, PIPA §26 trustee acknowledgment,
5-min idle timeout, Ctrl-C → `auto_denied_at_cancel`).

| Component | Old pattern | New pattern | Vocabulary preserved |
|---|---|---|---|
| `permissions/PermissionGauntletModal.tsx` (Spec 1635) | `Y/A/N` direct keystrokes | Arrow+Enter, Esc → deny | `allow_once / allow_session / deny / auto_denied_at_cancel / timeout_denied` |
| `coordinator/PermissionGauntletModal.tsx` (Spec 2077) | `y/n` direct keystrokes | Arrow+Enter, Esc → deny | `granted / denied` |
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
tui/tests/components/permissions/permission-gauntlet-modal.test.tsx (rewritten)
tui/tests/components/coordinator/PermissionGauntletModal.test.tsx   (rewritten)
specs/1979-plugin-dx-tui-integration/migration-scope-analysis.md    (this file)
```

## Out of scope (separate epics)

- **kosmosPendingConsent dead-state cleanup** in REPL.tsx — non-functional
  state declaration that can be removed after verifying no third-party
  consumer depends on its presence.
- **PluginInstallFlow inline-mount migration** — the auxiliary dispatch
  via `setToolJSX` works because `shouldHidePromptInput: false` keeps
  stdin raw mode hot. No need to mount inline like `kosmosPendingConsent`
  unless a runtime regression appears.
- **Replacing `useInput` with `<Select>`** — would require either patching
  ink-testing-library to drive `useKeybindings`, or making `useKeybindings`
  testable without raw mode. Both are framework-level changes deferred
  to a future epic.
- **`permissions/ConsentPrompt.tsx` (Spec 033 PIPA §15(2)) migration** —
  out of scope for Spec 1979. This component is regulator-driven UX
  (5-section PIPA §15(2) consent surface) and uses `Y/N + ←/→/Tab` for
  focus toggle. Migration to pure CC arrow+Enter would require coordination
  with the PIPA §15(2) audit team because the [Y]/[N] accelerator hints
  are part of the documented citizen-facing flow. Tracked as a follow-up
  item once the PIPA artefact pack is updated.
