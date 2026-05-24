# KFTC OpenAPI Sidebar Debug Report

This report is the per-section debugging ledger for the KFTC developer-site `오픈API` header tab and its left sidebar accordion content collected on 2026-05-19. It complements `kftc-openapi-endpoint-inventory.md`: the inventory is the compact table, while this file records the deeper decision and debugging state.

The filename keeps the earlier 56-section wording for link stability, but the scroll-verified browser pass corrected the source count:

| Source surface | Count | Meaning |
|---|---:|---|
| Left-sidebar `button.title` rows | 57 | Includes accordion headings and leaf menu items visible in the OpenAPI sidebar DOM. |
| Unique `vueMovePage(...)` routes | 49 | De-duplicated routable pages actually opened from the sidebar. |
| Pages with request-message specs | 42 | Pages that expose request tables under the public `오픈API` tab. |
| Pages with at least one HTTP URL row | 40 | Pages where a concrete endpoint or URL template was visible. |

No plaintext Client Secret, access token, authorization code, raw Authorization header, or real citizen financial identifier is stored here. Initial endpoint-reachability probes used missing/invalid redacted bearer headers or official sample-shaped dummy bodies. The later OpenBanking test-host pass used the operator-provided non-production Client ID/Secret only in direct `curl` calls and records sanitized results here.

## Source Discipline Correction

The current source of truth is the header-menu `오픈API` tab plus the left sidebar accordion only. The `문서`, `도구`, and `자료실` menus are approval-gated for this account and are not used as evidence in this report unless explicitly noted as a blocker. This matters because those gated menus can be useful later for Swagger/token tooling, but they are not required to read the public OpenAPI endpoint tables.

## Codex/Chrome Scroll Debugging Note

The browser-control issue was not a KFTC page defect. The official OpenAI Codex Chrome extension documentation confirms Chrome is the right browser surface when a task needs signed-in browser state. The installed Codex Chrome plugin's local API schema exposes supported scroll calls as `tab.cua.scroll(...)` and `tab.dom_cua.scroll(...)`; direct JavaScript scrolling through `window.scrollTo(...)` or assigning `documentElement.scrollTop` failed inside the wrapper.

Verified working call shape:

```text
tab.cua.scroll({ x: 500, y: 500, scrollY: 900, scrollX: 0 })
```

Important debugging details:

- `tab.cua.scroll({ x: 900, y: 700, ... })` failed with `Position out of bounds`; the coordinate must be inside the browser content viewport.
- `tab.cua.scroll({ x: 500, y: 500, scrollY: 900, scrollX: 0 })` moved the KFTC page from `documentElement.scrollTop=0` to `653` on `/dev/openapi/bankpay/pg`.
- The scroll-verified capture then opened all 49 unique sidebar routes and recorded `scrollTop` changes plus the page text, request URLs, methods, and scope hints.

## Debug Method

1. Enter the official developer site through header `오픈API`, not `문서`, `도구`, or `자료실`.
2. Use the left sidebar accordion routes and capture each public `/dev/openapi/**` page.
3. Scroll the page using Codex CUA scroll, then extract visible HTTP URL rows, method, required request fields, and OAuth scope hints.
4. Run direct `curl` probes for concrete endpoint URLs only. Skip official URL templates such as `{버전}` instead of guessing.
5. Classify the first failing boundary: no URL, DNS, TCP, HTTP auth envelope, endpoint activation, token flow, or approval gate.
6. Map the section into UMMAYA `find` / `locate` / `send` / `check` primitives with fail-closed Live criteria.

## 2026-05-19 Direct Replay Log

The latest pass did not treat this document as the main work item. It used the
developer-site tables as request evidence, executed direct HTTP probes, then
recorded only the debugging result here.

Representative direct `curl` checks:

| Surface | Request | Response | Debugging insight |
|---|---|---|---|
| OpenBanking balance | `GET /v2.0/account/balance/fin_num` with dummy query fields and no bearer | HTTP 200 `O0001` / `인증 파라미터 오류([992])` | The endpoint is reachable and rejects before business validation when Authorization is missing. |
| OpenBanking balance | Same request with invalid bearer | HTTP 200 `O0002` / `Access Token 거부` | Business read endpoints are blocked at token validation, not DNS or body shape. |
| OpenBanking token | `GET /oauth/2.0/token` | HTTP 200 `O0010` / method not allowed | The token endpoint exists and expects POST. |
| OpenBanking token | `POST /oauth/2.0/token` with dummy client-credentials form | HTTP 200 `O0001` / `인증 파라미터 오류([3000201])` | The endpoint parses token form data; real Client Secret must be supplied only through operator secret storage. |
| OpenGiro payment result | `GET /v1/payments` without bearer | HTTP 400 `O0001` / missing Authorization bearer | OpenGiro has an explicit missing-bearer guard. |
| OpenGiro production payment URL | `POST /v1/payments/giro-inqr-pay-url` with official sample-shaped body and invalid bearer | HTTP 403 `O0201` | Production payment URL is activation/permission blocked even with sample-shaped body. |
| OpenGiro development-host candidate | `POST https://testapi.giro.or.kr/v1/payments/giro-inqr-pay-url` and `giro-inpt-pay-url` with sample-shaped body and invalid bearer | HTTP 401 `O0101` | The candidate host reaches the auth layer, unlike production `O0201`; still not official until KFTC tool/담당자 confirmation. |
| FIN MAP | System resolver plus public DNS checks for `openapi.finmap.or.kr` | No A record returned | Live work is blocked before HTTP; this is DNS/VPN/allowlist/tool-access, not adapter code. |
| PayInfo account/loan | `POST` to visible account and loan URLs | `curl` connect timeout | Hostnames resolve but TCP does not complete from this network. |
| Bio | Production URL and `testbioapi.kftc.or.kr:8443` URL; KFTC 인증인프라업무팀 email reply | Production DNS fail; test host HTTP 404 HTML; official reply says Bio authentication is for corporate customers and requires application, service review, approval, and contract completion | Policy/contract gate now precedes technical debugging. Treat as corporate-contract handoff/mock under the current project account; no Live adapter or test execution without corporate approval credentials. |
| P2P | Production base and unofficial `/v1/loans/contract` hypothesis; test base; KFTC P2P금융업무팀 email reply | Production HTTP 403 / `B0102`; test TCP timeout; official reply says use is limited to 금융당국-registered 온투업자 and requires prior consultation plus registration proof | Production host exists, but UMMAYA is policy-gated before technical debugging. Treat as institutional handoff/mock unless regulated-provider eligibility is proved. |

Full replay summary for concrete non-template endpoint URLs:

