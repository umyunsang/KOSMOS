# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — mobile_id (모바일 신분증).

Source mode: OOS — shape-mirrored from Ministry of Interior and Safety
(행정안전부) 모바일 신분증 SDK reference documentation.
FR-009 (delegation-only): no signing keys, no credential issuer. Fixture-backed.
Default fixture uses 'mdl' (모바일운전면허). Test code may pass _fixture_override.

Epic ε #2296 T022: retrofitted with six transparency fields per
contracts/mock-adapter-response-shape.md § 4 "EXISTING (retrofitted)" rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from kosmos.primitives.verify import (
    MobileIdContext,
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
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/mobile_id"
_SECURITY_WRAPPING: Final = "OID4VP + DID-resolved RP + mTLS"
_POLICY_AUTHORITY: Final = (
    "https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do"
    "?bbsId=BBSMSTR_000000000016&nttId=104637"
)
_INTERNATIONAL_REF: Final = "EU EUDI Wallet"

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_mobile_id",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_mobile_id",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="mobile_id_mdl_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["모바일신분증", "모바일운전면허", "모바일주민등록증", "행정안전부"],
        "en": ["mobile id", "mobile driver license", "mdl", "mobile resident card"],
    },
    auth_type="oauth",
)

# Recorded fixture — default id_type is 'mdl' (모바일운전면허).
_FIXTURE = MobileIdContext.model_validate({
    "family": "mobile_id",
    "published_tier": "mobile_id_mdl_aal2",
    "nist_aal_hint": "AAL2",
    "verified_at": datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    "external_session_ref": "mock-mobile-id-ref-001",
    "id_type": "mdl",
    # Six transparency fields (T022 retrofit)
    "_mode": "mock",
    "_reference_implementation": _REFERENCE_IMPL,
    "_actual_endpoint_when_live": _ACTUAL_ENDPOINT,
    "_security_wrapping_pattern": _SECURITY_WRAPPING,
    "_policy_authority": _POLICY_AUTHORITY,
    "_international_reference": _INTERNATIONAL_REF,
}, by_alias=True)


def invoke(session_context: dict[str, object]) -> MobileIdContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        base = _FIXTURE.model_dump(by_alias=True)
        base.update(overrides)
        return MobileIdContext.model_validate(base, by_alias=True)
    return _FIXTURE


register_verify_adapter("mobile_id", invoke)
