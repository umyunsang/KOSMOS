# Phase 1 Data Model: Plugin DX TUI integration

**Feature**: 1979-plugin-dx-tui-integration
**Date**: 2026-04-28
**Inputs**: spec.md, plan.md, research.md (V1/V2 + R-1..R-6 verdicts)

## Scope of this document

This Epic adds **zero new persistent entities**. All Pydantic v2 schemas are reused as-is from upstream specs:
- `PluginOpFrame` (Spec 1636 + Spec 032) — already at `src/kosmos/ipc/frame_schema.py:780-936`
- `PluginManifest` (Spec 1636) — already at `src/kosmos/plugins/manifest_schema.py`
- `PluginConsentReceipt` (Spec 1636) — already at `src/kosmos/plugins/installer.py:153-181`
- `CatalogIndex` / `CatalogEntry` / `CatalogVersion` (Spec 1636) — already at `src/kosmos/plugins/installer.py:91-134`
- `ChatRequestFrame.tools[]` (Epic #1978) — already populated via `stdio.py:1182-1196`
- `PermissionRequestFrame` / `PermissionResponseFrame` (Spec 1978 + Spec 033) — reused for IPCConsentBridge

This document describes the **runtime entities** (function groups + class boundaries) introduced by this Epic. None of these are persisted; they live in process memory and are reconstructed on backend boot.

---

## E1 — `PluginOpDispatcher` (backend-side function group)

**Module**: `src/kosmos/ipc/plugin_op_dispatcher.py` (NEW)

**Purpose**: Pattern-match incoming `PluginOpFrame` frames with `op="request"` and route to install / uninstall / list handlers. Bridge `installer.py:install_plugin()` phase progression to `plugin_op_progress` frame emission.

**Public API**:

```python
async def handle_plugin_op_request(
    frame: PluginOpFrame,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    write_frame: Callable[[IPCFrame], Awaitable[None]],
    consent_bridge: IPCConsentBridge,
    session_id: str,
) -> None:
    """Route a plugin_op:request frame to the appropriate handler.

    Validates frame.request_op ∈ {install, uninstall, list}. Dispatches:
      - install   → handle_install(...)
      - uninstall → handle_uninstall(...)
      - list      → handle_list(...)

    Each handler emits its own plugin_op_progress and plugin_op_complete frames
    via write_frame. Errors are caught and surfaced as plugin_op_complete
    with result="failure" + error_kind + appropriate exit_code.
    """


async def handle_install(
    frame: PluginOpFrame,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    write_frame: Callable[[IPCFrame], Awaitable[None]],
    consent_bridge: IPCConsentBridge,
) -> None:
    """Phase-1..7 progress emission + install_plugin invocation."""


async def handle_uninstall(
    frame: PluginOpFrame,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    write_frame: Callable[[IPCFrame], Awaitable[None]],
) -> None:
    """rmtree install_root/<plugin_id>/ + ToolRegistry.deregister + BM25 rebuild + uninstall consent receipt."""


async def handle_list(
    frame: PluginOpFrame,
    *,
    registry: ToolRegistry,
    write_frame: Callable[[IPCFrame], Awaitable[None]],
) -> None:
    """Enumerate installed plugins from registry; emit single plugin_op_complete with body."""
```

**Validation rules**:
- `frame.kind == "plugin_op"` and `frame.op == "request"` (enforced by Pydantic discriminator + `_v_plugin_op_shape`)
- `frame.request_op ∈ {install, uninstall, list}` (enforced by Pydantic Literal)
- `frame.name` required when `request_op ∈ {install, uninstall}` (enforced by `_v_plugin_op_shape`)

**State**: Stateless — every call reconstructs from frame + injected dependencies.

**OTEL**: Each handler opens a child span `kosmos.plugin.<install|uninstall|list>` under the existing `kosmos.session` root. `kosmos.plugin.id` attribute populated from `frame.name` (install/uninstall) or absent (list).

---

## E2 — `IPCConsentBridge` (backend-side adapter)

**Module**: `src/kosmos/plugins/consent_bridge.py` (NEW)

**Purpose**: Replace `installer.py:_default_consent_prompt` (current "deny by default" stub at lines 219-229) with an IPC round-trip that emits a `permission_request` frame to the TUI and awaits the citizen's `permission_response`.

**Public API**:

```python
class IPCConsentBridge:
    """Wraps installer.py's consent_prompt callable signature with an IPC round-trip.

    The signature matches installer.ConsentPrompt:
        Callable[[CatalogEntry, CatalogVersion, PluginManifest], bool]

    Implementation:
      - Build PermissionRequestFrame from manifest (layer, processes_pii, trustee_org_name)
      - emit via write_frame
      - await asyncio.wait_for(_pending_response_future, timeout=60.0)
      - on TimeoutError → log warning, return False (denial)
      - on permission_response.decision == "allow_once" / "allow_session" → True
      - on "deny" → False
    """

    def __init__(
        self,
        *,
        write_frame: Callable[[IPCFrame], Awaitable[None]],
        pending_perms: dict[str, asyncio.Future[Any]],
        session_id: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        ...

    def __call__(
        self,
        entry: CatalogEntry,
        version: CatalogVersion,
        manifest: PluginManifest,
    ) -> bool:
        """Synchronous interface (matches installer.ConsentPrompt).

        Internally schedules an asyncio task and waits for it via
        asyncio.run_until_complete on the running loop. The dispatcher
        invokes this through asyncio.to_thread so install_plugin's
        synchronous flow keeps working unchanged.
        """
```

**Validation rules**:
- Bridge is created per dispatcher invocation; never cached across requests (reuses pending_perms dict from stdio.py — Spec 1978 D2 invariant).
- `request_id` for the permission frame is a fresh UUID4; the bridge owns it; the response future resolves on matching ID.
- 60s timeout (R-2 verdict). Configurable via constructor for tests.

**State**: Per-request future stored in `_pending_perms` dict (existing Spec 1978 infrastructure at `stdio.py:521`).

**OTEL**: Inherits the dispatcher's `kosmos.plugin.install` span. Adds attribute `kosmos.permission.decision` ∈ {`allow_once`, `allow_session`, `deny`, `timeout`} on completion.

---

## E3 — `uninstall_plugin` function

**Module**: `src/kosmos/plugins/uninstall.py` (NEW)

**Purpose**: Mirror `installer.py:install_plugin()` for the uninstall direction. Idempotent — calling twice does not error.

**Public API**:

```python
@dataclass(frozen=True, slots=True)
class UninstallResult:
    exit_code: int
    plugin_id: str
    receipt_id: str | None
    error_kind: str | None
    error_message: str | None


def uninstall_plugin(
    plugin_id: str,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    progress_emitter: Callable[[int, str, str], Awaitable[None]] | None = None,
) -> UninstallResult:
    """Reverse of install_plugin.

    Phases (mirrored from contracts/plugin-install.cli.md but inverted):
      1. 📋 등록 해제  — registry.deregister(tool_id) + BM25 rebuild
      2. 📁 설치 디렉터리 제거  — rmtree(install_root / plugin_id)
      3. 📜 동의 영수증 기록  — append plugin_uninstall PluginConsentReceipt

    Exit codes (3 phases → simpler table):
      0  Success
      6  I/O error during rmtree or registry deregister
      8  Plugin not installed (idempotent → exit_code=0 in this case but log warning)
    """
```

**Validation rules**:
- `plugin_id` MUST match the regex `^[a-z][a-z0-9_]*$` (mirrors `CatalogEntry.plugin_id` constraint).
- Idempotent: calling on a non-installed plugin returns exit_code=0 with warning log.
- Audit ledger position monotonically advances on each uninstall (reuses `_allocate_consent_position` flock).

**State**: Reads `~/.kosmos/memdir/user/plugins/<plugin_id>/` (Spec 1636 install_root). Writes `~/.kosmos/memdir/user/consent/<receipt_id>.json` (Spec 1636 + Spec 035 ledger).

**OTEL**: Span `kosmos.plugin.uninstall` carrying `kosmos.plugin.id` attribute.

---

## E4 — `ToolRegistry._inactive` shadow set

**Module**: `src/kosmos/tools/registry.py` (MODIFIED)

**Purpose**: In-memory enable/disable state for tools (R-3/R-4 verdict — backend support reserved; not exposed via IPC in this Epic).

**Field addition**:

```python
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, GovAPITool] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._inactive: set[str] = set()      # NEW
        # ... existing init ...
```

**Method addition**:

```python
def set_active(self, tool_id: str, active: bool) -> None:
    """Mark tool active or inactive. Active tools surface in BM25 + LLM tools[];
    inactive tools stay registered (consent receipt + install root preserved)
    but are filtered from discovery + dispatch.
    """
    if tool_id not in self._tools:
        raise UnknownToolError(tool_id)
    if active:
        self._inactive.discard(tool_id)
    else:
        self._inactive.add(tool_id)
    # Rebuild BM25 corpus to reflect new active set.
    corpus = {
        tid: t.search_hint
        for tid, t in self._tools.items()
        if tid not in self._inactive
    }
    self._retriever.rebuild(corpus)


def is_active(self, tool_id: str) -> bool:
    """Return True iff tool is registered AND not in _inactive."""
    return tool_id in self._tools and tool_id not in self._inactive
```

**Modifications to existing methods**:
- `register()` (line 205): No change — newly registered tools start active. `_inactive` defaults to empty set.
- `deregister()` if it exists, else add: removes from both `_tools` and `_inactive` (full removal).
- `core_tools()` / `situational_tools()` / `all_tools()`: filter `_inactive` from result.
- `to_openai_tool()` / `export_core_tools_openai()`: filter `_inactive` from result.
- BM25 corpus rebuild in `register()` (line 317): use the same filter.

**Validation rules**:
- `_inactive` is in-memory only; not persisted.
- Boot rebuilds `_inactive = set()`. To persist disable state across restarts, a follow-up Epic adds a manifest extension or sidecar.
- Idempotent: `set_active(id, False)` twice is a no-op the second time.

**State**: Per-process. Lost on restart.

**OTEL**: No new spans (set_active is a sync method called rarely — once per UI toggle).

---

## E5 — `CitizenPluginStoreSession` (TUI-side React state)

**Module**: `tui/src/commands/plugins.ts` (MODIFIED — currently a one-shot env-var read at lines 32-51)

**Purpose**: Subscribe to `plugin_op_complete` frames carrying list payloads; populate `PluginEntry[]` for the existing `PluginBrowser.tsx` (Spec 1635 T065).

**Public API** (TS):

```typescript
export type PluginEntry = {
  id: string;
  name: string;
  version: string;
  description_ko: string;
  description_en: string;
  isActive: boolean;
  // NEW (additive — backwards compatible with Spec 1635 T065)
  tier: 'live' | 'mock';
  layer: 1 | 2 | 3;
  trustee_org_name: string | null;
  install_timestamp_iso: string;
};


export type PluginsCommandResult = {
  plugins: PluginEntry[];
};


export async function executePlugins(
  args: CommandHandlerArgs,
): Promise<PluginsCommandResult> {
  // Phase E.1: emit kosmos.ui.surface=plugins (FR-037 — preserved)
  emitSurfaceActivation('plugins');

  // Phase E.2: round-trip plugin_op_request:list → plugin_op_complete
  if (!args.sendPluginOp || !args.awaitPluginOpComplete) {
    return { plugins: [] };
  }
  const correlationId = crypto.randomUUID();
  args.sendPluginOp({
    kind: 'plugin_op',
    op: 'request',
    request_op: 'list',
    correlation_id: correlationId,
    /* envelope fields ... */
  });
  const completeFrame = await args.awaitPluginOpComplete(correlationId);
  // Phase E.3: parse complete frame → PluginEntry[]
  // (complete frame body carries entries; data-model contract in
  //  contracts/citizen-plugin-store.md)
  return { plugins: parsePluginListBody(completeFrame) };
}
```

**Validation rules**:
- `correlationId` is a fresh UUID4 per browser open.
- If the list round-trip fails (timeout, error frame), surface a Korean error and return empty list.
- The browser is not blocked while the round-trip runs; an "조회 중…" placeholder is rendered (existing PluginBrowser empty-state line at line 126 — extend with a loading variant).

**State**: Component-scoped. Re-fetched on each `/plugins` invocation.

**OTEL**: TUI does not emit OTEL directly; the round-trip's `kosmos.plugin.list` span lives on the backend (E1.handle_list).

---

## Entity relationships

```
                        ┌──────────────┐
                        │ TUI: REPL    │
                        │ /plugin      │ (singular — install/uninstall)
                        │ /plugins     │ (plural — browser)
                        └──────┬───────┘
                               │
                  plugin_op    ▼
                  (request)
                  ┌────────────────────┐
                  │ tui/src/ipc/       │
                  │ bridge.ts          │
                  └──────┬─────────────┘
                         │  stdio JSONL
                         ▼
              ┌─────────────────────────┐
              │ src/kosmos/ipc/         │
              │ stdio.py:1675 dispatch  │
              │   if frame.kind ==      │
              │   "plugin_op":          │
              │     PluginOpDispatcher  │
              └─────┬───────────────────┘
                    │
        ┌───────────┼─────────────┐
        ▼           ▼             ▼
   handle_install  handle_      handle_list
        │          uninstall      │
        │              │          │
        │              │          ▼ enumerate registry._tools
        ▼              ▼
 install_plugin   uninstall_plugin
   (Spec 1636)        (NEW E3)
   uses            uses
   IPCConsentBridge  registry.deregister
   (NEW E2)
        │              │
        ▼              ▼
   ToolRegistry.register / .deregister
   ToolRegistry._inactive (E4 reserved)
        │
        ▼
   plugin_op_progress / plugin_op_complete
   frames written via write_frame
        │
        ▼
   TUI consumes frames via bridge.ts → React state
   PluginBrowser renders PluginEntry[] (Spec 1635 T065)
```

---

## State transitions

### Install state machine

```
[catalog_query]     →  📡 progress(phase=1)
[bundle_download]   →  📦 progress(phase=2)
[slsa_verify]       →  🔐 progress(phase=3)
[manifest_validate] →  🧪 progress(phase=4)
[await_consent]     →  📝 progress(phase=5)  ← IPCConsentBridge round-trip (60s timeout)
                     │     ├─ allow_once / allow_session  →  continue
                     │     └─ deny / timeout              →  complete(exit=5)
[register_bm25]     →  🔄 progress(phase=6)
[receipt_write]     →  📜 progress(phase=7)
                     ↓
                    complete(result=success, exit=0, receipt_id=rcpt-...)
```

### Uninstall state machine

```
[deregister]        →  📋 progress(phase=1)  ← ToolRegistry.deregister + BM25 rebuild
[rmtree]            →  📁 progress(phase=2)  ← shutil.rmtree(install_root / plugin_id)
[receipt_write]     →  📜 progress(phase=3)  ← uninstall PluginConsentReceipt
                     ↓
                    complete(result=success, exit=0, receipt_id=rcpt-...)
```

### List state machine

Single transition — no progress frames (R-1 + FR-007):

```
[enumerate_registry] → complete(result=success, exit=0, body={entries: [...]})
```

---

## Invariants (preserved across all changes)

- **I-1** (FR-005, ✓): A failed install leaves zero state under `~/.kosmos/memdir/user/plugins/` and `~/.kosmos/memdir/user/consent/`.
- **I-2** (FR-007, ✓): `list` operation MUST emit exactly one `plugin_op_complete` frame; no `plugin_op_progress` frames.
- **I-3** (FR-008, ✓): After successful install, the next `ChatRequestFrame.tools[]` includes the new plugin's `tool_id` (relies on Epic #1978 + R-6 fallback path).
- **I-4** (FR-013, ✓): Revoked consent receipts cause subsequent invocations to fail-closed at the gauntlet (Spec 033 invariant — preserved unchanged).
- **I-5** (Constitution §II, ✓): All new entities default to denial / inactive on edge cases (timeout, error, undefined state).
- **I-6** (FR-023, ✓): Zero new runtime dependencies in `pyproject.toml` or `tui/package.json`.
- **I-7** (Constitution §III, ✓): All new boundaries use existing Pydantic v2 schemas; `Any` is forbidden.