| Replay bucket | Count | Meaning |
|---|---:|---|
| `AUTH_REJECT_INVALID_BEARER` | 26 | Endpoint reached provider auth envelope and rejected the invalid bearer. |
| `DNS_FAIL` | 18 | Hostname did not resolve from this network. |
| `HTTP_404_ROUTE_OR_GATE` | 11 | Test host answered HTTP but route/gate was not accepted. |
| `TCP_TIMEOUT` | 7 | DNS resolved but TCP connection did not complete. |
| `ENDPOINT_INACTIVE_OR_NOT_ALLOWED` | 2 | Endpoint exists but current service/API activation is insufficient. |

## 2026-05-19 Credentialed Test-Host Findings

After the operator supplied a non-production Client ID and Client Secret, direct `curl` probes were run against the OpenBanking test host. The secret and returned bearer are intentionally not stored in this repository.

| Probe | Result | Debugging insight |
|---|---|---|
| `POST https://testapi.openbanking.or.kr/oauth/2.0/token` with `grant_type=client_credentials&scope=oob` | HTTP 200 token issued; response included `scope=oob` and `client_use_code=M202601315` | The Client ID/Secret is accepted by the OpenBanking test host for 2-legged `oob`. |
| Same token endpoint with `scope=inquiry`, `transfer`, `cardinfo`, `fintechinfo`, `insuinfo`, `finmap` | HTTP 200 provider error `O0001 인증 파라미터 오류([3000103])` | These scopes are not issued through the tested client-credentials path. For `inquiry`, the OAuth page explains the 3-legged user consent/account-registration path, not pure client credentials. |
| Same token endpoint with `scope=sa` | HTTP 200 provider error `O0011 허용되지 않은 Scope 입니다.` | User-authentication/account-registration scope is not available through this client-credentials call. |
| `GET /v2.0/account/balance/fin_num` on `testapi.openbanking.or.kr` with issued `oob` token | `O0011 허용되지 않은 Scope 입니다.` | Balance is correctly gated by the page's `scope=inquiry`; the endpoint is not blocked by DNS or Client ID. |
| `GET /v2.0/account/transaction_list/fin_num` on test host with issued `oob` token | `O0011 허용되지 않은 Scope 입니다.` | Transaction history shares the same `inquiry` delegated-user gate. |
| `POST /v2.0/inquiry/real_name` with `oob` token and sample-shaped body, but wrong `bank_tran_id` prefix | `A0004` with message that the `bank_tran_id` prefix must match the institution code | The token passed far enough to validate business-message format. `bank_tran_id` must begin with the returned `client_use_code`. |
| `POST /v2.0/inquiry/real_name` with `bank_tran_id=M202601315U` plus 9 AN chars | `A0002` / simulator response message missing; response echoed bank/account fields | Auth, token scope, prefix, and 20-char shape passed; the next blocker is test simulator fixture data, not OAuth. |
| `POST /v2.0/inquiry/receive` with corrected `bank_tran_id` | `A0322` unregistered contracted withdrawal account | Auth passed; the next blocker is the service's registered `cntr_account_num` test data. |

The key root-cause split is now concrete:

- `oob` is immediately testable with client credentials and supports institution-side checks such as account-name verification and receive inquiry.
- `inquiry` is a delegated user/account-registration token path. It needs the OAuth authorization-code/account-registration flow and a `fintech_use_num` before balance, transaction, card, prepaid, insurance, or loan-list reads can proceed.
- Transfer/payment APIs remain `send`-class and require a separate confirmation/idempotency/receipt design even after token issuance.

## Cross-Section Insights

- OpenBanking business endpoints are reachable and fail at the token boundary with provider JSON (`O0002`), so the next real blocker is OAuth/test-user/token readiness, not endpoint DNS or request body shape.
- OpenBanking token endpoint candidates on `openapi.openbanking.or.kr` and `testapi.openbanking.or.kr` respond on port 443; a GET returns method rejection and a POST with insufficient form data returns parameter rejection. Port 8443 on `testapi.openbanking.or.kr` times out.
- OpenGiro production has mixed behavior: bill/link/result endpoints reach auth (`O0101`), while two payment URL endpoints return `O0201` even with official sample-shaped bodies. That is an endpoint activation or service permission blocker separate from token issuance.
- `testapi.giro.or.kr` reaches auth (`O0101`) for the payment URL endpoints, so it is a useful development-host candidate, but it must be confirmed through KFTC tools or 담당자 before being treated as official.
- FIN MAP production hostnames do not resolve from public DNS in this environment. Bio production DNS also failed in direct probes, but KFTC's later 인증인프라업무팀 reply makes Bio a policy/contract gate before further route, token, or mTLS debugging.
- PayInfo account/loan hosts resolve but TCP connect times out. Treat this as network allowlist/testbed access, not an adapter-code issue.
- P2P public URL rows contain `{버전}` placeholders. Do not infer a version in adapter code.

## Scope Taxonomy

- `inquiry`: 3-legged delegated user token after consent/account registration; fintech_use_num based account read.
- `oob`: 2-legged/client or delegated OpenBanking token for institution-side oob calls; send/check flows still need user intent and permission gates.
- `transfer`: transfer-scoped token for withdrawal. Highest-risk money movement; never live without explicit confirmation and idempotency.
- `cardinfo`: card information scope. Usually combined with `sa` user authentication/registration scope.
- `fintechinfo`: prepaid/fintech information scope. Usually combined with `sa`.
- `insuinfo`: insurance/loan information scope as exposed by the KFTC page. Usually combined with `sa`.
- `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.

## Earlier 56-Section Ledger

This ledger is retained for continuity with the first generated pass. The
scroll-verified sidebar count at the top of this file is the current source
count for the investigation.

### 01. `/dev/openapi` — 오픈API 루트 / 오픈API 안내

- **Function**: 금융결제원 개발자사이트 오픈API 카탈로그 루트입니다. 자체 업무 API가 아니라 서비스군으로 진입하는 목차 역할입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: Catalog/handoff only; no adapter until URL and policy exist. Current fit: catalog: 어댑터 대상 아님
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 02. `/dev/openapi/open-banking` — 오픈뱅킹 / 오픈뱅킹 안내

- **Function**: 오픈뱅킹 서비스군 안내/alias 섹션입니다. 실제 어댑터 단위는 OAuth, 잔액, 거래내역, 실명조회, 이체, 카드, 선불, 보험, 대출리스 하위 섹션으로 분리해야 합니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 03. `/dev/openapi/account-info` — 어카운트인포 / 어카운트인포 안내

- **Function**: 어카운트인포 서비스군 안내/alias 섹션입니다. 계좌통합조회와 계좌해지·잔고이전 하위 기능으로 나누어 다룹니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/accountinfo/list`
- **Required request inputs**: `inquiry_bank_type`, `trace_no`, `inquiry_record_cnt`
- **Token/scope requirement**: `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/accountinfo/list` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 계좌통합 조회
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 04. `/dev/openapi/finance-certification` — 금융인증 / 금융인증

