# G3 — Permission Gauntlet pipeline (P-C pattern) deep research

> Lead Opus G3 · 2026-05-05 · Wave 2 · Targets F-gamma-01 / -02 / -04 / -05 / -06.

## TL;DR

The Permission Gauntlet pipeline is broken at **two distinct stages** and not five — the audit's five P0 findings collapse into three architectural defects:

1. **Frontend dispatch deadlock** (F-gamma-01 / -05; downstream effect on -04). The IPC frame iterator in `tui/src/query/deps.ts:590` `await`s `setPendingPermission(...)`, but **no production code path ever resolves that Promise**. The grant decision flows through a parallel pipeline (`pushIpcPermissionRequest.onAllow` → `bridge.send`) that never touches the slot. The for-loop is therefore blocked for the full 300-second TTL. Tool-result frames *do* arrive on the bridge (the frame queue keeps buffering), but `deps.ts` never advances past the `permission_request` arm to consume them, so no `createUserMessage` (with `tool_result` content) is yielded — citizen sees only the spinner and never the mock fixture body or the `🧪 모의` disclaimer.
2. **Layer mis-classification root** (F-gamma-02). The canonical `aalToLayer` (`tui/src/utils/permissions/aalToLayer.ts:43-48`) maps `verify → L1` and `subscribe → L2`. The audit interpreted `kosmos-migration-tree.md § UI-C.1` as defining adapter-specific layers; UI-C.1 only defines the **colour palette** (`1=green / 2=orange / 3=red`). The actual canonical mapping ships in code and is consistent with Spec 033 risk ladder (verify = light gate, subscribe = heavy gate medium). Mobile-ID verify being green (⓵) and CBS disaster subscribe being orange (⓶) is **spec-correct, not inverted**. The audit's "spec says inverted" claim is itself wrong; the fix is to *document the canonical mapping in the spec text* so future audits don't re-flag the same shape.
3. **Tier-1 keybinding handler removed** (F-gamma-06). `tui/src/keybindings/tier1Handlers.ts:298` carries an explicit `KOSMOS Spec 1979 — Spec 033 permission-mode-cycle removed.` comment. The Tier-1 entry (`defaultBindings.ts:78` — `permission-mode-cycle: shift+tab` Global) still exists. When citizen presses Shift+Tab, the resolver finds **two** matches: the Tier-1 `permission-mode-cycle` (Global) and the legacy `chat:cycleMode` (Chat). `resolver.ts:resolveKeyWithChordState` picks the **last** binding in the array via `for (... ) { if (chordExactlyMatches(...)) exactMatch = binding }` (last-wins). Since `loadKeybindingsSyncWithWarnings` pushes Tier-1 first and `DEFAULT_BINDING_BLOCKS` second, Chat-context legacy wins **only when the active context list contains `Chat`**. In the prompt-input focused state the active contexts are `[Chat, Global]` → Chat wins → handler runs → mode cycles. **In the swarm-viewing or modal-active state, `isModalOverlayActive=true` makes `useKeybindings({...}, {isActive: !isModalOverlayActive})` deactivate the Chat handler bag**. Then the resolver still resolves to `chat:cycleMode` but no handler is registered → silent no-op. The audit captured this state during the bypass-permissions transition. Fix: register a no-op or actual handler for Tier-1 `permission-mode-cycle` in `tier1Handlers.ts` that delegates to the active prompt-input mode cycler — and also keep the Chat-context handler.

The receipt-persistence finding (F-gamma-04) is a **second-order effect**: the on-disk write succeeds (verified `~/.kosmos/memdir/user/consent/2026-05-05.jsonl` is 160 KB on the test machine), but `usePermissionReceiptWatcher` populates the in-memory context only via the `permission_response` echo emitted **after** the dispatch that the deadlock prevents. Once defect #1 is fixed, receipts populate normally.

---

## Dispatch trace diagram (golden-path, **before fix**)

