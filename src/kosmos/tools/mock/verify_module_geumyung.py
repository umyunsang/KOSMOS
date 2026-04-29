# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — geumyung (금융인증서 / Financial Certificate AX-channel).

Epic ε #2296 — FR-001 (new verify mocks), FR-005 (transparency fields).

Source mode: HARNESS_ONLY — mirrors the public-mydata-read-v240930 reference
shape for the KFTC 금융인증서 (Financial Certificate) channel.
Issues a DelegationToken with 마이데이터 표준동의서 OAuth2 + finAuth envelope.

Contract: specs/2296-ax-mock-adapters/contracts/delegation-token-envelope.md § 1
Data model: specs/2296-ax-mock-adapters/data-model.md § 1-2
"""

from __future__ import annotations

import base64
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from kosmos.memdir.consent_ledger import DelegationIssuedEvent, append_delegation_issued
from kosmos.primitives.delegation import DelegationContext, DelegationToken
from kosmos.primitives.verify import GeumyungModuleContext, register_verify_adapter
from kosmos.tools.transparency import stamp_mock_response

# ---------------------------------------------------------------------------
# Per-adapter transparency constants (mock-adapter-response-shape.md § 4)
# ---------------------------------------------------------------------------

_REFERENCE_IMPL: Final = "public-mydata-read-v240930"
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/geumyung"
_SECURITY_WRAPPING: Final = "마이데이터 표준동의서 OAuth2 + finAuth"
_POLICY_AUTHORITY: Final = "https://www.kftc.or.kr/kftc/main/EgovMenuContent.do?menuId=CNT020400"
_INTERNATIONAL_REF: Final = "Singapore Myinfo"

_TOOL_ID: Final = "mock_verify_module_geumyung"
_ISSUER_DID: Final = "did:web:kftc.or.kr"

# ---------------------------------------------------------------------------
# Bilingual search hint
# ---------------------------------------------------------------------------

SEARCH_HINT: Final[dict[str, list[str]]] = {
    "ko": ["금융인증서", "금결원", "KFTC", "은행인증", "핀인증"],
    "en": ["financial certificate", "KFTC finAuth", "geumyung injeungseo", "fin auth"],
}


# ---------------------------------------------------------------------------
# JWS helper (Mock — no real cryptography)
# ---------------------------------------------------------------------------


def _mock_vp_jwt(scope: str, issued_at: datetime, expires_at: datetime) -> str:
    """Construct a deterministic Mock JWS triple (header.payload.signature)."""
    header_b64 = (
        base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "vp+jwt"}).encode())
        .rstrip(b"=")
        .decode()
    )
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "iss": _ISSUER_DID,
                    "scope": scope,
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
# ---------------------------------------------------------------------------


def invoke(session_context: dict[str, Any]) -> GeumyungModuleContext:
    """Issue a DelegationToken for the 금융인증서 AX channel.

    session_context keys consumed:
    - ``scope_list`` (list[str], required): scopes to embed in the token.
    - ``session_id`` (str, optional): calling session UUID for ledger.
    - ``purpose_ko`` (str, optional): Korean purpose statement.
    - ``purpose_en`` (str, optional): English purpose statement.
    - ``ledger_root`` (Path, optional): test override for ledger directory.
    """
    scope_list: list[str] = session_context.get("scope_list", ["verify:geumyung.identity"])
    scope_str = ",".join(scope_list)
    session_id: str = session_context.get("session_id", "mock-session-unknown")
    purpose_ko: str = session_context.get("purpose_ko", "금융인증서 신원확인")
    purpose_en: str = session_context.get(
        "purpose_en", "Financial-certificate identity verification (KFTC finAuth)"
    )

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=24)
    raw_token = f"del_{secrets.token_urlsafe(24)}"

    token = DelegationToken(
        vp_jwt=_mock_vp_jwt(scope_str, now, expires_at),
        delegation_token=raw_token,
        scope=scope_str,
        issuer_did=_ISSUER_DID,
        issued_at=now,
        expires_at=expires_at,
    )
    context = DelegationContext(
        token=token,
        citizen_did=None,
        purpose_ko=purpose_ko,
        purpose_en=purpose_en,
    )

    # Append delegation_issued ledger event.
    ledger_root = session_context.get("ledger_root")
    ledger_event = DelegationIssuedEvent(
        ts=now,
        session_id=session_id,
        delegation_token=raw_token,
        scope=scope_str,
        expires_at=expires_at,
        issuer_did=_ISSUER_DID,
        verify_tool_id=_TOOL_ID,
    )
    append_delegation_issued(ledger_event, ledger_root=ledger_root)

    # Build the transparency dict via stamp_mock_response on an empty payload —
    # we need the six stamped fields to populate the typed context (Spec 031
    # AuthContext envelope wraps the DelegationContext + carries transparency).
    transparency = stamp_mock_response(
        {},
        reference_implementation=_REFERENCE_IMPL,
        actual_endpoint_when_live=_ACTUAL_ENDPOINT,
        security_wrapping_pattern=_SECURITY_WRAPPING,
        policy_authority=_POLICY_AUTHORITY,
        international_reference=_INTERNATIONAL_REF,
    )

    # Return a typed AuthContext variant so verify(family_hint=...) accepts it
    # (Codex P1 #2446 fix). The wrapped DelegationContext carries the OID4VP
    # envelope; the six aliased transparency fields surface in model_dump(by_alias).
    return GeumyungModuleContext.model_validate(
        {
            "published_tier": "geumyung_module_aal3",
            "nist_aal_hint": "AAL3",
            "verified_at": now,
            "delegation_context": context,
            **transparency,
        }
    )


register_verify_adapter("geumyung_module", invoke)
