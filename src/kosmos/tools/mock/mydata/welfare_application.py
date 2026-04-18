# SPDX-License-Identifier: Apache-2.0
"""T026 — Mock submit adapter: welfare application filing (mydata ministry).

Acceptance Scenario 2: proves that a second ministry (mydata — 금융보안원 마이데이터)
routes through the same shape-only envelope, demonstrating 5→1 verb collapse
across ministry boundaries.

Adapter identity:
  tool_id: ``mock_welfare_application_submit_v1``
  ministry: mydata (KFTC MyData v240930 / 마이데이터 기본 API)
  source_mode: OOS (shape-mirrored from MyData standard API spec)
  primitive: submit

SC-002 compliance: domain vocabulary (applicant details, benefit codes,
household info) lives HERE in ``WelfareApplicationParams``, never on the
main ``SubmitInput`` / ``SubmitOutput`` surface.

V1 invariant: ``primitive=submit`` ∧ ``pipa_class=personal_standard`` →
``is_irreversible=True`` (application filing creates a government record).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kosmos.primitives.submit import (
    SubmitOutput,
    SubmitStatus,
    derive_transaction_id,
    register_submit_adapter,
)
from kosmos.tools.registry import AdapterPrimitive, AdapterRegistration, AdapterSourceMode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# T026-A: Adapter-typed input model
# ---------------------------------------------------------------------------


class WelfareApplicationParams(BaseModel):
    """Typed params for the welfare application filing adapter.

    Domain vocabulary lives here, not on the main SubmitInput envelope (SC-002).
    Real-world counterpart: 마이데이터 복지 서비스 신청 API (KFTC MyData v240930).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    applicant_id: str = Field(
        min_length=1,
        max_length=64,
        description="MyData-scoped applicant pseudonymous identifier (DI code).",
    )
    benefit_code: str = Field(
        min_length=1,
        max_length=32,
        description="Welfare benefit type code (e.g. 기초생활수급, 장애인지원).",
    )
    application_type: Literal["new", "renewal", "modification"] = Field(
        description="Whether this is a new application, renewal, or modification.",
    )
    household_size: int = Field(
        ge=1,
        le=50,
        description="Number of household members (1–50 inclusive).",
    )


# ---------------------------------------------------------------------------
# T026-B: Mock invoke coroutine
# ---------------------------------------------------------------------------

_ADAPTER_NONCE = "mock_welfare_application_submit_v1_nonce_v1"


async def invoke(params: dict[str, object]) -> SubmitOutput:
    """Mock invoke — validates params and returns a deterministic SubmitOutput.

    In production this coroutine would call the KFTC MyData welfare API.
    In mock mode it validates typed params and returns a fixture receipt.

    Args:
        params: Raw params dict from the main ``submit()`` envelope.

    Returns:
        ``SubmitOutput`` with deterministic ``transaction_id``.
    """
    typed: WelfareApplicationParams = WelfareApplicationParams.model_validate(params)
    logger.debug(
        "mock_welfare_application_submit_v1: applicant_id=%s benefit_code=%s application_type=%s",
        typed.applicant_id,
        typed.benefit_code,
        typed.application_type,
    )

    # Deterministic mock receipt number
    receipt_hash = hashlib.sha256(
        f"{typed.applicant_id}:{typed.benefit_code}:{typed.application_type}".encode()
    ).hexdigest()[:12]

    return SubmitOutput(
        transaction_id=derive_transaction_id(
            "mock_welfare_application_submit_v1",
            dict(params),
            adapter_nonce=_ADAPTER_NONCE,
        ),
        status=SubmitStatus.succeeded,
        adapter_receipt={
            "application_ref": f"MOCK-WA-{receipt_hash}",
            "benefit_code": typed.benefit_code,
            "application_type": typed.application_type,
            "household_size": typed.household_size,
            "mock": True,
        },
    )


# ---------------------------------------------------------------------------
# T026-C: AdapterRegistration + self-registration
# ---------------------------------------------------------------------------

REGISTRATION = AdapterRegistration(
    tool_id="mock_welfare_application_submit_v1",
    primitive=AdapterPrimitive.submit,
    module_path=__name__,
    input_model_ref=f"{__name__}.WelfareApplicationParams",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="mydata_individual_aal2",
    nist_aal_hint="AAL2",
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=5,
    search_hint={
        "ko": ["복지", "급여신청", "마이데이터", "기초생활", "장애인"],
        "en": ["welfare", "benefit application", "mydata", "social assistance"],
    },
    auth_type="oauth",
    auth_level="AAL2",
    pipa_class="personal_standard",
    is_irreversible=True,  # V1 invariant: submit + personal_* → irreversible
    dpa_reference="KosmosWelfareApplication-v1",
    nonce=_ADAPTER_NONCE,
)

# Register in the submit dispatcher's in-process table
register_submit_adapter(REGISTRATION, invoke)

__all__ = ["REGISTRATION", "WelfareApplicationParams", "invoke"]
