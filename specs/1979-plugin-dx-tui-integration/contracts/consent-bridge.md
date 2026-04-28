# Contract — IPCConsentBridge: `consent_prompt` IPC round-trip

**Surface**: `src/kosmos/plugins/consent_bridge.py` (NEW) wrapping `src/kosmos/plugins/installer.py:_default_consent_prompt` seam (lines 219-229) at runtime.
**Trigger**: `installer.py:install_plugin()` reaches phase 5 (📝 동의 확인) and calls `consent_prompt(entry, version, manifest)`.
**Purpose**: Replace the current "deny by default" stub with an IPC round-trip that emits a `permission_request` frame and awaits the citizen's `permission_response`. Reuse existing Spec 1978 + Spec 033 permission infrastructure.

---

## Signature compatibility

`installer.py` declares the seam at line 191:

```python
ConsentPrompt = Callable[[CatalogEntry, CatalogVersion, PluginManifest], bool]
```

`IPCConsentBridge` MUST satisfy this signature unchanged. Returning `True` grants consent; `False` denies. Internal implementation may async-await but the external interface stays synchronous (using `asyncio.run_coroutine_threadsafe` or `asyncio.to_thread` to bridge the loop).

---

## Frame sequence

```
[installer.py phase 5 reaches consent_prompt(entry, version, manifest)]
                                ↓
                   [IPCConsentBridge.__call__]
                                ↓
PermissionRequestFrame {
  kind: "permission_request",
  session_id: <S>,
  correlation_id: <C+P>,             # composite — links to plugin_op correlation
  request_id: <P>,                   # fresh UUID4
  role: "backend",
  ts: <now>,
  tool_id: "plugin.<id>.<verb>",
  layer: <manifest.permission_layer>, # 1 | 2 | 3
  processes_pii: <manifest.processes_pii>,
  trustee_org_name: <manifest.pipa_trustee_acknowledgment.trustee_org_name | null>,
  acknowledgment_sha256: <manifest.pipa_trustee_acknowledgment.acknowledgment_sha256 | null>,
  reason_ko: "플러그인 설치 동의: <plugin_id> v<version>",
  reason_en: "Plugin install consent: <plugin_id> v<version>",
  // ... other Spec 033 PermissionRequestFrame fields ...
}
                                ↓
[await asyncio.wait_for(_pending_perms[request_id], timeout=60.0)]
                                ↓
PermissionResponseFrame ← (TUI → backend)
{
  kind: "permission_response",
  request_id: <P>,                   # matches request
  decision: "allow_once" | "allow_session" | "deny",
  receipt_id: <R>,                   # if granted
  // ... Spec 033 fields ...
}
                                ↓
[bridge resolves → True (allow) | False (deny)]
                                ↓
[installer.py phase 5 sees True → continue to phase 6 // False → exit_code=5]
```

---

## Timeout behavior (R-2 verdict)

- 60-second `asyncio.wait_for` budget on the `_pending_perms[request_id]` future.
- On `asyncio.TimeoutError`:
  - Bridge returns `False` (denial — fail-closed per Constitution §II).
  - Bridge logs `WARNING` with `request_id` + plugin name.
  - OTEL attribute `kosmos.permission.decision = "timeout"` on the `kosmos.plugin.install` span.
  - The pending future is cancelled to clean up `_pending_perms`.
- The TUI overlay receives no special timeout frame — it remains responsible for cancelling its own modal if the response window passes.

---

## Layer-specific behavior

The TUI's permission gauntlet (Spec 033 + Spec 1978) renders the consent modal differently per `layer`:

| Layer | Color | Glyph | Modal text additions |
|---|---|---|---|
| 1 | green | ⓵ | Standard "[Y 한번만 / A 세션 자동 / N 거부]" |
| 2 | orange | ⓶ | Standard + display `trustee_org_name` if `processes_pii=true` |
| 3 | red | ⓷ | Standard + display `trustee_org_name` + `acknowledgment_sha256` + secondary confirmation step |

These are existing Spec 033 affordances; the bridge merely populates the source fields from `manifest`.

---

## PIPA §26 trustee acknowledgment (FR-012)

When `manifest.processes_pii == True`:
- The `PermissionRequestFrame` MUST include `trustee_org_name` and `acknowledgment_sha256` from the manifest.
- The TUI MUST render both fields prominently in the modal (existing Spec 1978 / Spec 035 PII consent surface).
- If `trustee_org_name` is `null` (manifest validation should reject this combination — Spec 1636 invariant) the bridge logs an ERROR and denies the request.

---

## Constructor parameters

```python
class IPCConsentBridge:
    def __init__(
        self,
        *,
        write_frame: Callable[[IPCFrame], Awaitable[None]],   # from stdio.py
        pending_perms: dict[str, asyncio.Future[Any]],        # from stdio.py:521
        session_id: str,
        timeout_seconds: float = 60.0,                        # R-2 default
    ) -> None: ...
```

The injection of `write_frame` + `pending_perms` keeps the bridge testable: unit tests inject mock writers and pre-populated futures.

---

## Test seams

Three classes of tests:

### Unit (test_consent_bridge.py)
1. `test_grant_once_returns_true`: pre-populate future with `decision="allow_once"` → bridge returns True.
2. `test_grant_session_returns_true`: pre-populate with `decision="allow_session"` → bridge returns True.
3. `test_deny_returns_false`: `decision="deny"` → bridge returns False.
4. `test_timeout_returns_false`: do not resolve future → after 60s (or shorter test timeout) bridge returns False, OTEL attribute `decision="timeout"` set.
5. `test_pii_includes_acknowledgment`: manifest with `processes_pii=true` → emitted frame carries `acknowledgment_sha256`.
6. `test_layer_3_secondary_confirm`: manifest with `permission_layer=3` → emitted frame triggers Spec 033 layer-3 path (verified via outbound frame inspection).

### Integration (test_install_consent_flow.py)
1. End-to-end: dispatcher receives `plugin_op_request:install` → bridge invoked at phase 5 → simulated TUI sends `permission_response:allow_once` → install completes with success.
2. Denial path: TUI sends `permission_response:deny` → install completes with exit_code=5; install root absent.

### E2E (test_plugin_install_e2e.py — see contracts/e2e-pty-scenario.md)
Exercises the full PTY-driven flow including consent.

---

## Citations

- `src/kosmos/plugins/installer.py:191` (`ConsentPrompt` type alias)
- `src/kosmos/plugins/installer.py:219-229` (`_default_consent_prompt` stub being replaced)
- `src/kosmos/ipc/stdio.py:521` (`_pending_perms` dict — Spec 1978 D2 invariant)
- `src/kosmos/ipc/stdio.py:814` (existing `asyncio.wait_for` permission timeout pattern)
- `specs/033-permission-v2-spectrum/` (PermissionRequestFrame / PermissionResponseFrame shapes)
- `specs/1636-plugin-dx-5tier/contracts/pipa-acknowledgment.md` (canonical PIPA text + hash extraction)
