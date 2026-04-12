# Implementation Plan: Permission Pipeline v1 (Layer 3)

**Epic**: #8
**Spec**: `specs/008-permission-pipeline-v1/spec.md`
**Status**: Ready for implementation
**Author**: Software Architect

---

## Phase 0 — Research Summary

### Reference source mapping

Every design decision traces to a concrete reference per Constitution § I.

| Decision | Primary source | Secondary source | Notes |
|---|---|---|---|
| Multi-step gauntlet as ordered callable chain | OpenAI Agents SDK — `guardrail` pipeline pattern | `claude-code-sourcemap` — 7-step permission model | Steps are individually replaceable without touching the runner |
| Bypass-immune rule set as a frozen constant | `claude-reviews-claude` — bypass-immune subset analysis | NeMo Guardrails — Colang 2.0 whitelist-of-approved-actions | Frozen at module level; runtime config cannot relax it |
| Classifier input isolation (future step 2) | NeMo Guardrails — declarative rail sees only tool + args | `docs/vision.md § Layer 3` | Step 2 stub designed to accept the same narrow signature |
| Runner-level enforcement, not adapter-level | Google ADK — runner-level plugin pattern | AutoGen — `InterventionHandler` | Pipeline wraps executor; adapters never see permission logic |
| Fail-closed on any step exception | LangGraph — `ToolNode(handle_tool_errors=True)`, `ValidationError` lesson | KOSMOS constitution § II | Exceptions are caught at the pipeline boundary, never propagated |
| Audit log structure and namespace | Google ADK — centralized permission enforcement log | `docs/vision.md § Layer 3` | Dedicated `kosmos.permissions.audit` logger namespace |
| Pydantic v2 frozen models for all I/O | Pydantic AI — schema-driven registry pattern | KOSMOS constitution § III | No `Any`; all models `frozen=True` |
| Env var read at call time (not import time) | `claude-code-sourcemap` — deferred credential resolution | KOSMOS constitution § II | Supports key rotation without process restart |

### Constitution compliance check

| Rule | Status | Notes |
|---|---|---|
| § II — Fail-closed defaults | Compliant | Pipeline denies on any exception; empty env var is denied |
| § II — Bypass-immune non-overridable | Compliant | `BYPASS_IMMUNE_RULES` is a `frozenset` module constant |
| § III — Pydantic v2, no `Any` | Compliant | All models use strict types; see data-model.md |
| § IV — No live API calls in CI | Compliant | Pipeline itself never calls external APIs; all tests mock the executor |
| § IV — `KOSMOS_`-prefixed env vars | Compliant | Only `KOSMOS_DATA_GO_KR_API_KEY` is read |

### Critical forward dependency: `ToolResult.error_type`

`kosmos.tools.models.ToolResult.error_type` is currently typed as:

```python
Literal["validation", "rate_limit", "not_found", "execution", "schema_mismatch"]
```

FR-021 requires the pipeline to return `ToolResult(error_type="permission_denied")`. This literal extension must be applied to `src/kosmos/tools/models.py` as part of Phase 4 (integration). It is a non-breaking additive change to an existing Literal type; no existing tests will break.

---

## Technical Context

- **Python 3.12+**, `pydantic>=2.0`, stdlib only (no new `pyproject.toml` entries)
- **Integration point**: `dispatch_tool_calls()` in `src/kosmos/engine/query.py` calls `tool_executor.dispatch()`. Phase 4 of this plan replaces that call with `permission_pipeline.run()`, which wraps the executor internally.
- **Existing tool models**: `GovAPITool.auth_type` is `Literal["public", "api_key", "oauth"]`; the pipeline maps this to `AccessTier` at entry (see data-model.md for the mapping table).
- **Executor contract**: `ToolExecutor.dispatch()` never raises — it returns `ToolResult`. The pipeline's step 6 calls it in an isolated credential context and captures any exception from the executor's own internals as a deny result.
- **Re-entrancy**: `PermissionPipeline.run()` creates all step state per-call. No shared mutable state between concurrent invocations. The executor's `RateLimiter` handles concurrent calls at the tool level.

---

## Module Structure

