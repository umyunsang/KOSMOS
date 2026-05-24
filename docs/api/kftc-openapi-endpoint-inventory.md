# KFTC OpenAPI Endpoint Inventory

This inventory answers one narrow question: what does the public KFTC developer
site expose at each `/dev/openapi/**` page, and how would each visible module
map into UMMAYA's primitive surface?

It is endpoint evidence, not a Live authorization claim. A row means the public
developer page exposed that page path and, where stated, an `HTTP URL` plus
method. It does not mean the current UMMAYA operator account can execute the
call. Document, tool, material, callback, token, and contract approval gates are
tracked separately.

For the deep per-section analysis, see
[`kftc-openapi-56-section-debug-report.md`](./kftc-openapi-56-section-debug-report.md).
That companion report expands the OpenAPI sidebar routes into
function, user-query coverage, request inputs, token/scope gate, direct probe
result, root-cause classification, UMMAYA primitive mapping, and next debugging
action.

## Collection Scope

Collected from the official KFTC developer-site navigation rooted at
`https://developers.kftc.or.kr/dev/openapi`. The 2026-05-19 refresh used the
logged-in developer portal state, the public `오픈API` header tab, the left
sidebar accordion, scroll-verified Chrome/Codex browser capture, and direct
sanitized `curl` probes. Approval-gated `문서`, `도구`, and `자료실` pages are not
used as source material here.

| Scope item | Result |
|---|---|
| Left-sidebar `button.title` rows | 57 rows |
| Unique routed `/dev/openapi/**` pages | 49 pages |
| HTML fetch failures | 0 paths |
| Pages with request-message specs | 42 pages |
| Pages with at least one visible `HTTP URL` row | 40 pages |
| Pages without a public URL table or with overview-only text | 9 pages |
| Concrete non-template endpoint URLs replayed on 2026-05-19 | 64 endpoint calls |

The previous "56 paths" count mixed sidebar rows, category aliases, and routed
pages. The scroll-verified pass makes the distinction explicit: 57 sidebar title
rows and 49 unique pages with actual `vueMovePage(...)` routes. Category aliases
and overview pages are useful for navigation checks but are not separate adapter
modules unless they expose their own request table.

## How To Read This

| Column | Meaning |
|---|---|
| Page | Developer-site path under `https://developers.kftc.or.kr` |
| Module | Page title or operation title shown by KFTC |
| Method | HTTP method stated by the public page |
| Endpoint evidence | Public URL evidence shown by the page; `no public URL row` means no endpoint URL was visible in the public HTML inspected |
| UMMAYA fit | Initial primitive and adapter treatment; final implementation still requires Spec Kit and direct sanitized curl evidence |

## 2026-05-19 Probe Findings

These are setup and endpoint-readiness findings, not successful money movement
or citizen account transactions. The first replay used missing/invalid redacted
bearers. A later credentialed test-host pass used the operator-provided
non-production Client ID/Secret to verify OpenBanking token behavior; returned
bearers and the Client Secret are not stored in this repository.

| Host family | Direct-call result | Adapter implication |
|---|---|---|
| `openapi.openbanking.or.kr` | Reachable. Invalid-token probes consistently returned HTTP 200 with `rsp_code=O0002` / `Access Token 거부`. | Endpoint and JSON error envelope are reachable; the next blocker is real OAuth/delegated token issuance plus test user/account data. |
| OpenBanking OAuth token endpoints | `POST https://openapi.openbanking.or.kr/oauth/2.0/token` and `POST https://testapi.openbanking.or.kr/oauth/2.0/token` are reachable. The test host issued a bearer for client-credentials `scope=oob`, returned `client_use_code=M202601315`, and rejected `inquiry`/`transfer`/`cardinfo`/`fintechinfo`/`insuinfo`/`finmap` through that same grant with `O0001`; `sa` returned `O0011`. | `oob` can be debugged now for 2-legged check APIs. `inquiry` and user-bound asset reads require the OAuth/account-registration flow and `fintech_use_num`; do not try to force them through client credentials. |
| `api.giro.or.kr` | Reachable. Bill endpoints returned HTTP 401 `O0101`; payment URL endpoints split between HTTP 401 `O0101` and HTTP 403 `O0201` (`미존재 혹은 비활성 API`). | Current mock OpenGiro adapters remain correct; Live conversion needs token acceptance and API activation/tool approval per endpoint, not only Client ID/Secret. |
| `testapi.giro.or.kr` | Development-host candidate reached the OpenGiro auth layer for sample-shaped payment URL/result requests and returned `O0101` with an invalid bearer. | Useful debugging signal, but not yet an official test path because the public OpenGiro page body does not publish this host; confirm via portal tool access or 담당자 before implementing Live. |
| `openapi.finmap.or.kr` | DNS resolution failed from the current network. | FIN MAP still has a clean `locate`/`find` schema, but Live work is blocked before HTTP; verify DNS/VPN/network allowlist or KFTC tool access before coding a Live adapter. |
| `bioapi.kftc.or.kr` | DNS resolution failed; `testbioapi.kftc.or.kr:8443` reached a server but returned 404 for empty invalid-token probes. KFTC 인증인프라업무팀 additionally replied on 2026-05-19 KST that Bio authentication is provided to corporate customers and is available only after application, service review, approval, and contract completion; individual customers, sole proprietors, and research-purpose use are not supported. | Treat Bio as a corporate-contract handoff/mock surface under the current project account. Do not promote any Bio endpoint to Live or request test execution until a corporate customer contract/approval credential exists. |
| `accountapi.payinfo.or.kr` | DNS resolved in earlier checks, but direct HTTPS probes timed out at connect. | Account closure/balance-transfer cannot be promoted to Live from current network evidence; keep as gated `check`/`send` design only. |
| `openapi.payinfo.or.kr` and `testapi.payinfo.or.kr:8443` | HTTPS probes timed out at connect. | Loan-switching remains high-value but blocked on network/testbed access and delegated identity evidence. |
| `openapi.p2pcenter.or.kr` / `testapi.p2pcenter.or.kr` | Public URL rows contain `{버전}` placeholders; probe skipped rather than guessing a version. KFTC P2P금융업무팀 additionally replied on 2026-05-19 KST that the central-record APIs are for 금융당국-registered 온투업자, and developer-site use requires prior team consultation plus proof such as 온투업자 등록신청 증빙. | Treat as institutional handoff/mock only. No Live adapter, test account request, or testbed execution is available for this project unless regulated-provider eligibility is proved. |

