# SPDX-License-Identifier: Apache-2.0
"""Registry invariant tests — T030 (FR-038) + T008–T011 (V6 FR-042/FR-043/FR-048).

FR-038: Registering a GovAPITool with is_personal_data=True and requires_auth=False
must raise RegistrationError at register time (fail-closed PII invariant).

Also verifies the positive case: is_personal_data=True with requires_auth=True
registers successfully.

V6 (FR-042/FR-043/FR-048): ToolRegistry.register() independently re-checks the
(auth_type, auth_level) consistency invariant against _AUTH_TYPE_LEVEL_MAPPING so
that GovAPITool objects bypassed via model_construct or object.__setattr__ are
rejected at the registry boundary with a RegistrationError distinguishable from the
pydantic ValidationError (FR-043 distinguishability contract).

These tests are unit-level: they build minimal GovAPITool stubs with only the
fields necessary to trigger or avoid the invariant. No network calls are made.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

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
    # V6 (FR-039/FR-040) requires auth_type to be consistent with auth_level:
    #   auth_level="public"  → auth_type must be "public" (api_key only allows AAL1+)
    #   auth_level="AAL1"    → auth_type can be "api_key" (or "oauth" or "public")
    auth_type = "api_key" if is_personal_data else "public"
    consistent_requires_auth = auth_level != "public"
    tool = GovAPITool(
        id=tool_id,
        name_ko=f"테스트 도구 {tool_id}",
        provider="Test Provider",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type=auth_type,
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


# ---------------------------------------------------------------------------
# V6 backstop tests — T008-T011
# FR-042/FR-043/FR-048: Registry re-checks (auth_type, auth_level) consistency
# as a second layer of defense against pydantic-bypass paths
# (model_construct / object.__setattr__).
# ---------------------------------------------------------------------------

# Shared minimal field values for model_construct calls.  We must supply every
# required GovAPITool field because model_construct skips __init__ and any
# validator, so missing fields produce AttributeError at access time.
_MC_DEFAULTS: dict[str, object] = {
    "id": "stub_v6_bypass",
    "name_ko": "V6 우회 스텁",
    "provider": "Test Provider",
    "category": ["test"],
    "endpoint": "https://example.com/api",
    "input_schema": _StubInput,
    "output_schema": _StubOutput,
    "search_hint": "v6 bypass stub tool",
    "pipa_class": "non_personal",
    "is_irreversible": False,
    "dpa_reference": None,
    "requires_auth": False,
    "is_concurrency_safe": False,
    "is_personal_data": False,
    "cache_ttl_seconds": 0,
    "rate_limit_per_minute": 10,
    "is_core": False,
    "llm_description": None,
}


class TestRegistryV6Backstop:
    """V6 registry backstop — FR-042/FR-043/FR-048 (T008–T011).

    Each test exercises the SECOND layer of defense: the backstop inside
    ToolRegistry.register() that catches (auth_type, auth_level) pairs that
    bypassed the pydantic model validator.
    """

    # ------------------------------------------------------------------
    # T008 — model_construct bypass rejected (primary path)
    # ------------------------------------------------------------------

    def test_v6_backstop_rejects_model_construct_bypass(self) -> None:  # T008
        """model_construct with (public, AAL2) bypasses pydantic but hits the backstop.

        (public, AAL2) is disallowed: _AUTH_TYPE_LEVEL_MAPPING["public"] = {"public", "AAL1"}.
        The backstop must reject it with RegistrationError whose message contains
        both "V6 violation" and "registry backstop" (FR-042 / FR-043).
        """
        fields = dict(_MC_DEFAULTS)
        fields["id"] = "stub_v6_mc_bypass"
        fields["auth_type"] = "public"
        fields["auth_level"] = "AAL2"
        fields["requires_auth"] = True  # AAL2 implies auth; irrelevant — bypass skips V5 too
        tool = GovAPITool.model_construct(**fields)

        registry = ToolRegistry()
        with pytest.raises(RegistrationError) as exc_info:
            registry.register(tool)

        msg = str(exc_info.value)
        assert "V6 violation" in msg, f"Expected 'V6 violation' in error; got: {msg!r}"
        assert "registry backstop" in msg, (
            f"Expected 'registry backstop' in error for FR-043 discriminator; got: {msg!r}"
        )
        assert "stub_v6_mc_bypass" not in registry

    # ------------------------------------------------------------------
    # T009 — object.__setattr__ mutation rejected
    # ------------------------------------------------------------------

    def test_v6_backstop_rejects_setattr_mutation(self) -> None:  # T009
        """object.__setattr__ mutation of a compliant tool into a disallowed pair is caught.

        Start with (public, AAL1, requires_auth=False) which is V6-compliant,
        then mutate auth_level to "AAL2" post-construction to simulate an
        out-of-tree caller bypassing validation. The registry backstop must
        catch this and raise RegistrationError with the required substrings.
        """
        # Build a fully valid tool via the normal constructor.
        tool = GovAPITool(
            id="stub_v6_setattr",
            name_ko="V6 setattr 스텁",
            provider="Test Provider",
            category=["test"],
            endpoint="https://example.com/api",
            auth_type="public",
            auth_level="AAL1",
            input_schema=_StubInput,
            output_schema=_StubOutput,
            search_hint="v6 setattr stub",
            pipa_class="non_personal",
            is_irreversible=False,
            dpa_reference=None,
            requires_auth=True,  # AAL1 requires auth per V5
            is_concurrency_safe=False,
            is_personal_data=False,
            cache_ttl_seconds=0,
            rate_limit_per_minute=10,
            is_core=False,
        )
        # Mutate into disallowed state: public + AAL2 is not in _AUTH_TYPE_LEVEL_MAPPING.
        object.__setattr__(tool, "auth_level", "AAL2")

        registry = ToolRegistry()
        with pytest.raises(RegistrationError) as exc_info:
            registry.register(tool)

        msg = str(exc_info.value)
        assert "V6 violation" in msg, f"Expected 'V6 violation' in error; got: {msg!r}"
        assert "registry backstop" in msg, (
            f"Expected 'registry backstop' in error for FR-043 discriminator; got: {msg!r}"
        )
        assert "stub_v6_setattr" not in registry

    # ------------------------------------------------------------------
    # T010 — compliant model_construct passes (backstop is not a blanket deny)
    # ------------------------------------------------------------------

    def test_v6_backstop_allows_compliant_model_construct(self) -> None:  # T010
        """model_construct with a compliant (api_key, AAL2) pair must register successfully.

        Confirms that the V6 backstop is a precision check, not a blanket deny
        for all bypassed instances (spec.md Edge Case §1).
        """
        fields = dict(_MC_DEFAULTS)
        fields["id"] = "stub_v6_mc_compliant"
        fields["auth_type"] = "api_key"
        fields["auth_level"] = "AAL2"
        fields["requires_auth"] = True  # AAL2 requires auth
        fields["pipa_class"] = "non_personal"
        tool = GovAPITool.model_construct(**fields)

        registry = ToolRegistry()
        registry.register(tool)

        assert "stub_v6_mc_compliant" in registry
        assert len(registry) == 1

    # ------------------------------------------------------------------
    # T011 — FR-043 discriminator: Layer-1 vs Layer-2 error shapes
    # ------------------------------------------------------------------

    def test_v6_backstop_error_distinguishable_from_pydantic(self) -> None:  # T011
        """Layer-1 (pydantic) and Layer-2 (registry backstop) errors are distinguishable.

        Layer-1: GovAPITool(...) via the normal constructor raises ValidationError.
            - Error text contains "V6 violation" but NOT "registry backstop".
        Layer-2: model_construct bypass + register() raises RegistrationError.
            - Error text contains BOTH "V6 violation" AND "registry backstop".
        Type assertions (FR-043):
            - isinstance(layer2_err, RegistrationError) is True.
            - type(layer2_err) is not ValidationError is True.
            - not isinstance(layer2_err, ValueError) is True.
        """
        # --- Layer 1: pydantic rejects at construction time ---
        layer1_err: ValidationError | None = None
        try:
            GovAPITool(
                id="stub_v6_l1",
                name_ko="V6 Layer1 스텁",
                provider="Test Provider",
                category=["test"],
                endpoint="https://example.com/api",
                auth_type="public",
                auth_level="AAL2",  # disallowed: public allows only {public, AAL1}
                input_schema=_StubInput,
                output_schema=_StubOutput,
                search_hint="v6 layer1 stub",
                pipa_class="non_personal",
                is_irreversible=False,
                dpa_reference=None,
                requires_auth=True,
                is_concurrency_safe=False,
                is_personal_data=False,
                cache_ttl_seconds=0,
                rate_limit_per_minute=10,
                is_core=False,
            )
        except ValidationError as exc:
            layer1_err = exc

        assert layer1_err is not None, "Expected pydantic ValidationError for (public, AAL2)"
        l1_msg = str(layer1_err)
        assert "V6 violation" in l1_msg, (
            f"Layer-1 error must contain 'V6 violation'; got: {l1_msg!r}"
        )
        assert "registry backstop" not in l1_msg, (
            f"Layer-1 error must NOT contain 'registry backstop'; got: {l1_msg!r}"
        )

        # --- Layer 2: registry backstop rejects at registration time ---
        fields = dict(_MC_DEFAULTS)
        fields["id"] = "stub_v6_l2"
        fields["auth_type"] = "public"
        fields["auth_level"] = "AAL2"
        fields["requires_auth"] = True
        bypassed_tool = GovAPITool.model_construct(**fields)

        layer2_err: RegistrationError | None = None
        registry = ToolRegistry()
        try:
            registry.register(bypassed_tool)
        except RegistrationError as exc:
            layer2_err = exc

        assert layer2_err is not None, "Expected RegistrationError from registry backstop"
        l2_msg = str(layer2_err)
        assert "V6 violation" in l2_msg, (
            f"Layer-2 error must contain 'V6 violation'; got: {l2_msg!r}"
        )
        assert "registry backstop" in l2_msg, (
            f"Layer-2 error must contain 'registry backstop'; got: {l2_msg!r}"
        )

        # FR-043 type assertions
        assert type(layer2_err) is RegistrationError, (
            f"Layer-2 error must be exactly RegistrationError; got {type(layer2_err)!r}"
        )
        assert not isinstance(layer2_err, ValidationError), (
            "Layer-2 error must not be an instance of pydantic ValidationError"
        )
        assert not isinstance(layer2_err, ValueError), (
            "Layer-2 error must not be an instance of ValueError"
        )