```
src/kosmos/permissions/
├── __init__.py            # exports: PermissionPipeline, AccessTier, PermissionDecision
├── models.py              # all Pydantic v2 models + enums (AccessTier, PermissionDecision,
│                          #   SessionContext, PermissionCheckRequest, PermissionStepResult,
│                          #   AuditLogEntry)
├── pipeline.py            # PermissionPipeline class — gauntlet runner + integration entry point
├── bypass.py              # BYPASS_IMMUNE_RULES frozenset + check_bypass_immune() function
├── audit.py               # AuditLogger — writes AuditLogEntry to kosmos.permissions.audit
└── steps/
    ├── __init__.py        # re-exports all step functions for clean imports
    ├── step1_config.py    # ACTIVE: configuration rules (access tier + api key check)
    ├── step2_intent.py    # STUB: intent analysis
    ├── step3_params.py    # STUB: parameter inspection
    ├── step4_authn.py     # STUB: citizen authentication
    ├── step5_terms.py     # STUB: ministry terms-of-use
    ├── step6_sandbox.py   # ACTIVE: sandboxed execution (isolated credential context)
    └── step7_audit.py     # ACTIVE: audit log emission

tests/permissions/
├── test_models.py         # model validation, frozen enforcement, no Any
├── test_pipeline.py       # end-to-end gauntlet: allow path, deny path, step ordering, audit always fires
├── test_step1_config.py   # all 4 AccessTier branches, empty string env var
├── test_step6_sandbox.py  # credential isolation, exception capture, env restoration
├── test_step7_audit.py    # field presence, arguments_json absent, log levels
└── test_bypass.py         # bypass_mode warning, citizen_id mismatch denial, BYPASS_IMMUNE_RULES frozen
```

---

## Key Design Decisions

### Decision 1: Steps as synchronous callables behind an async pipeline runner

Steps 1–5 and 7 are synchronous functions. Step 6 calls the async `ToolExecutor.dispatch()`.
`PermissionPipeline.run()` is itself an `async def` coroutine. The runner calls sync steps directly (no `asyncio.run()` nesting) and `await`s only step 6.

**Rationale**: Sync steps have no I/O; making them async would add overhead with no benefit. The runner being async allows it to call the executor without wrapping in `run_in_executor`. This aligns with the LangGraph lesson about not forcing sync wrappers around async boundaries.

**Trade-off**: Steps 2 and 3 (future active implementations) that require LLM classifiers will need to become async. Because the runner already `await`s step 6, changing any step from sync to async is a one-line change in the runner's step dispatch loop. The runner should use a helper that detects whether a step result is a coroutine:

```python
import asyncio, inspect

result = step_fn(request)
if inspect.isawaitable(result):
    result = await result
```

This makes the migration from stub (sync) to active (possibly async) a drop-in replacement.

### Decision 2: Credential isolation via context manager, not subprocess

Step 6 uses a `contextlib.contextmanager` that temporarily filters `os.environ` to a credential-scoped overlay, runs the adapter, then restores `os.environ`. It does NOT spin up a subprocess.

**Rationale**: Subprocess isolation is heavyweight for the v1 constraint (NFR-001: <5 ms overhead, non-execution path). The v1 threat model is: prevent adapters from accidentally reading other tools' keys via `os.environ`. Full process isolation (against a malicious adapter) is an explicit out-of-scope item.

**Trade-off**: A buggy adapter that spawns its own subprocess or uses `ctypes` to read environment bytes is not constrained by this approach. Accepted for v1 per the out-of-scope decision on per-ministry credential isolation.

**Implementation**: The sandbox function saves `os.environ.copy()`, deletes all `KOSMOS_*` vars except the ones relevant to the tool's `access_tier`, runs the adapter, then restores with `os.environ.clear(); os.environ.update(saved)`. A try/finally guarantees restoration even if the adapter raises.

### Decision 3: `BYPASS_IMMUNE_RULES` as a named frozenset of rule identifiers

`bypass.py` defines a `frozenset[str]` of rule identifiers (e.g., `"personal_data_citizen_mismatch"`) and a `check_bypass_immune()` function that evaluates them against the `PermissionCheckRequest`. The pipeline calls this function before checking `is_bypass_mode`.

**Rationale**: Using named rule identifiers rather than boolean flags makes the bypass logic auditable — the audit log can record which specific rule triggered. The frozenset is immutable at module load time; no constructor or setter can modify it. This satisfies FR-014.

**Trade-off**: Adding a new bypass-immune rule requires a code change and PR review (not a config change). This is the intended property, not a limitation.

### Decision 4: `ToolResult.error_type` extension

The pipeline must return `ToolResult(error_type="permission_denied")` (FR-021), but the existing Literal in `tools/models.py` does not include that value. The model validator in `ToolResult` will raise a `ValidationError` if we try to set an unlisted Literal.

