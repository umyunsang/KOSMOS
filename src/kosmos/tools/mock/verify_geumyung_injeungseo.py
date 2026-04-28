# SPDX-License-Identifier: Apache-2.0
"""Mock verify adapter — geumyung_injeungseo (금융인증서 / Financial Certificate, KFTC).

Source mode: OOS — shape-mirrored from KFTC 금융인증서 API specification.
FR-009 (delegation-only): no signing keys, no CA logic. Fixture-backed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from kosmos.primitives.verify import (
    GeumyungInjeungseoContext,
    register_verify_adapter,
)
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

ADAPTER_REGISTRATION = AdapterRegistration(
    tool_id="mock_verify_geumyung_injeungseo",
    primitive=AdapterPrimitive.verify,
    module_path="kosmos.tools.mock.verify_geumyung_injeungseo",
    input_model_ref="kosmos.primitives.verify:VerifyInput",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="geumyung_injeungseo_personal_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["금융인증서", "금결원", "KFTC", "은행인증"],
        "en": ["financial certificate", "KFTC", "geumyung injeungseo"],
    },
    auth_type="oauth",
)

# Recorded fixture — no real external calls (FR-009).
_FIXTURE = GeumyungInjeungseoContext(
    family="geumyung_injeungseo",
    published_tier="geumyung_injeungseo_personal_aal2",
    nist_aal_hint="AAL2",
    verified_at=datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC),
    external_session_ref="mock-geumyung-ref-001",
    bank_cluster="kftc",
)


def invoke(session_context: dict[str, object]) -> GeumyungInjeungseoContext:
    """Return the recorded fixture; override via session_context for test variants."""
    if session_context.get("_fixture_override"):
        overrides: dict[str, object] = dict(session_context["_fixture_override"])  # type: ignore[call-overload]
        return GeumyungInjeungseoContext.model_validate({**_FIXTURE.model_dump(), **overrides})
    return _FIXTURE


register_verify_adapter("geumyung_injeungseo", invoke)
