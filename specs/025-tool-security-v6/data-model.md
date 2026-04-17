# Phase 1 Data Model: Tool Template Security Spec V6

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-04-17

## Scope

V6 is a validator + backstop spec. The "data model" here is not a storage schema; it is:
1. The canonical `auth_type → {auth_level}` mapping that both layers consume.
2. The V6 validator error contract (shape of `ValueError` and `RegistrationError` emitted on violation).
3. The relationship to the existing `GovAPITool` fields and the V1–V5 chain.

No database, no persistent state, no new pydantic models. V6 extends the existing `GovAPITool` model validator and the existing `ToolRegistry.register()` method.

## 1. Canonical Mapping (single source of truth for FR-039/FR-040/FR-042)

Declared as a module-level `Final` constant in `src/kosmos/tools/models.py`, imported by `src/kosmos/tools/registry.py`.

```python
# src/kosmos/tools/models.py
from typing import Final

_AUTH_TYPE_LEVEL_MAPPING: Final[dict[str, frozenset[str]]] = {
    "public":  frozenset({"public", "AAL1"}),
    "api_key": frozenset({"AAL1", "AAL2", "AAL3"}),
    "oauth":   frozenset({"AAL1", "AAL2", "AAL3"}),
}
```

### Allow-list matrix (full enumeration)

| `auth_type` \ `auth_level` | `public` | `AAL1` | `AAL2` | `AAL3` |
|---|---|---|---|---|
| `public` | ✅ allowed | ✅ allowed | ❌ rejected | ❌ rejected |
| `api_key` | ❌ rejected | ✅ allowed | ✅ allowed | ✅ allowed |
| `oauth` | ❌ rejected | ✅ allowed | ✅ allowed | ✅ allowed |

### Derived sets

- **Total pairs**: 3 × 4 = 12.
- **Allowed pairs** (8): `(public, public)`, `(public, AAL1)`, `(api_key, AAL1)`, `(api_key, AAL2)`, `(api_key, AAL3)`, `(oauth, AAL1)`, `(oauth, AAL2)`, `(oauth, AAL3)`.
- **Disallowed pairs** (4): `(public, AAL2)`, `(public, AAL3)`, `(api_key, public)`, `(oauth, public)`.

### Rationale for allowed set (documentation mirror of FR-040)

- **`public` ⇒ `{public, AAL1}`**: A transport-layer `auth_type="public"` means the upstream API requires no credential. V5 already enforces that `auth_level="public"` ⇔ `requires_auth=False`, so the `(public, public)` pair is the classic no-auth transport + no-auth assurance combination. `(public, AAL1)` is the approved MVP-meta-tool pattern (`resolve_location`, `lookup`) — no upstream credential, but KOSMOS still requires an authenticated citizen session (`requires_auth=True`) for rate-limit accounting and audit continuity. AAL2+ with `auth_type="public"` is rejected because a transport-unauthenticated endpoint cannot by itself meet AAL2/AAL3 assurance; the assurance must come from the transport layer.
- **`api_key` / `oauth` ⇒ `{AAL1, AAL2, AAL3}`**: Both auth types deliver authenticated transport. `auth_level="public"` is rejected for both because V5 requires `requires_auth=False` at `auth_level="public"`, which contradicts needing an API key or OAuth token at all.

### Interaction with V5 (already in force)

V5: `auth_level == "public"` ⇔ `requires_auth is False`.

V6 + V5 combined effect on the MVP-meta-tool pattern:
- `auth_type="public", auth_level="AAL1", requires_auth=True` — V6 allows (`AAL1 ∈ {public, AAL1}`), V5 allows (`auth_level != "public"`, so `requires_auth=True` is required). ✅ This is the approved `resolve_location` / `lookup` combination.
- `auth_type="public", auth_level="public", requires_auth=False` — V6 allows, V5 allows. ✅ Classic public tool.
- `auth_type="public", auth_level="public", requires_auth=True` — V6 allows, V5 rejects. ❌ (V5 violation surfaces; V6 does not.)
- `auth_type="public", auth_level="AAL2", requires_auth=True` — V6 rejects, V5 allows. ❌ (V6 violation surfaces.) **This is the Epic #654 target case.**

## 2. V6 Validator Error Contract

### 2.1. Pydantic validator error (layer 1 — FR-039, FR-041)

- **Exception type**: `ValueError` (raised inside `@model_validator(mode="after")`; pydantic re-wraps as `ValidationError` with `type="value_error"`).
- **Error origin**: `src/kosmos/tools/models.py :: GovAPITool._validate_security_invariants`.
- **Message format** (exact, test-asserted):
  ```
  V6 violation (FR-039/FR-040): tool '{tool_id}' declares auth_type='{auth_type}' with auth_level='{auth_level}'; auth_type='{auth_type}' permits auth_level in {sorted_allowed_list}.
  ```
- **Required content**: MUST name both `auth_type` and `auth_level` field names; MUST include the sorted list of allowed values for the given `auth_type`. This satisfies FR-041 (both-fields-named + allowed-set).
- **Ordering in the V1–V5 chain**: V6 runs after V5 in `_validate_security_invariants`. If both V5 and V6 would reject, V5 surfaces first (matches edge-case guidance in spec.md).
- **Fail-closed on unknown `auth_type`** (FR-048): if `self.auth_type` is not a key in `_AUTH_TYPE_LEVEL_MAPPING`, the validator raises `ValueError("V6 violation (FR-048): unknown auth_type={auth_type!r}; canonical mapping has no entry. Extend _AUTH_TYPE_LEVEL_MAPPING in the same PR that adds a new auth_type value.")`. This case cannot actually occur today because `auth_type` is `Literal["public", "api_key", "oauth"]` and pydantic rejects unknown values earlier, but the defensive branch is required by Constitution §II and FR-048 in case the Literal is widened.