## 2026-05-19 Replay Buckets

The initial execution pass used the OpenAPI tab as source material, then called
the concrete endpoint URLs directly with no bearer, an invalid redacted bearer,
or official sample-shaped dummy JSON where the page exposed payment fields. The
follow-up OpenBanking test-host pass used the operator-provided non-production
Client ID/Secret and stored only sanitized outcomes.

| Bucket | Count | Services | Current blocker |
|---|---:|---|---|
| Auth envelope reached | 26 | OpenBanking, OpenGiro bill/link/result, AccountInfo aggregation | Normal delegated/service token is required before business validation can continue. |
| DNS failure | 18 | FIN MAP, Bio production | DNS/VPN/allowlist or tool access is required before HTTP debugging can continue. For Bio, the later KFTC reply supersedes this as a corporate-contract gate. |
| HTTP 404 route/gate | 11 | Bio test host | The test host answers, but KFTC's later reply makes contract/eligibility the next gate before route, token, or mTLS debugging. |
| TCP timeout | 7 | PayInfo account/loan, P2P test | Network/testbed allowlist is required before adapter-code debugging is meaningful. |
| Inactive/not allowed | 2 | OpenGiro production payment URL endpoints | Endpoint activation/service permission must be resolved separately from token issuance. |

P2P production was additionally probed outside the concrete replay because the
official URL rows still contain `{버전}`. The production base returns HTTP 403,
and an unofficial `/v1/loans/contract` hypothesis returns `B0102` / `잘못된 접근`.
This proves the production host exists, but it does not authorize hardcoding
`v1`. The stronger blocker is now policy, not only version discovery: KFTC
P2P금융업무팀 replied that use is limited to 금융당국-registered 온투업자 and
requires prior consultation with registration proof. For UMMAYA this means the
P2P central-record routes are not live-callable under the current student
portfolio account.

## Scroll-Verified Sidebar Route Snapshot

The following list is generated from the 2026-05-19 Chrome/Codex pass that used
`tab.cua.scroll({ x: 500, y: 500, scrollY: 900, scrollX: 0 })` on every routed
page before extraction. It is the canonical OpenAPI-sidebar inventory for the
current investigation.

