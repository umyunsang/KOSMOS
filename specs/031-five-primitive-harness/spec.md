# Feature Specification: Five-Primitive Harness Redesign

**Feature Branch**: `031-five-primitive-harness`
**Created**: 2026-04-19
**Status**: Draft
**Input**: User description: KOSMOS 메인 도구 surface를 5개 domain-agnostic primitive(`lookup` / `resolve_location` / `submit` / `subscribe` / `verify`)로 정규화. Claude Code always-loaded 5-tool 셋(Read / Edit / Grep / Bash / Glob)과 대응되는 harness 동사로, 부처·기관 특화 지식은 전부 adapter layer(`src/kosmos/tools/<ministry>/<adapter>.py`)로 격리. 근거 Discussion #1051. 주요 결정사항: (1) `submit`은 구 pay / issue_certificate / submit_application / reserve_slot / check_eligibility 5개 verb를 envelope 하나로 흡수. (2) `verify`는 한국 공표 티어(published_tier) 18종을 primary로, NIST AAL은 advisory hint로 분리 — 6-family discriminated union(gongdong_injeungseo / geumyung_injeungseo / ganpyeon_injeung / digital_onepass / mobile_id / mydata). (3) `subscribe`는 webhook 없이 CBS 방송 + REST pull + RSS 2.0 3계층을 하나의 스트림으로 통합. (4) Mock 설계서는 byte/shape mirror 가능한 6개 시스템(data.go.kr 16 도메인 / K-DIDF OmniOne did:omn / BaroCert / 마이데이터 / NPKI crypto layer / CBS 재난문자)만 포함. 정부24 민원 제출·KEC XML 서명부·NPKI 포털 세션은 시나리오 문서(`docs/scenarios/`)로만 기술. (5) KOSMOS는 CA / HSM / VC issuer 운영 금지 — harness-not-reimplementation 원칙 유지. 기존 Spec 022 `lookup` / `resolve_location` 구현 유지, 신규 추가는 `submit` / `subscribe` / `verify` 3종. `docs/security/tool-template-security-spec-v1.md`는 v1.2로 개정해 TOOL_MIN_AAL 표를 published_tier + nist_aal_hint 스키마로 전환(Spec 024 / 025 shipped 계약은 v1.2 배포 시점까지 유지).

---

## Context & Motivation

This feature replaces the previously rejected 8-verb main surface (`check_eligibility` / `reserve_slot` / `subscribe_alert` / `pay` / `issue_certificate` / `submit_application` + 2 resolvers) with 5 domain-agnostic primitives that mirror Claude Code's always-loaded 5-tool philosophy (Grep / Read / Glob / Edit / Bash). The 8-verb design leaked ministry knowledge into the main surface (e.g. `check_eligibility.declared_income_krw`, `pay.search_hint="공과금/세금"`, `issue_certificate.certificate_type` enum) and was rejected on 2026-04-19 alongside the full reset of Spec 031 v1, Epic #994, 55 sub-issues, and Discussion #506 (PR #1050).

This v2 redesign restores primitive-purity: the main surface declares *shape*; adapters own *domain*. The companion public record is Discussion #1051 (https://github.com/umyunsang/KOSMOS/discussions/1051).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — `submit` absorbs every write-transaction verb (Priority: P1)

A citizen agent completes a public-sector write action (pay a traffic fine, request a family-register certificate, submit a welfare application, reserve a civil-affairs timeslot, check welfare eligibility) through a **single** `submit` primitive envelope. The citizen never sees domain enum fields on the main surface; the adapter tree owns ministry-specific schemas, Literal enums, and cross-field validators.

**Why this priority**: `submit` is the largest surface-area collapse in the redesign (5 verbs → 1) and the primary evidence that ministry knowledge has been removed from the main surface. Without `submit` shipping, the 8-verb regression hasn't actually been reverted. It is also the highest-risk primitive — every failure mode of the old five verbs is inherited here and must be preserved across the adapter boundary.

