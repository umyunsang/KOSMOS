# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — digital_onepass (Digital Onepass Level 1–3).

Source mode: OOS — shape-mirrored from OmniOne OpenDID reference stack (Apache-2.0).
FR-009 (delegation-only): no signing keys, no VC-issuer logic. Fixture-backed.
Default fixture uses Level 2 (AAL2). Test code may pass _fixture_override.
"""

from __future__ import annotations

from datetime import UTC, datetime

from kosmos.primitives.verify import (
    DigitalOnepassContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_digital_onepass",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_digital_onepass",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="digital_onepass_level2_aal2",
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["디지털원패스", "Digital Onepass", "행정안전부", "공공서비스 인증"],
        "en": ["digital onepass", "MOIS public auth", "digital_onepass"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_standard",
    is_irreversible=False,
    dpa_reference="PIPA §26 — 수탁자 처리 (위탁)",
)

# Recorded fixture — default Level 2.
_FIXTURE = DigitalOnepassContext(
    family="digital_onepass",
    published_tier="digital_onepass_level2_aal2",
    nist_aal_hint="AAL2",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    external_session_ref="mock-onepass-ref-001",
    level=2,
)


def invoke(session_context: dict[str, object]) -> DigitalOnepassContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        return DigitalOnepassContext.model_validate({**_FIXTURE.model_dump(), **overrides})
    return _FIXTURE


register_verify_adapter("digital_onepass", invoke)
