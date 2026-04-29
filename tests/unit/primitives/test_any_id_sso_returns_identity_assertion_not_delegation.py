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
    """any_id_sso must return AnyIdSsoContext wrapping IdentityAssertion (NOT DelegationContext).

    Spec 2296 Codex P1 #2446 fix: invoke() now returns a typed AuthContext variant
    instead of a stamped dict, so the verify(family_hint='any_id_sso') dispatcher path
    works. The wrapped envelope is IdentityAssertion (no delegation grant).
    """
    from kosmos.primitives.verify import AnyIdSsoContext
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-sso"})

    assert isinstance(result, AnyIdSsoContext), (
        f"Expected AnyIdSsoContext, got {type(result).__name__}"
    )
    # AnyIdSsoContext carries identity_assertion, NOT delegation_context.
    assert hasattr(result, "identity_assertion"), "AnyIdSsoContext must carry 'identity_assertion'"
    assert not hasattr(result, "delegation_context"), (
        "AnyIdSsoContext must NOT carry 'delegation_context' — any_id_sso is "
        "SSO-only per delegation-flow-design.md § 2.2."
    )


def test_any_id_sso_has_no_scope_field() -> None:
    """IdentityAssertion does not carry a 'scope' field (no delegation)."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-sso-2"})
    assert not hasattr(result.identity_assertion, "scope"), (
        "IdentityAssertion must NOT carry 'scope' — any_id_sso is identity-only."
    )


def test_any_id_sso_assertion_jwt_jws_shape() -> None:
    """assertion_jwt must be a dot-separated JWS with 3 parts."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-jws"})
    parts = result.identity_assertion.assertion_jwt.split(".")
    assert len(parts) == 3, (
        f"assertion_jwt must be header.payload.signature, got {len(parts)} parts"
    )


# ---------------------------------------------------------------------------
# (b) Six transparency fields present
# ---------------------------------------------------------------------------


def test_any_id_sso_returns_transparency_fields() -> None:
    """invoke() carries all six transparency fields non-empty on the typed context."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "test-sess-transparency"})

    assert result.transparency_mode == "mock"
    for field in (
        "transparency_reference_implementation",
        "transparency_actual_endpoint_when_live",
        "transparency_security_wrapping_pattern",
        "transparency_policy_authority",
        "transparency_international_reference",
    ):
        value = getattr(result, field)
        assert value is not None and isinstance(value, str) and value.strip(), (
            f"any_id_sso missing or empty transparency field {field!r}"
        )


def test_any_id_sso_international_reference() -> None:
    """transparency_international_reference must be 'UK GOV.UK One Login'."""
    from kosmos.tools.mock.verify_module_any_id_sso import invoke

    result = invoke({"session_id": "s1"})
    assert result.transparency_international_reference == "UK GOV.UK One Login"


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

    # The Spec 2296 Codex P1 #2446 fix made the result a typed AnyIdSsoContext
    # instead of a stamped dict. To assert the fail-closed contract, we serialise
    # the wrapped IdentityAssertion to dict and try to parse it as DelegationContext;
    # this MUST fail (no `token` field on IdentityAssertion).
    from pydantic import ValidationError

    from kosmos.primitives.delegation import DelegationContext

    assertion_dump = sso_result.identity_assertion.model_dump(by_alias=True)
    with pytest.raises((ValidationError, KeyError, TypeError)):
        DelegationContext.model_validate(assertion_dump)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_any_id_sso_is_registered() -> None:
    """Importing the module registers 'any_id_sso' in _VERIFY_ADAPTERS."""
    import kosmos.tools.mock.verify_module_any_id_sso  # noqa: F401
    from kosmos.primitives.verify import _VERIFY_ADAPTERS

    assert "any_id_sso" in _VERIFY_ADAPTERS
