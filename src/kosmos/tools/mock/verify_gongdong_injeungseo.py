# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — gongdong_injeungseo (공동인증서 / KOSCOM Joint Certificate).

Source mode: OOS — shape-mirrored from PyPinkSign / KFTC API docs.
FR-009 (delegation-only): no signing keys, no CA logic. Fixture-backed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from kosmos.primitives.verify import (
    GongdongInjeungseoContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_gongdong_injeungseo",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_gongdong_injeungseo",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="gongdong_injeungseo_personal_aal3",
    nist_aal_hint="AAL3",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["공동인증서", "공인인증서", "KICA", "KOSCOM"],
        "en": ["joint certificate", "NPKI", "gongdong injeungseo"],
    },
    auth_type="oauth",
    auth_level="AAL3",
    pipa_class="personal_unique_id",
    is_irreversible=False,
    dpa_reference="PIPA §26 — 수탁자 처리 (위탁)",
)

# Recorded fixture — no real external calls (FR-009).
_FIXTURE = GongdongInjeungseoContext(
    family="gongdong_injeungseo",
    published_tier="gongdong_injeungseo_personal_aal3",
    nist_aal_hint="AAL3",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    external_session_ref="mock-gongdong-ref-001",
    certificate_issuer="KICA",
)


def invoke(session_context: dict[str, object]) -> GongdongInjeungseoContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        return GongdongInjeungseoContext.model_validate({**_FIXTURE.model_dump(), **overrides})
    return _FIXTURE


register_verify_adapter("gongdong_injeungseo", invoke)
