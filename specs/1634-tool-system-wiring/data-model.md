# Phase 1 Data Model — P3 · Tool System Wiring

**Branch**: `feat/1634-tool-system-wiring` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Convention

- All Pydantic models are `frozen=True, extra="forbid"` per Spec 024 + Spec 031 precedent.
- All field deltas below are *additive or rename* against the existing `src/kosmos/tools/models.py` and `src/kosmos/tools/registry.py`. No field is dropped.
- The Spec 025 v6 `(auth_type, auth_level)` invariant validator stays unchanged. New fields layer on top.

---

## 1. `GovAPITool` deltas

`src/kosmos/tools/models.py` — class `GovAPITool`.

### 1.1 Renamed field — `provider` → `ministry`

| Property | Before (existing) | After (P3) |
|---|---|---|
| Name | `provider` | `ministry` |
| Type | `str` | `Ministry` (Literal alias, see § 1.2) |
| Default | none (required) | none (required) |
| Docstring | "Ministry or agency that owns the API." | "Ministry or agency that owns the API. Closed enum; new institutions added by enum extension. `OTHER` is a transitional escape hatch and emits a CI warning." |

**Migration**: 15 currently-registered adapters in `src/kosmos/tools/{koroad,kma,hira,nmc,nfa,mohw,resolve_location,lookup}*` and 6 mock adapters in `src/kosmos/tools/mock/*` switch from `provider="..."` to `ministry=Ministry.<X>`. Mechanical edit; no behavioral change beyond enforced typing.

### 1.2 New type alias — `Ministry`

```python
# src/kosmos/tools/models.py (top of file, near other Literal aliases)
from typing import Literal

Ministry = Literal[
    "KOROAD",   # 도로교통공단 — road safety
    "KMA",      # 기상청 — weather
    "NMC",      # 국립중앙의료원 — emergency medical
    "HIRA",     # 건강보험심사평가원 — health insurance review
    "NFA",      # 소방청 — fire / 119
    "MOHW",     # 보건복지부 — welfare
    "MOLIT",    # 국토교통부 — land/infrastructure/transport
    "MOIS",     # 행정안전부 — public administration / safety
    "KEC",      # 한국교통안전공단 — vehicle inspection / e-signature
    "MFDS",     # 식품의약품안전처 — food & drug safety
    "GOV24",    # 정부24 — citizen submission portal (OPAQUE per feedback_mock_evidence_based)
    "OTHER",    # transitional escape hatch — CI emits warning
]
```

**Validation**: pydantic v2 enforces enum membership at construction. The CI consistency test additionally emits a warning when any registered adapter uses `ministry="OTHER"`.

### 1.3 New field — `adapter_mode`

| Property | Value |
|---|---|
| Name | `adapter_mode` |
| Type | `Literal["live", "mock"]` |
| Default | `"live"` (fail-explicit; deviation documented in plan.md § Complexity Tracking + research.md § 5.1) |
| Docstring | "Runtime source. `live` = adapter calls the real public API. `mock` = adapter returns recorded fixture or shape-compatible synthetic. Distinct from `AdapterRegistration.source_mode` which classifies mirror fidelity." |

**Validation**: pydantic v2 enforces literal membership. CI consistency test invariant 3 verifies `adapter_mode` is declared (i.e., not implicitly defaulted) on every adapter under `src/kosmos/tools/mock/*` (mock declarations must be explicit; live declarations may rely on the default).

### 1.4 Existing field — `primitive` (no schema change; population change only)

`primitive: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"] | None = None` (already exists, defaults `None` for the pre-v1.2 compatibility window).

**P3 change**: populate `primitive` on the 11 adapters that currently have `primitive=None`:

| Adapter (`tool_id`) | New `primitive` value | Rationale |
|---|---|---|
| `resolve_location` | `resolve_location` | Already set (verified via `grep`) |
| `lookup` | `lookup` | Already set |
| `koroad_accident_search` | `lookup` | Read-only data query |
| `koroad_accident_hazard_search` | `lookup` | Already set |
| `kma_weather_alert_status` | `lookup` | Read-only data query |
| `kma_current_observation` | `lookup` | Read-only data query |
| `kma_short_term_forecast` | `lookup` | Read-only data query |
| `kma_ultra_short_term_forecast` | `lookup` | Read-only data query |
| `kma_pre_warning` | `lookup` | Read-only data query |
| `kma_forecast_fetch` | `lookup` | Already set |
| `nmc_emergency_search` | `lookup` | Already set |
| `hira_hospital_search` | `lookup` | Already set |
| `nfa_emergency_info_service` | `lookup` | Read-only data query |
| `mohw_welfare_eligibility_search` | `lookup` | Read-only eligibility check |

After P3, no registered adapter has `primitive=None`. The `| None` union remains in the type for the mock-adapter pre-v1.2 compatibility window from Spec 031, but the CI consistency test fails the build if any registered adapter still has `None`.

