# Contract: Permission bridge protocol — `permission_request` ↔ `permission_response`

**Status**: ACTIVATING (frames defined in Spec 032; emit/consume code added by this Epic)
**Direction**: bidirectional (backend emits `permission_request`, TUI emits `permission_response`)
**Pairs by**: `transaction_id` (UUIDv7)
**Synchronicity**: synchronous request/response per ADR-0002 (60 s timeout, default `deny` on timeout)

## When this fires

The 7-step Permission Gauntlet (Spec 033 / vision.md § L3) runs `PermissionPipeline.evaluate(tool, ctx)` for every tool dispatch. `evaluate` returns one of:

| Decision | Bridge action |
|---|---|
| `ALLOW` | proceed silently — no frame emit |
| `DENY` | inject synthetic `tool_result{error_type="permission_denied"}` — no bridge frame to TUI (denial happens server-side) |
| `ASK` | emit `permission_request`, await `permission_response` — **this contract** |

`ASK` triggers when:
- Step 4 (citizen authentication): citizen lacks required AAL level for the tool
- Step 5 (ministry terms-of-use): no consent receipt yet, OR receipt expired, OR receipt revoked

## `PermissionRequestFrame` (backend → TUI)

| Field | Type | Constraint |
|---|---|---|
| envelope `role` | `"backend"` | E3 |
| envelope `correlation_id` | from originating `ChatRequestFrame` | |
| envelope `transaction_id` | UUIDv7 (NEW) | mandatory (E4) — gauntlet decision is auditable side-effect |
| `kind` | `"permission_request"` | discriminator |
| `primitive_kind` | `Literal["lookup","resolve_location","submit","subscribe","verify"]` | from gating tool |
| `tool_id` | `str` | adapter ID (e.g., `nmc_emergency_search`) |
| `gauntlet_step` | `int` (4 or 5) | which gauntlet step triggered |
| `pii_class` | `Literal["none","public","sensitive","ssn"]` | from adapter `pipa_class` |
| `data_recipient_ministry` | `str` | Korean name + acronym |
| `proposed_arguments` | `dict[str, object]` | what the model will call with |

**Emit timing**: inside `_handle_chat_request` ReAct loop, AFTER the LLM emits a function-call but BEFORE `tool_call` frame goes out.

## `PermissionResponseFrame` (TUI → backend)

| Field | Type | Constraint |
|---|---|---|
| envelope `role` | `"tui"` | E3 |
| envelope `correlation_id` | from originating `ChatRequestFrame` | |
| envelope `transaction_id` | matches `permission_request.transaction_id` | mandatory |
| `kind` | `"permission_response"` | discriminator |
| `decision` | `Literal["allow_once","allow_session","deny"]` | from citizen modal choice |
| `receipt_id` | `str` (UUIDv7) | TUI-generated; backend stores as part of receipt |

## Sequence

```
                            ┌─────────────┐                  ┌──────────────┐
                            │ TUI         │                  │ Backend      │
                            └──────┬──────┘                  └──────┬───────┘
                                   │  ChatRequestFrame              │
                                   │ ─────────────────────────────► │
                                   │                                │
                                   │  AssistantChunkFrame (text)    │  K-EXAONE
                                   │ ◄───────────────────────────── │  decides
                                   │                                │  function_call
                                   │                                │
                                   │                          PermissionPipeline.evaluate()
                                   │                          == ASK
                                   │                                │
                                   │  PermissionRequestFrame        │
                                   │ ◄───────────────────────────── │
                                   │                                │  await pending_perms[txid]
              modal renders        │                                │   (timeout=60s)
              citizen taps "allow_once"                             │
                                   │                                │
                                   │  PermissionResponseFrame       │
                                   │ ─────────────────────────────► │
                                   │                                │  write ConsentReceipt
                                   │                                │  to memdir
                                   │                                │
                                   │                          PermissionPipeline records receipt
                                   │                          decision == allow → proceed
                                   │                                │
                                   │  ToolCallFrame                 │
                                   │ ◄───────────────────────────── │
                                   │   ... (continues per tool-bridge-protocol.md)
```