**Resolution**: Phase 4 adds `"permission_denied"` to the Literal in `tools/models.py`. This is an additive change. No existing test assertions check the exhaustive list of Literal values, so this is safe.

**Why not introduce a new result type**: FR-021 explicitly forbids introducing a new result type. Layer 1 (`dispatch_tool_calls`) processes `ToolResult` uniformly — a new type would require changes to `query.py`, violating the spec's integration contract.

---

## Implementation Phases

### Phase 1 — Models and step protocol (no I/O, testable in isolation)

**Goal**: All data structures exist and validate correctly. No pipeline logic yet.

**Files to create/modify**:
- `src/kosmos/permissions/__init__.py` — empty package init
- `src/kosmos/permissions/models.py` — complete model definitions (see data-model.md)
- `src/kosmos/permissions/steps/__init__.py` — empty
- `tests/permissions/__init__.py` — empty
- `tests/permissions/test_models.py` — model validation tests

**Key acceptance criteria from spec**:
- FR-001 through FR-007: all models created with correct field types, frozen config, no `Any`
- SC-010: import-time env isolation verifiable (no env reads at import)

**Scope boundary**: No pipeline logic, no step implementations, no integration touches in Phase 1.

---

### Phase 2 — Bypass rules + step 1 (config) + stubs (steps 2–5)

**Goal**: The per-step logic for the pre-execution gate is complete and individually testable.

**Files to create**:
- `src/kosmos/permissions/bypass.py` — `BYPASS_IMMUNE_RULES`, `check_bypass_immune()`
- `src/kosmos/permissions/steps/step1_config.py` — access tier check against env var
- `src/kosmos/permissions/steps/step2_intent.py` — stub returning `allow`
- `src/kosmos/permissions/steps/step3_params.py` — stub returning `allow`
- `src/kosmos/permissions/steps/step4_authn.py` — stub returning `allow`
- `src/kosmos/permissions/steps/step5_terms.py` — stub returning `allow`

**Tests to create**:
- `tests/permissions/test_step1_config.py`
- `tests/permissions/test_bypass.py`

**Stub contract**: Each stub is a `def step_N(request: PermissionCheckRequest) -> PermissionStepResult` function. No class wrapping, no extra protocol ABC — the runner identifies steps by position, not by type. This keeps stub replacement a pure function swap.

**Step 1 logic**:
```
match request.access_tier:
    case AccessTier.public:
        return allow(step=1)
    case AccessTier.api_key:
        key = os.environ.get("KOSMOS_DATA_GO_KR_API_KEY", "")
        return allow(step=1) if key else deny(step=1, reason="api_key_not_configured")
    case AccessTier.authenticated:
        return deny(step=1, reason="citizen_auth_not_implemented")
    case AccessTier.restricted:
        return deny(step=1, reason="tier_restricted_not_implemented")
```

**Key acceptance criteria**: SC-001, SC-002, SC-003 (key not in logs), SC-004 (stubs), SC-007 (exception → deny), SC-008 (bypass immune).

---

### Phase 3 — Sandboxed execution (step 6) + audit log (step 7)

**Goal**: The execution and post-execution stages are complete.

**Files to create**:
- `src/kosmos/permissions/steps/step6_sandbox.py` — isolated credential context
- `src/kosmos/permissions/steps/step7_audit.py` — delegates to `audit.py`
- `src/kosmos/permissions/audit.py` — `AuditLogger.log()` writing `AuditLogEntry`

**Tests to create**:
- `tests/permissions/test_step6_sandbox.py`
- `tests/permissions/test_step7_audit.py`

**Step 6 sandbox design**:
```python
@contextlib.contextmanager
def _credential_scope(access_tier: AccessTier) -> Iterator[dict[str, str]]:
    """Yield a dict of only the credentials for this tier; restore env after."""
    saved = os.environ.copy()
    credentials: dict[str, str] = {}
    try:
        if access_tier == AccessTier.api_key:
            key = os.environ.get("KOSMOS_DATA_GO_KR_API_KEY", "")
            if key:
                credentials["data_go_kr_api_key"] = key
        # Remove ALL KOSMOS_* vars from os.environ during adapter execution
        for k in [k for k in os.environ if k.startswith("KOSMOS_")]:
            del os.environ[k]
        yield credentials
    finally:
        os.environ.clear()
        os.environ.update(saved)
```