**Composite removal (FR-027)**: `road_risk_score` (currently under `src/kosmos/tools/composite/`) is **deleted** in this epic. Its three inner adapter calls are left intact as standalone `lookup` adapters — the LLM composes risk-assessment results at the conversation level. Post-P3 live-adapter count is therefore **14**, not 15.

### 1.5 Removed-by-rename — `provider`

Once renamed to `ministry`, the original `provider` field no longer exists. Any external consumer of `GovAPITool.provider` is updated at the same commit. There are no external consumers outside `src/kosmos/` and `tui/src/` (verified via repo-wide grep).

---

## 2. `AdapterRegistration` — no schema change

`src/kosmos/tools/registry.py:93-161` — unchanged. The `source_mode: AdapterSourceMode` enum (`OPENAPI` / `OOS` / `HARNESS_ONLY`) stays as mirror-fidelity classification per research.md § 1.3 / Spec 031 design intent.

The Spec 031 v1.2 dual-axis `published_tier_minimum` / `nist_aal_hint` fields stay optional during pre-v1.2; P3 does not flip the v1.2 GA flag.

---

## 3. New helper — `compute_permission_tier`

```python
# src/kosmos/tools/permissions.py (NEW file)
"""Permission-tier derivation from existing GovAPITool fields.

Single source of truth consumed by:
- TUI permission gauntlet (UI-C C1 layer color rendering — green/orange/red)
- Audit ledger entry interpretation (Spec 024)
- Permission-mode transitions (Spec 033 Shift+Tab)
"""

from typing import Literal

from kosmos.tools.models import AALLevel  # Literal["public","AAL1","AAL2","AAL3"]


def compute_permission_tier(
    auth_level: AALLevel,
    is_irreversible: bool,
) -> Literal[1, 2, 3]:
    """Derive the UI-C permission layer from auth_level + irreversibility.

    Mapping (per spec FR-011 + research.md § 1.3 / Q3 clarification):
      public, AAL1                 → 1  (green ⓵)
      AAL2                         → 2  (orange ⓶)
      AAL3                         → 3  (red ⓷)
      is_irreversible=True         → 3  (overrides AAL mapping)

    Preserves Spec 025 v6 (auth_type, auth_level) invariant — does not read
    auth_type and therefore cannot drift from the v6 allow-list.
    """
    if is_irreversible:
        return 3
    if auth_level in ("public", "AAL1"):
        return 1
    if auth_level == "AAL2":
        return 2
    if auth_level == "AAL3":
        return 3
    # Defensive: AALLevel is a closed Literal; this branch is unreachable
    # under normal type checking, but Pydantic-validated input from external
    # JSON could theoretically deliver an unknown value at runtime if the
    # type contract is violated.
    raise ValueError(f"Unknown auth_level: {auth_level!r}")
```

**Properties**:
- Pure function, zero state, no I/O.
- Total over the closed `AALLevel` × `bool` domain (every combination returns a value or raises).
- Unit-testable in isolation; the CI consistency test exercises it on every registered adapter.

---

## 4. New module — `routing_index`

```python
# src/kosmos/tools/routing_index.py (NEW file)
"""Boot-time validation + primitive→adapter routing map.

Called from kosmos.tools.register_all at process start. Fails closed on:
- Any registered adapter with primitive=None
- Any registered adapter with ministry not in the closed enum
- Any registered adapter missing adapter_mode declaration in mock subtree
- Duplicate tool_id across the registry
- compute_permission_tier() raising for any adapter
- Spec 025 v6 invariant violation for any adapter (delegates to v12_dual_axis.enforce)

Returns a RoutingIndex that lookup(mode="search") consumes for primitive-
filtered ranking.
"""

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kosmos.tools.models import GovAPITool
from kosmos.tools.permissions import compute_permission_tier


class RoutingIndex(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    by_primitive: dict[
        Literal["lookup", "resolve_location", "submit", "subscribe", "verify"],
        tuple[GovAPITool, ...],
    ]
    by_tool_id: dict[str, GovAPITool]
    warnings: tuple[str, ...]  # e.g., ministry="OTHER" usage


class RoutingValidationError(Exception):
    """Fail-closed boot error naming the offending adapter and invariant."""


def build_routing_index(adapters: list[GovAPITool]) -> RoutingIndex:
    """Validate every adapter; return immutable routing index.

    Raises RoutingValidationError on the first failure with a message of the
    form: "<tool_id>: <invariant> — <details>".
    """
    by_primitive: dict[str, list[GovAPITool]] = defaultdict(list)
    by_tool_id: dict[str, GovAPITool] = {}
    warnings: list[str] = []

    for adapter in adapters:
        # Invariant 1: primitive declared
        if adapter.primitive is None:
            raise RoutingValidationError(
                f"{adapter.id}: invariant 1 (primitive declared) — "
                f"primitive=None on registered adapter"
            )

        # Invariant 4: tool_id unique
        if adapter.id in by_tool_id:
            raise RoutingValidationError(
                f"{adapter.id}: invariant 4 (unique tool_id) — "
                f"duplicate registration"
            )

        # Invariant 5: compute_permission_tier total
        try:
            compute_permission_tier(adapter.auth_level, adapter.is_irreversible)
        except ValueError as e:
            raise RoutingValidationError(
                f"{adapter.id}: invariant 5 (permission_tier total) — {e}"
            ) from e

        # Invariant 6: Spec 025 v6 — already enforced by GovAPITool validator at
        # construction time; if we reached here, the model is valid. No re-check.

        # Warning: ministry="OTHER"
        if adapter.ministry == "OTHER":
            warnings.append(
                f"{adapter.id}: ministry='OTHER' (transitional escape hatch)"
            )

        by_primitive[adapter.primitive].append(adapter)
        by_tool_id[adapter.id] = adapter

    return RoutingIndex(
        by_primitive={k: tuple(v) for k, v in by_primitive.items()},
        by_tool_id=by_tool_id,
        warnings=tuple(warnings),
    )
```

