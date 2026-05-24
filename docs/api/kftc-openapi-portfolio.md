# KFTC OpenAPI Portfolio Fit Analysis

This note maps the Korea Financial Telecommunications and Clearings Institute
(KFTC) OpenAPI portfolio to UMMAYA's active tool primitives. It is not an
implementation spec. Its purpose is to keep future KFTC adapter work aligned
with UMMAYA's thesis: wrap one official, LLM-callable public-infrastructure
module as one fail-closed tool, then expose it through `find`, `locate`, `send`,
or `check`.

## Reader Decision

KFTC is a high-fit provider for UMMAYA because it operates payment, account,
identity, loan-switching, location, data, and regulated record rails that sit
between citizens, financial institutions, and public-interest infrastructure.
The correct integration style is not one monolithic `kftc` adapter. UMMAYA
should split the portfolio into service-level adapter families, because each
family has different eligibility, consent, token scope, testbed access, and
irreversibility risk.

The 2026-05-19 direct-call pass changes the near-term order. OpenBanking
endpoints are reachable and return a stable KFTC JSON auth error when called
with a redacted invalid token. A credentialed test-host pass then proved that
the operator Client ID/Secret can issue a `scope=oob` bearer on
`testapi.openbanking.or.kr`, while `inquiry`, `transfer`, card, insurance,
fintech, and `finmap` scopes do not issue through the same client-credentials
grant. OpenGiro is reachable but split between token rejection and
inactive/not-allowed endpoint errors; FIN MAP is still a clean schema fit but
currently fails before HTTP at DNS resolution from this network; PayInfo
loan/account endpoints time out at TCP connect; Bio production DNS does not
resolve and the visible test host returns 404 for empty invalid-token probes,
but KFTC's 인증인프라업무팀 reply now supersedes those technical probes with a
corporate-customer approval and contract gate.
Therefore the next work should use `oob` to debug 2-legged account/receive
checks now, build the 3-legged OpenBanking authorization/account-registration
gate for `inquiry` reads, and keep DNS/allowlist-gated families documented but
not implemented as Live adapters. Bio specifically remains handoff/mock unless
a corporate contract and service approval credential exist.

## Official Sources

| Source | URL | Evidence used |
|---|---|---|
| KFTC developer starter workflow | `https://developers.kftc.or.kr/dev/starter/starter` | Service application, API Key, Callback URL, test data, token issuance, Swagger REST testing sequence |
| KFTC service access notice | `https://developers.kftc.or.kr/dev/support/notice/all/detail?id=44&boardCtgCd=all` | Which services require approval for document, tool, and material access; 담당자 emails |
| KFTC open API use procedure | `https://openapi.kftc.or.kr/intro/useProcedure` | Contract/application flow and note that some test execution rights are restricted |
| KFTC service overview pages | `https://openapi.kftc.or.kr/service/*` | Service purpose, eligible users, major API groups, contacts |
| KFTC developer OpenAPI pages | `https://developers.kftc.or.kr/dev/openapi/*` | Public endpoint pages and request/response tables where available |

## Access Model

KFTC separates "service is visible" from "testbed is usable". Treat these as
separate gates in every future feature:

1. **Portal membership**: user can log in to the developer site.
2. **Service application**: `MY PAGE > 내 서비스 관리` shows the service as
   `이용중`.
3. **API Key setup**: Client ID/Secret exists, Callback URL is registered, and
   the API Key is registered to the service.
4. **Test information**: the service exposes a test-info menu or equivalent
   fixture data path. The starter page says test data is service-specific.
5. **Token and Swagger tool access**: the `도구` menu, when approved, provides
   token issuance and Swagger-style REST API testing.
6. **Direct curl evidence**: before a Live adapter, run sanitized direct `curl`
   probes against the official test endpoint first. Use production endpoints
   only after the development/test path is understood.

The service access notice makes approval explicit. OpenGiro currently shows
`오픈API=모두공개`, `문서=승인필요`, `도구=-`, `자료실=승인필요`; OpenBanking
shows approval for document, tool, and materials; FIN MAP and BankPay show tool
approval; several services expose only material or separate-provider access.