**Independent Test**: Build one mock adapter (e.g. `src/kosmos/tools/mock/data_go_kr/fines_pay.py`) registered under a `tool_id`, invoke `submit(tool_id=..., params=...)`, and verify the harness returns a `(transaction_id, status, adapter_receipt)` triple without the main-surface schema containing any domain-specific field. Then register a *second* mock adapter under a different domain (e.g. mock welfare application) and prove both succeed through the same envelope.

**Acceptance Scenarios**:

1. **Given** a registered mock `submit` adapter for a public-sector write action, **When** the harness receives `submit(tool_id="mock_traffic_fine_pay_v1", params={<adapter-specific>})`, **Then** it returns an envelope `{transaction_id, status, adapter_receipt}` and the main `submit` Pydantic model exposes no fields named after any ministry, service, or transaction category.
2. **Given** two mock `submit` adapters from different ministries registered simultaneously, **When** each is invoked with its own `params` payload, **Then** both succeed and the adapter-specific validation errors surface through `adapter_receipt` rather than the main envelope.
3. **Given** an adapter whose invocation fails validation, **When** `submit` is called, **Then** a structured error result (not a raw exception) is returned and audit records are produced identically to the successful case.
4. **Given** the codebase post-merge, **When** an auditor greps the main `submit` Pydantic model for any of the strings `["check_eligibility", "reserve_slot", "subscribe_alert", "pay", "issue_certificate", "submit_application", "declared_income_krw", "certificate_type", "family_register", "resident_register"]`, **Then** zero matches are found.

---

### User Story 2 — `verify` publishes Korean tiers primary, NIST AAL advisory (Priority: P1)

A citizen agent needs an `AuthContext` that reflects the *Korean* published tier (e.g. `공동인증서` AAL3-tier, `PASS 간편인증` AAL2-tier, `모바일신분증` AAL2-tier) while also exposing an advisory NIST AAL hint for interop with US/international standards. The primary axis is the **18 published_tier labels** enumerated across the 6 authentication families; the `nist_aal_hint` is a *non-authoritative* secondary field.

**Why this priority**: The prior 8-verb design collapsed all Korean tiers into a single NIST-AAL dimension, which reject-reviewers flagged as "translation loss that erases the distinction between 공동인증서 and 금융인증서, and between PASS 간편인증 Level 2 and 디지털원패스 Level 2". This story restores fidelity while preserving interop. It is P1 because every downstream primitive (`submit`, `subscribe`) consumes `AuthContext` and a wrong shape here cascades.

**Independent Test**: For each of the 6 families, construct a `verify` call that produces an `AuthContext` with the correct `published_tier` label and matching `nist_aal_hint`. Confirm that a downstream consumer (e.g. `submit`) branches on `published_tier`, not on `nist_aal_hint`.

**Acceptance Scenarios**:

1. **Given** a `verify` input with `family_hint="gongdong_injeungseo"` and a valid mock session context, **When** the primitive executes, **Then** the returned `AuthContext` carries `published_tier="gongdong_injeungseo_aal3"` (or the exact label ratified in the published_tier enum) and `nist_aal_hint="AAL3"` as a separate advisory field.
2. **Given** an `AuthContext` with `published_tier="ganpyeon_injeung_kakao_aal2"` and `nist_aal_hint="AAL2"`, **When** an adapter enforces a minimum-tier policy, **Then** the adapter branches on the `published_tier` value and the `nist_aal_hint` is logged-only.
3. **Given** the 6-family discriminated union, **When** a caller passes a family_hint that does not match the actual session credentials, **Then** `verify` returns a structured mismatch error rather than silently coercing.
4. **Given** KOSMOS operates no CA / HSM / VC issuer, **When** `verify` is invoked, **Then** the primitive delegates credential verification to external Korean national infrastructure (금융결제원, PASS providers, 행정안전부 디지털원패스, 모바일 운전면허·주민등록증, 마이데이터 사업자) and never holds signing keys.

---

