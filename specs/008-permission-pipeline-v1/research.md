# Technical Research: Permission Pipeline v1

**Spec**: `specs/008-permission-pipeline-v1/spec.md`
**Purpose**: Records resolved technical unknowns. Each item is a question that required investigation before the implementation plan could be finalized.

---

## RES-001: `ToolResult.error_type` Literal gap

**Question**: FR-021 requires returning `ToolResult(error_type="permission_denied")`, but the existing Literal in `src/kosmos/tools/models.py` is:
```python
Literal["validation", "rate_limit", "not_found", "execution", "schema_mismatch"]
```
Pydantic v2 will raise `ValidationError` if an unlisted Literal value is passed.

**Resolution**: The Literal must be extended to include `"permission_denied"` as part of Phase 4. This is an additive, non-breaking change. No existing test asserts on the exhaustive Literal set.

**Action in plan**: Phase 4 explicitly modifies `src/kosmos/tools/models.py`. This is the only touch to Layer 2 code.

---

## RES-002: Step async migration path

**Question**: Steps 2–5 are synchronous stubs today. Active implementations (v2) may require LLM classifier calls, which are async. What is the migration path?

**Resolution**: The pipeline runner uses `inspect.isawaitable()` to detect whether a step returned a coroutine, and `await`s it if so. This means a stub step (sync) and an active step (async) are both valid return types for the same step function slot. The runner handles both without requiring a protocol/ABC change.

**Conclusion**: No abstract base class or Protocol is needed for steps. Type annotation `Callable[[PermissionCheckRequest], PermissionStepResult | Awaitable[PermissionStepResult]]` covers both cases.

---

## RES-003: `os.environ` mutation thread safety

**Question**: Step 6 mutates `os.environ` to isolate credentials. Is this safe in an async context where multiple `run()` calls may be in-flight?

**Analysis**: `asyncio` is single-threaded within an event loop. However, `os.environ` mutation in one coroutine and a context switch (e.g., `await executor.dispatch()`) would allow another coroutine to observe the modified environment during the awaited period.

**Resolution**: Step 6 must NOT yield control to the event loop while `os.environ` is in its modified state. The `await executor.dispatch()` call happens inside the `_credential_scope` context manager with `os.environ` in filtered state. This means another coroutine dispatched concurrently WILL see the filtered environment if scheduled during that await.

**v1 mitigation**: The `dispatch_tool_calls()` partition-sort algorithm in `query.py` already gates concurrent tool execution on `is_concurrency_safe`. Tools that access API keys have `is_concurrency_safe=False` (fail-closed default). Sequential execution means only one step 6 modifies `os.environ` at a time.

**v2 recommendation**: Replace `os.environ` mutation with an explicit `credentials: dict[str, str]` parameter injected into the adapter call signature, eliminating the global state issue entirely. This is the injection approach from FR-007/US-007.

**Action in plan**: Phase 3 documents the `is_concurrency_safe=False` requirement as the safety invariant. Phase 3 test suite includes a test verifying environment restoration after step 6.

---

## RES-004: `QueryContext` extension for `SessionContext`

**Question**: `dispatch_tool_calls()` in `query.py` currently receives `tool_executor: ToolExecutor`. Phase 4 needs to pass `permission_pipeline: PermissionPipeline` and `session_context: SessionContext`. How does `QueryContext` (in `engine/models.py`) evolve?

**Resolution**: Add two optional fields to `QueryContext`:
- `permission_pipeline: PermissionPipeline | None = None`
- `session_context: SessionContext | None = None`

When `permission_pipeline` is `None`, `dispatch_tool_calls()` falls back to the direct `tool_executor.dispatch()` call (backward compatible). When set, it delegates to `permission_pipeline.run()`. This allows the integration to be tested incrementally without breaking Wave 1/2 tests.

**Action in plan**: Phase 4 includes both `engine/models.py` and `engine/query.py` as files to modify.

---

## RES-005: `GovAPITool.auth_type` "oauth" mapping

**Question**: `GovAPITool.auth_type` has three values: `"public"`, `"api_key"`, `"oauth"`. `AccessTier` has four: `public`, `api_key`, `authenticated`, `restricted`. What does `"oauth"` map to?

**Resolution**: Per spec Assumption 1 and the edge case table (`access_tier not set on GovAPITool`), `"oauth"` maps to `AccessTier.authenticated`. This is the closest semantic match: OAuth requires citizen identity verification. In v1, `authenticated` is always denied, which is the correct fail-closed behavior for OAuth tools (no OAuth flow is implemented yet).

**Action in plan**: The `_AUTH_TYPE_TO_ACCESS_TIER` lookup table in `pipeline.py` maps `"oauth"` → `AccessTier.authenticated`.

---

## RES-006: Audit log and `datetime` timezone

**Question**: `AuditLogEntry.timestamp` is a `datetime`. Should it be timezone-aware?

**Resolution**: Use `datetime.now(UTC)` (stdlib `datetime.timezone.utc`). Naive datetimes in log records are ambiguous in multi-region deployments. Python 3.12's `datetime.now(UTC)` is idiomatic. Pydantic v2 serializes timezone-aware datetimes as ISO 8601 with offset.

**Action in data-model.md**: `timestamp` is documented as UTC.
