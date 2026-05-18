# Quickstart: KFTC OpenGiro Send Adapter

## 1. Verify Portal Readiness

Expected current state from 2026-05-18:

- OpenGiro service: `이용중`
- Callback URL: missing
- API Key registration: blocked by missing Callback URL
- OpenGiro documents: access denied
- 자료실 search for `오픈지로`: 0 results

Do not click Client Secret 조회.

## 2. Run Fixture Verification

```bash
uv run pytest tests/unit/tools/test_mock_kftc_opengiro.py \
  tests/integration/test_kftc_opengiro_discovery.py \
  tests/lint/test_kftc_secret_redaction.py
```

## 3. Check Schemas

```bash
uv run python scripts/build_schemas.py --check
```

## 4. Expected Send Fixture Shape

```python
from ummaya.primitives.submit import send
import ummaya.tools.mock.kftc.opengiro  # import registers adapters

result = await send(
    "mock_kftc_opengiro_payment_send_v1",
    {
        "operation": "create_link_payment_url",
        "payment_reference": "FIXTURE-PAY-2026-001",
        "amount_krw": 12000,
    },
    auth_context=<AAL2 auth context>,
)
```

Expected result:

- `transaction_id` starts with `urn:ummaya:send:`
- `status` is `pending`
- `adapter_receipt.mock` is `true`
- `adapter_receipt._actual_endpoint_when_live` points to the official KFTC endpoint

## 5. Future Live-Probe Gate

Only after the operator registers the real Callback URL and API Key:

1. Run direct `curl` probes manually against KFTC with secrets redacted from saved artifacts.
2. Store sanitized request/response evidence under this feature's evidence path.
3. Update the adapter from `mock_` to live in a follow-up task after the evidence passes review.