## Service-Level Fit Matrix

| KFTC service | Public role | UMMAYA primitive fit | Recommended status now | Why |
|---|---|---|---|---|
| 오픈뱅킹 | Account, transaction, transfer, card, prepaid, insurance, loan/lease APIs | `find` for balances/history/assets, `send` for transfers, `check` for OAuth consent/token delegation | Mock-to-live until tool/doc approval and test account data are available | It is central citizen financial infrastructure but token scopes and irreversible transfer actions require strict separation |
| 어카운트인포 | Account aggregation and account closure/balance transfer | `find` for account aggregation, `send` for closure and transfer | Mock-to-live for closure flows; possible Live research for read-only aggregation after approval | Account closure is legally and financially sensitive, so adapter receipts and final confirmation gates must be stronger than ordinary lookup |
| 금융인증 | Financial certificate identity/authentication rail | `check` | Handoff/mock until separate materials are granted | The developer site marks materials as separate-provided; UMMAYA should not invent a certificate ceremony |
| 바이오인증 | Distributed biometric registration, authentication, management, linked authentication | `check` for authentication scenarios, protected `send` for registration/revocation scenarios | Corporate-contract handoff/mock only under the current project account | KFTC 인증인프라업무팀 replied on 2026-05-19 KST that Bio is a corporate-customer service requiring application, review, approval, and contract completion; individual, sole-proprietor, and research use is not supported |
| 오픈지로 | Bill creation/cancel/status and payment URL/result APIs | `send` for bill/payment URL creation, `find` for status/result reads | Existing fixture-backed `send`; Live blocked until callback/token/test path and endpoint activation are proven | OpenGiro directly matches UMMAYA's bill/payment workflows; 2026-05-19 probes show both token-gated endpoints (`O0101`) and inactive/not-allowed endpoints (`O0201`) |
| 온투업중앙기록관리 | P2P lending central record submission and queries | `send` for record create/update, `find` for record query | Institutional mock/handoff only under current account | KFTC P2P금융업무팀 replied on 2026-05-19 KST that API use is limited to 금융당국-registered 온투업자 and requires prior consultation plus registration proof |
| 금융결제데이터개방 / Datop | De-identified financial datasets, datasets by file/API, statistics | `find` | High-priority Live candidate after dataset-level credential rules are known | It is read-oriented and useful for public-interest analytics, but schemas differ per dataset |
| FIN MAP | ATM and branch location, detail, fee, environment APIs | `locate` primary, `find` for environment/fee tables | High-fit schema candidate, but DNS/network-gated before Live | Location data is public/low-PII and directly matches UMMAYA's location primitive; `openapi.finmap.or.kr` must resolve before adapter implementation |
| 대출이동 | Loan-switching and repayment inquiry APIs | `find` for loan/repayment info, `send` for switching/prepayment actions | Mock-to-live after approval and test identity flow | High citizen value, high harm if wrong; must require `check` delegation and explicit user confirmation |
| 뱅크페이 | Account-transfer PG/payment APIs | `send` | Handoff/mock until contract and tool approval | Payment initiation is irreversible and merchant-oriented; do not expose as Live without contract proof |

## Recommended Implementation Order

1. **OpenBanking 2-legged `oob` checks**: `testapi.openbanking.or.kr` accepts
   the current non-production Client ID/Secret for `scope=oob`. With
   `bank_tran_id` shaped as returned `client_use_code` + `U` + nine AN chars,
   계좌실명조회 reaches simulator/business validation and 수취조회 reaches the
   registered-contract-account gate. These are the first concrete Live-debug
   candidates, mapped to `check`, not `send`.
2. **OpenBanking OAuth/account-registration readiness for `inquiry`**: balance
   and transaction reads correctly reject the `oob` token with `O0011`. The next
   useful Live work is a `check`/delegation setup flow that obtains a user-bound
   authorization-code token, test user/account identifiers, and `fintech_use_num`
   handling without touching transfer endpoints.