| Service | Page | Method | Scope hint | Visible URL count |
|---|---|---|---|---:|
| 오픈뱅킹 | OAuth 인증 | - | - | 0 |
| 오픈뱅킹 | 잔액조회 | `GET` | `inquiry` | 1 |
| 오픈뱅킹 | 거래내역조회 | `GET` | `inquiry` | 1 |
| 오픈뱅킹 | 계좌실명조회 | `POST` | `oob` | 1 |
| 오픈뱅킹 | 입금이체 | `POST` | - | 2 |
| 오픈뱅킹 | 출금이체 | `POST` | - | 1 |
| 오픈뱅킹 | 수취조회 | `POST` | `oob` | 1 |
| 오픈뱅킹 | 송금인정보조회 | `POST` | `oob` | 1 |
| 오픈뱅킹 | 관리API | - | - | 0 |
| 오픈뱅킹 | 카드목록조회 | `GET` | `cardinfo, sa` | 1 |
| 오픈뱅킹 | 카드기본정보조회 | `GET` | - | 1 |
| 오픈뱅킹 | 카드청구기본정보조회 | `GET` | - | 1 |
| 오픈뱅킹 | 카드청구상세정보조회 | `GET` | - | 1 |
| 오픈뱅킹 | 선불목록조회 | `GET` | - | 1 |
| 오픈뱅킹 | 선불연계정보조회 | `GET` | - | 1 |
| 오픈뱅킹 | 선불잔액조회 | `GET` | - | 1 |
| 오픈뱅킹 | 선불거래내역조회 | `GET` | - | 1 |
| 오픈뱅킹 | 보험목록조회 | `GET` | - | 1 |
| 오픈뱅킹 | 보험납입정보조회 | `POST` | - | 1 |
| 오픈뱅킹 | 대출리스목록조회 | `GET` | - | 1 |
| 오픈뱅킹 | 대출리스기본정보조회 | `POST` | - | 1 |
| 어카운트인포 | 계좌통합조회 | `POST` | - | 1 |
| 어카운트인포 | 계좌해지·잔고이전 | `POST` | - | 5 |
| 금융인증 | 금융인증 | - | - | 0 |
| 바이오인증 | 등록 | `POST` | - | 4 |
| 바이오인증 | 인증 | `POST` | - | 6 |
| 바이오인증 | 관리 | `POST` | - | 8 |
| 바이오인증 | 연계인증 | `POST` | - | 4 |
| 오픈지로 | 부과서비스 | `POST/GET` | - | 3 |
| 오픈지로 | 납부서비스 | `POST/GET` | - | 6 |
| 온투업중앙기록관리 | 대출계약 기록 | `POST` | - | 2 |
| 온투업중앙기록관리 | 투자계약 기록 | `POST` | - | 2 |
| 온투업중앙기록관리 | 양도양수 기록 | `POST` | - | 2 |
| 금융결제데이터개방 | 금융결제데이터개방 | - | - | 1 |
| 금융결제데이터개방 | 개방데이터셋 | - | - | 1 |
| FIN MAP | 환경정보조회 | `POST` | `finmap` | 1 |
| FIN MAP | ATM/지점통합정보조회 | `POST` | `finmap` | 1 |
| FIN MAP | ATM정보조회 | `POST` | `finmap` | 1 |
| FIN MAP | 지점정보조회 | `POST` | `finmap` | 1 |
| FIN MAP | ATM상세정보조회 | `POST` | `finmap` | 1 |
| FIN MAP | 지점정보상세조회 | `POST` | `finmap` | 1 |
| FIN MAP | 수수료정보조회 | `POST` | `finmap` | 1 |
| 대출이동 | 개인신용대출 정보조회 | `POST` | - | 2 |
| 대출이동 | 주택담보대출 정보조회 | - | - | 0 |
| 대출이동 | 전세대출 정보조회 | - | - | 0 |
| 대출이동 | 개인사업자신용대출 기존대출 통합조회 | - | - | 0 |
| 대출이동 | 개인사업자신용대출 상환정보 사전조회 | - | - | 0 |
| 뱅크페이 | 뱅크페이 | - | - | 0 |
| 뱅크페이 | 뱅크페이 PG | - | - | 0 |

## Earlier 56-Path Current State

This table is retained for continuity with the first pass. The scroll-verified
sidebar snapshot above is the current canonical route inventory.

