# V6 Error Contract

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md) | **Date**: 2026-04-17

## Scope

V6 does not expose a user-facing API. Its contracts are the **error shapes** produced at two defense layers. This document fixes those shapes so tests, logs, and the v1.1 spec document can reliably reference them.

## Contract 1 — Pydantic validator rejection (Layer 1)

**Trigger**: `GovAPITool(...)` or `GovAPITool.model_validate({...})` with `(auth_type, auth_level)` not in the canonical mapping.

**Exception class**: `pydantic.ValidationError` wrapping `ValueError`.

**Error message (stable, test-asserted)**:

```
V6 violation (FR-039/FR-040): tool '<tool_id>' declares auth_type='<auth_type>' with auth_level='<auth_level>'; auth_type='<auth_type>' permits auth_level in ['<v1>', '<v2>', ...].
```

**Assertions required by tests (FR-041)**:

1. Substring `"V6 violation"` MUST appear.
2. Substring `"auth_type"` MUST appear.
3. Substring `"auth_level"` MUST appear.
4. Every element of the allowed set for the offending `auth_type` MUST appear verbatim.

**Fail-closed variant (FR-048)**:

```
V6 violation (FR-048): unknown auth_type=<auth_type!r>; canonical mapping has no entry. Extend _AUTH_TYPE_LEVEL_MAPPING in the same PR that adds a new auth_type value.
```

## Contract 2 — Registry backstop rejection (Layer 2)

**Trigger**: `ToolRegistry.register(tool)` where `tool` was constructed via `GovAPITool.model_construct(...)` or mutated via `object.__setattr__(...)` post-construction, with `(auth_type, auth_level)` not in the canonical mapping.

**Exception class**: `kosmos.tools.errors.RegistrationError`.

**Error message (stable, test-asserted)**:

```
V6 violation (FR-042): tool '<tool_id>' declares auth_type='<auth_type>' with auth_level='<auth_level>'; permitted auth_levels are ['<v1>', '<v2>', ...]. (registry backstop — bypass of pydantic V6 detected)
```

**Assertions required by tests (FR-042, FR-043)**:

1. Substring `"V6 violation"` MUST appear.
2. Substring `"registry backstop"` MUST appear (this is the discriminator from Layer 1).
3. Exception type MUST be `RegistrationError`, NOT `ValueError` / `ValidationError`.

**Structured log (telemetry contract)**:

```
ERROR kosmos.tools.registry: V6 violation at registry.register: tool_id=<id> auth_type=<auth_type> auth_level=<auth_level> allowed=[...]
```

Emitted before the exception is raised. Log level `ERROR`. Uses `logger.error(...)` with `%s` format strings matching the V3 backstop precedent at `src/kosmos/tools/registry.py:68-74`.

**Fail-closed variant (FR-048)**:

```
V6 violation (FR-048): unknown auth_type=<auth_type!r> at registry.register; refusing to allow ambiguous registration.
```

## Contract 3 — Success path (no exception)

**Trigger**: `GovAPITool(...)` or `ToolRegistry.register(tool)` with `(auth_type, auth_level)` in the canonical mapping.

**Behavior**: V6 silently returns / allows through. No log, no exception. The next validator in the chain (or the rest of `register`) proceeds normally.

**Positive-case parameterization (FR-045)**:

Tests MUST cover all 8 allowed pairs:
- `(public, public)`
- `(public, AAL1)`
- `(api_key, AAL1)`
- `(api_key, AAL2)`
- `(api_key, AAL3)`
- `(oauth, AAL1)`
- `(oauth, AAL2)`
- `(oauth, AAL3)`

Negative-case parameterization (FR-045):

- `(public, AAL2)` — Epic #654 reference case
- `(public, AAL3)`
- `(api_key, public)`
- `(oauth, public)`

## Contract 4 — Registry-wide scan (FR-044 / SC-001)

**Trigger**: `pytest tests/tools/test_registry_invariant.py::test_registry_scan_all_adapters_pass_v6`.

**Behavior**: Instantiates the production registry factory (the same one the orchestrator uses). Iterates over `registry.all_tools()`. Asserts that for every registered tool, `tool.auth_level` is in `_AUTH_TYPE_LEVEL_MAPPING[tool.auth_type]`.

**On failure**: Pytest FAIL. Error message MUST name the offending tool id, its `(auth_type, auth_level)` pair, and the allowed set for that `auth_type`.

**Determinism requirement**: No network, no randomness, no sleep. Runs in the default CI suite. Must pass before any new-adapter PR can merge (SC-006).

## Contract 5 — Compatibility with V1–V5

V6 MUST NOT alter the error messages, exception types, or trigger conditions of V1–V5 validators (FR-047, SC-005). The existing test suite for V1–V5 MUST pass unchanged. No V1–V5 test may need to be updated to accommodate V6.