**Invariants 2 (ministry in closed enum) and 3 (adapter_mode declared in mock subtree)** are enforced by Pydantic at `GovAPITool` construction — by the time `build_routing_index` sees an adapter, the field has already been validated against the `Ministry` Literal alias. The mock-subtree-declaration check (invariant 3) is performed by the CI test, not the runtime function (it requires filesystem inspection that is inappropriate at runtime).

---

## 5. Primitive envelope types — referenced from Spec 031 + Spec 022

Each primitive uses its own Spec 031 envelope type (there is no unified `PrimitiveInput`/`PrimitiveOutput` — that phrasing was incorrect in earlier drafts). P3 does **not** redefine these types; TUI primitive wrappers serialize TS objects into the same shape.

| Primitive | Python type(s) | Canonical source | Current file |
|---|---|---|---|
| `lookup` | Spec 022 lookup input / output models | `specs/022-mvp-main-tool/data-model.md` | `src/kosmos/tools/lookup.py` |
| `submit` | `SubmitEnvelope` (input) + adapter-defined receipt (output) | `specs/031-five-primitive-harness/data-model.md § 1` | `src/kosmos/primitives/submit.py` |
| `subscribe` | `SubscriptionEvent` discriminated union (events) + adapter-defined `SubscriptionHandle` (creation output) | `specs/031-five-primitive-harness/data-model.md § 3` | `src/kosmos/primitives/subscribe.py` |
| `verify` | `VerifyInput` + `VerifyOutput` (already defined) | `specs/031-five-primitive-harness/data-model.md § 2` | `src/kosmos/primitives/verify.py:44,250` |

The TUI side at `tui/src/tools/primitive/*.ts` constructs the matching JSON-shaped payload for each primitive per `contracts/primitive-envelope.md § 2-5`. P3 does not introduce a shared base class or envelope module.

---

## 6. Entity relationships

```
GovAPITool ─┬── ministry: Ministry         (Literal closed enum)
            ├── primitive: AdapterPrimitive (populated on all adapters post-P3)
            ├── adapter_mode: live|mock     (NEW; default "live")
            ├── auth_level + is_irreversible
            │     └─→ compute_permission_tier() → Literal[1,2,3] (UI-C color)
            └── (Spec 024 + Spec 025 v6 fields unchanged)

build_routing_index(adapters) → RoutingIndex
                                  ├── by_primitive: primitive → tuple[GovAPITool]
                                  ├── by_tool_id: id → GovAPITool
                                  └── warnings: tuple[str]   (e.g., ministry="OTHER")

stdio MCP layer:
  TUI ──── tui/src/tools/primitive/{lookup,submit,verify,subscribe}.ts
              │
              └─→ tui/src/ipc/mcp.ts ── (handshake + tool list + tool call frames) ──┐
                       │                                                              │
                       └─→ tui/src/ipc/bridge.ts (Spec 287/032 stdio JSONL transport)─┘
                                                          │
                                                          ▼
                       src/kosmos/ipc/stdio.py (Spec 032 transport, unchanged)
                                                          │
                                                          ▼
                       src/kosmos/ipc/mcp_server.py (NEW; protocol-only stub)
                                                          │
                                                          ▼
                       src/kosmos/tools/registry.py + routing_index.py + primitives/*
```

---

## 7. Out-of-model concerns (deferred)

The following are referenced by the spec but not modeled here:

- **Plugin namespace `plugin.<id>.<verb>`** (`§ L1-C C7`) — schema and registration mechanics are P5 (Epic #1636) territory. P3 only reserves the four root primitive names against collision (the `Ministry` enum and the `primitive` Literal both being closed makes this automatic).
- **`docs/api/` per-adapter Markdown + JSON Schema/OpenAPI** — P6 (Epic #1637). The ministry enum being typed makes per-ministry doc generation trivial post-P3.
- **TUI rendering of `tool_use` / `tool_result` blocks** — P4 (Epic #1635).
