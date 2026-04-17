# SPDX-License-Identifier: Apache-2.0
"""V6 validator tests — T003–T006 (US1: auth_type ↔ auth_level consistency invariant).

FR-039 / FR-040: Every GovAPITool construction must satisfy the canonical
(auth_type, auth_level) consistency invariant defined in _AUTH_TYPE_LEVEL_MAPPING.

Design: tests are purely pydantic-construction-based; no registry interaction.
All stub tools avoid colliding with TOOL_MIN_AAL canonical ids (validator V3)
by using tool ids that are not in that table.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

from kosmos.tools.models import _AUTH_TYPE_LEVEL_MAPPING, GovAPITool

# ---------------------------------------------------------------------------
# Minimal stub schemas
# ---------------------------------------------------------------------------


class _StubInput(BaseModel):
    """Minimal input schema for test tools."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str


class _StubOutput(RootModel[dict]):
    """Minimal output schema for test tools."""


# ---------------------------------------------------------------------------
# Helper: build minimal GovAPITool kwargs
# ---------------------------------------------------------------------------


def _make_tool(
    auth_type: str,
    auth_level: str,
    *,
    requires_auth: bool,
    tool_id: str = "test_tool",
) -> GovAPITool:
    """Construct a GovAPITool with minimal required fields.

    pipa_class / dpa_reference / is_irreversible are chosen to satisfy V1–V4
    so only the V5/V6 logic under test fires on the (auth_type, auth_level,
    requires_auth) triple provided by the caller.
    """
    return GovAPITool(
        id=tool_id,
        name_ko="테스트 도구",
        provider="Test Provider",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type=auth_type,  # type: ignore[arg-type]
        input_schema=_StubInput,
        output_schema=_StubOutput,
        search_hint="test stub tool search hint",
        auth_level=auth_level,  # type: ignore[arg-type]
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=requires_auth,
        is_personal_data=False,
        is_concurrency_safe=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
        is_core=False,
    )


# ---------------------------------------------------------------------------
# T003 — Positive parametrize: all 8 allowed (auth_type, auth_level) pairs
# ---------------------------------------------------------------------------

_ALLOWED_PAIRS = [
    # (auth_type, auth_level, requires_auth)
    # public auth_type: auth_level='public' → no-auth tool (requires_auth=False)
    ("public", "public", False),
    # public auth_type: auth_level='AAL1' → requires_auth=True per V5
    ("public", "AAL1", True),
    # api_key auth_type: all three AAL levels require auth
    ("api_key", "AAL1", True),
    ("api_key", "AAL2", True),
    ("api_key", "AAL3", True),
    # oauth auth_type: all three AAL levels require auth
    ("oauth", "AAL1", True),
    ("oauth", "AAL2", True),
    ("oauth", "AAL3", True),
]


@pytest.mark.parametrize(
    ("auth_type", "auth_level", "requires_auth"),
    _ALLOWED_PAIRS,
    ids=[f"{a}/{b}/requires_auth={c}" for a, b, c in _ALLOWED_PAIRS],
)
def test_v6_allows_compliant_auth_pairs(
    auth_type: str,
    auth_level: str,
    requires_auth: bool,
) -> None:
    """T003: All 8 canonical allowed (auth_type, auth_level) pairs construct without error."""
    tool = _make_tool(auth_type, auth_level, requires_auth=requires_auth, tool_id="stub_v6_pos")
    assert tool.auth_type == auth_type
    assert tool.auth_level == auth_level


# ---------------------------------------------------------------------------
# T004 — Negative parametrize: 4 disallowed (auth_type, auth_level) pairs
# ---------------------------------------------------------------------------

# For (api_key, public) and (oauth, public): V5 requires auth_level='public' ⇔
# requires_auth=False; we set requires_auth=False here so V5 passes and V6 fires
# (the cleaner approach per the spec context §5).
# For (public, AAL2) and (public, AAL3): V5 requires requires_auth=True for
# non-public auth_level, so we set requires_auth=True.
_DISALLOWED_PAIRS = [
    # Epic #654 canonical example
    ("public", "AAL2", True),
    ("public", "AAL3", True),
    # api_key/oauth with auth_level='public' — V5 happy (requires_auth=False), V6 fires
    ("api_key", "public", False),
    ("oauth", "public", False),
]