- **Function**: 금융인증 서비스군 섹션입니다. 오픈API 탭에서 공개 HTTP URL이 보이지 않아 금융인증서/인증 절차는 승인자료 확보 전까지 handoff/mock 대상입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check; 승인자료 전까지 handoff/mock
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 05. `/dev/openapi/bio/register` — 바이오인증 / 바이오 등록

- **Function**: 이용기관이 생체인증 서비스를 제공할 때 고객 신원을 확인하고 생체정보를 이용기관과 분산관리시스템에 분할 저장하는 등록 API입니다.
- **Official endpoint evidence**: `POST https://bioapi.kftc.or.kr/v1/bio/procDlgRegi`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgRegi`; `POST https://bioapi.kftc.or.kr/v1/bio/procRegi`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/procRegi`
- **Official policy evidence**: KFTC 인증인프라업무팀 replied on 2026-05-19 KST that 바이오인증 is provided to corporate customers and can be used only after 이용신청, 서비스 검토, 이용승인, and 계약체결. 개인고객, 개인사업자, and research-purpose use are not supported.
- **Required request inputs**: `Authorization`, `trx_id`, `auth_co_code`, `cmpb_auth_tech_code`, `svc_code`, `reg_type_code`, `user_key_id`, `re_regi_yn`, `key_ver`, `enc_data1`, `enc_data2`, `enc_data3` 외 1개
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://bioapi.kftc.or.kr/v1/bio/procDlgRegi` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgRegi` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/procRegi` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/procRegi` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html>
- **Root-cause classification**: policy/contract gate. The DNS/404 results are retained as technical evidence, but KFTC's official reply means current-account Live debugging stops before route, token, or mTLS work.
- **UMMAYA adapter mapping**: Corporate-contract handoff/mock only. Registration is a protected `send`-class scenario shape for future institutional integrations, not a Live adapter under the current project account.
- **Next debugging action**: Do not retry Live/test calls for registration until a corporate customer contract, use approval, and service credential are obtained. Preserve only schema-faithful mock/handoff documentation.

### 06. `/dev/openapi/open-giro` — 오픈지로 / 오픈지로 안내

- **Function**: 오픈지로 부과서비스 안내/alias 섹션입니다. 고지내역 등록, 취소, 납부여부 조회 기능으로 분해됩니다.
- **Official endpoint evidence**: `POST https://api.giro.or.kr/v1/bills/giro`; `POST https://api.giro.or.kr/v1/bills/giro/cancel`; `GET https://api.giro.or.kr/v1/bills/giro/payment-yn`
- **Required request inputs**: `Authorization`, `ptco_code`, `cls_code`, `giro_no`, `cust_inqr_no`, `dudt_in_amt`, `dudt_aft_amt`, `data_form_type`, `dudt`, `noti_dl_dt`, `epay_no`, `noti_issu_type` 외 4개
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://api.giro.or.kr/v1/bills/giro` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}<br>`POST https://api.giro.or.kr/v1/bills/giro/cancel` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}<br>`GET https://api.giro.or.kr/v1/bills/giro/payment-yn` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}
- **Root-cause classification**: endpoint는 auth layer까지 도달한다. 실패 경계는 OpenGiro token 발급/등록/callback readiness다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; 현 mock 유지 후 token/callback/tool 승인 시 Live
- **Next debugging action**: Implement/verify callback and token acquisition outside repo secrets, then compare live receipt shape to existing mock fixture.

### 07. `/dev/openapi/p2p` — 온투업중앙기록관리 / 온투업중앙기록관리 안내

- **Function**: 온투업중앙기록관리 안내/alias 섹션입니다. P2P 대출계약, 투자계약, 양도양수 기록 API가 하위 기능입니다.
- **Official endpoint evidence**: `POST https://openapi.p2pcenter.or.kr/v{버전}/loans/contract`; `POST https://testapi.p2pcenter.or.kr/v{버전}/loans/contract`
- **Required request inputs**: `거래일시(밀리세컨드)`, `대출계약 정보`, `차입자 정보`, `대출상환 예정정보 목록`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.p2pcenter.or.kr/v{버전}/loans/contract` -> `SKIP_TEMPLATE` version placeholder<br>`POST https://testapi.p2pcenter.or.kr/v{버전}/loans/contract` -> `SKIP_TEMPLATE` version placeholder
- **Official email evidence**: KFTC P2P금융업무팀 replied on 2026-05-19 KST that 온투업 중앙기록관리업무 API is for 금융당국-registered 온투업자 to record 온투업 transaction information with the central record-management institution. Developer-site use requires prior consultation with the team, including proof such as 온투업자 등록신청 증빙. If 온투업자 registration is not complete, API use is difficult to permit.
- **Root-cause classification**: 공식 URL이 `{버전}` placeholder 상태인 것보다 더 앞선 policy gate가 있다. 현재 계정은 등록 온투업자 증빙이 없으므로 테스트데이터/테스트계정 제공과 Live 호출을 진행할 수 없다.
- **UMMAYA adapter mapping**: `send`-class institutional scenario only. Do not implement a Live adapter or hardcode a guessed version. Current fit: handoff/mock for regulated-provider record submission.
- **Next debugging action**: Stop technical retries for P2P under this account. Reopen only if the project can provide regulated 온투업자 eligibility proof or a partner institution account.

### 08. `/dev/openapi/datop` — 금융결제데이터개방 / 금융결제데이터개방 안내

- **Function**: 금융결제데이터개방/Datop 안내 섹션입니다. 개발자사이트는 dataset별 상세 URL 대신 Datop 데이터셋 선택 흐름을 가리킵니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; dataset별 schema 필요
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 09. `/dev/openapi/map` — FIN MAP / FIN MAP 안내

- **Function**: FIN MAP 안내/alias 섹션입니다. 환경정보, ATM/지점 통합조회, ATM/지점 상세, 수수료 조회 하위 기능으로 나뉩니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/env_lists`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/env_lists` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 10. `/dev/openapi/loan` — 대출이동 / 대출이동 안내

- **Function**: 대출이동 안내/alias 섹션입니다. 개인신용대출, 주택담보대출, 전세대출, 개인사업자 대출 조회/상환정보 하위 기능으로 나뉩니다.
- **Official endpoint evidence**: `POST https://openapi.payinfo.or.kr/loanswitch/v1.0/loan/repayment`; `POST https://testapi.payinfo.or.kr:8443/loanswitch/v1.0/loan/repayment`
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `보유기관 금융회사 코드`, `하위 보유기관 코드`, `대출식별번호`, `조회요청일자`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.payinfo.or.kr/loanswitch/v1.0/loan/repayment` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to openapi.payinfo.or.kr port 443 after 3003 ms: Timeout was reached<br>`POST https://testapi.payinfo.or.kr:8443/loanswitch/v1.0/loan/repayment` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to testapi.payinfo.or.kr port 8443 after 3005 ms: Timeout was reached
- **Root-cause classification**: DNS는 되지만 TCP connect timeout이다. traceroute도 KFTC/상위망 근처에서 멈추므로 승인망/allowlist 병목으로 본다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Ask KFTC/PayInfo for approved test network or allowlist. TCP success is the next evidence gate.

