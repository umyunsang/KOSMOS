# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — gongdong_injeungseo (공동인증서 / KOSCOM Joint Certificate).

Source mode: OOS — shape-mirrored from PyPinkSign / KFTC API docs.
FR-009 (delegation-only): no signing keys, no CA logic. Fixture-backed.

Epic ε #2296 T022: retrofitted with six transparency fields per
contracts/mock-adapter-response-shape.md § 4 "EXISTING (retrofitted)" rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from kosmos.primitives.verify import (
    GongdongInjeungseoContext,
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
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/verify/gongdong_injeungseo"
_SECURITY_WRAPPING: Final = "PKCS#7 + TLS 1.3 + scope-bound bearer"
_POLICY_AUTHORITY: Final = "https://www.rootca.or.kr/kor/accredited/accredited01.do"
_INTERNATIONAL_REF: Final = "Estonia X-Road (NPKI analog)"

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_gongdong_injeungseo",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_gongdong_injeungseo",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="gongdong_injeungseo_personal_aal3",
    nist_aal_hint="AAL3",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["공동인증서", "공인인증서", "KICA", "KOSCOM"],
        "en": ["joint certificate", "NPKI", "gongdong injeungseo"],
    },
    auth_type="oauth",
)

# Recorded fixture — no real external calls (FR-009).
_FIXTURE = GongdongInjeungseoContext.model_validate(
    {
        "family": "gongdong_injeungseo",
        "published_tier": "gongdong_injeungseo_personal_aal3",
        "nist_aal_hint": "AAL3",
        "verified_at": datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
        "external_session_ref": "mock-gongdong-ref-001",
        "certificate_issuer": "KICA",
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


def invoke(session_context: dict[str, object]) -> GongdongInjeungseoContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        base = _FIXTURE.model_dump(by_alias=True)
        base.update(overrides)
        return GongdongInjeungseoContext.model_validate(base, by_alias=True)
    return _FIXTURE


register_verify_adapter("gongdong_injeungseo", invoke)
