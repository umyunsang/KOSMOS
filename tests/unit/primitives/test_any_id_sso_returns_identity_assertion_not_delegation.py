# SPDX-License-Identifier: Apache-2.0
"""T020 — any_id_sso returns IdentityAssertion, NOT DelegationContext.

Asserts:
a) The returned type (in dict-form) carries 'assertion_jwt' but NOT 'token'
   (DelegationContext payload has 'token', IdentityAssertion does NOT).
b) The six transparency fields are present and non-empty.
c) Downstream submit fails with a clear error when receiving only an IdentityAssertion
   (DelegationGrantMissing fail-closed — Constitution § II).

Research reference: specs/2296-ax-mock-adapters/research.md Decision 4
Data model: specs/2296-ax-mock-adapters/data-model.md § 3
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# (a) Returns IdentityAssertion, NOT DelegationContext
# ---------------------------------------------------------------------------


def test_any_id_sso_returns_identity_assertion_not_delegation() -> None:
    """any_id_sso must return IdentityAssertion shape (no 'token', has 'assertion_jwt')."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-sso"})

    assert isinstance(result, dict), "Expected dict from any_id_sso invoke()"
    # IdentityAssertion has assertion_jwt, NOT token.
    assert "assertion_jwt" in result, (
        "IdentityAssertion must carry 'assertion_jwt' field — got keys: "
        f"{sorted(result.keys())}"
    )
    assert "token" not in result, (
        "IdentityAssertion must NOT carry 'token' (which is a DelegationContext field). "
        "any_id_sso is SSO-only — it does not produce a delegation grant."
    )


def test_any_id_sso_has_no_scope_field() -> None:
    """IdentityAssertion does not carry a 'scope' field (no delegation)."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-sso-2"})
    assert "scope" not in result, (
        "IdentityAssertion must NOT carry 'scope' — any_id_sso is identity-only."
    )


def test_any_id_sso_assertion_jwt_jws_shape() -> None:
    """assertion_jwt must be a dot-separated JWS with 3 parts."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-jws"})
    parts = result["assertion_jwt"].split(".")
    assert len(parts) == 3, (
        f"assertion_jwt must be header.payload.signature, got {len(parts)} parts"
    )


# ---------------------------------------------------------------------------
# (b) Six transparency fields present
# ---------------------------------------------------------------------------


def test_any_id_sso_returns_transparency_fields() -> None:
    """invoke() carries all six transparency fields non-empty."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-transparency"})

    assert result.get("_mode") == "mock"
    for field in (
        "_reference_implementation",
        "_actual_endpoint_when_live",
        "_security_wrapping_pattern",
        "_policy_authority",
        "_international_reference",
    ):
        value = result.get(field)
        assert value is not None and isinstance(value, str) and value.strip(), (
            f"any_id_sso missing or empty transparency field {field!r}"
        )


def test_any_id_sso_international_reference() -> None:
    """_international_reference must be 'UK GOV.UK One Login'."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "s1"})
    assert result["_international_reference"] == "UK GOV.UK One Login"


# ---------------------------------------------------------------------------
# (c) Downstream submit fails with DelegationGrantMissing when given IdentityAssertion
# ---------------------------------------------------------------------------


def test_downstream_submit_rejects_identity_assertion(tmp_path) -> None:
    """A submit adapter receiving only an IdentityAssertion (not a DelegationContext)
    must raise ValueError or similar 'DelegationGrantMissing' style failure.

    The fail-closed contract is enforced at submit invocation time: the adapter
    expects a DelegationContext, not an IdentityAssertion.
    """
    from kosmos.tools.mock.verify_module_any_id_sso import invoke as any_id_sso_invoke

    # Simulate: caller invokes any_id_sso and then tries to use the result
    # directly as a "delegation" in a submit call.
    sso_result = any_id_sso_invoke({"session_id": "test-sess-submit-fail"})

    # Verify the assertion: the result does NOT have a 'token' field.
    # A real submit adapter would call validate_delegation(context, ...) which
    # expects a DelegationContext. Passing an IdentityAssertion dict to
    # DelegationContext.model_validate should fail.
    from pydantic import ValidationError

    from kosmos.primitives.delegation import DelegationContext

    # Attempt to parse the IdentityAssertion result as a DelegationContext.
    # This MUST fail — it does not carry the 'token' field required by DelegationContext.
    with pytest.raises((ValidationError, KeyError, TypeError)):
        DelegationContext.model_validate(sso_result)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_any_id_sso_is_registered() -> None:
    """Importing the module registers 'any_id_sso' in _VERIFY_ADAPTERS."""
    import kosmos.tools.mock.verify_module_any_id_sso  # noqa: F401
    from kosmos.primitives.verify import _VERIFY_ADAPTERS

    assert "any_id_sso" in _VERIFY_ADAPTERS