3. **OpenBanking read-only `find` adapters**: once `inquiry` readiness is proven,
   implement balance, transaction, cards, prepaid, insurance, and loan-list
   reads before any money movement. These calls share the reachable
   `openapi.openbanking.or.kr` host and can reuse the same token/error envelope
   handling.
4. **OpenGiro live-read and live-send conversion**: keep current fixture-backed
   `send` adapters. The 2026-05-19 probes show the host is reachable, but
   payment URL endpoints differ between `O0101` token rejection and `O0201`
   inactive/not-allowed errors, so Live conversion needs per-endpoint activation
   evidence and a real callback/token path.
5. **FIN MAP live `locate` adapters after DNS/tool access is fixed**: the
   official pages expose endpoint paths, method `POST`, scope `finmap`, and
   location-oriented request shapes. However, `openapi.finmap.or.kr` currently
   fails DNS resolution from this network. Split into
   `kftc_finmap_atm_branch_locate`, `kftc_finmap_atm_detail_find`,
   `kftc_finmap_branch_detail_find`, and `kftc_finmap_atm_fee_find` only after
   DNS/VPN/allowlist or portal tool access is verified.
6. **Datop dataset discovery `find` adapter**: model it as a registry-backed
   dataset caller. The official Datop pages state dataset variables and output
   shapes vary by dataset, so the first tool should discover and fetch one
   dataset with a recorded schema rather than pretending all Datop datasets have
   one common contract.
7. **Financial identity rails**: keep financial certificate as a separate
   documentation/approval gate. Bio is now a stronger corporate-contract gate:
   KFTC says use requires application, review, approval, and contract execution,
   and is not available for individual, sole-proprietor, or research use.
   Therefore Bio should remain a schema-faithful handoff/mock surface for the
   current project, with registration/revocation documented only as protected
   `send` scenario shapes.
8. **Loan-switching and AccountInfo closure**: design after `check` delegation
   is stable and PayInfo hosts are reachable from the operator network. These
   are high-consequence workflows and should be spec-driven with red-team tests
   before any Live path.
9. **BankPay and P2P central records**: document as institutional handoff/mock
   until contracts and eligibility are proved. P2P is now an official policy
   gate, not merely a missing-version problem: KFTC requires registered
   온투업자 status and prior consultation before developer-site API use.

## Usage Method For Future Adapters

Every KFTC adapter should follow this sequence:

1. **Pick one official module**: use a developer-site page or one service
   module, not a whole service category.
2. **Classify the primitive**:
   - read-only public or delegated data -> `find`
   - geographic/nearby place resolution -> `locate`
   - identity, consent, certificate, or biometric verification -> `check`
   - payment, transfer, record creation, account closure, registration, or URL
     issuance -> `send`
3. **Record the KFTC gates**: service state, API Key state, Callback URL state,
   test-info state, token/tool access, and approval contact.
4. **Probe development/test first**: use the official test host if the page
   lists one. If no public test host is listed, use the portal `도구` path after
   approval or ask the 담당자; do not infer a host as official.
5. **Capture sanitized curl evidence**: request method, endpoint, headers,
   required parameters, status code, KFTC response code/message, and body shape.
   Never commit Client Secret, access tokens, auth codes, raw Authorization
   headers, or personal financial identifiers.
6. **Wrap in UMMAYA envelope**: map provider fields into `adapter_receipt` and
   keep the primitive output stable. Provider vocabulary belongs in `params` and
   receipt metadata, not in a new primitive.
7. **Fail closed by default**: Live calls are manual and opt-in; CI remains
   fixture-only. Missing token, missing callback, unapproved document access, or
   unknown test host returns setup-blocked, not fallback success.

### Example UMMAYA Calls

```json
{
  "primitive": "locate",
  "tool_id": "kftc_finmap_atm_branch_locate",
  "params": {
    "lat": 37.5665,
    "lon": 126.9780,
    "radius_m": 1000,
    "service_filter": ["atm", "branch"]
  }
}
```

