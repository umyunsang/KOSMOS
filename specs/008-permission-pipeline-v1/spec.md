# Feature Specification: Permission Pipeline v1 (Layer 3)

**Epic**: #8
**Created**: 2026-04-13
**Status**: Completed (Phase 1)
**Layer**: Layer 3 — Permission Pipeline
**Input**: 7-step permission gauntlet with all steps fully implemented; fail-closed defaults; API key management; Pydantic v2 models for all I/O.

---

## Overview & Context

Every tool invocation in KOSMOS must pass through a permission gauntlet before the adapter executes. This feature implements all 7 steps of that gauntlet: three core enforcement steps (1, 6, 7) and four additional enforcement steps (2–5) that were initially planned as pass-through stubs but have been fully implemented in v1. It integrates with the existing `ToolExecutor.dispatch()` flow from Layer 2.

### Why this exists

KOSMOS routes citizen queries to Korean government APIs that may return personal data (주민등록번호, 의료기록, 주소 등). Korea's Personal Information Protection Act (PIPA, 개인정보보호법) governs every data flow involving personal identifiers. A single unenforced tool call that leaks citizen data is a legal violation, not just a bug.

The permission pipeline is the mechanism that makes KOSMOS's fail-closed security posture operational. The constitution (§ II) mandates it; this spec makes it concrete for v1.

### Scope of v1

v1 ships a fully-operational gauntlet with all 7 steps implemented. Steps 2–5 were originally planned as pass-through stubs but have been fully implemented during v1 development, providing comprehensive pre-execution enforcement. All steps follow fail-closed semantics.

**Active in v1 (original plan)**:
- Step 1 — Configuration rules (per-API access tier check)
- Step 6 — Sandboxed execution (isolated context, no ambient credentials)
- Step 7 — Audit log (structured log of every invocation)

**Originally planned as stubs, fully implemented in v1**:
- Step 2 — Rule-based intent analysis (rapid-call burst detection, payload size limit, personal-data tier mismatch, JSON object validation)
- Step 3 — Korean PII parameter inspection (주민등록번호, 전화번호, 이메일, 여권번호, 신용카드 regex scan with PII-accepting param allowlist)
- Step 4 — Citizen authentication level enforcement (auth_level vs. tier requirement; restricted tier also requires citizen_id)
- Step 5 — Ministry terms-of-use consent tracking (in-memory per-session consent registry; provider extracted from tool_id prefix)

### Integration point

The permission pipeline wraps `ToolExecutor.dispatch()`. Before the executor runs, the pipeline runs steps 1–5. Step 6 is the execution context itself. Step 7 fires after the result is returned (success or failure).

---

## Reference Traceability

| Decision | Primary source | Secondary source |
|---|---|---|
| Multi-step gauntlet pattern | OpenAI Agents SDK (guardrail pipeline) | Claude Code reconstructed (permission model) |
| Bypass-immune subset | NeMo Guardrails (Colang 2.0 whitelist-of-approved-actions) | KOSMOS constitution § II |
| Classifier input isolation | NeMo Guardrails (declarative rail sees only tool + args) | docs/vision.md § Layer 3 |
| Runner-level enforcement | Google ADK (runner-level plugin pattern) | AutoGen (InterventionHandler) |
| Fail-closed on step error | LangGraph (ToolNode handle_tool_errors=True, ValidationError lesson) | KOSMOS constitution § II |
| Audit log structure | Google ADK (centralized permission enforcement log) | docs/vision.md § Layer 3 |
| Pydantic v2 models | Pydantic AI (schema-driven registry) | KOSMOS constitution § III |

---

## User Stories

### US-001 — Configuration-based access tier enforcement (P1)

As the KOSMOS permission pipeline, when a tool call arrives, I want to check the tool's declared `AccessTier` against the current session's privilege level before any API call is made, so that public-tier tools execute freely while api_key and higher tiers fail closed when credentials are absent.