### 11. `/dev/openapi/bankpay` — 뱅크페이 / 뱅크페이 안내

- **Function**: 뱅크페이 안내/alias 섹션입니다. 가맹점의 계좌이체PG 연계를 위한 API군이지만 공개 HTTP URL row는 없습니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; 가맹점계약 전 handoff/mock
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 12. `/dev/openapi/open-banking/oauth` — 오픈뱅킹 / OAuth 인증

- **Function**: 오픈뱅킹 OAuth 인증 설명 섹션입니다. OAuth 2.0 Authorization Code Grant를 준용하며 사용자 동의, 계좌등록, access token, fintech_use_num 수집이 하위 업무 API의 전제입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 업무 endpoint가 아니라 토큰/계좌등록 전제 섹션이다. 공식 페이지는 auth-code grant와 fintech_use_num 개념을 설명하지만 URL row는 제공하지 않는다. 별도 token endpoint는 직접 probe에서 443이 HTTP 응답함을 확인했다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/delegation foundation; gated docs 필요
- **Next debugging action**: Model this as a UMMAYA `check`/delegation setup tool: collect auth-code callback, exchange token through operator secret storage, persist only token metadata, then hand `user_seq_no`/`fintech_use_num` to downstream read/send adapters.

### 13. `/dev/openapi/open-banking/balance` — 오픈뱅킹 / 잔액조회

- **Function**: 사용자 계좌의 잔액을 fintech_use_num 기준으로 조회하는 오픈뱅킹 read-only API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/account/balance/fin_num`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `inquiry`: 3-legged delegated user token after consent/account registration; fintech_use_num based account read.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/account/balance/fin_num` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 14. `/dev/openapi/open-banking/transaction` — 오픈뱅킹 / 거래내역조회

- **Function**: 사용자 계좌의 거래내역을 조회하는 오픈뱅킹 read-only API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/account/transaction_list/fin_num`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `inquiry`: 3-legged delegated user token after consent/account registration; fintech_use_num based account read.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/account/transaction_list/fin_num` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 15. `/dev/openapi/open-banking/account` — 오픈뱅킹 / 계좌실명조회

- **Function**: 계좌번호와 예금주 실명 일치 여부를 확인하는 오픈뱅킹 계좌실명조회 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/real_name`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `oob`: 2-legged/client or delegated OpenBanking token for institution-side oob calls; send/check flows still need user intent and permission gates.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/real_name` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check; 계좌실명 검증
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 16. `/dev/openapi/open-banking/deposit` — 오픈뱅킹 / 입금이체

- **Function**: 이용기관이 목적지 계좌로 대금을 송금하는 입금이체 API입니다. fintech_use_num 방식과 실계좌번호 방식 두 endpoint가 있습니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/transfer/deposit/fin_num`; `POST https://openapi.openbanking.or.kr/v2.0/transfer/deposit/acnt_num`
- **Required request inputs**: `cntr_account_type`, `cntr_account_num`, `wd_pass_phrase`, `wd_print_content`, `name_check_option`, `tran_dtime`, `req_cnt`, `tran_no`, `bank_tran_id`, `fintech_use_num`, `print_content`, `tran_amt` 외 3개
- **Token/scope requirement**: `oob`: 2-legged/client or delegated OpenBanking token for institution-side oob calls; send/check flows still need user intent and permission gates.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/transfer/deposit/fin_num` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}<br>`POST https://openapi.openbanking.or.kr/v2.0/transfer/deposit/acnt_num` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; OAuth+동의+멱등성+권한 필수
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 17. `/dev/openapi/open-banking/withdraw` — 오픈뱅킹 / 출금이체

- **Function**: 사용자 계좌에서 출금이체를 수행하는 고위험 transfer API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/transfer/withdraw/fin_num`
- **Required request inputs**: `bank_tran_id`, `cntr_account_type`, `cntr_account_num`, `dps_print_content`, `fintech_use_num`, `tran_amt`, `tran_dtime`, `req_client_name`, `req_client_num`, `transfer_purpose`
- **Token/scope requirement**: `transfer`: transfer-scoped token for withdrawal. Highest-risk money movement; never live without explicit confirmation and idempotency.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/transfer/withdraw/fin_num` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; OAuth+동의+멱등성+권한 필수
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 18. `/dev/openapi/open-banking/receipt` — 오픈뱅킹 / 수취조회

- **Function**: 입금이체 전 수취계좌의 입금가능 여부와 수취인 성명을 확인하는 수취조회 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/receive`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `oob`: 2-legged/client or delegated OpenBanking token for institution-side oob calls; send/check flows still need user intent and permission gates.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/receive` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/find; 위임 토큰 필요
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 19. `/dev/openapi/open-banking/remitter` — 오픈뱅킹 / 송금인정보조회

- **Function**: 소액해외송금 등에서 수취계좌 입금 송금인의 성명과 계좌번호 내역을 확인하는 송금인정보조회 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/remit_list`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `oob`: 2-legged/client or delegated OpenBanking token for institution-side oob calls; send/check flows still need user intent and permission gates.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/inquiry/remit_list` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/find; 위임 토큰 필요
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 20. `/dev/openapi/open-banking/mgrapi` — 오픈뱅킹 / 관리API

- **Function**: 참가은행 상태조회 등 이용기관 운영 관리를 위한 관리API 설명 섹션입니다. 공개 HTTP URL row는 없습니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/delegation foundation; gated docs 필요
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 21. `/dev/openapi/open-banking/cards` — 오픈뱅킹 / 카드목록조회

- **Function**: 오픈뱅킹센터에 등록된 사용자의 신용/체크카드 발급 목록을 카드사별로 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/cards`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `befor_inquiry_trace_info`
- **Token/scope requirement**: `cardinfo`: card information scope. Usually combined with `sa` user authentication/registration scope.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/cards` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 22. `/dev/openapi/open-banking/issue_info` — 오픈뱅킹 / 카드기본정보조회

- **Function**: 카드 식별자를 이용해 카드 구분, 결제계좌 등 기본정보를 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/cards/issue_info`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `card_id`
- **Token/scope requirement**: `cardinfo`: card information scope. Usually combined with `sa` user authentication/registration scope.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/cards/issue_info` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 23. `/dev/openapi/open-banking/bills` — 오픈뱅킹 / 카드청구기본정보조회

- **Function**: 사용자의 월별 카드 청구 목록을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/cards/bills`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `from_month`, `to_month`
- **Token/scope requirement**: `cardinfo`: card information scope. Usually combined with `sa` user authentication/registration scope.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/cards/bills` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 24. `/dev/openapi/open-banking/bills_detail` — 오픈뱅킹 / 카드청구상세정보조회