| # | Path | 기능 | URL/호출 | 요청 핵심 | 실제 프로브 | UMMAYA 적용 |
|---:|---|---|---|---|---|---|
| 1 | `/dev/openapi` | 오픈API 루트 / 오픈API 안내 | no public URL row | - | - | catalog only |
| 2 | `/dev/openapi/open-banking` | 오픈뱅킹 / 안내 | no public URL row | - | - | category alias; no standalone adapter |
| 3 | `/dev/openapi/account-info` | 어카운트인포 / 안내 alias | `POST openapi.openbanking.or.kr` | `inquiry_bank_type`, `trace_no`, `inquiry_record_cnt` | HTTP 200 auth reject | `find` account aggregation |
| 4 | `/dev/openapi/finance-certification` | 금융인증 | no public URL row | - | - | `check` handoff/mock until approval |
| 5 | `/dev/openapi/bio/register` | 바이오 등록 | `POST bioapi.kftc.or.kr`, `POST testbioapi.kftc.or.kr:8443` (4 rows) | `Authorization`, `trx_id`, `auth_co_code`, `cmpb_auth_tech_code`, `svc_code`, ... | DNS fail + test-host 404; official corporate-contract gate | corporate-contract handoff/mock only |
| 6 | `/dev/openapi/open-giro` | 오픈지로 안내 alias | `GET/POST api.giro.or.kr` (3 rows) | `Authorization`, `ptco_code`, `cls_code`, `giro_no`, `cust_inqr_no`, ... | 401 token reject | existing mock `send`; Live gated |
| 7 | `/dev/openapi/p2p` | 온투업중앙기록관리 안내 alias | `POST openapi.p2pcenter.or.kr`, `POST testapi.p2pcenter.or.kr` (2 rows) | 거래일시, 대출계약 정보, 차입자 정보, 상환 예정정보 | skipped: version placeholder | institutional `send`; version required |
| 8 | `/dev/openapi/datop` | 금융결제데이터개방 안내 | no public URL row | - | - | dataset-level `find` candidate |
| 9 | `/dev/openapi/map` | FIN MAP 안내 alias | `POST openapi.finmap.or.kr` | - | DNS fail | `locate`/`find`; network-gated |
| 10 | `/dev/openapi/loan` | 대출이동 안내 alias | `POST openapi.payinfo.or.kr`, `POST testapi.payinfo.or.kr:8443` | 거래일시, 위임여부, 위임일시, 개인실명번호, 기관코드, ... | connect timeout | high-risk `find`/`check` |
| 11 | `/dev/openapi/bankpay` | 뱅크페이 안내 | no public URL row | - | - | merchant-contract `send` handoff/mock |
| 12 | `/dev/openapi/open-banking/oauth` | OAuth 인증 | no public URL row | - | - | `check`/delegation foundation |
| 13 | `/dev/openapi/open-banking/balance` | 잔액조회 | `GET openapi.openbanking.or.kr` | page exposes no parsed request table | HTTP 200 auth reject | delegated `find` |
| 14 | `/dev/openapi/open-banking/transaction` | 거래내역조회 | `GET openapi.openbanking.or.kr` | page exposes no parsed request table | HTTP 200 auth reject | delegated `find` |
| 15 | `/dev/openapi/open-banking/account` | 계좌실명조회 | `POST openapi.openbanking.or.kr` | page exposes no parsed request table | HTTP 200 auth reject | `check` account-name verification |
| 16 | `/dev/openapi/open-banking/deposit` | 입금이체 | `POST openapi.openbanking.or.kr` (2 rows) | `cntr_account_type`, `cntr_account_num`, `wd_pass_phrase`, `wd_print_content`, `name_check_option`, ... | HTTP 200 auth reject | protected `send` |
| 17 | `/dev/openapi/open-banking/withdraw` | 출금이체 | `POST openapi.openbanking.or.kr` | `bank_tran_id`, `cntr_account_type`, `cntr_account_num`, `dps_print_content`, `fintech_use_num`, ... | HTTP 200 auth reject | highest-risk `send` |
| 18 | `/dev/openapi/open-banking/receipt` | 수취조회 | `POST openapi.openbanking.or.kr` | page exposes no parsed request table | HTTP 200 auth reject | `check`/`find` |
| 19 | `/dev/openapi/open-banking/remitter` | 송금인정보조회 | `POST openapi.openbanking.or.kr` | page exposes no parsed request table | HTTP 200 auth reject | `check`/`find` provenance |
| 20 | `/dev/openapi/open-banking/mgrapi` | 관리API | no public URL row | - | - | gated management family |
| 21 | `/dev/openapi/open-banking/cards` | 카드목록조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `befor_inquiry_trace_info` | HTTP 200 auth reject | delegated `find` |
| 22 | `/dev/openapi/open-banking/issue_info` | 카드기본정보조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `card_id` | HTTP 200 auth reject | delegated `find`/`check` |
| 23 | `/dev/openapi/open-banking/bills` | 카드청구기본정보조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `from_month`, ... | HTTP 200 auth reject | delegated `find` |
| 24 | `/dev/openapi/open-banking/bills_detail` | 카드청구상세정보조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `member_bank_code`, `charge_month`, ... | HTTP 200 auth reject | delegated `find` |
| 25 | `/dev/openapi/open-banking/pays-list` | 선불목록조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std` | HTTP 200 auth reject | delegated `find` |
| 26 | `/dev/openapi/open-banking/pays-reload` | 선불연계정보조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id` | HTTP 200 auth reject | delegated `find` |
| 27 | `/dev/openapi/open-banking/pays-balances` | 선불잔액조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id` | HTTP 200 auth reject | delegated `find` |
| 28 | `/dev/openapi/open-banking/pays-transactions` | 선불거래내역조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std`, `faceofbill_id`, `from_date`, ... | HTTP 200 auth reject | delegated `find` |
| 29 | `/dev/openapi/open-banking/insurances-list` | 보험목록조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std` | HTTP 200 auth reject | delegated `find` |
| 30 | `/dev/openapi/open-banking/insurances-payment` | 보험납입정보조회 | `POST openapi.openbanking.or.kr` | `bank_tran_id`, `bank_code_std`, `user_seq_no`, `insu_num` | HTTP 200 auth reject | `check`/`find` |
| 31 | `/dev/openapi/open-banking/loans-list` | 대출리스목록조회 | `GET openapi.openbanking.or.kr` | `bank_tran_id`, `user_seq_no`, `bank_code_std` | HTTP 200 auth reject | delegated `find` |
| 32 | `/dev/openapi/open-banking/loans-basic` | 대출리스기본정보조회 | `POST openapi.openbanking.or.kr` | `bank_tran_id`, `bank_code_std`, `account_num`, `user_seq_no`, `from_date`, ... | HTTP 200 auth reject | `check`/`find` |
| 33 | `/dev/openapi/account-info/inquiry` | 계좌통합조회 | `POST openapi.openbanking.or.kr` | `inquiry_bank_type`, `trace_no`, `inquiry_record_cnt` | HTTP 200 auth reject | delegated `find` |
| 34 | `/dev/openapi/account-info/account` | 계좌해지·잔고이전 | `POST accountapi.payinfo.or.kr` (5 rows) | `api_trx_num`, `api_trx_dtm`, `api_org_code`, `delegation_yn`, `delegation_dtm`, ... | connect timeout | `check`/`find`/protected `send` |
| 35 | `/dev/openapi/bio/auth` | 바이오 인증 | `POST bioapi.kftc.or.kr`, `POST testbioapi.kftc.or.kr:8443` (6 rows) | `Authorization`, `trx_id`, `auth_co_code`, `cmpb_auth_tech_code`, `key_ver`, ... | DNS fail + test-host 404; official corporate-contract gate | corporate-contract handoff/mock only |
| 36 | `/dev/openapi/bio/manage` | 바이오 관리 | `POST bioapi.kftc.or.kr`, `POST testbioapi.kftc.or.kr:8443` (8 rows) | `Authorization`, `trx_id`, `svc_code`, `user_key_id`, `bio_type`, ... | DNS fail + test-host 404; official corporate-contract gate | corporate-contract handoff/mock only |
| 37 | `/dev/openapi/bio/linkAuth` | 연계인증 | `POST bioapi.kftc.or.kr`, `POST testbioapi.kftc.or.kr:8443` (4 rows) | `Authorization`, `trx_id`, `user_key_type`, `user_key_id`, `bio_type`, ... | DNS fail + test-host 404; official corporate-contract gate | corporate-contract handoff/mock only |
| 38 | `/dev/openapi/open-giro/index` | 부과서비스 | `GET/POST api.giro.or.kr` (3 rows) | `Authorization`, `ptco_code`, `cls_code`, `giro_no`, `cust_inqr_no`, ... | 401 token reject | existing mock `send`; Live gated |
| 39 | `/dev/openapi/open-giro/pay-service` | 납부서비스 | `GET/POST api.giro.or.kr` (4 rows) | `Authorization`, `ptco_code`, `org_tran_id`, `cls_code`, `giro_no`, ... | 403 inactive/not allowed + 401 token reject | existing mock `send`; endpoint activation gated |
| 40 | `/dev/openapi/p2p/loans-contract` | 대출계약 기록 | `POST openapi.p2pcenter.or.kr`, `POST testapi.p2pcenter.or.kr` | 거래일시, 대출계약 정보, 차입자 정보, 상환 예정정보 | skipped: version placeholder | institutional `send` |
| 41 | `/dev/openapi/p2p/investments-contract` | 투자계약 기록 | `POST openapi.p2pcenter.or.kr`, `POST testapi.p2pcenter.or.kr` | 거래일시, 상품관리번호, 투자계약 정보, 투자자 정보, 원리금수취권 예정정보 | skipped: version placeholder | institutional `send` |
| 42 | `/dev/openapi/p2p/investments-transfer` | 양도양수 기록 | `POST openapi.p2pcenter.or.kr`, `POST testapi.p2pcenter.or.kr` | 거래일시, 양도양수거래 상품ID, 양도 투자계약 정보, 양수 투자계약 반복부 | skipped: version placeholder | institutional `send` |
| 43 | `/dev/openapi/datop/dataset` | 개방데이터셋 | no public URL row | - | - | dataset-level `find` only |
| 44 | `/dev/openapi/map/config` | 환경정보조회 | `POST openapi.finmap.or.kr` | page exposes header-only request table | DNS fail | `find` config; network-gated |
| 45 | `/dev/openapi/map/all` | ATM/지점통합정보조회 | `POST openapi.finmap.or.kr` | `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`, ... | DNS fail | `locate` |
| 46 | `/dev/openapi/map/atm` | ATM정보조회 | `POST openapi.finmap.or.kr` | `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude`, ... | DNS fail | `locate` |
| 47 | `/dev/openapi/map/branch` | 지점정보조회 | `POST openapi.finmap.or.kr` | `Authorization`, `start_latitude`, `start_longitude`, `end_latitude`, `end_longitude` | DNS fail | `locate` |
| 48 | `/dev/openapi/map/adetail` | ATM정보상세조회 | `POST openapi.finmap.or.kr` | `Authorization`, `trns_org_code`, `atm_no`, `dup_atm_no` | DNS fail | `find`/`locate` detail |
| 49 | `/dev/openapi/map/bdetail` | 지점정보상세조회 | `POST openapi.finmap.or.kr` | `Authorization`, `trns_org_code`, `brch_code`, `dup_brch_code` | DNS fail | `find`/`locate` detail |
| 50 | `/dev/openapi/map/fee` | 수수료정보조회 | `POST openapi.finmap.or.kr` | `Authorization`, `trns_org_code`, `org_type_code` | DNS fail | `find` fee lookup |
| 51 | `/dev/openapi/loan/personLoanInfo` | 개인신용대출 정보조회 | `POST openapi.payinfo.or.kr`, `POST testapi.payinfo.or.kr:8443` | 거래일시, 위임여부, 위임일시, 개인실명번호, 기관코드, ... | connect timeout | high-risk `find`/`check` |
| 52 | `/dev/openapi/loan/residentialLoanInfo` | 주택담보대출 정보조회 | no public URL row | 거래일시, 위임여부, 위임일시, 개인실명번호, 기관코드, ... | - | gated `find`/`check` |
| 53 | `/dev/openapi/loan/rentLoanInfo` | 전세대출 정보조회 | no public URL row | 거래일시, 위임여부, 위임일시, 개인실명번호, 기관코드, ... | - | gated `find`/`check` |
| 54 | `/dev/openapi/loan/personOriginInfo` | 개인사업자 기존대출 통합조회 | no public URL row | 거래일시, 위임여부, 위임일시, 개인실명번호, 조회대상 기관코드, ... | - | gated `find`/`check` |
| 55 | `/dev/openapi/loan/personRepaymentInfo` | 개인사업자 상환정보 사전조회 | no public URL row | 거래일시, 위임여부, 위임일시, 개인실명번호, 사업자등록번호, ... | - | gated `find`/`check` |
| 56 | `/dev/openapi/bankpay/pg` | 뱅크페이 PG | no public URL row | - | - | merchant-contract `send` handoff/mock |

## Coverage Summary

| Service | Canonical pages checked | Public endpoint rows | UMMAYA treatment |
|---|---:|---:|---|
| 오픈뱅킹 | 21 | 20 | `find`/`check` for delegated reads; `send` for transfers only after OAuth, consent, idempotency, and tool access are proven |
| 어카운트인포 | 2 | 6 | `find` for aggregation; `send` for account closure and balance transfer |
| 금융인증 | 1 | 0 | `check` handoff/mock until separate documentation is granted |
| 바이오인증 | 4 | 11 | Corporate-contract handoff/mock only under the current project account; KFTC says legal/corporate review, approval, and contract completion are required before use |
| 오픈지로 | 2 | 7 | Existing fixture-backed `send`; Live remains blocked by callback/token/tool readiness plus per-endpoint activation (`O0201`) |
| 온투업중앙기록관리 | 3 | 3 | Institutional `send`; contract and eligibility gates first |
| 금융결제데이터개방 | 1 | 0 | `find` candidate; dataset-specific schema discovery required |
| FIN MAP | 7 | 7 | Strong `locate`/`find` schema candidate, but Live is DNS/network-gated before HTTP |
| 대출이동 | 5 | 1 | High-risk delegated `find`/`send`; four pages expose request/response tables but no public URL row |
| 뱅크페이 | 1 | 0 | Merchant-contract `send` handoff/mock until contract and tool approval |

## OpenBanking

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/open-banking/oauth` | OAuth 인증 | varies | no public URL row; page describes OAuth 2.0 authorization-code flow, user consent, account registration, token delegation, and fintech-use-number handling | `check`/delegation foundation, not a standalone business adapter |
| `/dev/openapi/open-banking/balance` | 잔액조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/account/balance/fin_num` | `find` after delegated token and `fintech_use_num` proof |
| `/dev/openapi/open-banking/transaction` | 거래내역조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/account/transaction_list/fin_num` | `find`; account-history PII gate |
| `/dev/openapi/open-banking/account` | 계좌실명조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/inquiry/real_name` | `check`; identity/account-name verification |
| `/dev/openapi/open-banking/deposit` | 입금이체 | `POST` | `https://openapi.openbanking.or.kr/v2.0/transfer/deposit/fin_num`; `https://openapi.openbanking.or.kr/v2.0/transfer/deposit/acnt_num` | `send`; irreversible transfer surface, defer Live until confirmation/idempotency evidence |
| `/dev/openapi/open-banking/withdraw` | 출금이체 | `POST` | `https://openapi.openbanking.or.kr/v2.0/transfer/withdraw/fin_num` | `send`; highest-risk OpenBanking action |
| `/dev/openapi/open-banking/receipt` | 수취조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/inquiry/receive` | `check` before transfer or receipt validation |
| `/dev/openapi/open-banking/remitter` | 송금인정보조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/inquiry/remit_list` | `check`/`find`; payment provenance |
| `/dev/openapi/open-banking/mgrapi` | 관리API | varies | no public URL row; page describes participant-bank status query, user-info query, account cancellation, and fee query, with detailed specs in gated materials | Gated management family; no adapter until document/tool access |
| `/dev/openapi/open-banking/cards` | 카드목록조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/cards` | `find`; delegated financial asset list |
| `/dev/openapi/open-banking/issue_info` | 카드기본정보조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/cards/issue_info` | `find`/`check`; card metadata |
| `/dev/openapi/open-banking/bills` | 카드청구기본정보조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/cards/bills` | `find`; card-bill summary |
| `/dev/openapi/open-banking/bills_detail` | 카드청구상세정보조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/cards/bills/detail` | `find`; card-bill detail |
| `/dev/openapi/open-banking/pays-list` | 선불목록조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/pays` | `find`; prepaid accounts |
| `/dev/openapi/open-banking/pays-reload` | 선불연계정보조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/pays/reload` | `find`; prepaid linkage |
| `/dev/openapi/open-banking/pays-balances` | 선불잔액조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/pays/balances` | `find`; prepaid balances |
| `/dev/openapi/open-banking/pays-transactions` | 선불거래내역조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/pays/transactions` | `find`; prepaid transaction history |
| `/dev/openapi/open-banking/insurances-list` | 보험목록조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/insurances` | `find`; delegated insurance list |
| `/dev/openapi/open-banking/insurances-payment` | 보험납입정보조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/insurances/payment` | `find`/`check`; insurance payment information, not payment execution |
| `/dev/openapi/open-banking/loans-list` | 대출리스목록조회 | `GET` | `https://openapi.openbanking.or.kr/v2.0/loans` | `find`; delegated loan/lease list |
| `/dev/openapi/open-banking/loans-basic` | 대출리스기본정보조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/loans/basic` | `find`/`check`; loan/lease detail lookup |

## AccountInfo

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/account-info/inquiry` | 계좌통합조회 | `POST` | `https://openapi.openbanking.or.kr/v2.0/accountinfo/list` | `find`; delegated account aggregation |
| `/dev/openapi/account-info/account` | 계좌해지 가능여부 조회 | `POST` | `https://accountapi.payinfo.or.kr/termination/v1.0/eligibility` | `check` before closure |
| `/dev/openapi/account-info/account` | 잔고이전 수취계좌 확인 조회 | `POST` | `https://accountapi.payinfo.or.kr/termination/v1.0/recipient` | `check` before transfer |
| `/dev/openapi/account-info/account` | 계좌해지 예상금액 조회 | `POST` | `https://accountapi.payinfo.or.kr/termination/v1.0/status` | `check`/`find`; closure preview |
| `/dev/openapi/account-info/account` | 계좌해지 및 잔고이전 요청 | `POST` | `https://accountapi.payinfo.or.kr/termination/v1.0/transfer` | `send`; protected account-state change |
| `/dev/openapi/account-info/account` | 계좌해지 결과 조회 API | `POST` | `https://accountapi.payinfo.or.kr/termination/v1.0/result` | `find`; receipt/status after `send` |

