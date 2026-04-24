# SPDX-License-Identifier: Apache-2.0
"""T075 — Registry-regression test: Spec 024/025 invariants preserved under v1.2 GA toggle.

Asserts that V1 (FR-004), V3 (FR-001/FR-005), and V6 (FR-039/FR-040) validators
still fire on ``GovAPITool`` construction when ``V12_GA_ACTIVE=True``. The v1.2
cutover (flipping the toggle) MUST NOT weaken any Spec 024 / Spec 025 shipped
invariant (FR-028).

For each invariant:
  - Negative control: construction with a violating field set raises ``ValueError``.
  - Positive control: construction with a compliant field set succeeds.

Expected state: ALL tests GREEN immediately (V1/V3/V6 live on GovAPITool
model_validator and are independent of the v12_dual_axis toggle). If any test
is red, a regression in the validator chain has been introduced.

References:
- specs/031-five-primitive-harness/spec.md FR-028
- specs/031-five-primitive-harness/tasks.md T075
- specs/024-tool-security-v1 data-model.md §1 (V1–V5)
- specs/025-tool-security-v6 data-model.md §1 (V6)
- src/kosmos/tools/models.py _validate_security_invariants
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from kosmos.tools.models import GovAPITool

# ---------------------------------------------------------------------------
# Minimal Pydantic stubs for input_schema / output_schema
# ---------------------------------------------------------------------------


class _FakeInput(BaseModel):
    """Minimal input schema for GovAPITool construction in tests."""

    query: str = ""


class _FakeOutput(BaseModel):
    """Minimal output schema for GovAPITool construction in tests."""

    result: str = ""


# ---------------------------------------------------------------------------
# Baseline compliant kwargs factory
# ---------------------------------------------------------------------------

# ``lookup`` is in TOOL_MIN_AAL (="AAL1"). For tests that do NOT want to
# exercise V3, we use an id not in TOOL_MIN_AAL so the V3 branch is skipped.
_NON_CANONICAL_ID = "fake_tool_for_v1_v6_test"
# ``lookup`` IS in TOOL_MIN_AAL (="AAL1") — used for V3 tests specifically.
_CANONICAL_LOOKUP_ID = "lookup"


def _compliant_kwargs(**overrides: object) -> dict[str, object]:
    """Minimum valid GovAPITool kwargs.

    Baseline: non_personal pipa_class (skips V1/V2), api_key auth_type
    with AAL2 auth_level (V6-safe), id not in TOOL_MIN_AAL (skips V3),
    requires_auth=True (V5-safe for AAL2).
    """
    base: dict[str, object] = {
        "id": _NON_CANONICAL_ID,
        "name_ko": "테스트 도구",
        "ministry": "OTHER",
        "category": ["test"],
        "endpoint": "https://api.example.com/test",
        "auth_type": "api_key",
        "input_schema": _FakeInput,
        "output_schema": _FakeOutput,
        "search_hint": "test tool for security spec preservation",
        "auth_level": "AAL2",
        "pipa_class": "non_personal",
        "is_irreversible": False,
        "dpa_reference": None,
        "requires_auth": True,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# V1 (FR-004): pipa_class != "non_personal" with auth_level="public" → ValueError
# ---------------------------------------------------------------------------


def test_v1_fires_when_pii_tool_declares_public_auth_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V1 violation: pipa_class='personal' + auth_level='public' → ValueError mentioning 'V1'.

    The v1.2 toggle does NOT affect this validator — it lives entirely in
    GovAPITool._validate_security_invariants() (Spec 024 contract).
    """
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    with pytest.raises((ValidationError, ValueError)) as exc_info:
        GovAPITool(
            **_compliant_kwargs(
                pipa_class="personal",
                auth_level="public",
                # V5: auth_level="public" → requires_auth must be False.
                requires_auth=False,
                # V2: pipa_class != non_personal → dpa_reference must be set.
                dpa_reference="kosmos_mock_mvp_v1",
            )
        )

    err_str = str(exc_info.value)
    assert "V1" in err_str, (
        f"Expected 'V1' in the error message for a pipa_class/auth_level violation. "
        f"Got: {err_str!r}"
    )