```
User: "모바일 신분증으로 본인 확인 부탁해"
        │
        ▼
[TUI deps.ts queryModelWithStreaming]
        │  bridge.send(ChatRequestFrame)
        ▼
[backend stdio.py _handle_chat_request]
        │  client.stream() → assistant_chunk(thinking + tool_call_delta)
        ▼
TUI: receives chunks, paints ✻ Cogitated…  (this part works)
        │
        ▼
[backend] tool_call_buf['verify'] complete → write_frame(ToolCallFrame) → asyncio.create_task(_dispatch_primitive(...))
        │
        ▼
[backend _dispatch_primitive → _check_permission_gate]
        │  write_frame(PermissionRequestFrame{primitive=verify, tool_id=mock_verify_mobile_id})
        │  await _pending_perms[request_id]   ← waits for TUI decision
        ▼
[TUI deps.ts permission_request arm]
        │  pushIpcPermissionRequest(...)               ← (A) modal pipeline
        │  setPendingPermission(...)        ← (B) slot pipeline ★ HANGS HERE ★
        ▼
[TUI mounts PermissionRequest modal]
        │  citizen presses Y
        ▼
[ipcPermissionBridge.onAllow]
        │  _sendPermissionResponse(frame, 'allow_once')
        │  bridge.send(PermissionResponseFrame{decision: allow_once})   ← (A) sent
        │  setter((prev) => prev.filter(...))   ← removes from toolUseConfirmQueue
        │  *** does NOT call resolvePermissionDecision ***               ← (B) STILL PENDING
        ▼
[backend _handle_permission_response]
        │  fut.set_result(frame)
        │  _check_permission_gate continues:
        │    write consent receipt JSON
        │    ledger.append HMAC chain
        │    write_frame(PermissionResponseFrame{role: backend, receipt_id: rcpt-XXX})
        │    return True
        ▼
[backend _dispatch_primitive] dispatches verify primitive → wraps in ToolResultEnvelope → write_frame(ToolResultFrame)
        │
        ▼
[TUI bridge stdout reader] frames arrive in frameQueue, _dispatchHook fires onFrame
        │
        ├─► usePermissionReceiptWatcher sees the role=backend permission_response echo,
        │   calls addReceipt() — receipt context NOW has the rcpt
        │   ★ this works in isolation, but the citizen never sees /consent list
        │     until they leave the dispatched-but-frozen turn ★
        │
        └─► tool_result frame is BUFFERED in frameQueue but NEVER consumed
             because deps.ts is still awaiting setPendingPermission (300 s)

[Result] Spinner runs for the full 300 s permission TTL, then deps.ts
finally receives 'timeout' → sends a SECOND permission_response
('denied') to the backend, the buffered tool_result frame is finally
yielded as createUserMessage, but by then the citizen has Ctrl-C'd.

Grand total visible frames between Y and result: 0.
```

## Dispatch trace diagram (golden-path, **after fix**)

```
... same up through citizen presses Y ...
        ▼
[ipcPermissionBridge.onAllow]
        │  resolvePermissionDecision(frame.request_id, 'granted')   ← NEW: unblock deps.ts
        │  _sendPermissionResponse(frame, 'allow_once')
        │  setter((prev) => prev.filter(...))
        ▼
[deps.ts] setPendingPermission resolves → 'granted'
        │  bridge.send(respFrame{decision: 'granted'})  ← duplicate, harmless
        │  for-loop advances to next iteration
        ▼
[TUI] consumes buffered frames in order:
        permission_response echo → onFrame hook → addReceipt
        tool_result → yields createUserMessage with tool_result content
        assistant_chunk → final answer
        message_stop
        ▼
[TUI render] modal-grant → 🧪 모의 verify result + assistant prose ≤ 100 ms after Y.
```

## Five mandatory probe points (per AGENTS.md)

