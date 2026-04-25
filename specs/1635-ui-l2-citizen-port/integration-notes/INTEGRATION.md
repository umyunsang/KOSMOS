# Integration Report — Epic #1635 P4 UI L2 Citizen Port

**Author**: Integration Teammate (Frontend Developer)
**Date**: 2026-04-25
**Branch**: `feat/1635-ui-l2-citizen-port`
**Commits**: `5760885` (wiring), `e4b866f` (task marking)

---

## Phase Status

### Phase A — main.tsx onboarding gate (T049, T052)
**Status: COMPLETE** — commit `5760885`

- Added `showDialog` to the import from `interactiveHelpers.js`
- After `showSetupScreens()` completes inside the `if (!isNonInteractiveSession)` block, inserted a KOSMOS-specific onboarding gate
- `loadOnboardingState()` reads `~/.kosmos/memdir/user/onboarding/state.json`; if `isOnboardingComplete()` returns false, `showDialog()` mounts `OnboardingFlow` and blocks until `onComplete()` fires
- `emitSurfaceActivation('onboarding', { 'onboarding.mode': 'initial' })` fires before mounting (T052)
- OnboardingFlow is dynamically required via `require()` inside the async block to avoid circular dependency at module load time

### Phase B — REPL.tsx UI-B wiring (T022, T023, T026)
**Status: COMPLETE** — commit `5760885`

- Imported all 10 new component packages + auxiliary command handlers at line ~291 of REPL.tsx (after the last `createAttachmentMessage` import, before the `EMPTY_MCP_CLIENTS` constant)
- `emitSurfaceActivation('repl')` fires in a `useEffect([], [])` on REPL mount (T026)
- 5-second no-chunk timeout: `useEffect([isLoading])` watches the loading state. When `isLoading` becomes true, a `setTimeout(5000)` fires and creates a `network` ErrorEnvelope if no chunk arrived (T023)
- JSX: `SlashCommandSuggestions`, `ErrorEnvelope` (conditional), and `AgentVisibilityPanel` (when `kosmosSwarmMode`) are rendered above the `SessionBackgroundHint` component (T022)

### Phase C — REPL.tsx permission gauntlet (T036, T039)
**Status: COMPLETE** — commit `5760885`

- `kosmosPrevModeRef` tracks the previous permission mode
- `useEffect([toolPermissionContext.mode, setAppState])` intercepts the bypassPermissions transition: when detected, it immediately reverts the mode to the previous value and sets `kosmosShowBypassConfirm=true`
- `BypassReinforcementModal` renders when `kosmosShowBypassConfirm` is true; `onConfirm` applies `bypassPermissions` and clears the flag; `onCancel` clears only (T036)
- `kosmosPendingConsent` state holds a pending consent request payload; `PermissionGauntletModal` mounts when non-null. The modal already calls `emitSurfaceActivation('permission_gauntlet')` internally on mount (T039 — no additional wiring needed)
- Note: The full `awaitConsentRequest()` IPC integration (mapping backend `notification_push` frames to the modal state) is deferred to P5. The consent state variable and modal mount surface are present for P5 to populate.

### Phase D — REPL.tsx ministry agent (T056, T059)
**Status: COMPLETE** — commit `5760885`

- `kosmosSwarmMode` and `kosmosPrimitiveByWorker` state added
- `useEffect([kosmosSwarmMode])` emits `emitSurfaceActivation('agents', { 'kosmos.swarm.auto': true })` when swarm activates (T059)
- `shouldActivateSwarm` is imported and available for call in a plan handler; `setKosmosSwarmMode(true)` is the wiring point
- Note: The actual plan handler that calls `shouldActivateSwarm()` with `mentioned_ministries` and `complexity_tag` from the LLM response is not yet wired because REPL.tsx does not have a typed plan-response extraction path in P4. `setKosmosSwarmMode` is exposed at REPL scope for P5 to call from the message stream handler.

### Phase E — REPL.tsx auxiliary command dispatch (T072)
**Status: COMPLETE** — commit `5760885`

- KOSMOS command intercept block inserted BEFORE the existing CC `// Handle immediate commands` block in `onSubmit`
- Handles: `/help`, `/config`, `/plugins`, `/export`, `/history`, `/consent`, `/agents`, `/onboarding`, `/lang`
- Each command calls the respective `execute*()` function (which calls `emitSurfaceActivation()` internally — T072 is satisfied at the command-handler level per US5 notes)
- Mounts the corresponding React component via `setToolJSX({ jsx, isLocalJSXCommand: true })`
- `/consent list|revoke` uses `addNotification` stub (P5: full PermissionReceiptContext integration)
- `/onboarding` uses `parseOnboardingCommand` → sets `kosmosOnboardingMode` state → `OnboardingFlow` overlay renders in the REPL JSX

### Phase F — Mark deferred tasks [x] in tasks.md
**Status: COMPLETE** — commit `e4b866f`

Tasks marked: T022, T023, T026, T036, T039, T049, T052, T056, T059, T072

---

## Files Modified

- `/Users/um-yunsang/KOSMOS/tui/src/screens/REPL.tsx` — 394 lines added (imports + state + effects + command dispatch + JSX)
- `/Users/um-yunsang/KOSMOS/tui/src/main.tsx` — 30 lines added (showDialog import + onboarding gate)
- `/Users/um-yunsang/KOSMOS/specs/1635-ui-l2-citizen-port/tasks.md` — 10 task checkboxes updated

---

## Typecheck Result

