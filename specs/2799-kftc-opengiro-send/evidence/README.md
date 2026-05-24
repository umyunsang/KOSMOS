# KFTC OpenGiro Evidence

## Official Sources

| Source | URL | Evidence used |
|---|---|---|
| Developer starter workflow | `https://developers.kftc.or.kr/dev/starter/starter` | Service application, API Key creation, Callback URL registration, token issuance, and REST test tool sequence |
| OpenGiro bill service | `https://developers.kftc.or.kr/dev/openapi/open-giro/index` | Public bill endpoint group for create, cancel, and payment-status inquiry |
| OpenGiro payment service | `https://developers.kftc.or.kr/dev/openapi/open-giro/pay-service` | Public payment URL and payment-result endpoint group |
| OpenGiro access notice | `https://developers.kftc.or.kr/dev/support/notice/all/detail?id=44&boardCtgCd=all` | OpenGiro OpenAPI is public; documents/materials need approval |
| OpenGiro launch notice | `https://developers.kftc.or.kr/dev/support/notice/all/detail?id=45&boardCtgCd=all` | Historical launch support only |

## Portal State Observed 2026-05-18

| Portal area | State | Handling |
|---|---|---|
| `MY PAGE > 내 서비스 관리` | OpenGiro is `이용중` after user-directed service application | Recorded as readiness evidence |
| `API Key 관리` | Client ID visible, Client Secret masked, OpenGiro `부과서비스` and `납부서비스` listed | No plaintext secret recorded in repository artifacts |
| API Key registration | `등록된 Callback URL 이 없습니다.` | Live probe blocked until operator registers Callback URL |
| `문서 > 오픈지로` | Access denied | Do not invent gated spec |
| `지원 > 자료실` search `오픈지로` | 0 results | Public documents not found through 자료실 |

## Post-Registration Portal State Observed 2026-05-18

| Portal area | State | Handling |
|---|---|---|
| `API Key 관리 > Callback URL` | `https://ummaya-live-gateway-ygjh3ipzqq-du.a.run.app/auth/kftc/opengiro/callback` saved successfully | Secret-free operator URL registration completed |
| `API Key 관리 > 이용중인 서비스 > 오픈지로` | `API Key 등록` = `완료`; `Callback URL 등록` = `완료` | Portal setup advanced past the original blocker |
| `오픈API > 오픈지로` | Public bill and payment pages accessible in the logged-in browser | Public endpoint and parameter evidence confirmed |
| `문서` top-level menu | Still returns `접근 권한이 없습니다. 관리자에게 문의해 주세요.` | Gated document/material access remains unavailable |
| `도구` top-level menu | Still returns `접근 권한이 없습니다. 관리자에게 문의해 주세요.` | Portal Swagger/token tooling remains unavailable for this account |
| UMMAYA live gateway callback probe | `GET /auth/kftc/opengiro/callback?code=PROBE_CODE&state=PROBE_STATE` returns `404 {"detail":"Not Found"}` | Registered callback path is not yet implemented by the deployed gateway |

## Sanitized Live HTTP Probes 2026-05-18

All probes used official OpenGiro sample-shaped parameters from the public KFTC OpenGiro pages. No Client Secret, access token, authorization code, or personal financial identifier is included.

| Probe | Request shape | Result |
|---|---|---|
| Payment result without bearer | `GET https://api.giro.or.kr/v1/payments?ptco_code=901012345&org_tran_id=951012345T20201021152245C00012` | `400 {"rsp_code":"O0001","rsp_message":"파라미터 오류 (헤더에 Authorization Bearer Access Token이 없음)"}` |
| Payment result with invalid bearer | Same request with a redacted invalid bearer header | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` |
| Inquiry payment URL with invalid bearer | `POST https://api.giro.or.kr/v1/payments/giro-inqr-pay-url` with official sample-shaped JSON | `403 {"rsp_code":"O0201","rsp_message":"허용되지 않은 API 호출 (미존재 혹은 비활성 API)"}` |
| Payment result without bearer, development-host candidate | `GET https://testapi.giro.or.kr/v1/payments?ptco_code=951012345&org_tran_id=951012345T20201021152245C00012` | `400 {"rsp_code":"O0001","rsp_message":"파라미터 오류 (헤더에 Authorization Bearer Access Token이 없음)"}` |
| Payment result with invalid bearer, development-host candidate | Same `testapi.giro.or.kr` request with a redacted invalid bearer header | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` |
| Inquiry payment URL with invalid bearer, development-host candidate | `POST https://testapi.giro.or.kr/v1/payments/giro-inqr-pay-url` with official sample-shaped JSON | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` |
| Token endpoint candidate | `POST https://api.giro.or.kr/oauth/2.0/token` and `POST https://testapi.giro.or.kr/oauth/2.0/token` with the portal Client ID and redacted Client Secret | `403 {"rsp_code":"O0003","rsp_message":"파라미터 오류 (존재하지 않는 Client ID)"}` |

The public OpenGiro pages list `https://api.giro.or.kr/...` endpoints, but they do
not publish an OpenGiro development token endpoint in the public page body. The
`testapi.giro.or.kr` probes above are therefore recorded as development-host
candidates, not as a confirmed official path. The official next route is portal
`도구` access or 담당자 confirmation.

