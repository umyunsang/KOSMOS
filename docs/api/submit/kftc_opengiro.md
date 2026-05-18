---
tool_id: mock_kftc_opengiro_bill_send_v1 / mock_kftc_opengiro_payment_send_v1
primitive: send
tier: mock
permission_tier: 2
---

# KFTC OpenGiro Send Adapters

## Overview

Wraps the Korea Financial Telecommunications and Clearings Institute (KFTC) OpenGiro bill and payment OpenAPI surfaces as two UMMAYA `send` adapters. The adapters are fixture-backed now because the current developer-portal state is not live-ready: Callback URL registration is missing, API Key registration is blocked by that missing Callback URL, and gated OpenGiro documents remain access-denied.

| Field | Value |
|---|---|
| Bill adapter | `mock_kftc_opengiro_bill_send_v1` |
| Payment adapter | `mock_kftc_opengiro_payment_send_v1` |
| Source | KFTC OpenGiro public OpenAPI pages |
| Primitive | `send` |
| Module | `src/ummaya/tools/mock/kftc/opengiro.py` |

## Envelope

Both adapters use the shared `SubmitInput` / `SubmitOutput` envelope. KFTC-specific vocabulary lives only in adapter params and `adapter_receipt`.

### Bill params

| Field | Type | Required | Description |
|---|---|---|---|
| `operation` | `create_bill`, `cancel_bill`, `check_payment_status` | yes | OpenGiro bill service operation |
| `giro_no` | `str` | yes | Biller giro number; receipts mask it |
| `bill_reference` | `str` | yes | Biller-side reference; receipts hash it |
| `amount_krw` | `int \| null` | create only | Bill amount |
| `due_date` | `date \| null` | create only | Bill due date |
| `payer_reference` | `str` | no | Sanitized fixture correlation reference |
| `live_probe_requested` | `bool` | no | Rejects unless KFTC live readiness is fully configured |

### Payment params

| Field | Type | Required | Description |
|---|---|---|---|
| `operation` | `create_inquiry_payment_url`, `create_input_payment_url`, `create_link_payment_url`, `query_payment_result` | yes | OpenGiro payment service operation |
| `giro_no` | `str` | yes | Biller giro number; receipts mask it |
| `payment_reference` | `str` | yes | Payment correlation reference; receipts hash it |
| `amount_krw` | `int \| null` | URL creation only | Payment amount |
| `payer_reference` | `str` | no | Sanitized fixture correlation reference |
| `redirect_return_url` | `str \| null` | no | Operator-approved browser return URL for fixtures |
| `live_probe_requested` | `bool` | no | Rejects unless KFTC live readiness is fully configured |

## Search hints

- 한국어: `오픈지로`, `금융결제원`, `지로`, `부과`, `청구`, `납부`, `결제URL`, `납부결과`
- English: `OpenGiro`, `KFTC`, `giro bill`, `bill issue`, `payment status`, `payment URL`, `payment result`

## Endpoint

- **Mode**: Fixture-backed mock-to-live
- **Bill public source**: https://developers.kftc.or.kr/dev/openapi/open-giro/index
- **Payment public source**: https://developers.kftc.or.kr/dev/openapi/open-giro/pay-service
- **Developer starter workflow**: https://developers.kftc.or.kr/dev/starter/starter
- **Service access notice**: https://developers.kftc.or.kr/dev/support/notice/all/detail?id=44&boardCtgCd=all

Official target endpoints mirrored by the fixture:

| Operation | Method | Target when live |
|---|---|---|
| Bill create | `POST` | `https://api.giro.or.kr/v1/bills/giro` |
| Bill cancel | `POST` | `https://api.giro.or.kr/v1/bills/giro/cancel` |
| Bill payment status | `GET` | `https://api.giro.or.kr/v1/bills/giro/payment-yn` |
| Payment inquiry URL | `POST` | `https://api.giro.or.kr/v1/payments/giro-inqr-pay-url` |
| Payment input URL | `POST` | `https://api.giro.or.kr/v1/payments/giro-inpt-pay-url` |
| Payment link URL | `POST` | `https://api.giro.or.kr/v1/payments/link-pay-url` |
| Payment result | `GET` | `https://api.giro.or.kr/v1/payments` |

## Permission tier rationale

OpenGiro bill and payment operations are side-effecting financial actions, so they map to `send`. UMMAYA does not invent a separate permission classification; each adapter cites the official KFTC developer page through `AdapterRealDomainPolicy.real_classification_url` and declares the citizen-facing gate as `send`.

The adapters require `published_tier_minimum="geumyung_injeungseo_personal_aal2"` because the user-facing flow involves KFTC financial infrastructure and payment-adjacent action. The dispatcher enforces this tier before adapter invocation.

## Worked example

### Payment URL fixture input

```json
{
  "tool_id": "mock_kftc_opengiro_payment_send_v1",
  "params": {
    "operation": "create_link_payment_url",
    "giro_no": "1234567",
    "payment_reference": "MOCK-PAY-2026-001",
    "amount_krw": 25000
  }
}
```

### Payment URL fixture output

```json
{
  "transaction_id": "urn:ummaya:send:<sha256>",
  "status": "pending",
  "adapter_receipt": {
    "receipt_ref": "MOCK-OG-PAY-<hash>",
    "service": "payment",
    "operation": "create_link_payment_url",
    "upstream_rsp_code": "A0000",
    "status_detail": "payment_url_issued",
    "giro_no_masked": "123***67",
    "reference_hash": "<sha256[:16]>",
    "payment_url": "https://mock.open-giro.ummaya.local/pay/<hash>",
    "mock": true,
    "_mode": "mock"
  }
}
```

## Operator setup

Live probing remains disabled until all readiness checks pass:

1. OpenGiro service application is complete in the KFTC developer portal.
2. The operator registers the deployment-specific Callback URL.
3. OpenGiro `부과서비스` and `납부서비스` are registered to the API Key.
4. `UMMAYA_KFTC_OPENGIRO_CLIENT_ID` and `UMMAYA_KFTC_OPENGIRO_CLIENT_SECRET` are provided through operator secret storage, never repository files.
5. KFTC access token material is obtained outside CI and redacted from evidence.
6. Gated OpenGiro documents are accessible.
7. `UMMAYA_KFTC_OPENGIRO_LIVE_PROBE_ENABLED=true` is set only for a manual live probe.

The canonical callback path documented for operators is:

```text
https://<operator-host>/auth/kftc/opengiro/callback
```

## Constraints

- Default tests and CI must not call KFTC.
- Do not click or capture the KFTC Client Secret in browser automation.
- `live_probe_requested=true` returns `setup_blocked` unless all UMMAYA_KFTC readiness settings are complete.
- Receipts mask `giro_no` and hash bill/payment references.
- Fixture paths cover success, validation failure, missing setup, rejected, and expired payment URL outcomes.