### User Story 3 — `subscribe` unifies CBS / REST pull / RSS 2.0 without webhook (Priority: P2)

A citizen agent receives emergency and advisory streams (긴급재난문자, 기상특보, 교통통제, 행정처분 알림) through a single `subscribe` primitive that yields an async iterator. The harness transparently handles the three delivery modalities (3GPP CBS broadcast Message IDs 4370–4385, periodic REST polling, RSS 2.0 feed tailing) without a webhook endpoint.

**Why this priority**: P2 because a Phase-1 citizen flow can survive on explicit `lookup` calls, but `subscribe` is the only primitive that expresses *passive observation* and is the natural home for the emergency-alert path that #287's TUI depends on. The webhook absence is deliberate — KOSMOS is a harness, not a hosted endpoint.

**Independent Test**: Register a mock CBS feed, a mock REST-pull feed, and a mock RSS feed under distinct `tool_id`s. `subscribe` to each and iterate. Confirm that events arrive through the same `AsyncIterator[Event]` interface and that subscription lifetime can be bounded.

**Acceptance Scenarios**:

1. **Given** a registered mock CBS adapter, **When** `subscribe(tool_id="mock_cbs_disaster_v1", lifetime=<bounded>)` is called, **Then** the caller receives an `AsyncIterator[Event]` whose events each carry a `kind` discriminator and the channel-native identifiers (e.g. CBS Message ID 4370).
2. **Given** a REST-pull adapter with a declared polling interval, **When** the subscription is active, **Then** events arrive at the declared interval and the harness does not require the caller to manage HTTP sessions.
3. **Given** an RSS 2.0 adapter, **When** the subscription is active, **Then** new items (since last-seen `guid`) surface as events and duplicates are suppressed.
4. **Given** `lifetime` expires or the caller explicitly cancels, **When** the subscription terminates, **Then** the underlying network resources are released and any in-flight events are either delivered or explicitly dropped with an audit record.
5. **Given** the primitive ships, **When** an auditor inspects the subscribe surface, **Then** no field accepts an inbound webhook URL — the harness does not operate as a receiver.

---

### User Story 4 — `lookup` / `resolve_location` preserved from Spec 022 (Priority: P1)

The existing `lookup` (mode = `search` | `fetch`) and `resolve_location` primitives shipped in Spec 022 continue to function unchanged under the new 5-primitive surface. No regression in Spec 022's existing 4 adapters (koroad_accident_hazard_search, kma_forecast_fetch, hira_hospital_search, nmc_emergency_search) and no change to the envelope `{mode, tool_id, params}`.

**Why this priority**: P1 because this story's *absence* of change is a precondition for the other primitives — if `lookup` / `resolve_location` contracts drift, downstream consumers break. This story exists explicitly to make the preservation requirement testable rather than implicit.

**Independent Test**: Re-run Spec 022's existing test suite against the new 5-primitive surface. All green, no adapter registration changes.

**Acceptance Scenarios**:

1. **Given** the Spec 022 test suite, **When** it runs against the merged branch, **Then** every test passes without modification.
2. **Given** the 4 Spec 022 adapters, **When** they are invoked through the new surface, **Then** their output shapes match the pre-redesign shapes exactly.
3. **Given** the main `lookup` Pydantic envelope, **When** compared to the Spec 022 baseline, **Then** the `{mode, tool_id, params}` structure is byte-identical.

---

### User Story 5 — Mock design scope = 6 mirror-able systems only (Priority: P2)