**Acceptance scenarios**:
1. Given a tool with `access_tier=AccessTier.public`, when a call arrives with no session context, then the pipeline returns `PermissionDecision.allow`.
2. Given a tool with `access_tier=AccessTier.api_key`, when `KOSMOS_DATA_GO_KR_API_KEY` is not set, then the pipeline returns `PermissionDecision.deny` with `reason="api_key_not_configured"`.
3. Given a tool with `access_tier=AccessTier.api_key`, when the env var is set and non-empty, then the pipeline returns `PermissionDecision.allow`.
4. Given a tool with `access_tier=AccessTier.restricted`, then the pipeline always returns `PermissionDecision.deny` with `reason="tier_restricted_not_implemented"` in v1.
5. Given a tool with `access_tier=AccessTier.authenticated`, then the pipeline always returns `PermissionDecision.deny` with `reason="citizen_auth_not_implemented"` in v1.

---

### US-002 — Steps 2–5 enforce pre-execution safety rules (P1)

As a developer integrating Layer 3 with the query engine, I want steps 2–5 to actively enforce safety policies before any tool adapter is invoked, so that suspicious calls are denied before they reach external APIs.

**Acceptance scenarios**:
1. Given a tool call that exceeds RAPID_CALL_THRESHOLD (10) calls in RAPID_CALL_WINDOW_SECONDS (5 s) from the same session, when step 2 is invoked, then it returns `PermissionDecision.deny` with `reason="rapid_call_burst"`.
2. Given a tool call with a personal-data tool (`is_personal_data=True`) that has `access_tier=public`, when step 2 is invoked, then it returns `PermissionDecision.deny` with `reason="personal_data_public_tier_mismatch"`.
3. Given a tool call whose `arguments_json` contains a Korean resident registration number (주민등록번호) pattern outside a declared PII-accepting parameter, when step 3 is invoked, then it returns `PermissionDecision.deny` with `reason="pii_detected:rrn"`.
4. Given a tool with `access_tier=authenticated` and a session with `auth_level < 2`, when step 4 is invoked, then it returns `PermissionDecision.deny` with `reason="insufficient_auth_level"`.
5. Given a tool call where the tool's provider has not been consented to in the session, when step 5 is invoked, then it returns `PermissionDecision.deny` with `reason="terms_not_accepted:<provider>"`.
6. Each step function has the same signature (`PermissionCheckRequest` → `PermissionStepResult`) and is individually testable without modifying the gauntlet runner.
7. A `stubs.py` shim re-exports all four functions to preserve backward-compatible import paths.

---

### US-003 — Sandboxed execution context (P1)

As the KOSMOS platform, I want every adapter to execute inside an isolated context where no ambient environment credentials are accessible, so that an adapter cannot exfiltrate API keys that belong to other tools.

**Acceptance scenarios**:
1. Given a tool adapter call, when it executes in the sandbox, then it receives only the credentials it declared via its `access_tier` — no other `KOSMOS_*` env vars are visible in the execution scope.
2. Given an adapter that raises an exception, when the sandbox catches it, then it returns a `PermissionDecision.deny` result with `reason="execution_error"` and logs the exception; no exception propagates to the caller.
3. Given a successful adapter execution, when the sandbox returns, then the original environment is fully restored (no credential leakage between calls).

---

### US-004 — Audit log on every invocation (P1)

As a KOSMOS operator, I want every tool invocation (approved or denied, succeeded or failed) to produce a structured log entry, so that I have a complete trail for PIPA compliance audits.

**Acceptance scenarios**:
1. Given any tool call that is approved, when the call completes (success or error), then a log record is emitted at INFO level containing: `timestamp`, `tool_id`, `access_tier`, `decision`, `step_that_decided`, `outcome` (success/failure), and `error_type` if applicable.
2. Given any tool call that is denied at any step, then a log record is emitted at WARNING level with the same fields plus `deny_reason`.
3. Given a denied call, when the audit log entry is written, then the `arguments_json` field is omitted (to avoid logging PII from request parameters).
4. All audit log entries use `logging.getLogger("kosmos.permissions.audit")` so they can be routed to a dedicated handler independently of the main application log.

