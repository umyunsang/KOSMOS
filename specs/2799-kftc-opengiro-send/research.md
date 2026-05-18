# Research: KFTC OpenGiro Send Adapter

## Reference Bootstrap

- **UMMAYA thesis/docs**: `docs/vision.md` Layer 2 states each public-service channel is a schema-driven tool module with fail-closed defaults; `docs/requirements/ummaya-migration-tree.md` fixes active primitives as `find`, `locate`, `send`, `check`.
- **Claude Code restored source**: `.references/claude-code-sourcemap/restored-src/src/query/deps.ts` supports explicit dependency injection; `.references/claude-code-sourcemap/restored-src/src/services/oauth/auth-code-listener.ts` shows callback capture as a narrow listener that validates `state`; `.references/claude-code-sourcemap/restored-src/src/services/oauth/client.ts` shows redirect URI and token exchange are separate phases.
- **UMMAYA adapter sources**: `src/ummaya/primitives/submit.py` defines the `send` envelope and deterministic transaction id; `src/ummaya/tools/mock/data_go_kr/fines_pay.py` is the nearest existing financial send mock; `src/ummaya/tools/discovery_bridge.py` bridges send/check mock adapters into discovery; `scripts/build_schemas.py` exports send schemas.
- **External primary sources**: KFTC developer site public OpenGiro bill and payment pages; KFTC developer site starter guide; KFTC service-access notice; logged-in portal state observed through Computer Use on 2026-05-18.
- **Implementation constraints**: No live KFTC call in CI; no Client Secret lookup or storage; no arbitrary Callback URL registration; no live financial `send` gateway expansion in this epic.
- **Blocked evidence**: `/dev/doc/open-giro` still shows "접근 권한이 없습니다. 관리자에게 문의해 주세요."; API Key registration shows "등록된 Callback URL 이 없습니다."; 자료실 `오픈지로` search returns 0 results.

## Decision 1: Map OpenGiro to `send`

**Decision**: KFTC OpenGiro bill and payment modules are `send` adapters.

**Rationale**: Public OpenGiro pages expose bill creation/cancellation and payment URL/result flows. These are financial or payment-adjacent side effects, not read-only public-data lookups. UMMAYA's `send` envelope already absorbs write transactions and produces `SubmitOutput`.

**Alternatives considered**:
- `find`: rejected because payment URL creation and bill registration are not read-only.
- New `pay` primitive: rejected because `send` is the active reserved write primitive.

## Decision 2: Ship fixture-backed `mock_` adapters now

**Decision**: Implement `mock_kftc_opengiro_bill_send_v1` and `mock_kftc_opengiro_payment_send_v1` as official-shape, fixture-backed adapters.

**Rationale**: The user account has OpenGiro service in `이용중`, but API Key registration is blocked until a Callback URL exists. KFTC documents remain gated. AGENTS.md states: public API plus credential becomes Live; channel exists but no credential/access becomes Mock mirroring the reference shape. The correct status today is mock-to-live, not live.

**Alternatives considered**:
- Register a live adapter that silently returns fixture data: rejected because it would blur real settlement with mock behavior.
- Register a live adapter and attempt calls with incomplete credentials: rejected by the direct-curl evidence rule and KFTC portal blocker.

## Decision 3: Use two adapters for the two OpenGiro modules

**Decision**: Use two send adapters: bill service and payment service.

**Rationale**: KFTC presents OpenGiro as two modules: `부과서비스` and `납부서비스`. They have different operation sets and field groups. Two adapters keep schemas smaller and make discovery more precise while still belonging to one OpenGiro feature family.

**Alternatives considered**:
- One `operation`-switching mega-adapter: rejected because it would mix bill and payment schemas and weaken validation.
- One adapter per endpoint: rejected as too granular for the LLM tool surface.

## Decision 4: Canonical operator setup before live probing

**Decision**: Document a canonical UMMAYA callback path and setup readiness checklist, but do not register a Callback URL in the portal during this implementation.

**Rationale**: Registering a portal Callback URL changes third-party persistent account configuration. The deployment owner must choose the real gateway host. The agent should not store or reveal Client Secret values. The contract should tell operators exactly what readiness evidence is required.

**Alternatives considered**:
- Register `http://localhost:8000/auth/kftc/callback`: rejected because it may be wrong for production and the current UMMAYA gateway has no KFTC callback route.
- Click Client Secret 조회: rejected because secret retrieval is unnecessary and unsafe.

## Decision 5: Do not expand live adapter gateway in this epic

**Decision**: Keep live gateway send support deferred.

**Rationale**: `src/ummaya/gateway/app.py` and `src/ummaya/tools/live_proxy.py` currently constrain operator-managed live proxy calls to `find` and `locate`. Financial `send` gateway semantics need idempotency, irreversible-action handling, credential isolation, and stronger operator review. This feature can prepare fixture-backed adapters and setup docs without changing that architecture.

**Alternatives considered**:
- Add `send` to proxyable primitives now: rejected because it is a high-risk cross-cutting gateway change.

## Official KFTC Evidence Matrix

| Surface | Official URL | Evidence Used | Feature Decision |
|---|---|---|---|
| Developer starter workflow | `https://developers.kftc.or.kr/dev/starter/starter` | Service application, API Key creation, Callback URL registration, API Key registration, token issuance, REST API test tool sequence | Operator setup guide |
| OpenGiro bill service | `https://developers.kftc.or.kr/dev/openapi/open-giro/index` | `POST /v1/bills/giro`, `POST /v1/bills/giro/cancel`, `GET /v1/bills/giro/payment-yn` documented on public page | Bill send adapter |
| OpenGiro payment service | `https://developers.kftc.or.kr/dev/openapi/open-giro/pay-service` | `POST /v1/payments/giro-inqr-pay-url`, `POST /v1/payments/giro-inpt-pay-url`, `POST /v1/payments/link-pay-url`, `GET /v1/payments` documented on public page | Payment send adapter |
| Service access notice | `https://developers.kftc.or.kr/dev/support/notice/all/detail?id=44&boardCtgCd=all` | OpenGiro OpenAPI public; document/material access approval required; contact channel `opengiro@kftc.or.kr` observed in prior CUA research | Gated-doc blocker |
| OpenGiro launch notice | `https://developers.kftc.or.kr/dev/support/notice/all/detail?id=45&boardCtgCd=all` | Service added 2021-02-05, no attachment | Historical support only |

## Portal Readiness Evidence - 2026-05-18

| Portal Area | Observed State | Security Handling |
|---|---|---|
| `MY PAGE > 내 서비스 관리` | OpenGiro changed from `신청` to `이용중` | State change performed under user direction |
| `API Key 관리` | Client ID visible; Client Secret masked; OpenGiro APIs listed as `부과서비스`, `납부서비스` | Secret 조회 was not clicked |
| API Key registration | Clicking `등록` showed `등록된 Callback URL 이 없습니다.` | Treat as setup blocker |
| `문서 > 오픈지로` | Access denied alert | Do not invent gated spec |
| `지원 > 자료실` search for `오픈지로` | 0 results | Public docs not available through 자료실 |

## Deferred Item Validation

Spec deferred table has three tracked follow-up issues:

1. #2979: Production financial settlement confirmation beyond documented redirect/result APIs.
2. #2980: General live `send` gateway support for all financial adapters.
3. #2981: Additional KFTC services beyond OpenGiro.

All three are represented in the Deferred Items table and were converted to GitHub tracking issues by `/speckit-taskstoissues`.
