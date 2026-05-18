# SPDX-License-Identifier: Apache-2.0
"""Fixture-backed KFTC OpenGiro send adapters.

KFTC public OpenGiro pages expose bill and payment OpenAPI surfaces, but the
current developer-portal state is not live-ready: Callback URL and API Key
registration remain incomplete and gated OpenGiro documents are inaccessible.
Per UMMAYA adapter rules, these adapters mirror the public reference shape as
mock ``send`` tools until operator-owned live probe evidence exists.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ummaya.primitives.submit import (
    SubmitOutput,
    SubmitStatus,
    derive_transaction_id,
    register_submit_adapter,
)
from ummaya.settings import UmmayaSettings, settings
from ummaya.tools.models import AdapterRealDomainPolicy
from ummaya.tools.registry import AdapterPrimitive, AdapterRegistration, AdapterSourceMode
from ummaya.tools.transparency import stamp_mock_response

logger = logging.getLogger(__name__)

BillOperation = Literal["create_bill", "cancel_bill", "check_payment_status"]
PaymentOperation = Literal[
    "create_inquiry_payment_url",
    "create_input_payment_url",
    "create_link_payment_url",
    "query_payment_result",
]
OpenGiroStatusDetail = Literal[
    "created",
    "cancelled",
    "payment_status_checked",
    "payment_url_issued",
    "payment_result_confirmed",
    "expired",
    "rejected",
    "setup_blocked",
    "failed",
]

_BILL_TOOL_ID: Final = "mock_kftc_opengiro_bill_send_v1"
_PAYMENT_TOOL_ID: Final = "mock_kftc_opengiro_payment_send_v1"
_BILL_NONCE: Final = "mock_kftc_opengiro_bill_send_v1_nonce_v1"
_PAYMENT_NONCE: Final = "mock_kftc_opengiro_payment_send_v1_nonce_v1"

_REFERENCE_IMPL: Final = "kftc-opengiro-public-openapi"
_SECURITY_WRAPPING: Final = (
    "KFTC developer portal service application + Callback URL + API Key registration "
    "+ OAuth-style access token"
)
_INTERNATIONAL_REF: Final = "Singapore APEX payment API gateway"
_BILL_POLICY_URL: Final = "https://developers.kftc.or.kr/dev/openapi/open-giro/index"
_PAYMENT_POLICY_URL: Final = "https://developers.kftc.or.kr/dev/openapi/open-giro/pay-service"
_STARTER_URL: Final = "https://developers.kftc.or.kr/dev/starter/starter"
_FIXTURE_ISSUED_AT: Final = datetime(2026, 5, 18, 0, 0, tzinfo=UTC)

_BILL_ENDPOINTS: Final[dict[str, str]] = {
    "create_bill": "https://api.giro.or.kr/v1/bills/giro",
    "cancel_bill": "https://api.giro.or.kr/v1/bills/giro/cancel",
    "check_payment_status": "https://api.giro.or.kr/v1/bills/giro/payment-yn",
}
_PAYMENT_ENDPOINTS: Final[dict[str, str]] = {
    "create_inquiry_payment_url": "https://api.giro.or.kr/v1/payments/giro-inqr-pay-url",
    "create_input_payment_url": "https://api.giro.or.kr/v1/payments/giro-inpt-pay-url",
    "create_link_payment_url": "https://api.giro.or.kr/v1/payments/link-pay-url",
    "query_payment_result": "https://api.giro.or.kr/v1/payments",
}


class OpenGiroSetupReadiness(BaseModel):
    """Operator-owned live-readiness state for KFTC OpenGiro."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service_enabled: bool = False
    callback_url_registered: bool = False
    api_key_registered: bool = False
    client_id_configured: bool = False
    client_secret_configured: bool = False
    access_token_configured: bool = False
    documents_accessible: bool = False
    live_probe_enabled: bool = False
    live_ready: bool = False
    blockers: tuple[str, ...] = Field(default_factory=tuple)


