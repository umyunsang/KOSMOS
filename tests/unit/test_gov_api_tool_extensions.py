# SPDX-License-Identifier: Apache-2.0
"""Unit tests for GovAPITool security-spec-v1 field extensions (US3 / T020-T021).

Covers:
- Happy-path registration of a compliant adapter (all four new fields set).
- V1 violation: pipa_class != non_personal + auth_level = public → ValidationError.
- V2 violation: pipa_class != non_personal + dpa_reference = None → ValidationError.
- V3 violation: auth_level disagrees with TOOL_MIN_AAL row → ValidationError.
- V4 violation: is_irreversible=True + auth_level=public → ValidationError.
- Omission of each of the four new fields → ValidationError at load time.
- Registry-scan invariant: all in-tree adapter modules register without exception (T021).

References: specs/024-tool-security-v1/spec.md, data-model.md §1.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil

import pytest
from pydantic import BaseModel, ValidationError

from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Minimal stub schemas shared across all test helpers
# ---------------------------------------------------------------------------


class _StubInput(BaseModel):
    query: str


class _StubOutput(BaseModel):
    result: str


# ---------------------------------------------------------------------------
# _MINIMAL_KWARGS: a fully-compliant GovAPITool kwargs dict.
# pipa_class=non_personal + auth_level=public satisfies V1/V2/V4.
# id=test_tool_ext does NOT appear in TOOL_MIN_AAL, so V3 passes too.
# ---------------------------------------------------------------------------

_MINIMAL_KWARGS: dict[str, object] = {
    "id": "test_tool_ext",
    "name_ko": "보안 확장 테스트 도구",
    "ministry": "OTHER",
    "category": ["test"],
    "endpoint": "https://apis.data.go.kr/test_ext",
    # V6 (FR-039/FR-040): baseline uses auth_type='public' so that the default
    # (public, public) pair is V6-allowed. V1–V5 negative tests that override
    # auth_level to AAL1/AAL2 also override auth_type where needed (or rely on
    # the earlier validator in the chain raising first).
    "auth_type": "public",
    "input_schema": _StubInput,
    "output_schema": _StubOutput,
    "search_hint": "test extension security 보안",
    # Security spec v1 fields — all four mandatory new fields:
    "auth_level": "public",
    "pipa_class": "non_personal",
    "is_irreversible": False,
    "dpa_reference": None,
    # V5 biconditional: auth_level='public' ⇔ requires_auth=False.
    "requires_auth": False,
    # FR-038: pipa_class=non_personal implies no PII, so is_personal_data=False.
    "is_personal_data": False,
}


def _make(**overrides: object) -> GovAPITool:
    """Build a GovAPITool from _MINIMAL_KWARGS with optional field overrides."""
    return GovAPITool(**{**_MINIMAL_KWARGS, **overrides})


# ===========================================================================
# TestGovAPIToolHappyPath
# ===========================================================================


class TestGovAPIToolHappyPath:
    """Happy-path: compliant adapter with all four fields registers in ToolRegistry."""

    def test_compliant_adapter_registers(self) -> None:
        """A fully-compliant adapter must register in ToolRegistry without error."""
        tool = _make()
        registry = ToolRegistry()
        # Must not raise
        registry.register(tool)
        assert "test_tool_ext" in registry


# ===========================================================================
# TestGovAPIToolValidatorV1
# ===========================================================================


class TestGovAPIToolValidatorV1:
    """V1 (FR-004): pipa_class != non_personal + auth_level = public → error."""

    def test_pipa_personal_with_public_auth_raises(self) -> None:
        """pipa_class=personal + auth_level=public must raise ValidationError (V1/FR-004)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v1_violation",
                pipa_class="personal",
                auth_level="public",
                dpa_reference="dpa-test-v1",  # satisfy V2 so only V1 triggers
            )
        err_str = str(exc_info.value)
        # Error must reference V1 or FR-004
        assert "V1" in err_str or "FR-004" in err_str, (
            f"ValidationError did not reference V1 or FR-004: {err_str!r}"
        )

    def test_pipa_sensitive_with_public_auth_raises(self) -> None:
        """pipa_class=sensitive + auth_level=public must also raise (V1/FR-004)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v1_sensitive",
                pipa_class="sensitive",
                auth_level="public",
                dpa_reference="dpa-sensitive-v1",
            )
        err_str = str(exc_info.value)
        assert "V1" in err_str or "FR-004" in err_str, (
            f"ValidationError did not reference V1 or FR-004: {err_str!r}"
        )

    def test_pipa_identifier_with_public_auth_raises(self) -> None:
        """pipa_class=identifier + auth_level=public must also raise (V1/FR-004)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v1_identifier",
                pipa_class="identifier",
                auth_level="public",
                dpa_reference="dpa-identifier-v1",
            )
        err_str = str(exc_info.value)
        assert "V1" in err_str or "FR-004" in err_str, (
            f"ValidationError did not reference V1 or FR-004: {err_str!r}"
        )


