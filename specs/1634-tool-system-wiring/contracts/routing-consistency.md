# Contract: Routing Consistency Failure Modes

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data Model**: [../data-model.md](../data-model.md)

## 1. Purpose

`build_routing_index()` and `tests/tools/test_routing_consistency.py` together form the boot-time + CI governance gate. This contract enumerates the six invariants and the exact failure-message format so contributors can fix violations without spelunking.

## 2. Invariants (in evaluation order)

### Invariant 1 — Primitive declared

Every registered `GovAPITool` MUST have a non-`None` `primitive` field with value in `{lookup, resolve_location, submit, subscribe, verify}`.

**Failure message**: `"<tool_id>: invariant 1 (primitive declared) — primitive=None on registered adapter"`

**Source**: `routing_index.build_routing_index()`, `tests/tools/test_routing_consistency.py`.

### Invariant 2 — Ministry in closed enum

Every `GovAPITool.ministry` MUST be a member of the `Ministry` Literal alias.

**Failure message** (raised by Pydantic at construction, before `build_routing_index` sees the adapter): `"Input should be 'KOROAD', 'KMA', 'NMC', 'HIRA', 'NFA', 'MOHW', 'MOLIT', 'MOIS', 'KEC', 'MFDS', 'GOV24' or 'OTHER'"`

**Source**: Pydantic v2 validator on `GovAPITool.ministry`.

**Warning** (not failure): `ministry="OTHER"` triggers `RoutingIndex.warnings` entry: `"<tool_id>: ministry='OTHER' (transitional escape hatch)"`. Use of `OTHER` is a CI WARN, not a build break — it indicates an institution that needs to be added to the enum in a future commit.

### Invariant 3 — adapter_mode declared in mock subtree

Every adapter under `src/kosmos/tools/mock/*` MUST set `adapter_mode="mock"` explicitly (not rely on the `"live"` default).

**Failure message** (CI test only — runtime cannot inspect file paths cheaply): `"<tool_id>: invariant 3 (mock subtree adapter_mode declared) — adapter at <file_path> uses default adapter_mode='live'; mock adapters MUST declare 'mock' explicitly"`

**Source**: `tests/tools/test_routing_consistency.py`.

### Invariant 4 — Unique tool_id

No two registered adapters MAY share a `tool_id`.

**Failure message**: `"<tool_id>: invariant 4 (unique tool_id) — duplicate registration"`

**Source**: `routing_index.build_routing_index()`.

### Invariant 5 — `compute_permission_tier` total

`compute_permission_tier(adapter.auth_level, adapter.is_irreversible)` MUST return a value in `{1, 2, 3}` for every registered adapter.

**Failure message**: `"<tool_id>: invariant 5 (permission_tier total) — Unknown auth_level: <repr>"`

**Source**: `routing_index.build_routing_index()` (catches the `ValueError` raised by `compute_permission_tier`).

### Invariant 6 — Spec 025 v6 (auth_type, auth_level) preserved

Already enforced by Pydantic at `GovAPITool` construction time via the existing v6 validator (`src/kosmos/tools/models.py:313-327`). `build_routing_index()` does NOT re-check; if it received the adapter as a valid `GovAPITool` instance, this invariant has already passed.

**Failure message** (raised at adapter construction, before `build_routing_index` is called): `"V6 violation (FR-039): tool '<id>' has auth_type=<repr> with auth_level=<repr>; auth_type=<repr> permits auth_level in <set>"`

**Source**: `GovAPITool._enforce_v6_consistency()` validator.

## 3. CI test additional checks

`tests/tools/test_routing_consistency.py` runs invariants 1–6 against the live registry plus four additional CI-only checks:

### Check 7 — Tool list closure

The set of tools registered for the LLM-visible surface MUST equal the closed set defined in `contracts/primitive-envelope.md § 1`.

**Failure message**: `"Tool surface drift — expected {<set A>}, got {<set B>}; missing: {<…>}, extra: {<…>}"`

### Check 8 — CC dev tool absence

The runtime tool registration entry points (Python `register_all.py` + TUI tool dispatcher init) MUST contain zero references to the FR-012 dev tool names.

**Failure message**: `"CC dev tool re-imported — found '<name>' in <path:line>; deletion required per FR-012"`

**Implementation**: grep across `src/kosmos/tools/register_all.py` and `tui/src/tools/index.ts` (or whichever module composes the registered list).

### Check 9 — Auxiliary tool ministry/primitive consistency

Auxiliary tools (Translate, Calculator, DateParser, ExportPDF, WebFetch, WebSearch, Brief, MCP, Task) are NOT `GovAPITool` instances and are NOT subject to invariants 1–6. CI verifies they do not accidentally appear in the `GovAPITool` registry.

**Failure message**: `"Auxiliary tool '<name>' must not be registered as GovAPITool — auxiliary tools have a separate registration path"`

### Check 10 — Plugin namespace reservation

If any registered tool name (primitive, auxiliary, or adapter `tool_id`) starts with the prefix `plugin.`, it MUST follow the pattern `plugin.<id>.<verb>` per `§ L1-C C7`.

**Failure message**: `"Plugin namespace violation — '<name>' must match pattern 'plugin.<id>.<verb>'"`

## 4. Test execution

```bash
uv run pytest tests/tools/test_routing_consistency.py -v
```

Expected output on success:
```
tests/tools/test_routing_consistency.py::test_invariant_1_primitive_declared PASSED
tests/tools/test_routing_consistency.py::test_invariant_2_ministry_enum PASSED
tests/tools/test_routing_consistency.py::test_invariant_3_mock_adapter_mode_declared PASSED
tests/tools/test_routing_consistency.py::test_invariant_4_unique_tool_id PASSED
tests/tools/test_routing_consistency.py::test_invariant_5_permission_tier_total PASSED
tests/tools/test_routing_consistency.py::test_invariant_6_v6_preserved PASSED
tests/tools/test_routing_consistency.py::test_check_7_tool_list_closed PASSED
tests/tools/test_routing_consistency.py::test_check_8_cc_dev_tools_absent PASSED
tests/tools/test_routing_consistency.py::test_check_9_aux_not_in_gov_registry PASSED
tests/tools/test_routing_consistency.py::test_check_10_plugin_namespace PASSED
```

## 5. Boot integration

`kosmos.tools.register_all` calls `build_routing_index()` after registering all adapters. On `RoutingValidationError`, the process exits with code 78 (`EX_CONFIG`) per AGENTS.md fail-closed convention; the TUI surfaces this as "tool subsystem misconfigured — check logs."

Pseudocode:
```python
# src/kosmos/tools/register_all.py (end of file)
from kosmos.tools.routing_index import build_routing_index, RoutingValidationError

def register_all() -> RoutingIndex:
    adapters = _build_all_adapters()
    try:
        return build_routing_index(adapters)
    except RoutingValidationError as e:
        logger.fatal("Tool registry validation failed: %s", e)
        raise SystemExit(78) from e
```

## 6. Exemptions

None. Every `GovAPITool` instance, whether live or mock, is subject to all six invariants. Mock adapters under `src/kosmos/tools/mock/*` are additionally subject to CI check 3 (explicit `adapter_mode="mock"` declaration).