@pytest.mark.parametrize(
    ("auth_type", "auth_level", "requires_auth"),
    _DISALLOWED_PAIRS,
    ids=[f"{a}/{b}/requires_auth={c}" for a, b, c in _DISALLOWED_PAIRS],
)
def test_v6_rejects_disallowed_auth_pairs(
    auth_type: str,
    auth_level: str,
    requires_auth: bool,
) -> None:
    """T004: All 4 disallowed (auth_type, auth_level) pairs raise ValidationError.

    The error message must contain:
    - "V6 violation"
    - "auth_type"
    - "auth_level"
    - every element of the sorted allowed set for the offending auth_type
    """
    with pytest.raises(ValidationError) as exc_info:
        _make_tool(auth_type, auth_level, requires_auth=requires_auth, tool_id="stub_v6_neg")

    err_str = str(exc_info.value)
    assert "V6 violation" in err_str, f"Expected 'V6 violation' in error; got: {err_str!r}"
    assert "auth_type" in err_str, f"Expected 'auth_type' in error; got: {err_str!r}"
    assert "auth_level" in err_str, f"Expected 'auth_level' in error; got: {err_str!r}"

    # Every element of the sorted allowed set for this auth_type must appear
    allowed = sorted(_AUTH_TYPE_LEVEL_MAPPING[auth_type])
    for level in allowed:
        assert level in err_str, (
            f"Expected allowed level {level!r} to appear in error message; got: {err_str!r}"
        )


# ---------------------------------------------------------------------------
# T005 — Fail-closed branch: unknown auth_type (FR-048)
# ---------------------------------------------------------------------------


def test_v6_fail_closed_on_unknown_auth_type() -> None:
    """T005: FR-048 fail-closed branch fires when auth_type is not in the canonical mapping.

    Technique: GovAPITool.model_construct directly with auth_type='bogus_type'
    — this bypasses pydantic Literal validation at construction time, so the
    unknown auth_type is already present on the instance. Then call the
    validator method directly to prove the FR-048 fail-closed branch raises.
    This simulates a future widening of the Literal without a matching
    _AUTH_TYPE_LEVEL_MAPPING update.
    """
    # Build a valid tool first to get a proper GovAPITool instance
    valid_tool = _make_tool("public", "public", requires_auth=False, tool_id="stub_v6_fr048")

    # Use model_construct to build a new instance bypassing Literal validation
    tool = GovAPITool.model_construct(
        id="stub_v6_fr048",
        name_ko="테스트 도구",
        provider="Test Provider",
        category=["test"],
        endpoint="https://example.com/api",
        auth_type="bogus_type",  # bypasses Literal check
        input_schema=_StubInput,
        output_schema=_StubOutput,
        search_hint="test stub tool search hint",
        auth_level="AAL1",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=True,
        is_personal_data=False,
        is_concurrency_safe=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
        is_core=False,
    )
    # Confirm the bypass worked
    assert tool.auth_type == "bogus_type"

    # Call the validator directly — FR-048 branch must fire
    with pytest.raises(ValueError, match=r"V6 violation \(FR-048\)"):
        tool._validate_security_invariants()

    err_msg = ""
    try:
        tool._validate_security_invariants()
    except ValueError as exc:
        err_msg = str(exc)

    assert "unknown auth_type" in err_msg, (
        f"FR-048 error must mention 'unknown auth_type'; got: {err_msg!r}"
    )
    assert "_AUTH_TYPE_LEVEL_MAPPING" in err_msg, (
        f"FR-048 error must mention '_AUTH_TYPE_LEVEL_MAPPING'; got: {err_msg!r}"
    )

    # Prevent use of the valid_tool variable flagged as unused
    _ = valid_tool


# ---------------------------------------------------------------------------
# T006 — V5 interaction regression test
# ---------------------------------------------------------------------------


def test_v6_does_not_regress_v5_interaction() -> None:
    """T006: V6 validator does not break V5 interaction logic.

    Sub-assertion (a): (public, AAL1, requires_auth=True) — MVP meta-tool pattern —
    constructs cleanly. V5 permits AAL1 + requires_auth=True. V6 permits
    auth_type='public' with auth_level='AAL1'.

    Sub-assertion (b): (public, AAL2, requires_auth=True) raises a V6 error,
    not a V5 error. Confirms the error message contains "V6 violation"
    and NOT "V5 violation".
    """
    # (a) MVP meta-tool pattern must succeed
    tool = _make_tool("public", "AAL1", requires_auth=True, tool_id="stub_v6_meta")
    assert tool.auth_type == "public"
    assert tool.auth_level == "AAL1"

    # (b) public + AAL2 must raise with V6 message, not V5
    with pytest.raises(ValidationError) as exc_info:
        _make_tool("public", "AAL2", requires_auth=True, tool_id="stub_v6_v5v6")

    err_str = str(exc_info.value)
    assert "V6 violation" in err_str, f"Error should be from V6, not V5; got: {err_str!r}"
    assert "V5 violation" not in err_str, (
        f"Error should be V6 only, but V5 message appeared; got: {err_str!r}"
    )
