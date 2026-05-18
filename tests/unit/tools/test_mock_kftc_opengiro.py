# SPDX-License-Identifier: Apache-2.0
"""Unit tests for KFTC OpenGiro fixture-backed send adapters."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

import ummaya.tools.mock  # noqa: F401
from ummaya.primitives._errors import AdapterInvocationError
from ummaya.primitives.submit import SubmitOutput, SubmitStatus, submit
from ummaya.settings import UmmayaSettings
from ummaya.tools.mock.kftc.opengiro import (
    build_setup_readiness,
    invoke_bill,
    invoke_payment,
)

_TRANSPARENCY_FIELDS = (
    "_mode",
    "_reference_implementation",
    "_actual_endpoint_when_live",
    "_security_wrapping_pattern",
    "_policy_authority",
    "_international_reference",
)


class _MinimalAuthContext(BaseModel):
    """Minimal AuthContext carrying only the published tier needed by send."""

    model_config = ConfigDict(frozen=True, extra="allow")
    published_tier: str


def _auth_context() -> _MinimalAuthContext:
    return _MinimalAuthContext(published_tier="geumyung_injeungseo_personal_aal2")


def _assert_transparency(receipt: dict[str, object]) -> None:
    for field in _TRANSPARENCY_FIELDS:
        value = receipt.get(field)
        assert value is not None and isinstance(value, str) and value.strip(), (
            f"adapter_receipt missing or empty {field!r}: {value!r}"
        )
    assert receipt["_mode"] == "mock"


def test_setup_readiness_fails_closed_by_default() -> None:
    cfg = UmmayaSettings(_env_file=None)
    readiness = build_setup_readiness(cfg)

    assert readiness.live_ready is False
    assert "KFTC Callback URL is not registered" in readiness.blockers
    assert "OpenGiro API Key registration is incomplete" in readiness.blockers
    assert "KFTC Client Secret is not configured" in readiness.blockers


def test_setup_readiness_exposes_only_booleans_not_secret_values() -> None:
    cfg = UmmayaSettings(
        _env_file=None,
        kftc_opengiro_service_enabled=True,
        kftc_opengiro_callback_url="https://operator.example/auth/kftc/opengiro/callback",
        kftc_opengiro_api_key_registered=True,
        kftc_opengiro_client_id="client-id-visible-in-portal",
        kftc_opengiro_client_secret="redacted-test-credential",
        kftc_opengiro_access_token="redacted-test-token",
        kftc_opengiro_documents_accessible=True,
        kftc_opengiro_live_probe_enabled=True,
    )
    readiness = build_setup_readiness(cfg)
    serialized = readiness.model_dump_json()

    assert readiness.live_ready is True
    assert "redacted-test-credential" not in serialized
    assert "redacted-test-token" not in serialized
    assert "client-id-visible-in-portal" not in serialized


@pytest.mark.asyncio
async def test_bill_adapter_happy_path_uses_send_envelope() -> None:
    result = await submit(
        tool_id="mock_kftc_opengiro_bill_send_v1",
        params={
            "operation": "create_bill",
            "giro_no": "1234567",
            "bill_reference": "MOCK-BILL-2026-001",
            "amount_krw": 25_000,
            "due_date": "2026-06-30",
        },
        auth_context=_auth_context(),
    )

    assert isinstance(result, SubmitOutput)
    assert result.status == SubmitStatus.succeeded
    assert result.transaction_id.startswith("urn:ummaya:send:")
    assert result.model_dump().keys() == {"transaction_id", "status", "adapter_receipt"}
    assert result.adapter_receipt["status_detail"] == "created"
    assert result.adapter_receipt["giro_no_masked"] == "123***67"
    assert "MOCK-BILL-2026-001" not in str(result.adapter_receipt)
    _assert_transparency(result.adapter_receipt)


@pytest.mark.asyncio
async def test_bill_adapter_validation_error_returns_structured_invocation_error() -> None:
    result = await submit(
        tool_id="mock_kftc_opengiro_bill_send_v1",
        params={
            "operation": "create_bill",
            "giro_no": "1234567",
            "bill_reference": "MOCK-BILL-VALIDATION",
            "amount_krw": None,
        },
        auth_context=_auth_context(),
    )

    assert isinstance(result, AdapterInvocationError)
    assert result.tool_id == "mock_kftc_opengiro_bill_send_v1"
    assert result.reason == "adapter_invocation_failed"
    assert "create_bill requires amount_krw" in result.message


@pytest.mark.asyncio
async def test_bill_adapter_live_probe_missing_setup_is_rejected() -> None:
    result = await submit(
        tool_id="mock_kftc_opengiro_bill_send_v1",
        params={
            "operation": "check_payment_status",
            "giro_no": "1234567",
            "bill_reference": "MOCK-BILL-LIVE-BLOCKED",
            "live_probe_requested": True,
        },
        auth_context=_auth_context(),
    )

    assert isinstance(result, SubmitOutput)
    assert result.status == SubmitStatus.rejected
    assert result.adapter_receipt["status_detail"] == "setup_blocked"
    assert "KFTC Callback URL is not registered" in str(result.adapter_receipt["setup_blockers"])
    _assert_transparency(result.adapter_receipt)


@pytest.mark.asyncio
async def test_payment_adapter_url_creation_returns_pending_fixture() -> None:
    result = await submit(
        tool_id="mock_kftc_opengiro_payment_send_v1",
        params={
            "operation": "create_link_payment_url",
            "giro_no": "1234567",
            "payment_reference": "MOCK-PAY-2026-001",
            "amount_krw": 25_000,
        },
        auth_context=_auth_context(),
    )

    assert isinstance(result, SubmitOutput)
    assert result.status == SubmitStatus.pending
    assert result.adapter_receipt["status_detail"] == "payment_url_issued"
    assert str(result.adapter_receipt["payment_url"]).startswith(
        "https://mock.open-giro.ummaya.local/pay/"
    )
    assert "MOCK-PAY-2026-001" not in str(result.adapter_receipt)
    _assert_transparency(result.adapter_receipt)


@pytest.mark.asyncio
async def test_payment_adapter_rejected_and_expired_paths() -> None:
    rejected = await invoke_payment(
        {
            "operation": "query_payment_result",
            "giro_no": "1234567",
            "payment_reference": "REJECT-PAY-001",
        }
    )
    expired = await invoke_payment(
        {
            "operation": "query_payment_result",
            "giro_no": "1234567",
            "payment_reference": "EXPIRED-PAY-001",
        }
    )

    assert rejected.status == SubmitStatus.rejected
    assert rejected.adapter_receipt["status_detail"] == "rejected"
    assert expired.status == SubmitStatus.failed
    assert expired.adapter_receipt["status_detail"] == "expired"


@pytest.mark.asyncio
async def test_direct_bill_and_payment_invokes_have_policy_urls() -> None:
    bill = await invoke_bill(
        {
            "operation": "cancel_bill",
            "giro_no": "1234567",
            "bill_reference": "MOCK-BILL-CANCEL-001",
        }
    )
    payment = await invoke_payment(
        {
            "operation": "query_payment_result",
            "giro_no": "1234567",
            "payment_reference": "MOCK-PAY-QUERY-001",
        }
    )

    assert bill.adapter_receipt["_policy_authority"].endswith("/open-giro/index")
    assert payment.adapter_receipt["_policy_authority"].endswith("/open-giro/pay-service")