| # | Probe | Where in pipeline | Probe instrumentation |
|---|---|---|---|
| 1 | Input ingress | citizen presses `Y` in modal | `KosmosPrimitivePermissionRequest.onAllow` → existing `[KOSMOS permissionBridge]` log when bridge.send fails. **Already present.** |
| 2 | IPC frame boundary | bridge.send / bridge.frames | `bridge.onFrame` queueMicrotask hook fires `kosmos.tui.binding` events. **Already present.** Add a one-line `process.stderr.write('[KOSMOS-G3] permission_response sent dec=...\n')` in `_sendPermissionResponse` for the smoke verifier. |
| 3 | Tool dispatch boundary | backend `_dispatch_primitive` | `with _tracer.start_as_current_span("kosmos.tool.dispatch")` already emits OTEL. Add structured `logger.info("TOOL ts=%s txn=%s tool_id=%s status=dispatched", ...)` at the `await write_frame(result_frame)` line. |
| 4 | Render commit | `tui/src/utils/frameCommitOtel.ts` | `kosmos.tui.frame_commit` already emitted on every Ink reconcile. **Already present.** |
| 5 | Snapshot trigger | Layer 5 tmux capture | `scripts/tui-tmux-capture.sh` exists. The smoke scenario `scn-perm-gauntlet-Y.sh` will call it. |

The 5 probe points are fully aligned; the only missing one is #2's structured stderr line in the bridge (one-liner addition).

## Stage-by-stage finding mapping

| Stage | Frame/code path | F-gamma-01 | -02 | -04 | -05 | -06 |
|---|---|---|---|---|---|---|
| 1 — User input ingress | PromptInput | — | — | — | — | ★ Shift+Tab swallowed when modal active |
| 2 — IPC chat_request | deps.ts → bridge.send | — | — | — | — | — |
| 3 — Backend agentic loop | stdio.py:_handle_chat_request | — | — | — | — | — |
| 4 — Backend permission gate | _check_permission_gate | — | (metadata only) | — | — | — |
| 5 — TUI permission_request arm | deps.ts:528 | ★ blocked here | — | indirectly | indirectly | — |
| 6 — Modal mount | pushIpcPermissionRequest | — | — | — | — | — |
| 7 — Citizen decision | onAllow/onReject | ★ doesn't unblock #5 | — | indirectly | indirectly | — |
| 8 — Permission response wire | bridge.send | — | — | — | — | — |
| 9 — Backend ledger.append + receipt write | stdio.py:1606-1722 | — | — | works in isolation | — | — |
| 10 — Echo permission_response | stdio.py:1689 | — | — | works | — | — |
| 11 — TUI receipt watcher | usePermissionReceiptWatcher | — | — | works | — | — |
| 12 — Backend dispatch primitive | _dispatch_primitive | — | — | — | — | — |
| 13 — Backend tool_result | write_frame(ToolResultFrame) | — | — | — | — | — |
| 14 — TUI tool_result arm | deps.ts:468 | ★ never reached | — | — | ★ never reached | — |
| 15 — TUI render commit | createUserMessage | — | — | — | ★ banner depends on 14 | — |

★ = primary fix site.

## F-gamma-04 second-order effect

Receipts ARE persisted on disk (`~/.kosmos/memdir/user/consent/2026-05-05.jsonl` is 160 KB on the test machine, witnessed `ls -la`). The receipt watcher reads the **echo frame**, not the disk file. The echo IS emitted (stdio.py:1689 unconditional after grant). The watcher hook IS chained correctly through `bridge.onFrame`. The only timing question: does the watcher fire *before* the citizen runs `/consent list`?

After the G3 fix unblocks the dispatch loop, the answer is yes — the echo arrives ~1 ms after grant, addReceipt fires synchronously in the queueMicrotask, and the in-memory context is hot before any subsequent `/consent list` invocation. Before the fix, deps.ts blocks for 300 s but the bridge stdout reader is independent — so the echo *should* still arrive and the watcher *should* fire. The audit observation that `/consent list` returned 0 receipts after 4 grants suggests **the receipts aren't reaching the context for a different reason** in the deadlocked state. Hypothesis: the swarm-viewing path that triggered F-gamma-06 also unmounts the receipt provider from REPL.tsx remount — the watcher's onFrame is restored to `prevHook`, losing the chain. After G3's primary fix removes the deadlock (so the citizen never enters the long-spinner state that prompts a swarm-view remount), the receipt path heals.