---

### US-005 — Fail-closed on any step error (P1)

As the KOSMOS permission pipeline, when any step raises an unexpected exception (not a normal deny decision), I want the overall result to be `PermissionDecision.deny`, so that a buggy or crashed step never accidentally grants access.

**Acceptance scenarios**:
1. Given step 1 raises a Python exception (not a `PermissionDeniedError`), then the pipeline catches it, logs it at ERROR level, and returns `PermissionDecision.deny` with `reason="internal_error"`.
2. Given the same scenario, then the executor is never invoked.
3. Given any of steps 2–5 that raises an exception, then the same fail-closed behavior applies.

---

### US-006 — Bypass-immune subset (P1)

As the KOSMOS platform, I want certain permission checks to be enforced even when future operating modes (batch automation, admin override, test harness) attempt to skip the pipeline, so that the system cannot be configured into a state that violates PIPA.

**Acceptance scenarios**:
1. Given the bypass-immune rule set (`BYPASS_IMMUNE_RULES`), when a tool call targets another citizen's personal records (is_personal_data=True and citizen_id in arguments does not match session citizen_id), then the pipeline denies regardless of any override flag.
2. Given a future "bypass_permissions" flag on the session, when the flag is set to True, then bypass-immune rules are still enforced and a WARNING log is emitted recording the bypass attempt.
3. The bypass-immune rule set is a frozen constant, not configurable at runtime without a code change.

---

### US-007 — API key injection for data.go.kr (P2)

As an adapter for a data.go.kr API, I want to receive the validated API key from the pipeline's sandbox rather than reading `os.environ` directly, so that API key access is mediated and auditable.

**Acceptance scenarios**:
1. Given a tool with `access_tier=AccessTier.api_key`, when the sandbox constructs the execution context, then it injects `data_go_kr_api_key` as a parameter to the adapter function.
2. Given the env var `KOSMOS_DATA_GO_KR_API_KEY` is set, when the sandbox reads it, then it reads it once at call time (not at import time) to support key rotation.
3. Given the env var is absent, then the pipeline denies at step 1 before the sandbox is entered.

---

### US-008 — Pipeline integration with ToolExecutor (P2)

As the query engine (Layer 1), I want a single `PermissionPipeline.run(tool_id, arguments_json, session_context)` entry point that wraps the full 7-step gauntlet and returns a `ToolResult`, so that Layer 1 does not need to call the executor and pipeline separately.

**Acceptance scenarios**:
1. Given a pipeline instance wrapping a `ToolExecutor`, when `run()` is called for an allowed tool, then steps 1–7 fire in order and a `ToolResult(success=True)` is returned.
2. Given a tool denied at step 1, when `run()` is called, then a `ToolResult(success=False, error_type="permission_denied")` is returned and steps 2–6 are never invoked; step 7 (audit log) still fires to record the denial.
3. Given any call (approved or denied), then step 7 (audit log) always fires last.

---

## Functional Requirements

### Models

- **FR-001**: `AccessTier` MUST be a Python `Enum` with values: `public`, `api_key`, `authenticated`, `restricted`.
- **FR-002**: `PermissionDecision` MUST be a Python `Enum` with values: `allow`, `deny`, `escalate`.
- **FR-003**: `PermissionCheckRequest` MUST be a frozen Pydantic v2 `BaseModel` with fields: `tool_id: str`, `access_tier: AccessTier`, `arguments_json: str`, `session_context: SessionContext`, `is_personal_data: bool`, `is_bypass_mode: bool = False`.
- **FR-004**: `PermissionStepResult` MUST be a frozen Pydantic v2 `BaseModel` with fields: `decision: PermissionDecision`, `reason: str | None = None`, `step: int`.
- **FR-005**: `SessionContext` MUST be a frozen Pydantic v2 `BaseModel` with fields: `session_id: str`, `citizen_id: str | None = None`, `auth_level: int = 0`, `consented_providers: tuple[str, ...] = ()`. The `tuple` type ensures immutability of the collection on a frozen model.
- **FR-006**: `AuditLogEntry` MUST be a frozen Pydantic v2 `BaseModel` with fields: `timestamp: datetime`, `tool_id: str`, `access_tier: AccessTier`, `decision: PermissionDecision`, `step_that_decided: int`, `outcome: Literal["success", "failure", "denied"]`, `error_type: str | None = None`, `deny_reason: str | None = None`, `session_id: str`. The `arguments_json` field MUST NOT be present.
- **FR-007**: No `Any` types are permitted in any permission pipeline model.

