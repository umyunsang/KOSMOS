# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — ganpyeon_injeung (간편인증 — Kakao/Naver/Toss/PASS/etc.).

Source mode: OOS — shape-mirrored from Barocert developers.barocert.com SDK docs.
FR-009 (delegation-only): no signing keys, no CA logic. Fixture-backed.
Default fixture uses 'kakao' provider. Test code may pass _fixture_override.
"""

from __future__ import annotations

from datetime import UTC, datetime

from kosmos.primitives.verify import (
    GanpyeonInjeungContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_ganpyeon_injeung",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_ganpyeon_injeung",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="ganpyeon_injeung_kakao_aal2",
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["간편인증", "카카오인증", "네이버인증", "토스인증", "PASS", "삼성패스"],
        "en": ["simple auth", "kakao cert", "naver cert", "toss cert", "PASS", "ganpyeon injeung"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_standard",
    is_irreversible=False,
    dpa_reference="PIPA §26 — 수탁자 처리 (위탁)",
)

# Recorded fixture — default provider is 'kakao'.
_FIXTURE = GanpyeonInjeungContext(
    family="ganpyeon_injeung",
    published_tier="ganpyeon_injeung_kakao_aal2",
    nist_aal_hint="AAL2",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    external_session_ref="mock-ganpyeon-ref-001",
    provider="kakao",
)


def invoke(session_context: dict[str, object]) -> GanpyeonInjeungContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        return GanpyeonInjeungContext.model_validate({**_FIXTURE.model_dump(), **overrides})
    return _FIXTURE


register_verify_adapter("ganpyeon_injeung", invoke)
