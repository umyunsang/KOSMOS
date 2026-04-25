# US2 Integration Notes — Permission Gauntlet

**Author**: Sonnet Teammate #2
**Date**: 2026-04-25
**Tasks completed**: T027 T028 T029 T030 T031 T032 T033 T034 T035 T037 T038

---

## Tasks Completed

| Task | Status | File |
|------|--------|------|
| T027 PermissionLayerHeader | Done | `tui/src/components/permissions/PermissionLayerHeader.tsx` |
| T028 PermissionGauntletModal (3-choice) | Done | `tui/src/components/permissions/PermissionGauntletModal.tsx` |
| T029 ReceiptToast | Done | `tui/src/components/permissions/ReceiptToast.tsx` |
| T030 BypassReinforcementModal | Done | `tui/src/components/permissions/BypassReinforcementModal.tsx` |
| T031 PermissionReceiptContext | Done | `tui/src/context/PermissionReceiptContext.tsx` |
| T032 /consent list | Done | `tui/src/commands/consent.ts` |
| T033 /consent revoke (idempotent) | Done | `tui/src/commands/consent.ts` |
| T034 Ctrl-C handler (auto_denied_at_cancel) | Done | `PermissionGauntletModal.tsx` |
| T035 5-min idle handler (timeout_denied) | Done | `PermissionGauntletModal.tsx` |
| T037 bun:test — component tests | Done | `tui/tests/components/permissions/*.test.tsx` |
| T038 bun:test — consent command tests | Done | `tui/tests/commands/consent.test.ts` |

**Test results**: 45 new tests, 0 failures.

---

## Files Added

- `tui/src/components/permissions/PermissionLayerHeader.tsx` — Layer badge with green/orange/red glyph (FR-016).
- `tui/src/components/permissions/PermissionGauntletModal.tsx` — 3-choice [Y/A/N] modal with Ctrl-C (FR-023) and 5-min timeout (FR-024) fail-closed handlers.
- `tui/src/components/permissions/ReceiptToast.tsx` — Toast surface for `rcpt-<id>` after every decision (FR-018).
- `tui/src/components/permissions/BypassReinforcementModal.tsx` — Extra confirmation before bypassPermissions (FR-022).
- `tui/src/context/PermissionReceiptContext.tsx` — In-session receipt registry with `addReceipt` / `revokeReceipt` / `listReceipts` (FR-018/019).
- `tui/src/commands/consent.ts` — `/consent list` (FR-019) and `/consent revoke` (FR-020/021) logic.
- `tui/tests/components/permissions/layer-header.test.tsx` — 5 tests (FR-016).
- `tui/tests/components/permissions/permission-gauntlet-modal.test.tsx` — 9 tests (FR-015/017/023).
- `tui/tests/components/permissions/receipt-toast.test.tsx` — 4 tests (FR-018).
- `tui/tests/components/permissions/bypass-reinforcement-modal.test.tsx` — 6 tests (FR-022).
- `tui/tests/commands/consent.test.ts` — 21 tests (FR-019/020/021).

---

## IPC Reuse Decisions

The existing `tui/src/permissions/consentBridge.ts` (Spec 033) is the IPC path for all permission writes. The new `PermissionGauntletModal` and `PermissionReceiptContext` are **read/display surfaces only**:

- `PermissionGauntletModal.onDecide(decision)` — caller in REPL.tsx provides this callback; the callback must route the decision through the existing `consentBridge.ts` `resolve()` mechanism (NOT a new IPC frame).
- `PermissionReceiptContext.addReceipt(receipt)` — caller populates this from the IPC frame that returns the `consent_receipt_id` after the backend commits the ledger entry.
- `PermissionReceiptContext.revokeReceipt(id)` — sets `revoked_at` in-memory only for display. The actual ledger append must go through `consentBridge.ts` `_sendDecision()` before calling this.

No new IPC frames were created. The consent sub-protocol (`CONSENT_REQUEST_KIND` / `CONSENT_DECISION_KIND`) in `consentBridge.ts` is reused as-is.

---

## Integration Handoffs for Lead (T036 + T039)

### T036 — Wire Shift+Tab mode cycle into `tui/src/screens/REPL.tsx`

The `BypassReinforcementModal` is ready to render. Lead must:

1. Import `BypassReinforcementModal` from `@/components/permissions/BypassReinforcementModal`.
2. Add a `showBypassConfirm` boolean to the REPL local state (default `false`).
3. In the existing `chat:cycleMode` keybinding handler (already in `defaultBindings.ts` via `MODE_CYCLE_KEY = shift+tab`), detect when the next mode would be `bypassPermissions` (use `computeTier1NextMode` from `tui/src/keybindings/actions/permissionModeCycle.ts`).
4. When `bypassPermissions` is the candidate: set `showBypassConfirm = true` and suspend the mode change.
5. Render `<BypassReinforcementModal onConfirm={applyBypass} onCancel={cancelBypass} />` when `showBypassConfirm === true`.
6. `applyBypass()` calls `setMode('bypassPermissions')` then `setShowBypassConfirm(false)`.
7. `cancelBypass()` just calls `setShowBypassConfirm(false)` — mode reverts to previous.

### T039 — Emit `kosmos.ui.surface=permission_gauntlet` on every modal show

`PermissionGauntletModal` already emits the OTEL attribute in its `useEffect` on mount:

```typescript
useEffect(() => {
  emitSurfaceActivation('permission_gauntlet', { layer })
}, [layer])
```

Lead only needs to ensure the modal is mounted (rendered) via REPL.tsx; no additional OTEL wiring is needed.

### Rendering `PermissionGauntletModal` from REPL.tsx

Lead must:

1. Subscribe to the pending permission request from either:
   - `useCanUseTool()` hook (for the existing coordinator flow), or
   - `awaitConsentRequest()` from `consentBridge.ts` (for the Spec 033 flow).
2. When a request arrives, render `<PermissionGauntletModal layer={...} toolName={...} description={...} onDecide={handleDecide} />`.
3. In `handleDecide(decision)`, call `consentBridge.result.resolve(granted, scope)` with the mapping:
   - `allow_once` → `granted=true, scope='one-shot'`
   - `allow_session` → `granted=true, scope='session'`
   - `deny` / `auto_denied_at_cancel` / `timeout_denied` → `granted=false, scope='one-shot'`
4. After the backend confirms the ledger entry, call `addReceipt(receipt)` on the `PermissionReceiptContext` and show a `<ReceiptToast>` via the notifications queue.

### Wrapping PermissionReceiptProvider

Add `<PermissionReceiptProvider>` to the root component tree (above REPL.tsx) so that `usePermissionReceipts()` is available throughout the app.

---

## Typecheck / Test Results

- `bun run typecheck` — clean (0 errors in the narrowed scope).
- `bun run typecheck:full` — 0 errors in US2 files (pre-existing CC port errors unrelated to US2).
- `bun test tests/components/permissions/` — 24 pass, 0 fail.
- `bun test tests/commands/consent.test.ts` — 21 pass, 0 fail.
- Full `bun test` — 561 pre-existing passes + 45 new passes; all 57 pre-existing failures are from Epic #1633 dead-code invariants (unrelated to US2).
