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
| `API Key 관리` | Client ID visible, Client Secret masked, OpenGiro `부과서비스` and `납부서비스` listed | Secret was not revealed or copied |
| API Key registration | `등록된 Callback URL 이 없습니다.` | Live probe blocked until operator registers Callback URL |
| `문서 > 오픈지로` | Access denied | Do not invent gated spec |
| `지원 > 자료실` search `오픈지로` | 0 results | Public documents not found through 자료실 |

## Sanitization Rules

- No Client Secret, access token, authorization code, raw `Authorization` header, or raw personal financial identifier may be committed.
- Direct `curl` evidence is required before any future live conversion, with headers and personal identifiers redacted.
- Default verification remains fixture-only.