## Bio Authentication

KFTC 인증인프라업무팀 confirmed on 2026-05-19 KST that Bio authentication is
provided to corporate customers and can be used only after application, service
review, use approval, and contract execution. Individual customers, sole
proprietors, and research-purpose use are not supported. The endpoint rows below
remain useful for schema and scenario fidelity, but under the current UMMAYA
project account they are not Live-callable and no test-account/testbed execution
should be attempted.

| Page | Module | Method | Production endpoint | Test endpoint | UMMAYA fit |
|---|---|---|---|---|---|
| `/dev/openapi/bio/register` | 위탁등록 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/procDlgRegi` | `https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgRegi` | corporate-contract handoff/mock; protected `send` shape only |
| `/dev/openapi/bio/register` | 자사등록 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/procRegi` | `https://testbioapi.kftc.or.kr:8443/v1/bio/procRegi` | corporate-contract handoff/mock; protected `send` shape only |
| `/dev/openapi/bio/auth` | 위탁인증 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/procDlgAuth` | `https://testbioapi.kftc.or.kr:8443/v1/bio/procDlgAuth` | corporate-contract handoff/mock; `check` scenario only |
| `/dev/openapi/bio/auth` | 인증정보조회(자사) API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/searchAuthBio` | `https://testbioapi.kftc.or.kr:8443/v1/bio/searchAuthBio` | corporate-contract handoff/mock; `check`/`find` scenario only |
| `/dev/openapi/bio/auth` | 자사인증결과보고 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/reportAuthRlst` | `https://testbioapi.kftc.or.kr:8443/v1/bio/reportAuthRlst` | corporate-contract handoff/mock; protected `send` shape only |
| `/dev/openapi/bio/manage` | 바이오조회 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/searchBioInfo` | `https://testbioapi.kftc.or.kr:8443/v1/bio/searchBioInfo` | corporate-contract handoff/mock; `find`/`check` scenario only |
| `/dev/openapi/bio/manage` | 바이오삭제 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/revokeBioInfo` | `https://testbioapi.kftc.or.kr:8443/v1/bio/revokeBioInfo` | corporate-contract handoff/mock; protected `send` revocation shape only |
| `/dev/openapi/bio/manage` | 블랙리스트 해지 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/reactiveBio` | `https://testbioapi.kftc.or.kr:8443/v1/bio/reactiveBio` | corporate-contract handoff/mock; protected `send` status-change shape only |
| `/dev/openapi/bio/manage` | 공개키 조회 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/searchPubKeyInfo` | `https://testbioapi.kftc.or.kr:8443/v1/bio/searchPubKeyInfo` | corporate-contract handoff/mock; `find` scenario only |
| `/dev/openapi/bio/linkAuth` | 연계바이오조회 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/searchCombiAuth` | `https://testbioapi.kftc.or.kr:8443/v1/bio/searchCombiAuth` | corporate-contract handoff/mock; `check`/`find` scenario only |
| `/dev/openapi/bio/linkAuth` | 연계인증 API | `POST` | `https://bioapi.kftc.or.kr/v1/bio/procCombiAuth` | `https://testbioapi.kftc.or.kr:8443/v1/bio/procCombiAuth` | corporate-contract handoff/mock; `check` scenario only |

