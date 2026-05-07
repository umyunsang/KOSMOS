# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — ganpyeon_injeung (간편인증 — Kakao/Naver/Toss/PASS/etc.).

Source mode: OOS — shape-mirrored from Barocert developers.barocert.com SDK docs.
FR-009 (delegation-only): no signing keys, no CA logic. Fixture-backed.
Default fixture uses 'kakao' provider. Test code may pass _fixture_override.

Epic ε #2296 T022: retrofitted with six transparency fields per
contracts/mock-adapter-response-shape.md § 4 "EXISTING (retrofitted)" rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from kosmos.primitives.verify import (
    GanpyeonInjeungContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

# ---------------------------------------------------------------------------
# Per-adapter transparency constants (mock-adapter-response-shape.md § 4)
# ---------------------------------------------------------------------------

_REFERENCE_IMPL: Final = "public-mydata-read-v240930"
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/ganpyeon_injeung"
_SECURITY_WRAPPING: Final = "OAuth2.1 + PKCE + app-to-app redirect"
_POLICY_AUTHORITY: Final = (
    "https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do"
    "?bbsId=BBSMSTR_000000000016&nttId=104636"
)
_INTERNATIONAL_REF: Final = "Japan JPKI"

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_ganpyeon_injeung",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_ganpyeon_injeung",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="ganpyeon_injeung_kakao_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["간편인증", "카카오인증", "네이버인증", "토스인증", "PASS", "삼성패스"],
        "en": ["simple auth", "kakao cert", "naver cert", "toss cert", "PASS", "ganpyeon injeung"],
    },
    auth_type="oauth",
)

# Recorded fixture — default provider is 'kakao'.
_FIXTURE = GanpyeonInjeungContext.model_validate(
    {
        "family": "ganpyeon_injeung",
        "published_tier": "ganpyeon_injeung_kakao_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
        "external_session_ref": "mock-ganpyeon-ref-001",
        "provider": "kakao",
        # Six transparency fields (T022 retrofit)
        "_mode": "mock",
        "_reference_implementation": _REFERENCE_IMPL,
        "_actual_endpoint_when_live": _ACTUAL_ENDPOINT,
        "_security_wrapping_pattern": _SECURITY_WRAPPING,
        "_policy_authority": _POLICY_AUTHORITY,
        "_international_reference": _INTERNATIONAL_REF,
    },
    by_alias=True,
)


def invoke(session_context: dict[str, object]) -> GanpyeonInjeungContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        base = _FIXTURE.model_dump(by_alias=True)
        base.update(overrides)
        return GanpyeonInjeungContext.model_validate(base, by_alias=True)
    return _FIXTURE


register_verify_adapter("ganpyeon_injeung", invoke)
