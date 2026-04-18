# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — mydata (마이데이터 OAuth 2.0 + mTLS).

Source mode: OOS — shape-mirrored from KFTC MyData v240930 specification
(마이데이터 표준 API 규격서, open-source schema).
FR-009 (delegation-only): no TLS private keys, no OAuth server logic. Fixture-backed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from kosmos.primitives.verify import (
    MyDataContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_mydata",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_mydata",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="mydata_individual_aal2",
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["마이데이터", "금융데이터", "금결원", "KFTC", "개인신용정보"],
        "en": ["mydata", "open banking", "KFTC mydata", "personal credit data"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_sensitive",
    is_irreversible=False,
    dpa_reference="PIPA §26 — 수탁자 처리 (위탁); 신용정보법 §33의2",
)

# Recorded fixture — provider_id is an anonymised test code.
_FIXTURE = MyDataContext(
    family="mydata",
    published_tier="mydata_individual_aal2",
    nist_aal_hint="AAL2",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=timezone.utc),
    external_session_ref="mock-mydata-ref-001",
    provider_id="TEST_PROVIDER_001",
)


def invoke(session_context: dict[str, object]) -> MyDataContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[arg-type]
        return MyDataContext.model_validate(
            {**_FIXTURE.model_dump(), **overrides}
        )
    return _FIXTURE


register_verify_adapter("mydata", invoke)
