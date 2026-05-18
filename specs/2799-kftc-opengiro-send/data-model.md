# Data Model: KFTC OpenGiro Send Adapter

## Entity: OpenGiroSetupReadiness

Represents whether the KFTC developer portal and UMMAYA operator environment are ready for live OpenGiro probing.

| Field | Type | Validation |
|---|---|---|
| `service_status` | `Literal["not_requested", "pending", "active"]` | `active` maps to portal `이용중` |
| `callback_url_registered` | `bool` | Must be true before API Key registration is considered ready |
| `api_key_registered` | `bool` | Must be true before live token or API probes |
| `documents_accessible` | `bool` | False when `/dev/doc/open-giro` access is denied |
| `tool_accessible` | `bool` | False when portal test tools are unavailable |
| `last_checked_at` | `datetime` | UTC timestamp |
| `blockers` | `tuple[str, ...]` | Sanitized messages only; no secrets |

## Entity: OpenGiroBillParams

Adapter-specific input model for `mock_kftc_opengiro_bill_send_v1`.

| Field | Type | Required | Validation |
|---|---|---|---|
| `operation` | `Literal["create_bill", "cancel_bill", "check_payment_status"]` | yes | Selects the bill-service fixture path |
| `giro_no` | `str` | yes | 1-32 chars, fixture-safe identifier |
| `bill_reference` | `str | None` | conditional | Required for create/cancel fixture flows |
| `amount_krw` | `int | None` | conditional | Required for create; 0 < amount <= 10,000,000 |
| `payer_label` | `str | None` | no | Sanitized display label, max 64 chars |
| `due_date` | `date | None` | no | ISO date; fixture validation only |

## Entity: OpenGiroPaymentParams

Adapter-specific input model for `mock_kftc_opengiro_payment_send_v1`.

| Field | Type | Required | Validation |
|---|---|---|---|
| `operation` | `Literal["create_inquiry_payment_url", "create_input_payment_url", "create_link_payment_url", "query_payment_result"]` | yes | Selects payment-service fixture path |
| `giro_no` | `str | None` | conditional | Required for giro-based URL flows |
| `payment_reference` | `str` | yes | 1-64 chars, fixture-safe identifier |
| `amount_krw` | `int | None` | conditional | Required for URL creation, 0 < amount <= 10,000,000 |
| `redirect_hint` | `str | None` | no | Non-secret label or fixture redirect hint; never a real secret-bearing URL |

## Entity: OpenGiroReceipt

Domain-specific data nested under `SubmitOutput.adapter_receipt`.

| Field | Type | Validation |
|---|---|---|
| `source` | `Literal["kftc_opengiro_fixture"]` | Required in this epic |
| `operation` | `str` | Echoes the operation |
| `rsp_code` | `str` | Fixture response code, e.g. `A0000` |
| `rsp_message` | `str` | Sanitized response message |
| `status_detail` | `Literal["accepted", "pending_external_payment", "rejected", "expired", "setup_blocked"]` | Maps into `SubmitStatus` |
| `next_redirect_url` | `str | None` | Fixture URL only; real URLs are not stored in CI artifacts |
| `expires_in_seconds` | `int | None` | Payment URL expiry metadata when applicable |
| `mock` | `bool` | Always true in this epic |
| `_reference_implementation` | `str` | Transparency field |
| `_actual_endpoint_when_live` | `str` | Official KFTC target URL |
| `_security_wrapping_pattern` | `str` | OAuth/API-key/callback pattern |
| `_policy_authority` | `str` | Official KFTC URL |
| `_international_reference` | `str` | Reference analog |

## State Transitions

### Setup readiness

```text
not_requested -> active
active -> callback_missing
callback_missing -> api_key_missing
api_key_missing -> ready_for_sanitized_live_probe
ready_for_sanitized_live_probe -> live_validated
```

This epic stops at `callback_missing` or `api_key_missing` unless the operator completes portal setup outside the agent flow and provides sanitized evidence.

### Payment URL lifecycle

```text
created -> pending_external_payment -> settled
created -> expired
created -> rejected
```

Fixture tests cover `created`, `expired`, and `rejected`. Real `settled` confirmation is deferred until KFTC live evidence exists.

## Validation Rules

- New input models use `ConfigDict(frozen=True, extra="forbid")`.
- Adapter functions accept `dict[str, object]` from the `send` dispatcher and validate with their Pydantic input model.
- No top-level `SubmitInput` or `SubmitOutput` field changes.
- No raw Client Secret, token, authorization code, or personal financial identifier may be stored in any model dump used by tests.

