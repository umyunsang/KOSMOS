# Contract: KFTC OpenGiro Operator Setup

## Required Setup States

| Step | Required Evidence | Secret Handling |
|---|---|---|
| OpenGiro service application | Portal row shows `오픈지로` as `이용중` | No secret involved |
| Callback URL registration | Portal shows at least one operator-approved Callback URL | Do not embed secrets in URL |
| Callback URL reachability | Registered callback URL returns a non-404 fail-closed or token-exchange response | Do not log `code`, `state`, or token material |
| API Key registration | OpenGiro `부과서비스` and `납부서비스` show API Key registered | Do not reveal Client Secret in screenshots |
| Secret provisioning | `UMMAYA_KFTC_OPENGIRO_CLIENT_ID` and secret counterpart exist in operator storage | Never commit `.env` or print values |
| Live probe readiness | Sanitized curl headers/body stored in feature evidence path | Redact Authorization, Client Secret, tokens, personal identifiers |

## Canonical Callback Path

The documented deployment path is:

```text
https://<operator-gateway-host>/auth/kftc/opengiro/callback
```

For local development, an operator may choose a localhost URL only when the local callback server exists and the portal account owner accepts that environment-specific registration.

## Fail-Closed Behavior

- Missing Callback URL: report setup blocker.
- Callback URL registered but non-routable: report setup blocker.
- Missing API Key registration: report setup blocker.
- Missing Client ID or Client Secret: report setup blocker.
- Missing access token: report setup blocker.
- Gated KFTC documents inaccessible: keep fixture mode and mark live validation incomplete.