class OpenGiroBillParams(BaseModel):
    """Typed params for the OpenGiro bill service fixture."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: BillOperation = Field(
        default="create_bill",
        description="OpenGiro bill operation to mirror.",
    )
    giro_no: str = Field(
        default="1234567",
        min_length=4,
        max_length=32,
        description="OpenGiro giro number from the biller contract.",
    )
    bill_reference: str = Field(
        default="MOCK-BILL-2026-001",
        min_length=1,
        max_length=64,
        description="Biller-side bill reference. Fixture values may use MOCK/REJECT/EXPIRED.",
    )
    amount_krw: int | None = Field(
        default=15_000,
        ge=1,
        le=99_999_999,
        description="Bill amount in KRW. Required for create_bill.",
    )
    due_date: date | None = Field(
        default=date(2026, 6, 30),
        description="Bill due date. Required for create_bill.",
    )
    payer_reference: str = Field(
        default="MOCK-PAYER",
        min_length=1,
        max_length=64,
        description="Sanitized payer reference for fixture correlation.",
    )
    live_probe_requested: bool = Field(
        default=False,
        description="Opt-in live probe flag. Fixture mode is used unless this is true.",
    )

    @model_validator(mode="after")
    def _validate_operation_requirements(self) -> OpenGiroBillParams:
        if self.operation == "create_bill":
            if self.amount_krw is None:
                raise ValueError("create_bill requires amount_krw")
            if self.due_date is None:
                raise ValueError("create_bill requires due_date")
        if self.operation in {"cancel_bill", "check_payment_status"} and not self.bill_reference:
            raise ValueError(f"{self.operation} requires bill_reference")
        return self


class OpenGiroPaymentParams(BaseModel):
    """Typed params for the OpenGiro payment service fixture."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation: PaymentOperation = Field(
        default="create_link_payment_url",
        description="OpenGiro payment operation to mirror.",
    )
    giro_no: str = Field(
        default="1234567",
        min_length=4,
        max_length=32,
        description="OpenGiro giro number from the biller contract.",
    )
    payment_reference: str = Field(
        default="MOCK-PAY-2026-001",
        min_length=1,
        max_length=64,
        description="Payment correlation reference. Fixture values may use MOCK/REJECT/EXPIRED.",
    )
    amount_krw: int | None = Field(
        default=15_000,
        ge=1,
        le=99_999_999,
        description="Payment amount in KRW. Required for payment URL creation.",
    )
    payer_reference: str = Field(
        default="MOCK-PAYER",
        min_length=1,
        max_length=64,
        description="Sanitized payer reference for fixture correlation.",
    )
    redirect_return_url: str | None = Field(
        default=None,
        max_length=512,
        description="Operator-approved return URL for browser redirect fixtures.",
    )
    live_probe_requested: bool = Field(
        default=False,
        description="Opt-in live probe flag. Fixture mode is used unless this is true.",
    )

    @model_validator(mode="after")
    def _validate_operation_requirements(self) -> OpenGiroPaymentParams:
        if self.operation != "query_payment_result" and self.amount_krw is None:
            raise ValueError(f"{self.operation} requires amount_krw")
        if self.operation == "query_payment_result" and not self.payment_reference:
            raise ValueError("query_payment_result requires payment_reference")
        return self