```json
{
  "primitive": "find",
  "tool_id": "kftc_openbanking_balance_find",
  "params": {
    "fintech_use_num": "<delegated-fintech-use-num>",
    "delegation_token": "<issued-by-check>"
  }
}
```

```json
{
  "primitive": "send",
  "tool_id": "kftc_opengiro_payment_url_send",
  "params": {
    "operation": "create_link_payment_url",
    "giro_no": "1234567",
    "payment_reference": "BILL-2026-001",
    "amount_krw": 25000,
    "delegation_token": "<issued-by-check>"
  }
}
```

## Developer-Site OpenAPI Inventory

The endpoint-by-endpoint table is now separated into
[`kftc-openapi-endpoint-inventory.md`](./kftc-openapi-endpoint-inventory.md).
That file records every menu-visible canonical `/dev/openapi/**` page, the
visible `HTTP URL` rows, pages with no public URL table, and the first-pass
UMMAYA primitive fit for each row.

The deep debugging companion is
[`kftc-openapi-56-section-debug-report.md`](./kftc-openapi-56-section-debug-report.md).
Use it when choosing the next Spec Kit feature because it keeps the sidebar
routes separate and records each route's function, user-query coverage, request
inputs, token/scope requirement, direct probe result, root-cause classification,
UMMAYA adapter mapping, and next debugging action. OAuth is treated there as one
readiness section, not as a replacement for the business endpoint routes.

The 2026-05-19 refresh now separates sidebar rows from routable pages. The
public OpenAPI sidebar exposes 57 `button.title` rows and 49 unique routed
`vueMovePage(...)` pages. The scroll-verified pass opened all 49 unique pages,
recorded page-scroll evidence through Codex CUA scroll, and found 42 pages with
request-message specs plus 40 pages with at least one visible URL row. Each
concrete pair was either directly probed with a redacted invalid token, probed
with the credentialed `oob` test-host token where appropriate, or skipped only
when the official URL still contained a `{버전}` placeholder.

The follow-up replay called 64 concrete non-template endpoint URLs directly.
Twenty-six reached a provider auth envelope, 18 failed DNS, 11 reached a Bio test
host but returned HTTP 404, seven timed out at TCP connect, and two OpenGiro
production payment URL endpoints returned `O0201` inactive/not allowed. This
execution result is the basis for the current implementation order: first token
and test-user readiness on reachable OpenBanking/OpenGiro paths, then
network/allowlist debugging for FIN MAP and PayInfo. Bio and P2P are now
official policy/eligibility gates under the current account, so additional
technical retries are lower priority than obtaining the required institutional
approval.

## Approval Contacts Used

The service access notice lists the following 담당자 contacts. Approval request
Client-ID-inclusive approval emails were resent from the connected Gmail account
on 2026-05-19 KST for all listed services. KFTC P2P금융업무팀 has already replied
that 온투업 중앙기록관리업무 is restricted to registered 온투업자 use.

| Service | Contact |
|---|---|
| 오픈뱅킹 | `openbanking_tech@kftc.or.kr` |
| 어카운트인포 | `accountinfo@kftc.or.kr` |
| 금융인증 | `yeskeycert@kftc.or.kr` |
| 바이오인증 | `bio@kftc.or.kr` |
| 오픈지로 | `opengiro@kftc.or.kr` |
| 온투업중앙기록관리 | `p2pcenter@kftc.or.kr` |
| 금융결제데이터개방 | `datop@kftc.or.kr` |
| FIN MAP | `finmap@kftc.or.kr` |
| 대출이동 | `loan@kftc.or.kr` |
| 뱅크페이 | `bankpay@kftc.or.kr` |

## Boundary

This document does not authorize Live financial execution. It defines the
portfolio map and the safest next implementation order. Any adapter that moves
money, changes account state, registers identity data, or submits regulated
records must go through Spec Kit, direct development/test curl evidence,
credential isolation, explicit permission-gate receipts, and manual live-run
exclusion from CI.