Step 6 calls `await executor.dispatch(tool_id, arguments_json)` inside the `_credential_scope` context. If the dispatch raises (should not — executor is no-raise), it is caught and converted to a deny result.

**Step 7 audit design**:
- `AuditLogger` has one method: `log(entry: AuditLogEntry) -> None`
- Logs at `INFO` if `entry.decision == PermissionDecision.allow` and `entry.outcome != "denied"`
- Logs at `WARNING` if `entry.outcome == "denied"`
- Uses `getLogger("kosmos.permissions.audit")`
- If the log call itself raises, a fallback `logging.error()` to root logger is made — step 7 never raises (US-004 edge case)

**Key acceptance criteria**: SC-005, SC-006.

---

### Phase 4 — Pipeline orchestrator + integration

**Goal**: Full gauntlet runner assembled; integration with `ToolExecutor` complete; `query.py` updated.

**Files to create/modify**:
- `src/kosmos/permissions/pipeline.py` — `PermissionPipeline` class
- `src/kosmos/permissions/__init__.py` — update exports
- `src/kosmos/tools/models.py` — add `"permission_denied"` to `error_type` Literal
- `src/kosmos/engine/query.py` — replace `tool_executor.dispatch()` with `permission_pipeline.run()` in `dispatch_tool_calls()`

**Tests to create/modify**:
- `tests/permissions/test_pipeline.py` — end-to-end tests

**Pipeline runner design**:

```python
class PermissionPipeline:
    def __init__(self, executor: ToolExecutor, registry: ToolRegistry) -> None:
        self._executor = executor
        self._registry = registry

    async def run(
        self,
        tool_id: str,
        arguments_json: str,
        session_context: SessionContext,
    ) -> ToolResult:
        # 1. Build PermissionCheckRequest from registry lookup
        try:
            tool = self._registry.lookup(tool_id)
        except ToolNotFoundError:
            # tool_executor.dispatch() will handle not_found; skip to step 7
            ...
        access_tier = _map_auth_type(tool.auth_type)
        request = PermissionCheckRequest(
            tool_id=tool_id,
            access_tier=access_tier,
            arguments_json=arguments_json,
            session_context=session_context,
            is_personal_data=tool.is_personal_data,
        )

        # 2. Bypass-immune check (always runs, even in bypass mode)
        if request.is_bypass_mode:
            logger.warning("Bypass mode requested for tool %s session %s", ...)
        bypass_result = check_bypass_immune(request)
        if bypass_result is not None:
            # Write audit, return deny ToolResult
            ...

        # 3. Run steps 1-5 (pre-execution gate)
        deciding_step: PermissionStepResult | None = None
        for step_fn in _PRE_EXECUTION_STEPS:
            try:
                result = step_fn(request)
                if inspect.isawaitable(result):
                    result = await result
            except Exception as exc:
                logger.error("Step exception: %s", exc)
                deciding_step = PermissionStepResult(
                    decision=PermissionDecision.deny,
                    step=_step_number(step_fn),
                    reason="internal_error",
                )
                break
            if result.decision != PermissionDecision.allow:
                deciding_step = result
                break

        if deciding_step is not None:
            # Denied at pre-execution gate — run step 7, return deny ToolResult
            await _run_step7(request, deciding_step, outcome="denied")
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=deciding_step.reason or "permission_denied",
                error_type="permission_denied",
            )

        # 4. Step 6 — sandboxed execution
        tool_result = await run_step6_sandbox(request, self._executor)

        # 5. Step 7 — audit always fires
        outcome = "success" if tool_result.success else "failure"
        await _run_step7(request, PermissionStepResult(decision=allow, step=6), outcome=outcome)

        return tool_result
```

**`_map_auth_type` lookup table** (in `pipeline.py`):
```python
_AUTH_TYPE_TO_ACCESS_TIER: dict[str, AccessTier] = {
    "public": AccessTier.public,
    "api_key": AccessTier.api_key,
    "oauth": AccessTier.authenticated,
}
```

**Integration with `query.py`**: `dispatch_tool_calls()` currently takes `tool_executor: ToolExecutor`. In Phase 4, it receives `permission_pipeline: PermissionPipeline` instead (or an optional override). The call site `await tool_executor.dispatch(tc.function.name, tc.function.arguments)` becomes `await permission_pipeline.run(tc.function.name, tc.function.arguments, session_context)`. This requires `QueryContext` to carry a `PermissionPipeline` reference and a `SessionContext`. Both are additive fields.