## OpenGiro

OpenGiro is the current KFTC `send` implementation target. The public endpoint
pages are visible and `api.giro.or.kr` is reachable. Credentialed Live execution
remains blocked by callback reachability, token acceptance, portal tool access,
and per-endpoint activation: the 2026-05-19 invalid-token sweep reached the
auth layer for bill/link-payment/result endpoints (`O0101`), while
`giro-inqr-pay-url` and `giro-inpt-pay-url` returned `O0201` inactive/not
allowed.

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/open-giro/index` | 지로 고지내역 등록 | `POST` | `https://api.giro.or.kr/v1/bills/giro` | Existing fixture-backed `send` |
| `/dev/openapi/open-giro/index` | 지로 고지내역 취소 | `POST` | `https://api.giro.or.kr/v1/bills/giro/cancel` | Existing fixture-backed `send` |
| `/dev/openapi/open-giro/index` | 납부여부 조회 | `GET` | `https://api.giro.or.kr/v1/bills/giro/payment-yn` | `find`/receipt status after `send` |
| `/dev/openapi/open-giro/pay-service` | 지로 조회납부 URL 발급 | `POST` | `https://api.giro.or.kr/v1/payments/giro-inqr-pay-url` | Existing fixture-backed `send` |
| `/dev/openapi/open-giro/pay-service` | 지로 입력납부 URL 발급 | `POST` | `https://api.giro.or.kr/v1/payments/giro-inpt-pay-url` | Existing fixture-backed `send` |
| `/dev/openapi/open-giro/pay-service` | 간편납부 URL 발급 | `POST` | `https://api.giro.or.kr/v1/payments/link-pay-url` | Existing fixture-backed `send` |
| `/dev/openapi/open-giro/pay-service` | 납부결과 조회 | `GET` | `https://api.giro.or.kr/v1/payments` | `find`/receipt status after `send` |