- **Function**: 특정 청구월/정산순번 기준 카드 청구 상세 내역을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/cards/bills/detail`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `charge_month`, `settlement_seq_no`
- **Token/scope requirement**: `cardinfo`: card information scope. Usually combined with `sa` user authentication/registration scope.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/cards/bills/detail` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 25. `/dev/openapi/open-banking/pays-list` — 오픈뱅킹 / 선불목록조회

- **Function**: 사용자의 선불전자지급수단 목록을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/pays`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`
- **Token/scope requirement**: `fintechinfo`: prepaid/fintech information scope. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/pays` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 26. `/dev/openapi/open-banking/pays-reload` — 오픈뱅킹 / 선불연계정보조회

- **Function**: 선불수단의 연계/충전 관련 정보를 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/pays/reload`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id`
- **Token/scope requirement**: `fintechinfo`: prepaid/fintech information scope. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/pays/reload` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 27. `/dev/openapi/open-banking/pays-balances` — 오픈뱅킹 / 선불잔액조회

- **Function**: 선불수단 잔액을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/pays/balances`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id`
- **Token/scope requirement**: `fintechinfo`: prepaid/fintech information scope. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/pays/balances` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 28. `/dev/openapi/open-banking/pays-transactions` — 오픈뱅킹 / 선불거래내역조회

- **Function**: 선불수단 거래내역을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/pays/transactions`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id`, `from_date`, `to_date`, `befor_inquiry_trace_info`
- **Token/scope requirement**: `fintechinfo`: prepaid/fintech information scope. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/pays/transactions` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 29. `/dev/openapi/open-banking/insurances-list` — 오픈뱅킹 / 보험목록조회

- **Function**: 등록 사용자의 보험목록을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/insurances`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`
- **Token/scope requirement**: `insuinfo`: insurance/loan information scope as exposed by the KFTC page. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/insurances` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 30. `/dev/openapi/open-banking/insurances-payment` — 오픈뱅킹 / 보험납입정보조회

- **Function**: 특정 보험계약의 납입정보를 조회하는 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/insurances/payment`
- **Required request inputs**: `bank_tran_id`, `bank_code_std`, `user_seq_no`, `insu_num`
- **Token/scope requirement**: `insuinfo`: insurance/loan information scope as exposed by the KFTC page. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/insurances/payment` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/find; 위임 토큰 필요
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 31. `/dev/openapi/open-banking/loans-list` — 오픈뱅킹 / 대출리스목록조회

- **Function**: 등록 사용자의 대출/리스 목록을 조회하는 API입니다.
- **Official endpoint evidence**: `GET https://openapi.openbanking.or.kr/v2.0/loans`
- **Required request inputs**: `bank_tran_id`, `user_seq_no`, `bank_code_std`
- **Token/scope requirement**: `insuinfo`: insurance/loan information scope as exposed by the KFTC page. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `GET https://openapi.openbanking.or.kr/v2.0/loans` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 금융자산/거래 조회, PII gate
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 32. `/dev/openapi/open-banking/loans-basic` — 오픈뱅킹 / 대출리스기본정보조회

- **Function**: 특정 대출/리스 계좌의 기본정보를 조회하는 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/loans/basic`
- **Required request inputs**: `bank_tran_id`, `bank_code_std`, `account_num`, `user_seq_no`, `from_date`, `to_date`
- **Token/scope requirement**: `insuinfo`: insurance/loan information scope as exposed by the KFTC page. Usually combined with `sa`.; `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/loans/basic` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: check/find; 위임 토큰 필요
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 33. `/dev/openapi/account-info/inquiry` — 어카운트인포 / 계좌통합조회

- **Function**: 전 금융기관에 개설된 사용자의 계좌내역을 통합 조회하는 어카운트인포 API입니다.
- **Official endpoint evidence**: `POST https://openapi.openbanking.or.kr/v2.0/accountinfo/list`
- **Required request inputs**: `inquiry_bank_type`, `trace_no`, `inquiry_record_cnt`
- **Token/scope requirement**: `sa`: user authentication/account registration scope. Required to bind user_seq_no or fintech_use_num before downstream reads.
- **Direct probe result**: `POST https://openapi.openbanking.or.kr/v2.0/accountinfo/list` -> `200` {"rsp_code":"O0002","rsp_message":"Access Token 거부"}
- **Root-cause classification**: endpoint는 정상 도달한다. invalid token이 KFTC JSON envelope로 거절되므로 실패 경계는 네트워크나 body가 아니라 token/user delegation이다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; 계좌통합 조회
- **Next debugging action**: Do token-readiness first, then promote read-only `find` APIs. Transfer APIs remain blocked until explicit transfer scope, confirmation UI, idempotency, and receipt evidence exist.

### 34. `/dev/openapi/account-info/account` — 어카운트인포 / 계좌해지·잔고이전

- **Function**: 계좌해지 가능여부, 잔고이전 수취계좌 확인, 예상금액, 해지/잔고이전 요청, 결과조회를 포함하는 계좌 상태변경 API군입니다.
- **Official endpoint evidence**: `POST https://accountapi.payinfo.or.kr/termination/v1.0/eligibility`; `POST https://accountapi.payinfo.or.kr/termination/v1.0/recipient`; `POST https://accountapi.payinfo.or.kr/termination/v1.0/status`; `POST https://accountapi.payinfo.or.kr/termination/v1.0/transfer`; `POST https://accountapi.payinfo.or.kr/termination/v1.0/result`
- **Required request inputs**: `api_trx_num`, `api_trx_dtm`, `api_org_code`, `delegation_yn`, `delegation_dtm`, `user_name`, `user_email`, `bank_code`, `account_num`, `identity_num`, `account_type`, `recv_bank_code` 외 14개
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://accountapi.payinfo.or.kr/termination/v1.0/eligibility` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to accountapi.payinfo.or.kr port 443 after 3003 ms: Timeout was reached<br>`POST https://accountapi.payinfo.or.kr/termination/v1.0/recipient` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to accountapi.payinfo.or.kr port 443 after 3003 ms: Timeout was reached<br>`POST https://accountapi.payinfo.or.kr/termination/v1.0/status` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to accountapi.payinfo.or.kr port 443 after 3002 ms: Timeout was reached<br>`POST https://accountapi.payinfo.or.kr/termination/v1.0/transfer` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to accountapi.payinfo.or.kr port 443 after 3003 ms: Timeout was reached<br>`POST https://accountapi.payinfo.or.kr/termination/v1.0/result` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to accountapi.payinfo.or.kr port 443 after 3006 ms: Timeout was reached
- **Root-cause classification**: DNS는 되지만 TCP connect timeout이다. traceroute도 KFTC/상위망 근처에서 멈추므로 승인망/allowlist 병목으로 본다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: check/find/send 혼합; 해지·잔고이전은 send 보호
- **Next debugging action**: Ask KFTC/PayInfo for approved test network or allowlist. TCP success is the next evidence gate.