Mock design documents under `docs/mock/` include *only* the 6 systems that admit byte- or shape-level mirroring from public specs and reference implementations (data.go.kr 16 domains via serviceKey fixture recording; K-DIDF OmniOne did:omn via Apache-2.0 full stack; BaroCert via developers.barocert.com SDK docs; 마이데이터 via v240930 standard mTLS + OAuth 2.0; NPKI crypto layer only via PyPinkSign PKCS#7 / #12; CBS 긴급재난문자 via 3GPP TS 23.041 Message ID 4370–4385). The 3 OPAQUE items (정부24 민원 제출 — submission API withheld; KEC 전자세금계산서 XML 서명부 — XSD/public key withheld; NPKI 포털별 challenge-response — portal-proprietary sessions) are excluded from `docs/mock/` and documented only in `docs/scenarios/` with a scenario→mock promotion path triggered by institutional disclosure.

**Why this priority**: P2 because Spec 031 v1 can ship with only the 5 primitive contracts + 4 existing Spec 022 adapters. Mock expansion is ship-gated but not ship-blocking. Prioritising it explicitly prevents the main surface from learning fake contracts for OPAQUE systems (the "harness-not-reimplementation" failure mode).

**Independent Test**: After merge, verify that `docs/mock/` contains exactly 6 subdirectory trees (one per mirror-able system) and that `docs/scenarios/` contains user-journey markdown for the 3 OPAQUE items *without* any accompanying mock adapter.

**Acceptance Scenarios**:

1. **Given** the merged branch, **When** an auditor lists `docs/mock/`, **Then** exactly 6 system directories exist (data.go.kr / omnione / barocert / mydata / npki_crypto / cbs) each containing fixture directory + adapter stub + public-spec URL.
2. **Given** the merged branch, **When** an auditor lists `docs/scenarios/`, **Then** the 3 OPAQUE user journeys (정부24 제출, KEC XML 서명부, NPKI 포털 세션) are present and each explicitly states "이 단계에서 사용자가 실제 시스템으로 이동" or equivalent.
3. **Given** an institutional contribution lands later (e.g. 정부24 제출 API published), **When** the repository documents the promotion, **Then** the scenario entry moves into `docs/mock/` with a new adapter stub and the scenario file records the promotion.

---

### User Story 6 — Security Spec v1.2 replaces TOOL_MIN_AAL with dual-axis schema (Priority: P3)

`docs/security/tool-template-security-spec-v1.md` is bumped to v1.2, replacing the existing `TOOL_MIN_AAL` single-axis table (currently listing the 8 legacy tool IDs) with a dual-axis schema `(published_tier_minimum, nist_aal_hint)`. Spec 024 and Spec 025 shipped contracts (V1–V6 invariants, canonical auth-type ↔ auth-level mapping) are preserved verbatim until the v1.2 release tag; v1.2 deployment is the authoritative cutover point.

**Why this priority**: P3 because Spec 031 v1 can ship with the v1.1 doc still describing 8-tool shipping contracts — the v1.2 bump is a documentation concern and does not gate runtime behaviour of the new primitives. It must happen before Spec 031 v1.1 (bugfix release) to prevent the drift from compounding.

**Independent Test**: Diff `docs/security/tool-template-security-spec-v1.md` pre- and post-merge; confirm the `TOOL_MIN_AAL` table is replaced with a two-column `(published_tier_minimum, nist_aal_hint)` schema, v1.2 is tagged in the doc's metadata, and a migration note explains the v1.1→v1.2 transition.

**Acceptance Scenarios**:

1. **Given** the pre-merge v1.1 doc, **When** v1.2 lands, **Then** the TOOL_MIN_AAL table has been replaced with the dual-axis schema and an explicit "v1.1 contracts preserved until v1.2 GA" migration note.
2. **Given** the v1.2 doc, **When** any Spec 024 / 025 referenced invariant is consulted, **Then** it is present verbatim or explicitly delegated to the v1.2 schema.
3. **Given** the v1.2 cutover, **When** the new 5-primitive tools are registered, **Then** each registration declares both a `published_tier_minimum` and a `nist_aal_hint`.

---

### Edge Cases

- **Adapter tool_id collision**: Two adapters register the same `tool_id`. System MUST reject the second registration at boot with a structured error; first-registration-wins is the only stable resolution.
- **`submit` with missing adapter**: A caller invokes `submit(tool_id="does_not_exist", ...)`. System MUST return a structured `AdapterNotFoundError`, not raise.
- **`verify` mismatch between `family_hint` and session credentials**: Caller claims `family_hint="gongdong_injeungseo"` but the session holds a `ganpyeon_injeung` credential. System MUST return a structured mismatch error and MUST NOT coerce.
- **`subscribe` lifetime exhaustion mid-event**: An in-flight event arrives exactly as `lifetime` expires. System MUST either deliver-then-terminate or drop-with-audit; implementer must pick one and document.
- **CBS broadcast storm**: The mock CBS feed emits 100 events/sec during a drill. Subscribers MUST receive back-pressure rather than a silent drop.
- **RSS 2.0 feed publisher resets `guid`s**: System MUST treat reset `guid`s as new items (delivery is the safer default) and log the anomaly.
- **`published_tier` value not in the 18-label enum**: Adapter tries to emit an unknown tier. System MUST reject at Pydantic validation — the enum is closed in v1 (extensions require a spec amendment).
- **Spec 022 adapter invoked through a deprecated surface shape**: System MUST continue to accept Spec 022 shapes identically; there is no migration path because there is no change.
- **Institutional contribution that invalidates a mock**: A 정부24 spec drop disagrees with an existing mock assumption. System MUST treat the spec as authoritative and either update or retire the mock, never the reverse.
- **`nist_aal_hint` downgraded by NIST itself** (e.g. SP 800-63-4 renaming or removing a level): `published_tier` remains stable; `nist_aal_hint` is updated. Callers that branched on `published_tier` are unaffected.

---

## Requirements *(mandatory)*

### Functional Requirements

**`submit` primitive (5-verb absorption)**

- **FR-001**: System MUST expose a `submit` primitive with Pydantic v2 input schema `{tool_id: str, params: dict}` and output schema `{transaction_id: str, status: <enum>, adapter_receipt: dict}`.
- **FR-002**: The `submit` main-surface Pydantic model MUST NOT contain any ministry-specific, service-specific, or transaction-category field.
- **FR-003**: Ministry / service / category semantics MUST reside exclusively under `src/kosmos/tools/<ministry>/<adapter>.py` trees, each adapter owning its own Pydantic v2 input model, `async def invoke(params)` method, and registration metadata.
- **FR-004**: `submit` MUST produce a deterministic `transaction_id` per invocation and MUST emit an audit record per the Spec 024 `ToolCallAuditRecord` contract (preserved under v1.2 cutover rules — see FR-028).
- **FR-005**: `submit` MUST fail closed when an adapter is missing, misregistered, or raises — never leaking an unhandled exception to the tool loop.

**`verify` primitive (Korean tier primary, NIST AAL advisory)**

- **FR-006**: System MUST expose a `verify` primitive whose output is a 6-family discriminated union: `gongdong_injeungseo | geumyung_injeungseo | ganpyeon_injeung | digital_onepass | mobile_id | mydata`.
- **FR-007**: Each family variant MUST carry a `published_tier` field selected from the 18-label enum ratified in the Spec 031 plan (exhaustive enumeration ships in the plan, not in this spec).
- **FR-008**: Each family variant MUST carry a `nist_aal_hint` field (`AAL1 | AAL2 | AAL3`) as a *secondary advisory* — consumers MUST be able to branch on `published_tier` without reading `nist_aal_hint`.
- **FR-009**: `verify` MUST delegate credential verification to external Korean national infrastructure (금융결제원·은행·PASS providers·행정안전부 디지털원패스·모바일 신분증·마이데이터 사업자) — KOSMOS MUST NOT operate a CA, HSM, or VC issuer (harness-not-reimplementation).
- **FR-010**: `verify` MUST return a structured mismatch error when `family_hint` disagrees with session credentials; coercion is prohibited.

**`subscribe` primitive (3 modalities, no webhook)**

- **FR-011**: System MUST expose a `subscribe` primitive with input `{tool_id: str, params: dict, lifetime: Duration}` and output `AsyncIterator[Event] | subscription_handle`.
- **FR-012**: `subscribe` MUST support three delivery modalities under a uniform iterator surface: (a) 3GPP CBS broadcast (Message IDs 4370–4385), (b) periodic REST polling with adapter-declared interval, (c) RSS 2.0 feed tailing with `guid` de-duplication.
- **FR-013**: `subscribe` MUST NOT accept any inbound webhook URL field — the harness never operates as a receiver.
- **FR-014**: `subscribe` MUST release network resources on lifetime expiry or explicit cancellation and MUST record either delivery or dropped-with-audit for any event in flight at termination.
- **FR-015**: `subscribe` MUST propagate back-pressure to the adapter during burst conditions (per Edge Case: CBS broadcast storm).

**`lookup` / `resolve_location` preservation**

- **FR-016**: The `lookup` primitive envelope `{mode, tool_id, params}` from Spec 022 MUST remain byte-identical.
- **FR-017**: The `resolve_location` primitive shape from Spec 022 MUST remain byte-identical.
- **FR-018**: All 4 existing Spec 022 adapters (koroad_accident_hazard_search, kma_forecast_fetch, hira_hospital_search, nmc_emergency_search) MUST pass their existing test suite unchanged against the new 5-primitive surface.

**Adapter tree organisation**

- **FR-019**: The `src/kosmos/tools/` layout MUST organise adapters by ministry / institution (`src/kosmos/tools/<ministry>/<adapter>.py`), with a parallel mock tree at `src/kosmos/tools/mock/<ministry>/<adapter>.py`.
- **FR-020**: Each adapter MUST declare a globally unique `tool_id` at registration time; collisions MUST be rejected at boot with a structured error (first-wins is the only stable resolution).

**Mock scope separation**

- **FR-021**: `docs/mock/` MUST contain exactly these 6 mirror-able system trees: data.go.kr (16 domains) / omnione (K-DIDF did:omn) / barocert / mydata / npki_crypto / cbs.
- **FR-022**: Each `docs/mock/<system>/` MUST include a fixture directory, an adapter stub referencing `src/kosmos/tools/mock/<ministry>/<adapter>.py`, and a public-spec URL (OpenAPI / SDK docs / XSD / ECMA / 3GPP / Apache-2.0 reference impl).
- **FR-023**: `docs/scenarios/` MUST document exactly these 3 OPAQUE user journeys *without* mock adapters: 정부24 민원 제출, KEC XML 서명부, NPKI 포털별 challenge-response.
- **FR-024**: Each `docs/scenarios/<journey>.md` MUST state the point at which the user transitions out of KOSMOS to the real external system.
- **FR-025**: A scenario→mock promotion path MUST be documented: when an institution discloses the previously-opaque contract (e.g. 정부24 submission API becomes public), the scenario entry moves into `docs/mock/` and gains an adapter stub.
- **FR-026**: Adapters for OPAQUE systems MUST NOT be created in `src/kosmos/tools/mock/` — the harness must not encode fake contracts.

**Security spec v1.2**

- **FR-027**: `docs/security/tool-template-security-spec-v1.md` MUST be bumped to v1.2, replacing the `TOOL_MIN_AAL` single-axis table with a dual-axis `(published_tier_minimum, nist_aal_hint)` schema.
- **FR-028**: Until the v1.2 release tag, Spec 024 V1–V4 invariants and Spec 025 V6 invariant (and the canonical `auth_type` ↔ `auth_level` allow-list) MUST remain enforced verbatim.
- **FR-029**: v1.2 MUST include a migration note documenting the v1.1→v1.2 transition and explicitly listing which invariants were re-stated vs which were superseded.
- **FR-030**: Every new 5-primitive tool registration MUST declare both `published_tier_minimum` and `nist_aal_hint` on or after v1.2 GA.

**Backwards compatibility & observability**

- **FR-031**: The 5 primitives MUST emit Spec 021 / Spec 028 OTEL spans (`gen_ai.tool_loop.iteration` and peer attributes) identically to the existing Spec 022 emission surface.
- **FR-032**: Existing Spec 027 (agent swarm core) coordinator/worker contracts MUST continue to consume `lookup` / `resolve_location` outputs unchanged; `submit` / `subscribe` / `verify` integration with the swarm is out of scope for this spec (see Deferred Items).

### Key Entities

- **`SubmitEnvelope`** — main-surface input `{tool_id: str, params: dict}`; output `{transaction_id, status, adapter_receipt}`; no domain fields.
- **`AuthContext`** — discriminated union over 6 families; each variant carries `published_tier` (primary) + `nist_aal_hint` (advisory) + family-specific session metadata.
- **`SubscriptionEvent`** — discriminated on `kind` (`cbs_broadcast | rest_pull_tick | rss_item`); carries channel-native identifiers (CBS Message ID, REST response payload, RSS `guid`).
- **`AdapterRegistration`** — per-adapter metadata: `tool_id`, primitive (`submit`|`subscribe`|`verify`|`lookup`|`resolve_location`), source mode (`OPENAPI`|`OOS`|`harness-only`), Pydantic input model, `published_tier_minimum`, `nist_aal_hint`.
- **`ScenarioEntry`** — a `docs/scenarios/<journey>.md` file documenting an OPAQUE user journey with an explicit "KOSMOS ↔ real system" handoff point.
- **`MockSystemRoot`** — a `docs/mock/<system>/` directory containing fixtures, adapter stub, and public-spec URL.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After merge, the main-surface tool count is exactly 5 (`lookup`, `resolve_location`, `submit`, `subscribe`, `verify`) — verified by a one-line registry count assertion in the tool-loop tests.
- **SC-002**: After merge, the `submit` Pydantic model contains zero domain-specific field names — verified by a ripgrep assertion over the model file against a banned-words list (e.g. the 10 legacy strings enumerated in Acceptance Scenario 4 of User Story 1).
- **SC-003**: After merge, every Spec 022 test passes unchanged — verified by the existing `uv run pytest specs/022-*` suite remaining green.
- **SC-004**: After merge, `docs/mock/` contains exactly 6 system directories and `docs/scenarios/` contains exactly 3 OPAQUE journeys — verified by a `find`-based count in a docs-lint check.
- **SC-005**: After merge, `verify` callers can branch on `published_tier` without reading `nist_aal_hint` — verified by at least one integration test that exercises a `submit` adapter enforcing a `published_tier` minimum.
- **SC-006**: KOSMOS holds no private keys, CA certificates, or VC issuer material — verified by a grep of the repo and a `.gitignore` audit for forbidden extensions (`.pem` private halves, `.p12`, etc.) outside test fixtures explicitly scoped to mock NPKI crypto.
- **SC-007**: After `docs/security/tool-template-security-spec-v1.md` v1.2 lands, every registered 5-primitive tool declares both `published_tier_minimum` and `nist_aal_hint` — verified by a registration-time assertion.
- **SC-008**: No new runtime dependency is introduced by this spec — verified against `pyproject.toml` diff (AGENTS.md hard rule).
- **SC-009**: A fresh contributor reading `docs/vision.md § Claude Code` and this spec can map each of the 5 primitives to its Claude Code analogue (Grep / Read / Glob / Bash / Edit plus the two non-Claude-Code-native primitives `subscribe` / `verify`) in under 5 minutes — verified by an onboarding checklist entry.
- **SC-010**: The 8-verb regression cannot re-emerge silently — verified by a CI lint rule that rejects any new top-level tool registration matching the banned legacy verb names (`check_eligibility`, `reserve_slot`, `subscribe_alert`, `pay`, `issue_certificate`, `submit_application`).

---

## Assumptions

- Spec 022 primitives (`lookup`, `resolve_location`) remain the canonical implementation reference; no refactor of those is in scope here.
- Pydantic v2 `@model_validator` + `ToolRegistry.register()` backstop pattern from Spec 025 V6 is the intended enforcement site for new registration invariants (e.g. "both `published_tier_minimum` and `nist_aal_hint` present").
- The 18 `published_tier` labels are enumerated in the Spec 031 plan document (not in this spec) to keep the spec technology-agnostic. The plan will ratify the exact label strings.
- `submit` transaction semantics inherit Spec 024's `ToolCallAuditRecord` contract verbatim; v1.2 of the security spec clarifies how the dual-axis schema reshapes the audit record's `auth_level` field (migration note required).
- Discussion #1051 is the canonical public decision record; any discrepancy between this spec and #1051 is resolved by amending #1051 first, then this spec.
- The TUI Epic #287 is co-developed but *not* gated by this spec. #287 will require a body rewrite after this spec ships because its existing text references the deleted 8-verb facade (old Epic #994).
- Agent swarm (Spec 027) integration of `submit` / `subscribe` / `verify` is explicitly deferred (see Deferred Items) — the swarm currently consumes only `lookup` / `resolve_location` and that remains unchanged here.

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **KOSMOS-operated Certificate Authority, HSM, or Verifiable Credential issuer** — violates the harness-not-reimplementation principle (Constitution v1.3.0 Principle VI). `verify` is delegation-only.
- **Inbound webhooks for `subscribe`** — KOSMOS is a client-side harness, not a hosted endpoint. All `subscribe` delivery is CBS broadcast + REST pull + RSS tail.
- **Reverse-engineered mock adapters for OPAQUE systems** — 정부24 submission API, KEC XML 서명부 signature verification, and NPKI portal challenge-response sessions remain scenario-only. Encoding fake contracts for these would teach the harness to fail in novel ways when institutions contribute.
- **NIST AAL as primary authorisation axis** — the prior 8-verb design used AAL-only and was rejected. `nist_aal_hint` is advisory-only by permanent design.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Full Ink + React + Bun TUI renderers for `submit` / `subscribe` / `verify` outputs | TUI depends on frozen primitive output shapes shipping first | #287 Epic: Full TUI (Ink + React + Bun) | #287 |
| #287 body rewrite removing references to deleted 8-verb Epic #994 | Blocked on this spec shipping so that the replacement 5-primitive surface can be cited | #287 body maintenance | #1141 |
| Spec 027 agent-swarm integration of `submit` / `subscribe` / `verify` | Swarm contracts currently assume `lookup`-only; a separate spec amendment is needed to extend coordinator/worker messaging for write, streaming, and auth primitives | Spec 027 amendment (TBD) | #1142 |
| `docs/mock/` 6-system stub build-out (fixture recording + adapter stubs) | Spec 031 v1 ships only the primitive contracts; per-system mock stubs are shipped incrementally post-v1 | Spec 031 v1.1+ mock rollout | #1143 |
| `docs/scenarios/` content authoring for 3 OPAQUE journeys | Same as above — content work follows contract freeze | Spec 031 v1.1+ scenario authoring | #1144 |
| `docs/security/tool-template-security-spec-v1.md` v1.2 documentation revision bump (filename/header/matrix update only — the v1.2 **code** implementation ships in this spec via US6: `src/kosmos/security/v12_dual_axis.py` backstop + `V12_GA_ACTIVE` cutover) | Documentation revision is decoupled from the code freeze; docs PR follows to keep the primitive-contract PR small | Security spec v1.2 documentation PR | #1145 |
| Scenario→mock promotion automation (CI rule that blocks PR if a journey both exists in `docs/scenarios/` and has an adapter in `src/kosmos/tools/mock/`) | Manual discipline is sufficient for v1; automation needs its own spec | Spec 031 v1.2 automation pass | #1146 |
| CI lint rule rejecting re-introduction of legacy 8-verb names | Small but requires a separate GitHub Actions workflow definition | Spec 031 v1.1 tooling | #1147 |
| `published_tier` enum expansion beyond the ratified 18 labels (e.g. new Korean national ID schemes) | v1 closes the enum deliberately; future expansion requires a spec amendment | Future spec amendment | #1148 |