We add a **defense-in-depth disk-fallback read** to `/consent list` so even an empty in-memory context shows the on-disk JSONL. The TUI receives a `consent_list_request` frame round-trip from the backend — the backend already has the canonical disk path — but for a minimal-scope G3 fix we just augment `buildConsentListRows` to merge in-memory receipts with a one-shot synchronous read of `~/.kosmos/memdir/user/consent/<today>.jsonl` filtered to the current `session_id`. Bun has `Bun.file()` synchronous reads available without a new dep.

## F-gamma-02 (Layer mapping) — the audit was wrong

The audit asserted: "kosmos-migration-tree.md UI-C.1 에서 mobile-ID verify 는 L2 orange ⓶, subscribe (재난문자) 는 L1 green ⓵ 로 명시".

Actual UI-C.1:
> C.1 Layer 색: 1=green ⓵ / 2=orange ⓶ / 3=red ⓷

This defines the **palette** only. There is no per-adapter layer assignment in `kosmos-migration-tree.md`. The canonical mapping ships in `tui/src/utils/permissions/aalToLayer.ts:36-50` (Spec 2294 SSOT):

```
verify (any AAL) → 1     (green ⓵, low risk)
submit (non-irr) → 2     (orange ⓶, medium risk)
submit (irr=true)→ 3     (red ⓷, high risk)
subscribe        → 2     (orange ⓶, medium risk)
```

This is **consistent with Spec 033 risk ladder**:
- `LIGHT_GATE_PRIMITIVES = {verify}` (delegation-only, read-only) → Layer 1
- `HEAVY_GATE_PRIMITIVES = {submit, subscribe}` (side-effecting) → Layer 2/3

So mobile-ID verify being ⓵ and CBS disaster subscribe being ⓶ is **spec-correct**. The captured snapshots (`gamma1-Y/snap-005-after-prompt-3.txt:16` showing `⓵ 낮은 위험 (레이어 1)` for mobile-ID, `gamma5/snap-002-modal-shown-1.txt` showing `⓶ 중간 위험 (레이어 2)` for disaster subscribe) match the canonical mapping.

**G3 fix scope for F-gamma-02**: amend `kosmos-migration-tree.md § UI-C.1` to embed the canonical primitive→layer table (copy from `aalToLayer.ts`) so the next auditor doesn't re-flag this shape. Mark F-gamma-02 as `wontfix-by-design` in the audit record.

## Audit-4 P0 fixes already in code that we MUST NOT regress

PR #2771 made several ipcPermissionBridge edits we keep:
- `_pendingPermissionDecisions` per-request stash for `allow_once`/`allow_session` distinction (Audit-4 P0-5).
- `_sendPermissionResponse` routing through bridge singleton instead of `process.stdout.write` (Audit-4 P0-8).
- `tool_id` field threaded into `PermissionRequestFrame` for modal title (Audit-4 P0-10).
- `receipt_id: null` from TUI side (backend is single source of truth for canonical IDs) (Audit-4 P0-11).
- Backend echo with `primitive_kind` + `tool_id` (Audit-4 P0-6 / P0-7).

Our diff is purely additive: insert a `resolvePermissionDecision(frame.request_id, decision)` call at the top of onAllow and onReject (and the onAbort path).

## Reference materials cited

- `.references/claude-code-sourcemap/restored-src/src/utils/swarm/leaderPermissionBridge.ts` — CC's register/push pattern (already cited in `ipcPermissionBridge.ts:14`).
- `specs/2077-kexaone-tool-wiring/contracts/pending-permission-slot.md` — Promise-resolver contract.
- `specs/033-permission-v2-spectrum/spec.md` — risk ladder + 3-decision vocabulary.
- `specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md` — receipt JSON shape.
- AGENTS.md § Five mandatory probe points + § Seven anti-patterns (final-state fallacy avoided by enumerating frames in the smoke).