### Gauntlet implementation

- **FR-008**: The `PermissionPipeline` class MUST execute steps in order 1–6, stopping at the first `deny` or `escalate` result, then always running step 7.
- **FR-009**: Step 1 MUST check the tool's `AccessTier`:
  - `public` → `allow` unconditionally.
  - `api_key` → `allow` iff `KOSMOS_DATA_GO_KR_API_KEY` env var is set and non-empty; `deny` otherwise.
  - `authenticated` → `deny` in v1 with `reason="citizen_auth_not_implemented"`.
  - `restricted` → `deny` in v1 with `reason="tier_restricted_not_implemented"`.
- **FR-010**: Steps 2–5 MUST be synchronous functions that accept a `PermissionCheckRequest` and return a `PermissionStepResult`. Each step enforces the following policies:
  - **Step 2 (intent)**: Denies if rapid-call burst detected (≥ `RAPID_CALL_THRESHOLD` calls in `RAPID_CALL_WINDOW_SECONDS`), argument payload exceeds `MAX_ARGS_BYTES` (16 KiB), a personal-data tool arrives with `access_tier=public` (tier mismatch), or `arguments_json` is not a valid JSON object.
  - **Step 3 (params)**: Scans all string-typed argument values for Korean PII patterns (주민등록번호, 전화번호, 이메일, 여권번호, 신용카드). Parameters listed in `PII_ACCEPTING_PARAMS` are excluded from the scan. Denies with `reason="pii_detected:<type>"` on match.
  - **Step 4 (authn)**: Enforces minimum `auth_level` per access tier (public/api_key → 0, authenticated/restricted → 2). Restricted tier additionally requires a non-None `citizen_id`. Denies with `reason="insufficient_auth_level"` or `reason="citizen_id_required"` as appropriate.
  - **Step 5 (terms)**: Verifies that the session has accepted the tool provider's terms-of-use. Consent may be recorded via `SessionContext.consented_providers` or via the `grant_consent(session_id, provider)` API. Provider is derived from the tool_id prefix (before the first `_`). Denies with `reason="terms_not_accepted:<provider>"` if consent is absent.
- **FR-011**: Step 6 MUST execute the adapter inside an isolated context:
  - Builds a `dict` containing only the credentials relevant to the tool's `AccessTier`.
  - Calls the adapter function from `ToolExecutor` with the isolated credential context.
  - Catches all exceptions and converts them to a deny result with `reason="execution_error"`.
  - Restores the original environment after execution (no side effects on `os.environ`).
- **FR-012**: Step 7 MUST write an `AuditLogEntry` to `logging.getLogger("kosmos.permissions.audit")` at `INFO` level for approved calls and `WARNING` level for denied calls.
- **FR-013**: Any uncaught exception in steps 1–6 MUST cause the pipeline to return `PermissionDecision.deny` with `reason="internal_error"` and log the exception at `ERROR` level.

### Bypass-immune enforcement