### 35. `/dev/openapi/bio/auth` — 바이오인증 / 바이오 인증

- **Function**: 바이오 인증, 인증정보조회, 인증결과보고를 포함하는 바이오인증 API군입니다.
- **Official endpoint evidence**: `POST https://bioapi.kftc.or.kr/v1/bio/procDlgAuth`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgAuth`; `POST https://bioapi.kftc.or.kr/v1/bio/searchAuthBio`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchAuthBio`; `POST https://bioapi.kftc.or.kr/v1/bio/reportAuthRlst`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/reportAuthRlst`
- **Official policy evidence**: KFTC 인증인프라업무팀 replied on 2026-05-19 KST that 바이오인증 is a corporate-customer service available only after application, review, approval, and contract execution; individual, sole-proprietor, and research use is not supported.
- **Required request inputs**: `Authorization`, `trx_id`, `auth_co_code`, `cmpb_auth_tech_code`, `key_ver`, `enc_data1`, `enc_data2`, `enc_data3`, `div_bio_info`, `auth_rslt`, `auth_dtm`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://bioapi.kftc.or.kr/v1/bio/procDlgAuth` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgAuth` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/searchAuthBio` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchAuthBio` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/reportAuthRlst` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/reportAuthRlst` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html>
- **Root-cause classification**: policy/contract gate. The technical probes show route/network constraints, but official eligibility blocks current-account Live execution first.
- **UMMAYA adapter mapping**: Corporate-contract handoff/mock only. Authentication remains a future `check` scenario shape for approved corporate integrations.
- **Next debugging action**: Stop Live/test retries under the current account. Resume only after corporate-customer approval and contract-backed service credentials exist.

### 36. `/dev/openapi/bio/manage` — 바이오인증 / 바이오 관리

- **Function**: 바이오정보 조회, 삭제, 블랙리스트 해지, 공개키 조회를 포함하는 관리 API군입니다.
- **Official endpoint evidence**: `POST https://bioapi.kftc.or.kr/v1/bio/searchBioInfo`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchBioInfo`; `POST https://bioapi.kftc.or.kr/v1/bio/revokeBioInfo`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/revokeBioInfo`; `POST https://bioapi.kftc.or.kr/v1/bio/reactiveBio`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/reactiveBio`; `POST https://bioapi.kftc.or.kr/v1/bio/searchPubKeyInfo`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchPubKeyInfo`
- **Official policy evidence**: KFTC 인증인프라업무팀 replied on 2026-05-19 KST that 바이오인증 is a corporate-customer service and requires application, service review, use approval, and contract execution before use.
- **Required request inputs**: `Authorization`, `trx_id`, `svc_code`, `user_key_id`, `bio_type`, `no_iden_cfnm_key`, `svc_type`, `proc_type`, `auth_co_code`, `pub_org_code`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://bioapi.kftc.or.kr/v1/bio/searchBioInfo` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchBioInfo` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/revokeBioInfo` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/revokeBioInfo` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/reactiveBio` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/reactiveBio` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/searchPubKeyInfo` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchPubKeyInfo` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html>
- **Root-cause classification**: policy/contract gate. Management operations include sensitive lookup, deletion, and status changes, so current-account Live execution is blocked before technical remediation.
- **UMMAYA adapter mapping**: Corporate-contract handoff/mock only. Lookup is future `find`/`check`; deletion and blacklist reactivation are protected `send` shapes only after institutional approval.
- **Next debugging action**: Do not issue further management calls without corporate approval, contract-backed credentials, and written data-handling requirements.

### 37. `/dev/openapi/bio/linkAuth` — 바이오인증 / 연계인증

- **Function**: 연계바이오조회와 연계인증을 제공하는 바이오 연계인증 API군입니다.
- **Official endpoint evidence**: `POST https://bioapi.kftc.or.kr/v1/bio/searchCombiAuth`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchCombiAuth`; `POST https://bioapi.kftc.or.kr/v1/bio/procCombiAuth`; `POST https://testbioapi.kftc.or.kr:8443/v1/bio/procCombiAuth`
- **Official policy evidence**: KFTC 인증인프라업무팀 replied on 2026-05-19 KST that Bio authentication is not available for individual, sole-proprietor, or research-purpose use and requires the corporate service approval/contract process.
- **Required request inputs**: `Authorization`, `trx_id`, `user_key_type`, `user_key_id`, `bio_type`, `auth_co_code`, `cmpb_auth_tech_code`, `no_iden_cfnm_key`, `key_ver`, `enc_data1`, `enc_data2`, `enc_data3`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://bioapi.kftc.or.kr/v1/bio/searchCombiAuth` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/searchCombiAuth` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html><br>`POST https://bioapi.kftc.or.kr/v1/bio/procCombiAuth` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: bioapi.kftc.or.kr<br>`POST https://testbioapi.kftc.or.kr:8443/v1/bio/procCombiAuth` -> `404` <!DOCTYPE html> <html> <head> <meta charset="UTF-8"> <title>오류</title> </head> <body> <h1>비정상적인 페이지 접근입니다.</h1> </body> </html>
- **Root-cause classification**: policy/contract gate. Linked authentication remains outside current-account Live eligibility regardless of route availability.
- **UMMAYA adapter mapping**: Corporate-contract handoff/mock only. Future approved use maps to `check`/`find` scenario shapes, not current Live execution.
- **Next debugging action**: Resume only if KFTC grants corporate-service approval and supplies contract-scoped test credentials, routing, and biometric handling requirements.

### 38. `/dev/openapi/open-giro/index` — 오픈지로 / 부과서비스

- **Function**: 오픈지로 부과서비스입니다. 고지내역 등록, 고지내역 취소, 납부여부 조회를 포함합니다.
- **Official endpoint evidence**: `POST https://api.giro.or.kr/v1/bills/giro`; `POST https://api.giro.or.kr/v1/bills/giro/cancel`; `GET https://api.giro.or.kr/v1/bills/giro/payment-yn`
- **Required request inputs**: `Authorization`, `ptco_code`, `cls_code`, `giro_no`, `cust_inqr_no`, `dudt_in_amt`, `dudt_aft_amt`, `data_form_type`, `dudt`, `noti_dl_dt`, `epay_no`, `noti_issu_type` 외 4개
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://api.giro.or.kr/v1/bills/giro` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}<br>`POST https://api.giro.or.kr/v1/bills/giro/cancel` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}<br>`GET https://api.giro.or.kr/v1/bills/giro/payment-yn` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}
- **Root-cause classification**: endpoint는 auth layer까지 도달한다. 실패 경계는 OpenGiro token 발급/등록/callback readiness다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; 현 mock 유지 후 token/callback/tool 승인 시 Live
- **Next debugging action**: Implement/verify callback and token acquisition outside repo secrets, then compare live receipt shape to existing mock fixture.