## Backend implementation skeleton

```python
# stdio.py (sketch — full code in Phase E tasks)
pending_perms: dict[str, asyncio.Future[PermissionResponseFrame]] = {}

async def _check_permission_via_bridge(tool, ctx) -> Decision:
    decision = await pipeline.evaluate(tool, ctx)
    if decision.outcome != "ASK":
        return decision
    # ASK path — bridge to TUI
    txid = uuid.uuid7()
    req = PermissionRequestFrame(
        transaction_id=txid,
        primitive_kind=tool.primitive_kind,
        tool_id=tool.tool_id,
        gauntlet_step=decision.gauntlet_step,
        pii_class=tool.pipa_class,
        data_recipient_ministry=tool.ministry_display,
        proposed_arguments=ctx.proposed_arguments,
    )
    pending_perms[txid] = asyncio.get_running_loop().create_future()
    await write_frame(req)
    try:
        response = await asyncio.wait_for(pending_perms[txid], timeout=60.0)
    except asyncio.TimeoutError:
        # Default deny on timeout (Constitution §II fail-closed)
        await _audit_permission_timeout(txid)
        return Decision(outcome="DENY", reason="permission_timeout")
    finally:
        pending_perms.pop(txid, None)
    # Persist receipt
    await _write_receipt(response)
    if response.decision == "allow_session":
        ctx.session_grants.add(tool.tool_id)
    return Decision(outcome="ALLOW" if response.decision != "deny" else "DENY", receipt_id=response.receipt_id)
```

## TUI implementation skeleton

```typescript
// tui/src/ipc/llmClient.ts (sketch — full in Phase E TUI tasks)
case 'permission_request':
    // Hand off to existing permission modal (CC-fidelity)
    const decision = await showPermissionModal({
        toolId: frame.tool_id,
        ministry: frame.data_recipient_ministry,
        piiClass: frame.pii_class,
        gauntletStep: frame.gauntlet_step,
        proposedArguments: frame.proposed_arguments,
    })
    const response: PermissionResponseFrame = {
        ...envelope(frame),
        kind: 'permission_response',
        role: 'tui',
        transaction_id: frame.transaction_id,
        decision,
        receipt_id: crypto.randomUUID(),
    }
    bridge.send(response)
    break
```

## Receipt persistence

On `decision != "deny"`, backend writes:

```
Path: ~/.kosmos/memdir/user/consent/<receipt_id>.json
Content: {
    "receipt_id": "<uuid>",
    "session_id": "<session>",
    "tool_id": "<tool>",
    "decision": "allow_once" | "allow_session",
    "gauntlet_step": 4 | 5,
    "granted_at": "<iso8601>",
    "revoked_at": null,
}
```

Append-only — no overwrite. Revocation creates `<receipt_id>.json.revoked` marker (Spec 027 pattern).

## Telemetry

Span `kosmos.frame.permission_request` opened on emit, closed on response or timeout. Attributes:

```
kosmos.permission.tool_id        = <tool_id>
kosmos.permission.gauntlet_step  = <int>
kosmos.permission.pii_class      = <enum>
kosmos.permission.decision       = <on close: allow_once | allow_session | deny | timeout>
kosmos.consent.receipt_id        = <on allow: receipt_id>
```

Per Spec 033 attribute names — no new attribute conventions introduced.

## Failure modes

| Mode | Recovery |
|---|---|
| TUI process crashes during modal | backend timeout fires (60 s) → default deny → audit `permission_response_unreachable` |
| Citizen takes > 60 s | timeout → deny → re-ask is up to model (it sees the denial as a tool result and may rephrase) |
| Two concurrent `permission_request`s for same `tool_id` | both kept pending; citizen sees them serialised by frame_seq order in TUI; each gets its own receipt |
| TUI sends `permission_response` for unknown `transaction_id` | backend logs structured warning, drops; no crash |
