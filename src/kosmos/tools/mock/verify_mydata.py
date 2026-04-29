# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — mydata (마이데이터 OAuth 2.0 + mTLS).

Source mode: OOS — shape-mirrored from KFTC MyData v240930 specification
(마이데이터 표준 API 규격서, open-source schema).
FR-009 (delegation-only): no TLS private keys, no OAuth server logic. Fixture-backed.

Epic ε #2296 T022: retrofitted with six transparency fields per
contracts/mock-adapter-response-shape.md § 4 "EXISTING (retrofitted)" rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from kosmos.primitives.verify import (
    MyDataContext,
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
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/mydata"
_SECURITY_WRAPPING: Final = "마이데이터 표준동의서 OAuth2 + mTLS + finAuth"
_POLICY_AUTHORITY: Final = (
    "https://www.kftc.or.kr/kftc/main/EgovMenuContent.do?menuId=CNT020400"
)
_INTERNATIONAL_REF: Final = "Singapore Myinfo"

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_mydata",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_mydata",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="mydata_individual_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["마이데이터", "금융데이터", "금결원", "KFTC", "개인신용정보"],
        "en": ["mydata", "open banking", "KFTC mydata", "personal credit data"],
    },
    auth_type="oauth",
)

# Recorded fixture — provider_id is an anonymised test code.
_FIXTURE = MyDataContext.model_validate({
    "family": "mydata",
    "published_tier": "mydata_individual_aal2",
    "nist_aal_hint": "AAL2",
    "verified_at": datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    "external_session_ref": "mock-mydata-ref-001",
    "provider_id": "TEST_PROVIDER_001",
    # Six transparency fields (T022 retrofit)
    "_mode": "mock",
    "_reference_implementation": _REFERENCE_IMPL,
    "_actual_endpoint_when_live": _ACTUAL_ENDPOINT,
    "_security_wrapping_pattern": _SECURITY_WRAPPING,
    "_policy_authority": _POLICY_AUTHORITY,
    "_international_reference": _INTERNATIONAL_REF,
}, by_alias=True)


def invoke(session_context: dict[str, object]) -> MyDataContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        base = _FIXTURE.model_dump(by_alias=True)
        base.update(overrides)
        return MyDataContext.model_validate(base, by_alias=True)
    return _FIXTURE


register_verify_adapter("mydata", invoke)