**Key acceptance criteria**: SC-001 through SC-010, US-008 scenarios 1–3.

---

## Integration Change Summary

| File | Change type | Description |
|---|---|---|
| `src/kosmos/tools/models.py` | Additive Literal extension | Add `"permission_denied"` to `error_type` |
| `src/kosmos/engine/query.py` | Interface addition | `dispatch_tool_calls()` accepts optional `PermissionPipeline`; `QueryContext` gains `permission_pipeline` field |
| `src/kosmos/engine/models.py` | Additive field | `QueryContext` gains `permission_pipeline: PermissionPipeline \| None = None` and `session_context: SessionContext \| None = None` |
| `src/kosmos/permissions/` | New package | All new files |
| `tests/permissions/` | New directory | All new test files |

---

## Dependency Order

```
Phase 1 (models)
    ↓
Phase 2 (bypass + steps 1-5)    ← no dependency on Phase 3
Phase 3 (steps 6-7 + audit)     ← no dependency on Phase 2
    ↓ (both must be done)
Phase 4 (pipeline + integration)
```

Phases 2 and 3 are independent and can be parallelized by separate agents.

---

## Test Coverage Requirements

| Test file | FR covered | SC covered |
|---|---|---|
| `test_models.py` | FR-001–FR-007 | SC-010 |
| `test_step1_config.py` | FR-009, FR-017, FR-018, FR-019 | SC-001, SC-002, SC-003 |
| `test_bypass.py` | FR-014, FR-015, FR-016 | SC-008 |
| `test_step6_sandbox.py` | FR-011 | SC-005 |
| `test_step7_audit.py` | FR-012 | SC-006 |
| `test_pipeline.py` | FR-008, FR-013, FR-020, FR-021, FR-022 | SC-001–SC-009 (integration) |

All tests use `pytest` + `pytest-asyncio`. No `@pytest.mark.live` tests — the pipeline never calls external APIs.

---

## Non-Functional Requirement Compliance

| NFR | Mechanism |
|---|---|
| NFR-001 (<5 ms overhead, non-exec path) | Steps 1 and 7 are env var read + `logging` call. No serialization, no I/O. Benchmark target: each active step <1 ms; combined <3 ms. |
| NFR-002 (no new deps) | `os`, `logging`, `datetime`, `enum`, `contextlib` + `pydantic>=2.0` only. |
| NFR-003 (individually testable steps) | Each step is a standalone function with a `PermissionCheckRequest → PermissionStepResult` signature. |
| NFR-004 (audit log namespace) | `getLogger("kosmos.permissions.audit")` dedicated namespace. |
| NFR-005 (re-entrant) | No class-level mutable state. Each `run()` builds its own `PermissionCheckRequest` and step result chain. |

---

## Edge Case Handling Plan

| Edge case | Handling |
|---|---|
| Malformed `arguments_json` | Step 1 does not parse args (only reads `access_tier`). Malformed JSON propagates to `ToolExecutor.dispatch()` which returns `error_type="validation"`. Step 7 logs the outcome. |
| `KOSMOS_DATA_GO_KR_API_KEY` is non-empty whitespace | `os.environ.get(..., "").strip()` — whitespace-only treated as absent; deny at step 1. |
| `session_context.citizen_id` is `None` with `is_personal_data=True` | `check_bypass_immune()` compares `None` to any `citizen_id` in args. Since `None != <any_value>`, the rule triggers. Pipeline denies. |
| Step 7 itself raises | Caught in `_run_step7` wrapper with try/except; fallback `logging.error()` to root logger. Never propagates. |
| Concurrent calls for same tool | Each `run()` is independent. `RateLimiter` in `ToolExecutor` handles concurrency at tool level. |
| Tool not found | Step 1 receives a synthesized `PermissionCheckRequest` with fallback tier; the pipeline calls `ToolExecutor.dispatch()` in step 6, which returns `error_type="not_found"`. Step 7 logs the outcome. |
| `access_tier` not in `_AUTH_TYPE_TO_ACCESS_TIER` | `pipeline.py` raises `ValueError` before constructing `PermissionCheckRequest`; pipeline catches it, logs at ERROR, returns deny with `reason="internal_error"`. |
| `escalate` decision | Treated as `deny` in v1. Runner checks `result.decision != PermissionDecision.allow` which is true for both `deny` and `escalate`. |