## P2P Central Record Management

KFTC P2P금융업무팀 confirmed on 2026-05-19 KST that these APIs are used by
registered online investment-linked finance firms to record transaction
information with the central record-management institution. Developer-site API
use requires prior consultation and proof such as 온투업자 등록신청 증빙. Without
that regulated-provider status, API use is not permitted. UMMAYA should model
these routes as institutional handoff/mock scenarios, not as Live tools.

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/p2p/loans-contract` | 대출계약 기록 | `POST` | production `https://openapi.p2pcenter.or.kr/v{version}/loans/contract`; test `https://testapi.p2pcenter.or.kr/v{version}/loans/contract` | Institutional handoff/mock; no Live without registered 온투업자 eligibility |
| `/dev/openapi/p2p/investments-contract` | 투자계약 기록 | `POST` | production `https://openapi.p2pcenter.or.kr/v{version}/investments/contract`; test `https://testapi.p2pcenter.or.kr/v{version}/investments/contract` | Institutional handoff/mock; no Live without registered 온투업자 eligibility |
| `/dev/openapi/p2p/investments-transfer` | 양도양수 기록 | `POST` | production `https://openapi.p2pcenter.or.kr/v{version}/investments/transfer`; test `https://testapi.p2pcenter.or.kr/v{version}/investments/transfer` | Institutional handoff/mock; no Live without registered 온투업자 eligibility |

