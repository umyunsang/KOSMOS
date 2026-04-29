# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — any_id_sso (통합 SSO / Any-ID Single Sign-On).

Epic ε #2296 — FR-001 (new verify mocks), FR-005 (transparency fields).

IMPORTANT: This adapter returns an ``IdentityAssertion`` (NOT a ``DelegationContext``).
Per data-model.md § 3 and research.md Decision 4:
    Any-ID SSO is identity-SSO only — it does NOT produce a delegation grant.
    A submit/lookup adapter receiving an IdentityAssertion MUST reject with
    DelegationGrantMissing (fail-closed, Constitution § II).

Source mode: HARNESS_ONLY — mirrors the AX-infrastructure-callable-channel
reference shape for UK GOV.UK One Login style SSO-only identity flow.

Contract: specs/2296-ax-mock-adapters/contracts/delegation-token-envelope.md § 1
Data model: specs/2296-ax-mock-adapters/data-model.md § 3
"""

from __future__ import annotations

import base64
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from kosmos.primitives.delegation import IdentityAssertion
from kosmos.primitives.verify import register_verify_adapter
from kosmos.tools.transparency import stamp_mock_response

# ---------------------------------------------------------------------------
# Per-adapter transparency constants (mock-adapter-response-shape.md § 4)
# ---------------------------------------------------------------------------

_REFERENCE_IMPL: Final = "ax-infrastructure-callable-channel"
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/any_id_sso"
_SECURITY_WRAPPING: Final = "OpenID Connect 1.0 + PKCE + session-bound SSO"
_POLICY_AUTHORITY: Final = (
    "https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do"
    "?bbsId=BBSMSTR_000000000016&nttId=104638"
)
_INTERNATIONAL_REF: Final = "UK GOV.UK One Login"

_TOOL_ID: Final = "mock_verify_module_any_id_sso"
_ISSUER_DID: Final = "did:web:anyid.go.kr"

# ---------------------------------------------------------------------------
# Bilingual search hint
# ---------------------------------------------------------------------------

SEARCH_HINT: Final[dict[str, list[str]]] = {
    "ko": ["통합SSO", "통합로그인", "Any-ID", "단일인증", "공공통합인증"],
    "en": ["any id sso", "unified login", "single sign on", "public SSO", "government sso"],
}


# ---------------------------------------------------------------------------
# JWS helper (Mock — no real cryptography)
# ---------------------------------------------------------------------------


def _mock_assertion_jwt(issued_at: datetime, expires_at: datetime) -> str:
    """Construct a deterministic Mock JWS triple for the identity assertion."""
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "id_token"}).encode())
        .rstrip(b"=")
        .decode()
    )
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "iss": _ISSUER_DID,
                    "sub": f"mock-citizen-{secrets.token_hex(4)}",
                    "iat": int(issued_at.timestamp()),
                    "exp": int(expires_at.timestamp()),
                }
            ).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header_b64}.{payload_b64}.mock-signature-not-cryptographic"


# ---------------------------------------------------------------------------
# invoke — registered via register_verify_adapter
# Returns IdentityAssertion — NOT DelegationContext (per Decision 4)
# ---------------------------------------------------------------------------


def invoke(session_context: dict[str, Any]) -> dict[str, Any]:
    """Return an IdentityAssertion for the Any-ID SSO channel.

    IMPORTANT: This adapter does NOT issue a DelegationToken. Downstream
    submit/lookup adapters MUST reject this with DelegationGrantMissing.

    session_context keys consumed:
    - ``session_id`` (str, optional): calling session UUID (for logging only).
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=1)  # SSO assertion is shorter-lived

    assertion = IdentityAssertion(
        assertion_jwt=_mock_assertion_jwt(now, expires_at),
        citizen_did=None,
        expires_at=expires_at,
        **{"_mode": "mock"},
    )

    # Stamp transparency fields on top of the identity assertion dict.
    domain_payload = assertion.model_dump(by_alias=True)
    return stamp_mock_response(
        domain_payload,
        reference_implementation=_REFERENCE_IMPL,
        actual_endpoint_when_live=_ACTUAL_ENDPOINT,
        security_wrapping_pattern=_SECURITY_WRAPPING,
        policy_authority=_POLICY_AUTHORITY,
        international_reference=_INTERNATIONAL_REF,
    )


register_verify_adapter("any_id_sso", invoke)
