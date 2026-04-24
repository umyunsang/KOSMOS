# SPDX-License-Identifier: Apache-2.0
"""T015 — FR-020 tool_id collision backstop tests.

Spec 031 FR-020: a second registration with an existing ``tool_id`` is rejected
with a structured :class:`AdapterIdCollisionError`. First-wins — the originally
registered tool stays live; the second call never mutates registry state.

``AdapterIdCollisionError`` subclasses :class:`DuplicateToolError` so pre-031
call sites that catch the parent class keep working. The subclass carries
``existing_module`` metadata so callers can distinguish harness collisions from
unrelated duplicate registrations.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, RootModel

from kosmos.tools.errors import AdapterIdCollisionError, DuplicateToolError
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry


class _StubInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str


class _StubOutput(RootModel[dict]):
    pass


def _make_tool(tool_id: str) -> GovAPITool:
    """Minimal V5/V6-consistent public tool suitable for registry registration."""
    return GovAPITool(
        id=tool_id,
        name_ko=f"테스트 {tool_id}",
        ministry="OTHER",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type="public",
        input_schema=_StubInput,
        output_schema=_StubOutput,
        search_hint="collision test stub",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_personal_data=False,
        is_concurrency_safe=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
        is_core=False,
    )


def test_second_registration_raises_adapter_id_collision_error() -> None:
    registry = ToolRegistry()
    registry.register(_make_tool("duplicate_probe"))

    with pytest.raises(AdapterIdCollisionError) as exc_info:
        registry.register(_make_tool("duplicate_probe"))

    assert exc_info.value.tool_id == "duplicate_probe"
    assert exc_info.value.existing_module is not None


def test_collision_error_subclasses_duplicate_tool_error() -> None:
    """Backward-compatibility gate: legacy catches of DuplicateToolError keep working."""
    registry = ToolRegistry()
    registry.register(_make_tool("legacy_catch_probe"))

    with pytest.raises(DuplicateToolError) as exc_info:
        registry.register(_make_tool("legacy_catch_probe"))

    assert isinstance(exc_info.value, AdapterIdCollisionError)


def test_first_wins_registry_unchanged_after_collision() -> None:
    """Second registration MUST NOT mutate registry state (first-wins)."""
    registry = ToolRegistry()
    first = _make_tool("first_wins_probe")
    registry.register(first)

    snapshot = registry._tools["first_wins_probe"]
    assert snapshot is first

    second = _make_tool("first_wins_probe")
    with pytest.raises(AdapterIdCollisionError):
        registry.register(second)

    # The stored tool is still the first one, by identity.
    assert registry._tools["first_wins_probe"] is first
    assert registry._tools["first_wins_probe"] is not second


def test_collision_exposes_existing_module_metadata() -> None:
    registry = ToolRegistry()
    registry.register(_make_tool("metadata_probe"))

    with pytest.raises(AdapterIdCollisionError) as exc_info:
        registry.register(_make_tool("metadata_probe"))

    # GovAPITool lives under kosmos.tools.models; existing_module MUST reflect that.
    assert exc_info.value.existing_module == "kosmos.tools.models"