## Sanitized OpenAPI Sweep Probes 2026-05-19

These probes were part of the full 56-path KFTC `오픈API` tab refresh. They used
a redacted invalid bearer header and empty/minimal request bodies only. No
Client Secret, access token, authorization code, or personal financial
identifier was transmitted or stored in the repository.

| Probe | Request shape | Result | Insight |
|---|---|---|---|
| Bill create | `POST https://api.giro.or.kr/v1/bills/giro` with invalid bearer and `{}` | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Endpoint exists and reaches the OpenGiro auth layer. |
| Bill cancel | `POST https://api.giro.or.kr/v1/bills/giro/cancel` with invalid bearer and `{}` | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Same auth-layer behavior as bill create. |
| Bill payment status | `GET https://api.giro.or.kr/v1/bills/giro/payment-yn` with invalid bearer | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Status read is reachable but token-gated. |
| Inquiry payment URL | `POST https://api.giro.or.kr/v1/payments/giro-inqr-pay-url` with invalid bearer and `{}` | `403 {"rsp_code":"O0201","rsp_message":"허용되지 않은 API 호출 (미존재 혹은 비활성 API)"}` | This endpoint is not merely token-gated; current service/API activation is also insufficient. |
| Input payment URL | `POST https://api.giro.or.kr/v1/payments/giro-inpt-pay-url` with invalid bearer and `{}` | `403 {"rsp_code":"O0201","rsp_message":"허용되지 않은 API 호출 (미존재 혹은 비활성 API)"}` | Same endpoint-activation blocker as inquiry payment URL. |
| Link payment URL | `POST https://api.giro.or.kr/v1/payments/link-pay-url` with invalid bearer and `{}` | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Link payment URL reaches the auth layer, unlike the two giro payment URL variants. |
| Payment result | `GET https://api.giro.or.kr/v1/payments` with invalid bearer | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Result lookup is reachable but token-gated. |

The important new distinction is that OpenGiro does not have one uniform
"invalid token" failure mode. Some endpoints reach authentication (`O0101`);
two payment URL endpoints return `O0201`, meaning endpoint activation or service
permission must be debugged separately from token issuance.

### Development-Host Candidate Follow-Up

The same public sample-shaped payment requests were replayed against
`https://testapi.giro.or.kr` as a development-host candidate. This host is not
listed as the official OpenGiro test base in the public OpenGiro page body, so
the evidence below is useful for debugging but not sufficient for adapter
configuration.

| Probe | Request shape | Result | Insight |
|---|---|---|---|
| Inquiry payment URL | `POST https://testapi.giro.or.kr/v1/payments/giro-inqr-pay-url` with invalid bearer and official sample-shaped JSON | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | The development-host candidate reaches the OpenGiro auth layer, unlike production `O0201` for the same operation. |
| Input payment URL | `POST https://testapi.giro.or.kr/v1/payments/giro-inpt-pay-url` with invalid bearer and official sample-shaped JSON | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | This suggests production `O0201` is activation/permission-specific, not caused by malformed sample body. |
| Link payment URL | `POST https://testapi.giro.or.kr/v1/payments/link-pay-url` with invalid bearer and official sample-shaped JSON | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Consistent auth-layer rejection. |
| Payment result | `GET https://testapi.giro.or.kr/v1/payments` with invalid bearer and official sample query fields | `401 {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}` | Consistent auth-layer rejection for status/result lookup. |

### Direct Debugging Conclusions

- Production `giro-inqr-pay-url` and `giro-inpt-pay-url` return `O0201` even
  with official sample-shaped bodies and an invalid bearer. This rules out
  "empty body" as the root cause for those two endpoints.
- The development-host candidate returns `O0101` for the same two operations,
  which means the request reaches an auth layer there. The host remains a
  candidate only because the public OpenGiro page body does not publish it as
  the official test base.
- A credentialed OpenGiro token probe was attempted only against the candidate
  token endpoints, and both production and test candidate token endpoints
  rejected the portal Client ID as non-existent. Future retries must move the
  secret into operator secret storage or approved portal tooling, not repository
  files or reusable scripts.

## Current Live Blockers

- The KFTC portal setup is no longer blocked at Callback URL/API Key registration.
- Full credentialed OpenGiro execution is still blocked because the deployed UMMAYA callback URL returns 404.
- Full credentialed OpenGiro execution is still blocked because the token endpoint candidates reject the portal Client ID as non-existent.
- Full development-environment execution is still blocked because the public OpenGiro pages do not publish a complete test token path, and the portal `도구` menu is inaccessible for this account.
- The KFTC Client Secret is not committed and must not be copied into scripts,
  shell history, or documentation; any future token exchange must use operator
  secret storage.
- The KFTC developer portal `도구` menu is still inaccessible, so Swagger-based token issuance could not be used as a workaround.
- The 2026-05-19 sweep adds an endpoint-activation blocker for
  `/v1/payments/giro-inqr-pay-url` and `/v1/payments/giro-inpt-pay-url`
  (`O0201`), separate from the ordinary token blocker (`O0101`).

## Sanitization Rules

- No Client Secret, access token, authorization code, raw `Authorization` header, or raw personal financial identifier may be committed.
- Direct `curl` evidence is required before any future live conversion, with headers and personal identifiers redacted.
- Default verification remains fixture-only.
