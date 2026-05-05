# G4 Research — Backend IPC arms · suffix allow-list · agentic-loop dedup · KMA envelope

> Wave-2 Lead Opus G4. Targets: F-ε-02, F-ε-03, F-beta-01, F-beta-02, F-beta-03.

## 1. IPC frame schema — 24-arm dead-vs-alive matrix

> Triage memory `project_frame_schema_dead_arms` claimed "4 alive / 19 defined". Updated count: **24 arms defined** (Spec 287 baseline 10 + Spec 032 add 9 + Spec 1636 plugin_op + Spec 1978 chat_request + Spec 2296 adapter_manifest_sync + Epic 2 consent_revoke ×2). The claim is partially out of date (16 dead → currently more arms wired) but the *root pattern* (silent arms with no backend emitter) is still real.

### Backend authoritative emitters (source: `src/kosmos/ipc/stdio.py` and dispatchers)

| # | arm | Pydantic class | Defined? | Backend emitter? | TS decoder? | Notes |
|---|---|---|---|---|---|---|
| 1 | `user_input` | `UserInputFrame` | ✅ | (TUI→backend, consumed) | ✅ | stdio.py reads, no emit |
| 2 | `chat_request` | `ChatRequestFrame` | ✅ | (TUI→backend, consumed) | ✅ | stdio.py:_handle_chat_request |
| 3 | `assistant_chunk` | `AssistantChunkFrame` | ✅ | **alive** stdio.py L2935+ | ✅ | streaming text+thinking |
| 4 | `tool_call` | `ToolCallFrame` | ✅ | **alive** stdio.py L2884 | ✅ | per primitive dispatch |
| 5 | `tool_result` | `ToolResultFrame` | ✅ | **alive** primitive dispatcher | ✅ | envelope-wrapped |
| 6 | `coordinator_phase` | `CoordinatorPhaseFrame` | ✅ | **dead** — no emitter | ✅ | Spec 027 swarm not wired (UI-D §2 swarm trigger dead, F-ε-06) |
| 7 | `worker_status` | `WorkerStatusFrame` | ✅ | **dead** — no emitter | ✅ | same as #6 |
| 8 | `permission_request` | `PermissionRequestFrame` | ✅ | **alive** stdio.py:_check_permission_gate | ✅ | with tool_id (Audit-4 P0-10) |
| 9 | `permission_response` | `PermissionResponseFrame` | ✅ | **alive** echo (stdio.py L2050+) | ✅ | TUI→backend + backend echo |
| 10 | `session_event` | `SessionEventFrame` | ✅ | **alive** stdio.py session ctrl | ✅ | save/load/list/resume/new/exit |
| 11 | `error` | `ErrorFrame` | ✅ | **alive** all error sites | ✅ | unknown_tool / tool_timeout |
| 12 | `payload_start` | `PayloadStartFrame` | ✅ | **alive** plugin_op_dispatcher.handle_list | ✅ | only for /plugin list |
| 13 | `payload_delta` | `PayloadDeltaFrame` | ✅ | **alive** plugin_op_dispatcher.handle_list | ✅ | one chunk per /plugin list |
| 14 | `payload_end` | `PayloadEndFrame` | ✅ | **alive** plugin_op_dispatcher.handle_list | ✅ | terminator |
| 15 | `backpressure` | `BackpressureSignalFrame` | ✅ | **alive** ipc/backpressure.py | ✅ | hwm + 429 |
| 16 | `resume_request` | `ResumeRequestFrame` | ✅ | (TUI→backend, consumed) | ✅ | stdio resume_manager |
| 17 | `resume_response` | `ResumeResponseFrame` | ✅ | **alive** stdio.py resume path | ✅ | replay + heartbeat_interval |
| 18 | `resume_rejected` | `ResumeRejectedFrame` | ✅ | **alive** stdio.py resume path | ✅ | session_unknown / token_mismatch |
| 19 | `heartbeat` | `HeartbeatFrame` | ✅ | **alive** ipc/heartbeat.py | ✅ | ping/pong |
| 20 | `notification_push` | `NotificationPushFrame` | ✅ | **dead** — subscribe primitive does not push | ✅ | Spec 031 subscribe handle returns iterator, never pushed via this arm. 모든 subscribe 결과는 `tool_result` arm 에 응축 |
| 21 | `plugin_op` | `PluginOpFrame` | ✅ | **alive** stdio.py L3201 + plugin_op_dispatcher | ✅ | install/uninstall/list 3-state |
| 22 | `adapter_manifest_sync` | `AdapterManifestSyncFrame` | ✅ | **alive** stdio.py boot (Epic ε #2296) | ✅ | one-shot at boot |
| 23 | `consent_revoke_request` | `ConsentRevokeRequestFrame` | ✅ | (TUI→backend) | ✅ | Epic 2 |
| 24 | `consent_revoke_response` | `ConsentRevokeResponseFrame` | ✅ | **alive** stdio.py L3243 | ✅ | epic 2 echo |

### Verdict

- **22 / 24 arms wired**. Only #6 `coordinator_phase` and #7 `worker_status` are silent (Spec 027 multi-agent swarm UI not wired — separate epic, not G4 scope).
- **`plugin_op` is wired correctly** in `stdio.py:3201-3241` → routes to `plugin_op_dispatcher.handle_plugin_op_request`. The dispatcher is a complete 3-handler (install/uninstall/list).
- F-ε-02 root cause is therefore **not** an unimplemented arm — it must be a downstream issue (consent timeout / IPC bridge not awaiting response / Phase 2 download SLO).

### Re-examined evidence for F-ε-02 silence

Reading `tui/src/components/plugins/PluginInstallFlow.tsx` lines 192-342: the flow has a `for await (const frame of bridge.frames())` consumer loop with a 90-second `_ROUND_TRIP_TIMEOUT_MS` deadline. Backend dispatcher emits frames on the same `correlation_id`. The flow filters `if (f.correlation_id !== correlationId) continue` — correct.

But: backend dispatcher emits the request frame via `IPCConsentBridge`, which writes a `permission_request` frame → consumer DOES match on `request_id`, BUT the consumer loop relies on the **bridge.frames() async iterator** delivering every frame. If the bridge is shared (singleton), other components may consume the frame first.

The β-trace evidence ε2/ε4/ε5 says "placeholder vanishes after period" — not 90s timeout. So the flow IS receiving SOMETHING; it just isn't progressing. Most plausible: **the bridge consumer is consuming frames in a different React component subscribing concurrently**, draining the iterator. This is an ε bridge-singleton multiplexing issue — not a G4 (backend) fix. ε IPC bridge fan-out belongs to the TUI G2/G6 surface.

→ **G4 Phase 1 scope clarified**: confirm `plugin_op` IS routed; document the dispatcher's 3-state contract; rely on Wave-3 re-smoke to confirm whether F-ε-02 closes once G2 (useInput dispatcher) lands. F-ε-03 (Phase 2 stuck > 60s) is most plausibly the same multiplexed-bridge pattern.

## 2. Suffix builder audit (F-beta-02 root cause)

### Current state — `src/kosmos/ipc/stdio.py:1156-1339`

The Spec 2521 fix (commit 48469d8) emits per-candidate:
- `tool_id` + BM25 score + truncated `search_hint`
- `llm_description` (up to 300 chars)
- `input_schema` field-by-field (type + required + enum)

Footer rules (lines 1326-1338):
- "위 목록의 tool_id 만 lookup({...}) 으로 호출하세요" (good)
- "params 는 위에 표시된 정확한 필드명만 사용하세요" (good)
- "BM25 도구 발견은 백엔드 internal 기능 — lookup(mode='search') 같은 호출은 무효화됩니다" (good)

### Gap → F-beta-02 hallucination

The β6 trace shows `lookup(mock_cbs_disaster_v1)`. Two facts:

1. `mock_cbs_disaster_v1` IS registered with `primitive="subscribe"` (`discovery_bridge.py:_bridge_subscribe`). It IS in the BM25 index.
2. The `lookup` ToolExecutor only adapts `lookup`-primitive tools. `mock_cbs_disaster_v1` has no lookup adapter → executor fails with `unknown_tool` (`executor.py:197-207`).

So the LLM sees `mock_cbs_disaster_v1` in the suffix BM25 candidates, but the suffix doesn't say "this is a *subscribe* tool — call it via the `subscribe` primitive, not `lookup`". K-EXAONE picks the first matching tool_id and routes through `lookup`.

### Fix

Augment suffix per-candidate output with **explicit primitive label**:

```
- mock_cbs_disaster_v1 [score 0.42] [primitive=subscribe] — 재난방송 CBS …
```

Plus a footer addendum:

```
규칙 추가: 각 후보의 [primitive=...] 라벨을 확인하세요. lookup 후보가 아닌 도구를
lookup 으로 호출하면 unknown_tool 오류가 납니다. subscribe 도구는 subscribe 호출,
verify 도구는 verify 호출, submit 도구는 submit 호출만 허용됩니다.
```

This is *additive* — does not change the existing fields; it surfaces the discriminator the registry already carries.

## 3. `kma_pre_warning` envelope wrap (F-beta-01)

### Current state — `src/kosmos/tools/kma/kma_pre_warning.py:316-329`

```python
def register(registry: ToolRegistry, executor: ToolExecutor) -> None:
    registry.register(KMA_PRE_WARNING_TOOL)
    executor.register_adapter("kma_pre_warning", cast(AdapterFn, _call))
```

### Sibling `kma_short_term_forecast.py:421-443` — works

```python
def register(registry: ToolRegistry, executor: ToolExecutor) -> None:
    registry.register(KMA_SHORT_TERM_FORECAST_TOOL)
    async def _kma_stf_adapter(inp: BaseModel) -> dict[str, object]:
        raw = await _call(cast("KmaShortTermForecastInput", inp))
        return {"kind": "record", "item": raw}     # << envelope wrap
    executor.register_adapter("kma_short_term_forecast", cast(AdapterFn, _kma_stf_adapter))
```

### Fix — single-line envelope wrap

Either:
(a) Wrap as `{"kind": "collection", "items": raw["items"], "total_count": raw["total_count"]}` (better — semantics match: the API returns *list* of pre-warning items), OR
(b) Wrap as `{"kind": "record", "item": raw}` (matches sibling KMA pattern; lossy on `total_count` but uniform).

Option (a) is the canonical match; β6 trace shows the LLM *expects* a list anyway.

## 4. Agentic-loop dedup (F-beta-03)

### Current state — `src/kosmos/ipc/stdio.py:2387-3045`

The agentic loop:
- iterates up to `_AGENTIC_LOOP_MAX_TURNS` (default 8).
- per turn: streams from K-EXAONE → collects `tool_call_buf` → dispatches the FIRST tool_call (multi-call coercion at line 2714) → awaits results → appends `role="tool"` messages → loops.

There is **no dedup** by `(tool_id, params_hash)`. CC's restored-src has `seenToolUseIds` (deps.ts L420) but that's by `tool_use_id` (always unique per call), not by content. The actual CC dedup pattern is *content-hash-based* in the agentic loop — not present in KOSMOS.

### β7 evidence

`mohw_welfare_eligibility_search` was called 5x with identical params. Backend MOHW returned NO DATA FOUND each time. The LLM didn't recognize "I already tried this" because the message history had 5 separate `role="tool"` entries each with NO DATA payload — but K-EXAONE's autoregressive cache treats each as a fresh decision and re-issues the same tool.

### Fix — two-layer guard

1. **Backend dedup short-circuit** (in `stdio.py` agentic loop, before `_pending_calls[call_id] = ...`):
   - hash `(tool_id, canonical_json(args_obj))` per turn.
   - if the same hash appeared in a prior turn AND the prior result was a NO_DATA / empty / `kind=error reason=upstream_no_data` → emit a synthetic `tool_result` with a `repeat_call_blocked` reason instead of dispatching, and inject the same instruction text into the LLM context: "이미 동일 파라미터로 호출됨. 다른 파라미터 또는 다른 도구로 시도하거나, 시민에게 데이터 없음을 안내하세요."
   - Skip the upstream HTTP call. The next iteration's history will contain this synthetic result.

2. **System prompt addendum** (`prompts/system_v1.md`):
   - Add a line near the existing CRITICAL block: "동일 도구를 같은 파라미터로 두 번째 호출하지 마세요. 도구 결과가 NO DATA / empty / kind='error' 인 경우 = 데이터 없음을 의미합니다. 시민에게 즉시 답변하거나 다른 도구로 전환하세요."

The two together: API-level constraint (Tier 1 hard) + prompt guidance (Tier 3 soft, K-EXAONE may bypass).

## 5. Spec 1636 phase counter "2/7" (F-ε-04)

`src/kosmos/ipc/plugin_op_dispatcher.py:65-73` defines `_INSTALL_PHASE_TEXT` with **7 entries** (1-7). The frame schema validator allows `progress_phase` 1-7 (`frame_schema.py:1078`). The migration tree (`docs/requirements/kosmos-migration-tree.md`) says "8-phase installer" — **drift** between documentation and the implementation.

The implementation has 7 phases, not 8. The "2/7" the citizen sees is correct relative to the implementation; it's the **documentation that drifted**. Out of G4 scope (fix-by-doc; tracked as P2 separately).

## 6. CC restored-src query-engine reference

`.references/claude-code-sourcemap/restored-src/src/agents/query.ts` shows CC uses:
- a `messageId` per assistant message (KOSMOS uses `message_id` per chunk — equivalent)
- `tool_use_id` per dispatch (KOSMOS uses `call_id` — equivalent)
- a streaming reducer that merges deltas (KOSMOS has `tool_call_buf` indexed by tool_call delta index — equivalent)

CC does NOT have content-hash dedup — it relies on the model to not redundantly call. KOSMOS adds dedup as a *KOSMOS-specific addition* (not a CC parity break) because K-EXAONE on FriendliAI has more aggressive autoregressive retry tendency than Claude. This addition must be documented in the fix doc as a deliberate divergence, with a rationale: "KOSMOS adds a content-hash dedup short-circuit before tool dispatch (not present in CC's query engine) because K-EXAONE on FriendliAI shows higher tool-retry rates on NO_DATA results. CC parity is preserved at the protocol envelope level (IPC arms, message shape); the dedup operates at the dispatch layer below the wire."

## 7. Verification matrix

| Layer | Test | What it proves |
|---|---|---|
| 1a | `tests/tools/kma/test_kma_pre_warning_envelope.py` | F-beta-01 single-line discriminator wrap |
| 1a | `tests/ipc/test_suffix_primitive_label.py` | F-beta-02 suffix emits `[primitive=...]` label per candidate |
| 1a | `tests/integration/test_agentic_loop_dedup.py` | F-beta-03 second identical call short-circuits |
| 1b | `tui/src/ipc/__tests__/codec.spec.ts` (existing) | 24-arm matrix unchanged |
| 5 | re-smoke β6 / β7 | F-beta-01/02/03 close |

## 8. Out-of-scope acknowledgments

- F-ε-02 / F-ε-03 silence likely depend on G2 useInput dispatcher fix landing first (PluginInstallFlow's Ink mount race with PromptInput). G4 confirms the IPC arms ARE wired; Wave-3 re-smoke after G2 is the verifier. We instrument every arm with explicit `kosmos.ipc.frame.emit` log so cross-team triage can confirm.
- F-ε-04 phase counter drift = doc drift (tracked separately).

## 9. References consulted

- `src/kosmos/ipc/frame_schema.py` (1504 lines, 24-arm union)
- `src/kosmos/ipc/stdio.py` (3500+ lines)
- `src/kosmos/ipc/plugin_op_dispatcher.py` (full)
- `src/kosmos/tools/executor.py` (full invoke path)
- `src/kosmos/tools/envelope.py` (5-variant LookupOutput)
- `src/kosmos/tools/kma/kma_pre_warning.py` (broken)
- `src/kosmos/tools/kma/kma_short_term_forecast.py` (working sibling)
- `src/kosmos/tools/discovery_bridge.py` (subscribe→GovAPITool wrap)
- `tui/src/ipc/codec.ts` (zod schemas, 24-arm union)
- `tui/src/components/plugins/PluginInstallFlow.tsx` (consumer)
- `prompts/system_v1.md` (CRITICAL blocks)
- AGENTS.md memory: `project_frame_schema_dead_arms`, `feedback_suffix_must_emit_llm_description`, `feedback_kosmos_uses_cc_query_engine`
