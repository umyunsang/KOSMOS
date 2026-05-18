# Contract: OpenGiro Send Adapters

## Adapter IDs

- `mock_kftc_opengiro_bill_send_v1`
- `mock_kftc_opengiro_payment_send_v1`

The `mock_` prefix is mandatory until KFTC Callback URL, API Key, and sanitized direct-curl evidence are complete.

## Input Envelope

The shared primitive envelope remains:

```json
{
  "tool_id": "mock_kftc_opengiro_payment_send_v1",
  "params": {
    "operation": "create_link_payment_url",
    "payment_reference": "FIXTURE-PAY-2026-001",
    "amount_krw": 12000
  }
}
```

Domain-specific fields are allowed only inside `params`.

## Output Envelope

The adapter returns `SubmitOutput`:

```json
{
  "transaction_id": "urn:ummaya:send:<sha256>",
  "status": "pending",
  "adapter_receipt": {
    "source": "kftc_opengiro_fixture",
    "operation": "create_link_payment_url",
    "rsp_code": "A0000",
    "rsp_message": "fixture accepted",
    "status_detail": "pending_external_payment",
    "next_redirect_url": "https://www.giro.or.kr/open/apipay.do?T=fixture",
    "expires_in_seconds": 600,
    "mock": true,
    "_actual_endpoint_when_live": "https://api.giro.or.kr/v1/payments/link-pay-url"
  }
}
```

## Status Mapping

| OpenGiro condition | `SubmitStatus` | Receipt `status_detail` |
|---|---|---|
| Fixture accepted and awaits external citizen payment | `pending` | `pending_external_payment` |
| Fixture accepted for bill creation/cancellation | `succeeded` | `accepted` |
| Validation/setup blocker | `rejected` | `setup_blocked` |
| Upstream-style rejection fixture | `rejected` | `rejected` |
| Expired payment URL fixture | `failed` | `expired` |

## Source URLs

- Bill service: `https://developers.kftc.or.kr/dev/openapi/open-giro/index`
- Payment service: `https://developers.kftc.or.kr/dev/openapi/open-giro/pay-service`
- Starter/setup flow: `https://developers.kftc.or.kr/dev/starter/starter`

