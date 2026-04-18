# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — mobile_id (모바일 신분증).

Source mode: OOS — shape-mirrored from Ministry of Interior and Safety
(행정안전부) 모바일 신분증 SDK reference documentation.
FR-009 (delegation-only): no signing keys, no credential issuer. Fixture-backed.
Default fixture uses 'mdl' (모바일운전면허). Test code may pass _fixture_override.
"""

from __future__ import annotations

from datetime import datetime, timezone

from kosmos.primitives.verify import (
    MobileIdContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_mobile_id",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_mobile_id",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="mobile_id_mdl_aal2",
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["모바일신분증", "모바일운전면허", "모바일주민등록증", "행정안전부"],
        "en": ["mobile id", "mobile driver license", "mdl", "mobile resident card"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_unique_id",
    is_irreversible=False,
    dpa_reference="PIPA §26 — 수탁자 처리 (위탁)",
)

# Recorded fixture — default id_type is 'mdl' (모바일운전면허).
_FIXTURE = MobileIdContext(
    family="mobile_id",
    published_tier="mobile_id_mdl_aal2",
    nist_aal_hint="AAL2",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=timezone.utc),
    external_session_ref="mock-mobile-id-ref-001",
    id_type="mdl",
)


def invoke(session_context: dict[str, object]) -> MobileIdContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[arg-type]
        return MobileIdContext.model_validate(
            {**_FIXTURE.model_dump(), **overrides}
        )
    return _FIXTURE


register_verify_adapter("mobile_id", invoke)
