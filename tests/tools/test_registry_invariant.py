# SPDX-License-Identifier: Apache-2.0
"""Registry invariant tests — T030.

FR-038: Registering a GovAPITool with is_personal_data=True and requires_auth=False
must raise RegistrationError at register time (fail-closed PII invariant).

Also verifies the positive case: is_personal_data=True with requires_auth=True
registers successfully.

These tests are unit-level: they build minimal GovAPITool stubs with only the
fields necessary to trigger or avoid the invariant. No network calls are made.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, RootModel

from kosmos.tools.errors import RegistrationError
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal stub schemas for test tools
# ---------------------------------------------------------------------------


class _StubInput(BaseModel):
    """Minimal input schema for stub tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str


class _StubOutput(RootModel[dict]):
    """Minimal output schema for stub tools."""


def _make_tool(
    tool_id: str,
    *,
    is_personal_data: bool,
    requires_auth: bool,
) -> GovAPITool:
    """Build a minimal GovAPITool for invariant testing.

    Post Spec-024 V5 the model enforces ``auth_level=='public' ⇔ requires_auth==False``,
    so we first construct a V5-consistent tool (auth_level/pipa_class/dpa_reference
    derived from ``is_personal_data``; ``requires_auth`` matches ``auth_level``),
    then use ``object.__setattr__`` to re-apply the caller-requested
    ``requires_auth`` so the *registry-level* FR-038 backstop is what gets
    tested (matching the purpose of this file — exercising the registry
    check, not the model validator).
    """
    auth_level = "AAL1" if is_personal_data else "public"
    consistent_requires_auth = auth_level != "public"
    tool = GovAPITool(
        id=tool_id,
        name_ko=f"테스트 도구 {tool_id}",
        provider="Test Provider",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type="api_key",
        input_schema=_StubInput,
        output_schema=_StubOutput,
        search_hint="test stub tool",
        auth_level=auth_level,
        pipa_class="personal" if is_personal_data else "non_personal",
        is_irreversible=False,
        dpa_reference="dpa-test-v1" if is_personal_data else None,
        requires_auth=consistent_requires_auth,
        is_personal_data=is_personal_data,
        is_concurrency_safe=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
        is_core=False,
    )
    if requires_auth != consistent_requires_auth:
        object.__setattr__(tool, "requires_auth", requires_auth)
    return tool


# ---------------------------------------------------------------------------
# T030 — FR-038 invariant: is_personal_data=True, requires_auth=False → error
# ---------------------------------------------------------------------------


class TestRegistryInvariantFR038:
    """FR-038: PII-flagged adapters must require authentication."""

    def test_personal_data_without_auth_raises_registration_error(self) -> None:
        """is_personal_data=True with requires_auth=False must raise RegistrationError."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_pii_no_auth",
            is_personal_data=True,
            requires_auth=False,
        )
        with pytest.raises(RegistrationError) as exc_info:
            registry.register(tool)

        err = exc_info.value
        assert err.tool_id == "stub_pii_no_auth"
        assert "is_personal_data" in str(err).lower() or "FR-038" in str(err)

    def test_error_message_references_invariant(self) -> None:
        """RegistrationError message must mention the relevant invariant."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_pii_no_auth_msg",
            is_personal_data=True,
            requires_auth=False,
        )
        with pytest.raises(RegistrationError) as exc_info:
            registry.register(tool)

        msg = str(exc_info.value)
        # Message must reference either the field name or the spec clause.
        assert "is_personal_data" in msg or "FR-038" in msg or "requires_auth" in msg, (
            f"RegistrationError message missing invariant reference: {msg!r}"
        )

    def test_tool_not_stored_after_invariant_violation(self) -> None:
        """Registry must not store the tool when the invariant is violated."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_pii_no_auth_no_store",
            is_personal_data=True,
            requires_auth=False,
        )
        with pytest.raises(RegistrationError):
            registry.register(tool)

        assert "stub_pii_no_auth_no_store" not in registry, (
            "Tool should not be present in registry after invariant violation"
        )
        assert len(registry) == 0

    # ---------------------------------------------------------------------------
    # Positive case: is_personal_data=True, requires_auth=True → OK
    # ---------------------------------------------------------------------------

    def test_personal_data_with_auth_registers_successfully(self) -> None:
        """is_personal_data=True with requires_auth=True must register without error."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_pii_with_auth",
            is_personal_data=True,
            requires_auth=True,
        )
        # Must not raise
        registry.register(tool)
        assert "stub_pii_with_auth" in registry
        assert len(registry) == 1

    def test_no_pii_no_auth_registers_successfully(self) -> None:
        """is_personal_data=False with requires_auth=False is allowed (no PII, no auth needed)."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_no_pii_no_auth",
            is_personal_data=False,
            requires_auth=False,
        )
        registry.register(tool)
        assert "stub_no_pii_no_auth" in registry

    def test_no_pii_with_auth_registers_successfully(self) -> None:
        """is_personal_data=False with requires_auth=True is allowed (extra-cautious)."""
        registry = ToolRegistry()
        tool = _make_tool(
            "stub_no_pii_with_auth",
            is_personal_data=False,
            requires_auth=True,
        )
        registry.register(tool)
        assert "stub_no_pii_with_auth" in registry

    def test_nmc_emergency_search_satisfies_invariant(self) -> None:
        """NMC emergency search (is_personal_data=True, requires_auth=True) registers OK."""
        from kosmos.tools.nmc.emergency_search import NMC_EMERGENCY_SEARCH_TOOL

        registry = ToolRegistry()
        # Must not raise
        registry.register(NMC_EMERGENCY_SEARCH_TOOL)
        assert "nmc_emergency_search" in registry


# ---------------------------------------------------------------------------
# B2 — Registry defense: auth_level='public' + is_personal_data=True rejected
# independently of requires_auth (defense-in-depth against V5 bypass).
# ---------------------------------------------------------------------------


class TestRegistryInvariantB2:
    """Even if requires_auth=True slips past V5, auth_level='public' alone fails closed."""

    def test_public_auth_level_with_pii_rejected(self) -> None:
        """auth_level='public' + is_personal_data=True must raise even when requires_auth=True."""
        registry = ToolRegistry()
        # Construct a PII tool with consistent AAL1 + requires_auth=True + dpa,
        # then downgrade auth_level to 'public' via bypass to simulate a V5
        # violation that reached the registry through model_construct.
        tool = _make_tool(
            "stub_public_pii_bypass",
            is_personal_data=True,
            requires_auth=True,
        )
        object.__setattr__(tool, "auth_level", "public")
        with pytest.raises(RegistrationError) as exc_info:
            registry.register(tool)

        err = exc_info.value
        assert err.tool_id == "stub_public_pii_bypass"
        msg = str(err)
        assert "auth_level" in msg or "public" in msg or "FR-038" in msg, (
            f"RegistrationError must cite auth_level/public invariant; got {msg!r}"
        )
        assert "stub_public_pii_bypass" not in registry
        assert len(registry) == 0