def test_v1_positive_control_pii_tool_with_aal1_constructs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V1 positive control: pipa_class='personal' + auth_level='AAL1' → succeeds.

    Proves the toggle does not block compliant constructions.
    """
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    tool = GovAPITool(
        **_compliant_kwargs(
            id="pii_tool_aal1_v1",
            pipa_class="personal",
            auth_level="AAL1",
            auth_type="api_key",
            requires_auth=True,
            dpa_reference="kosmos_mock_mvp_v1",
        )
    )
    assert tool.pipa_class == "personal"
    assert tool.auth_level == "AAL1"


# ---------------------------------------------------------------------------
# V3 (FR-001/FR-005): id in TOOL_MIN_AAL with wrong auth_level → ValueError
# ---------------------------------------------------------------------------


def test_v3_fires_when_lookup_declares_wrong_auth_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V3 violation: id='lookup' (TOOL_MIN_AAL='AAL1') + auth_level='AAL2' → ValueError 'V3'.

    TOOL_MIN_AAL is the single source of truth; drift is a load-time failure.
    The v1.2 toggle does NOT affect this validator.
    """
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    with pytest.raises((ValidationError, ValueError)) as exc_info:
        GovAPITool(
            **_compliant_kwargs(
                id=_CANONICAL_LOOKUP_ID,
                auth_level="AAL2",  # TOOL_MIN_AAL requires AAL1
                auth_type="api_key",
                requires_auth=True,
                pipa_class="non_personal",
                dpa_reference=None,
            )
        )

    err_str = str(exc_info.value)
    assert "V3" in err_str, (
        f"Expected 'V3' in the error message for a TOOL_MIN_AAL drift violation. Got: {err_str!r}"
    )


def test_v3_positive_control_lookup_with_aal1_constructs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V3 positive control: id='lookup' + auth_level='AAL1' (matches TOOL_MIN_AAL) → succeeds."""
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    tool = GovAPITool(
        **_compliant_kwargs(
            id=_CANONICAL_LOOKUP_ID,
            auth_level="AAL1",  # matches TOOL_MIN_AAL["lookup"]
            auth_type="api_key",
            requires_auth=True,
            pipa_class="non_personal",
            dpa_reference=None,
        )
    )
    assert tool.id == "lookup"
    assert tool.auth_level == "AAL1"


# ---------------------------------------------------------------------------
# V6 (FR-039/FR-040): auth_type="public" with auth_level="AAL3" → ValueError
# ---------------------------------------------------------------------------


def test_v6_fires_when_public_auth_type_declares_aal3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V6 violation: auth_type='public' + auth_level='AAL3' → ValueError mentioning 'V6'.

    The canonical mapping: public ⇒ {public, AAL1}. AAL3 is outside this set.
    The v1.2 toggle does NOT affect this validator.
    """
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    with pytest.raises((ValidationError, ValueError)) as exc_info:
        GovAPITool(
            **_compliant_kwargs(
                id="fake_v6_violation_tool",
                auth_type="public",
                auth_level="AAL3",  # outside {public, AAL1} for auth_type="public"
                pipa_class="non_personal",
                dpa_reference=None,
                requires_auth=True,  # V5: AAL3 → requires_auth=True
            )
        )

    err_str = str(exc_info.value)
    assert "V6" in err_str, (
        f"Expected 'V6' in the error message for an auth_type↔auth_level "
        f"allow-list violation. Got: {err_str!r}"
    )


def test_v6_positive_control_public_auth_type_with_aal1_constructs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V6 positive control: auth_type='public' + auth_level='AAL1' → succeeds.

    (public, AAL1) is in the canonical allow-list per _AUTH_TYPE_LEVEL_MAPPING.
    MVP meta-tool pattern (public, AAL1) + requires_auth=True is documented as
    compliant per Spec 025 v1.1 worked examples.
    """
    import kosmos.security.v12_dual_axis as _mod

    monkeypatch.setattr(_mod, "V12_GA_ACTIVE", True)

    tool = GovAPITool(
        **_compliant_kwargs(
            id="fake_v6_compliant_tool",
            auth_type="public",
            auth_level="AAL1",
            pipa_class="non_personal",
            dpa_reference=None,
            # V5: auth_level != "public" → requires_auth=True required.
            requires_auth=True,
        )
    )
    assert tool.auth_type == "public"
    assert tool.auth_level == "AAL1"