# ===========================================================================
# TestGovAPIToolValidatorV2
# ===========================================================================


class TestGovAPIToolValidatorV2:
    """V2 (FR-014): pipa_class != non_personal + dpa_reference = None → error."""

    def test_pipa_identifier_without_dpa_raises(self) -> None:
        """pipa_class=identifier + dpa_reference=None must raise ValidationError (V2/FR-014)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v2_violation",
                pipa_class="identifier",
                auth_level="AAL2",  # satisfy V1 (non-public)
                dpa_reference=None,  # V2 trigger
            )
        err_str = str(exc_info.value)
        assert "V2" in err_str or "FR-014" in err_str, (
            f"ValidationError did not reference V2 or FR-014: {err_str!r}"
        )

    def test_pipa_personal_without_dpa_raises(self) -> None:
        """pipa_class=personal + dpa_reference=None must raise ValidationError (V2/FR-014)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v2_personal",
                pipa_class="personal",
                auth_level="AAL1",  # satisfy V1
                dpa_reference=None,  # V2 trigger
            )
        err_str = str(exc_info.value)
        assert "V2" in err_str or "FR-014" in err_str, (
            f"ValidationError did not reference V2 or FR-014: {err_str!r}"
        )


# ===========================================================================
# TestGovAPIToolValidatorV3
# ===========================================================================


class TestGovAPIToolValidatorV3:
    """V3 (FR-001/FR-005): auth_level disagrees with TOOL_MIN_AAL row → error.

    Post Spec 031 T080: the legacy 8-verb table has been pruned to the four
    ``GovAPITool`` IDs still bound to V3 — ``lookup`` (AAL1),
    ``resolve_location`` (AAL1), ``nfa_emergency_info_service`` (AAL1), and
    ``mohw_welfare_eligibility_search`` (AAL2). The negative tests below pick
    two of those and present the wrong AAL to trigger V3.
    """

    def test_auth_level_disagreement_with_tool_min_aal_raises(self) -> None:
        """mohw_welfare_eligibility_search (AAL2 in TOOL_MIN_AAL) + auth_level=AAL1 → V3."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="mohw_welfare_eligibility_search",
                auth_type="api_key",  # V6: (api_key, AAL1) is allowed.
                auth_level="AAL1",  # conflicts with TOOL_MIN_AAL["mohw_..."] = "AAL2"
                pipa_class="personal",
                dpa_reference="dpa-ssis-v1",
                is_irreversible=False,
                requires_auth=True,  # V5: AAL1+ requires requires_auth=True.
                is_personal_data=True,
            )
        err_str = str(exc_info.value)
        # Error must reference V3 or FR-001 or FR-005
        assert "V3" in err_str or "FR-001" in err_str or "FR-005" in err_str, (
            f"ValidationError did not reference V3/FR-001/FR-005: {err_str!r}"
        )

    def test_pay_with_wrong_aal_raises(self) -> None:
        """nfa_emergency_info_service (AAL1 in TOOL_MIN_AAL) + auth_level=AAL2 → V3."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="nfa_emergency_info_service",
                auth_type="api_key",  # V6: (api_key, AAL2) is allowed.
                auth_level="AAL2",  # conflicts with TOOL_MIN_AAL["nfa_..."] = "AAL1"
                pipa_class="non_personal",  # NFA EMS stats are anonymized.
                dpa_reference=None,
                is_irreversible=False,
                requires_auth=True,  # V5: AAL1+ requires requires_auth=True.
                is_personal_data=False,
            )
        err_str = str(exc_info.value)
        assert "V3" in err_str or "FR-001" in err_str or "FR-005" in err_str, (
            f"ValidationError did not reference V3/FR-001/FR-005: {err_str!r}"
        )

    def test_lookup_with_correct_aal_passes(self) -> None:
        """id=lookup (AAL1 in TOOL_MIN_AAL) + auth_level=AAL1 must succeed (V3 green)."""
        tool = _make(
            id="lookup",
            auth_level="AAL1",  # correct — matches TOOL_MIN_AAL["lookup"]
            pipa_class="non_personal",
            dpa_reference=None,
            is_irreversible=False,
            requires_auth=True,  # V5: AAL1 requires requires_auth=True
        )
        assert tool.id == "lookup"
        assert tool.auth_level == "AAL1"