### 39. `/dev/openapi/open-giro/pay-service` — 오픈지로 / 납부서비스

- **Function**: 오픈지로 납부서비스입니다. 지로 조회납부 URL, 입력납부 URL, 링크납부 URL 발급과 납부결과 조회를 포함합니다.
- **Official endpoint evidence**: `POST https://api.giro.or.kr/v1/payments/giro-inqr-pay-url`; `POST https://api.giro.or.kr/v1/payments/giro-inpt-pay-url`; `POST https://api.giro.or.kr/v1/payments/link-pay-url`; `GET https://api.giro.or.kr/v1/payments`
- **Required request inputs**: `Authorization`, `ptco_code`, `org_tran_id`, `cls_code`, `giro_no`, `epay_no`, `pay_yymm`, `noti_issu_type`, `etc_type_code`, `pyr_name`, `pyr_brdd`, `bank_code` 외 2개
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://api.giro.or.kr/v1/payments/giro-inqr-pay-url` -> `403` {"rsp_code":"O0201","rsp_message":"허용되지 않은 API 호출 (미존재 혹은 비활성 API)"}<br>`POST https://api.giro.or.kr/v1/payments/giro-inpt-pay-url` -> `403` {"rsp_code":"O0201","rsp_message":"허용되지 않은 API 호출 (미존재 혹은 비활성 API)"}<br>`POST https://api.giro.or.kr/v1/payments/link-pay-url` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}<br>`GET https://api.giro.or.kr/v1/payments` -> `401` {"rsp_code":"O0101","rsp_message":"Access Token 거부(Cannot convert access token to JSON)"}
- **Root-cause classification**: 공식 샘플 body로 재시도해도 두 payment URL endpoint가 O0201을 반환했다. production endpoint activation/service permission 병목이다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; 현 mock 유지 후 token/callback/tool 승인 시 Live
- **Next debugging action**: Use KFTC 담당자/tool approval to activate or confirm production payment URL endpoints; compare with `testapi.giro.or.kr` auth-layer behavior before Live.

### 40. `/dev/openapi/p2p/loans-contract` — 온투업중앙기록관리 / 대출계약 기록

- **Function**: 연계대출계약 체결 후 온라인투자연계금융업자가 대출계약 정보를 중앙기록관리로 전송하는 기록 API입니다.
- **Official endpoint evidence**: `POST https://openapi.p2pcenter.or.kr/v{버전}/loans/contract`; `POST https://testapi.p2pcenter.or.kr/v{버전}/loans/contract`
- **Required request inputs**: `거래일시(밀리세컨드)`, `대출계약 정보`, `차입자 정보`, `대출상환 예정정보 목록`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.p2pcenter.or.kr/v{버전}/loans/contract` -> `SKIP_TEMPLATE` version placeholder<br>`POST https://testapi.p2pcenter.or.kr/v{버전}/loans/contract` -> `SKIP_TEMPLATE` version placeholder
- **Official email evidence**: KFTC P2P금융업무팀 reply, 2026-05-19 KST: API use is limited to registered 온투업자 and requires prior consultation/registration proof.
- **Root-cause classification**: policy/eligibility gate. Version discovery and test-host reachability are secondary because the current account is not a regulated 온투업자.
- **UMMAYA adapter mapping**: institutional handoff/mock only. This can be represented as a scenario where a regulated provider records a loan contract, but UMMAYA must not expose a Live caller for a citizen/student account.
- **Next debugging action**: No further curl retries until eligibility proof or a partner institution test credential exists.

### 41. `/dev/openapi/p2p/investments-contract` — 온투업중앙기록관리 / 투자계약 기록

- **Function**: P2P 투자계약 정보를 중앙기록관리로 전송하는 기록 API입니다.
- **Official endpoint evidence**: `POST https://openapi.p2pcenter.or.kr/v{버전}/investments/contract`; `POST https://testapi.p2pcenter.or.kr/v{버전}/investments/contract`
- **Required request inputs**: `거래일시(밀리세컨드)`, `P2P온투업자 상품관리번호`, `투자계약 정보`, `투자자 정보`, `원리금수취권 예정정보`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.p2pcenter.or.kr/v{버전}/investments/contract` -> `SKIP_TEMPLATE` version placeholder<br>`POST https://testapi.p2pcenter.or.kr/v{버전}/investments/contract` -> `SKIP_TEMPLATE` version placeholder
- **Official email evidence**: KFTC P2P금융업무팀 reply, 2026-05-19 KST: API use is limited to registered 온투업자 and requires prior consultation/registration proof.
- **Root-cause classification**: policy/eligibility gate. The route is not live-callable from the current project account.
- **UMMAYA adapter mapping**: institutional handoff/mock only. Model the expected record-submission shape but keep Live disabled.
- **Next debugging action**: No further curl retries until eligibility proof or a partner institution test credential exists.

### 42. `/dev/openapi/p2p/investments-transfer` — 온투업중앙기록관리 / 양도양수 기록

- **Function**: P2P 투자계약의 양도양수 거래 정보를 중앙기록관리로 전송하는 기록 API입니다.
- **Official endpoint evidence**: `POST https://openapi.p2pcenter.or.kr/v{버전}/investments/transfer`; `POST https://testapi.p2pcenter.or.kr/v{버전}/investments/transfer`
- **Required request inputs**: `거래일시(밀리세컨드)`, `양도양수거래 상품ID`, `(양도) 투자계약 정보`, `(양수) 투자계약 반복부`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.p2pcenter.or.kr/v{버전}/investments/transfer` -> `SKIP_TEMPLATE` version placeholder<br>`POST https://testapi.p2pcenter.or.kr/v{버전}/investments/transfer` -> `SKIP_TEMPLATE` version placeholder
- **Official email evidence**: KFTC P2P금융업무팀 reply, 2026-05-19 KST: API use is limited to registered 온투업자 and requires prior consultation/registration proof.
- **Root-cause classification**: policy/eligibility gate. The route is not live-callable from the current project account.
- **UMMAYA adapter mapping**: institutional handoff/mock only. Model the transfer-record scenario, but do not register a Live tool.
- **Next debugging action**: No further curl retries until eligibility proof or a partner institution test credential exists.

### 43. `/dev/openapi/datop/dataset` — 금융결제데이터개방 / 개방데이터셋

- **Function**: Datop 개방 데이터셋 목록/선택 섹션입니다. dataset별 schema와 URL을 별도로 확정해야 합니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `find` candidate. Normalize lookup results into list/detail/receipt envelopes. Current fit: find; dataset별 schema 필요
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 44. `/dev/openapi/map/config` — FIN MAP / 환경정보조회