- **FR-014**: `BYPASS_IMMUNE_RULES` MUST be a module-level frozenset constant, not a configurable setting.
- **FR-015**: If `is_personal_data=True` and `citizen_id` in `arguments_json` does not match `session_context.citizen_id`, then the pipeline MUST deny regardless of `is_bypass_mode`. Note: bypass-immune enforcement is the sole exception where `arguments_json` is parsed; only the `citizen_id` field is extracted. The full `arguments_json` is never logged or stored.
- **FR-016**: If `is_bypass_mode=True`, a `WARNING` log MUST be emitted recording the bypass attempt before bypass-immune rules are checked.

### API key management

- **FR-017**: API keys MUST be read from environment variables at call time (not at module import time) to support key rotation without process restart.
- **FR-018**: The environment variable for the default data.go.kr key is `KOSMOS_DATA_GO_KR_API_KEY`. No other naming is accepted.
- **FR-019**: API keys MUST NOT appear in log output, `AuditLogEntry` fields, or any Pydantic model that is serialized.

### Integration

- **FR-020**: `PermissionPipeline` MUST accept a `ToolExecutor` in its constructor and expose a `run(tool_id: str, arguments_json: str, session_context: SessionContext) -> ToolResult` coroutine.
- **FR-021**: A denied pipeline result MUST return `ToolResult(success=False, error_type="permission_denied", error=<reason>)` using the existing `ToolResult` model from `kosmos.tools.models`.
- **FR-022**: The pipeline MUST NOT modify the `ToolRegistry` or `GovAPITool` definitions. It reads them; it does not write them.

---

## Non-Functional Requirements

- **NFR-001** — Latency: The three active steps (1, 6, 7) combined must add less than 5 ms overhead per call in the non-execution path (i.e., env var read + log write). The adapter execution time itself is not counted.
- **NFR-002** — No new dependencies: The permission pipeline MUST be implemented using only stdlib (`os`, `logging`, `datetime`, `enum`, `contextlib`) plus already-declared dependencies (`pydantic>=2.0`). No new entries in `pyproject.toml`.
- **NFR-003** — Testability: All steps MUST be individually testable. Stub steps must be replaceable with real implementations without modifying the gauntlet runner.
- **NFR-004** — Log routing: Audit log entries MUST use the `kosmos.permissions.audit` logger namespace, separate from the root application logger.
- **NFR-005** — Thread safety: The pipeline MUST be re-entrant (no shared mutable state between calls). Each `run()` invocation creates its own step result chain.

---

## Module Layout

```
src/kosmos/
└── permissions/
    ├── __init__.py          # exports: PermissionPipeline, AccessTier, PermissionDecision
    ├── models.py            # AccessTier, PermissionDecision, PermissionCheckRequest,
    │                        #   PermissionStepResult, SessionContext, AuditLogEntry
    ├── pipeline.py          # PermissionPipeline class (gauntlet runner)
    ├── steps/
    │   ├── __init__.py
    │   ├── step1_config.py  # ACTIVE: configuration rules
    │   ├── step2_intent.py  # ACTIVE: rule-based intent analysis (burst, payload, tier mismatch, JSON)
    │   ├── step3_params.py  # ACTIVE: Korean PII parameter inspection (5 pattern categories)
    │   ├── step4_authn.py   # ACTIVE: citizen authentication level enforcement
    │   ├── step5_terms.py   # ACTIVE: ministry terms-of-use consent (in-memory registry)
    │   ├── step6_sandbox.py # ACTIVE: sandboxed execution
    │   └── step7_audit.py   # ACTIVE: audit log
    └── bypass.py            # BYPASS_IMMUNE_RULES constant + enforcement

tests/
└── permissions/
    ├── test_models.py
    ├── test_pipeline.py
    ├── test_step1_config.py
    ├── test_step6_sandbox.py
    ├── test_step7_audit.py
    └── test_bypass.py
```

---

## Data Model

### Enums

```python
class AccessTier(str, Enum):
    public        = "public"        # No auth; open data
    api_key       = "api_key"       # Requires KOSMOS_DATA_GO_KR_API_KEY
    authenticated = "authenticated" # Requires citizen identity verification (v2+)
    restricted    = "restricted"    # Special approval required (v2+)

class PermissionDecision(str, Enum):
    allow    = "allow"    # Proceed to next step / execute
    deny     = "deny"     # Halt; return error to query engine
    escalate = "escalate" # Pause; request more info from citizen (v2+)
```

