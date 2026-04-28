# Contract — `plugin_op` backend dispatcher routing

**Surface**: `src/kosmos/ipc/stdio.py` if-elif dispatch chain (line ~1675) → `src/kosmos/ipc/plugin_op_dispatcher.py` (NEW).
**Trigger**: TUI emits `PluginOpFrame` with `op="request"`.
**Purpose**: Route incoming citizen-initiated plugin lifecycle operations to backend handlers; emit progress + complete frames per the IPC envelope.

---

## Inbound frame shape (TUI → backend)

```json
{
  "kind": "plugin_op",
  "version": "1.0",
  "session_id": "<ULID>",
  "correlation_id": "<UUID4>",
  "ts": "2026-04-28T12:00:00.000Z",
  "role": "tui",
  "op": "request",
  "request_op": "install" | "uninstall" | "list",
  "name": "<catalog-name>",        // required when request_op ∈ {install, uninstall}
  "requested_version": "1.0.0",    // optional, install only
  "dry_run": false                 // optional, install only
}
```

Validation enforced by `frame_schema.py:_v_plugin_op_shape` at frame deserialization. Dispatcher does not re-validate.

---

## Dispatch logic — `stdio.py:1675` if-elif extension

Insert after the `session_event` branch:

```python
elif frame.kind == "plugin_op":
    try:
        await handle_plugin_op_request(
            frame,
            registry=_ensure_tool_registry(),
            executor=_ensure_tool_executor(),
            write_frame=write_frame,
            consent_bridge=IPCConsentBridge(
                write_frame=write_frame,
                pending_perms=_pending_perms,
                session_id=frame.session_id,
            ),
            session_id=frame.session_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("plugin_op handler failed: %s", exc)
        err = ErrorFrame(
            session_id=frame.session_id,
            correlation_id=frame.correlation_id or str(uuid.uuid4()),
            role="backend",
            ts=_utcnow(),
            kind="error",
            code="plugin_op_error",
            message=f"plugin_op handler failed: {exc}",
            details={"request_op": getattr(frame, "request_op", None)},
        )
        await write_frame(err)
```

The `ErrorFrame` fanout follows the existing pattern from `chat_request` / `tool_result` / `permission_response` arms.

---

## Outbound frame sequence — install (request_op="install")

```
PluginOpFrame { op=request, request_op=install, name=<n>, correlation_id=<C> }
                                ↓
PluginOpFrame { op=progress, progress_phase=1, progress_message_ko=📡..., progress_message_en=Catalog query..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=2, progress_message_ko=📦..., progress_message_en=Bundle download..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=3, progress_message_ko=🔐..., progress_message_en=SLSA verification..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=4, progress_message_ko=🧪..., progress_message_en=Manifest validation..., correlation_id=<C> }
                                ↓
                     [IPCConsentBridge round-trip]
PermissionRequestFrame { request_id=<P>, layer=<L>, processes_pii=<B>, trustee_org_name=<T>, correlation_id=<C+P> }
PermissionResponseFrame ← (TUI → backend, decision ∈ {allow_once, allow_session, deny})
                                ↓
PluginOpFrame { op=progress, progress_phase=5, progress_message_ko=📝..., progress_message_en=Consent..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=6, progress_message_ko=🔄..., progress_message_en=Register + BM25..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=7, progress_message_ko=📜..., progress_message_en=Receipt..., correlation_id=<C> }
                                ↓
PluginOpFrame { op=complete, result=success, exit_code=0, receipt_id=rcpt-<id>, correlation_id=<C> }
```

**Total frame count** (happy path): 1 inbound + 7 progress + 1 permission_request + 1 permission_response (inbound) + 1 complete = 10 frames + 1 inbound.

**Failure paths** (early termination):
- Catalog miss after phase 1: `complete { exit_code=1, error_kind=catalog_miss }`. No further progress frames.
- Bundle SHA mismatch after phase 2: `complete { exit_code=2, error_kind=bundle_sha_mismatch }`.
- SLSA failure after phase 3: `complete { exit_code=3, error_kind=<slsa-failure-subkind> }`.
- Manifest invalid after phase 4: `complete { exit_code=4, error_kind=manifest_invalid }`.
- Consent denied / timeout at phase 5: `complete { exit_code=5, error_kind=consent_rejected | consent_timeout }`. Phase 5 progress frame still emits before the complete (citizen sees "📝 동의 확인…" then immediate failure).
- Register/BM25 failure at phase 6: `complete { exit_code=6, error_kind=register_failed }`. Install root rolled back.
- Receipt write failure at phase 7: `complete { exit_code=6, error_kind=receipt_write_failed }`. Install root rolled back.

---

## Outbound frame sequence — uninstall (request_op="uninstall")

```
PluginOpFrame { op=request, request_op=uninstall, name=<n>, correlation_id=<C> }
                                ↓
PluginOpFrame { op=progress, progress_phase=1, progress_message_ko=📋 등록 해제..., progress_message_en=Deregister..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=2, progress_message_ko=📁 디렉터리 제거..., progress_message_en=Remove install dir..., correlation_id=<C> }
PluginOpFrame { op=progress, progress_phase=3, progress_message_ko=📜 영수증 기록..., progress_message_en=Uninstall receipt..., correlation_id=<C> }
                                ↓
PluginOpFrame { op=complete, result=success, exit_code=0, receipt_id=rcpt-<id>, correlation_id=<C> }
```

**Phase count**: 3 (vs 7 for install). The uninstall progress frames re-use the same `PluginOpFrame` shape but with `progress_phase ∈ {1, 2, 3}`. The shape validator allows phases 1-7; the citizen-facing message text simply omits phases 4-7 for uninstalls.

