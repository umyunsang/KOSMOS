"""Boot-time validation + primitive→adapter routing map.

Called from kosmos.tools.register_all at process start. Fails closed on:
- Any registered adapter with primitive=None
- Any registered adapter missing adapter_mode declaration in mock subtree (CI-only; not runtime)
- Duplicate tool_id across the registry
- compute_permission_tier() raising for any adapter
- Spec 025 v6 invariant violation for any adapter (delegates to GovAPITool validator)

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
    warnings: tuple[str, ...]


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
                f"{adapter.id}: invariant 4 (unique tool_id) — duplicate registration"
            )

        # Invariant 5: compute_permission_tier total
        try:
            compute_permission_tier(adapter.auth_level, adapter.is_irreversible)
        except ValueError as e:
            raise RoutingValidationError(
                f"{adapter.id}: invariant 5 (permission_tier total) — {e}"
            ) from e

        # Warning: ministry="OTHER"
        if hasattr(adapter, "ministry") and adapter.ministry == "OTHER":
            warnings.append(f"{adapter.id}: ministry='OTHER' (transitional escape hatch)")

        by_primitive[adapter.primitive].append(adapter)
        by_tool_id[adapter.id] = adapter

    return RoutingIndex(
        by_primitive={k: tuple(v) for k, v in by_primitive.items()},
        by_tool_id=by_tool_id,
        warnings=tuple(warnings),
    )