## FIN MAP

FIN MAP remains a clean schema candidate because the public pages expose simple
location-oriented endpoints and the citizen workflow is lookup/location, not
money movement. It is not ready for Live implementation yet: the 2026-05-19
direct probes failed DNS resolution for `openapi.finmap.or.kr`, so DNS/VPN,
network allowlist, or KFTC tool access must be debugged before coding a Live
adapter.

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/map/config` | 환경정보조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/env_lists` | `find`; configuration/environment table |
| `/dev/openapi/map/all` | ATM/지점통합정보조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_atm_lists` | `locate` |
| `/dev/openapi/map/atm` | ATM정보조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_lists` | `locate` |
| `/dev/openapi/map/branch` | 지점정보조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_lists` | `locate` |
| `/dev/openapi/map/adetail` | ATM정보상세조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_detail` | `find`/`locate` detail |
| `/dev/openapi/map/bdetail` | 지점정보상세조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/brch_detail` | `find`/`locate` detail |
| `/dev/openapi/map/fee` | 수수료정보조회 | `POST` | `https://openapi.finmap.or.kr/v1.0/kftc/inquiry/atm_fee` | `find`; fee lookup |

## Loan Switching

The loan-switching pages are high-value but not low-risk. Only the personal
credit-loan page exposed an `HTTP URL` row in the public HTML inspected. The
other four pages expose descriptions plus request/response message tables and
state `POST`, but no public URL row was visible.

| Page | Module | Method | Endpoint evidence | UMMAYA fit |
|---|---|---|---|---|
| `/dev/openapi/loan/personLoanInfo` | 개인신용대출 정보조회 | `POST` | production `https://openapi.payinfo.or.kr/loanswitch/v1.0/loan/repayment`; test `https://testapi.payinfo.or.kr:8443/loanswitch/v1.0/loan/repayment` | `find`/`check`; repayment information |
| `/dev/openapi/loan/residentialLoanInfo` | 주택담보대출 정보조회 | `POST` | no public URL row | Gated before adapter; do not infer endpoint |
| `/dev/openapi/loan/rentLoanInfo` | 전세대출 정보조회 | `POST` | no public URL row | Gated before adapter; do not infer endpoint |
| `/dev/openapi/loan/personOriginInfo` | 개인사업자신용대출 기존대출 통합조회 | `POST` | no public URL row | Gated before adapter; do not infer endpoint |
| `/dev/openapi/loan/personRepaymentInfo` | 개인사업자신용대출 상환정보 사전조회 | `POST` | no public URL row | Gated before adapter; do not infer endpoint |

## Other KFTC Pages

| Page | Module | Public endpoint evidence | UMMAYA treatment |
|---|---|---|---|
| `/dev/openapi/datop/dataset` | 개방데이터셋 | no public `HTTP URL` row on this developer page; it points readers to Datop dataset-specific access | `find` candidate after dataset-level schema and credential rules are selected |
| `/dev/openapi/finance-certification` | 금융인증 | no public URL table visible in the page inspected; service access notice marks related resources as separate/approval-gated | `check` handoff/mock until official docs are granted |
| `/dev/openapi/bankpay/pg` | 뱅크페이 | no public URL table visible; public page says merchant ID/Secret are issued after contract | `send` handoff/mock until merchant contract/tool access |

## Implementation Direction

1. Treat this file as the endpoint catalog; treat
   `kftc-openapi-portfolio.md` as the strategy and prioritization note.
2. Create new KFTC adapters from a single row or tightly coupled row group, not
   from a whole service category.
3. For any row marked `send`, require a `check`/permission precondition, a
   deterministic transaction id, a sanitized receipt, and idempotency/duplicate
   handling evidence before Live execution.
4. For any row without a public URL table, stop at mock/handoff until KFTC
   documents, tools, or 담당자 confirmation provide an exact endpoint.
5. Before moving a row to Live, run direct sanitized curl probes against the
   official development/test endpoint first. Do not call KFTC financial,
   identity, or payment endpoints from CI.