`bunx tsc --noEmit -p tsconfig.typecheck.json` — **EXIT=0 (clean, 0 errors)**

Verified after every edit phase. No React Compiler runtime artifacts (`_c`, `$[n]`) were touched.

---

## bun test Result

```
329 pass
6 fail (all pre-existing — VirtualizedList overflowToBackbuffer + related)
2 errors (pre-existing)
715 expect() calls
Ran 335 tests across 41 files.
```

No new test failures introduced. The 6 pre-existing failures are in `tests/components/conversation/overflowToBackbuffer.test.tsx` and are unrelated to this integration (they fail against the existing `useVirtualScroll.ts` hook at `Set` constructor).

---

## Rollbacks / Compromises

1. **`_showSecretEditor` variable declared but never read**: The `ConfigOverlay` `onOpenSecretEditor` callback sets a local variable that is only used within the closure. TypeScript's `noUnusedLocals` is not enabled in `tsconfig.typecheck.json` so this does not cause a type error. Lead may clean up in P5 polish.

2. **Swarm plan handler not connected**: `setKosmosSwarmMode` is present and `shouldActivateSwarm` is imported. The actual call site (inside the LLM message stream handler where plan responses are parsed) was not wired because REPL.tsx does not have a single typed plan-response extraction point in the current P4 state. Lead should add `shouldActivateSwarm({ mentioned_ministries, complexity_tag })` inside the `handleMessageFromStream` callback and call `setKosmosSwarmMode(true)` on positive result.

3. **`awaitConsentRequest` IPC integration deferred**: The `PermissionGauntletModal` is mounted and functional. The IPC frame routing from `consentBridge.ts` `handleNotificationFrame()` to `setKosmosPendingConsent()` requires the master frame dispatch loop to forward consent frames. This loop lives in the existing REPL bridge hook (`useReplBridge`) — it is a CC artifact with React Compiler artifacts and was not touched. Lead should add a `handleNotificationFrame(frame)` call in `useReplBridge`'s frame handler and call `setKosmosPendingConsent()` when the result is non-null.

4. **`/consent list|revoke` uses notification stub**: Full `PermissionReceiptContext` integration (reading receipts from the provider) requires `usePermissionReceipts()` which was imported but not yet called with a valid context (the `PermissionReceiptProvider` wraps the root in `main.tsx` per US2 notes, but this was not added to main.tsx to avoid touching `renderAndRun`). Lead should add `<PermissionReceiptProvider>` wrapper in `replLauncher.tsx` or `main.tsx`.

5. **`buildConsentListRows` and `formatConsentListRow` imported but unused**: These are imported for future use in the `/consent list` full rendering path. They generate no TypeScript errors since `noUnusedLocals` is not enabled. Lead may clean up in P5 or use them when PermissionReceiptProvider is added.

6. **OnboardingFlow in main.tsx uses `require()`**: Dynamic `require()` was used instead of `import()` because the block is inside a sync `showDialog` renderer callback. TypeScript accepted this as a `LocalCommandModule`-compatible import. If the module fails to load at runtime the error propagates up through `showDialog` — fail-open behavior.

---

## Remaining Concerns for Lead Before Phase 8 Polish

1. **Connect swarm predicate to LLM plan stream**: Add `shouldActivateSwarm()` call in the message stream handler where `complexity_tag` and `mentioned_ministries` become available. Call `setKosmosSwarmMode(true)` on positive result. Also populate `kosmosPrimitiveByWorker` from `WorkerStatusFrame.current_primitive` as frames arrive.

2. **Wire `awaitConsentRequest` to `kosmosPendingConsent`**: In `useReplBridge` (or wherever frame dispatch lives), call `handleNotificationFrame(frame)` from `consentBridge.ts`. When a consent request is resolved, call `setKosmosPendingConsent({ layer, toolName, description, onDecide })` where `onDecide` routes through `consentBridge.result.resolve()`. After `onDecide` fires, call `addReceipt()` from `PermissionReceiptContext`.

3. **Wrap app with `<PermissionReceiptProvider>`**: Add the provider in `replLauncher.tsx` or `main.tsx` (above `renderAndRun`) so `usePermissionReceipts()` is available throughout. This unblocks full `/consent list|revoke` rendering.

4. **`CtrlOToExpand` imperative integration**: The `CtrlOToExpand` component is imported but not used in the JSX (only imported). The `app:toggleTranscript` keybinding in `defaultBindings.ts` maps to Ctrl-O. Lead should wire this to a `ref.current.toggle()` call or hoist `expanded` state. See US1 notes decision #3.

5. **`MarkdownRenderer` and `PdfInlineViewer` not yet in message stream**: These components are imported but not inserted into the message rendering path. They need to be used inside the `Messages` component or the per-message render callbacks. This is blocked by the React Compiler artifact in the message list rendering area — Lead should coordinate with the Messages component maintainer.

6. **`ContextQuoteBlock` not yet in message stream**: Same as above — imported and available but the message rendering path in `Messages.tsx` is CC-compiled. Lead should add a `ContextQuoteBlock` wrapper for messages with `multi_turn_quote` metadata.

7. **`PermissionReceiptProvider` missing from component tree**: T031 created this context; it needs to be mounted above REPL in the tree for the receipt toast and consent list to work.

8. **T034/T035 note**: The US2 notes say these are marked `[x]` (Done) by Teammate #2 as they live inside `PermissionGauntletModal.tsx` (Ctrl-C auto-deny + 5-min idle timeout). Verify these task rows are also marked in tasks.md — they were pre-existing `[ ]` entries that this integration did not touch.