# ===========================================================================
# TestGovAPIToolValidatorV4
# ===========================================================================


class TestGovAPIToolValidatorV4:
    """V4 (FR-004 ext): is_irreversible=True + auth_level=public → error."""

    def test_irreversible_with_public_auth_raises(self) -> None:
        """is_irreversible=True + auth_level=public must raise ValidationError (V4/FR-004)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_v4_violation",
                is_irreversible=True,
                auth_level="public",  # V4 trigger: irreversible + public
                pipa_class="non_personal",
                dpa_reference=None,
            )
        err_str = str(exc_info.value)
        assert "V4" in err_str or "FR-004" in err_str, (
            f"ValidationError did not reference V4 or FR-004: {err_str!r}"
        )

    def test_irreversible_with_aal1_passes(self) -> None:
        """is_irreversible=True + auth_level=AAL1 must be accepted (V4 only blocks public)."""
        tool = _make(
            id="test_v4_aal1_ok",
            is_irreversible=True,
            auth_level="AAL1",  # non-public, so V4 does not apply
            pipa_class="personal",
            dpa_reference="dpa-test-v4",
            requires_auth=True,  # V5: AAL1 requires requires_auth=True
        )
        assert tool.is_irreversible is True
        assert tool.auth_level == "AAL1"


# ===========================================================================
# TestGovAPIToolFieldOmission
# ===========================================================================


class TestGovAPIToolFieldOmission:
    """Omitting any of the four new mandatory fields must raise ValidationError at load time."""

    def test_missing_auth_level_raises(self) -> None:
        """Missing auth_level must raise ValidationError (required field)."""
        kwargs = {k: v for k, v in _MINIMAL_KWARGS.items() if k != "auth_level"}
        with pytest.raises(ValidationError):
            GovAPITool(**kwargs)

    def test_missing_pipa_class_raises(self) -> None:
        """Missing pipa_class must raise ValidationError (required field)."""
        kwargs = {k: v for k, v in _MINIMAL_KWARGS.items() if k != "pipa_class"}
        with pytest.raises(ValidationError):
            GovAPITool(**kwargs)

    def test_missing_is_irreversible_raises(self) -> None:
        """Missing is_irreversible must raise ValidationError (required field)."""
        kwargs = {k: v for k, v in _MINIMAL_KWARGS.items() if k != "is_irreversible"}
        with pytest.raises(ValidationError):
            GovAPITool(**kwargs)

    def test_missing_dpa_reference_with_personal_pipa_raises(self) -> None:
        """dpa_reference=None with pipa_class=personal must fail (V2 validator).

        V2 rule: pipa_class != non_personal requires dpa_reference to be non-null.
        This test verifies the correct behavior: omitting dpa_reference (or passing
        None) when pipa_class is personal must fail.
        """
        with pytest.raises(ValidationError) as exc_info:
            _make(
                id="test_missing_dpa",
                pipa_class="personal",
                auth_level="AAL1",
                dpa_reference=None,  # V2 violation
            )
        err_str = str(exc_info.value)
        assert "V2" in err_str or "FR-014" in err_str or "dpa_reference" in err_str.lower(), (
            f"Expected V2/FR-014/dpa_reference in error: {err_str!r}"
        )

    def test_missing_dpa_reference_with_non_personal_pipa_passes(self) -> None:
        """dpa_reference=None with pipa_class=non_personal is allowed (V2 does not apply).

        This asserts correct behavior: when pipa_class=non_personal, dpa_reference
        may legitimately be None (no processor chain required).
        """
        tool = _make(pipa_class="non_personal", dpa_reference=None)
        assert tool.dpa_reference is None


# ===========================================================================
# TestAdapterRegistryScan (T021)
# ===========================================================================


class TestAdapterRegistryScan:
    """Registry-scan invariant: all in-tree adapters carry all four new fields (SC-003).

    Scans every Python module under the 4 canonical adapter provider packages:
      src/kosmos/tools/koroad/
      src/kosmos/tools/kma/
      src/kosmos/tools/hira/
      src/kosmos/tools/nmc/

    For each module, discovers any GovAPITool module-level instances and
    registers them in a fresh ToolRegistry. No exceptions must be raised.

    The count of discovered adapters MUST be >= 4 (koroad_accident_hazard_search,
    kma_forecast_fetch, hira_hospital_search, nmc_emergency_search per T008).
    """

    def test_all_in_tree_adapters_register_cleanly(self) -> None:  # noqa: C901 — walks 4 provider packages × module-level GovAPITool instances; splitting would obscure the SC-003 invariant
        """Every in-tree GovAPITool instance must register without exception (SC-003)."""
        # Provider packages that house the 4 seed adapters
        provider_packages = [
            "kosmos.tools.koroad",
            "kosmos.tools.kma",
            "kosmos.tools.hira",
            "kosmos.tools.nmc",
        ]

        discovered: list[tuple[str, GovAPITool]] = []

        for pkg_name in provider_packages:
            try:
                pkg = importlib.import_module(pkg_name)
            except ImportError as exc:
                logger.warning("Could not import package %s: %s", pkg_name, exc)
                continue

            pkg_path = getattr(pkg, "__path__", None)
            if pkg_path is None:
                continue

            for module_info in pkgutil.iter_modules(pkg_path):
                if module_info.name.startswith("_"):
                    continue  # skip __init__ and private utilities

                full_module_name = f"{pkg_name}.{module_info.name}"
                try:
                    mod = importlib.import_module(full_module_name)
                except ImportError as exc:
                    logger.warning("Could not import module %s: %s", full_module_name, exc)
                    continue

                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name, None)
                    if isinstance(attr, GovAPITool):
                        discovered.append((full_module_name, attr))
                        logger.debug(
                            "Discovered GovAPITool id=%s in %s",
                            attr.id,
                            full_module_name,
                        )

        # Guard: must discover >= 4 canonical seed adapters
        assert len(discovered) >= 4, (
            f"Expected >= 4 GovAPITool instances in provider packages, "
            f"found {len(discovered)}: {[f'{m}:{t.id}' for m, t in discovered]}"
        )

        # Register each discovered tool in a fresh registry — must not raise
        registry = ToolRegistry()
        registered_ids: list[str] = []

        for module_name, tool in discovered:
            # Some tools (e.g. nmc_emergency_search) share the same id across
            # multiple module-level variable aliases; skip duplicates.
            if tool.id in registered_ids:
                logger.debug(
                    "Skipping duplicate GovAPITool id=%s from %s",
                    tool.id,
                    module_name,
                )
                continue
            try:
                registry.register(tool)
                registered_ids.append(tool.id)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(
                    f"Tool id={tool.id!r} from module {module_name!r} raised "
                    f"{type(exc).__name__} during ToolRegistry.register(): {exc}"
                )

        assert len(registered_ids) >= 4, (
            f"Expected >= 4 distinct GovAPITool ids after registration, "
            f"got {len(registered_ids)}: {registered_ids}"
        )