class OpenGiroReceipt(BaseModel):
    """Sanitized receipt placed inside SubmitOutput.adapter_receipt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    receipt_ref: str
    service: Literal["bill", "payment"]
    operation: str
    upstream_rsp_code: str
    upstream_rsp_message: str
    status_detail: OpenGiroStatusDetail
    giro_no_masked: str
    reference_hash: str
    amount_krw: int | None = None
    payment_url: str | None = None
    expires_at: datetime | None = None
    setup_blockers: tuple[str, ...] = Field(default_factory=tuple)
    mock: bool = True


def build_setup_readiness(
    settings_obj: UmmayaSettings | None = None,
) -> OpenGiroSetupReadiness:
    """Build fail-closed OpenGiro live-readiness state from UMMAYA settings."""
    cfg = settings if settings_obj is None else settings_obj
    service_enabled = bool(cfg.kftc_opengiro_service_enabled)
    callback_url_registered = bool(str(cfg.kftc_opengiro_callback_url).strip())
    api_key_registered = bool(cfg.kftc_opengiro_api_key_registered)
    client_id_configured = bool(str(cfg.kftc_opengiro_client_id).strip())
    client_secret_configured = bool(str(cfg.kftc_opengiro_client_secret).strip())
    access_token_configured = bool(str(cfg.kftc_opengiro_access_token).strip())
    documents_accessible = bool(cfg.kftc_opengiro_documents_accessible)
    live_probe_enabled = bool(cfg.kftc_opengiro_live_probe_enabled)

    blockers: list[str] = []
    if not service_enabled:
        blockers.append("OpenGiro service is not marked enabled in UMMAYA settings")
    if not callback_url_registered:
        blockers.append("KFTC Callback URL is not registered")
    if not api_key_registered:
        blockers.append("OpenGiro API Key registration is incomplete")
    if not client_id_configured:
        blockers.append("KFTC Client ID is not configured")
    if not client_secret_configured:
        blockers.append("KFTC Client Secret is not configured")
    if not access_token_configured:
        blockers.append("KFTC access token is not configured")
    if not documents_accessible:
        blockers.append("Gated KFTC OpenGiro documents are not accessible")
    if not live_probe_enabled:
        blockers.append("UMMAYA_KFTC_OPENGIRO_LIVE_PROBE_ENABLED is false")

    return OpenGiroSetupReadiness(
        service_enabled=service_enabled,
        callback_url_registered=callback_url_registered,
        api_key_registered=api_key_registered,
        client_id_configured=client_id_configured,
        client_secret_configured=client_secret_configured,
        access_token_configured=access_token_configured,
        documents_accessible=documents_accessible,
        live_probe_enabled=live_probe_enabled,
        live_ready=not blockers,
        blockers=tuple(blockers),
    )


def _hash_ref(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _mask_giro_no(giro_no: str) -> str:
    if len(giro_no) <= 5:
        return "*" * len(giro_no)
    return f"{giro_no[:3]}***{giro_no[-2:]}"


def _fixture_outcome(reference: str) -> tuple[SubmitStatus, str, str, OpenGiroStatusDetail]:
    upper = reference.upper()
    if "REJECT" in upper:
        return SubmitStatus.rejected, "R4001", "Rejected by fixture upstream", "rejected"
    if "EXPIRED" in upper:
        return SubmitStatus.failed, "E4100", "Payment URL expired in fixture", "expired"
    if "FAIL" in upper:
        return SubmitStatus.failed, "E5000", "Fixture upstream failure", "failed"
    return SubmitStatus.succeeded, "A0000", "Fixture accepted", "created"


def _stamp_receipt(
    receipt: OpenGiroReceipt,
    *,
    endpoint: str,
    policy_authority: str,
) -> dict[str, object]:
    return stamp_mock_response(
        receipt.model_dump(mode="json", exclude_none=True),
        reference_implementation=_REFERENCE_IMPL,
        actual_endpoint_when_live=endpoint,
        security_wrapping_pattern=_SECURITY_WRAPPING,
        policy_authority=policy_authority,
        international_reference=_INTERNATIONAL_REF,
    )


def _setup_blocked_output(
    *,
    tool_id: str,
    params: dict[str, object],
    nonce: str,
    service: Literal["bill", "payment"],
    operation: str,
    giro_no: str,
    reference: str,
    endpoint: str,
    policy_authority: str,
) -> SubmitOutput:
    readiness = build_setup_readiness()
    receipt = OpenGiroReceipt(
        receipt_ref=f"MOCK-OG-SETUP-{_hash_ref(reference)}",
        service=service,
        operation=operation,
        upstream_rsp_code="UMMAYA_SETUP_BLOCKED",
        upstream_rsp_message="; ".join(readiness.blockers),
        status_detail="setup_blocked",
        giro_no_masked=_mask_giro_no(giro_no),
        reference_hash=_hash_ref(reference),
        setup_blockers=readiness.blockers,
    )
    return SubmitOutput(
        transaction_id=derive_transaction_id(tool_id, params, adapter_nonce=nonce),
        status=SubmitStatus.rejected,
        adapter_receipt=_stamp_receipt(
            receipt,
            endpoint=endpoint,
            policy_authority=policy_authority,
        ),
    )


async def invoke_bill(params: dict[str, object]) -> SubmitOutput:
    """Invoke the fixture-backed OpenGiro bill adapter."""
    typed = OpenGiroBillParams.model_validate(params)
    endpoint = _BILL_ENDPOINTS[typed.operation]
    if typed.live_probe_requested and not build_setup_readiness().live_ready:
        return _setup_blocked_output(
            tool_id=_BILL_TOOL_ID,
            params=dict(params),
            nonce=_BILL_NONCE,
            service="bill",
            operation=typed.operation,
            giro_no=typed.giro_no,
            reference=typed.bill_reference,
            endpoint=endpoint,
            policy_authority=_BILL_POLICY_URL,
        )

    status, rsp_code, rsp_message, detail = _fixture_outcome(typed.bill_reference)
    if status == SubmitStatus.succeeded:
        if typed.operation == "create_bill":
            detail = "created"
        elif typed.operation == "cancel_bill":
            detail = "cancelled"
        else:
            detail = "payment_status_checked"

    receipt = OpenGiroReceipt(
        receipt_ref=f"MOCK-OG-BILL-{_hash_ref(typed.bill_reference)}",
        service="bill",
        operation=typed.operation,
        upstream_rsp_code=rsp_code,
        upstream_rsp_message=rsp_message,
        status_detail=detail,
        giro_no_masked=_mask_giro_no(typed.giro_no),
        reference_hash=_hash_ref(typed.bill_reference),
        amount_krw=typed.amount_krw,
    )
    logger.debug("mock_kftc_opengiro_bill_send_v1: operation=%s", typed.operation)
    return SubmitOutput(
        transaction_id=derive_transaction_id(
            _BILL_TOOL_ID,
            dict(params),
            adapter_nonce=_BILL_NONCE,
        ),
        status=status,
        adapter_receipt=_stamp_receipt(
            receipt,
            endpoint=endpoint,
            policy_authority=_BILL_POLICY_URL,
        ),
    )


async def invoke_payment(params: dict[str, object]) -> SubmitOutput:
    """Invoke the fixture-backed OpenGiro payment adapter."""
    typed = OpenGiroPaymentParams.model_validate(params)
    endpoint = _PAYMENT_ENDPOINTS[typed.operation]
    if typed.live_probe_requested and not build_setup_readiness().live_ready:
        return _setup_blocked_output(
            tool_id=_PAYMENT_TOOL_ID,
            params=dict(params),
            nonce=_PAYMENT_NONCE,
            service="payment",
            operation=typed.operation,
            giro_no=typed.giro_no,
            reference=typed.payment_reference,
            endpoint=endpoint,
            policy_authority=_PAYMENT_POLICY_URL,
        )

    status, rsp_code, rsp_message, detail = _fixture_outcome(typed.payment_reference)
    payment_url: str | None = None
    expires_at: datetime | None = None
    if status == SubmitStatus.succeeded:
        if typed.operation == "query_payment_result":
            detail = "payment_result_confirmed"
        else:
            status = SubmitStatus.pending
            detail = "payment_url_issued"
            reference_hash = _hash_ref(typed.payment_reference)
            payment_url = f"https://mock.open-giro.ummaya.local/pay/{reference_hash}"
            expires_at = _FIXTURE_ISSUED_AT + timedelta(minutes=10)

    receipt = OpenGiroReceipt(
        receipt_ref=f"MOCK-OG-PAY-{_hash_ref(typed.payment_reference)}",
        service="payment",
        operation=typed.operation,
        upstream_rsp_code=rsp_code,
        upstream_rsp_message=rsp_message,
        status_detail=detail,
        giro_no_masked=_mask_giro_no(typed.giro_no),
        reference_hash=_hash_ref(typed.payment_reference),
        amount_krw=typed.amount_krw,
        payment_url=payment_url,
        expires_at=expires_at,
    )
    logger.debug("mock_kftc_opengiro_payment_send_v1: operation=%s", typed.operation)
    return SubmitOutput(
        transaction_id=derive_transaction_id(
            _PAYMENT_TOOL_ID,
            dict(params),
            adapter_nonce=_PAYMENT_NONCE,
        ),
        status=status,
        adapter_receipt=_stamp_receipt(
            receipt,
            endpoint=endpoint,
            policy_authority=_PAYMENT_POLICY_URL,
        ),
    )


BILL_REGISTRATION = AdapterRegistration(
    tool_id=_BILL_TOOL_ID,
    primitive=AdapterPrimitive.send,
    module_path=__name__,
    input_model_ref=f"{__name__}.OpenGiroBillParams",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="geumyung_injeungseo_personal_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["오픈지로", "금융결제원", "지로", "부과", "청구", "납부확인"],
        "en": ["OpenGiro", "KFTC", "giro bill", "bill issue", "payment status"],
    },
    auth_type="oauth",
    nonce=_BILL_NONCE,
    policy=AdapterRealDomainPolicy(
        real_classification_url=_BILL_POLICY_URL,
        real_classification_text=(
            "금융결제원 OpenGiro 부과서비스 — 공식 OpenAPI 페이지와 개발자 "
            "Callback URL/API Key 절차에 근거한 send 게이트."
        ),
        citizen_facing_gate="send",
        last_verified=datetime(2026, 5, 18, tzinfo=UTC),
    ),
)

PAYMENT_REGISTRATION = AdapterRegistration(
    tool_id=_PAYMENT_TOOL_ID,
    primitive=AdapterPrimitive.send,
    module_path=__name__,
    input_model_ref=f"{__name__}.OpenGiroPaymentParams",
    source_mode=AdapterSourceMode.OOS,
    published_tier_minimum="geumyung_injeungseo_personal_aal2",
    nist_aal_hint="AAL2",
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    search_hint={
        "ko": ["오픈지로", "금융결제원", "지로", "납부", "결제URL", "납부결과"],
        "en": ["OpenGiro", "KFTC", "giro payment", "payment URL", "payment result"],
    },
    auth_type="oauth",
    nonce=_PAYMENT_NONCE,
    policy=AdapterRealDomainPolicy(
        real_classification_url=_PAYMENT_POLICY_URL,
        real_classification_text=(
            "금융결제원 OpenGiro 납부서비스 — 공식 OpenAPI 페이지와 개발자 "
            "Callback URL/API Key 절차에 근거한 send 게이트."
        ),
        citizen_facing_gate="send",
        last_verified=datetime(2026, 5, 18, tzinfo=UTC),
    ),
)

register_submit_adapter(BILL_REGISTRATION, invoke_bill)
register_submit_adapter(PAYMENT_REGISTRATION, invoke_payment)

__all__ = [
    "BILL_REGISTRATION",
    "PAYMENT_REGISTRATION",
    "OpenGiroBillParams",
    "OpenGiroPaymentParams",
    "OpenGiroReceipt",
    "OpenGiroSetupReadiness",
    "build_setup_readiness",
    "invoke_bill",
    "invoke_payment",
]
