# Data Model: Permission Pipeline v1

**Spec**: `specs/008-permission-pipeline-v1/spec.md`
**Module**: `src/kosmos/permissions/models.py`

---

## Entity Definitions

### `AccessTier` (Enum)

Maps from `GovAPITool.auth_type` (`Literal["public", "api_key", "oauth"]`) to the permission pipeline's richer type.

| Value | String | Meaning in v1 |
|---|---|---|
| `public` | `"public"` | No auth required; allow unconditionally at step 1 |
| `api_key` | `"api_key"` | `KOSMOS_DATA_GO_KR_API_KEY` must be set and non-empty |
| `authenticated` | `"authenticated"` | Citizen identity verification required; denied in v1 |
| `restricted` | `"restricted"` | Special approval gate; denied in v1 |

**`auth_type` → `AccessTier` mapping table** (in `pipeline.py`, not in models):

| `GovAPITool.auth_type` | `AccessTier` |
|---|---|
| `"public"` | `AccessTier.public` |
| `"api_key"` | `AccessTier.api_key` |
| `"oauth"` | `AccessTier.authenticated` |

---

### `PermissionDecision` (Enum)

| Value | String | Meaning |
|---|---|---|
| `allow` | `"allow"` | Proceed to next step or execute |
| `deny` | `"deny"` | Halt; return error result to query engine |
| `escalate` | `"escalate"` | Treated as `deny` in v1; reserved for v2 human-in-the-loop |

---

### `SessionContext` (Pydantic v2, frozen)

Passed in from the query engine. The pipeline does not create or mutate sessions.

| Field | Type | Default | Description |
|---|---|---|---|
| `session_id` | `str` | required | Unique session identifier for audit trail |
| `citizen_id` | `str \| None` | `None` | Citizen identity; `None` in v1 (no auth yet) |
| `auth_level` | `int` | `0` | Authentication level: 0=anonymous, 1=basic, 2=verified |
| `consented_providers` | `list[str]` | `[]` | Providers for which the citizen has accepted ToS |

---

### `PermissionCheckRequest` (Pydantic v2, frozen)

The single input passed to every step function. Constructed once at `PermissionPipeline.run()` entry and never mutated.

| Field | Type | Default | Description |
|---|---|---|---|
| `tool_id` | `str` | required | Stable tool identifier (e.g., `koroad_accident_search`) |
| `access_tier` | `AccessTier` | required | Mapped from `GovAPITool.auth_type` at pipeline entry |
| `arguments_json` | `str` | required | Raw JSON string of tool arguments (not parsed by pipeline) |
| `session_context` | `SessionContext` | required | Session state from query engine |
| `is_personal_data` | `bool` | required | From `GovAPITool.is_personal_data`; drives bypass-immune checks |
| `is_bypass_mode` | `bool` | `False` | If `True`, bypass-immune rules still apply; warning is emitted |

**Invariants**:
- `arguments_json` is never parsed by the pipeline itself. Step 3 (future) and `ToolExecutor` handle parsing.
- `arguments_json` is never written to logs, error messages, or `AuditLogEntry`.

---

### `PermissionStepResult` (Pydantic v2, frozen)

Returned by every step function (active or stub).

| Field | Type | Default | Description |
|---|---|---|---|
| `decision` | `PermissionDecision` | required | The step's verdict |
| `step` | `int` | required | Step number (1–7) for audit trail clarity |
| `reason` | `str \| None` | `None` | Machine-readable deny reason; `None` on allow |

**Deny reason vocabulary** (step 1 active values):
- `"api_key_not_configured"` — env var absent or empty
- `"citizen_auth_not_implemented"` — `authenticated` tier in v1
- `"tier_restricted_not_implemented"` — `restricted` tier in v1
- `"internal_error"` — unexpected exception in any step
- `"execution_error"` — adapter raised in step 6

---

### `AuditLogEntry` (Pydantic v2, frozen)

Written to `logging.getLogger("kosmos.permissions.audit")` after every invocation.

| Field | Type | Default | Description |
|---|---|---|---|
| `timestamp` | `datetime` | required | UTC timestamp at log time (`datetime.now(UTC)`) |
| `tool_id` | `str` | required | Tool identifier |
| `access_tier` | `AccessTier` | required | Tier at time of call |
| `decision` | `PermissionDecision` | required | Final pipeline decision |
| `step_that_decided` | `int` | required | Which step produced the final decision |
| `outcome` | `Literal["success", "failure", "denied"]` | required | Execution outcome |
| `error_type` | `str \| None` | `None` | Error type string from `ToolResult` on failure |
| `deny_reason` | `str \| None` | `None` | Machine-readable deny reason on denied outcome |
| `session_id` | `str` | required | From `session_context.session_id` |

**Intentionally absent**: `arguments_json`, `citizen_id`, any field that could contain PII. This prevents personal data from appearing in log aggregators (ELK, CloudWatch, Loki).

**Log levels**:
- `outcome == "denied"` → `WARNING`
- `outcome in ("success", "failure")` → `INFO`

---

### Integration with `ToolResult` (existing model, no new type)

`PermissionPipeline.run()` returns the existing `kosmos.tools.models.ToolResult`. No new result type.

Denied calls:
```python
ToolResult(
    tool_id=tool_id,
    success=False,
    error=deny_reason or "permission_denied",
    error_type="permission_denied",  # requires Literal extension in Phase 4
)
```

**Required change**: `ToolResult.error_type` Literal must be extended to include `"permission_denied"` in `src/kosmos/tools/models.py` during Phase 4.

---

## Model Dependency Graph

```
SessionContext
    └── used by → PermissionCheckRequest
                       └── used by → every step function
                                         └── returns → PermissionStepResult
                                                            └── used by → AuditLogEntry
                                                                              └── written by → AuditLogger

PermissionPipeline.run() → returns → ToolResult (existing)
```

---

## What This Model Does Not Contain

- No stored session state — the pipeline is stateless; sessions are owned by the query engine.
- No tool schema references — `PermissionCheckRequest` carries `access_tier` and `is_personal_data` as scalar values; the pipeline reads the tool once from the registry and discards the reference.
- No API keys in any model field — keys are read from env vars inside step 6 only, never stored in a model.