**Failure paths**:
- Plugin not installed: `complete { exit_code=8, error_kind=not_installed }`. Idempotent fallback — log warning, return success exit_code=0 instead of 8 (per data-model.md E3 invariant).
- I/O error during rmtree: `complete { exit_code=6, error_kind=rmtree_failed }`.
- Receipt write failure: `complete { exit_code=6, error_kind=receipt_write_failed }`.

---

## Outbound frame sequence — list (request_op="list")

```
PluginOpFrame { op=request, request_op=list, correlation_id=<C> }
                                ↓
PluginOpFrame { op=complete, result=success, exit_code=0, correlation_id=<C> }
```

**Phase count**: 0 progress frames. Single `complete` frame.

**Body**: The `complete` frame itself does not carry a list body (PluginOpFrame has no payload field beyond receipt_id). To return the entries, two options:

**Option A — extend PluginOpFrame** with an optional `list_body: list[PluginListEntry] | None` field. **Rejected** per R-3/R-4 verdict (no schema change).

**Option B (chosen)** — emit the list payload via a sibling `payload_start` / `payload_delta` / `payload_end` frame triplet (existing Spec 032 large-payload mechanism at `frame_schema.py:680-740`). The `complete` frame's `correlation_id` matches the payload's `correlation_id`; TUI reassembles.

**Sub-optimal but correct**: The list response is small (≤ 100 plugins typically). Use a single `payload_delta` frame with the entire JSON-encoded list. The TUI's existing payload-reassembly path in `tui/src/ipc/codec.ts` handles this without modification.

**PluginListEntry shape** (JSON in payload_delta body):

```json
{
  "plugin_id": "seoul_subway",
  "name": "seoul-subway",
  "version": "1.0.0",
  "tier": "live",
  "permission_layer": 1,
  "processes_pii": false,
  "trustee_org_name": null,
  "is_active": true,
  "install_timestamp_iso": "2026-04-28T12:00:00.000Z",
  "description_ko": "서울 지하철 도착 정보 조회",
  "description_en": "Seoul subway arrival lookup",
  "search_hint_ko": "지하철 도착 시간 강남역",
  "search_hint_en": "subway arrival time station"
}
```

Source of truth: `PluginManifest` fields + `ToolRegistry.is_active(tool_id)` for the runtime active flag.

---

## Concurrency contract

- The dispatcher is invoked from `_reader_loop`'s `_handle_frame` callback. Each frame handler is awaited individually.
- For multiple simultaneous `plugin_op_request` frames (e.g., parallel installs), each runs in its own dispatcher invocation. The fcntl-flocked `_allocate_consent_position` in `installer.py:348-369` already serialises receipt position assignment.
- Concurrent installs of the **same plugin** are detected via `install_root / plugin_id` existence: the installer's phase 6 detects `if plugin_dir.exists(): shutil.rmtree(plugin_dir)` (line 686-689). This is a "last writer wins" semantic; for this Epic, we accept it. A follow-up Epic could add a per-plugin lock.

---

## Tools[] propagation contract (R-6 verdict)

After a successful `plugin_op_complete:install:success`, the TUI sets a session-scoped flag `pluginsModifiedThisSession=true` (in `tui/src/ipc/bridgeSingleton.ts` or equivalent). On the next `ChatRequestFrame` build:
- If the flag is true → omit `frame.tools` (set to `[]`).
- Backend's existing fallback at `stdio.py:1192-1195` rebuilds `llm_tools` from `registry.export_core_tools_openai()` which now includes the new plugin.
- TUI resets the flag after one use.

This is causally race-free: `register_plugin_adapter` updates the registry BEFORE `plugin_op_complete:success` is emitted (phase 6 → phase 7 → phase 8 ordering in `installer.py`). No timer-based waiting needed.

---

## Negative-path tests

1. `plugin_op_request` with `request_op="install"` and missing `name` → Pydantic rejects at frame deserialize; dispatcher never invoked.
2. `plugin_op_request` with unknown `request_op` value → Pydantic rejects.
3. Backend dispatcher raises during install → ErrorFrame emitted; `plugin_op_complete` NOT emitted (caller's responsibility to handle either ErrorFrame or complete; TUI must support both terminal arms).
4. TUI sends two `plugin_op_request:install` for the same plugin in flight → both proceed; second one rmtrees the first's partially extracted dir. Last-writer-wins; documented edge case in spec.md.

---

## OTEL spans

| Span name | Parent | Attributes |
|---|---|---|
| `kosmos.plugin.install` | `kosmos.session` | `kosmos.plugin.id`, `kosmos.plugin.tier`, `kosmos.plugin.permission_layer`, `kosmos.plugin.slsa_verification` |
| `kosmos.plugin.uninstall` | `kosmos.session` | `kosmos.plugin.id` |
| `kosmos.plugin.list` | `kosmos.session` | (none — count of returned entries logged at info level) |

Each span emits `kosmos.ipc.frame` child spans for every progress + complete frame, per existing Spec 032 OTEL conventions.

---

## Citations

- `src/kosmos/ipc/stdio.py:1675-1751` (existing dispatch chain)
- `src/kosmos/ipc/frame_schema.py:776-936` (PluginOpFrame schema)
- `src/kosmos/plugins/installer.py:install_plugin` (8-phase impl)
- `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md` (canonical phase text)
- `specs/032-ipc-stdio-hardening/` (envelope conventions)
- Epic #1978 (ChatRequestFrame.tools[] auto-build path)