### Core models (Pydantic v2)

```python
class SessionContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id:           str
    citizen_id:           str | None = None
    auth_level:           int        = 0
    consented_providers:  tuple[str, ...]  = ()

class PermissionCheckRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_id:         str
    access_tier:     AccessTier
    arguments_json:  str
    session_context: SessionContext
    is_personal_data: bool
    is_bypass_mode:   bool = False

class PermissionStepResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    decision: PermissionDecision
    step:     int
    reason:   str | None = None

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp:          datetime
    tool_id:            str
    access_tier:        AccessTier
    decision:           PermissionDecision
    step_that_decided:  int
    outcome:            Literal["success", "failure", "denied"]
    error_type:         str | None = None
    deny_reason:        str | None = None
    session_id:         str
    # arguments_json intentionally absent — prevents PII in audit trail
```

### Integration with existing models

`PermissionPipeline.run()` returns the existing `ToolResult` from `kosmos.tools.models`. No new result type is introduced. Denied calls return:

```python
ToolResult(
    tool_id=tool_id,
    success=False,
    error=deny_reason,
    error_type="permission_denied",
)
```

---

## Success Criteria

- **SC-001**: A tool with `access_tier=AccessTier.public` is dispatched to the adapter without any credential check, verified by unit test with no env vars set.
- **SC-002**: A tool with `access_tier=AccessTier.api_key` is denied when `KOSMOS_DATA_GO_KR_API_KEY` is unset, verified by unit test with `os.environ` patched.
- **SC-003**: A tool with `access_tier=AccessTier.api_key` is allowed when the env var is set, and the key value is not present in any log output, verified by unit test capturing log records.
- **SC-004**: All 4 steps (2–5) return `allow` for clean, compliant requests (no burst, no PII, sufficient auth level, consent granted), verified by unit tests covering both the allow path and each deny condition.
- **SC-005**: A step 6 adapter exception produces `ToolResult(success=False, error_type="permission_denied")`, verified by injecting a raising mock adapter.
- **SC-006**: Step 7 audit log entry contains all required fields and omits `arguments_json`, verified by unit test asserting on the logged `AuditLogEntry`.
- **SC-007**: An unexpected exception in step 1 produces a deny result (not a Python exception propagating to the caller), verified by monkey-patching step 1 to raise.
- **SC-008**: `is_bypass_mode=True` does not bypass the personal-data citizen-id mismatch rule, verified by unit test with mismatched citizen IDs.
- **SC-009**: `uv run pytest tests/permissions/` passes with zero live API calls (no `@pytest.mark.live` tests in this module, since the pipeline itself never calls external APIs).
- **SC-010**: Importing `kosmos.permissions` does not read any environment variables at import time; env var reads occur only inside `run()`, verified by import-time env isolation test.

---

## Edge Cases

| Scenario | Expected behavior |
|---|---|
| `arguments_json` is malformed JSON | Step 1 parses the tier and allows/denies without parsing args; step 2 detects invalid JSON and denies with `reason="invalid_arguments_json"`; step 3 also has a defensive JSON-parse guard. Step 6 is never reached for malformed payloads. |
| `KOSMOS_DATA_GO_KR_API_KEY` is set but empty string | Treated as absent; step 1 denies with `reason="api_key_not_configured"`. An empty string is not a valid key. |
| `session_context.citizen_id` is None and tool `is_personal_data=True` | Bypass-immune rule triggers: citizen_id mismatch (None != any value). Pipeline denies. |
| Step 7 (audit logger) itself raises | Exception is swallowed; a fallback `logging.error()` call is made to the root logger. The audit failure MUST NOT cause the caller to receive an exception. |
| Pipeline called concurrently for same tool | Each call is independent (no shared mutable state). Rate limiting is handled by `ToolExecutor`'s existing `RateLimiter`. |
| Tool not found in registry | `ToolExecutor.dispatch()` returns `ToolResult(error_type="not_found")` before the pipeline's step 6 runs; step 7 still logs the outcome. |
| `access_tier` not set on `GovAPITool` | `GovAPITool.auth_type` (existing field) maps to `AccessTier` at pipeline entry: `"public"→public`, `"api_key"→api_key`, `"oauth"→authenticated`. The mapping is a lookup table in `pipeline.py`. |