- **Function**: FIN MAP 사용에 필요한 데이터 제공 기관 목록 등 환경정보를 조회하는 API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/env_lists`
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/env_lists` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 45. `/dev/openapi/map/all` — FIN MAP / ATM/지점통합정보조회

- **Function**: 좌표 범위와 필터를 기준으로 ATM과 지점 정보를 통합 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_atm_lists`
- **Required request inputs**: `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`, `brch_inqr_yn`, `atm_inqr_yn`, `mob_cash_card_psb_yn`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_atm_lists` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 46. `/dev/openapi/map/atm` — FIN MAP / ATM정보조회

- **Function**: 좌표 범위와 필터를 기준으로 ATM 목록을 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_lists`
- **Required request inputs**: `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`, `mob_cash_card_psb_yn`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_lists` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 47. `/dev/openapi/map/branch` — FIN MAP / 지점정보조회

- **Function**: 좌표 범위 기준으로 금융회사 지점 목록을 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_lists`
- **Required request inputs**: `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_lists` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 48. `/dev/openapi/map/adetail` — FIN MAP / ATM정보상세조회

- **Function**: 기관코드와 ATM 번호로 ATM 상세정보를 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_detail`
- **Required request inputs**: `Authorization`, `trns_org_code`, `atm_no`, `dup_atm_no`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_detail` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 49. `/dev/openapi/map/bdetail` — FIN MAP / 지점정보상세조회

- **Function**: 기관코드와 지점코드로 지점 상세정보를 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_detail`
- **Required request inputs**: `Authorization`, `trns_org_code`, `brch_code`, `dup_brch_code`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_detail` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 50. `/dev/openapi/map/fee` — FIN MAP / 수수료정보조회

- **Function**: 기관코드와 기관유형 기준 ATM 수수료 정보를 조회하는 FIN MAP API입니다.
- **Official endpoint evidence**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_fee`
- **Required request inputs**: `Authorization`, `trns_org_code`, `org_type_code`
- **Token/scope requirement**: `finmap`: FIN MAP location/config scope. Low PII but currently DNS-gated.
- **Direct probe result**: `POST https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_fee` -> `curl_exit_6` STDERR: curl: (6) Could not resolve host: openapi.finmap.or.kr
- **Root-cause classification**: hostname이 공개 DNS에서 resolve되지 않는다. DNS/VPN/allowlist 또는 KFTC tool approval이 먼저다.
- **UMMAYA adapter mapping**: `locate` candidate. Map UMMAYA coordinates/radius/filter into provider fields and normalize branch/ATM points. Current fit: locate/find Live 후보
- **Next debugging action**: Fix DNS/allowlist/VPN first. No Live adapter until hostname resolves and returns a provider auth/error envelope.

### 51. `/dev/openapi/loan/personLoanInfo` — 대출이동 / 개인신용대출 정보조회

- **Function**: 개인신용대출의 상환가능 여부와 중도상환수수료 등 대출상환 정보를 조회하는 API입니다.
- **Official endpoint evidence**: `POST https://openapi.payinfo.or.kr/loanswitch/v1.0/loan/repayment`; `POST https://testapi.payinfo.or.kr:8443/loanswitch/v1.0/loan/repayment`
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `보유기관 금융회사 코드`, `하위 보유기관 코드`, `대출식별번호`, `조회요청일자`
- **Token/scope requirement**: Bearer token required, but this public section does not expose a concrete scope string. Treat as service-specific token pending KFTC tool/document approval.
- **Direct probe result**: `POST https://openapi.payinfo.or.kr/loanswitch/v1.0/loan/repayment` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to openapi.payinfo.or.kr port 443 after 3003 ms: Timeout was reached<br>`POST https://testapi.payinfo.or.kr:8443/loanswitch/v1.0/loan/repayment` -> `curl_exit_28` STDERR: curl: (28) Failed to connect to testapi.payinfo.or.kr port 8443 after 3005 ms: Timeout was reached
- **Root-cause classification**: DNS는 되지만 TCP connect timeout이다. traceroute도 KFTC/상위망 근처에서 멈추므로 승인망/allowlist 병목으로 본다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Ask KFTC/PayInfo for approved test network or allowlist. TCP success is the next evidence gate.

### 52. `/dev/openapi/loan/residentialLoanInfo` — 대출이동 / 주택담보대출 정보조회

- **Function**: 주택담보대출 관련 정보를 조회하는 대출이동 API 섹션입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `보유기관 금융회사 코드`, `하위 보유기관 코드`, `대출식별번호`, `조회요청일자`
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 53. `/dev/openapi/loan/rentLoanInfo` — 대출이동 / 전세대출 정보조회

- **Function**: 전세대출 관련 정보를 조회하는 대출이동 API 섹션입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `보유기관 금융회사 코드`, `하위 보유기관 코드`, `대출식별번호`, `조회요청일자`
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 54. `/dev/openapi/loan/personOriginInfo` — 대출이동 / 개인사업자신용대출 기존대출 통합조회

- **Function**: 개인사업자신용대출 기존대출 통합조회 API 섹션입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `조회대상 금융회사 코드`, `하위 조회대상 기관코드`, `지정번호`, `데이터 건수`, `조회요청일자`
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 55. `/dev/openapi/loan/personRepaymentInfo` — 대출이동 / 개인사업자신용대출 상환정보 사전조회

- **Function**: 개인사업자신용대출 상환정보 사전조회 API 섹션입니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: `거래일시(밀리세컨드)`, `고객위임여부`, `고객위임일시`, `개인실명번호`, `사업자등록번호`, `보유기관 금융회사 코드`, `하위 보유기관 코드`, `대출식별번호`, `조회요청일자`
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `check` candidate. Normalize identity, delegation, account-name, or readiness state into a verification result. Current fit: find/check; 대출정보·이동 고위험 gate
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.

### 56. `/dev/openapi/bankpay/pg` — 뱅크페이 / 뱅크페이 PG

- **Function**: 뱅크페이 계좌이체PG API 섹션입니다. 가맹점 계약과 도구/문서 승인이 선행되어야 합니다.
- **Official endpoint evidence**: 공개 HTTP URL 없음
- **Required request inputs**: 공개 요청 명세 없음 또는 header-only/설명형 페이지
- **Token/scope requirement**: 토큰 요구사항을 공개 URL/요청표에서 확인 불가
- **Direct probe result**: 직접 호출 대상 없음
- **Root-cause classification**: 공개 오픈API 탭에 HTTP URL row가 없다. 문서/도구/자료실 승인, 별도 계약, 또는 dataset 선택이 선행되어야 한다.
- **UMMAYA adapter mapping**: `send` candidate. Permission gauntlet, idempotency key, irreversible-action confirmation, sanitized receipt, and status/rollback check are mandatory. Current fit: send; 가맹점계약 전 handoff/mock
- **Next debugging action**: Request document/tool/material approval or service contract. Do not invent endpoint URLs.