### 2.2. Registry backstop error (layer 2 — FR-042, FR-043)

- **Exception type**: `RegistrationError` (existing class in `src/kosmos/tools/errors.py`).
- **Error origin**: `src/kosmos/tools/registry.py :: ToolRegistry.register`.
- **Message format** (exact, test-asserted):
  ```
  V6 violation (FR-042): tool '{tool_id}' declares auth_type='{auth_type}' with auth_level='{auth_level}'; permitted auth_levels are {sorted_allowed_list}. (registry backstop — bypass of pydantic V6 detected)
  ```
- **Distinguishability from layer 1** (FR-043): the `"(registry backstop — bypass of pydantic V6 detected)"` suffix is a unique substring not present in the layer-1 message. Log observability and tests can reliably tell which layer fired.
- **Structured log emission**: before raising, emit `logger.error("V6 violation at registry.register: tool_id=%s auth_type=%s auth_level=%s allowed=%s", tool.id, tool.auth_type, tool.auth_level, sorted(allowed))`. Matches the V3 backstop's log shape at `src/kosmos/tools/registry.py:68-74`.
- **Fail-closed on unknown `auth_type`** (FR-048): if `tool.auth_type` is not a key in the mapping, `RegistrationError(tool.id, "V6 violation (FR-048): unknown auth_type={...!r} at registry.register; refusing to allow ambiguous registration.")` is raised.

### 2.3. Positional guarantees (no drift between layers)

Both layers consume the identical `_AUTH_TYPE_LEVEL_MAPPING` constant (imported — not redeclared — in `registry.py`). This guarantees there is no way for the two layers to disagree on what is allowed; the only way to change the mapping is to edit the single module-level constant, and both layers pick up the change simultaneously.

## 3. Relationship to `GovAPITool` and V1–V5

### 3.1. Fields touched (read-only — no schema changes)

| Field | Declared in models.py | V6 reads | V6 mutates |
|---|---|---|---|
| `id` | line 24 | yes (for error messages only) | no |
| `auth_type` | line 49 `Literal["public", "api_key", "oauth"]` | yes | no |
| `auth_level` | line 62 `AALLevel` | yes | no |
| `requires_auth` | line 57 | no (V5 handles this relation) | no |

**V6 introduces zero new fields on `GovAPITool`.** This is a pure cross-field validator.

### 3.2. Validator-chain ordering inside `_validate_security_invariants`

Current chain (lines 166-238 of `models.py`): V1 → V2 → V3 → V4 → V5 → `return self`.

New chain with V6: V1 → V2 → V3 → V4 → V5 → **V6** → `return self`.

V6 placed after V5 intentionally: in the overlap case `auth_type="public", auth_level="public", requires_auth=True`, V5 has already declared the error clearer ("public tools MUST NOT require authentication"). V6 does not contradict — it just sits behind V5 in the surface-order and will fire first only when the violation is purely V6 (e.g., `auth_type="public", auth_level="AAL2"`, which V1–V5 would all accept).

### 3.3. Backstop-chain ordering inside `ToolRegistry.register`

Current chain (lines 36-79 of `registry.py`): duplicate-id check → FR-038 PII+public check → FR-038 PII+requires_auth check → V3 FR-038 TOOL_MIN_AAL drift check → append to `self._tools`.

New chain with V6: duplicate-id check → FR-038 PII+public → FR-038 PII+requires_auth → V3 FR-038 TOOL_MIN_AAL drift → **V6 backstop** → append.

V6 placed after V3 drift check intentionally: if a tool fails the `TOOL_MIN_AAL` check, that's a stronger per-tool-id assertion than the categorical V6 mapping, so surfacing V3 first gives the author the more specific error. V6 only fires for tool ids not in `TOOL_MIN_AAL` or when `TOOL_MIN_AAL` says AAL2 and `auth_type` says `public` (which V3 would already have caught via the drift check — V6 is the fallback for adapters not yet in the `TOOL_MIN_AAL` registry).

## 4. State Transitions

**None.** V6 is stateless. The canonical mapping is immutable. Validation runs once per `GovAPITool` construction and once per `ToolRegistry.register()` call. No caching, no memoization, no invalidation logic needed.

## 5. Baseline Snapshot — all current adapters satisfy V6

Verified by spec inspection (production registry factory, to be confirmed by the FR-044 registry-scan test during implementation):

| Tool id | auth_type | auth_level | V6 verdict |
|---|---|---|---|
| `koroad_accident_hazard_search` | `api_key` | `AAL1` | ✅ allowed |
| `kma_forecast_fetch` | `api_key` | `AAL1` | ✅ allowed |
| `hira_hospital_search` | `api_key` | `AAL1` | ✅ allowed |
| `nmc_emergency_search` | `api_key` | `AAL1` | ✅ allowed |
| `resolve_location` | `public` | `AAL1` | ✅ allowed (approved MVP-meta-tool pattern) |
| `lookup` | `public` | `AAL1` | ✅ allowed (approved MVP-meta-tool pattern) |

**No adapter needs to change.** The registry-scan test (FR-044) will assert this deterministically and will fail loudly if any future adapter regresses.