---

## Out of Scope for v1

- **LLM-based intent analysis** — Deep semantic classification of whether the natural language request justifies the tool call (distinct from the rule-based step 2 implemented in v1). Requires a separate LLM call with classifier isolation. Targeted for v2.
- **Extended PII pattern library** — Additional regex patterns beyond the five categories (RRN, phone, email, passport, credit card) implemented in step 3 v1. Targeted for v2.
- **Gov24 identity API integration** — Dynamic auth level verification against live Gov24 tokens (step 4 v1 uses the static `auth_level` field from `SessionContext`). Targeted for Phase 2.
- **Persistent consent storage** — Durable across process restarts (step 5 v1 stores consent in-memory only). Targeted for Phase 2.
- **`escalate` decision path** — The `PermissionDecision.escalate` value is defined in the enum but the gauntlet runner treats it as `deny` in v1.
- **Refusal circuit breaker** — Consecutive denial counting and routing to human channel. Targeted for v2.
- **Classifier separation of concerns** — Ensuring LLM classifiers see only tool calls and arguments, not justifying prose. Relevant only when LLM-based intent analysis (v2) activates.
- **Per-ministry credential isolation** — Separate `KOSMOS_KOROAD_API_KEY`, etc. per-provider env vars beyond the shared `KOSMOS_DATA_GO_KR_API_KEY`. Targeted for v2.
- **Credential rotation / secret management** — Dynamic key rotation, HashiCorp Vault integration. Out of scope for Phase 1.

---

## Dependencies

| Dependency | Type | Notes |
|---|---|---|
| `kosmos.tools.models.ToolResult` | Internal, existing | Permission pipeline returns this type |
| `kosmos.tools.executor.ToolExecutor` | Internal, existing | Pipeline wraps the executor; step 6 calls it |
| `kosmos.tools.registry.ToolRegistry` | Internal, existing | Pipeline reads tool definitions to get `access_tier` |
| `pydantic>=2.0` | External, already declared | All pipeline models |
| stdlib `os`, `logging`, `datetime`, `enum`, `contextlib` | Stdlib | No new pyproject.toml entries |
| `KOSMOS_DATA_GO_KR_API_KEY` env var | Runtime config | Must be set for `api_key`-tier tools |
| Epic #6 (Tool System) | Epic dependency | `ToolExecutor`, `ToolRegistry`, `GovAPITool`, `ToolResult` must be merged first |

---

## Assumptions

1. `GovAPITool.auth_type` (values: `"public"`, `"api_key"`, `"oauth"`) is the v1 source of truth for access tier mapping. A dedicated `access_tier: AccessTier` field on `GovAPITool` is a v2 enhancement; the pipeline performs the mapping at entry.
2. All tools registered in v1 use `KOSMOS_DATA_GO_KR_API_KEY` for api_key-tier access. Provider-specific keys are a v2 concern.
3. Session context is passed in from the query engine. The permission pipeline does not create sessions.
4. In v1, `SessionContext.citizen_id` is always `None` (no citizen authentication yet). Bypass-immune rules still apply.
5. The pipeline is synchronous in v1 (steps are sync functions). Step 6 calls the async `ToolExecutor.dispatch()` via `asyncio`; the `PermissionPipeline.run()` is itself a coroutine.
6. No persistent storage of audit logs in v1; they go to the Python logging system. Forwarding to a structured log sink (e.g., CloudWatch, LOKI) is an operational concern outside this spec.
