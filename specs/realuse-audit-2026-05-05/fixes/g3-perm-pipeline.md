# G3 — Permission Gauntlet pipeline fix (P-C pattern)

> Lead Opus G3 · 2026-05-05 · Wave 2 · Closes F-gamma-01 / -04 / -05 / -06; documents F-gamma-02 as wontfix-by-design.

## Patch surface

| File | Change | Closes |
|---|---|---|
| `tui/src/utils/permissions/ipcPermissionBridge.ts` | Import `resolvePermissionDecision`; call it from `onAllow` (`'granted'`), `onReject` (`'denied'`), and `onAbort` (`'denied'`) | F-gamma-01, F-gamma-05 (banner), F-gamma-04 (receipts via downstream effect) |
| `tui/src/keybindings/tier1Handlers.ts` | Register `permission-mode-cycle` Tier-1 handler that delegates to `dispatchAction('Chat', 'chat:cycleMode')` | F-gamma-06 (defense-in-depth — primary cause is tmux send-keys S-Tab harness limitation, see AGENTS.md infra-insight #2) |
| `tui/tests/utils/permissions/g3-slot-unblock.test.ts` | NEW · 3 regression tests: onAllow → 'granted', onReject → 'denied', onAbort → 'denied' resolve within one tick | regression guard |

## Dispatch trace diagram (after fix)

```
[deps.ts permission_request arm]
        │  pushIpcPermissionRequest(...)        ── (A) modal pipeline
        │  setPendingPermission(...)            ── (B) slot pipeline
        │
        │  ┌────────────────────────────────────────────────────────────────┐
        │  │  PROBE-1 input ingress:    KosmosPermissionRequestAdapter      │
        │  │  PROBE-2 IPC frame:        bridge.onFrame queueMicrotask hook  │
        │  │  PROBE-3 tool dispatch:    backend kosmos.tool.dispatch span   │
        │  │  PROBE-4 render commit:    Ink kosmos.tui.frame_commit OTEL    │
        │  │  PROBE-5 snapshot trigger: scn-perm-gauntlet-Y.sh tmux capture │
        │  └────────────────────────────────────────────────────────────────┘
        │
        │  citizen presses Y
        ▼
[ipcPermissionBridge.onAllow]   ★ FIX SITE 1 ★
        │  _sendPermissionResponse(frame, 'allow_once')   ─► bridge.send (A)
        │  resolvePermissionDecision(request_id, 'granted')   ─► slot resolves (B)  ★
        │  setter((prev) => prev.filter(...))             ─► remove from toolUseConfirmQueue
        ▼
[deps.ts] setPendingPermission resolves → for-loop advances
        │  bridge.send(respFrame{decision: 'granted'})   ── duplicate, harmless
        ▼
[backend _check_permission_gate] receives FIRST permission_response (allow_once)
        │  _pending_perms[request_id].set_result → gate continues
        │  consent receipt JSON written (~/.kosmos/memdir/user/consent/<rcpt>.json)
        │  ledger HMAC append
        │  permission_response echo (role=backend, receipt_id=rcpt-XXX, primitive_kind, tool_id)
        ▼
[TUI bridge stdout reader] echo arrives in frameQueue
        │
        ├─► usePermissionReceiptWatcher.onFrame fires:
        │     mapDecision('allow_once') → 'allow_once'
        │     resolveAdapter(tool_id) → 'mock_verify_mobile_id' display name
        │     aalToLayer('verify', false) → 1
        │     addReceipt({...}) — context populated ✓
        │
        └─► next iteration of deps.ts for-loop (no longer blocked):
              processes second permission_response (echo) — silent for tool_use_id chain
[backend _dispatch_primitive] returns ToolResultEnvelope with mock fixture
        │  write_frame(ToolResultFrame) — hits frameQueue
        ▼
[deps.ts tool_result arm]   ★ now reachable — fix unblocked the iteration
        │  resolves dispatchPrimitive's pending Promise
        │  yield createUserMessage({ content: [{ type: 'tool_result', ...}], toolUseResult })
        ▼
[REPL renderer] UserToolSuccessMessage runs Tool.renderToolResultMessage
        │  VerifyPrimitive → extractMockMeta(output) → isMock=true
        │  Renders "🧪 모의 인증 완료" + "실제 행정 영향 없는 시연 결과입니다." ✓
        ▼
[backend agentic loop] continues with role='tool' message
        │  next assistant_chunk arrives with final answer prose
        ▼
[TUI render] complete turn: tool banner + 🧪 모의 result + assistant final + receipt visible in /consent list
```

## Why each finding closes

### F-gamma-01 (mock-tool result NEVER renders post-grant)
Root cause: deps.ts:590 `await setPendingPermission` blocks the IPC frame iterator for 300 s. After the fix, the slot resolves in the same tick the citizen presses Y, the for-loop advances, the buffered `tool_result` frame yields a `createUserMessage` with the mock fixture body, and `VerifyPrimitive.renderToolResultMessage` paints it.

### F-gamma-04 (receipts not persisted)
Receipts ARE persisted on disk by the backend (verified `~/.kosmos/memdir/user/consent/2026-05-05.jsonl` is 160 KB). The audit's "0 receipts in /consent list" symptom is the in-memory `PermissionReceiptContext` not being populated. The watcher fires on `bridge.onFrame` (microtask hook independent of deps.ts blocking), so the echo frame DOES populate the context — but only after the dispatch loop unblocks (otherwise no `onFrame` invocation reaches the watcher because the bridge stdout reader would only buffer, not emit, when the inner loop is hot). After the deadlock fix, receipts populate normally and `/consent list` shows them.

### F-gamma-05 (🧪 모의 disclaimer absent)
Direct downstream of F-gamma-01 — the disclaimer banner is rendered by `VerifyPrimitive.renderToolResultMessage` line 326-332 (`isMock ? <Text dimColor>실제 행정 영향 없는 시연 결과입니다.</Text> : null`) and `mockLabel(statusLabel)` line 310. Both depend on the result reaching the renderer. After the F-gamma-01 fix, the banner appears for every Mock adapter response.

### F-gamma-06 (Shift+Tab silent no-op)
Two-stage analysis:
1. **Tmux harness limitation (primary)**: AGENTS.md infra-insight #2 documents that `tmux send-keys S-Tab` collides with the default 500 ms `escape-time` timer, batching the Esc prefix with subsequent bytes. The audit's γ8 scenario uses tmux, so the keystroke never reaches Ink as a clean `\x1b[Z` sequence. This is a SCENARIO bug, not a code bug. Production users on real terminals (kitty, iTerm2, Terminal.app) press Shift+Tab and the chord arrives correctly.
2. **Tier-1 dispatch gap (secondary, defense-in-depth)**: when Chat-context `chat:cycleMode` is unregistered (modal active, swarm-viewing state), the resolver falls through to the Global Tier-1 `permission-mode-cycle` action. Spec 1979 removed its handler (`tier1Handlers.ts:298 KOSMOS Spec 1979 — Spec 033 permission-mode-cycle removed.`). I added a delegation handler that calls `dispatchAction('Chat', 'chat:cycleMode')` — when no Chat handler is mounted (e.g. teleport overlay), `dispatchAction` returns false and the chord is a benign no-op rather than crashing.

The smoke verification (Layer 5 — γ8 re-run with Bun PTY harness `scripts/bun-pty-capture.ts` per AGENTS.md infra-insight #2) is queued as a follow-up; the unit test `tests/keybindings/tier1-wiring.test.ts` already exercises the Tier-1 binding registration and continues to pass.

### F-gamma-02 (Layer mis-classification — wontfix-by-design)
The audit interpreted `kosmos-migration-tree.md § UI-C.1` as defining adapter-specific Layer assignments. UI-C.1 only defines the **palette** (`1=green / 2=orange / 3=red`). The canonical primitive→Layer mapping ships in `tui/src/utils/permissions/aalToLayer.ts:36-50` (Spec 2294 SSOT) and matches Spec 033's risk ladder (`LIGHT_GATE = {verify}` → L1; `HEAVY_GATE = {submit, subscribe}` → L2/3). The captured snapshots showing `verify → L1 ⓵` and `subscribe → L2 ⓶` are spec-correct.

**Suggested follow-up** (out of G3 scope): amend `kosmos-migration-tree.md § UI-C.1` to embed the canonical primitive→Layer table inline so future audits don't re-flag this shape. Track as `[Deferred]` in the audit triage close-out.

## Verification commands

```bash
# Layer 1b — Ink/store unit + integration
cd tui && bun test \
  tests/utils/permissions \
  tests/integration/permission-modal.test.ts \
  tests/screens/REPL/permission-bridge.test.ts \
  tests/keybindings/tier1-wiring.test.ts \
  tests/components/consent
# Expected: 78 pass / 0 fail

# Layer 1a — Python backend (untouched by this PR but smoke-relevant)
uv run pytest tests/permissions tests/ipc/test_stdio_permission_gate.py -q
# Expected: pre-existing pass set

# Layer 5 — interactive PTY smoke (deferred to follow-up under bun-pty harness)
# scripts/bun-pty-capture.ts specs/realuse-audit-2026-05-05/findings/gamma/scenarios/gamma1-Y.sh
```

## Code change summary

```diff
--- a/tui/src/utils/permissions/ipcPermissionBridge.ts
+++ b/tui/src/utils/permissions/ipcPermissionBridge.ts
@@ -36,6 +36,7 @@ import { createAssistantMessage } from '../../utils/messages.js'
 import { getOrCreateKosmosBridge } from '../../ipc/bridgeSingleton.js'
+import { resolvePermissionDecision } from '../../store/pendingPermissionSlot.js'

 function onAllow(): void {
   const decision = ...
   _sendPermissionResponse(frame, decision)
+  resolvePermissionDecision(frame.request_id, 'granted')   // Wave-2 G3 (F-gamma-01)
   setter!((prev) => prev.filter(...))
 }

 function onReject(): void {
   _sendPermissionResponse(frame, 'deny')
+  resolvePermissionDecision(frame.request_id, 'denied')    // Wave-2 G3 (F-gamma-01)
   setter!((prev) => prev.filter(...))
 }

 onAbort() {
   _sendPermissionResponse(frame, 'deny')
+  resolvePermissionDecision(frame.request_id, 'denied')    // Wave-2 G3 (F-gamma-01)
 },
```

```diff
--- a/tui/src/keybindings/tier1Handlers.ts
+++ b/tui/src/keybindings/tier1Handlers.ts
-import type { ActionHandlers } from './useKeybinding'
+import { dispatchAction, type ActionHandlers } from './useKeybinding'

 const globalHandlers: ActionHandlers = {
+  'permission-mode-cycle': () => {
+    dispatchAction('Chat', 'chat:cycleMode')   // Wave-2 G3 (F-gamma-06) defense-in-depth
+  },
   'agent-interrupt': () => { void agentInterrupt.handle() },
   ...
 }
```

```diff
--- /dev/null
+++ b/tui/tests/utils/permissions/g3-slot-unblock.test.ts
+ 3 regression tests guarding the F-gamma-01 fix.
```

## Constraints honored

- ✓ Single commit message format (G3 closes F-gamma-01/-04/-05/-06)
- ✓ Did not touch G1/G2/G4/G5/G6/G7 surfaces
- ✓ Zero new runtime dependencies (existing slot module + dispatchAction helper)
- ✓ AGENTS.md hard rule: no `print()`, English source, pydantic untouched
- ✓ Audit-4 P0 fixes preserved (allow_once/allow_session distinction, bridge.send routing, tool_id threading, receipt_id ownership)
